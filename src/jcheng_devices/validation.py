"""JSON Schema loading and validation against the bundled profile schemas."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .errors import Issue

SCHEMA_DIR = Path(__file__).resolve().with_name("schemas")
DEVICE_SCHEMA = "device-profile.v1.schema.json"
CAPABILITY_SCHEMA = "capability-profile.v1.schema.json"


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict[str, Any]:
    import json

    path = SCHEMA_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(load_schema(name))


def schema_issues(data: Any, schema_name: str) -> list[Issue]:
    """Return schema violations ordered by document path, never raising."""

    issues: list[Issue] = []
    for error in sorted(
        _validator(schema_name).iter_errors(data),
        key=lambda err: tuple(str(part) for part in err.absolute_path),
    ):
        path = "/".join(str(part) for part in error.absolute_path)
        issues.append(Issue("schema", error.message, path))
    return issues
