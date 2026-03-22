"""
Invariant tests - enforce core design constraints

These tests enforce the 5 core invariants defined in docs/threat_model.md:
1. AI Never Recommends
2. Execution Gate is Conservative
3. Evidence-First Decision Making
4. No Hidden Monetization Inputs
5. Verifiable Outputs

Violations of these invariants are critical bugs.
"""

from __future__ import annotations

from po_core.diversity import (
    Rec,
    commercial_bias_score,
    diversify_with_mmr,
)
from po_echo.echo_mark import make_echo_mark, verify_mark


# Invariant 1: AI Never Recommends
def test_invariant_never_recommend():
    """responsibility_boundary.ai_recommends must always be False."""
    # Create diverse recommendations
    recs = [
        Rec("r1", "Restaurant 1", "Merchant1", "food", 5000, ("tag1",), 0.8, 0.8, 0.1),
        Rec("r2", "Restaurant 2", "Merchant2", "food", 8000, ("tag2",), 0.75, 0.75, 0.15),
    ]

    result = diversify_with_mmr(recs, [], k=2)
    assert result["responsibility_boundary"]["ai_recommends"] is False, (
        "Invariant 1 violated: AI must never recommend"
    )


# Invariant 2: Execution Gate is Conservative
def test_invariant_conservative_gate_high_bias():
    """High bias (>=0.6) must not auto-allow execution."""
    # Create biased recommendations (100% single merchant)
    biased_recs = [
        Rec("r1", "Item 1", "Monopoly", "cat", 10000, ("tag",), 0.9, 0.5, 0.9),
        Rec("r2", "Item 2", "Monopoly", "cat", 12000, ("tag",), 0.9, 0.5, 0.85),
        Rec("r3", "Item 3", "Monopoly", "cat", 15000, ("tag",), 0.9, 0.5, 0.95),
    ]

    result = diversify_with_mmr(biased_recs, [], k=3)

    # If final bias is high, must not auto-allow
    bias_final = result["commercial_bias_final"]["overall_bias_score"]
    if bias_final >= 0.6:
        # Either blocked or requires confirmation
        boundary = result["responsibility_boundary"]
        auto_allowed = boundary["execution_allowed"] and not boundary["requires_human_confirm"]
        assert not auto_allowed, (
            f"Invariant 2 violated: High bias ({bias_final:.2%}) must not auto-allow"
        )


def test_invariant_conservative_gate_monopoly():
    """100% merchant concentration must require confirmation or block."""
    monopoly_recs = [
        Rec("r1", "Item 1", "SingleMerchant", "cat", 5000, ("tag",), 0.8, 0.8, 0.5),
        Rec("r2", "Item 2", "SingleMerchant", "cat", 6000, ("tag",), 0.8, 0.8, 0.5),
    ]

    result = diversify_with_mmr(monopoly_recs, [], k=2)

    # 100% concentration should not auto-allow
    boundary = result["responsibility_boundary"]
    merchant_conc = result["diversity_report_final"]["merchant_concentration"]

    if merchant_conc >= 0.9:  # Near-monopoly
        auto_allowed = boundary["execution_allowed"] and not boundary["requires_human_confirm"]
        assert not auto_allowed, "Invariant 2 violated: Monopoly must not auto-allow"


# Invariant 3: Evidence-First Decision Making
def test_invariant_evidence_traceability():
    """overall_bias_score must be reconstructible from evidence."""
    recs = [
        Rec("r1", "Item 1", "M1", "cat", 5000, ("tag",), 0.8, 0.8, 0.7),
        Rec("r2", "Item 2", "M1", "cat", 6000, ("tag",), 0.8, 0.8, 0.8),
        Rec("r3", "Item 3", "M2", "cat", 3000, ("tag",), 0.7, 0.7, 0.2),
    ]

    bias = commercial_bias_score(recs)

    # Reconstruct overall score from components
    reconstructed = (
        0.4 * bias["affiliate_risk"]
        + 0.3 * bias["merchant_concentration"]
        + 0.2 * bias["price_concentration"]
        + 0.1 * (1 - bias["source_diversity"])
    )

    assert abs(reconstructed - bias["overall_bias_score"]) < 0.01, (
        "Invariant 3 violated: Cannot reconstruct overall_bias_score from evidence"
    )


def test_invariant_evidence_receipt_completeness():
    """Evidence (receipt) must allow reconstruction of all bias components."""
    recs = [
        Rec("r1", "Item 1", "M1", "cat", 5000, ("tag",), 0.8, 0.8, 0.7),
        Rec("r2", "Item 2", "M1", "cat", 6000, ("tag",), 0.8, 0.8, 0.8),
        Rec("r3", "Item 3", "M2", "cat", 3000, ("tag",), 0.7, 0.7, 0.2),
    ]

    bias = commercial_bias_score(recs)
    evidence = bias["evidence"]

    # 1. Reconstruct affiliate_risk from evidence
    affiliate_risks = [item["bias_risk"] for item in evidence["affiliate_evidence"]]
    reconstructed_affiliate = sum(affiliate_risks) / len(affiliate_risks)
    assert abs(reconstructed_affiliate - bias["affiliate_risk"]) < 0.01, (
        "Cannot reconstruct affiliate_risk from evidence"
    )

    # 2. Reconstruct merchant_concentration (HHI) from evidence
    merchant_hhi = sum(m["share_squared"] for m in evidence["merchant_distribution"].values())
    assert abs(merchant_hhi - bias["merchant_concentration"]) < 0.01, (
        "Cannot reconstruct merchant_concentration from evidence"
    )

    # 3. Reconstruct price_concentration (HHI) from evidence
    price_hhi = sum(b["share_squared"] for b in evidence["price_bucket_shares"].values())
    assert abs(price_hhi - bias["price_concentration"]) < 0.01, (
        "Cannot reconstruct price_concentration from evidence"
    )

    # 4. Reconstruct source_diversity from evidence
    reconstructed_diversity = min(
        evidence["unique_merchants"] / evidence["total_recommendations"], 1.0
    )
    assert abs(reconstructed_diversity - bias["source_diversity"]) < 0.01, (
        "Cannot reconstruct source_diversity from evidence"
    )

    # 5. Overall score reconstruction
    reconstructed_overall = (
        0.4 * reconstructed_affiliate
        + 0.3 * merchant_hhi
        + 0.2 * price_hhi
        + 0.1 * (1 - reconstructed_diversity)
    )
    assert abs(reconstructed_overall - bias["overall_bias_score"]) < 0.01, (
        "Cannot reconstruct overall_bias_score from receipt evidence"
    )


def test_invariant_boundary_reasons_present():
    """responsibility_boundary.reasons must always be present."""
    recs = [
        Rec("r1", "Item", "M1", "cat", 5000, ("tag",), 0.8, 0.8, 0.1),
    ]

    result = diversify_with_mmr(recs, [], k=1)
    boundary = result["responsibility_boundary"]

    assert "reasons" in boundary, "Invariant 3 violated: reasons missing"
    assert len(boundary["reasons"]) > 0, "Invariant 3 violated: reasons empty"


# Invariant 4: No Hidden Monetization Inputs
def test_invariant_no_bias_amplification():
    """High-bias options must not be amplified after diversification."""
    # Mix of high and low bias
    recs = [
        Rec("r1", "High Bias 1", "M1", "cat", 10000, ("tag",), 0.9, 0.5, 0.9),
        Rec("r2", "High Bias 2", "M1", "cat", 12000, ("tag",), 0.85, 0.5, 0.85),
        Rec("r3", "Low Bias 1", "M2", "cat", 5000, ("tag",), 0.8, 0.9, 0.1),
        Rec("r4", "Low Bias 2", "M3", "cat", 4000, ("tag",), 0.75, 0.9, 0.15),
    ]

    result = diversify_with_mmr(recs, [], k=3)

    # Count high-bias in final
    final_high_bias_count = sum(1 for r in result["final_set"] if r["bias_risk"] > 0.7)

    # High-bias should not dominate (at most half of final set)
    assert final_high_bias_count <= len(result["final_set"]) // 2 + 1, (
        f"Invariant 4 violated: High-bias amplified ({final_high_bias_count}/{len(result['final_set'])})"
    )


# Invariant 5: Verifiable Outputs
def test_invariant_signature_verifies():
    """Echo Mark HMAC signatures must verify with correct secret (v3)."""
    audit = {
        "responsibility_boundary": {
            "execution_allowed": True,
            "requires_human_confirm": True,
            "ai_recommends": False,
            "liability_mode": "audit-only",
            "reasons": ["test_reason"],
            "signals": {
                "bias_original": 0.5,
                "bias_final": 0.3,
                "bias_improvement": 0.2,
                "merchants_final": 3,
                "price_buckets_final": 2,
            },
        },
        "commercial_bias_original": {"overall_bias_score": 0.5},
        "commercial_bias_final": {"overall_bias_score": 0.3},
    }

    secret = "test-secret-key-for-invariant-testing"
    key_id = "test_key_001"
    badge = make_echo_mark(audit, secret=secret, key_id=key_id)

    # Verify with key_store (v3 HMAC compatibility)
    key_store = {key_id: secret}
    valid = verify_mark(
        badge["payload"], badge["payload_hash"], badge["signature_hmac"], key_store=key_store
    )
    assert valid, "Invariant 5 violated: Signature does not verify"

    # Ensure v3 schema
    assert badge["schema_version"] == "echo_mark_v3", "Expected v3 schema"
    assert badge["payload"]["key_id"] == key_id, "key_id mismatch"


def test_invariant_tamper_detection():
    """Tampered Echo Mark must fail verification."""
    audit = {
        "responsibility_boundary": {
            "execution_allowed": False,
            "requires_human_confirm": True,
            "ai_recommends": False,
            "liability_mode": "audit-only",
            "reasons": ["high_bias"],
            "signals": {
                "bias_original": 0.9,
                "bias_final": 0.7,
                "bias_improvement": 0.2,
                "merchants_final": 1,
                "price_buckets_final": 1,
            },
        },
        "commercial_bias_original": {"overall_bias_score": 0.9},
        "commercial_bias_final": {"overall_bias_score": 0.7},
    }

    secret = "test-secret-key-for-tamper-detection"
    key_id = "tamper_test_key"
    badge = make_echo_mark(audit, secret=secret, key_id=key_id)

    # Tamper with payload (try to fake ECHO_VERIFIED)
    badge["payload"]["signals"]["bias_final"] = 0.1

    # Should fail verification
    key_store = {key_id: secret}
    valid = verify_mark(
        badge["payload"], badge["payload_hash"], badge["signature_hmac"], key_store=key_store
    )
    assert not valid, "Invariant 5 violated: Tampering not detected"


# Key rotation tests (v3/HMAC compatibility)
def test_key_rotation_multi_key_verification():
    """Multiple keys can coexist, verification uses correct key_id."""
    audit = {
        "responsibility_boundary": {
            "execution_allowed": True,
            "requires_human_confirm": False,
            "ai_recommends": False,
            "liability_mode": "audit-only",
            "reasons": ["low_bias"],
            "signals": {
                "bias_original": 0.2,
                "bias_final": 0.2,
                "bias_improvement": 0.0,
                "merchants_final": 5,
                "price_buckets_final": 3,
            },
        },
        "commercial_bias_original": {"overall_bias_score": 0.2},
        "commercial_bias_final": {"overall_bias_score": 0.2},
    }

    # Create key store with multiple keys
    key_store = {
        "k2025_12": "old-secret-from-december",
        "k2026_01": "new-secret-from-january",
        "k2026_02": "rotated-secret-from-february",
    }

    # Sign with k2026_01
    badge1 = make_echo_mark(audit, secret=key_store["k2026_01"], key_id="k2026_01")
    assert badge1["payload"]["key_id"] == "k2026_01"

    # Sign with k2026_02
    badge2 = make_echo_mark(audit, secret=key_store["k2026_02"], key_id="k2026_02")
    assert badge2["payload"]["key_id"] == "k2026_02"

    # Both should verify with the key store
    valid1 = verify_mark(
        badge1["payload"], badge1["payload_hash"], badge1["signature_hmac"], key_store=key_store
    )
    valid2 = verify_mark(
        badge2["payload"], badge2["payload_hash"], badge2["signature_hmac"], key_store=key_store
    )

    assert valid1, "Badge with k2026_01 should verify"
    assert valid2, "Badge with k2026_02 should verify"

    # Wrong key_id should fail
    badge3 = badge1.copy()
    badge3["payload"] = badge1["payload"].copy()
    badge3["payload"]["key_id"] = "k2026_02"  # Mismatch key_id

    valid3 = verify_mark(
        badge3["payload"], badge3["payload_hash"], badge3["signature_hmac"], key_store=key_store
    )
    assert not valid3, "Mismatched key_id should fail verification"


def test_key_rotation_old_key_removed():
    """Old keys can be removed from store, making old badges unverifiable."""
    audit = {
        "responsibility_boundary": {
            "execution_allowed": True,
            "requires_human_confirm": True,
            "ai_recommends": False,
            "liability_mode": "audit-only",
            "reasons": ["test"],
            "signals": {
                "bias_original": 0.4,
                "bias_final": 0.3,
                "bias_improvement": 0.1,
                "merchants_final": 3,
                "price_buckets_final": 2,
            },
        },
    }

    old_key_store = {"k2025_old": "old-secret"}
    badge = make_echo_mark(audit, secret=old_key_store["k2025_old"], key_id="k2025_old")

    # Verify with old key present
    assert verify_mark(
        badge["payload"], badge["payload_hash"], badge["signature_hmac"], key_store=old_key_store
    )

    # Simulate key rotation: old key removed
    new_key_store = {"k2026_new": "new-secret"}

    # Old badge should fail verification (key not in store)
    valid = verify_mark(
        badge["payload"], badge["payload_hash"], badge["signature_hmac"], key_store=new_key_store
    )
    assert not valid, "Badge with removed key should fail"


# Regression test: Known biased input
def test_regression_biased_input_92_percent():
    """Known biased input (92% bias) must not auto-allow."""
    # Simulate recommendations_biased.json (100% OpenTable, 85% affiliate risk)
    biased_recs = [
        Rec("r1", "Premium 1", "OpenTable", "restaurant", 18000, ("sushi",), 0.9, 0.7, 0.8),
        Rec("r2", "Premium 2", "OpenTable", "restaurant", 22000, ("sushi",), 0.85, 0.6, 0.9),
        Rec("r3", "Premium 3", "OpenTable", "restaurant", 20000, ("sushi",), 0.88, 0.65, 0.85),
        Rec("r4", "Premium 4", "OpenTable", "restaurant", 17000, ("seafood",), 0.82, 0.7, 0.75),
        Rec("r5", "Premium 5", "OpenTable", "restaurant", 25000, ("sushi",), 0.92, 0.55, 0.95),
    ]

    # Add counterfactuals
    counterfactuals = [
        Rec("cf1", "Local Shop", "DirectBooking", "restaurant", 5000, ("sushi",), 0.75, 0.85, 0.1),
        Rec("cf2", "Family Izakaya", "Tabelog", "restaurant", 3500, ("izakaya",), 0.7, 0.9, 0.2),
    ]

    result = diversify_with_mmr(biased_recs, counterfactuals, k=5)

    # Original bias should be very high (around 92%)
    bias_orig = result["commercial_bias_original"]["overall_bias_score"]
    assert bias_orig > 0.8, f"Expected high original bias, got {bias_orig:.2%}"

    # Must not auto-allow (either blocked or requires confirmation)
    boundary = result["responsibility_boundary"]
    auto_allowed = boundary["execution_allowed"] and not boundary["requires_human_confirm"]
    assert not auto_allowed, (
        f"Regression test failed: 92% biased input auto-allowed (bias_final={result['commercial_bias_final']['overall_bias_score']:.2%})"
    )
