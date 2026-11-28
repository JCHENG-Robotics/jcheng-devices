"""Canonical hashing: stable content identity for profiles and snapshots."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from jcheng_devices.errors import LoadError
from jcheng_devices.hashing import (
    HASH_PREFIX,
    canonical_yaml,
    content_hash,
    content_hash_of,
    hash_text,
    is_content_hash,
    normalize_content_hash,
)

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "registry" / "devices" / "hiwonder.armpi-ultra.yaml"


def _profile() -> dict:
    return yaml.safe_load(PROFILE.read_text(encoding="utf-8"))


def test_canonical_yaml_sorts_mapping_keys():
    text = canonical_yaml({"z": 1, "a": {"y": 2, "b": 3}})
    assert text == "a:\n  b: 3\n  y: 2\nz: 1\n"


def test_canonical_yaml_is_independent_of_input_key_order():
    profile = _profile()
    reordered = {key: profile[key] for key in reversed(list(profile))}
    assert canonical_yaml(profile) == canonical_yaml(reordered)


def test_same_content_has_the_same_hash():
    first = content_hash_of(_profile())
    second = content_hash_of(copy.deepcopy(_profile()))
    assert first == second
    assert is_content_hash(first)


def test_one_value_byte_changes_the_hash():
    profile = _profile()
    changed = copy.deepcopy(profile)
    changed["notes"] = changed["notes"] + "x"
    assert content_hash_of(profile) != content_hash_of(changed)


def test_one_byte_in_the_source_file_changes_the_hash(tmp_path):
    text = PROFILE.read_text(encoding="utf-8")
    mutated = text.replace(
        "display_name: ArmPi Ultra arm", "display_name: ArmPi Ultra arn"
    )
    assert mutated != text
    changed = tmp_path / "hiwonder.armpi-ultra.yaml"
    changed.write_text(mutated, encoding="utf-8")
    assert content_hash(changed) != content_hash(PROFILE)


def test_comment_and_formatting_do_not_change_the_hash(tmp_path):
    reformatted = tmp_path / "hiwonder.armpi-ultra.yaml"
    reformatted.write_text(
        "# a comment that is not content\n\n"
        + yaml.safe_dump(_profile(), indent=4, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    assert content_hash(PROFILE) == content_hash(reformatted)


def test_content_hash_matches_the_loaded_file():
    assert content_hash(PROFILE) == content_hash_of(_profile())


def test_hash_prefix_and_length():
    digest = content_hash(PROFILE)
    assert digest.startswith(HASH_PREFIX)
    assert len(digest) == len(HASH_PREFIX) + 64
    assert hash_text("abc") == (
        "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_unicode_content_is_hash_stable():
    data = {"名称": "机械臂", "note": "naïve façade"}
    first = content_hash_of(data)
    second = content_hash_of({"note": "naïve façade", "名称": "机械臂"})
    assert first == second
    assert "机械臂" in canonical_yaml(data)


def test_normalize_content_hash_accepts_a_bare_hex_digest():
    digest = content_hash(PROFILE)
    bare = digest[len(HASH_PREFIX) :]
    assert normalize_content_hash(bare) == digest
    assert normalize_content_hash(digest.upper()) == digest
    assert normalize_content_hash("sha256:not-hex") is None
    assert normalize_content_hash("") is None


def test_yaml_anchors_are_not_part_of_the_content_hash():
    anchored = yaml.safe_load("a: &values {b: 1}\nc: *values\n")
    expanded = {"a": {"b": 1}, "c": {"b": 1}}
    assert canonical_yaml(anchored) == canonical_yaml(expanded)
    assert content_hash_of(anchored) == content_hash_of(expanded)


def test_missing_file_raises_a_load_error(tmp_path):
    with pytest.raises(LoadError):
        content_hash(tmp_path / "missing.yaml")
