"""Thin orchestration layer for Voice Boundary + Ear Handshake + RTH + Echo Mark.

This module keeps CLI glue minimal by centralizing the integrated voice flow:
- input validation (schema-aligned)
- ear handshake/session evidence
- execution gate (voice boundary + RTH)
- dual-signature Echo Mark generation
- output assembly (candidate_set + evidence + responsibility_boundary)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from po_echo.ear_handshake import derive_session_key, issue_challenge, new_device, verify_response
from po_echo.echo_mark import make_echo_mark_dual
from po_echo.execution_gate import gate_audio
from po_echo.voice_boundary import make_echo_verified_voice_text

VOICE_INPUT_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Project Echo Voice CLI Input",
    "type": "object",
    "required": ["intent", "transcript", "metadata"],
    "properties": {
        "intent": {"type": "string", "minLength": 1, "description": "Intent category"},
        "transcript": {"type": "string", "minLength": 1, "description": "Last 5-second transcript"},
        "metadata": {"type": "object", "description": "Action metadata such as amount"},
        "simulate_ok": {"type": "boolean", "default": False},
        "run_id": {"type": ["string", "null"]},
        "key_id": {"type": "string", "default": "default"},
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
    "Input schema(required): {'intent':str,'transcript':str,'metadata':object}; "
    "Output schema: {'candidate_set':array,'evidence':array,'responsibility_boundary':object,'voice_text':str,'echo_mark':object}"
)


@dataclass(frozen=True)
class VoiceFlowInput:
    """Validated voice-flow input payload."""

    intent: str
    transcript: str
    metadata: dict[str, Any]
    simulate_ok: bool = False
    run_id: str | None = None
    key_id: str = "default"
    device_secret_hex: str | None = None


class VoiceFlowError(RuntimeError):
    """Domain error for voice orchestration failures."""


def inventory_voice_stack() -> list[dict[str, str]]:
    """Return auditable implementation inventory for CLI and docs."""
    return [
        {"component": "voice_boundary", "module": "po_echo.voice_boundary", "role": "risk+responsibility boundary"},
        {"component": "ear_handshake", "module": "po_echo.ear_handshake", "role": "device challenge-response"},
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


def run_voice_flow(
    *,
    audit: dict[str, Any],
    payload: VoiceFlowInput,
    hmac_secret: str,
    ed25519_private_key: str,
    require_execution_allowed: bool = False,
) -> dict[str, Any]:
    """Execute voice flow and return schema-stable result object."""
    _validate_input(payload)

    try:
        master_key = bytes.fromhex(payload.device_secret_hex) if payload.device_secret_hex else None
    except ValueError as exc:  # pragma: no cover - caller also validates
        raise VoiceFlowError("device_secret_hex must be valid hex") from exc

    device = new_device(master_key=master_key)
    challenge = issue_challenge(device)
    if not verify_response(device, challenge):
        raise VoiceFlowError("ear handshake verification failed")

    session_key = derive_session_key(device, challenge)

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
            "key_id": challenge.get("key_id"),
            "challenge_ts": challenge.get("ts"),
            "session_key_prefix": session_key[:16],
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
