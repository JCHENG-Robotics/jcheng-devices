"""Fact checks for the reference and candidate devices.

These tests pin the facts that were actually read from the workspace. They do
not upgrade any verification status: the ArmPi Ultra profile remains
partially verified and the PiPER X profile remains unverified.
"""

from __future__ import annotations

from pathlib import Path

from jcheng_devices import Registry

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = Registry.load(ROOT)


def _profile(profile_id: str) -> dict:
    return REGISTRY.devices[profile_id].profile


def test_armpi_ultra_is_the_reference_arm():
    profile = _profile("hiwonder.armpi-ultra")
    assert profile["category"] == "arm"
    assert profile["status"] == "reference"
    assert profile["verification"]["status"] == "partially_verified"
    kinematics = profile["kinematics"]
    assert kinematics["dof"] == 5
    assert [joint["name"] for joint in kinematics["joints"]] == [
        "joint1",
        "joint2",
        "joint3",
        "joint4",
        "joint5",
    ]
    assert set(profile["capabilities"]) == {
        "arm.position_control",
        "arm.joint_feedback",
    }


def test_armpi_ultra_joint_limits_match_the_learning_adapter():
    joints = _profile("hiwonder.armpi-ultra")["kinematics"]["joints"]
    expected = {
        "joint1": (-103.2, 103.2),
        "joint2": (-37.9, 66.0),
        "joint3": (-103.2, 0.0),
        "joint4": (-91.2, 91.2),
        "joint5": (-91.2, 88.8),
    }
    for joint in joints:
        low, high = expected[joint["name"]]
        assert joint["limits"]["min_deg"] == low
        assert joint["limits"]["max_deg"] == high
        assert joint["verified"] is False


def test_armpi_profile_defers_runtime_authority_to_the_system_profile():
    profile = _profile("hiwonder.armpi-ultra")
    for joint in profile["kinematics"]["joints"]:
        assert "system robot profile" in joint["source"].lower()
    assert "runtime authority" in profile["verification"]["notes"].lower()
    assert any(
        "configs/robots/armpi_ultra/profile.yaml" in link
        for link in profile["verification"]["evidence"]
    )


def test_piper_profile_cites_the_simulation_only_system_profile():
    profile = _profile("agilex.piper-x")
    assert "simulation-only" in profile["vendor"]["source"].lower()
    for joint in profile["kinematics"]["joints"]:
        assert "simulation-only robot profile" in joint["source"].lower()


def test_armpi_bus_ids_are_recorded_without_a_pulse_contract():
    profile = _profile("hiwonder.armpi-ultra")
    assert "1-6" in profile["hardware"]["bus"]
    assert "radians" in profile["notes"]
    assert "pulse" in profile["notes"].lower()


def test_gripper_range_and_nominal_pulses_are_separated():
    profile = _profile("hiwonder.armpi-ultra-gripper")
    assert profile["category"] == "end_effector"
    assert profile["end_effector"]["canonical_range_rad"] == [0.0, 2.22]
    assert profile["end_effector"]["pulse_range"] == {"min": 170, "max": 700}
    assert profile["end_effector"]["verified"] is False
    assert "183-645" in profile["verification"]["notes"]


def test_chassis_limit_is_an_intent_limit_not_a_measurement():
    profile = _profile("hiwonder.armpi-ultra-chassis")
    assert profile["category"] == "mobile_base"
    assert profile["chassis"]["drive_type"] == "mecanum"
    assert profile["chassis"]["wheel_count"] == 4
    assert profile["chassis"]["max_linear_mps"] == 0.20
    assert profile["chassis"]["verified"] is False
    assert profile["verification"]["status"] == "unverified"


def test_d435i_records_the_split_deployment_caveat():
    profile = _profile("intel.realsense-d435i")
    assert profile["sensor"]["sensor_type"] == "rgbd_camera"
    assert profile["sensor"]["interface"] == "usb"
    assert profile["sensor"]["rate_hz"] == 8.0
    notes = profile["notes"] + profile["verification"]["notes"]
    assert "aligned colour and depth" in notes
    assert profile["verification"]["status"] == "partially_verified"


def test_m10_is_planned_and_explicitly_unverified():
    profile = _profile("lslidar.m10")
    assert profile["status"] == "planned"
    assert profile["verification"]["status"] == "unverified"
    assert profile["verification"]["evidence"] == []
    assert profile["verification"]["date"] == ""
    assert profile["sensor"]["range_m"] == [0.05, 12.0]
    assert profile["sensor"]["rate_hz"] == 10.0
    assert profile["sensor"]["fov_deg"] == 360
    assert profile["sensor"]["verified"] is False


def test_piper_x_is_a_candidate_with_six_joints():
    profile = _profile("agilex.piper-x")
    assert profile["category"] == "arm"
    assert profile["status"] == "candidate"
    assert profile["verification"]["status"] == "unverified"
    assert profile["kinematics"]["dof"] == 6
    assert len(profile["kinematics"]["joints"]) == 6
    limits = {
        joint["name"]: (joint["limits"]["min_deg"], joint["limits"]["max_deg"])
        for joint in profile["kinematics"]["joints"]
    }
    assert limits["joint1"] == (-150.0, 150.0)
    assert limits["joint6"] == (-165.0, 165.0)


def test_every_reference_device_belongs_to_the_armpi_platform():
    reference_ids = {
        entry.id
        for entry in REGISTRY.devices.values()
        if entry.profile["status"] == "reference"
    }
    assert reference_ids == {
        "hiwonder.armpi-ultra",
        "hiwonder.armpi-ultra-gripper",
        "hiwonder.armpi-ultra-chassis",
        "intel.realsense-d435i",
    }


def test_no_payload_is_claimed_anywhere():
    for entry in REGISTRY.devices.values():
        assert "max_payload_kg" not in entry.profile
        assert "payload_kg" not in entry.profile


def test_rokae_ar5_records_verified_model_and_vendor_public_facts():
    profile = _profile("rokae.ar5")
    assert profile["status"] == "planned"
    assert profile["data_status"] == "partial"
    assert profile["verification"]["status"] == "unverified"
    assert profile["verification"]["evidence"] == [
        "https://www.rokae.com/en/product/show/595/"
    ]
    assert profile["vendor"]["product"] == "AR5"
    assert profile["vendor"]["url"] == "https://www.rokae.com/en/product/show/595/"
    assert profile["kinematics"]["dof"] == 7
    assert [joint["name"] for joint in profile["kinematics"]["joints"]] == [
        "axis1", "axis2", "axis3", "axis4", "axis5", "axis6", "axis7"
    ]
    assert profile["kinematics"]["workspace"]["verified"] is False
    assert profile["capabilities"] == ["arm.position_control"]
    assert "seven-axis" in profile["description"].lower()
    assert "EtherCAT" in profile["hardware"]["interfaces"][0]


def test_rokae_ar5_left_and_right_are_separate_missing_variants():
    left = _profile("rokae.ar5l")
    right = _profile("rokae.ar5r")
    for profile, product in ((left, "AR5L"), (right, "AR5R")):
        assert profile["status"] == "planned"
        assert profile["data_status"] == "missing"
        assert profile["vendor"]["product"] == product
        assert "kinematics" not in profile
        assert profile["capabilities"] == ["arm.position_control"]
        assert profile["verification"]["status"] == "unverified"
        assert "docs.rokae.com" in profile["vendor"]["url"]
