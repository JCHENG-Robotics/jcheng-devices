"""Deployment-shaped device snapshots generated from the registry.

A snapshot is a read-only, deterministic projection of one device profile plus
its capability declarations. It exists so a consumer (system, simulation,
learning, studio or the applications reference harness) can read a single file
and record ``source_device``, ``device_version`` and ``content_hash`` without
importing this package or contacting the device library at runtime.

The optional safety overlay follows one rule: an overlay may only tighten joint
limits or the joint-space workspace. A looser or unprovable bound is an error,
never a preference.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Final, Iterable

import yaml

from .errors import Issue
from .hashing import content_hash_of, is_content_hash
from .loading import load_yaml
from .registry import Registry
from .version import __version__

SNAPSHOT_SCHEMA: Final = "jcheng.device_snapshot.v1"
OVERLAY_SCHEMA: Final = "jcheng.device_safety_overlay.v1"
GENERATED_BY: Final = f"jcheng-devices {__version__}"

SNAPSHOT_FIELDS: Final = (
    "schema",
    "source_device",
    "device_version",
    "content_hash",
    "generated_by",
    "source_path",
    "capabilities",
    "joints",
    "safety_overlay",
    "notes",
)
OVERLAY_FIELDS: Final = ("schema", "source", "joint_limits", "workspace", "notes")
PARAMETER_TYPES: Final = ("bool", "int", "float", "string", "duration", "list")
FEEDBACK_TYPES: Final = ("bool", "int", "float", "string", "list")
CAPABILITY_ID_RE: Final = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
SEMVER_RE: Final = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")

_YAML_DUMP = {
    "sort_keys": False,
    "allow_unicode": True,
    "default_flow_style": False,
    "width": 10**9,
}


class SnapshotError(Exception):
    """A snapshot or overlay that cannot be generated or read safely."""

    def __init__(self, issues: Iterable[Issue]):
        self.issues = tuple(issues)
        super().__init__("; ".join(issue.render() for issue in self.issues))


# -- generation ---------------------------------------------------------


def build_snapshot(
    registry: Registry,
    device_id: str,
    overlay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic ``jcheng.device_snapshot.v1`` document.

    ``overlay`` is already-loaded overlay data, not a path. The caller is
    responsible for reading it with :func:`load_overlay`. A registry with any
    validation issue is refused: a snapshot is never generated from a registry
    that has not passed validation.
    """

    if not registry.ok:
        raise SnapshotError(
            [
                Issue(
                    "REGISTRY_INVALID",
                    "registry has validation issues; run 'jcheng-devices validate'",
                )
            ]
        )

    entry = registry.device(device_id)
    profile = entry.profile
    joints = _snapshot_joints(profile)
    notes = str(profile.get("notes", "")).strip()
    safety_overlay: dict[str, Any] = {
        "applied": False,
        "source": None,
        "content_hash": None,
        "stricter_wins": True,
    }

    if overlay is not None:
        joints, safety_overlay = apply_overlay(joints, overlay)
        source = str(overlay["source"]).strip()
        overlay_note = f"Safety overlay from {source} applied; stricter bounds win."
        notes = f"{notes}\n\n{overlay_note}".strip()

    if not notes:
        notes = (
            "Declarative device snapshot generated from the registry; "
            "it is not runtime authority."
        )

    return {
        "schema": SNAPSHOT_SCHEMA,
        "source_device": profile["id"],
        "device_version": profile["profile_version"],
        "content_hash": content_hash_of(profile),
        "generated_by": GENERATED_BY,
        "source_path": entry.path.relative_to(registry.root).as_posix(),
        "capabilities": _snapshot_capabilities(registry, profile),
        "joints": joints,
        "safety_overlay": safety_overlay,
        "notes": notes,
    }


def _snapshot_capabilities(
    registry: Registry, profile: dict[str, Any]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    capability_ids = profile.get("capabilities", [])
    if not isinstance(capability_ids, list):
        return rows
    for capability_id in sorted(capability_ids):
        capability = registry.capabilities[capability_id].profile
        rows.append(
            {
                "id": capability_id,
                "parameters": [
                    _parameter_row(parameter)
                    for parameter in capability.get("parameters", [])
                ],
                "feedback": [
                    _feedback_row(feedback)
                    for feedback in capability.get("feedback", [])
                ],
            }
        )
    return rows


def _parameter_row(parameter: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "name": parameter["name"],
        "type": parameter["type"],
        "required": bool(parameter["required"]),
    }
    if "unit" in parameter:
        row["unit"] = parameter["unit"]
    row["description"] = parameter.get("description", "")
    return row


def _feedback_row(feedback: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "name": feedback["name"],
        "type": feedback["type"],
    }
    if "unit" in feedback:
        row["unit"] = feedback["unit"]
    row["description"] = feedback.get("description", "")
    if "rate_hz" in feedback:
        row["rate_hz"] = feedback["rate_hz"]
    return row


def _snapshot_joints(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Return joints in profile order; that order defines the target vector."""

    kinematics = profile.get("kinematics")
    if not isinstance(kinematics, dict):
        return []
    joints = kinematics.get("joints")
    if not isinstance(joints, list):
        return []
    rows: list[dict[str, Any]] = []
    for joint in joints:
        if not isinstance(joint, dict):
            continue
        limits = joint.get("limits", {})
        rows.append(
            {
                "name": joint["name"],
                "role": joint["role"],
                "limits": {
                    "min_deg": limits["min_deg"],
                    "max_deg": limits["max_deg"],
                },
            }
        )
    return rows


# -- safety overlay -----------------------------------------------------


def load_overlay(path: str | Path) -> dict[str, Any]:
    """Load an overlay YAML mapping; validation happens in :func:`apply_overlay`."""

    return load_yaml(Path(path))


def apply_overlay(
    joints: list[dict[str, Any]], overlay: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate and apply a safety overlay, returning tightened joints.

    Only ``joint_limits`` and the joint-space ``workspace`` box are accepted.
    Every bound must lie inside the declared device bound; otherwise the overlay
    is rejected. The effective bound is the intersection of the device bound,
    the per-joint override and the workspace box.
    """

    ranges, issues = _effective_ranges(joints, overlay)
    if issues:
        raise SnapshotError(issues)

    tightened: list[dict[str, Any]] = []
    for joint, (low, high) in zip(joints, ranges):
        tightened.append(
            {
                "name": joint["name"],
                "role": joint["role"],
                "limits": {"min_deg": low, "max_deg": high},
            }
        )
    return tightened, {
        "applied": True,
        "source": str(overlay["source"]).strip(),
        "content_hash": content_hash_of(overlay),
        "stricter_wins": True,
    }


def _effective_ranges(
    joints: list[dict[str, Any]], overlay: Any
) -> tuple[list[tuple[float, float]], list[Issue]]:
    issues: list[Issue] = []
    base: list[tuple[float, float]] = []
    names: list[str] = []
    for joint in joints:
        limits = joint["limits"]
        base.append((float(limits["min_deg"]), float(limits["max_deg"])))
        names.append(str(joint["name"]))

    if not isinstance(overlay, dict):
        return base, [Issue("OVERLAY_INVALID", "overlay must be a mapping")]
    unknown = sorted(set(overlay) - set(OVERLAY_FIELDS), key=str)
    if unknown:
        issues.append(
            Issue(
                "OVERLAY_UNKNOWN_FIELD",
                f"unknown overlay field(s): {', '.join(str(item) for item in unknown)}",
            )
        )
    if overlay.get("schema") != OVERLAY_SCHEMA:
        issues.append(
            Issue(
                "OVERLAY_SCHEMA",
                f"overlay schema must be {OVERLAY_SCHEMA!r}",
            )
        )
    source = overlay.get("source")
    if not isinstance(source, str) or not source.strip():
        issues.append(
            Issue("OVERLAY_SOURCE", "overlay source must be a non-empty string")
        )
    if "notes" in overlay and not isinstance(overlay["notes"], str):
        issues.append(Issue("OVERLAY_INVALID", "overlay notes must be a string"))

    joint_limits = overlay.get("joint_limits", {})
    if joint_limits is None:
        joint_limits = {}
    if not isinstance(joint_limits, dict):
        issues.append(Issue("OVERLAY_INVALID", "joint_limits must be a mapping"))
        joint_limits = {}
    workspace = overlay.get("workspace")
    if workspace is not None and not isinstance(workspace, dict):
        issues.append(Issue("OVERLAY_INVALID", "workspace must be a mapping"))
        workspace = {}
    if workspace is not None and not base:
        issues.append(
            Issue(
                "OVERLAY_INVALID_WORKSPACE",
                "workspace requires a device with at least one declared joint",
            )
        )
        workspace = None
    if not joint_limits and workspace is None:
        issues.append(
            Issue(
                "OVERLAY_EMPTY",
                "an overlay must narrow at least one joint limit or the workspace",
            )
        )

    effective = list(base)
    by_name = {name: index for index, name in enumerate(names)}

    for joint_name in sorted(joint_limits, key=str):
        index = by_name.get(str(joint_name))
        if index is None:
            issues.append(
                Issue(
                    "OVERLAY_UNKNOWN_JOINT",
                    f"joint_limits names an unknown joint: {joint_name}",
                    str(joint_name),
                )
            )
            continue
        spec = joint_limits[joint_name]
        if not isinstance(spec, dict):
            issues.append(
                Issue(
                    "OVERLAY_INVALID_LIMIT",
                    "limits must be a mapping",
                    str(joint_name),
                )
            )
            continue
        unknown_fields = sorted(set(spec) - {"min_deg", "max_deg"}, key=str)
        if unknown_fields:
            issues.append(
                Issue(
                    "OVERLAY_INVALID_LIMIT",
                    "unknown limit field(s): "
                    f"{', '.join(str(item) for item in unknown_fields)}",
                    str(joint_name),
                )
            )
            continue
        if not spec:
            issues.append(
                Issue(
                    "OVERLAY_INVALID_LIMIT",
                    "provide min_deg and/or max_deg",
                    str(joint_name),
                )
            )
            continue
        low, high = effective[index]
        device_low, device_high = base[index]
        provided_low = _overlay_number(spec, "min_deg", issues, str(joint_name))
        provided_high = _overlay_number(spec, "max_deg", issues, str(joint_name))
        if provided_low is None and provided_high is None:
            continue
        if provided_low is not None and provided_low < device_low:
            issues.append(
                Issue(
                    "OVERLAY_LOOSENS_LIMIT",
                    f"min_deg {provided_low} is below the declared lower bound "
                    f"{device_low}",
                    str(joint_name),
                )
            )
        if provided_high is not None and provided_high > device_high:
            issues.append(
                Issue(
                    "OVERLAY_LOOSENS_LIMIT",
                    f"max_deg {provided_high} is above the declared upper bound "
                    f"{device_high}",
                    str(joint_name),
                )
            )
        if provided_low is not None:
            low = max(low, provided_low)
        if provided_high is not None:
            high = min(high, provided_high)
        if low > high:
            issues.append(
                Issue(
                    "OVERLAY_EMPTY_RANGE",
                    f"the tightened range is empty ({low} > {high})",
                    str(joint_name),
                )
            )
        effective[index] = (low, high)

    if workspace is not None:
        unknown_fields = sorted(set(workspace) - {"min_deg", "max_deg"}, key=str)
        if unknown_fields:
            issues.append(
                Issue(
                    "OVERLAY_INVALID_WORKSPACE",
                    "workspace has unknown field(s): "
                    f"{', '.join(str(item) for item in unknown_fields)}",
                )
            )
        elif not workspace:
            issues.append(
                Issue(
                    "OVERLAY_INVALID_WORKSPACE",
                    "workspace must provide min_deg and/or max_deg",
                )
            )
        else:
            mins = _workspace_values(workspace, "min_deg", len(base), issues)
            maxs = _workspace_values(workspace, "max_deg", len(base), issues)
            if mins is not None or maxs is not None:
                for index, joint_name in enumerate(names):
                    low, high = effective[index]
                    device_low, device_high = base[index]
                    if mins is not None and mins[index] < device_low:
                        issues.append(
                            Issue(
                                "OVERLAY_LOOSENS_WORKSPACE",
                                f"min_deg {mins[index]} is below the declared "
                                f"lower bound {device_low}",
                                joint_name,
                            )
                        )
                    if maxs is not None and maxs[index] > device_high:
                        issues.append(
                            Issue(
                                "OVERLAY_LOOSENS_WORKSPACE",
                                f"max_deg {maxs[index]} is above the declared "
                                f"upper bound {device_high}",
                                joint_name,
                            )
                        )
                    if mins is not None:
                        low = max(low, mins[index])
                    if maxs is not None:
                        high = min(high, maxs[index])
                    if low > high:
                        issues.append(
                            Issue(
                                "OVERLAY_EMPTY_RANGE",
                                f"the tightened workspace range is empty "
                                f"({low} > {high})",
                                joint_name,
                            )
                        )
                    effective[index] = (low, high)

    return effective, issues


def _overlay_number(
    spec: dict[str, Any], key: str, issues: list[Issue], path: str
) -> float | None:
    if key not in spec:
        return None
    value = spec[key]
    if not _is_number(value):
        issues.append(
            Issue(
                "OVERLAY_INVALID_LIMIT",
                f"{key} must be a finite number",
                path,
            )
        )
        return None
    number = float(value)
    other_key = "max_deg" if key == "min_deg" else "min_deg"
    if other_key in spec and _is_number(spec[other_key]):
        if key == "min_deg" and number > float(spec[other_key]):
            issues.append(
                Issue(
                    "OVERLAY_INVALID_LIMIT",
                    f"min_deg {number} is greater than max_deg "
                    f"{float(spec[other_key])}",
                    path,
                )
            )
    return number


def _workspace_values(
    workspace: dict[str, Any], key: str, joint_count: int, issues: list[Issue]
) -> list[float] | None:
    if key not in workspace:
        return None
    values = workspace[key]
    if not isinstance(values, list):
        issues.append(
            Issue(
                "OVERLAY_INVALID_WORKSPACE",
                f"workspace {key} must be a list with one value per joint",
            )
        )
        return None
    if len(values) != joint_count:
        issues.append(
            Issue(
                "OVERLAY_INVALID_WORKSPACE",
                f"workspace {key} has {len(values)} value(s) for "
                f"{joint_count} joint(s)",
            )
        )
        return None
    numbers: list[float] = []
    for index, value in enumerate(values):
        if not _is_number(value):
            issues.append(
                Issue(
                    "OVERLAY_INVALID_WORKSPACE",
                    f"workspace {key}[{index}] must be a finite number",
                )
            )
            return None
        numbers.append(float(value))
    return numbers


def _is_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


# -- reading and serialising -------------------------------------------


def load_snapshot(path: str | Path) -> dict[str, Any]:
    """Load and validate a ``jcheng.device_snapshot.v1`` YAML document."""

    data = load_yaml(Path(path))
    issues = validate_snapshot(data)
    if issues:
        raise SnapshotError(issues)
    return data


def validate_snapshot(data: Any) -> list[Issue]:
    """Return structural issues for a snapshot document, never raising."""

    issues: list[Issue] = []
    if not isinstance(data, dict):
        return [Issue("INVALID_SNAPSHOT", "snapshot must be a mapping")]

    unknown = sorted(set(data) - set(SNAPSHOT_FIELDS), key=str)
    if unknown:
        issues.append(
            Issue(
                "INVALID_SNAPSHOT",
                "unknown snapshot field(s): "
                f"{', '.join(str(item) for item in unknown)}",
            )
        )
    for field in SNAPSHOT_FIELDS:
        if field not in data:
            issues.append(
                Issue("INVALID_SNAPSHOT", f"missing snapshot field: {field}", field)
            )

    if data.get("schema") != SNAPSHOT_SCHEMA:
        issues.append(
            Issue(
                "SNAPSHOT_SCHEMA_MISMATCH",
                f"snapshot schema must be {SNAPSHOT_SCHEMA!r}",
                "schema",
            )
        )
    for field in ("source_device", "generated_by", "source_path"):
        _require_non_empty_string(data, field, issues)
    version = data.get("device_version")
    if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
        issues.append(
            Issue(
                "INVALID_SNAPSHOT",
                "device_version must be MAJOR.MINOR.PATCH",
                "device_version",
            )
        )
    if not is_content_hash(data.get("content_hash")):
        issues.append(
            Issue(
                "INVALID_SNAPSHOT",
                "content_hash must be sha256:<64 lower-case hex digits>",
                "content_hash",
            )
        )

    capabilities = data.get("capabilities")
    seen_capabilities: set[str] = set()
    if not isinstance(capabilities, list):
        issues.append(
            Issue("INVALID_SNAPSHOT", "capabilities must be a list", "capabilities")
        )
    else:
        for index, capability in enumerate(capabilities):
            _validate_snapshot_capability(
                capability, index, seen_capabilities, issues
            )

    joints = data.get("joints")
    seen_joints: set[str] = set()
    if not isinstance(joints, list):
        issues.append(Issue("INVALID_SNAPSHOT", "joints must be a list", "joints"))
    else:
        for index, joint in enumerate(joints):
            _validate_snapshot_joint(joint, index, seen_joints, issues)

    _validate_safety_overlay(data.get("safety_overlay"), issues)
    if not isinstance(data.get("notes"), str):
        issues.append(Issue("INVALID_SNAPSHOT", "notes must be a string", "notes"))
    return issues


def _validate_snapshot_capability(
    capability: Any,
    index: int,
    seen: set[str],
    issues: list[Issue],
) -> None:
    path = f"capabilities/{index}"
    if not isinstance(capability, dict):
        issues.append(Issue("INVALID_SNAPSHOT", "capability must be a mapping", path))
        return
    capability_id = capability.get("id")
    if not isinstance(capability_id, str) or not CAPABILITY_ID_RE.fullmatch(
        capability_id
    ):
        issues.append(
            Issue("INVALID_SNAPSHOT", "capability has an invalid id", path)
        )
    elif capability_id in seen:
        issues.append(
            Issue(
                "INVALID_SNAPSHOT",
                f"duplicate capability: {capability_id}",
                path,
            )
        )
    else:
        seen.add(capability_id)

    parameters = capability.get("parameters")
    if not isinstance(parameters, list):
        issues.append(
            Issue("INVALID_SNAPSHOT", "parameters must be a list", f"{path}/parameters")
        )
    else:
        names: set[str] = set()
        for position, parameter in enumerate(parameters):
            _validate_parameter(parameter, f"{path}/parameters/{position}", names, issues)

    feedback = capability.get("feedback")
    if not isinstance(feedback, list):
        issues.append(
            Issue("INVALID_SNAPSHOT", "feedback must be a list", f"{path}/feedback")
        )
    else:
        names = set()
        for position, item in enumerate(feedback):
            _validate_feedback(item, f"{path}/feedback/{position}", names, issues)


def _validate_parameter(
    parameter: Any, path: str, names: set[str], issues: list[Issue]
) -> None:
    if not isinstance(parameter, dict):
        issues.append(Issue("INVALID_SNAPSHOT", "parameter must be a mapping", path))
        return
    name = parameter.get("name")
    if not isinstance(name, str) or not name:
        issues.append(Issue("INVALID_SNAPSHOT", "parameter has no name", path))
    elif name in names:
        issues.append(Issue("INVALID_SNAPSHOT", f"duplicate parameter: {name}", path))
    else:
        names.add(name)
    if parameter.get("type") not in PARAMETER_TYPES:
        issues.append(
            Issue("INVALID_SNAPSHOT", f"parameter {name!r} has an invalid type", path)
        )
    if not isinstance(parameter.get("required"), bool):
        issues.append(
            Issue("INVALID_SNAPSHOT", f"parameter {name!r} needs a boolean required", path)
        )


def _validate_feedback(
    item: Any, path: str, names: set[str], issues: list[Issue]
) -> None:
    if not isinstance(item, dict):
        issues.append(Issue("INVALID_SNAPSHOT", "feedback must be a mapping", path))
        return
    name = item.get("name")
    if not isinstance(name, str) or not name:
        issues.append(Issue("INVALID_SNAPSHOT", "feedback has no name", path))
    elif name in names:
        issues.append(Issue("INVALID_SNAPSHOT", f"duplicate feedback: {name}", path))
    else:
        names.add(name)
    if item.get("type") not in FEEDBACK_TYPES:
        issues.append(
            Issue("INVALID_SNAPSHOT", f"feedback {name!r} has an invalid type", path)
        )


def _validate_snapshot_joint(
    joint: Any, index: int, seen: set[str], issues: list[Issue]
) -> None:
    path = f"joints/{index}"
    if not isinstance(joint, dict):
        issues.append(Issue("INVALID_SNAPSHOT", "joint must be a mapping", path))
        return
    name = joint.get("name")
    if not isinstance(name, str) or not name:
        issues.append(Issue("INVALID_SNAPSHOT", "joint has no name", path))
    elif name in seen:
        issues.append(Issue("INVALID_SNAPSHOT", f"duplicate joint: {name}", path))
    else:
        seen.add(name)
    if not isinstance(joint.get("role"), str) or not joint["role"]:
        issues.append(Issue("INVALID_SNAPSHOT", "joint has no role", path))
    limits = joint.get("limits")
    if not isinstance(limits, dict):
        issues.append(Issue("INVALID_SNAPSHOT", "joint limits must be a mapping", path))
        return
    low, high = limits.get("min_deg"), limits.get("max_deg")
    if not _is_number(low) or not _is_number(high):
        issues.append(
            Issue("INVALID_SNAPSHOT", "joint limits must be finite numbers", path)
        )
    elif float(low) > float(high):
        issues.append(
            Issue("INVALID_SNAPSHOT", f"joint {name!r} has min_deg > max_deg", path)
        )


def _validate_safety_overlay(overlay: Any, issues: list[Issue]) -> None:
    if not isinstance(overlay, dict):
        issues.append(
            Issue("INVALID_SNAPSHOT", "safety_overlay must be a mapping", "safety_overlay")
        )
        return
    expected = {"applied", "source", "content_hash", "stricter_wins"}
    if set(overlay) != expected:
        issues.append(
            Issue(
                "INVALID_SNAPSHOT",
                "safety_overlay must contain applied, source, content_hash and stricter_wins",
                "safety_overlay",
            )
        )
        return
    if not isinstance(overlay["applied"], bool):
        issues.append(
            Issue(
                "INVALID_SNAPSHOT",
                "safety_overlay applied must be a boolean",
                "safety_overlay",
            )
        )
    if overlay.get("stricter_wins") is not True:
        issues.append(
            Issue(
                "INVALID_SNAPSHOT",
                "safety_overlay stricter_wins must be true",
                "safety_overlay",
            )
        )
    source = overlay.get("source")
    digest = overlay.get("content_hash")
    if overlay.get("applied") is True:
        if not isinstance(source, str) or not source.strip():
            issues.append(
                Issue(
                    "INVALID_SNAPSHOT",
                    "an applied overlay needs a source",
                    "safety_overlay",
                )
            )
        if not is_content_hash(digest):
            issues.append(
                Issue(
                    "INVALID_SNAPSHOT",
                    "an applied overlay needs a content_hash",
                    "safety_overlay",
                )
            )
    elif overlay.get("applied") is False:
        if source is not None or digest is not None:
            issues.append(
                Issue(
                    "INVALID_SNAPSHOT",
                    "an unapplied overlay must have null source and content_hash",
                    "safety_overlay",
                )
            )


def _require_non_empty_string(
    data: dict[str, Any], field: str, issues: list[Issue]
) -> None:
    if field not in data:
        return
    value = data[field]
    if not isinstance(value, str) or not value.strip():
        issues.append(
            Issue("INVALID_SNAPSHOT", f"{field} must be a non-empty string", field)
        )


def dump_snapshot(snapshot: dict[str, Any], *, as_json: bool = False) -> str:
    """Serialise a snapshot deterministically with a trailing newline."""

    if as_json:
        text = json.dumps(
            snapshot, indent=2, sort_keys=True, ensure_ascii=False
        )
    else:
        text = yaml.safe_dump(snapshot, **_YAML_DUMP)
    if not text.endswith("\n"):
        text += "\n"
    return text


def write_snapshot(
    snapshot: dict[str, Any], path: str | Path, *, as_json: bool = False
) -> Path:
    """Write a snapshot file; the parent directory must already exist."""

    target = Path(path)
    target.write_text(dump_snapshot(snapshot, as_json=as_json), encoding="utf-8")
    return target
