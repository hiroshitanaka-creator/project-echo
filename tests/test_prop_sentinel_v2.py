"""Property-based tests for sentinel_v2 semantic diversity.

These tests exercise invariants that the existing unit tests do not cover:
- semantic_delta is always in [0.0, 1.0] regardless of input
- final_set length never exceeds k
- all required output keys are always present
- adversarial inputs (mono-merchant, empty titles) are handled gracefully
- counterfactual injection does not break output schema

Why property-based: the diversity pipeline contains several numeric paths
(cosine similarity, MMR scoring, fallback 6D vectors) where adversarial
inputs (all-same-merchant, zero-utility, empty title) can hit degenerate
branches that unit tests with hand-crafted fixtures tend to miss.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from po_echo.sentinel_v2 import apply_semantic_diversity

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_MERCHANTS = ["m1", "m2", "m3", "m4"]
_CATEGORIES = ["electronics", "food", "fashion", "home"]
_TAGS = ["t1", "t2", "t3", "sale", "new"]

_candidate_strategy = st.fixed_dictionaries(
    {
        "id": st.text(
            min_size=1,
            max_size=10,
            alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
        ),
        "title": st.text(min_size=0, max_size=60),
        "merchant": st.sampled_from(_MERCHANTS),
        "category": st.sampled_from(_CATEGORIES),
        "price": st.floats(
            min_value=100.0, max_value=100_000.0, allow_nan=False, allow_infinity=False
        ),
        "tags": st.lists(st.sampled_from(_TAGS), min_size=0, max_size=4),
        "utility": st.floats(
            min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
        "ethics": st.floats(
            min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
        "bias_risk": st.floats(
            min_value=0.0, max_value=0.99, allow_nan=False, allow_infinity=False
        ),
    }
)

_k_strategy = st.integers(min_value=1, max_value=5)


# ---------------------------------------------------------------------------
# Core invariant properties
# ---------------------------------------------------------------------------


@given(
    candidates=st.lists(_candidate_strategy, min_size=1, max_size=10),
    k=_k_strategy,
)
@settings(max_examples=60, deadline=None)
def test_semantic_delta_always_in_unit_interval(
    candidates: list[dict],
    k: int,
) -> None:
    """semantic_delta must always be in [0.0, 1.0].

    Why: semantic_delta = 1 - cosine_similarity. If the cosine or fallback
    vector computation produces out-of-range values, downstream callers using
    the delta as a diversity threshold would silently fail.
    """
    result = apply_semantic_diversity(candidates, k=k)
    delta = result["semantic_delta"]
    assert isinstance(delta, float), f"semantic_delta must be float, got {type(delta)}"
    assert 0.0 <= delta <= 1.0, f"semantic_delta={delta!r} out of [0.0, 1.0]"


@given(
    candidates=st.lists(_candidate_strategy, min_size=1, max_size=10),
    k=_k_strategy,
)
@settings(max_examples=60, deadline=None)
def test_final_set_length_never_exceeds_k(
    candidates: list[dict],
    k: int,
) -> None:
    """final_set must have at most k items regardless of input size.

    Why: callers treat k as a hard upper bound for display/voice-readout.
    Exceeding k would violate the candidate-set contract.
    """
    result = apply_semantic_diversity(candidates, k=k)
    assert len(result["final_set"]) <= k, (
        f"final_set has {len(result['final_set'])} items but k={k}"
    )


@given(
    candidates=st.lists(_candidate_strategy, min_size=1, max_size=10),
    k=_k_strategy,
)
@settings(max_examples=60, deadline=None)
def test_required_schema_keys_always_present(
    candidates: list[dict],
    k: int,
) -> None:
    """All schema keys required by downstream consumers must always be present.

    Why: downstream modules (cli, voice_orchestration) access these keys
    without defensive checks; a missing key causes a KeyError in production.
    """
    result = apply_semantic_diversity(candidates, k=k)
    for key in ("final_set", "semantic_delta", "6d_values", "freedom_pressure_snapshot"):
        assert key in result, f"required key '{key}' missing from output"
    assert "prompt" in result["6d_values"], "'prompt' missing from 6d_values"
    assert "candidate" in result["6d_values"], "'candidate' missing from 6d_values"


# ---------------------------------------------------------------------------
# Counterfactual injection
# ---------------------------------------------------------------------------


@given(
    candidates=st.lists(_candidate_strategy, min_size=1, max_size=8),
    counterfactuals=st.lists(_candidate_strategy, min_size=0, max_size=5),
    k=_k_strategy,
)
@settings(max_examples=50, deadline=None)
def test_counterfactual_injection_preserves_schema(
    candidates: list[dict],
    counterfactuals: list[dict],
    k: int,
) -> None:
    """Output schema must be stable whether or not counterfactuals are provided.

    Why: callers optionally inject counterfactuals; None and [] must behave
    identically to a non-empty list from a schema perspective.
    """
    result = apply_semantic_diversity(candidates, counterfactuals=counterfactuals, k=k)
    assert "semantic_delta" in result
    assert 0.0 <= result["semantic_delta"] <= 1.0
    assert len(result["final_set"]) <= k


# ---------------------------------------------------------------------------
# Adversarial inputs
# ---------------------------------------------------------------------------


@given(
    candidates=st.lists(
        _candidate_strategy.map(lambda c: {**c, "merchant": "mono_merchant"}),
        min_size=2,
        max_size=8,
    ),
    k=_k_strategy,
)
@settings(max_examples=40, deadline=None)
def test_mono_merchant_adversarial_does_not_crash(
    candidates: list[dict],
    k: int,
) -> None:
    """All candidates from one merchant must not raise.

    Why: this is the canonical vendor lock-in scenario sentinel_v2 is designed
    to detect. The diversity pipeline must handle a fully saturated merchant
    distribution without crashing, even if the resulting set is less diverse.
    """
    result = apply_semantic_diversity(candidates, k=k)
    assert "final_set" in result
    assert "semantic_delta" in result
    assert 0.0 <= result["semantic_delta"] <= 1.0


@given(
    candidates=st.lists(
        _candidate_strategy.map(lambda c: {**c, "title": ""}),
        min_size=1,
        max_size=6,
    ),
    k=_k_strategy,
)
@settings(max_examples=40, deadline=None)
def test_empty_title_candidates_handled_gracefully(
    candidates: list[dict],
    k: int,
) -> None:
    """Empty-title candidates must not crash or produce invalid semantic_delta.

    Why: _text_to_fallback_6d("") returns [0.0]*6; the zero-vector path in
    _safe_cosine_similarity must return 0.0 rather than divide-by-zero.
    """
    result = apply_semantic_diversity(candidates, k=k)
    assert 0.0 <= result["semantic_delta"] <= 1.0
    assert "final_set" in result


@given(
    candidates=st.lists(_candidate_strategy, min_size=1, max_size=3),
)
@settings(max_examples=40, deadline=None)
def test_k_larger_than_candidates_returns_at_most_input_size(
    candidates: list[dict],
) -> None:
    """When k > len(candidates), final_set cannot exceed number of input candidates.

    Why: MMR selection draws from the input pool; requesting more than available
    candidates must not fabricate items.
    """
    k = len(candidates) + 5
    result = apply_semantic_diversity(candidates, k=k)
    assert len(result["final_set"]) <= len(candidates), (
        f"final_set has {len(result['final_set'])} items but only {len(candidates)} candidates were given"
    )
