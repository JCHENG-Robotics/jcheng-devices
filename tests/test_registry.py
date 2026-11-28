"""Registry loading, cross-reference validation and failure paths."""

from __future__ import annotations

import copy
from pathlib import Path

import yaml

from jcheng_devices import Registry

ROOT = Path(__file__).resolve().parents[1]


def _load_profile(relative: str) -> dict:
    return yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))


def _write_registry(
    tmp_path: Path,
    devices: list[dict],
    capabilities: list[dict],
    extra_index: dict | None = None,
) -> Path:
    registry_dir = tmp_path / "registry"
    (registry_dir / "devices").mkdir(parents=True)
    (registry_dir / "capabilities").mkdir()
    index: dict = {"schema_version": 1, "devices": [], "capabilities": []}
    for profile in devices:
        (registry_dir / "devices" / f"{profile['id']}.yaml").write_text(
            yaml.safe_dump(profile, sort_keys=False), encoding="utf-8"
        )
        index["devices"].append(
            {"id": profile["id"], "path": f"devices/{profile['id']}.yaml"}
        )
    for profile in capabilities:
        (registry_dir / "capabilities" / f"{profile['id']}.yaml").write_text(
            yaml.safe_dump(profile, sort_keys=False), encoding="utf-8"
        )
        index["capabilities"].append(
            {"id": profile["id"], "path": f"capabilities/{profile['id']}.yaml"}
        )
    if extra_index:
        for key in ("devices", "capabilities"):
            index[key].extend(extra_index.get(key, []))
        for key, value in extra_index.items():
            if key not in {"devices", "capabilities"}:
                index[key] = value
    (registry_dir / "registry.yaml").write_text(
        yaml.safe_dump(index, sort_keys=False), encoding="utf-8"
    )
    return tmp_path


def _armpi() -> dict:
    return copy.deepcopy(
        _load_profile("registry/devices/hiwonder.armpi-ultra.yaml")
    )


def _arm_position_control() -> dict:
    return copy.deepcopy(
        _load_profile("registry/capabilities/arm.position_control.yaml")
    )


def _arm_joint_feedback() -> dict:
    return copy.deepcopy(
        _load_profile("registry/capabilities/arm.joint_feedback.yaml")
    )


def test_repository_registry_is_valid():
    registry = Registry.load(ROOT)
    assert registry.ok, "\n".join(issue.render() for issue in registry.issues)
    assert len(registry.devices) == 9
    assert len(registry.capabilities) == 7


def test_ids_and_paths_are_consistent():
    registry = Registry.load(ROOT)
    for entry in registry.devices.values():
        assert entry.path.stem == entry.id
        assert entry.profile["id"] == entry.id
        assert entry.path.is_relative_to(ROOT / "registry")
    for entry in registry.capabilities.values():
        assert entry.path.stem == entry.id
        assert entry.profile["id"] == entry.id
        assert entry.path.is_relative_to(ROOT / "registry")


def test_all_five_categories_are_reserved():
    from jcheng_devices.registry import CATEGORIES

    registry = Registry.load(ROOT)
    used = {entry.profile["category"] for entry in registry.devices.values()}
    assert used <= set(CATEGORIES)
    # Four categories have reference, candidate or planned profiles; the
    # teleop_device category is reserved with no profile yet.
    assert used == {"arm", "mobile_base", "end_effector", "sensor"}
    assert "teleop_device" in CATEGORIES


def test_every_device_capability_resolves():
    registry = Registry.load(ROOT)
    for entry in registry.devices.values():
        for capability_id in entry.profile["capabilities"]:
            capability = registry.capabilities[capability_id]
            assert capability.profile["category"] == entry.profile["category"]


def test_digest_is_deterministic_and_order_independent():
    first = Registry.load(ROOT)
    second = Registry.load(ROOT)
    assert first.digest() == second.digest()
    assert first.digest().startswith("sha256:")
    assert len(first.digest()) == len("sha256:") + 64


def test_duplicate_device_id_is_rejected(tmp_path):
    profile = _armpi()
    root = _write_registry(
        tmp_path,
        [profile],
        [_arm_position_control(), _arm_joint_feedback()],
        extra_index={
            "devices": [
                {
                    "id": profile["id"],
                    "path": f"devices/{profile['id']}.yaml",
                }
            ]
        },
    )
    registry = Registry.load(root)
    assert any(issue.code == "duplicate" for issue in registry.issues)


def test_path_escape_is_rejected(tmp_path):
    profile = _armpi()
    root = _write_registry(
        tmp_path,
        [profile],
        [_arm_position_control(), _arm_joint_feedback()],
    )
    (tmp_path / "outside.yaml").write_text(
        yaml.safe_dump(profile, sort_keys=False), encoding="utf-8"
    )
    index = yaml.safe_load(
        (tmp_path / "registry/registry.yaml").read_text(encoding="utf-8")
    )
    index["devices"][0]["path"] = "../outside.yaml"
    (tmp_path / "registry/registry.yaml").write_text(
        yaml.safe_dump(index, sort_keys=False), encoding="utf-8"
    )
    registry = Registry.load(root)
    assert any(issue.code == "path" for issue in registry.issues)


def test_unverified_profile_needs_an_explanation(tmp_path):
    profile = _armpi()
    profile["verification"] = {
        "status": "unverified",
        "evidence": [],
        "date": "",
        "notes": "",
    }
    root = _write_registry(
        tmp_path,
        [profile],
        [_arm_position_control(), _arm_joint_feedback()],
    )
    registry = Registry.load(root)
    assert any(issue.code == "verification" for issue in registry.issues)


def test_verified_profile_needs_evidence_and_date(tmp_path):
    profile = _armpi()
    profile["verification"] = {
        "status": "verified",
        "evidence": [],
        "date": "",
        "notes": "",
    }
    root = _write_registry(
        tmp_path,
        [profile],
        [_arm_position_control(), _arm_joint_feedback()],
    )
    registry = Registry.load(root)
    codes = [issue.code for issue in registry.issues]
    assert "verification" in codes


def test_capability_category_mismatch_is_rejected(tmp_path):
    profile = _armpi()
    profile["capabilities"] = ["sensor.rgb_stream"]
    root = _write_registry(
        tmp_path,
        [profile],
        [
            _arm_position_control(),
            _arm_joint_feedback(),
            _load_profile("registry/capabilities/sensor.rgb_stream.yaml"),
        ],
    )
    registry = Registry.load(root)
    assert any(
        issue.code == "capability" and "targets category" in issue.message
        for issue in registry.issues
    )


def test_missing_capability_is_rejected(tmp_path):
    profile = _armpi()
    profile["capabilities"] = ["arm.position_control", "arm.not_registered"]
    root = _write_registry(
        tmp_path,
        [profile],
        [_arm_position_control(), _arm_joint_feedback()],
    )
    registry = Registry.load(root)
    assert any(
        issue.code == "capability" and "unknown capability" in issue.message
        for issue in registry.issues
    )


def test_dof_mismatch_is_rejected(tmp_path):
    profile = _armpi()
    profile["kinematics"]["dof"] = 6
    root = _write_registry(
        tmp_path,
        [profile],
        [_arm_position_control(), _arm_joint_feedback()],
    )
    registry = Registry.load(root)
    assert any(
        issue.code == "kinematics" and "does not match" in issue.message
        for issue in registry.issues
    )


def test_unknown_required_capability_is_rejected(tmp_path):
    capability = _arm_position_control()
    capability["requires"] = ["arm.missing_feedback"]
    root = _write_registry(
        tmp_path,
        [_armpi()],
        [capability, _arm_joint_feedback()],
    )
    registry = Registry.load(root)
    assert any(
        issue.code == "requires" and "unknown required capability" in issue.message
        for issue in registry.issues
    )
