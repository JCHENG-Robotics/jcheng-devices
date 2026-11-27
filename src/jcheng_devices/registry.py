"""Registry loading, cross-reference validation and deterministic digesting.

The registry is an explicit index of device and capability profiles. Loading
is offline: it reads YAML files inside the repository and validates them
against the bundled schemas. It never imports a robot stack or opens a device.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import Issue, LoadError
from .loading import canonical_json, load_yaml
from .validation import CAPABILITY_SCHEMA, DEVICE_SCHEMA, schema_issues

CATEGORIES = ("arm", "mobile_base", "end_effector", "sensor", "teleop_device")
DEVICE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.[a-z0-9][a-z0-9-]*$")
CAPABILITY_ID_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


@dataclass(frozen=True)
class DeviceEntry:
    id: str
    path: Path
    profile: dict[str, Any]


@dataclass(frozen=True)
class CapabilityEntry:
    id: str
    path: Path
    profile: dict[str, Any]


@dataclass
class Registry:
    """A validated view of ``registry/registry.yaml`` and its profiles."""

    root: Path
    devices: dict[str, DeviceEntry]
    capabilities: dict[str, CapabilityEntry]
    issues: list[Issue] = field(default_factory=list)

    @classmethod
    def load(cls, root: str | Path | None = None) -> "Registry":
        base = Path(root).resolve() if root is not None else find_root(Path.cwd())
        issues: list[Issue] = []

        index = load_yaml(base / "registry" / "registry.yaml")
        if index.get("schema_version") != 1:
            issues.append(
                Issue(
                    "index",
                    "registry.yaml schema_version must be 1",
                    "registry/registry.yaml",
                )
            )

        capability_entries: dict[str, CapabilityEntry] = {}
        seen_capability_ids: set[str] = set()
        for raw in _as_list(index.get("capabilities"), "capabilities", issues):
            parsed = _parse_entry(raw, "capabilities", issues)
            if parsed is None:
                continue
            profile_id, rel_path = parsed
            if not CAPABILITY_ID_RE.fullmatch(profile_id):
                issues.append(
                    Issue("id", f"invalid capability id: {profile_id}", profile_id)
                )
                continue
            if profile_id in seen_capability_ids:
                issues.append(Issue("duplicate", f"duplicate capability id: {profile_id}", profile_id))
                continue
            seen_capability_ids.add(profile_id)
            path = _resolve_path(base, rel_path, profile_id, issues)
            if path is None:
                continue
            profile = _load_profile(
                path, "capability-profile", profile_id, CAPABILITY_SCHEMA, issues
            )
            if profile is None:
                continue
            capability_entries[profile_id] = CapabilityEntry(profile_id, path, profile)

        device_entries: dict[str, DeviceEntry] = {}
        seen_device_ids: set[str] = set()
        for raw in _as_list(index.get("devices"), "devices", issues):
            parsed = _parse_entry(raw, "devices", issues)
            if parsed is None:
                continue
            profile_id, rel_path = parsed
            if not DEVICE_ID_RE.fullmatch(profile_id):
                issues.append(Issue("id", f"invalid device id: {profile_id}", profile_id))
                continue
            if profile_id in seen_device_ids:
                issues.append(Issue("duplicate", f"duplicate device id: {profile_id}", profile_id))
                continue
            seen_device_ids.add(profile_id)
            if profile_id in capability_entries:
                issues.append(
                    Issue(
                        "duplicate",
                        f"id is used by both a device and a capability: {profile_id}",
                        profile_id,
                    )
                )
                continue
            path = _resolve_path(base, rel_path, profile_id, issues)
            if path is None:
                continue
            profile = _load_profile(path, "device-profile", profile_id, DEVICE_SCHEMA, issues)
            if profile is None:
                continue
            device_entries[profile_id] = DeviceEntry(profile_id, path, profile)

        registry = cls(base, device_entries, capability_entries, issues)
        registry._check_capability_requires()
        registry._check_devices()
        return registry

    # -- cross-reference checks ------------------------------------------

    def _check_capability_requires(self) -> None:
        for entry in self.capabilities.values():
            requires = entry.profile.get("requires", [])
            if not isinstance(requires, list):
                continue
            for required in requires:
                if required == entry.id:
                    self.issues.append(
                        Issue("requires", "a capability cannot require itself", entry.id)
                    )
                elif required not in self.capabilities:
                    self.issues.append(
                        Issue(
                            "requires",
                            f"unknown required capability: {required}",
                            entry.id,
                        )
                    )

    def _check_devices(self) -> None:
        for entry in self.devices.values():
            profile = entry.profile
            category = profile.get("category")
            if category not in CATEGORIES:
                continue
            capabilities = profile.get("capabilities", [])
            if not isinstance(capabilities, list):
                continue
            for capability_id in capabilities:
                capability = self.capabilities.get(capability_id)
                if capability is None:
                    self.issues.append(
                        Issue(
                            "capability",
                            f"unknown capability: {capability_id}",
                            entry.id,
                        )
                    )
                elif capability.profile.get("category") != category:
                    self.issues.append(
                        Issue(
                            "capability",
                            f"capability {capability_id} targets category "
                            f"{capability.profile.get('category')!r}, not {category!r}",
                            entry.id,
                        )
                    )
            self._check_kinematics(entry)
            self._check_profile_version(entry)

    def _check_kinematics(self, entry: DeviceEntry) -> None:
        kinematics = entry.profile.get("kinematics")
        if not isinstance(kinematics, dict):
            return
        joints = kinematics.get("joints")
        if not isinstance(joints, list):
            return
        names = [joint.get("name") for joint in joints if isinstance(joint, dict)]
        if kinematics.get("dof") != len(names):
            self.issues.append(
                Issue(
                    "kinematics",
                    f"dof {kinematics.get('dof')} does not match {len(names)} joints",
                    entry.id,
                )
            )
        if len(names) != len(set(names)):
            self.issues.append(
                Issue("kinematics", "joint names must be unique", entry.id)
            )
        for joint in joints:
            if not isinstance(joint, dict):
                continue
            limits = joint.get("limits")
            if not isinstance(limits, dict):
                continue
            low, high = limits.get("min_deg"), limits.get("max_deg")
            if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
                continue
            name = joint.get("name", "?")
            if low > high:
                self.issues.append(
                    Issue(
                        "kinematics",
                        f"joint {name}: min_deg {low} is greater than max_deg {high}",
                        entry.id,
                    )
                )
            elif joint.get("type") != "fixed" and low == high:
                self.issues.append(
                    Issue(
                        "kinematics",
                        f"joint {name}: a movable joint needs a non-zero range",
                        entry.id,
                    )
                )

    def _check_profile_version(self, entry: DeviceEntry) -> None:
        version = entry.profile.get("profile_version")
        if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
            self.issues.append(
                Issue("version", "profile_version must be MAJOR.MINOR.PATCH", entry.id)
            )

    # -- read API --------------------------------------------------------

    @property
    def ok(self) -> bool:
        return not self.issues

    def device(self, profile_id: str) -> DeviceEntry:
        try:
            return self.devices[profile_id]
        except KeyError as exc:
            raise KeyError(f"unknown device id: {profile_id}") from exc

    def capability(self, profile_id: str) -> CapabilityEntry:
        try:
            return self.capabilities[profile_id]
        except KeyError as exc:
            raise KeyError(f"unknown capability id: {profile_id}") from exc

    def device_rows(self) -> list[dict[str, str]]:
        return [
            {
                "id": entry.id,
                "category": str(entry.profile.get("category", "")),
                "status": str(entry.profile.get("status", "")),
                "verification": str(
                    entry.profile.get("verification", {}).get("status", "")
                ),
                "path": entry.path.relative_to(self.root).as_posix(),
            }
            for entry in sorted(self.devices.values(), key=lambda item: item.id)
        ]

    def capability_rows(self) -> list[dict[str, str]]:
        return [
            {
                "id": entry.id,
                "category": str(entry.profile.get("category", "")),
                "path": entry.path.relative_to(self.root).as_posix(),
            }
            for entry in sorted(self.capabilities.values(), key=lambda item: item.id)
        ]

    def digest(self) -> str:
        """sha256 over the canonical registry content, independent of file order."""

        payload = {
            "schema_version": 1,
            "devices": [
                self.devices[key].profile for key in sorted(self.devices)
            ],
            "capabilities": [
                self.capabilities[key].profile for key in sorted(self.capabilities)
            ],
        }
        return "sha256:" + hashlib.sha256(
            canonical_json(payload).encode("utf-8")
        ).hexdigest()


# -- module helpers ------------------------------------------------------


def find_root(start: Path) -> Path:
    """Walk up from ``start`` until a registry index is found."""

    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "registry" / "registry.yaml").is_file():
            return candidate
    raise LoadError(
        "no registry/registry.yaml found from "
        f"{start}; pass --root or run inside the repository"
    )


def _as_list(value: Any, name: str, issues: list[Issue]) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        issues.append(Issue("index", f"registry {name} must be a list"))
        return []
    return value


def _parse_entry(
    raw: Any, section: str, issues: list[Issue]
) -> tuple[str, str] | None:
    if not isinstance(raw, dict):
        issues.append(Issue("index", f"each {section} entry must be a mapping"))
        return None
    profile_id = raw.get("id")
    rel_path = raw.get("path")
    if not isinstance(profile_id, str) or not profile_id:
        issues.append(Issue("index", f"{section} entry has no string id"))
        return None
    if not isinstance(rel_path, str) or not rel_path:
        issues.append(Issue("index", f"{profile_id}: entry has no string path", profile_id))
        return None
    return profile_id, rel_path


def _resolve_path(
    root: Path, rel_path: str, owner: str, issues: list[Issue]
) -> Path | None:
    base = (root / "registry").resolve()
    candidate = Path(rel_path)
    if candidate.is_absolute():
        issues.append(Issue("path", "profile path must be relative to registry/", owner))
        return None
    resolved = (base / candidate).resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        issues.append(Issue("path", "profile path escapes registry/", owner))
        return None
    if not resolved.is_file():
        issues.append(Issue("path", f"missing profile file: {rel_path}", owner))
        return None
    return resolved


def _load_profile(
    path: Path,
    expected_kind: str,
    expected_id: str,
    schema_name: str,
    issues: list[Issue],
) -> dict[str, Any] | None:
    try:
        profile = load_yaml(path)
    except LoadError as exc:
        issues.append(Issue("load", str(exc), expected_id))
        return None

    if path.stem != expected_id:
        issues.append(
            Issue(
                "filename",
                f"file name {path.stem!r} must equal the registered id {expected_id!r}",
                expected_id,
            )
        )
    if profile.get("kind") != expected_kind:
        issues.append(
            Issue(
                "kind",
                f"kind must be {expected_kind!r}, got {profile.get('kind')!r}",
                expected_id,
            )
        )
    if profile.get("id") != expected_id:
        issues.append(
            Issue(
                "id",
                f"profile id {profile.get('id')!r} does not match the registry entry",
                expected_id,
            )
        )

    for issue in schema_issues(profile, schema_name):
        where = f"{expected_id}:{issue.path}" if issue.path else expected_id
        issues.append(Issue(issue.code, issue.message, where))

    _check_verification(profile, expected_id, issues)
    _check_description(profile, expected_id, issues)
    return profile


def _check_verification(
    profile: dict[str, Any], owner: str, issues: list[Issue]
) -> None:
    verification = profile.get("verification")
    if not isinstance(verification, dict):
        return
    status = verification.get("status")
    evidence = verification.get("evidence")
    date = verification.get("date")
    notes = verification.get("notes")

    if status in {"verified", "partially_verified"}:
        if not isinstance(evidence, list) or not evidence:
            issues.append(
                Issue("verification", f"{status} requires at least one evidence link", owner)
            )
        if not isinstance(date, str) or not date:
            issues.append(
                Issue("verification", f"{status} requires an evidence date", owner)
            )
    elif status == "unverified":
        if not isinstance(notes, str) or not notes.strip():
            issues.append(
                Issue(
                    "verification",
                    "an unverified profile must explain what is unknown",
                    owner,
                )
            )


def _check_description(
    profile: dict[str, Any], owner: str, issues: list[Issue]
) -> None:
    description = profile.get("description")
    if not isinstance(description, str) or not description.strip():
        issues.append(Issue("description", "description must be non-empty", owner))
