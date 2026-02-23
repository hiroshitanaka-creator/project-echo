from __future__ import annotations

import importlib.util
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

MODULE_PATH = Path(__file__).resolve().parent.parent / "tools" / "generate_keypair.py"
SPEC = importlib.util.spec_from_file_location("generate_keypair", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@given(
    st.text(
        alphabet=st.sampled_from(list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")),
        min_size=1,
        max_size=64,
    )
)
def test_validate_key_id_accepts_allowed_characters(valid_key_id: str) -> None:
    MODULE.validate_key_id(valid_key_id)


@given(
    st.text(
        alphabet=st.sampled_from(list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")),
        min_size=1,
        max_size=64,
    )
)
def test_generate_key_material_dual_mode_shapes(valid_key_id: str) -> None:
    material = MODULE.generate_key_material(valid_key_id, with_hmac=True)

    assert material["algorithm"] == "Ed25519"
    assert material["signature_mode"] == "ed25519+hmac"
    assert isinstance(material["private_key"], str) and len(material["private_key"]) == 64
    assert isinstance(material["public_key"], str) and len(material["public_key"]) == 64
    assert isinstance(material["hmac_secret"], str) and len(material["hmac_secret"]) == 64


@given(st.text(min_size=1, max_size=20).filter(lambda s: any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in s)))
def test_validate_key_id_rejects_unsupported_characters(invalid_key_id: str) -> None:
    try:
        MODULE.validate_key_id(invalid_key_id)
    except ValueError:
        return
    raise AssertionError("validate_key_id should reject unsupported characters")
