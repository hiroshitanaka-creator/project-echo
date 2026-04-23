"""Thin orchestration layer for Voice Boundary + verified session + Echo Mark."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from po_echo.ear_handshake import EarHandshakeError, EarHandshakeService, VerifiedSession
from po_echo.echo_mark import make_echo_mark_dual
from po_echo.execution_gate import gate_audio
from po_echo.voice_boundary import make_echo_verified_voice_text

VOICE_INPUT_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Project Echo Voice CLI Input",
    "type": "object",
    "required": ["intent", "transcript", "metadata", "device_id", "challenge_id", "response_hex"],
    "properties": {
        "intent": {"type": "string", "minLength": 1, "description": "Intent category"},
        "transcript": {"type": "string", "minLength": 1, "description": "Last 5-second transcript"},
        "metadata": {"type": "object", "description": "Action metadata such as amount"},
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
        "candidate_set": {"type": "array", "description": "Non-recommendation candidate set"},
        "evidence": {
            "type": "array",
            "items": {"type": "object"},
            "description": "Ear handshake + RTH + Echo Mark evidence blocks",
        },
        "responsibility_boundary": {"type": "object", "description": "Execution responsibility boundary"},
        "voice_text": {"type": "string"},
        "echo_mark": {"type": "object", "description": "Dual-signature receipt"},
    },
    "additionalProperties": False,
}

VOICE_SCHEMA_HELP = (
    "Input schema(required): {'intent':str,'transcript':str,'metadata':object," 
    "'device_id':str,'challenge_id':str,'response_hex':str}; "
    "Output schema: {'candidate_set':array,'evidence':array,'responsibility_boundary':object,'voice_text':str,'echo_mark':object}"
)


@dataclass(frozen=True)
class VoiceFlowInput:
    """Validated voice-flow input payload."""

    intent: str
    transcript: str
    metadata: dict[str, Any]
    device_id: str
    challenge_id: str
    response_hex: str
    simulate_ok: bool = False
    run_id: str | None = None
    key_id: str = "default"


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


def authenticate_voice_session(*, handshake: EarHandshakeService, payload: VoiceFlowInput) -> VerifiedSession:
    try:
        return handshake.verify_response(
            device_id=payload.device_id,
            challenge_id=payload.challenge_id,
            response_hex=payload.response_hex,
        )
    except EarHandshakeError as exc:
        raise VoiceFlowError(f"ear handshake verification failed: {exc}") from exc


def run_voice_flow(
    *,
    audit: dict[str, Any],
    payload: VoiceFlowInput,
    handshake: EarHandshakeService,
    hmac_secret: str,
    ed25519_private_key: str,
    require_execution_allowed: bool = False,
) -> dict[str, Any]:
    """Execute voice flow and return schema-stable result object."""
    _validate_input(payload)
    session = authenticate_voice_session(handshake=handshake, payload=payload)

    audit_with_gate = gate_audio(
        audit=audit,
        intent=payload.intent,
        meta=payload.metadata,
        transcript_tail=payload.transcript,
        simulate_user_ok=payload.simulate_ok,
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
            "key_id": session.key_id,
            "device_id": session.device_id,
            "challenge_id": session.challenge_id,
            "authenticated_at": session.authenticated_at,
            "session_id": session.session_id,
            "session_key_prefix": session.session_key[:16],
        },
        {
            "type": "rth_snapshot",
            "hash_hex": boundary.get("rth_snapshot", {}).get("hash_hex", ""),
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
