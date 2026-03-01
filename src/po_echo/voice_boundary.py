"""
Voice-Boundary Policy for Audio Channel

Determines responsibility boundary for voice-initiated actions based on risk level.
Designed for ear-worn devices (Sweetpea) with low-friction I/O (voice, tap, IMU).

Risk levels:
- low: Search, summary (auto-execute)
- medium: Booking, itinerary (double-tap or passphrase)
- high: Payment, identity disclosure (app confirmation + screen)

All executions generate Echo Mark receipts regardless of channel.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Literal

Risk = Literal["low", "medium", "high"]
Confirm = Literal["none", "double_tap", "passphrase", "app_confirm"]
FieldName = Literal["amount", "bias_score", "battery_level"]


@dataclass
class VoiceBoundaryDecision:
    """Voice-specific responsibility boundary decision."""

    risk: Risk
    required_action: Confirm
    execution_allowed: bool
    requires_human_confirm: bool
    reasons: list[str]


POLICY = {
    "low": {"required_action": "none", "requires_human_confirm": False},
    "medium": {"required_action": "double_tap", "requires_human_confirm": True},
    "high": {"required_action": "app_confirm", "requires_human_confirm": True},
}

HIGH_BIAS_BLOCK_THRESHOLD = 0.6
LOW_BATTERY_THRESHOLD = 0.15

CRITICAL_INTENTS = {"payment", "purchase", "identity_disclosure"}
SENSITIVE_INTENTS = {"booking", "itinerary", "data_share", "home_access"}
_LOGGER = logging.getLogger(__name__)


def _safe_float(value: Any, *, default: float, field_name: FieldName) -> float:
    """
    Safely coerce numeric-like values to float with audit-friendly warnings.

    Args:
        value: Input value expected to be numeric-like.
        default: Fallback value when conversion fails.
        field_name: Whitelisted field identifier for structured audit logging.

    Returns:
        Parsed float value or the provided default.

    Raises:
        This function does not raise exceptions by design.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        _LOGGER.warning(
            "voice_boundary_invalid_float field=%s value=%r default=%s",
            field_name,
            value,
            default,
        )
        return default


def classify_risk(intent: str, meta: dict | None = None) -> Risk:
    """
    Classify intent risk level for voice-initiated actions.

    Args:
        intent: Intent category (e.g., "booking", "payment", "search")
        meta: Optional metadata (e.g., {"amount": 10000})

    Returns:
        Risk level: "low", "medium", or "high"
    """
    intent_l = (intent or "").lower()
    if intent_l in CRITICAL_INTENTS:
        return "high"
    if intent_l in SENSITIVE_INTENTS:
        return "medium"

    # Fallback: classify by amount or other metadata
    meta = meta or {}
    amt = _safe_float(meta.get("amount", 0), default=0.0, field_name="amount")
    if amt >= 10000:  # High-value transaction
        return "high"
    if amt >= 1000:  # Medium-value transaction
        return "medium"

    return "low"


def decide(intent: str, meta: dict | None = None) -> VoiceBoundaryDecision:
    """
    Determine responsibility boundary for voice-initiated action.

    Args:
        intent: Intent category
        meta: Optional metadata

    Returns:
        VoiceBoundaryDecision with risk level and required confirmation
    """
    risk = classify_risk(intent, meta)
    pol = POLICY[risk]
    reasons = [f"risk:{risk}", f"intent:{intent}"]

    return VoiceBoundaryDecision(
        risk=risk,
        required_action=pol["required_action"],  # type: ignore
        execution_allowed=True,
        requires_human_confirm=pol["requires_human_confirm"],  # type: ignore
        reasons=reasons,
    )


def attach_boundary(
    audit: dict, decision: VoiceBoundaryDecision, rth_snapshot: dict | None = None
) -> dict:
    """
    Attach voice-specific responsibility boundary to audit result.

    Args:
        audit: Audit result from diversify_with_mmr()
        decision: Voice boundary decision
        rth_snapshot: Rolling Transcript Hash snapshot (optional)

    Returns:
        Audit with responsibility_boundary attached
    """
    rb: dict[str, Any] = {
        "channel": "audio",
        "risk": decision.risk,
        "required_action": decision.required_action,
        "execution_allowed": decision.execution_allowed,
        "requires_human_confirm": decision.requires_human_confirm,
        "reasons": decision.reasons,
    }
    if rth_snapshot:
        rb["rth_snapshot"] = rth_snapshot

    audit = dict(audit)
    audit["responsibility_boundary"] = rb
    return audit


def get_voice_boundary_policy(bias_score: float, is_gumdrop: bool = False) -> dict[str, Any]:
    """
    Get voice boundary policy dict for the given bias score and device type.

    Args:
        bias_score: Commercial bias score [0, 1]
        is_gumdrop: True if device is a gumdrop (screenless) device

    Returns:
        Policy dict with risk, required_action, and requires_human_confirm
    """
    safe_bias_score = _safe_float(bias_score, default=0.0, field_name="bias_score")
    if safe_bias_score >= 0.5:
        risk: Risk = "high"
    elif safe_bias_score >= 0.2:
        risk = "medium"
    else:
        risk = "low"
    pol = POLICY[risk]
    return {
        "risk": risk,
        "required_action": pol["required_action"],
        "requires_human_confirm": pol["requires_human_confirm"],
        "is_gumdrop": is_gumdrop,
    }


def evaluate_screenless_safety(
    *,
    bias_score: float,
    battery_level: float,
    bluetooth_connected: bool,
    replay_detected: bool = False,
    tamper_detected: bool = False,
) -> dict[str, Any]:
    """
    Evaluate safety gate for screenless ambient audio channel.

    Why this exists:
        Screenless devices need mechanical enforcement of fallback and block rules
        because users cannot inspect rich UI before execution.
    """
    safe_bias_score = _safe_float(bias_score, default=0.0, field_name="bias_score")
    safe_battery_level = _safe_float(
        battery_level,
        default=0.0,
        field_name="battery_level",
    )
    policy = get_voice_boundary_policy(bias_score=safe_bias_score, is_gumdrop=True)
    fallback_mode = "normal"

    if safe_battery_level < LOW_BATTERY_THRESHOLD or not bluetooth_connected:
        fallback_mode = "on_device_safe_mode"

    should_block = (
        safe_bias_score >= HIGH_BIAS_BLOCK_THRESHOLD or replay_detected or tamper_detected
    )
    if should_block:
        return {
            **policy,
            "execution_allowed": False,
            "requires_human_confirm": True,
            "required_action": "app_confirm",
            "fallback_mode": fallback_mode,
            "reasons": [
                "screenless_guard",
                f"bias_score:{safe_bias_score:.3f}",
                f"replay_detected:{replay_detected}",
                f"tamper_detected:{tamper_detected}",
            ],
        }

    return {
        **policy,
        "execution_allowed": True,
        "fallback_mode": fallback_mode,
        "reasons": ["screenless_guard", f"bias_score:{safe_bias_score:.3f}"],
    }


def make_echo_verified_voice_text(candidate_count: int, evidence_count: int, boundary: dict) -> str:
    """Build voice narration text with responsibility boundary disclosure."""
    return (
        "Echo Verified candidate set ready. "
        f"候補セット{candidate_count}件、証拠{evidence_count}件。"
        "責任境界: "
        f"{boundary.get('required_action', 'app_confirm')} まで。"
    )
