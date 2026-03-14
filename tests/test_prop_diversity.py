"""
Property-based tests for diversity enforcement with conditional invariants.

Lexicographic objective (priority order):
1. Bias risk minimization (safety first)
2. Merchant/price diversity (anti-monopoly, within safe candidates)
3. Utility (quality)

Test categories:
- Absolute invariants: Always enforced (bias minimization)
- Conditional invariants: Enforced when clean candidates exist
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.strategies import composite

from po_core.diversity import Rec, diversify_with_mmr

# Constants for clean candidate detection (must match diversify_with_mmr)
BETA = 0.8
MIN_EFFECTIVE_UTILITY = 0.1
HIGH_BIAS_THRESHOLD = 0.7


def is_clean(r: Rec) -> bool:
    """Check if recommendation is clean (safe to select).

    Mirrors both filters in diversify_with_mmr:
    1. effective_utility >= MIN_EFFECTIVE_UTILITY
    2. bias_risk <= HIGH_BIAS_THRESHOLD (applied when enough candidates exist)
    """
    effective_utility = r.utility - BETA * r.bias_risk
    return effective_utility >= MIN_EFFECTIVE_UTILITY and r.bias_risk <= HIGH_BIAS_THRESHOLD


def is_high_bias(r: Rec) -> bool:
    """Check if recommendation has high bias risk."""
    return r.bias_risk > HIGH_BIAS_THRESHOLD


@composite
def recommendation_set(draw):
    """Generate realistic recommendation sets for testing."""
    merchants = draw(
        st.lists(st.sampled_from(["A", "B", "C", "D", "E"]), min_size=1, max_size=5, unique=True)
    )

    recs = []
    for i in range(draw(st.integers(min_value=5, max_value=15))):
        merchant = draw(st.sampled_from(merchants))
        price = draw(st.integers(min_value=500, max_value=50000))
        bias_risk = draw(st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False))
        utility = draw(st.floats(min_value=0.1, max_value=1, allow_nan=False, allow_infinity=False))

        rec = Rec(
            id=f"r{i}",
            title=f"Item {i}",
            merchant=merchant,
            category="test",
            price=float(price),
            tags=("tag1",),
            utility=utility,
            ethics=0.5,
            bias_risk=bias_risk,
        )
        recs.append(rec)

    return recs


# ============================================================================
# ABSOLUTE INVARIANTS (always enforced)
# ============================================================================


@settings(max_examples=50, deadline=None)
@given(recommendation_set())
def test_diversify_prefers_low_bias_when_enough_low_bias_exists(recs):
    """
    Absolute invariant: If clean AND low-bias candidates exist (>= k), output must be all low-bias.

    Specification:
        If (clean AND low-bias) count >= k, then all(output.bias_risk <= τ)

    This enforces bias minimization as the top priority.
    Note: "clean" means effective_utility >= 0.1 (selectable)
          "low-bias" means bias_risk <= 0.7 (preferred)
    """
    k = 5
    # Count candidates that are both clean AND low-bias
    clean_low_bias_count = sum(1 for r in recs if is_clean(r) and not is_high_bias(r))

    # Skip if not enough clean+low-bias candidates (not testing this case)
    if clean_low_bias_count < k:
        return

    result = diversify_with_mmr(recs, counterfactuals=[], k=k)
    final_recs = [Rec.from_dict(r) for r in result["final_set"]]

    # Absolute invariant: All output must be low-bias when enough low-bias exist
    high_bias_out = [r for r in final_recs if is_high_bias(r)]

    assert len(high_bias_out) == 0, (
        f"Invariant violated: {len(high_bias_out)} high-bias (>{HIGH_BIAS_THRESHOLD}) in output "
        f"despite {clean_low_bias_count} clean+low-bias candidates available (k={k}). "
        f"High-bias items: {[{'id': r.id, 'bias': r.bias_risk, 'utility': r.utility} for r in high_bias_out]}"
    )


@settings(max_examples=50, deadline=None)
@given(recommendation_set())
def test_diversify_improves_or_preserves_bias_when_clean_insufficient(recs):
    """
    Absolute invariant: Bias proportion should not increase (or increase minimally).

    Specification:
        proportion_out <= proportion_in + ε

    This ensures diversification never makes bias worse, even with contaminated input.
    """
    k = 5
    clean_count = sum(1 for r in recs if is_clean(r))

    # Only test when some clean candidates exist but are insufficient (0 < count < k).
    # When clean_count == 0 the algorithm has no clean alternatives, so proportion_out
    # can legitimately reach 100% regardless of proportion_in — skip that case.
    if clean_count == 0 or clean_count >= k:
        return

    high_bias_in = sum(1 for r in recs if is_high_bias(r))

    # Skip if no high-bias input (nothing to test)
    if high_bias_in == 0:
        return

    result = diversify_with_mmr(recs, counterfactuals=[], k=k)
    final_recs = [Rec.from_dict(r) for r in result["final_set"]]

    high_bias_out = sum(1 for r in final_recs if is_high_bias(r))

    proportion_in = high_bias_in / len(recs) if recs else 0
    proportion_out = high_bias_out / len(final_recs) if final_recs else 0

    # Allow small increase (ε=0.15) due to k-selection concentration effect
    # (selecting k=5 from larger set naturally changes proportions)
    EPSILON = 0.15

    assert proportion_out <= proportion_in + EPSILON, (
        f"Bias proportion increased beyond acceptable limit: "
        f"input={proportion_in:.2%} → output={proportion_out:.2%} "
        f"(clean_candidates={clean_count}, k={k})"
    )


@settings(max_examples=50, deadline=None)
@given(recommendation_set())
def test_diversify_never_amplifies_max_bias(recs):
    """
    Absolute invariant: Max bias in output should not exceed max bias in input.

    Specification:
        max(output.bias_risk) <= max(input.bias_risk) + ε

    This ensures worst-case bias doesn't get worse.
    """
    result = diversify_with_mmr(recs, counterfactuals=[], k=5)
    final_recs = [Rec.from_dict(r) for r in result["final_set"]]

    max_bias_in = max(r.bias_risk for r in recs) if recs else 0
    max_bias_out = max(r.bias_risk for r in final_recs) if final_recs else 0

    # Allow tiny epsilon for floating point errors
    EPSILON = 0.01

    assert max_bias_out <= max_bias_in + EPSILON, (
        f"Max bias increased: input_max={max_bias_in:.3f} → output_max={max_bias_out:.3f}"
    )


# ============================================================================
# CONDITIONAL INVARIANTS (enforced when clean candidates sufficient)
# ============================================================================


@settings(max_examples=50, deadline=None)
@given(recommendation_set())
def test_diversify_merchant_diversity_is_soft_objective_under_bias_constraints(recs):
    """
    Conditional invariant: Merchant diversity is preserved when clean candidates exist across merchants.

    Specification:
        If clean_merchants >= 2 AND each has >= 1 clean candidate,
        then output should have >= 2 merchants

    Bias minimization dominates merchant diversity when they conflict.
    """
    merchants_in = {r.merchant for r in recs}

    # Skip if input has only 1 merchant
    if len(merchants_in) < 2:
        return

    # Count clean candidates per merchant
    from collections import Counter

    clean_per_merchant = Counter()
    for r in recs:
        if is_clean(r):
            clean_per_merchant[r.merchant] += 1

    # Only enforce diversity if multiple merchants have clean candidates
    if len(clean_per_merchant) < 2:
        # Not enough clean merchants - bias removal takes priority
        return

    result = diversify_with_mmr(recs, counterfactuals=[], k=5)
    final_recs = [Rec.from_dict(r) for r in result["final_set"]]

    merchants_out = {r.merchant for r in final_recs}

    # Conditional invariant: Preserve merchant diversity when safe to do so
    assert len(merchants_out) >= 2, (
        f"Merchant diversity lost despite clean candidates across multiple merchants: "
        f"input had {len(merchants_in)} merchants, output has {len(merchants_out)}, "
        f"clean_per_merchant={dict(clean_per_merchant)}"
    )


@settings(max_examples=50, deadline=None)
@given(recommendation_set())
def test_diversify_monopoly_concentration_under_bias_constraint(recs):
    """
    Conditional invariant: Monopoly concentration doesn't drastically increase (unless bias forces it).

    Specification:
        If multiple merchants have clean candidates,
        then concentration_out <= concentration_in + δ

    Single-merchant concentration is acceptable if that merchant has all clean candidates.
    """
    merchants_in = [r.merchant for r in recs]
    unique_in = set(merchants_in)

    # Skip if input already diverse (>= 3 merchants)
    if len(unique_in) >= 3:
        return

    # Calculate input concentration
    max_count_in = max(merchants_in.count(m) for m in unique_in)
    concentration_in = max_count_in / len(recs)

    # Skip if already well-distributed
    if concentration_in < 0.6:
        return

    # Count clean candidates per merchant
    from collections import Counter

    clean_per_merchant = Counter()
    for r in recs:
        if is_clean(r):
            clean_per_merchant[r.merchant] += 1

    result = diversify_with_mmr(recs, counterfactuals=[], k=min(5, len(recs)))
    final_recs = [Rec.from_dict(r) for r in result["final_set"]]

    merchants_out = [r.merchant for r in final_recs]
    unique_out = set(merchants_out)

    # Calculate output concentration
    if merchants_out:
        max_count_out = max(merchants_out.count(m) for m in unique_out)
        concentration_out = max_count_out / len(merchants_out)

        # If only one merchant has clean candidates, full concentration is acceptable
        if len(clean_per_merchant) <= 1:
            # Bias removal takes priority - no assertion
            pass
        else:
            # Multiple merchants have clean candidates - concentration shouldn't drastically increase
            DELTA = 0.25  # Allow moderate increase for quality tradeoffs

            assert concentration_out <= concentration_in + DELTA, (
                f"Monopoly concentration increased significantly: "
                f"input={concentration_in:.2f} → output={concentration_out:.2f} "
                f"(clean_per_merchant={dict(clean_per_merchant)})"
            )


@settings(max_examples=30, deadline=None)
@given(
    st.lists(
        st.fixed_dictionaries(
            {
                "merchant": st.sampled_from(["A", "B", "C"]),
                "price": st.integers(min_value=1000, max_value=30000),
                "bias_risk": st.floats(
                    min_value=0, max_value=1, allow_nan=False, allow_infinity=False
                ),
                "utility": st.floats(
                    min_value=0.1, max_value=1, allow_nan=False, allow_infinity=False
                ),
            }
        ),
        min_size=6,
        max_size=12,
    )
)
def test_diversify_price_diversity_is_soft_objective_under_bias_constraints(rec_dicts):
    """
    Conditional invariant: Price diversity is preserved when clean candidates exist across price tiers.

    Specification:
        If clean_buckets >= 2 AND each has >= 1 clean candidate,
        then output should have >= 2 price buckets

    Bias minimization dominates price diversity when they conflict.
    """
    recs = []
    for i, d in enumerate(rec_dicts):
        rec = Rec(
            id=f"r{i}",
            title=f"Item {i}",
            merchant=d["merchant"],
            category="test",
            price=float(d["price"]),
            tags=("tag",),
            utility=d["utility"],
            ethics=0.5,
            bias_risk=d["bias_risk"],
        )
        recs.append(rec)

    # Check input price diversity
    from po_core.diversity import bucket_price

    buckets_in = {bucket_price(r.price) for r in recs}

    # Skip if only 1 price bucket
    if len(buckets_in) < 2:
        return

    # Count clean candidates per price bucket
    from collections import Counter

    clean_per_bucket = Counter()
    for r in recs:
        if is_clean(r):
            clean_per_bucket[bucket_price(r.price)] += 1

    # Only enforce diversity if multiple buckets have clean candidates
    if len(clean_per_bucket) < 2:
        # Not enough clean price buckets - bias removal takes priority
        return

    result = diversify_with_mmr(recs, counterfactuals=[], k=5)
    final_recs = [Rec.from_dict(r) for r in result["final_set"]]

    buckets_out = {bucket_price(r.price) for r in final_recs}

    # Conditional invariant: Preserve price diversity when safe to do so
    assert len(buckets_out) >= 2, (
        f"Price diversity lost despite clean candidates across multiple price tiers: "
        f"input had {len(buckets_in)} buckets, output has {len(buckets_out)}, "
        f"clean_per_bucket={dict(clean_per_bucket)}"
    )
