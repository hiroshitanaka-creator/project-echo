"""
Echo Mark - Signed badge for recommendation audits

HMAC-SHA256 based signing system for audit results.
Provides tamper-evident badges: ECHO_VERIFIED, ECHO_CHECK, ECHO_BLOCKED
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime
from typing import Any


def canonical_json(obj: dict[str, Any]) -> str:
    """
    Deterministic JSON (canonical-ish):
    - sorted keys
    - no whitespace
    - ensure_ascii=False
    """
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(s: str) -> str:
    """SHA256 hash of string, return hex digest."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def hmac_sha256_hex(secret: str, message_hex: str) -> str:
    """
    HMAC(secret, payload_hash_hex) -> signature hex
    """
    return hmac.new(secret.encode("utf-8"), message_hex.encode("utf-8"), hashlib.sha256).hexdigest()


def label_from_boundary(boundary: dict[str, Any]) -> str:
    """Determine Echo Mark label from responsibility boundary."""
    allowed = bool(boundary.get("execution_allowed", False))
    confirm = bool(boundary.get("requires_human_confirm", True))
    if not allowed:
        return "ECHO_BLOCKED"
    if confirm:
        return "ECHO_CHECK"
    return "ECHO_VERIFIED"


def badge_text(label: str) -> str:
    """Human-readable badge text for label."""
    if label == "ECHO_VERIFIED":
        return "ECHO VERIFIED — low bias"
    if label == "ECHO_CHECK":
        return "ECHO CHECK — human confirm"
    return "ECHO BLOCKED — high risk/bias"


def build_payload(audit: dict[str, Any], run_id: str | None = None) -> dict[str, Any]:
    """
    Build minimal payload for signing.

    Extracts essential signals from audit result for tamper-evident signing.
    """
    boundary = audit.get("responsibility_boundary") or {}
    label = label_from_boundary(boundary)

    # pull minimal signals (robust to missing keys)
    signals = boundary.get("signals") or {}

    payload = {
        "schema_version": "echo_mark_v1",
        "timestamp": datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "label": label,
        "policy": {
            "ai_recommends": False,
            "liability_mode": (boundary.get("liability_mode") or "audit-only"),
        },
        "signals": {
            # boundary signals (preferred)
            "bias_original": float(
                signals.get(
                    "bias_original",
                    audit.get("commercial_bias_original", {}).get("overall_bias_score", 0.0) or 0.0,
                )
            ),
            "bias_final": float(
                signals.get(
                    "bias_final",
                    audit.get("commercial_bias_final", {}).get("overall_bias_score", 0.0) or 0.0,
                )
            ),
            "bias_improvement": float(signals.get("bias_improvement", 0.0) or 0.0),
            "merchants_final": int(signals.get("merchants_final", 0) or 0),
            "price_buckets_final": int(signals.get("price_buckets_final", 0) or 0),
        },
        "reasons": list(boundary.get("reasons") or []),
        "run_id": run_id or audit.get("run_id") or audit.get("id") or None,
    }
    return payload


def sign_mark(payload: dict[str, Any], secret: str) -> tuple[str, str]:
    """
    Sign payload with HMAC-SHA256.

    Returns:
        (payload_hash_hex, signature_hex)
    """
    canon = canonical_json(payload)
    payload_hash = sha256_hex(canon)
    sig = hmac_sha256_hex(secret, payload_hash)
    return payload_hash, sig


def verify_mark(payload: dict[str, Any], payload_hash: str, signature: str, secret: str) -> bool:
    """
    Verify Echo Mark signature.

    Returns:
        True if signature is valid, False otherwise
    """
    canon = canonical_json(payload)
    computed_hash = sha256_hex(canon)
    if computed_hash != payload_hash:
        return False
    computed_sig = hmac_sha256_hex(secret, payload_hash)
    # constant-time compare
    return hmac.compare_digest(computed_sig, signature)


def make_echo_mark(audit: dict[str, Any], secret: str, run_id: str | None = None) -> dict[str, Any]:
    """
    Generate Echo Mark badge from audit result.

    Args:
        audit: Audit result with responsibility_boundary
        secret: HMAC secret key
        run_id: Optional run identifier

    Returns:
        Complete Echo Mark with signature
    """
    payload = build_payload(audit, run_id=run_id)
    payload_hash, sig = sign_mark(payload, secret)

    label = payload["label"]
    out = {
        "schema_version": "echo_mark_v1",
        "label": label,
        "badge_text": badge_text(label),
        "payload": payload,
        "payload_hash": payload_hash,
        "signature": sig,
        "short": {
            "bias_original": payload["signals"]["bias_original"],
            "bias_final": payload["signals"]["bias_final"],
            "bias_improvement": payload["signals"]["bias_improvement"],
            "reasons": payload["reasons"],
        },
    }
    return out


def get_secret_from_env() -> str:
    """
    Get ECHO_MARK_SECRET from environment.

    Raises:
        RuntimeError: If secret not set or too short
    """
    secret = os.getenv("ECHO_MARK_SECRET", "")
    if not secret:
        raise RuntimeError("ECHO_MARK_SECRET is not set")
    if len(secret) < 16:
        # 最小限の安全策（短すぎる秘密鍵は事故る）
        raise RuntimeError("ECHO_MARK_SECRET is too short (min 16 chars recommended)")
    return secret
