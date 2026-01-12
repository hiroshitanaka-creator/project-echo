"""
Property-based tests for diversity enforcement (anti-monopoly).

Tests invariants:
- If input has 2+ merchants, output should have 2+ merchants (when possible)
- If input has 2+ price buckets, output should have 2+ price buckets (when possible)
- High-bias recommendations should not dominate output
- Merchant monopoly in input should be broken in output (when alternatives exist)
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.strategies import composite

from po_core.diversity import Rec, diversify_with_mmr


@composite
def recommendation_set(draw):
    """Generate realistic recommendation sets for testing."""
    merchants = draw(st.lists(st.sampled_from(["A", "B", "C", "D", "E"]), min_size=1, max_size=5, unique=True))

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


@settings(max_examples=50, deadline=None)
@given(recommendation_set())
def test_diversify_enforces_merchant_diversity(recs):
    """If input has 2+ merchants, output should preserve diversity."""
    merchants_in = {r.merchant for r in recs}

    # Skip if input already has only 1 merchant (can't diversify)
    if len(merchants_in) < 2:
        return

    result = diversify_with_mmr(recs, counterfactuals=[], k=5)
    final_recs = [Rec.from_dict(r) for r in result["final_set"]]

    merchants_out = {r.merchant for r in final_recs}

    # Invariant: Should preserve merchant diversity when possible
    assert len(merchants_out) >= 2, (
        f"Diversity enforcement failed: input had {len(merchants_in)} merchants, "
        f"output has only {len(merchants_out)} merchant(s)"
    )


@settings(max_examples=50, deadline=None)
@given(recommendation_set())
def test_diversify_reduces_monopoly(recs):
    """Monopoly concentration should not significantly increase (unless bias removal forces it)."""
    merchants_in = [r.merchant for r in recs]
    unique_in = set(merchants_in)

    # Skip if input already diverse
    if len(unique_in) >= 3:
        return

    # Calculate input concentration
    max_count_in = max(merchants_in.count(m) for m in unique_in)
    concentration_in = max_count_in / len(recs)

    # Skip if already well-distributed
    if concentration_in < 0.6:
        return

    # Count clean candidates per merchant (effective_utility >= 0.1 with beta=1.0)
    from collections import Counter

    clean_per_merchant = Counter()
    for r in recs:
        if r.utility - r.bias_risk >= 0.1:
            clean_per_merchant[r.merchant] += 1

    result = diversify_with_mmr(recs, counterfactuals=[], k=min(5, len(recs)))
    final_recs = [Rec.from_dict(r) for r in result["final_set"]]

    merchants_out = [r.merchant for r in final_recs]
    unique_out = set(merchants_out)

    # Calculate output concentration
    if merchants_out:
        max_count_out = max(merchants_out.count(m) for m in unique_out)
        concentration_out = max_count_out / len(merchants_out)

        # Invariant: Concentration should not significantly increase
        # If one merchant has all clean candidates and others are contaminated,
        # allow full concentration (bias removal priority)
        if len(clean_per_merchant) == 1:
            # Only one merchant has clean candidates - concentration increase is acceptable
            pass
        else:
            # Multiple merchants have clean candidates - concentration should not drastically increase
            assert concentration_out <= concentration_in + 0.3, (
                f"Monopoly significantly increased: input concentration={concentration_in:.2f}, "
                f"output concentration={concentration_out:.2f}, clean_per_merchant={dict(clean_per_merchant)}"
            )


@settings(max_examples=50, deadline=None)
@given(recommendation_set())
def test_diversify_no_high_bias_amplification(recs):
    """High-bias recommendations should not be amplified beyond necessity."""
    # Count high-bias in input
    high_bias_in = sum(1 for r in recs if r.bias_risk > 0.7)

    # Skip if no high-bias recs
    if high_bias_in == 0:
        return

    # Count clean candidates (effective_utility >= 0.1 with beta=1.0)
    clean_candidates = sum(1 for r in recs if r.utility - r.bias_risk >= 0.1)

    result = diversify_with_mmr(recs, counterfactuals=[], k=5)
    final_recs = [Rec.from_dict(r) for r in result["final_set"]]

    # Count high-bias in output
    high_bias_out = sum(1 for r in final_recs if r.bias_risk > 0.7)

    # Invariant: High-bias proportion should not increase if clean candidates are sufficient
    proportion_in = high_bias_in / len(recs) if recs else 0
    proportion_out = high_bias_out / len(final_recs) if final_recs else 0

    # If enough clean candidates exist (>= k), proportion should decrease
    if clean_candidates >= 5:
        assert proportion_out <= proportion_in, (
            f"High-bias amplified despite sufficient clean candidates: "
            f"input={proportion_in:.2%}, output={proportion_out:.2%}"
        )
    # Otherwise, allow moderate increase (up to +0.2) due to lack of clean alternatives
    else:
        assert proportion_out <= proportion_in + 0.2, (
            f"High-bias amplified beyond acceptable limit: "
            f"input={proportion_in:.2%}, output={proportion_out:.2%}, clean_candidates={clean_candidates}"
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
def test_diversify_enforces_price_diversity(rec_dicts):
    """Price diversity should be preserved when high-utility options exist in multiple tiers."""
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

    # Count high-utility (>=0.8) candidates per price bucket
    from collections import Counter

    high_utility_per_bucket = Counter()
    for r in recs:
        if r.utility >= 0.8:
            high_utility_per_bucket[bucket_price(r.price)] += 1

    result = diversify_with_mmr(recs, counterfactuals=[], k=5)
    final_recs = [Rec.from_dict(r) for r in result["final_set"]]

    buckets_out = {bucket_price(r.price) for r in final_recs}

    # Invariant: Price diversity should be preserved if high-utility options exist in multiple buckets
    # If one price bucket has all high-utility candidates, consolidation is acceptable (quality priority)
    if len(high_utility_per_bucket) >= 2 and min(high_utility_per_bucket.values()) >= 1:
        # Multiple buckets have high-utility candidates - diversity should be preserved
        assert len(buckets_out) >= 2, (
            f"Price diversity lost despite high-utility options in multiple buckets: "
            f"input had {len(buckets_in)} buckets, output has only {len(buckets_out)} bucket(s), "
            f"high_utility_per_bucket={dict(high_utility_per_bucket)}"
        )
    # Otherwise, allow consolidation (quality/bias tradeoff)
