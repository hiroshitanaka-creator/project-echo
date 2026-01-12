"""
Property-based tests for Echo Mark signature system.

Tests invariants:
- canonical_json is deterministic (order-independent)
- sign → verify always succeeds with correct secret
- tamper → verify always fails
- wrong secret → verify always fails
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from po_echo.echo_mark import canonical_json, make_echo_mark, verify_mark

SECRET = "test-secret-key-for-property-tests-1234567890"
KEY_ID = "prop_test_key"


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
        signature=badge["signature"],
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
        signature=badge["signature"],
        key_store=key_store,
    ), "Tampered badge must fail verification"


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
        signature=badge["signature"],
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
        signature=badge["signature"],
        key_store=key_store,
    ), "Mismatched key_id must fail verification"
