"""Property-based tests for key generation operational boundaries."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tools.generate_keypair import (
    generate_keypair,
    update_registry,
    validate_key_id,
)


@settings(max_examples=100, deadline=None)
@given(st.from_regex(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$", fullmatch=True))
def test_validate_key_id_accepts_policy_conformant_inputs(key_id: str) -> None:
    """Allowed key_id patterns must pass unchanged."""
    assert validate_key_id(key_id) == key_id


@settings(max_examples=100, deadline=None)
@given(st.text(min_size=1, max_size=80))
def test_validate_key_id_rejects_non_conformant_inputs(candidate: str) -> None:
    """Out-of-policy key_id formats must be rejected."""
    allowed = len(candidate) <= 64 and candidate[0].isalnum() and all(
        ch.isalnum() or ch in "._-" for ch in candidate
    )
    if allowed:
        return

    with pytest.raises(ValueError):
        validate_key_id(candidate)


def test_update_registry_requires_explicit_force_for_duplicate_key(tmp_path: Path) -> None:
    """Duplicate key_id replacement must require explicit operator intent."""
    first = generate_keypair("v1")
    update_registry(first, tmp_path)

    second = generate_keypair("v1")
    with pytest.raises(ValueError, match="Use --force"):
        update_registry(second, tmp_path)


def test_update_registry_overwrites_with_force(tmp_path: Path) -> None:
    """Force overwrite keeps single entry for deterministic verification path."""
    first = generate_keypair("v1")
    update_registry(first, tmp_path)

    second = generate_keypair("v1")
    update_registry(second, tmp_path, force=True)

    registry = json.loads((tmp_path / "registry.json").read_text(encoding="utf-8"))
    entries = [k for k in registry["keys"] if k["key_id"] == "v1"]
    assert len(entries) == 1
    assert entries[0]["public_key"] == second["public_key"]
