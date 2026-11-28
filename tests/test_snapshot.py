"""Deployment snapshots: provenance, determinism and overlay tightening."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from jcheng_devices import __version__
from jcheng_devices.hashing import content_hash, content_hash_of
from jcheng_devices.registry import Registry
from jcheng_devices.snapshot import (
    GENERATED_BY,
    OVERLAY_SCHEMA,
    SNAPSHOT_FIELDS,
    SNAPSHOT_SCHEMA,
    SnapshotError,
    build_snapshot,
    dump_snapshot,
    load_snapshot,
    validate_snapshot,
    write_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "registry" / "devices" / "hiwonder.armpi-ultra.yaml"
BASE_LIMITS = {
    "joint1": (-103.2, 103.2),
    "joint2": (-37.9, 66.0),
    "joint3": (-103.2, 0.0),
    "joint4": (-91.2, 91.2),
    "joint5": (-91.2, 88.8),
}


@pytest.fixture(scope="module")
def registry() -> Registry:
    return Registry.load(ROOT)


@pytest.fixture(scope="module")
def snapshot(registry: Registry) -> dict:
    return build_snapshot(registry, "hiwonder.armpi-ultra")


def _overlay(**overrides) -> dict:
    data = {
        "schema": OVERLAY_SCHEMA,
        "source": "jcheng-system/configs/robots/armpi_ultra/profile.yaml",
        "joint_limits": {"joint1": {"min_deg": -100.0, "max_deg": 100.0}},
    }
    data.update(overrides)
    return data


def _limits(snapshot: dict) -> dict[str, tuple[float, float]]:
    return {
        joint["name"]: (
            joint["limits"]["min_deg"],
            joint["limits"]["max_deg"],
        )
        for joint in snapshot["joints"]
    }


def _codes(exc: SnapshotError) -> set[str]:
    return {issue.code for issue in exc.issues}


def test_snapshot_has_exactly_the_v1_fields(snapshot):
    assert tuple(snapshot) == SNAPSHOT_FIELDS
    assert snapshot["schema"] == SNAPSHOT_SCHEMA
    assert validate_snapshot(snapshot) == []


def test_snapshot_provenance_matches_the_source_profile(snapshot):
    assert snapshot["source_device"] == "hiwonder.armpi-ultra"
    assert snapshot["device_version"] == "0.1.0"
    assert snapshot["content_hash"] == content_hash(PROFILE)
    assert snapshot["generated_by"] == GENERATED_BY
    assert snapshot["generated_by"].endswith(__version__)
    assert snapshot["source_path"] == "registry/devices/hiwonder.armpi-ultra.yaml"


def test_snapshot_capabilities_are_sorted_and_declared(snapshot):
    ids = [capability["id"] for capability in snapshot["capabilities"]]
    assert ids == sorted(ids)
    assert ids == ["arm.joint_feedback", "arm.position_control"]
    position = next(
        capability
        for capability in snapshot["capabilities"]
        if capability["id"] == "arm.position_control"
    )
    parameters = {row["name"]: row for row in position["parameters"]}
    assert parameters["joint_names"]["type"] == "list"
    assert parameters["joint_names"]["required"] is True
    assert parameters["duration_s"]["required"] is False
    feedback = {row["name"]: row for row in position["feedback"]}
    assert feedback["position_deg"]["unit"] == "deg"


def test_snapshot_joints_keep_profile_order_and_limits(snapshot):
    assert [joint["name"] for joint in snapshot["joints"]] == list(BASE_LIMITS)
    assert _limits(snapshot) == BASE_LIMITS
    assert snapshot["joints"][0]["role"] == "shoulder_pan"


def test_snapshot_is_byte_deterministic(registry):
    first = build_snapshot(registry, "hiwonder.armpi-ultra")
    second = build_snapshot(registry, "hiwonder.armpi-ultra")
    assert first == second
    assert dump_snapshot(first) == dump_snapshot(second)
    assert dump_snapshot(first, as_json=True) == dump_snapshot(
        second, as_json=True
    )


def test_snapshot_without_overlay_records_not_applied(snapshot):
    assert snapshot["safety_overlay"] == {
        "applied": False,
        "source": None,
        "content_hash": None,
        "stricter_wins": True,
    }


def test_overlay_tightens_joint_limits_and_records_its_hash(registry):
    overlay = _overlay()
    tightened = build_snapshot(registry, "hiwonder.armpi-ultra", overlay=overlay)
    assert _limits(tightened)["joint1"] == (-100.0, 100.0)
    assert tightened["safety_overlay"]["applied"] is True
    assert tightened["safety_overlay"]["source"] == overlay["source"]
    assert tightened["safety_overlay"]["content_hash"] == content_hash_of(overlay)
    assert tightened["safety_overlay"]["stricter_wins"] is True
    assert "stricter bounds win" in tightened["notes"]


def test_overlay_workspace_tightens_the_joint_box(registry):
    overlay = _overlay(
        joint_limits={},
        workspace={
            "min_deg": [-90.0, -30.0, -90.0, -80.0, -80.0],
            "max_deg": [90.0, 60.0, 0.0, 80.0, 80.0],
        },
    )
    tightened = build_snapshot(registry, "hiwonder.armpi-ultra", overlay=overlay)
    assert _limits(tightened) == {
        "joint1": (-90.0, 90.0),
        "joint2": (-30.0, 60.0),
        "joint3": (-90.0, 0.0),
        "joint4": (-80.0, 80.0),
        "joint5": (-80.0, 80.0),
    }


def test_overlay_applies_the_stricter_of_limit_and_workspace(registry):
    overlay = _overlay(
        joint_limits={"joint1": {"min_deg": -100.0, "max_deg": 100.0}},
        workspace={
            "min_deg": [-90.0, -37.9, -103.2, -91.2, -91.2],
            "max_deg": [90.0, 66.0, 0.0, 91.2, 88.8],
        },
    )
    tightened = build_snapshot(registry, "hiwonder.armpi-ultra", overlay=overlay)
    assert _limits(tightened)["joint1"] == (-90.0, 90.0)
    assert _limits(tightened)["joint2"] == (-37.9, 66.0)


def test_overlay_cannot_loosen_a_joint_limit(registry):
    overlay = _overlay(
        joint_limits={"joint1": {"min_deg": -200.0, "max_deg": 200.0}}
    )
    with pytest.raises(SnapshotError) as excinfo:
        build_snapshot(registry, "hiwonder.armpi-ultra", overlay=overlay)
    assert "OVERLAY_LOOSENS_LIMIT" in _codes(excinfo.value)


def test_overlay_cannot_loosen_the_workspace(registry):
    overlay = _overlay(
        joint_limits={},
        workspace={
            "min_deg": [-200.0, -30.0, -90.0, -80.0, -80.0],
            "max_deg": [90.0, 60.0, 0.0, 80.0, 80.0],
        },
    )
    with pytest.raises(SnapshotError) as excinfo:
        build_snapshot(registry, "hiwonder.armpi-ultra", overlay=overlay)
    assert "OVERLAY_LOOSENS_WORKSPACE" in _codes(excinfo.value)


def test_overlay_cannot_name_an_unknown_joint(registry):
    overlay = _overlay(joint_limits={"joint9": {"min_deg": -1.0, "max_deg": 1.0}})
    with pytest.raises(SnapshotError) as excinfo:
        build_snapshot(registry, "hiwonder.armpi-ultra", overlay=overlay)
    assert "OVERLAY_UNKNOWN_JOINT" in _codes(excinfo.value)


def test_overlay_rejects_unknown_fields(registry):
    overlay = _overlay(cartesian_workspace={"lower": [0, 0, 0]})
    with pytest.raises(SnapshotError) as excinfo:
        build_snapshot(registry, "hiwonder.armpi-ultra", overlay=overlay)
    assert "OVERLAY_UNKNOWN_FIELD" in _codes(excinfo.value)


def test_overlay_must_tighten_something(registry):
    overlay = _overlay(joint_limits={})
    with pytest.raises(SnapshotError) as excinfo:
        build_snapshot(registry, "hiwonder.armpi-ultra", overlay=overlay)
    assert "OVERLAY_EMPTY" in _codes(excinfo.value)


def test_overlay_requires_its_schema_and_source(registry):
    overlay = _overlay(schema="wrong", source="")
    with pytest.raises(SnapshotError) as excinfo:
        build_snapshot(registry, "hiwonder.armpi-ultra", overlay=overlay)
    codes = _codes(excinfo.value)
    assert "OVERLAY_SCHEMA" in codes
    assert "OVERLAY_SOURCE" in codes


def test_overlay_workspace_requires_a_device_with_joints(registry):
    overlay = _overlay(
        joint_limits={},
        workspace={"min_deg": [], "max_deg": []},
    )
    with pytest.raises(SnapshotError) as excinfo:
        build_snapshot(registry, "intel.realsense-d435i", overlay=overlay)
    assert "OVERLAY_INVALID_WORKSPACE" in _codes(excinfo.value)


def test_unknown_device_raises_key_error(registry):
    with pytest.raises(KeyError):
        build_snapshot(registry, "vendor.missing")


def test_snapshot_file_is_plain_data(tmp_path, snapshot):
    yaml_path = write_snapshot(snapshot, tmp_path / "snapshot.yaml")
    json_path = write_snapshot(snapshot, tmp_path / "snapshot.json", as_json=True)
    with yaml_path.open(encoding="utf-8") as handle:
        assert yaml.safe_load(handle) == snapshot
    with json_path.open(encoding="utf-8") as handle:
        assert json.load(handle) == snapshot
    assert load_snapshot(yaml_path) == snapshot


def test_sensor_snapshot_has_no_joints(registry):
    sensor = build_snapshot(registry, "intel.realsense-d435i")
    assert sensor["joints"] == []
    assert [capability["id"] for capability in sensor["capabilities"]] == [
        "sensor.depth_stream",
        "sensor.rgb_stream",
    ]
    assert validate_snapshot(sensor) == []


def test_validate_snapshot_rejects_a_missing_field(snapshot):
    broken = dict(snapshot)
    del broken["content_hash"]
    codes = {issue.code for issue in validate_snapshot(broken)}
    assert "INVALID_SNAPSHOT" in codes
