"""CLI surface for snapshots and compatibility, including file-only use."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

from jcheng_devices.compatibility import REQUIREMENTS_SCHEMA
from jcheng_devices.registry import Registry
from jcheng_devices.snapshot import OVERLAY_SCHEMA, build_snapshot, write_snapshot

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _run(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    command = [sys.executable, "-m", "jcheng_devices", *args]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _requirements(path: Path) -> Path:
    path.write_text(
        yaml.safe_dump(
            {
                "schema": REQUIREMENTS_SCHEMA,
                "device": "hiwonder.armpi-ultra",
                "capabilities": [
                    {"id": "arm.position_control", "required": True},
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def test_snapshot_cli_json_matches_the_library():
    result = _run("snapshot", "hiwonder.armpi-ultra", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    expected = build_snapshot(Registry.load(ROOT), "hiwonder.armpi-ultra")
    assert payload == expected


def test_snapshot_cli_writes_a_consumable_yaml_file(tmp_path):
    output = tmp_path / "armpi.yaml"
    result = _run(
        "snapshot", "hiwonder.armpi-ultra", "--output", str(output)
    )
    assert result.returncode == 0, result.stderr
    with output.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    assert data["schema"] == "jcheng.device_snapshot.v1"
    assert data["source_device"] == "hiwonder.armpi-ultra"
    assert data["content_hash"].startswith("sha256:")


def test_snapshot_cli_rejects_a_looser_overlay(tmp_path):
    overlay = tmp_path / "overlay.yaml"
    overlay.write_text(
        yaml.safe_dump(
            {
                "schema": OVERLAY_SCHEMA,
                "source": "system/test",
                "joint_limits": {
                    "joint1": {"min_deg": -200.0, "max_deg": 200.0}
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    result = _run(
        "snapshot",
        "hiwonder.armpi-ultra",
        "--overlay",
        str(overlay),
    )
    assert result.returncode == 1
    assert "OVERLAY_LOOSENS_LIMIT" in result.stderr


def test_snapshot_cli_unknown_device_exits_2():
    result = _run("snapshot", "vendor.missing")
    assert result.returncode == 2
    assert "unknown device id" in result.stderr


def test_compatibility_cli_passes_and_reports_json(tmp_path):
    snapshot = tmp_path / "snapshot.yaml"
    write_snapshot(
        build_snapshot(Registry.load(ROOT), "hiwonder.armpi-ultra"), snapshot
    )
    requirements = _requirements(tmp_path / "requirements.yaml")
    result = _run(
        "compatibility",
        "--requirements",
        str(requirements),
        "--snapshot",
        str(snapshot),
        "--json",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["deployable"] is True
    assert payload["errors"] == []


def test_compatibility_cli_fails_when_required_is_missing(tmp_path):
    snapshot = tmp_path / "snapshot.yaml"
    write_snapshot(
        build_snapshot(Registry.load(ROOT), "hiwonder.armpi-ultra"), snapshot
    )
    requirements = tmp_path / "requirements.yaml"
    requirements.write_text(
        yaml.safe_dump(
            {
                "schema": REQUIREMENTS_SCHEMA,
                "capabilities": [
                    {"id": "sensor.depth_stream", "required": True}
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    result = _run(
        "compatibility",
        "--requirements",
        str(requirements),
        "--snapshot",
        str(snapshot),
        "--json",
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["deployable"] is False
    codes = {issue["code"] for issue in payload["errors"]}
    assert "MISSING_REQUIRED_CAPABILITY" in codes


def test_compatibility_cli_human_output_has_a_verdict(tmp_path):
    snapshot = tmp_path / "snapshot.yaml"
    write_snapshot(
        build_snapshot(Registry.load(ROOT), "hiwonder.armpi-ultra"), snapshot
    )
    requirements = _requirements(tmp_path / "requirements.yaml")
    result = _run(
        "compatibility",
        "--requirements",
        str(requirements),
        "--snapshot",
        str(snapshot),
    )
    assert result.returncode == 0, result.stderr
    assert "deployable: hiwonder.armpi-ultra" in result.stdout
    assert "result: PASS" in result.stdout


def test_compatibility_cli_missing_file_exits_2(tmp_path):
    requirements = _requirements(tmp_path / "requirements.yaml")
    result = _run(
        "compatibility",
        "--requirements",
        str(requirements),
        "--snapshot",
        str(tmp_path / "missing.yaml"),
    )
    assert result.returncode == 2
    assert "cannot read" in result.stderr


def test_compatibility_cli_needs_no_registry(tmp_path):
    """A snapshot is a file artifact; the consumer does not need this repository."""

    snapshot = tmp_path / "snapshot.yaml"
    write_snapshot(
        build_snapshot(Registry.load(ROOT), "hiwonder.armpi-ultra"), snapshot
    )
    requirements = _requirements(tmp_path / "requirements.yaml")
    result = _run(
        "compatibility",
        "--requirements",
        str(requirements),
        "--snapshot",
        str(snapshot),
        "--json",
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["deployable"] is True
