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

from typing import Any

from po_echo.rth import RollingTranscriptHash
from po_echo.voice_boundary import attach_boundary, decide


def gate_audio(
    audit: dict,
    intent: str,
    meta: dict | None,
    transcript_tail: str,
    simulate_user_ok: bool = False,
) -> dict:
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


def enrich_audit_with_semantic_evidence(
    audit: dict[str, Any],
    semantic_result: dict[str, Any] | None,
) -> dict[str, Any]:
    """Attach semantic evidence blocks without mutating execution-gate behavior.

    Args:
        audit: Existing audit payload returned by the diversity pipeline.
        semantic_result: Optional semantic-analysis output to be embedded.

    Returns:
        New audit dictionary that includes ``semantic_evidence`` and
        ``semantic_evidence_present`` fields.

    Raises:
        TypeError: If ``audit`` is not a dictionary.
    """
    if not isinstance(audit, dict):
        raise TypeError("audit must be a dictionary")

    merged = dict(audit)
    semantic_evidence = semantic_result or {}
    merged["semantic_evidence"] = semantic_evidence
    merged["semantic_evidence_present"] = bool(semantic_evidence)

    for key in ("semantic_delta", "6d_values", "freedom_pressure_snapshot"):
        if key in semantic_evidence:
            merged[key] = semantic_evidence[key]

    return merged
