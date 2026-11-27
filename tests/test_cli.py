"""CLI behaviour: deterministic output, explicit exit codes, fail-closed validate."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from jcheng_devices import Registry

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _run(*args: str, root: Path | None = None) -> subprocess.CompletedProcess:
    command = [sys.executable, "-m", "jcheng_devices"]
    if root is not None:
        command += ["--root", str(root)]
    command += list(args)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_version():
    result = _run("--version")
    assert result.returncode == 0
    assert result.stdout.strip() == "0.1.0"


def test_validate_reports_ok_as_json():
    result = _run("validate", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["devices"] == 6
    assert payload["capabilities"] == 7
    assert payload["issues"] == []


def test_list_is_sorted_and_machine_readable():
    result = _run("list", "--json")
    assert result.returncode == 0, result.stderr
    rows = json.loads(result.stdout)
    assert [row["id"] for row in rows] == sorted(row["id"] for row in rows)
    assert all(set(row) == {"id", "category", "status", "verification", "path"} for row in rows)


def test_list_human_output_has_a_header_and_the_reference_device():
    result = _run("list")
    assert result.returncode == 0, result.stderr
    assert "ID" in result.stdout
    assert "hiwonder.armpi-ultra" in result.stdout


def test_show_returns_the_registered_profile():
    result = _run("show", "hiwonder.armpi-ultra", "--json")
    assert result.returncode == 0, result.stderr
    profile = json.loads(result.stdout)
    assert profile["id"] == "hiwonder.armpi-ultra"
    assert profile["kind"] == "device-profile"


def test_show_unknown_id_exits_2():
    result = _run("show", "vendor.missing")
    assert result.returncode == 2
    assert "unknown device id" in result.stderr


def test_digest_matches_the_library():
    result = _run("digest")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == Registry.load(ROOT).digest()


def test_validate_exits_1_on_a_broken_registry(tmp_path):
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    (registry_dir / "registry.yaml").write_text(
        "schema_version: 1\n"
        "devices:\n"
        "  - {id: vendor.missing, path: devices/vendor.missing.yaml}\n"
        "  - {id: vendor.missing, path: devices/vendor.missing.yaml}\n"
        "capabilities: []\n",
        encoding="utf-8",
    )
    result = _run("validate", "--json", root=tmp_path)
    assert result.returncode == 1, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    codes = [issue["code"] for issue in payload["issues"]]
    assert "duplicate" in codes
    assert "path" in codes
