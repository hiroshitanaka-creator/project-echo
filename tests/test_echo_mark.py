"""Echo Mark v3 focused property tests.

Required scenarios:
- dual signature verification success
- replay attack rejection
- old key invalid after rotation
"""

from __future__ import annotations

import datetime as dt

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from nacl.encoding import HexEncoder
from nacl.signing import SigningKey

from po_echo.echo_mark import build_payload, make_echo_mark_dual, verify_echo_mark
from po_echo import echo_mark_verify

SECRET = "test-secret-for-echo-v3-rotation-123456"
KEY_A = "k2026_a"
KEY_B = "k2026_b"



def _audit() -> dict:
    return {
        "responsibility_boundary": {
            "execution_allowed": True,
            "requires_human_confirm": False,
            "liability_mode": "audit-only",
            "schema_version": "1.0",
            "reasons": ["test"],
            "signals": {
                "bias_original": 0.44,
                "bias_final": 0.12,
                "bias_improvement": 0.32,
                "merchants_final": 4,
                "price_buckets_final": 3,
            },
        },
        "semantic_evidence": {"semantic_delta": 0.11, "engine": "compute_v2"},
    }


@settings(max_examples=30, deadline=None)
@given(st.booleans())
def test_dual_signature_verification_success(_flag):
    """Dual signature badge verifies with Ed25519 as primary path when an
    explicit external trust anchor is provided."""
    key = SigningKey.generate()
    badge = make_echo_mark_dual(
        audit=_audit(),
        hmac_secret=SECRET,
        ed25519_private_key=key.encode(HexEncoder).decode(),
        key_id=KEY_A,
    )
    # Ed25519 verification requires an explicit caller-controlled trust anchor;
    # the inline badge['public_key'] must never serve as one.
    explicit_public_keys = {KEY_A: key.verify_key.encode(HexEncoder).decode()}
    result = verify_echo_mark(badge, public_keys=explicit_public_keys)
    assert result["status"] == "VERIFIED"
    assert result["verification_method"] == "Ed25519"


@settings(max_examples=30, deadline=None)
@given(st.text(min_size=6, max_size=24, alphabet="abcdef0123456789"))
def test_replay_attack_is_rejected_on_second_use(nonce):
    """Second verification of identical nonce within window is rejected."""
    key = SigningKey.generate()
    issued_at = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    payload = build_payload(_audit(), key_id=KEY_A, nonce=nonce, issued_at=issued_at)
    badge = make_echo_mark_dual(
        audit={**_audit(), "responsibility_boundary": _audit()["responsibility_boundary"]},
        hmac_secret=SECRET,
        ed25519_private_key=key.encode(HexEncoder).decode(),
        key_id=KEY_A,
    )
    badge["payload"] = payload
    from po_echo.echo_mark import canonical_json, hmac_sha256_hex, sha256_hex, sign_ed25519

    badge["payload_hash"] = sha256_hex(canonical_json(payload))
    badge["signature"] = sign_ed25519(badge["payload_hash"], key.encode(HexEncoder).decode())
    badge["signature_hmac"] = hmac_sha256_hex(SECRET, badge["payload_hash"])

    seen: set[str] = set()
    explicit_public_keys = {KEY_A: key.verify_key.encode(HexEncoder).decode()}
    first = verify_echo_mark(badge, public_keys=explicit_public_keys, nonce_cache=seen)
    second = verify_echo_mark(badge, public_keys=explicit_public_keys, nonce_cache=seen)

    assert first["status"] == "VERIFIED"
    assert second["status"] == "INVALID"
    assert second["reason"] == "replay_detected"


def test_default_verify_path_rejects_replay_without_explicit_nonce_cache():
    """Default verifier path must reject second use of the same badge nonce."""
    echo_mark_verify._DEFAULT_REPLAY_NONCE_SEEN_AT.clear()
    key = SigningKey.generate()
    badge = make_echo_mark_dual(
        audit=_audit(),
        hmac_secret=SECRET,
        ed25519_private_key=key.encode(HexEncoder).decode(),
        key_id=KEY_A,
    )
    explicit_public_keys = {KEY_A: key.verify_key.encode(HexEncoder).decode()}

    first = verify_echo_mark(badge, public_keys=explicit_public_keys)
    second = verify_echo_mark(badge, public_keys=explicit_public_keys)

    assert first["status"] == "VERIFIED"
    assert second["status"] == "INVALID"
    assert second["reason"] == "replay_detected"


@settings(max_examples=20, deadline=None)
@given(st.booleans())
def test_self_signed_badge_is_rejected_without_trusted_key_source(_flag):
    """Badges must not verify using only their embedded public key."""
    attacker_key = SigningKey.generate()
    badge = make_echo_mark_dual(
        audit=_audit(),
        hmac_secret=SECRET,
        ed25519_private_key=attacker_key.encode(HexEncoder).decode(),
        key_id=KEY_A,
    )

    # No public key trust anchor and no HMAC secret: must fail verification.
    badge_no_hmac = dict(badge)
    badge_no_hmac.pop("signature_hmac", None)
    result = verify_echo_mark(badge_no_hmac)

    assert result["status"] == "INVALID"
    assert result["reason"] == "signature_invalid"


@settings(max_examples=20, deadline=None)
@given(st.booleans())
def test_key_rotation_invalidates_old_signature_without_old_public_key(_flag):
    """After rotation, verifier with new key map rejects old-key signatures."""
    old_key = SigningKey.generate()
    new_key = SigningKey.generate()

    badge = make_echo_mark_dual(
        audit=_audit(),
        hmac_secret=SECRET,
        ed25519_private_key=old_key.encode(HexEncoder).decode(),
        key_id=KEY_A,
    )

    rotated_public_map = {KEY_B: new_key.verify_key.encode(HexEncoder).decode()}
    result = verify_echo_mark(badge, public_keys=rotated_public_map, key_store={KEY_B: SECRET})

    assert result["status"] == "INVALID"
    assert result["reason"] == "signature_invalid"


@settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.booleans())
def test_revoked_registry_key_rejects_inline_public_key(monkeypatch, tmp_path, _flag):
    """Registry revocation must win over inline public key fallback."""
    key = SigningKey.generate()
    badge = make_echo_mark_dual(
        audit=_audit(),
        hmac_secret=SECRET,
        ed25519_private_key=key.encode(HexEncoder).decode(),
        key_id="default",
    )

    keys_dir = tmp_path / ".keys"
    keys_dir.mkdir(exist_ok=True)
    registry = {
        "keys": [
            {
                "key_id": "default",
                "public_key": key.verify_key.encode(HexEncoder).decode(),
                "status": "revoked",
            }
        ]
    }
    import json

    (keys_dir / "registry.json").write_text(json.dumps(registry), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = verify_echo_mark(badge)

    assert result["status"] == "INVALID"
    assert result["reason"] == "key_revoked"
