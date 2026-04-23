# src/po_echo/gumdrop_defense.py
"""
Gumdrop（画面無しデバイス）向けEcho Mark強化
OpenAI World Register戦略（状態保持チップ＋「失敗しなかった意図」課金）への直接カウンター
"""

from __future__ import annotations

from typing import Any

from .diversity import _safe_create_freedom_pressure_v2
from .echo_mark import generate_echo_mark
from .rth import compute_rth
from .voice_boundary import get_voice_boundary_policy


def apply_gumdrop_defense(recommendation: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Run lightweight gumdrop defense flow with non-destructive safeguards."""
    bias_score = _light_commercial_bias_audit(recommendation, context)
    diversified = _voice_diversity_noise(recommendation, bias_score)
    policy = get_voice_boundary_policy(bias_score, context.get("device_type") == "gumdrop")

    signing_secret = context.get("echo_mark_secret")
    if not isinstance(signing_secret, str) or not signing_secret:
        raise RuntimeError("echo_mark_secret is required for gumdrop Echo Mark signing")

    mark = generate_echo_mark(payload=diversified, secret=signing_secret)

    return {
        "candidates": diversified["candidates"],
        "policy": policy,
        "echo_mark": mark,
        "rth": compute_rth(context.get("transcript", "")),
        "freedom_pressure_snapshot": diversified.get("freedom_pressure_snapshot"),
    }


def _light_commercial_bias_audit(rec: dict[str, Any], context: dict[str, Any] | None = None) -> float:
    """Estimate bias score using candidate risk + FreedomPressureV2 snapshot.

    This intentionally avoids affiliate-flag dependency and relies on observable
    candidate signals plus lightweight semantic pressure.
    """
    candidates = rec.get("alternatives") or [rec]
    risk_values = [float(item.get("bias_risk", 0.0) or 0.0) for item in candidates if isinstance(item, dict)]
    avg_risk = sum(risk_values) / len(risk_values) if risk_values else 0.0

    snapshot = _safe_create_freedom_pressure_v2()
    engine = snapshot.get("engine")
    prompt_text = str((context or {}).get("prompt", ""))
    pressure_score = 0.0

    compute_v2 = getattr(engine, "compute_v2", None)
    if callable(compute_v2):
        try:
            raw = compute_v2(prompt_text)
            values = raw.get("values") if isinstance(raw, dict) else raw
            if isinstance(values, (list, tuple)) and values:
                nums = [abs(float(v)) for v in values[:6]]
                pressure_score = min(1.0, sum(nums) / max(len(nums), 1))
        except Exception:
            pressure_score = 0.0

    return max(0.0, min(1.0, (avg_risk * 0.8) + (pressure_score * 0.2)))


def _voice_diversity_noise(rec: dict[str, Any], bias: float) -> dict[str, Any]:
    """Limit candidates to voice-friendly top-three while preserving transparency."""
    candidates = (rec.get("alternatives") or [rec])[:3]
    snapshot = _safe_create_freedom_pressure_v2()
    return {"candidates": candidates, "bias_score": bias, "freedom_pressure_snapshot": snapshot}
