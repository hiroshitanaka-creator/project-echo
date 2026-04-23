from __future__ import annotations

import pytest

from po_echo.echo_mark import (
    EchoMarkSigningError,
    generate_echo_mark,
    make_echo_mark,
    make_echo_mark_dual,
    verify_echo_mark,
)


def _audit() -> dict:
    return {
        "responsibility_boundary": {
            "execution_allowed": True,
            "requires_human_confirm": False,
            "liability_mode": "audit-only",
            "reasons": ["contract_test"],
            "signals": {
                "bias_original": 0.4,
                "bias_final": 0.2,
                "bias_improvement": 0.2,
                "merchants_final": 3,
                "price_buckets_final": 2,
            },
        }
    }


def test_make_echo_mark_fails_closed_without_signing_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ECHO_MARK_SECRET", "")
    monkeypatch.setenv("ECHO_MARK_KEYS", "")
    monkeypatch.setenv("ECHO_MARK_ED25519_PRIVATE_KEYS", "")

    with pytest.raises(EchoMarkSigningError, match="missing_signing_keys"):
        make_echo_mark(_audit(), key_id="no_keys")


def test_generate_echo_mark_requires_signing_material() -> None:
    with pytest.raises(EchoMarkSigningError, match="missing_signing_keys"):
        generate_echo_mark(_audit(), secret=None)


def test_generate_echo_mark_no_longer_exposes_unsigned_badge() -> None:
    badge = generate_echo_mark(_audit(), secret="contract-secret-123456")
    assert badge["verification_method"] in {"HMAC", "Ed25519", "Ed25519+HMAC"}
    assert badge["verification_method"] != "UNSIGNED"
    assert "error" not in badge


def test_dual_signature_main_path_still_verifies() -> None:
    try:
        from nacl.encoding import HexEncoder
        from nacl.signing import SigningKey
    except ImportError:
        pytest.skip("PyNaCl not installed")

    secret = "contract-secret-123456"
    key_id = "contract_dual"
    signing_key = SigningKey.generate()
    private_key = signing_key.encode(HexEncoder).decode()
    public_key = signing_key.verify_key.encode(HexEncoder).decode()

    badge = make_echo_mark_dual(
        audit=_audit(),
        hmac_secret=secret,
        ed25519_private_key=private_key,
        key_id=key_id,
    )
    result = verify_echo_mark(badge, public_keys={key_id: public_key})
    assert result["status"] == "VERIFIED"
    assert result["verification_method"] == "Ed25519"
