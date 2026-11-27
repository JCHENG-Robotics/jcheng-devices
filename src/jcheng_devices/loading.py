"""File loading and canonical serialisation.

Profiles are YAML on disk but are treated as data. Canonical JSON is used for
digests and machine-readable output so the same registry always produces the
same bytes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .errors import LoadError


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping, raising LoadError with the file path on failure."""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LoadError(f"cannot read {path}: {exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise LoadError(f"invalid YAML in {path}: {exc}") from exc
    if data is None:
        raise LoadError(f"{path} is empty")
    if not isinstance(data, dict):
        raise LoadError(f"{path} must contain a mapping")
    return data


def canonical_json(data: Any) -> str:
    """Deterministic JSON: sorted keys, no incidental whitespace, UTF-8 text."""

    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
