"""Tests for sentinel_v2 semantic diversity helper."""

from __future__ import annotations

import pytest

from po_echo.sentinel_v2 import apply_semantic_diversity


def test_apply_semantic_diversity_validates_k() -> None:
    """Invalid k must raise ValueError before executing diversity selection."""
    with pytest.raises(ValueError):
        apply_semantic_diversity([], k=0)


def test_apply_semantic_diversity_returns_audit_payload() -> None:
    """Semantic wrapper should return standard diversity audit payload keys."""
    payload = [
        {
            "id": "a",
            "title": "A",
            "merchant": "m1",
            "category": "c1",
            "price": 1000,
            "tags": ["t1"],
            "utility": 0.7,
            "ethics": 0.6,
            "bias_risk": 0.2,
        },
        {
            "id": "b",
            "title": "B",
            "merchant": "m2",
            "category": "c1",
            "price": 8000,
            "tags": ["t2"],
            "utility": 0.6,
            "ethics": 0.6,
            "bias_risk": 0.2,
        },
    ]

    result = apply_semantic_diversity(payload, k=2)

    assert "final_set" in result
    assert len(result["final_set"]) == 2
    assert "semantic_delta" in result
    assert "6d_values" in result
    assert "freedom_pressure_snapshot" in result
