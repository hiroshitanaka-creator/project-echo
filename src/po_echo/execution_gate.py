# -*- coding: utf-8 -*-
"""
Execution Gate for Multi-Channel Actions

Unified execution gate for different channels (screen, audio, etc.).
Determines responsibility boundary based on:
- Channel type (screen vs audio)
- Risk level (low/medium/high)
- User confirmation status

Integrates with:
- Voice-Boundary Policy (src/po_echo/voice_boundary.py)
- Rolling Transcript Hash (src/po_echo/rth.py)
- Echo Mark (src/po_echo/echo_mark.py)
"""
from __future__ import annotations

from typing import Dict, Optional

from po_echo.rth import RollingTranscriptHash
from po_echo.voice_boundary import attach_boundary, decide


def gate_audio(
    audit: Dict,
    intent: str,
    meta: Optional[Dict],
    transcript_tail: str,
    simulate_user_ok: bool = False,
) -> Dict:
    """
    Apply execution gate for audio channel (voice-initiated actions).

    Args:
        audit: Audit result from diversify_with_mmr()
        intent: Intent category (e.g., "booking", "payment", "search")
        meta: Optional metadata (e.g., {"amount": 10000})
        transcript_tail: Last N seconds of transcript (typically 5 seconds)
        simulate_user_ok: If True, simulate user confirmation (for testing)

    Returns:
        Audit with responsibility_boundary attached

    Flow:
        1. Update Rolling Transcript Hash with transcript_tail
        2. Classify risk level based on intent and metadata
        3. Determine required confirmation action (none/double_tap/app_confirm)
        4. If requires_human_confirm and not confirmed, block execution
        5. Attach responsibility_boundary with RTH snapshot to audit
        6. Return audit (ready for Echo Mark generation)

    Example:
        audit = diversify_with_mmr(...)
        audit_with_gate = gate_audio(
            audit=audit,
            intent="booking",
            meta={"amount": 10000},
            transcript_tail="予約したい。土曜の夜、2人、予算は1万円以下で",
            simulate_user_ok=True
        )
        badge = make_echo_mark(audit_with_gate, secret=..., key_id="v1")
    """
    # Update Rolling Transcript Hash
    rth = RollingTranscriptHash()
    rth.update_text(transcript_tail)

    # Determine voice-specific boundary
    decision = decide(intent=intent, meta=meta or {})

    # If requires human confirmation and not provided, block execution
    if decision.requires_human_confirm and not simulate_user_ok:
        decision.execution_allowed = False
        decision.reasons.append("awaiting_user_confirmation")

    # Attach boundary with RTH snapshot
    audit = attach_boundary(audit, decision, rth_snapshot=rth.snapshot())

    return audit
