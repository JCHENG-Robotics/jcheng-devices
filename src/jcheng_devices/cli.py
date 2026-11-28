"""Command line interface for the offline device library.

Commands are read-only and deterministic. ``validate`` exits 1 when any issue
is found, so CI fails closed. ``snapshot`` writes a deployment-shaped file and
``compatibility`` matches requirements against such a file; neither opens a
device or joins a runtime.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

import yaml

from .compatibility import CompatibilityReport, load_requirements, match
from .errors import LoadError
from .registry import Registry
from .snapshot import (
    SnapshotError,
    build_snapshot,
    dump_snapshot,
    load_overlay,
    load_snapshot,
    write_snapshot,
)
from .version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jcheng-devices",
        description=(
            "Validate and inspect declarative device profiles. "
            "Offline only: no device is opened and no runtime graph is joined."
        ),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repository root containing registry/registry.yaml (default: search upward)",
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="list registered devices")
    list_parser.add_argument("--json", action="store_true", dest="as_json")

    show_parser = sub.add_parser("show", help="show one device profile")
    show_parser.add_argument("profile_id")
    show_parser.add_argument("--json", action="store_true", dest="as_json")

    validate_parser = sub.add_parser(
        "validate", help="validate the registry and every profile"
    )
    validate_parser.add_argument("--json", action="store_true", dest="as_json")

    digest_parser = sub.add_parser(
        "digest", help="print a deterministic sha256 of the registry content"
    )
    digest_parser.add_argument("--json", action="store_true", dest="as_json")

    snapshot_parser = sub.add_parser(
        "snapshot",
        help="generate a deterministic deployment snapshot for one device",
    )
    snapshot_parser.add_argument("device_id")
    snapshot_parser.add_argument(
        "--overlay",
        type=Path,
        default=None,
        help="safety overlay YAML; it may only tighten joint limits or workspace",
    )
    snapshot_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="write the snapshot to this file instead of standard output",
    )
    snapshot_parser.add_argument("--json", action="store_true", dest="as_json")

    compatibility_parser = sub.add_parser(
        "compatibility",
        help="match device capability requirements against a snapshot file",
    )
    compatibility_parser.add_argument(
        "--requirements",
        type=Path,
        required=True,
        help="requirements YAML (jcheng.device_requirements.v1)",
    )
    compatibility_parser.add_argument(
        "--snapshot",
        type=Path,
        required=True,
        help="snapshot YAML (jcheng.device_snapshot.v1)",
    )
    compatibility_parser.add_argument("--json", action="store_true", dest="as_json")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Compatibility consumes two files and does not need the registry; keeping
    # it registry-free makes the snapshot a standalone consumer artifact.
    if args.command == "compatibility":
        return _compatibility(args)

    try:
        registry = Registry.load(args.root)
    except LoadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.command == "validate":
        return _validate(registry, args.as_json)
    if args.command == "list":
        return _list(registry, args.as_json)
    if args.command == "show":
        return _show(registry, args.profile_id, args.as_json)
    if args.command == "digest":
        return _digest(registry, args.as_json)
    if args.command == "snapshot":
        return _snapshot(registry, args)
    print(f"error: unknown command {args.command}", file=sys.stderr)
    return 2


def _validate(registry: Registry, as_json: bool) -> int:
    payload = {
        "ok": registry.ok,
        "devices": len(registry.devices),
        "capabilities": len(registry.capabilities),
        "issues": [issue.as_dict() for issue in registry.issues],
    }
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif registry.ok:
        print(
            f"ok: {payload['devices']} devices, "
            f"{payload['capabilities']} capabilities"
        )
    else:
        for issue in registry.issues:
            print(issue.render(), file=sys.stderr)
        print(
            f"failed: {len(registry.issues)} issue(s)",
            file=sys.stderr,
        )
    return 0 if registry.ok else 1


def _list(registry: Registry, as_json: bool) -> int:
    rows = registry.device_rows()
    if as_json:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    if not rows:
        print("no devices registered")
        return 0
    columns = ("id", "category", "status", "verification", "path")
    widths = {
        column: max(len(column), *(len(row[column]) for row in rows))
        for column in columns
    }
    print("  ".join(column.upper().ljust(widths[column]) for column in columns))
    for row in rows:
        print("  ".join(row[column].ljust(widths[column]) for column in columns))
    return 0


def _show(registry: Registry, profile_id: str, as_json: bool) -> int:
    if profile_id not in registry.devices:
        print(f"error: unknown device id: {profile_id}", file=sys.stderr)
        return 2
    profile = registry.devices[profile_id].profile
    if as_json:
        print(json.dumps(profile, indent=2, sort_keys=True))
    else:
        print(yaml.safe_dump(profile, sort_keys=False, allow_unicode=True), end="")
    return 0


def _digest(registry: Registry, as_json: bool) -> int:
    payload = {
        "digest": registry.digest(),
        "devices": len(registry.devices),
        "capabilities": len(registry.capabilities),
    }
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload["digest"])
    return 0


def _snapshot(registry: Registry, args: argparse.Namespace) -> int:
    if not registry.ok:
        for issue in registry.issues:
            print(issue.render(), file=sys.stderr)
        print(
            f"failed: {len(registry.issues)} issue(s); refusing to snapshot",
            file=sys.stderr,
        )
        return 1
    if args.device_id not in registry.devices:
        print(f"error: unknown device id: {args.device_id}", file=sys.stderr)
        return 2

    overlay = None
    if args.overlay is not None:
        try:
            overlay = load_overlay(args.overlay)
        except LoadError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    try:
        snapshot = build_snapshot(registry, args.device_id, overlay=overlay)
    except SnapshotError as exc:
        for issue in exc.issues:
            print(issue.render(), file=sys.stderr)
        print(f"failed: {len(exc.issues)} overlay issue(s)", file=sys.stderr)
        return 1

    if args.output is None:
        print(dump_snapshot(snapshot, as_json=args.as_json), end="")
        return 0
    try:
        write_snapshot(snapshot, args.output, as_json=args.as_json)
    except OSError as exc:
        print(f"error: cannot write {args.output}: {exc}", file=sys.stderr)
        return 2
    return 0


def _compatibility(args: argparse.Namespace) -> int:
    try:
        requirements = load_requirements(args.requirements)
    except LoadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        snapshot = load_snapshot(args.snapshot)
    except LoadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except SnapshotError as exc:
        for issue in exc.issues:
            print(issue.render(), file=sys.stderr)
        print(f"failed: {len(exc.issues)} snapshot issue(s)", file=sys.stderr)
        return 1

    report = match(requirements, snapshot)
    if args.as_json:
        print(
            json.dumps(
                report.as_dict(), indent=2, sort_keys=True, ensure_ascii=False
            )
        )
    else:
        _print_compatibility(report)
    return 0 if report.deployable else 1


def _print_compatibility(report: CompatibilityReport) -> None:
    verdict = "deployable" if report.deployable else "not deployable"
    print(f"{verdict}: {report.device} {report.device_version} ({report.content_hash})")
    for item in report.capabilities:
        suffix = "required" if item.required else "optional"
        print(f"  {item.status}: {item.id} ({suffix})")
    for warning in report.warnings:
        print(f"warning: {warning.render()}", file=sys.stderr)
    for error in report.errors:
        print(f"error: {error.render()}", file=sys.stderr)
    print(
        f"result: {'PASS' if report.deployable else 'FAIL'} "
        f"({len(report.errors)} error(s), {len(report.warnings)} warning(s))"
    )
