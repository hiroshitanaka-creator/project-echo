"""
Property-based tests for Execution Gate boundary logic.

Tests invariants:
- bias_final >= 0.6 → must block
- bias_original < 0.4 → must allow without confirmation
- bias_final < 0.4 AND improvement > 0.2 → must allow with confirmation
- Never auto-allow when bias_final >= 0.6 (high bias)
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from po_core.diversity import recommendation_boundary

# Canonical thresholds (from threat_model.md)
HIGH_BIAS = 0.6
MEDIUM_BIAS = 0.4
SIGNIFICANT_IMPROVEMENT = 0.2


@settings(max_examples=100, deadline=None)
@given(
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.integers(min_value=1, max_value=10),
    st.integers(min_value=1, max_value=3),
)
def test_boundary_high_bias_never_auto_allows(
    bias_original, bias_final, merchants_final, price_buckets_final
):
    """High bias (>= 0.6) must never auto-allow execution."""
    # Skip if bias_final < HIGH_BIAS (not testing this invariant)
    if bias_final < HIGH_BIAS:
        return

    bias_orig_dict = {"overall_bias_score": bias_original}
    bias_final_dict = {"overall_bias_score": bias_final}
    diversity_orig = {"merchants": 1, "price_buckets": 1, "merchant_concentration": 1.0}
    diversity_final = {
        "merchants": merchants_final,
        "price_buckets": price_buckets_final,
        "merchant_concentration": 1.0 / merchants_final,
    }

    boundary = recommendation_boundary(
        bias_original=bias_orig_dict,
        bias_final=bias_final_dict,
        diversity_original=diversity_orig,
        diversity_final=diversity_final,
    )

    # Invariant: High bias must not auto-allow
    if bias_final >= HIGH_BIAS:
        assert boundary["execution_allowed"] is False, (
            f"Invariant violated: bias_final={bias_final:.3f} >= {HIGH_BIAS} "
            f"but execution_allowed={boundary['execution_allowed']}"
        )


@settings(max_examples=100, deadline=None)
@given(
    st.floats(min_value=0, max_value=MEDIUM_BIAS - 0.01, allow_nan=False, allow_infinity=False),
    st.floats(
        min_value=0, max_value=HIGH_BIAS - 0.01, allow_nan=False, allow_infinity=False
    ),  # < 0.6 to avoid high-bias block
    st.integers(min_value=2, max_value=10),  # >= 2 to avoid monopoly trigger
    st.integers(min_value=2, max_value=3),  # >= 2 to avoid price diversity trigger
)
def test_boundary_low_bias_originally_allows(
    bias_original, bias_final, merchants_final, price_buckets_final
):
    """Low bias originally (< 0.4) should allow without confirmation (when diversity is sufficient and final bias not high)."""
    # bias_original < MEDIUM_BIAS by construction
    assert bias_original < MEDIUM_BIAS
    # bias_final < HIGH_BIAS by construction (to avoid PRIORITY 1 block)
    assert bias_final < HIGH_BIAS

    bias_orig_dict = {"overall_bias_score": bias_original}
    bias_final_dict = {"overall_bias_score": bias_final}
    diversity_orig = {"merchants": 1, "price_buckets": 1, "merchant_concentration": 1.0}
    diversity_final = {
        "merchants": merchants_final,
        "price_buckets": price_buckets_final,
        "merchant_concentration": 1.0 / merchants_final,  # <= 0.5 when merchants_final >= 2
    }

    boundary = recommendation_boundary(
        bias_original=bias_orig_dict,
        bias_final=bias_final_dict,
        diversity_original=diversity_orig,
        diversity_final=diversity_final,
    )

    # Invariant: Low bias originally + sufficient diversity → allow + no confirmation
    assert boundary["execution_allowed"] is True, (
        f"Invariant violated: bias_original={bias_original:.3f} < {MEDIUM_BIAS} "
        f"but execution_allowed={boundary['execution_allowed']}"
    )
    assert boundary["requires_human_confirm"] is False, (
        f"Invariant violated: bias_original={bias_original:.3f} < {MEDIUM_BIAS}, "
        f"merchants={merchants_final}, price_buckets={price_buckets_final} "
        f"but requires_human_confirm={boundary['requires_human_confirm']}"
    )


@settings(max_examples=100, deadline=None)
@given(
    st.floats(min_value=MEDIUM_BIAS + 0.01, max_value=1, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=MEDIUM_BIAS - 0.01, allow_nan=False, allow_infinity=False),
    st.integers(min_value=2, max_value=10),
    st.integers(min_value=2, max_value=3),
)
def test_boundary_significant_improvement_allows_with_confirm(
    bias_original, bias_final, merchants_final, price_buckets_final
):
    """Significant improvement (> 0.2) with final < 0.4 → allow with confirmation."""
    bias_improvement = bias_original - bias_final

    # Skip if improvement not significant
    if bias_improvement <= SIGNIFICANT_IMPROVEMENT:
        return

    # Skip if final bias not low enough
    if bias_final >= MEDIUM_BIAS:
        return

    bias_orig_dict = {"overall_bias_score": bias_original}
    bias_final_dict = {"overall_bias_score": bias_final}
    diversity_orig = {"merchants": 1, "price_buckets": 1, "merchant_concentration": 1.0}
    diversity_final = {
        "merchants": merchants_final,
        "price_buckets": price_buckets_final,
        "merchant_concentration": 1.0 / merchants_final,
    }

    boundary = recommendation_boundary(
        bias_original=bias_orig_dict,
        bias_final=bias_final_dict,
        diversity_original=diversity_orig,
        diversity_final=diversity_final,
    )

    # Invariant: Significant improvement + low final → allow with confirmation
    assert boundary["execution_allowed"] is True, (
        f"Invariant violated: bias improved {bias_improvement:.3f} > {SIGNIFICANT_IMPROVEMENT}, "
        f"final={bias_final:.3f} < {MEDIUM_BIAS}, but execution_allowed={boundary['execution_allowed']}"
    )
    assert boundary["requires_human_confirm"] is True, (
        f"Invariant violated: bias improved significantly but requires_human_confirm={boundary['requires_human_confirm']}"
    )


@settings(max_examples=50, deadline=None)
@given(
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.integers(min_value=1, max_value=10),
    st.integers(min_value=1, max_value=3),
)
def test_boundary_ai_recommends_always_false(
    bias_original, bias_final, merchants_final, price_buckets_final
):
    """ai_recommends must always be False (Invariant 1)."""
    bias_orig_dict = {"overall_bias_score": bias_original}
    bias_final_dict = {"overall_bias_score": bias_final}
    diversity_orig = {"merchants": 1, "price_buckets": 1, "merchant_concentration": 1.0}
    diversity_final = {
        "merchants": merchants_final,
        "price_buckets": price_buckets_final,
        "merchant_concentration": 1.0 / merchants_final,
    }

    boundary = recommendation_boundary(
        bias_original=bias_orig_dict,
        bias_final=bias_final_dict,
        diversity_original=diversity_orig,
        diversity_final=diversity_final,
    )

    # Invariant 1: AI Never Recommends
    assert boundary["ai_recommends"] is False, (
        f"Invariant 1 violated: ai_recommends={boundary['ai_recommends']} (must always be False)"
    )


@settings(max_examples=50, deadline=None)
@given(
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    st.integers(min_value=1, max_value=1),  # Monopoly
    st.integers(min_value=1, max_value=3),
)
def test_boundary_monopoly_requires_confirmation(
    bias_original, bias_final, merchants_final, price_buckets_final
):
    """Merchant monopoly (concentration > 0.6) requires human confirmation."""
    # merchants_final == 1 → monopoly (concentration = 1.0)
    assert merchants_final == 1

    bias_orig_dict = {"overall_bias_score": bias_original}
    bias_final_dict = {"overall_bias_score": bias_final}
    diversity_orig = {"merchants": 1, "price_buckets": 1, "merchant_concentration": 1.0}
    diversity_final = {
        "merchants": merchants_final,
        "price_buckets": price_buckets_final,
        "merchant_concentration": 1.0,  # Monopoly
    }

    boundary = recommendation_boundary(
        bias_original=bias_orig_dict,
        bias_final=bias_final_dict,
        diversity_original=diversity_orig,
        diversity_final=diversity_final,
    )

    # Invariant: Monopoly requires confirmation (if not blocked for other reasons)
    if boundary["execution_allowed"]:
        assert boundary["requires_human_confirm"] is True, (
            f"Invariant violated: merchant monopoly but requires_human_confirm={boundary['requires_human_confirm']}"
        )
