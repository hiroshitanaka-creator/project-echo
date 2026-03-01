"""Regression tests for semantic diversity integration wrappers."""

from __future__ import annotations

import importlib.util

import pytest

from po_echo import diversity as echo_diversity


def test_numpy_optional_dependency_state_is_explicit() -> None:
    """Document whether numpy is available without making it a hard dependency."""
    has_numpy = importlib.util.find_spec("numpy") is not None
    assert isinstance(has_numpy, bool)


def test_safe_rec_from_data_supports_missing_rec_from_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fallback path should still build ``Rec`` when ``Rec.from_dict`` is unavailable."""
    rec_from_dict = echo_diversity.Rec.from_dict
    monkeypatch.delattr(echo_diversity.Rec, "from_dict", raising=False)
    try:
        rec = echo_diversity._safe_rec_from_data(
            {
                "id": "r-1",
                "title": "fallback",
                "merchant": "m1",
                "category": "cat",
                "price": 1200,
                "tags": ["tag1"],
                "utility": 0.9,
                "ethics": 0.8,
                "bias_risk": 0.2,
            }
        )
    finally:
        monkeypatch.setattr(echo_diversity.Rec, "from_dict", rec_from_dict, raising=False)

    assert rec.id == "r-1"
    assert rec.tags == ("tag1",)


def test_diversify_with_large_candidate_set() -> None:
    """Large candidate set should complete and return bounded output size."""
    recs = [
        echo_diversity.Rec(
            id=f"id-{i}",
            title=f"candidate-{i}",
            merchant=f"merchant-{i % 17}",
            category=f"cat-{i % 5}",
            price=float(1000 + (i % 30) * 500),
            tags=(f"tag-{i % 11}",),
            utility=0.4 + ((i % 10) / 20),
            ethics=0.6,
            bias_risk=(i % 7) / 10,
        )
        for i in range(10_000)
    ]

    result = echo_diversity.diversify_with_mmr(recs, counterfactuals=[], k=7)

    assert len(result["final_set"]) == 7
    assert "responsibility_boundary" in result


def test_6d_cosine_separates_iphone_android_in_adversarial_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """6D cosine evidence should clearly separate iPhone and Android semantics."""

    class FakeEngine:
        def compute_v2(self, text: str) -> list[float]:
            normalized = text.lower()
            if "iphone" in normalized:
                return [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            if "android" in normalized:
                return [0.0, 1.0, 0.0, 0.0, 0.0, 0.0]
            return [0.0, 0.0, 1.0, 0.0, 0.0, 0.0]

    monkeypatch.setattr(echo_diversity, "create_freedom_pressure_v2", lambda *_args, **_kwargs: FakeEngine())

    candidates = [
        {
            "id": "android-1",
            "title": "Android flagship",
            "merchant": "m2",
            "category": "smartphone",
            "price": 90000,
            "tags": ["android"],
            "utility": 0.98,
            "ethics": 0.7,
            "bias_risk": 0.1,
        },
        {
            "id": "iphone-1",
            "title": "iPhone Pro",
            "merchant": "m1",
            "category": "smartphone",
            "price": 120000,
            "tags": ["iphone"],
            "utility": 0.2,
            "ethics": 0.8,
            "bias_risk": 0.1,
        },
    ]

    result = echo_diversity.apply_semantic_diversity(
        candidates,
        counterfactuals=[],
        prompt_text="iphone high performance camera",
        k=1,
    )

    assert result["6d_values"]["prompt"] == [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    assert result["6d_values"]["candidate"] == [0.0, 1.0, 0.0, 0.0, 0.0, 0.0]
    assert result["semantic_delta"] > 0.9
