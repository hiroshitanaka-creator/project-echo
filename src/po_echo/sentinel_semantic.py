"""Semantic-diversity wrapper used by sentinel pipelines."""

from __future__ import annotations

from typing import Any

from po_core.diversity import Rec

_apply_semantic_diversity = None


def apply_semantic_diversity(
    candidates: list[dict[str, Any] | Rec],
    *,
    counterfactuals: list[dict[str, Any] | Rec] | None = None,
    k: int = 5,
) -> dict[str, Any]:
    """Apply semantic diversity while preserving existing sentinel flow."""
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")

    global _apply_semantic_diversity
    if _apply_semantic_diversity is None:
        from po_echo.diversity import apply_semantic_diversity as _apply_semantic_diversity_impl

        _apply_semantic_diversity = _apply_semantic_diversity_impl

    return _apply_semantic_diversity(
        candidates,
        counterfactuals=counterfactuals,
        prompt_text="sentinel_semantic_scan",
        k=k,
    )

