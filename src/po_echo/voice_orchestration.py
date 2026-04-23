"""Thin orchestration layer for Voice Boundary + verified session + Echo Mark."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from po_echo.ear_handshake import (
    EarHandshakeError,
    EarHandshakeService,
    InMemoryChallengeStore,
    InMemoryDeviceTrustStore,
    VerifiedSession,
)
from po_echo.echo_mark import make_echo_mark_dual
from po_echo.execution_gate import (
    InMemorySessionStore,
    SessionStore,
    VoiceSessionContext,
    gate_audio,
)
from po_echo.security_fingerprints import fingerprint_session_key
from po_echo.voice_boundary import make_echo_verified_voice_text

VOICE_INPUT_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Project Echo Voice CLI Input",
    "type": "object",
    "required": ["intent", "transcript", "metadata", "device_id", "challenge_id", "response_hex"],
    "properties": {
        "intent": {"type": "string", "minLength": 1},
        "transcript": {"type": "string", "minLength": 1},
        "metadata": {"type": "object"},
        "simulate_ok": {"type": "boolean", "default": False},
        "run_id": {"type": ["string", "null"]},
        "key_id": {"type": "string", "default": "default"},
        "device_id": {"type": "string", "minLength": 1},
        "challenge_id": {"type": "string", "minLength": 1},
        "response_hex": {"type": "string", "minLength": 1},
    },
    "additionalProperties": False,
}

VOICE_OUTPUT_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Project Echo Voice CLI Output",
    "type": "object",
    "required": ["candidate_set", "evidence", "responsibility_boundary", "voice_text", "echo_mark"],
    "properties": {
        "candidate_set": {"type": "array"},
        "evidence": {"type": "array", "items": {"type": "object"}},
        "responsibility_boundary": {"type": "object"},
        "voice_text": {"type": "string"},
        "echo_mark": {"type": "object"},
    },
    "additionalProperties": False,
}

VOICE_SCHEMA_HELP = (
    "Input schema(required): {'intent':str,'transcript':str,'metadata':object,'device_id':str,'challenge_id':str,'response_hex':str}; "
    "Output schema: {'candidate_set':array,'evidence':array,'responsibility_boundary':object,'voice_text':str,'echo_mark':object}"
)


@dataclass(frozen=True)
class VoiceFlowInput:
    intent: str
    transcript: str
    metadata: dict[str, Any]
    device_id: str
    challenge_id: str
    response_hex: str
    simulate_ok: bool = False
    run_id: str | None = None
    key_id: str = "default"
    session_id: str | None = None


class VoiceFlowError(RuntimeError):
    """Domain error for voice orchestration failures."""


def inventory_voice_stack() -> list[dict[str, str]]:
    return [
        {"component": "voice_boundary", "module": "po_echo.voice_boundary", "role": "risk+responsibility boundary"},
        {"component": "ear_handshake", "module": "po_echo.ear_handshake", "role": "trusted registry challenge-response"},
        {"component": "rth", "module": "po_echo.rth", "role": "rolling transcript hash evidence"},
        {"component": "execution_gate", "module": "po_echo.execution_gate", "role": "audio gate orchestration"},
        {"component": "echo_mark", "module": "po_echo.echo_mark", "role": "dual signature receipt"},
    ]


def _validate_input(payload: VoiceFlowInput) -> None:
    if not payload.intent.strip():
        raise VoiceFlowError("intent is required")
    if not payload.transcript.strip():
        raise VoiceFlowError("transcript is required")
    if not isinstance(payload.metadata, dict):
        raise VoiceFlowError("metadata must be object")
    if not payload.device_id.strip() or not payload.challenge_id.strip() or not payload.response_hex.strip():
        raise VoiceFlowError("device_id/challenge_id/response_hex are required")


def begin_handshake(*, handshake: EarHandshakeService, device_id: str) -> dict[str, str | int]:
    return handshake.issue_challenge(device_id=device_id)


def complete_handshake(*, handshake: EarHandshakeService, payload: VoiceFlowInput) -> VerifiedSession:
    try:
        return handshake.verify_response(
            device_id=payload.device_id,
            challenge_id=payload.challenge_id,
            response_hex=payload.response_hex,
        )
    except EarHandshakeError as exc:
        raise VoiceFlowError(f"ear handshake verification failed: {exc}") from exc


def run_voice_flow_with_verified_session(
    *,
    audit: dict[str, Any],
    payload: VoiceFlowInput,
    verified_session: VerifiedSession,
    hmac_secret: str,
    ed25519_private_key: str,
    session_store: SessionStore | None = None,
    require_execution_allowed: bool = False,
) -> dict[str, Any]:
    effective_session_store = session_store or InMemorySessionStore()
    effective_session_id = payload.session_id or verified_session.session_id

    audit_with_gate = gate_audio(
        audit=audit,
        intent=payload.intent,
        meta=payload.metadata,
        transcript_tail=payload.transcript,
        simulate_user_ok=payload.simulate_ok,
        session_context=VoiceSessionContext(session_id=effective_session_id),
        session_store=effective_session_store,
    )

    boundary = audit_with_gate.get("responsibility_boundary", {})
    if require_execution_allowed and not boundary.get("execution_allowed", False):
        raise VoiceFlowError("dangerous_or_unconfirmed_action_blocked")

    badge = make_echo_mark_dual(
        audit=audit_with_gate,
        hmac_secret=hmac_secret,
        ed25519_private_key=ed25519_private_key,
        key_id=payload.key_id,
        run_id=payload.run_id,
    )

    candidate_set = audit_with_gate.get("final_set", [])
    evidence = [
        {
            "type": "ear_handshake",
            "device_id": verified_session.device_id,
            "key_id": verified_session.key_id,
            "challenge_id": verified_session.challenge_id,
            "session_key_fingerprint": fingerprint_session_key(verified_session.session_key),
            "session_id": effective_session_id,
        },
        {
            "type": "rth_snapshot",
            "hash_hex": boundary.get("rth_snapshot", {}).get("hash_hex", ""),
            "state_continuity": boundary.get("rth_snapshot", {}).get("state_continuity", "unknown"),
        },
        {
            "type": "echo_mark",
            "schema_version": badge.get("schema_version"),
            "verification_method": badge.get("verification_method"),
            "signature_prefix": badge.get("signature", "")[:32],
        },
    ]

    voice_text = make_echo_verified_voice_text(len(candidate_set), len(evidence), boundary)
    return {
        "candidate_set": candidate_set,
        "evidence": evidence,
        "responsibility_boundary": boundary,
        "voice_text": voice_text,
        "echo_mark": badge,
    }


def run_voice_flow(
    *,
    audit: dict[str, Any],
    payload: VoiceFlowInput,
    handshake: EarHandshakeService,
    hmac_secret: str,
    ed25519_private_key: str,
    require_execution_allowed: bool = False,
    trust_store: InMemoryDeviceTrustStore | None = None,
    challenge_store: InMemoryChallengeStore | None = None,
    session_store: SessionStore | None = None,
) -> dict[str, Any]:
    del trust_store, challenge_store
    _validate_input(payload)
    verified_session = complete_handshake(handshake=handshake, payload=payload)
    return run_voice_flow_with_verified_session(
        audit=audit,
        payload=payload,
        verified_session=verified_session,
        hmac_secret=hmac_secret,
        ed25519_private_key=ed25519_private_key,
        session_store=session_store,
        require_execution_allowed=require_execution_allowed,
    )
