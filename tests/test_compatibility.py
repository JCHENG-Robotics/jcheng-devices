"""Compatibility matching: pass, unknown, missing required, parameters, pins."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from jcheng_devices.compatibility import (
    REPORT_SCHEMA,
    REQUIREMENTS_SCHEMA,
    CompatibilityReport,
    match,
)
from jcheng_devices.hashing import content_hash
from jcheng_devices.registry import Registry
from jcheng_devices.snapshot import build_snapshot

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "registry" / "devices" / "hiwonder.armpi-ultra.yaml"


@pytest.fixture(scope="module")
def snapshot() -> dict:
    return build_snapshot(Registry.load(ROOT), "hiwonder.armpi-ultra")


def _requirements(*capabilities, **pins) -> dict:
    data = {
        "schema": REQUIREMENTS_SCHEMA,
        "capabilities": list(capabilities),
    }
    data.update(pins)
    return data


def _codes(report: CompatibilityReport) -> set[str]:
    return {issue.code for issue in report.errors}


def _statuses(report: CompatibilityReport) -> dict[str, str]:
    return {item.id: item.status for item in report.capabilities}


def test_required_capability_passes(snapshot):
    report = match(
        _requirements(
            {
                "id": "arm.position_control",
                "required": True,
                "parameters": {
                    "joint_names": [
                        "joint1",
                        "joint2",
                        "joint3",
                        "joint4",
                        "joint5",
                    ]
                },
            }
        ),
        snapshot,
    )
    assert report.ok is True
    assert report.deployable is True
    assert report.errors == ()
    assert report.warnings == ()
    assert _statuses(report) == {"arm.position_control": "satisfied"}


def test_omitted_required_defaults_to_true(snapshot):
    report = match(
        _requirements({"id": "sensor.depth_stream"}),
        snapshot,
    )
    assert report.deployable is False
    assert "MISSING_REQUIRED_CAPABILITY" in _codes(report)


def test_optional_missing_capability_is_a_warning(snapshot):
    report = match(
        _requirements(
            {"id": "arm.position_control", "required": True},
            {"id": "sensor.depth_stream", "required": False},
        ),
        snapshot,
    )
    assert report.ok is True
    assert report.deployable is True
    assert [issue.code for issue in report.warnings] == [
        "MISSING_OPTIONAL_CAPABILITY"
    ]


def test_unknown_capability_is_an_explicit_error(snapshot):
    report = match(
        _requirements({"id": "arm.unknown_control", "required": True}),
        snapshot,
    )
    assert report.deployable is False
    assert "UNKNOWN_CAPABILITY" in _codes(report)


def test_missing_required_capability_is_an_explicit_error(snapshot):
    report = match(
        _requirements({"id": "sensor.depth_stream", "required": True}),
        snapshot,
    )
    assert report.deployable is False
    assert "MISSING_REQUIRED_CAPABILITY" in _codes(report)


def test_parameter_name_mismatch_is_an_explicit_error(snapshot):
    report = match(
        _requirements(
            {
                "id": "arm.position_control",
                "required": True,
                "parameters": {"not_a_parameter": 1},
            }
        ),
        snapshot,
    )
    assert report.deployable is False
    assert "INCOMPATIBLE_PARAMETER" in _codes(report)
    assert _statuses(report) == {"arm.position_control": "incompatible"}


def test_parameter_type_mismatch_is_an_explicit_error(snapshot):
    report = match(
        _requirements(
            {
                "id": "arm.position_control",
                "required": True,
                "parameters": {"joint_names": "joint1"},
            }
        ),
        snapshot,
    )
    assert report.deployable is False
    assert "INCOMPATIBLE_PARAMETER" in _codes(report)


def test_duration_parameter_rejects_a_string(snapshot):
    report = match(
        _requirements(
            {
                "id": "arm.position_control",
                "required": True,
                "parameters": {"duration_s": "2 seconds"},
            }
        ),
        snapshot,
    )
    assert "INCOMPATIBLE_PARAMETER" in _codes(report)


def test_float_parameter_accepts_an_integer(snapshot):
    report = match(
        _requirements(
            {
                "id": "arm.position_control",
                "required": True,
                "parameters": {"duration_s": 2},
            }
        ),
        snapshot,
    )
    assert report.deployable is True


def test_device_version_mismatch_is_an_explicit_error(snapshot):
    report = match(
        _requirements(
            {"id": "arm.position_control", "required": True},
            device_version="9.9.9",
        ),
        snapshot,
    )
    assert report.deployable is False
    assert "DEVICE_VERSION_MISMATCH" in _codes(report)


def test_content_hash_mismatch_is_an_explicit_error(snapshot):
    report = match(
        _requirements(
            {"id": "arm.position_control", "required": True},
            content_hash="sha256:" + "0" * 64,
        ),
        snapshot,
    )
    assert report.deployable is False
    assert "CONTENT_HASH_MISMATCH" in _codes(report)


def test_bare_hex_content_hash_pin_is_accepted(snapshot):
    digest = content_hash(PROFILE)
    report = match(
        _requirements(
            {"id": "arm.position_control", "required": True},
            content_hash=digest.split(":", 1)[1],
        ),
        snapshot,
    )
    assert report.deployable is True
    assert report.content_hash == digest


def test_device_id_mismatch_is_an_explicit_error(snapshot):
    report = match(
        _requirements(
            {"id": "arm.position_control", "required": True},
            device="hiwonder.other-arm",
        ),
        snapshot,
    )
    assert report.deployable is False
    assert "DEVICE_ID_MISMATCH" in _codes(report)


def test_snapshot_schema_mismatch_is_rejected(snapshot):
    stale = copy.deepcopy(snapshot)
    stale["schema"] = "jcheng.device_snapshot.v0"
    report = match(
        _requirements({"id": "arm.position_control", "required": True}),
        stale,
    )
    assert report.deployable is False
    assert "SNAPSHOT_SCHEMA_MISMATCH" in _codes(report)


def test_requirements_with_no_required_capability_are_not_deployable(snapshot):
    report = match(
        _requirements({"id": "arm.position_control", "required": False}),
        snapshot,
    )
    assert report.ok is False
    assert report.deployable is False
    assert "NO_REQUIRED_CAPABILITY" in _codes(report)


def test_empty_requirements_are_not_deployable(snapshot):
    report = match(_requirements(), snapshot)
    assert report.ok is False
    assert report.deployable is False
    assert "NO_REQUIRED_CAPABILITY" in _codes(report)


def test_malformed_requirements_are_not_deployable(snapshot):
    report = match({"capabilities": "arm.position_control"}, snapshot)
    assert report.deployable is False
    assert "INVALID_REQUIREMENTS" in _codes(report)


def test_duplicate_requirement_is_rejected(snapshot):
    report = match(
        _requirements(
            {"id": "arm.position_control", "required": True},
            {"id": "arm.position_control", "required": True},
        ),
        snapshot,
    )
    assert report.deployable is False
    assert "INVALID_REQUIREMENTS" in _codes(report)


def test_snapshot_without_capabilities_is_rejected(snapshot):
    broken = copy.deepcopy(snapshot)
    broken["capabilities"] = []
    report = match(
        _requirements({"id": "arm.position_control", "required": True}),
        broken,
    )
    assert report.deployable is False
    assert "MISSING_REQUIRED_CAPABILITY" in _codes(report)


def test_report_is_json_serialisable(snapshot):
    report = match(
        _requirements({"id": "arm.position_control", "required": True}),
        snapshot,
    )
    payload = report.as_dict()
    assert payload["schema"] == REPORT_SCHEMA
    assert payload["deployable"] is True
    assert json.loads(json.dumps(payload)) == payload
    assert report["ok"] is True
    assert report.get("deployable") is True
