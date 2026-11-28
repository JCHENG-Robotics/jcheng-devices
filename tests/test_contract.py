"""Contract checks for the jcheng-devices capability manifest.

The checks mirror ``capability-manifest.v1.schema.json`` in jcheng-interfaces
without adding a contract dependency. They also pin the document set, the
version sources and the README structure required by the organization
documentation standard.
"""

from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = yaml.safe_load((ROOT / "capability.yaml").read_text(encoding="utf-8"))

TOP_LEVEL = {
    "schema_version",
    "name",
    "version",
    "contract",
    "safety",
    "hardware_access",
    "runtime",
}
CONTRACT_HASH = (
    "sha256:afca22a42f7163e0351d185d5a8577b0b51f2f3da4b92278f161a4a7d2c35b1c"
)


def _version_sources() -> dict[str, str]:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package = (ROOT / "src/jcheng_devices/version.py").read_text(encoding="utf-8")
    return {
        "VERSION": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "capability.yaml": str(MANIFEST["version"]),
        "pyproject.toml": re.search(
            r'^version = "([^"]+)"', pyproject, re.MULTILINE
        ).group(1),
        "version.py": re.search(
            r'__version__ = "([^"]+)"', package
        ).group(1),
    }


def test_top_level_fields():
    assert set(MANIFEST) == TOP_LEVEL


def test_identity_and_version():
    assert MANIFEST["schema_version"] == 1
    assert MANIFEST["name"] == "jcheng-devices"
    assert re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", MANIFEST["version"])
    versions = _version_sources()
    assert len(set(versions.values())) == 1, versions


def test_contract_hash_and_ranges():
    contract = MANIFEST["contract"]
    assert set(contract) == {"interfaces", "contract_hash", "system_api"}
    assert contract["interfaces"] == ">=0.2,<0.3"
    assert contract["system_api"] == ">=0.2,<0.4"
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", contract["contract_hash"])
    assert contract["contract_hash"] == CONTRACT_HASH


def test_safety_is_offline_and_scoped_out():
    safety = MANIFEST["safety"]
    assert set(safety) == {
        "class",
        "scopes",
        "requires_lease",
        "max_rate_hz",
        "deadman_ms",
    }
    assert safety["class"] == "offline"
    assert safety["scopes"] == []
    assert safety["requires_lease"] is True
    assert safety["max_rate_hz"] == 1
    assert safety["deadman_ms"] == 500


def test_hardware_access_is_none():
    assert MANIFEST["hardware_access"] == "none"


def test_runtime_surface_is_empty():
    runtime = MANIFEST["runtime"]
    assert set(runtime) == {"ros_domains", "publishes", "subscribes"}
    assert runtime["ros_domains"] == []
    assert runtime["publishes"] == []
    assert runtime["subscribes"] == []


def test_document_set_exists():
    for name in (
        "README.md",
        "README.zh-CN.md",
        "ROADMAP.md",
        "CHANGELOG.md",
        "ACCEPTANCE.md",
        "LICENSE-REVIEW.md",
        "VERSION",
        "SCHEMA_OWNERSHIP.md",
        "capability.yaml",
        "pyproject.toml",
        "registry/registry.yaml",
        "src/jcheng_devices/schemas/device-profile.v1.schema.json",
        "src/jcheng_devices/schemas/capability-profile.v1.schema.json",
        "docs/ARCHITECTURE.md",
        "docs/DEVICE_REGISTRY.md",
        "docs/DEVICE_ASSET_INVENTORY.md",
        "docs/PROFILE_SCHEMA.md",
        "docs/SOURCE_OF_TRUTH.md",
        "docs/ASSET_LAYOUT.md",
        "docs/INTEGRATION.md",
        "docs/SAFETY_MODEL.md",
        "docs/DEPENDENCY_REVIEW.md",
        "docs/M1_PLAN.md",
        "assets/README.md",
        "scripts/check_repo_gate.sh",
        ".github/CODEOWNERS",
        ".github/workflows/ci.yml",
        "evidence/20261127_scaffold/README.md",
    ):
        assert (ROOT / name).is_file(), f"missing {name}"


def test_every_schema_is_declared_in_schema_ownership():
    files = {
        f"src/jcheng_devices/schemas/{path.name}"
        for path in (ROOT / "src" / "jcheng_devices" / "schemas").glob("*.schema.json")
    }
    text = (ROOT / "SCHEMA_OWNERSHIP.md").read_text(encoding="utf-8")
    declared = set(
        re.findall(
            r"\| `(src/jcheng_devices/schemas/[^`]+\.schema\.json)` \|", text
        )
    )
    assert declared == files, {
        "undeclared": sorted(files - declared),
        "missing": sorted(declared - files),
    }
    for line in text.splitlines():
        if "| `src/jcheng_devices/schemas/" not in line:
            continue
        assert "`repo-local`" in line, line
        assert "none;" in line, line


def test_readme_required_sections():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for heading in (
        "## Scope and boundary",
        "## Repository layout",
        "## Requirements",
        "## Quick start",
        "## Validation status",
        "## Related repositories",
        "## License",
    ):
        assert heading in text, f"missing section {heading}"


def test_status_vocabulary():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    match = re.search(r"Status: \*\*([^*]+)\*\*", readme)
    assert match, "README status block not found"
    assert match.group(1) in {"Experimental", "Deployed", "Frozen", "Archived"}

    # No ad-hoc status synonyms in the root documents.
    for name in ("README.md", "ROADMAP.md", "ACCEPTANCE.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert not re.search(r"\b(Done|Finished|WIP|TODO|TBD)\b", text), name
