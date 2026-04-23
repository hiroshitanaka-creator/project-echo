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

from dataclasses import dataclass, replace
from typing import Any

from po_echo.rth import RollingTranscriptHash
from po_echo.voice_boundary import attach_boundary, decide, evaluate_screenless_safety


class SessionStore:
    """Persistence boundary for per-session audio gate state."""

    def get(self, *, session_id: str) -> dict[str, Any] | None:  # pragma: no cover - protocol default
        raise NotImplementedError

    def set(self, *, session_id: str, state: dict[str, Any]) -> None:  # pragma: no cover - protocol default
        raise NotImplementedError


class InMemorySessionStore(SessionStore):
    """Single-process in-memory session store for tests/local gateway usage."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}

    def get(self, *, session_id: str) -> dict[str, Any] | None:
        return self._sessions.get(session_id)

    def set(self, *, session_id: str, state: dict[str, Any]) -> None:
        self._sessions[session_id] = state

    def delete(self, *, session_id: str) -> None:
        self._sessions.pop(session_id, None)


@dataclass(frozen=True)
class VoiceSessionContext:
    """Trusted session context for audio-gate state continuity."""

    session_id: str
    start_new_session: bool = False


def gate_audio(
    audit: dict,
    intent: str,
    meta: dict | None,
    transcript_tail: str,
    simulate_user_ok: bool = False,
    session_id: str | None = None,
    session_store: SessionStore | None = None,
    session_context: VoiceSessionContext | None = None,
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
    # Trusted continuity is session-scoped: explicit context takes precedence.
    effective_session_id = session_context.session_id if session_context else session_id
    reset_session = bool(session_context and session_context.start_new_session)

    persisted_state = None
    if effective_session_id and session_store and not reset_session:
        persisted = session_store.get(session_id=effective_session_id) or {}
        persisted_state = persisted.get("rth")

    rth = (
        RollingTranscriptHash.from_dict(persisted_state)
        if isinstance(persisted_state, dict)
        else RollingTranscriptHash()
    )
    rth_assessment = rth.apply_window(transcript_tail)

    # Determine voice-specific boundary
    decision = decide(intent=intent, meta=meta or {})
    safe_meta = meta or {}

    screenless_safety = evaluate_screenless_safety(
        bias_score=(audit.get("commercial_bias_final") or {}).get("overall_bias_score", 0.0),
        battery_level=safe_meta.get("battery_level", 1.0),
        bluetooth_connected=bool(safe_meta.get("bluetooth_connected", True)),
        replay_detected=rth_assessment.replay_detected,
        tamper_detected=rth_assessment.tamper_detected,
    )

    if not screenless_safety.get("execution_allowed", True):
        decision = replace(
            decision,
            execution_allowed=False,
            requires_human_confirm=True,
            required_action=screenless_safety.get("required_action", "app_confirm"),
            reasons=[*decision.reasons, *screenless_safety.get("reasons", [])],
        )

    if rth_assessment.replay_detected:
        decision = replace(
            decision,
            execution_allowed=False,
            requires_human_confirm=True,
            required_action="app_confirm",
            reasons=[*decision.reasons, "session_transcript_replay_detected"],
        )
    if rth_assessment.discontinuity_detected:
        decision = replace(
            decision,
            execution_allowed=False,
            requires_human_confirm=True,
            required_action="app_confirm",
            reasons=[*decision.reasons, "session_state_discontinuity_detected"],
        )
    if rth_assessment.tamper_detected:
        decision = replace(
            decision,
            execution_allowed=False,
            requires_human_confirm=True,
            required_action="app_confirm",
            reasons=[*decision.reasons, "session_rth_tamper_detected"],
        )

    # If requires human confirmation and not provided, block execution
    if decision.requires_human_confirm and not simulate_user_ok:
        decision = replace(
            decision,
            execution_allowed=False,
            reasons=[*decision.reasons, "awaiting_user_confirmation"],
        )

    # Attach boundary with RTH snapshot
    rth_snapshot = rth.snapshot()
    rth_snapshot["state_continuity"] = rth_assessment.state_continuity
    rth_snapshot["discontinuity_detected"] = rth_assessment.discontinuity_detected
    audit = attach_boundary(audit, decision, rth_snapshot=rth_snapshot)
    if effective_session_id and session_store:
        session_store.set(session_id=effective_session_id, state={"rth": rth.to_dict()})
        audit["responsibility_boundary"]["session_id"] = effective_session_id

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
