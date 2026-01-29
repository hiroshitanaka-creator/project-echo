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
from typing import Literal

Risk = Literal["low", "medium", "high"]
Confirm = Literal["none", "double_tap", "passphrase", "app_confirm"]


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

CRITICAL_INTENTS = {"payment", "purchase", "identity_disclosure"}
SENSITIVE_INTENTS = {"booking", "itinerary", "data_share", "home_access"}


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
    amt = float(meta.get("amount", 0))
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
    rb = {
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
