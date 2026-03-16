"""
Property-based tests for Echo Mark signature system.

Tests invariants:
- canonical_json is deterministic (order-independent)
- sign → verify always succeeds with correct secret
- tamper → verify always fails
- wrong secret → verify always fails
- Ed25519: sign → verify always succeeds with correct public key
- Ed25519: tamper → verify always fails
- Timestamp: old badges are rejected (replay attack mitigation)
"""

from __future__ import annotations

import datetime as dt

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from po_echo.echo_mark import (
    build_payload,
    canonical_json,
    make_echo_mark,
    make_echo_mark_dual,
    make_echo_mark_ed25519,
    validate_timestamp,
    verify_echo_mark_dual,
    verify_echo_mark_ed25519,
    verify_mark,
)

SECRET = "test-secret-key-for-property-tests-1234567890"
KEY_ID = "prop_test_key"

# Ed25519 test keypair (generated for testing only)
# NEVER use these keys in production!
TEST_PRIVATE_KEY = "0" * 64  # 32 bytes hex-encoded
TEST_PUBLIC_KEY = "3b6a27bcceb6a42d62a3a8d02a6f0d73653215771de243a63ac048a18b59da29"

try:
    from nacl.encoding import HexEncoder
    from nacl.signing import SigningKey

    # Generate a proper test keypair
    _test_key = SigningKey.generate()
    TEST_PRIVATE_KEY = _test_key.encode(HexEncoder).decode()
    TEST_PUBLIC_KEY = _test_key.verify_key.encode(HexEncoder).decode()
    ED25519_AVAILABLE = True
except ImportError:
    ED25519_AVAILABLE = False


@settings(max_examples=100, deadline=None)
@given(
    st.dictionaries(
        st.text(min_size=1, max_size=5, alphabet="abcdefghijklmnopqrstuvwxyz_"),
        st.integers(min_value=-1000, max_value=1000) | st.booleans(),
        min_size=1,
        max_size=10,
    )
)
def test_canonical_json_deterministic(d):
    """canonical_json produces same output regardless of key order."""
    s1 = canonical_json(d)
    s2 = canonical_json(dict(reversed(list(d.items()))))
    assert s1 == s2, "canonical_json must be order-independent"


def _minimal_audit(
    execution_allowed: bool,
    requires_confirm: bool,
    bias_o: float,
    bias_f: float,
    imp: float,
) -> dict:
    """Create minimal audit structure for testing."""
    return {
        "responsibility_boundary": {
            "execution_allowed": execution_allowed,
            "requires_human_confirm": requires_confirm,
            "liability_mode": "audit-only",
            "reasons": ["prop_test"],
            "signals": {
                "bias_original": bias_o,
                "bias_final": bias_f,
                "bias_improvement": imp,
                "merchants_final": 3,
                "price_buckets_final": 2,
            },
        },
        "commercial_bias_original": {"overall_bias_score": bias_o},
        "commercial_bias_final": {"overall_bias_score": bias_f},
    }


@settings(max_examples=100, deadline=None)
@given(
    st.booleans(),
    st.booleans(),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
)
def test_mark_verify_true_then_false_on_tamper(allowed, confirm, bo, bf, imp):
    """Sign → verify succeeds; tamper → verify fails."""
    audit = _minimal_audit(allowed, confirm, bo, bf, imp)
    badge = make_echo_mark(audit, secret=SECRET, key_id=KEY_ID, run_id="prop")

    # Original badge should verify
    key_store = {KEY_ID: SECRET}
    assert verify_mark(
        payload=badge["payload"],
        payload_hash=badge["payload_hash"],
        signature=badge["signature_hmac"],
        key_store=key_store,
    ), "Original badge must verify"

    # Tamper with payload: change label (always different)
    tampered = dict(badge["payload"])
    original_label = tampered["label"]
    tampered["label"] = "ECHO_VERIFIED" if original_label != "ECHO_VERIFIED" else "ECHO_BLOCKED"

    # Tampered badge should NOT verify
    assert not verify_mark(
        payload=tampered,
        payload_hash=badge["payload_hash"],
        signature=badge["signature_hmac"],
        key_store=key_store,
    ), "Tampered badge must fail verification"


@settings(max_examples=100, deadline=None)
@given(
    st.booleans(),
    st.booleans(),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
)
def test_payload_boundary_schema_version_is_unified(allowed, confirm, bo, bf, imp):
    """Payload must always include unified responsibility boundary schema_version=1.0."""
    audit = _minimal_audit(allowed, confirm, bo, bf, imp)
    payload = build_payload(audit, run_id="prop_schema", key_id=KEY_ID)

    assert payload["policy"]["schema_version"] == "1.0"


@settings(max_examples=50, deadline=None)
@given(
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
)
def test_mark_invalid_with_wrong_secret(bo, bf):
    """Verification with wrong secret always fails."""
    audit = _minimal_audit(True, True, bo, bf, abs(bo - bf))
    badge = make_echo_mark(audit, secret=SECRET, key_id=KEY_ID, run_id="prop")

    # Wrong secret should fail
    wrong_key_store = {KEY_ID: "wrong-secret-key-definitely-wrong"}
    assert not verify_mark(
        payload=badge["payload"],
        payload_hash=badge["payload_hash"],
        signature=badge["signature_hmac"],
        key_store=wrong_key_store,
    ), "Wrong secret must fail verification"


@settings(max_examples=50, deadline=None)
@given(
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
)
def test_mark_invalid_with_wrong_key_id(bo, bf):
    """Verification with mismatched key_id always fails."""
    audit = _minimal_audit(True, True, bo, bf, abs(bo - bf))
    badge = make_echo_mark(audit, secret=SECRET, key_id=KEY_ID, run_id="prop")

    # Tamper with key_id in payload
    tampered = dict(badge["payload"])
    tampered["key_id"] = "different_key_id"

    # Should fail verification (hash mismatch)
    key_store = {KEY_ID: SECRET}
    assert not verify_mark(
        payload=tampered,
        payload_hash=badge["payload_hash"],
        signature=badge["signature_hmac"],
        key_store=key_store,
    ), "Mismatched key_id must fail verification"


# ================================================================================
# Ed25519 Property Tests
# ================================================================================


@settings(max_examples=100, deadline=None)
@given(
    st.booleans(),
    st.booleans(),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
)
def test_ed25519_verify_true_then_false_on_tamper(allowed, confirm, bo, bf, imp):
    """Ed25519: Sign → verify succeeds; tamper → verify fails."""
    if not ED25519_AVAILABLE:
        return  # Skip if PyNaCl not installed

    audit = _minimal_audit(allowed, confirm, bo, bf, imp)
    badge = make_echo_mark_ed25519(
        audit, private_key_hex=TEST_PRIVATE_KEY, key_id=KEY_ID, run_id="prop_ed25519"
    )

    # Original badge should verify — Ed25519 requires an explicit trust anchor.
    result = verify_echo_mark_ed25519(badge, public_keys={KEY_ID: TEST_PUBLIC_KEY})
    assert result["status"] == "VERIFIED", f"Original badge must verify: {result}"
    assert result["checks"]["hash_integrity"], "Hash integrity must pass"
    assert result["checks"]["signature_valid"], "Signature must be valid"

    # Tamper with payload: change label
    tampered_badge = dict(badge)
    tampered_payload = dict(badge["payload"])
    original_label = tampered_payload["label"]
    tampered_payload["label"] = (
        "ECHO_VERIFIED" if original_label != "ECHO_VERIFIED" else "ECHO_BLOCKED"
    )
    tampered_badge["payload"] = tampered_payload

    # Tampered badge should NOT verify (hash mismatch)
    result = verify_echo_mark_ed25519(tampered_badge)
    assert result["status"] == "INVALID", "Tampered badge must fail verification"
    assert not result["checks"]["hash_integrity"], "Hash integrity must fail for tampered payload"


@settings(max_examples=50, deadline=None)
@given(
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
)
def test_ed25519_invalid_with_wrong_signature(bo, bf):
    """Ed25519: Wrong signature always fails."""
    if not ED25519_AVAILABLE:
        return  # Skip if PyNaCl not installed

    audit = _minimal_audit(True, True, bo, bf, abs(bo - bf))
    badge = make_echo_mark_ed25519(
        audit, private_key_hex=TEST_PRIVATE_KEY, key_id=KEY_ID, run_id="prop_ed25519"
    )

    # Tamper with signature
    tampered_badge = dict(badge)
    # Flip first byte of signature
    sig = badge["signature"]
    tampered_sig = ("00" if sig[:2] == "ff" else "ff") + sig[2:]
    tampered_badge["signature"] = tampered_sig

    # Wrong signature should fail
    result = verify_echo_mark_ed25519(tampered_badge)
    assert result["status"] == "INVALID", "Wrong signature must fail verification"
    assert not result["checks"]["signature_valid"], "Signature validation must fail"


@settings(max_examples=50, deadline=None)
@given(
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
)
def test_ed25519_invalid_with_wrong_public_key(bo, bf):
    """Ed25519: Wrong public key always fails."""
    if not ED25519_AVAILABLE:
        return  # Skip if PyNaCl not installed

    audit = _minimal_audit(True, True, bo, bf, abs(bo - bf))
    badge = make_echo_mark_ed25519(
        audit, private_key_hex=TEST_PRIVATE_KEY, key_id=KEY_ID, run_id="prop_ed25519"
    )

    # Tamper with public key
    tampered_badge = dict(badge)
    # Use a different public key (flip first byte)
    pub = badge["public_key"]
    tampered_pub = ("00" if pub[:2] == "ff" else "ff") + pub[2:]
    tampered_badge["public_key"] = tampered_pub

    # Wrong public key should fail
    result = verify_echo_mark_ed25519(tampered_badge)
    assert result["status"] == "INVALID", "Wrong public key must fail verification"


@settings(max_examples=50, deadline=None)
@given(
    st.booleans(),
    st.booleans(),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
)
def test_dual_signature_verify_with_ed25519(allowed, confirm, bo, bf, imp):
    """Dual signature: Ed25519 verification succeeds."""
    if not ED25519_AVAILABLE:
        return  # Skip if PyNaCl not installed

    audit = _minimal_audit(allowed, confirm, bo, bf, imp)
    badge = make_echo_mark_dual(
        audit,
        hmac_secret=SECRET,
        ed25519_private_key=TEST_PRIVATE_KEY,
        key_id=KEY_ID,
        run_id="prop_dual",
    )

    # Verify with Ed25519 (preferred) — explicit trust anchor required.
    result = verify_echo_mark_dual(badge, public_keys={KEY_ID: TEST_PUBLIC_KEY})
    assert result["status"] == "VERIFIED", f"Dual badge must verify: {result}"
    assert result["verification_method"] == "Ed25519", "Should prefer Ed25519 verification"


@settings(max_examples=50, deadline=None)
@given(
    st.booleans(),
    st.booleans(),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
)
def test_dual_signature_fallback_to_hmac(allowed, confirm, bo, bf, imp):
    """Dual signature: Falls back to HMAC if Ed25519 fails."""
    if not ED25519_AVAILABLE:
        return  # Skip if PyNaCl not installed

    audit = _minimal_audit(allowed, confirm, bo, bf, imp)
    badge = make_echo_mark_dual(
        audit,
        hmac_secret=SECRET,
        ed25519_private_key=TEST_PRIVATE_KEY,
        key_id=KEY_ID,
        run_id="prop_dual",
    )

    # Tamper with Ed25519 signature (but keep HMAC valid)
    tampered_badge = dict(badge)
    tampered_badge["signature"] = "00" * 64  # Invalid Ed25519 signature

    # Should fall back to HMAC
    key_store = {KEY_ID: SECRET}
    result = verify_echo_mark_dual(tampered_badge, hmac_secret=SECRET, key_store=key_store)
    assert result["status"] == "VERIFIED", "Should fall back to HMAC verification"
    assert result["verification_method"] == "HMAC", "Should use HMAC fallback"


# ================================================================================
# Timestamp Validation Property Tests (Replay Attack Mitigation)
# ================================================================================


@settings(max_examples=100, deadline=None)
@given(st.integers(min_value=0, max_value=29))
def test_timestamp_valid_within_max_age(days_ago):
    """Timestamps within max_age are valid."""
    issued_at = (dt.datetime.now(dt.UTC) - dt.timedelta(days=days_ago)).isoformat()
    is_valid, reason = validate_timestamp(issued_at, max_age_seconds=30 * 24 * 60 * 60)
    assert is_valid, f"Timestamp {days_ago} days ago should be valid: {reason}"


@settings(max_examples=50, deadline=None)
@given(st.integers(min_value=31, max_value=365))
def test_timestamp_invalid_beyond_max_age(days_ago):
    """Timestamps beyond max_age are invalid."""
    issued_at = (dt.datetime.now(dt.UTC) - dt.timedelta(days=days_ago)).isoformat()
    is_valid, reason = validate_timestamp(issued_at, max_age_seconds=30 * 24 * 60 * 60)
    assert not is_valid, f"Timestamp {days_ago} days ago should be invalid"
    assert "expired" in reason.lower(), f"Reason should mention expiration: {reason}"


@settings(max_examples=50, deadline=None)
@given(st.integers(min_value=1, max_value=365))
def test_timestamp_invalid_in_future(days_ahead):
    """Timestamps in the future are invalid."""
    issued_at = (dt.datetime.now(dt.UTC) + dt.timedelta(days=days_ahead)).isoformat()
    is_valid, reason = validate_timestamp(issued_at, max_age_seconds=30 * 24 * 60 * 60)
    assert not is_valid, "Future timestamp should be invalid"
    assert "future" in reason.lower(), f"Reason should mention future: {reason}"


def test_timestamp_missing_is_invalid():
    """Missing timestamp is invalid."""
    is_valid, reason = validate_timestamp(None)
    assert not is_valid, "Missing timestamp should be invalid"
    assert reason == "missing_timestamp"


@settings(max_examples=50, deadline=None)
@given(st.text(min_size=1, max_size=20, alphabet="abcdef0123456789"))
def test_timestamp_malformed_is_invalid(bad_timestamp):
    """Malformed timestamps are invalid."""
    # Avoid accidentally valid ISO8601 strings
    assume(not any(c in bad_timestamp for c in "T:-+Z"))

    is_valid, reason = validate_timestamp(bad_timestamp)
    assert not is_valid, f"Malformed timestamp '{bad_timestamp}' should be invalid"
    assert "invalid_timestamp" in reason, f"Reason should mention format: {reason}"
