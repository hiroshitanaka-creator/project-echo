"""Compatibility wrapper for semantic diversity integration in Project Echo."""

from __future__ import annotations

import math
from typing import Any, cast

from po_core.diversity import Rec, diversify_with_mmr

try:
    from po_core.tensors.engine import create_freedom_pressure_v2
except Exception:  # pragma: no cover - defensive fallback for optional tensor engine
    create_freedom_pressure_v2 = None


def _safe_rec_from_data(candidate: dict[str, Any] | Rec) -> Rec:
    """Normalize a candidate payload into ``Rec`` with non-crashing fallback.

    Args:
        candidate: Recommendation payload as a ``Rec`` instance or dictionary.

    Returns:
        A normalized ``Rec`` instance.

    Raises:
        TypeError: If ``candidate`` is neither ``Rec`` nor ``dict``.
    """
    if isinstance(candidate, Rec):
        return candidate
    if not isinstance(candidate, dict):
        raise TypeError(f"candidate must be Rec or dict, got {type(candidate)!r}")

    rec_from_dict = getattr(Rec, "from_dict", None)
    if callable(rec_from_dict):
        return cast(Rec, rec_from_dict(candidate))

    return Rec(
        id=str(candidate.get("id", "unknown")),
        title=str(candidate.get("title", "")),
        merchant=str(candidate.get("merchant", "unknown")),
        category=str(candidate.get("category", "general")),
        price=float(candidate.get("price", 0.0)),
        tags=tuple(candidate.get("tags", [])),
        utility=float(candidate.get("utility", 0.5)),
        ethics=float(candidate.get("ethics", 0.5)),
        bias_risk=float(candidate.get("bias_risk", 0.0)),
    )


def _safe_create_freedom_pressure_v2() -> dict[str, Any]:
    """Create freedom-pressure v2 engine safely.

    Returns:
        Snapshot containing engine object when available, otherwise fallback metadata.
    """
    if create_freedom_pressure_v2 is None:
        return {
            "status": "fallback",
            "reason": "po_core.tensors.engine.create_freedom_pressure_v2 unavailable",
            "engine": None,
        }

    try:
        engine = create_freedom_pressure_v2()
    except TypeError:
        try:
            engine = create_freedom_pressure_v2({})
        except Exception as exc:  # pragma: no cover
            return {
                "status": "fallback",
                "reason": f"tensor_engine_error:{exc.__class__.__name__}",
                "engine": None,
            }
    except Exception as exc:  # pragma: no cover
        return {
            "status": "fallback",
            "reason": f"tensor_engine_error:{exc.__class__.__name__}",
            "engine": None,
        }

    return {"status": "ok", "engine": engine}


def _safe_cosine_similarity(left: list[float], right: list[float]) -> float:
    """Compute cosine similarity with strong guards."""
    if not left or not right:
        raise ValueError("cosine vectors must be non-empty")

    size = min(len(left), len(right))
    left_s = left[:size]
    right_s = right[:size]

    dot = sum(left_val * right_val for left_val, right_val in zip(left_s, right_s, strict=False))
    left_norm = math.sqrt(sum(left_val * left_val for left_val in left_s))
    right_norm = math.sqrt(sum(right_val * right_val for right_val in right_s))

    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0

    score = dot / (left_norm * right_norm)
    return max(0.0, min(1.0, score))


def _text_to_fallback_6d(text: str) -> list[float]:
    """Build deterministic fallback 6D vector from text."""
    normalized = text.strip().lower()
    if not normalized:
        return [0.0] * 6

    values = [0.0] * 6
    for idx, ch in enumerate(normalized):
        values[idx % 6] += (ord(ch) % 97) / 97.0

    max_val = max(values) or 1.0
    return [round(v / max_val, 6) for v in values]


def _compute_v2_values(snapshot: dict[str, Any], text: str) -> list[float]:
    """Extract 6D tensor values through ``compute_v2(text)`` with fallback safety."""
    engine = snapshot.get("engine")
    compute_v2 = getattr(engine, "compute_v2", None)

    if callable(compute_v2):
        try:
            raw = compute_v2(text)
            if isinstance(raw, dict):
                raw = raw.get("values") or raw.get("6d_values") or []
            values = [float(v) for v in raw][:6]
            if len(values) == 6:
                return values
        except Exception:
            pass

    return _text_to_fallback_6d(text)


def apply_semantic_diversity(
    candidates: list[dict[str, Any] | Rec],
    *,
    counterfactuals: list[dict[str, Any] | Rec] | None = None,
    prompt_text: str,
    k: int = 5,
) -> dict[str, Any]:
    """Apply diversity plus 6D semantic evidence for prompt-vs-candidate distance."""
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")

    original_recs = [_safe_rec_from_data(rec) for rec in candidates]
    cf_recs = [_safe_rec_from_data(rec) for rec in (counterfactuals or [])]
    audit = diversify_with_mmr(original=original_recs, counterfactuals=cf_recs, k=k)

    top_candidate = audit.get("final_set", [{}])[0] if audit.get("final_set") else {}
    candidate_text = f"{top_candidate.get('title', '')} {top_candidate.get('category', '')}".strip()

    snapshot = _safe_create_freedom_pressure_v2()
    snapshot["input"] = {
        "prompt_text": prompt_text,
        "candidate_text": candidate_text,
        "mode": "semantic_6d_cosine",
    }
    prompt_values = _compute_v2_values(snapshot, prompt_text)
    candidate_values = _compute_v2_values(snapshot, candidate_text)
    cosine_similarity = _safe_cosine_similarity(prompt_values, candidate_values)

    enriched = dict(audit)
    enriched["semantic_delta"] = 1.0 - cosine_similarity
    enriched["6d_values"] = {
        "prompt": prompt_values,
        "candidate": candidate_values,
    }
    enriched["freedom_pressure_snapshot"] = snapshot
    return enriched


__all__ = [
    "Rec",
    "create_freedom_pressure_v2",
    "diversify_with_mmr",
    "apply_semantic_diversity",
]
