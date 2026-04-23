"""Regression tests to ensure po_core.diversity uses centralized thresholds."""

from __future__ import annotations

from po_core import config
from po_core.diversity import Rec, diversify_with_mmr, recommendation_boundary


def _boundary_inputs(*, bias_original: float, bias_final: float, merchant_concentration: float = 0.5):
    return (
        {"overall_bias_score": bias_original},
        {"overall_bias_score": bias_final},
        {"merchants": 2, "price_buckets": 2, "merchant_concentration": merchant_concentration},
        {"merchants": 2, "price_buckets": 2, "merchant_concentration": merchant_concentration},
    )


def test_boundary_blocks_at_high_bias_threshold() -> None:
    args = _boundary_inputs(
        bias_original=config.MEDIUM_BIAS_THRESHOLD,
        bias_final=config.HIGH_BIAS_THRESHOLD,
    )
    boundary = recommendation_boundary(*args)
    assert boundary["execution_allowed"] is False
    assert "high_bias_after_diversification" in boundary["reasons"]


def test_boundary_uses_medium_and_improvement_thresholds() -> None:
    bias_final = config.MEDIUM_BIAS_THRESHOLD - 0.01
    bias_original = bias_final + config.SIGNIFICANT_IMPROVEMENT_THRESHOLD + 0.01
    args = _boundary_inputs(bias_original=bias_original, bias_final=bias_final)
    boundary = recommendation_boundary(*args)
    assert boundary["execution_allowed"] is True
    assert boundary["requires_human_confirm"] is True
    assert "bias_improved_significantly" in boundary["reasons"]


def test_boundary_uses_monopoly_threshold_from_config() -> None:
    args = _boundary_inputs(
        bias_original=config.MEDIUM_BIAS_THRESHOLD,
        bias_final=config.MEDIUM_BIAS_THRESHOLD,
        merchant_concentration=config.MONOPOLY_CONCENTRATION_THRESHOLD + 0.01,
    )
    boundary = recommendation_boundary(*args)
    assert "merchant_monopoly_detected" in boundary["reasons"]
    assert boundary["requires_human_confirm"] is True


def test_diversify_filters_using_central_high_bias_filter_threshold() -> None:
    clean = [
        Rec(
            id=f"clean-{idx}",
            title="clean",
            merchant=f"m-{idx}",
            category="cat",
            price=1000.0 + idx,
            tags=("safe",),
            utility=0.9,
            ethics=0.7,
            bias_risk=config.HIGH_BIAS_FILTER_THRESHOLD,
        )
        for idx in range(5)
    ]
    high_bias = [
        Rec(
            id=f"high-{idx}",
            title="high",
            merchant=f"h-{idx}",
            category="cat",
            price=2000.0 + idx,
            tags=("risky",),
            utility=0.95,
            ethics=0.7,
            bias_risk=min(1.0, config.HIGH_BIAS_FILTER_THRESHOLD + 0.05),
        )
        for idx in range(5)
    ]

    result = diversify_with_mmr(clean + high_bias, counterfactuals=[], k=5)
    selected = [Rec.from_dict(r) for r in result["final_set"]]
    assert all(r.bias_risk <= config.HIGH_BIAS_FILTER_THRESHOLD for r in selected)
