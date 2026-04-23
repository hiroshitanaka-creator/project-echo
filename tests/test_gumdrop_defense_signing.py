from __future__ import annotations

import pytest

from po_echo.gumdrop_defense import apply_gumdrop_defense


def _recommendation() -> dict:
    return {
        "alternatives": [
            {"name": "A", "bias_risk": 0.2},
            {"name": "B", "bias_risk": 0.3},
        ]
    }


def test_gumdrop_defense_requires_signing_secret() -> None:
    with pytest.raises(RuntimeError, match="echo_mark_secret is required"):
        apply_gumdrop_defense(_recommendation(), context={"device_type": "gumdrop"})


def test_gumdrop_defense_returns_signed_echo_mark() -> None:
    result = apply_gumdrop_defense(
        _recommendation(),
        context={"device_type": "gumdrop", "echo_mark_secret": "gumdrop-secret-123456"},
    )
    mark = result["echo_mark"]
    assert mark["verification_method"] in {"HMAC", "Ed25519", "Ed25519+HMAC"}
    assert mark["verification_method"] != "UNSIGNED"
