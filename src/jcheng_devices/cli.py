"""Command line interface for the offline device library.

Commands are read-only and deterministic. ``validate`` exits 1 when any issue
is found, so CI fails closed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

import yaml

from .errors import LoadError
from .registry import Registry
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

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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
