"""Profile-level invariants: no guessed parameters, no unmarked claims."""

from __future__ import annotations

import re
from pathlib import Path

from jcheng_devices import Registry

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = Registry.load(ROOT)
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*\.[a-z0-9][a-z0-9-]*$")


def test_registry_loads_without_issues():
    assert REGISTRY.ok, "\n".join(issue.render() for issue in REGISTRY.issues)


def test_every_device_has_a_vendor_source():
    for entry in REGISTRY.devices.values():
        vendor = entry.profile["vendor"]
        assert vendor["source"].strip(), entry.id
        assert vendor["verification"] in {
            "verified",
            "partially_verified",
            "unverified",
        }, entry.id


def test_every_profile_has_a_verification_statement():
    for entry in (*REGISTRY.devices.values(), *REGISTRY.capabilities.values()):
        verification = entry.profile["verification"]
        assert verification["notes"].strip(), entry.id
        if verification["status"] in {"verified", "partially_verified"}:
            assert verification["evidence"], entry.id
            assert verification["date"], entry.id


def test_v010_makes_no_verified_profile_claim():
    """This repository has not measured any device itself."""

    for entry in REGISTRY.devices.values():
        assert entry.profile["verification"]["status"] != "verified", entry.id
    for entry in REGISTRY.capabilities.values():
        assert entry.profile["verification"]["status"] != "verified", entry.id


def test_device_ids_follow_vendor_slug():
    for entry in REGISTRY.devices.values():
        assert ID_PATTERN.fullmatch(entry.id), entry.id


def test_arm_profiles_have_consistent_kinematics():
    arm_entries = [
        entry
        for entry in REGISTRY.devices.values()
        if entry.profile["category"] == "arm"
        and entry.profile.get("data_status") != "missing"
    ]
    assert arm_entries
    for entry in arm_entries:
        kinematics = entry.profile["kinematics"]
        joints = kinematics["joints"]
        assert kinematics["dof"] == len(joints), entry.id
        names = [joint["name"] for joint in joints]
        assert len(names) == len(set(names)), entry.id
        for joint in joints:
            assert joint["source"].strip(), f"{entry.id}/{joint['name']}"
            assert isinstance(joint["verified"], bool)
            assert joint["limits"]["min_deg"] < joint["limits"]["max_deg"], (
                f"{entry.id}/{joint['name']}"
            )


def test_sensor_profiles_are_sourced_and_marked():
    sensor_entries = [
        entry
        for entry in REGISTRY.devices.values()
        if entry.profile["category"] == "sensor"
    ]
    assert sensor_entries
    for entry in sensor_entries:
        sensor = entry.profile["sensor"]
        assert sensor["source"].strip(), entry.id
        assert isinstance(sensor["verified"], bool)
        if "range_m" in sensor:
            assert sensor["range_m"][0] < sensor["range_m"][1], entry.id


def test_capability_profiles_have_unique_parameters_and_constraints():
    for entry in REGISTRY.capabilities.values():
        profile = entry.profile
        parameter_names = [parameter["name"] for parameter in profile["parameters"]]
        feedback_names = [item["name"] for item in profile["feedback"]]
        assert len(parameter_names) == len(set(parameter_names)), entry.id
        assert len(feedback_names) == len(set(feedback_names)), entry.id
        assert profile["constraints"], entry.id
        for required in profile.get("requires", []):
            assert required in REGISTRY.capabilities, entry.id


def test_no_device_profile_ships_an_asset_path_yet():
    """v0.1.0 has no copied URDF, calibration file or simulation asset."""

    for entry in REGISTRY.devices.values():
        assert "assets" not in entry.profile, entry.id


def test_capability_rows_are_sorted():
    rows = REGISTRY.capability_rows()
    ids = [row["id"] for row in rows]
    assert ids == sorted(ids)
    assert all(row["path"].startswith("registry/capabilities/") for row in rows)
