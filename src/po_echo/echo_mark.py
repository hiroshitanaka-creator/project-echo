"""
Echo Mark - Signed badge for recommendation audits

HMAC-SHA256 based signing system for audit results.
Provides tamper-evident badges: ECHO_VERIFIED, ECHO_CHECK, ECHO_BLOCKED

Schema versions:
- v1: Single secret (ECHO_MARK_SECRET)
- v2: Multi-key support with key_id (ECHO_MARK_KEYS, ECHO_MARK_ACTIVE_KEY_ID)
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
import warnings
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


def build_payload(
    audit: dict[str, Any],
    run_id: str | None = None,
    key_id: str | None = None,
    audience: str | None = None,
) -> dict[str, Any]:
    """
    Build minimal payload for signing (v2).

    Extracts essential signals from audit result for tamper-evident signing.

    Args:
        audit: Audit result with responsibility_boundary
        run_id: Optional run identifier
        key_id: Key ID for signature (v2 required)
        audience: Optional audience restriction (e.g., "po-cosmic", "report")

    Returns:
        Payload dict with schema_version v2
    """
    boundary = audit.get("responsibility_boundary") or {}
    label = label_from_boundary(boundary)

    # pull minimal signals (robust to missing keys)
    signals = boundary.get("signals") or {}

    issued_at = dt.datetime.now(dt.UTC)

    payload = {
        "schema_version": "echo_mark_v2",
        "key_id": key_id or "default",
        "issued_at": issued_at.isoformat(timespec="seconds"),
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

    # Optional: audience restriction
    if audience:
        payload["audience"] = audience

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


def verify_mark(
    payload: dict[str, Any],
    payload_hash: str,
    signature: str,
    secret: str | None = None,
    key_store: dict[str, str] | None = None,
) -> bool:
    """
    Verify Echo Mark signature (supports v1 and v2).

    Args:
        payload: Badge payload
        payload_hash: Expected hash of canonical payload
        signature: HMAC signature
        secret: Secret for v1 (deprecated, for backward compat)
        key_store: Key store for v2 (key_id -> secret mapping)

    Returns:
        True if signature is valid, False otherwise
    """
    # Check payload hash first
    canon = canonical_json(payload)
    computed_hash = sha256_hex(canon)
    if computed_hash != payload_hash:
        return False

    # Determine schema version
    schema_version = payload.get("schema_version", "echo_mark_v1")

    if schema_version == "echo_mark_v2":
        # v2: Use key_id to lookup secret
        key_id = payload.get("key_id", "default")
        if not key_store:
            key_store = get_key_store()

        if key_id not in key_store:
            warnings.warn(
                f"Echo Mark v2: key_id '{key_id}' not found in key store",
                UserWarning,
                stacklevel=2,
            )
            return False

        secret_to_use = key_store[key_id]

    elif schema_version == "echo_mark_v1":
        # v1: Use provided secret or fall back to env
        if not secret:
            key_store = key_store or get_key_store()
            secret = key_store.get("default")

        if not secret:
            warnings.warn(
                "Echo Mark v1: No secret provided and ECHO_MARK_SECRET not set",
                UserWarning,
                stacklevel=2,
            )
            return False

        warnings.warn(
            "Echo Mark v1 is deprecated, please migrate to v2 with key_id",
            DeprecationWarning,
            stacklevel=2,
        )
        secret_to_use = secret

    else:
        warnings.warn(
            f"Unknown schema_version: {schema_version}",
            UserWarning,
            stacklevel=2,
        )
        return False

    # Verify signature
    computed_sig = hmac_sha256_hex(secret_to_use, payload_hash)
    return hmac.compare_digest(computed_sig, signature)


def make_echo_mark(
    audit: dict[str, Any],
    secret: str | None = None,
    run_id: str | None = None,
    key_id: str | None = None,
    audience: str | None = None,
) -> dict[str, Any]:
    """
    Generate Echo Mark badge from audit result (v2 by default).

    Args:
        audit: Audit result with responsibility_boundary
        secret: HMAC secret key (v1 compat, or single key for v2)
        run_id: Optional run identifier
        key_id: Key ID for v2 (if None, uses ECHO_MARK_ACTIVE_KEY_ID or "default")
        audience: Optional audience restriction

    Returns:
        Complete Echo Mark with signature (v2 schema)
    """
    # Determine key_id and secret
    if key_id is None:
        key_id = get_active_key_id()

    if secret is None:
        # Get from key store
        key_store = get_key_store()
        if key_id not in key_store:
            raise RuntimeError(
                f"key_id '{key_id}' not found in key store. "
                "Set ECHO_MARK_KEYS or ECHO_MARK_SECRET environment variable."
            )
        secret = key_store[key_id]

    # Build v2 payload
    payload = build_payload(audit, run_id=run_id, key_id=key_id, audience=audience)
    payload_hash, sig = sign_mark(payload, secret)

    label = payload["label"]
    out = {
        "schema_version": "echo_mark_v2",
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
            "key_id": key_id,
        },
    }
    return out


def parse_key_store(keys_str: str) -> dict[str, str]:
    """
    Parse ECHO_MARK_KEYS into key_id -> secret mapping.

    Format: "k2026_01=secret1;k2026_02=secret2"

    Returns:
        Dict mapping key_id to secret
    """
    store = {}
    if not keys_str:
        return store

    for part in keys_str.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key_id, secret = part.split("=", 1)
        key_id = key_id.strip()
        secret = secret.strip()
        if key_id and secret:
            store[key_id] = secret
    return store


def get_key_store() -> dict[str, str]:
    """
    Get key store from environment (v2).

    Priority:
    1. ECHO_MARK_KEYS (v2 multi-key)
    2. ECHO_MARK_SECRET (v1 fallback, maps to "default")

    Returns:
        Dict mapping key_id to secret
    """
    store = {}

    # v2: multi-key
    keys_str = os.getenv("ECHO_MARK_KEYS", "")
    if keys_str:
        store = parse_key_store(keys_str)

    # v1 fallback
    v1_secret = os.getenv("ECHO_MARK_SECRET", "")
    if v1_secret:
        store["default"] = v1_secret

    return store


def get_active_key_id() -> str:
    """
    Get active key_id for signing (v2).

    Priority:
    1. ECHO_MARK_ACTIVE_KEY_ID
    2. "default" (v1 fallback)

    Returns:
        key_id to use for signing
    """
    return os.getenv("ECHO_MARK_ACTIVE_KEY_ID", "default")


def get_secret_from_env() -> str:
    """
    Get ECHO_MARK_SECRET from environment (v1 compatibility).

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
