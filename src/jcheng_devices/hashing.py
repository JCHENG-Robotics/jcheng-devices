"""Canonical hashing for device profiles and generated snapshots.

The hash is computed over a canonical YAML rendering: mapping keys are sorted,
the text is UTF-8 and no generated timestamp or file-system metadata is
included. Reordering keys, changing comments or reformatting a file therefore
does not change the hash; changing a value does.

``content_hash`` is the identity of declarative content, not of the bytes on
disk. It is stable across checkouts and machines for the same profile data.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Final

import yaml

from .loading import load_yaml

HASH_PREFIX: Final = "sha256:"
HEX_LENGTH: Final = 64

# A very large width disables incidental line folding. Explicit newlines in a
# scalar are still rendered, so the output depends only on the data.
_CANONICAL_DUMP = {
    "sort_keys": True,
    "allow_unicode": True,
    "default_flow_style": False,
    "width": 10**9,
}


class _CanonicalDumper(yaml.SafeDumper):
    """A safe dumper that never emits anchors or aliases.

    YAML anchors are a file representation detail. Two documents with the same
    expanded data must hash the same even when one uses anchors and the other
    repeats the values.
    """

    def ignore_aliases(self, data: Any) -> bool:  # noqa: ARG002 - PyYAML API
        return True


def canonical_yaml(data: Any) -> str:
    """Return deterministic YAML for ``data`` with sorted mapping keys.

    The result is UTF-8 text. It contains no generated timestamp, no comment,
    no document-start marker, anchor or alias. Data that cannot be represented
    as plain YAML raises ``yaml.YAMLError``.
    """

    return yaml.dump(data, Dumper=_CanonicalDumper, **_CANONICAL_DUMP)


def hash_text(text: str) -> str:
    """Return ``sha256:<hex>`` for UTF-8 ``text``."""

    return HASH_PREFIX + hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_hash_of(data: Any) -> str:
    """Return the ``sha256:<hex>`` content hash of a loaded YAML document."""

    return hash_text(canonical_yaml(data))


def content_hash(path: str | Path) -> str:
    """Return the content hash of the YAML file at ``path``.

    Reading failures and invalid YAML raise :class:`jcheng_devices.errors.LoadError`.
    """

    return content_hash_of(load_yaml(Path(path)))


def is_content_hash(value: Any) -> bool:
    """True when ``value`` is a ``sha256:`` digest with 64 lower-case hex digits."""

    if not isinstance(value, str):
        return False
    if not value.startswith(HASH_PREFIX):
        return False
    digest = value[len(HASH_PREFIX) :]
    return len(digest) == HEX_LENGTH and all(
        character in "0123456789abcdef" for character in digest
    )


def normalize_content_hash(value: Any) -> str | None:
    """Return a canonical ``sha256:`` digest, accepting a bare hex digest.

    Anything that is not a SHA-256 digest returns ``None``. The compatibility
    checker treats that as a malformed pin rather than guessing.
    """

    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if candidate.startswith(HASH_PREFIX):
        candidate = candidate[len(HASH_PREFIX) :]
    elif candidate.startswith("SHA256:"):
        candidate = candidate[len("SHA256:") :]
    candidate = candidate.lower()
    if len(candidate) != HEX_LENGTH:
        return None
    if any(character not in "0123456789abcdef" for character in candidate):
        return None
    return HASH_PREFIX + candidate
