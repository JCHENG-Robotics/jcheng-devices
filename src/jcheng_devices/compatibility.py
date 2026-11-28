"""Capability compatibility between a requirement set and a device snapshot.

The matcher is offline and file-oriented. It never reads the registry, opens a
device or treats a missing value as acceptable. A requirement that is marked
required (the default) must be satisfied by a capability declared in the
snapshot; an optional capability that is absent produces a warning, not a pass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from .errors import Issue
from .hashing import normalize_content_hash
from .loading import load_yaml
from .snapshot import CAPABILITY_ID_RE, PARAMETER_TYPES, SNAPSHOT_SCHEMA, validate_snapshot

REQUIREMENTS_SCHEMA: Final = "jcheng.device_requirements.v1"
REPORT_SCHEMA: Final = "jcheng.device_compatibility.v1"

REQUIREMENT_FIELDS: Final = (
    "schema",
    "device",
    "device_version",
    "source_hash",
    "capabilities",
    "notes",
)
REQUIREMENT_CAPABILITY_FIELDS: Final = ("id", "required", "parameters")

SATISFIED: Final = "satisfied"
MISSING: Final = "missing"
INCOMPATIBLE: Final = "incompatible"


@dataclass(frozen=True)
class CapabilityMatch:
    """One capability requirement and its outcome."""

    id: str
    required: bool
    status: str
    parameters: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "required": self.required,
            "status": self.status,
            "parameters": list(self.parameters),
        }


@dataclass(frozen=True)
class CompatibilityReport:
    """Capability-only result.

    ``capability_satisfied`` means every required *declared capability* passed.
    It does not authorize deployment or motion. ``deployable`` is a deprecated
    alias kept for older consumers.
    """

    device: str
    device_version: str
    source_hash: str
    ok: bool
    capability_satisfied: bool
    deployable: bool
    deployment_ready: bool = False
    motion_authorized: bool = False
    errors: tuple[Issue, ...] = ()
    warnings: tuple[Issue, ...] = ()
    capabilities: tuple[CapabilityMatch, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": REPORT_SCHEMA,
            "device": self.device,
            "device_version": self.device_version,
            "source_hash": self.source_hash,
            "ok": self.ok,
            "capability_satisfied": self.capability_satisfied,
            "deployable": self.deployable,
            "deployment_ready": self.deployment_ready,
            "motion_authorized": self.motion_authorized,
            "errors": [issue.as_dict() for issue in self.errors],
            "warnings": [issue.as_dict() for issue in self.warnings],
            "capabilities": [item.as_dict() for item in self.capabilities],
        }

    def __getitem__(self, key: str) -> Any:
        """Mapping-style access for callers that consume the report as data."""

        return self.as_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.as_dict().get(key, default)


@dataclass(frozen=True)
class _Requirement:
    id: str
    required: bool
    parameters: dict[str, Any] = field(default_factory=dict)


def load_requirements(path: str | Path) -> dict[str, Any]:
    """Load a requirements YAML mapping; shape errors are reported by :func:`match`."""

    return load_yaml(Path(path))


def match(
    requirements: dict[str, Any], snapshot: dict[str, Any]
) -> CompatibilityReport:
    """Match ``requirements`` against ``snapshot``.

    The function never defaults to "deployable": the requirements must contain
    at least one required capability, and every required capability must match
    a capability declared by the snapshot with compatible declared parameters.
    An absent optional capability is a warning.
    """

    errors: list[Issue] = []
    warnings: list[Issue] = []
    errors.extend(validate_snapshot(snapshot))

    device, device_version, source_hash = _snapshot_identity(snapshot, errors)
    requirement_rows = _parse_requirements(requirements, errors)
    _check_pins(requirements, device, device_version, source_hash, errors)

    snapshot_capabilities = _snapshot_capability_map(snapshot, errors)
    matches: list[CapabilityMatch] = []

    for requirement in sorted(requirement_rows, key=lambda row: row.id):
        capability = snapshot_capabilities.get(requirement.id)
        if capability is None:
            if requirement.required:
                # Two machine-readable facts: the device does not declare the
                # capability, and the requirement was mandatory.
                errors.append(
                    Issue(
                        "UNKNOWN_CAPABILITY",
                        f"unknown capability: {requirement.id}",
                        requirement.id,
                    )
                )
                errors.append(
                    Issue(
                        "MISSING_REQUIRED_CAPABILITY",
                        f"required capability {requirement.id} is not declared by "
                        f"{device or 'the snapshot'}",
                        requirement.id,
                    )
                )
                matches.append(
                    CapabilityMatch(
                        requirement.id,
                        requirement.required,
                        MISSING,
                        tuple(sorted(requirement.parameters)),
                    )
                )
            else:
                warnings.append(
                    Issue(
                        "MISSING_OPTIONAL_CAPABILITY",
                        f"optional capability {requirement.id} is not declared by "
                        f"{device or 'the snapshot'}",
                        requirement.id,
                    )
                )
                matches.append(
                    CapabilityMatch(
                        requirement.id,
                        requirement.required,
                        MISSING,
                        tuple(sorted(requirement.parameters)),
                    )
                )
            continue

        parameter_errors = _check_parameters(requirement, capability)
        if parameter_errors:
            errors.extend(parameter_errors)
            matches.append(
                CapabilityMatch(
                    requirement.id,
                    requirement.required,
                    INCOMPATIBLE,
                    tuple(sorted(requirement.parameters)),
                )
            )
        else:
            matches.append(
                CapabilityMatch(
                    requirement.id,
                    requirement.required,
                    SATISFIED,
                    tuple(sorted(requirement.parameters)),
                )
            )

    required_matches = [item for item in matches if item.required]
    if not required_matches and not any(
        issue.code == "NO_REQUIRED_CAPABILITY" for issue in errors
    ):
        errors.append(
            Issue(
                "NO_REQUIRED_CAPABILITY",
                "requirements must declare at least one required capability",
            )
        )
    deployable = (
        not errors
        and bool(required_matches)
        and all(item.status == SATISFIED for item in required_matches)
    )
    return CompatibilityReport(
        device=device,
        device_version=device_version,
        source_hash=source_hash,
        ok=not errors,
        capability_satisfied=deployable,
        deployable=deployable,
        deployment_ready=False,
        motion_authorized=False,
        errors=tuple(errors),
        warnings=tuple(warnings),
        capabilities=tuple(matches),
    )


# -- requirements -------------------------------------------------------


def _parse_requirements(
    requirements: Any, errors: list[Issue]
) -> list[_Requirement]:
    if not isinstance(requirements, dict):
        errors.append(Issue("INVALID_REQUIREMENTS", "requirements must be a mapping"))
        return []

    unknown = sorted(set(requirements) - set(REQUIREMENT_FIELDS), key=str)
    if unknown:
        errors.append(
            Issue(
                "INVALID_REQUIREMENTS",
                "unknown requirements field(s): "
                f"{', '.join(str(item) for item in unknown)}",
            )
        )
    schema = requirements.get("schema")
    if schema is not None and schema != REQUIREMENTS_SCHEMA:
        errors.append(
            Issue(
                "INVALID_REQUIREMENTS",
                f"requirements schema must be {REQUIREMENTS_SCHEMA!r}",
                "schema",
            )
        )
    for field in ("device", "device_version"):
        if field in requirements and not isinstance(requirements[field], str):
            errors.append(
                Issue("INVALID_REQUIREMENTS", f"{field} must be a string", field)
            )
    if "source_hash" in requirements:
        digest = requirements["source_hash"]
        if not isinstance(digest, str) or normalize_content_hash(digest) is None:
            errors.append(
                Issue(
                    "INVALID_REQUIREMENTS",
                    "source_hash must be sha256:<64 hex digits>",
                    "source_hash",
                )
            )
    if "notes" in requirements and not isinstance(requirements["notes"], str):
        errors.append(Issue("INVALID_REQUIREMENTS", "notes must be a string", "notes"))

    raw_capabilities = requirements.get("capabilities")
    if not isinstance(raw_capabilities, list):
        errors.append(
            Issue(
                "INVALID_REQUIREMENTS",
                "requirements.capabilities must be a list",
                "capabilities",
            )
        )
        return []
    if not raw_capabilities:
        errors.append(
            Issue(
                "NO_REQUIRED_CAPABILITY",
                "requirements must declare at least one required capability",
                "capabilities",
            )
        )
        return []

    rows: list[_Requirement] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_capabilities):
        path = f"capabilities/{index}"
        if not isinstance(raw, dict):
            errors.append(
                Issue("INVALID_REQUIREMENTS", "capability must be a mapping", path)
            )
            continue
        unknown_fields = sorted(
            set(raw) - set(REQUIREMENT_CAPABILITY_FIELDS), key=str
        )
        if unknown_fields:
            errors.append(
                Issue(
                    "INVALID_REQUIREMENTS",
                    "unknown capability field(s): "
                    f"{', '.join(str(item) for item in unknown_fields)}",
                    path,
                )
            )
            continue
        capability_id = raw.get("id")
        if not isinstance(capability_id, str) or not CAPABILITY_ID_RE.fullmatch(
            capability_id
        ):
            errors.append(
                Issue(
                    "UNKNOWN_CAPABILITY",
                    f"unknown or invalid capability id: {capability_id!r}",
                    path,
                )
            )
            continue
        if capability_id in seen:
            errors.append(
                Issue(
                    "INVALID_REQUIREMENTS",
                    f"duplicate capability requirement: {capability_id}",
                    path,
                )
            )
            continue
        seen.add(capability_id)
        required = raw.get("required", True)
        if not isinstance(required, bool):
            errors.append(
                Issue(
                    "INVALID_REQUIREMENTS",
                    f"capability {capability_id}: required must be a boolean",
                    path,
                )
            )
            continue
        parameters = raw.get("parameters", {})
        if parameters is None:
            parameters = {}
        if not isinstance(parameters, dict):
            errors.append(
                Issue(
                    "INVALID_REQUIREMENTS",
                    f"capability {capability_id}: parameters must be a mapping",
                    path,
                )
            )
            continue
        valid_parameters: dict[str, Any] = {}
        for name, value in parameters.items():
            if not isinstance(name, str) or not name:
                errors.append(
                    Issue(
                        "INVALID_REQUIREMENTS",
                        f"capability {capability_id}: parameter names must be non-empty strings",
                        path,
                    )
                )
                continue
            valid_parameters[name] = value
        rows.append(
            _Requirement(
                id=capability_id,
                required=required,
                parameters=valid_parameters,
            )
        )
    return rows


# -- snapshot -----------------------------------------------------------


def _snapshot_identity(
    snapshot: Any, errors: list[Issue]
) -> tuple[str, str, str]:
    if not isinstance(snapshot, dict):
        errors.append(Issue("INVALID_SNAPSHOT", "snapshot must be a mapping"))
        return "", "", ""
    schema = snapshot.get("schema")
    if schema != SNAPSHOT_SCHEMA:
        errors.append(
            Issue(
                "SNAPSHOT_SCHEMA_MISMATCH",
                f"snapshot schema must be {SNAPSHOT_SCHEMA!r}",
                "schema",
            )
        )
    device = snapshot.get("source_device")
    version = snapshot.get("device_version")
    digest = snapshot.get("source_hash")
    if not isinstance(device, str) or not device:
        errors.append(
            Issue("INVALID_SNAPSHOT", "source_device must be a non-empty string")
        )
        device = ""
    if not isinstance(version, str) or not version:
        errors.append(
            Issue("INVALID_SNAPSHOT", "device_version must be a non-empty string")
        )
        version = ""
    normalized = normalize_content_hash(digest)
    if normalized is None:
        errors.append(
            Issue(
                "INVALID_SNAPSHOT",
                "source_hash must be sha256:<64 hex digits>",
                "source_hash",
            )
        )
        digest = ""
    else:
        digest = normalized
    return device, version, digest


def _snapshot_capability_map(
    snapshot: Any, errors: list[Issue]
) -> dict[str, dict[str, Any]]:
    if not isinstance(snapshot, dict):
        return {}
    raw_capabilities = snapshot.get("capabilities")
    if not isinstance(raw_capabilities, list):
        errors.append(
            Issue("INVALID_SNAPSHOT", "snapshot.capabilities must be a list")
        )
        return {}
    result: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(raw_capabilities):
        path = f"capabilities/{index}"
        if not isinstance(raw, dict):
            errors.append(Issue("INVALID_SNAPSHOT", "capability must be a mapping", path))
            continue
        capability_id = raw.get("id")
        if not isinstance(capability_id, str) or not CAPABILITY_ID_RE.fullmatch(
            capability_id
        ):
            errors.append(
                Issue("INVALID_SNAPSHOT", "capability has an invalid id", path)
            )
            continue
        if capability_id in result:
            errors.append(
                Issue(
                    "INVALID_SNAPSHOT",
                    f"duplicate capability: {capability_id}",
                    path,
                )
            )
            continue
        if not isinstance(raw.get("parameters"), list):
            errors.append(
                Issue(
                    "INVALID_SNAPSHOT",
                    f"capability {capability_id}: parameters must be a list",
                    path,
                )
            )
            continue
        result[capability_id] = raw
    return result


def _check_pins(
    requirements: Any,
    device: str,
    device_version: str,
    source_hash: str,
    errors: list[Issue],
) -> None:
    if not isinstance(requirements, dict):
        return
    pinned_device = requirements.get("device")
    if isinstance(pinned_device, str) and pinned_device != device:
        errors.append(
            Issue(
                "DEVICE_ID_MISMATCH",
                f"requirements pin {pinned_device!r}, snapshot is {device!r}",
                "device",
            )
        )
    pinned_version = requirements.get("device_version")
    if isinstance(pinned_version, str) and pinned_version != device_version:
        errors.append(
            Issue(
                "DEVICE_VERSION_MISMATCH",
                f"requirements pin version {pinned_version!r}, snapshot is "
                f"{device_version!r}",
                "device_version",
            )
        )
    pinned_hash = requirements.get("source_hash")
    if isinstance(pinned_hash, str):
        normalized = normalize_content_hash(pinned_hash)
        if normalized is not None and normalized != source_hash:
            errors.append(
                Issue(
                    "SOURCE_HASH_MISMATCH",
                    f"requirements pin {normalized}, snapshot source is {source_hash}",
                    "source_hash",
                )
            )


# -- parameters ---------------------------------------------------------


def _check_parameters(
    requirement: _Requirement, capability: dict[str, Any]
) -> list[Issue]:
    declared: dict[str, dict[str, Any]] = {}
    issues: list[Issue] = []
    for index, parameter in enumerate(capability.get("parameters", [])):
        path = f"{requirement.id}/parameters/{index}"
        if not isinstance(parameter, dict):
            issues.append(
                Issue("INVALID_SNAPSHOT", "parameter must be a mapping", path)
            )
            continue
        name = parameter.get("name")
        if not isinstance(name, str) or not name:
            issues.append(Issue("INVALID_SNAPSHOT", "parameter has no name", path))
            continue
        declared[name] = parameter

    if issues:
        return issues

    for name in sorted(requirement.parameters, key=str):
        value = requirement.parameters[name]
        parameter = declared.get(name)
        if parameter is None:
            issues.append(
                Issue(
                    "INCOMPATIBLE_PARAMETER",
                    f"capability {requirement.id} does not declare parameter {name!r}",
                    requirement.id,
                )
            )
            continue
        declared_type = parameter.get("type")
        if declared_type not in PARAMETER_TYPES:
            issues.append(
                Issue(
                    "INCOMPATIBLE_PARAMETER",
                    f"capability {requirement.id} parameter {name!r} has an "
                    f"unknown type {declared_type!r}",
                    requirement.id,
                )
            )
            continue
        if not _value_matches_type(value, declared_type):
            issues.append(
                Issue(
                    "INCOMPATIBLE_PARAMETER",
                    f"capability {requirement.id} parameter {name!r} expects "
                    f"{declared_type}, got {type(value).__name__}",
                    requirement.id,
                )
            )
    return issues


def _value_matches_type(value: Any, declared: str) -> bool:
    if declared == "bool":
        return isinstance(value, bool)
    if declared == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if declared in {"float", "duration"}:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if declared == "string":
        return isinstance(value, str)
    if declared == "list":
        return isinstance(value, list)
    return False
