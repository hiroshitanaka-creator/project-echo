"""Echo Mark v3 payload construction and signature generation."""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import secrets
from typing import Any, cast

from po_echo.echo_mark_registry import (
    get_active_key_id,
    get_ed25519_private_store,
    get_key_store,
)

UTC = getattr(dt, "UTC", dt.timezone.utc)

try:
    from nacl.encoding import HexEncoder
    from nacl.signing import SigningKey

    NACL_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on environment
    NACL_AVAILABLE = False


def canonical_json(obj: dict[str, Any]) -> str:
    """Return deterministic JSON text."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(s: str) -> str:
    """Return SHA-256 hex digest for UTF-8 input text."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def hmac_sha256_hex(secret: str, message_hex: str) -> str:
    """Return HMAC-SHA256 hex digest."""
    return hmac.new(secret.encode("utf-8"), message_hex.encode("utf-8"), hashlib.sha256).hexdigest()


def label_from_boundary(boundary: dict[str, Any]) -> str:
    """Derive Echo Mark label from responsibility boundary."""
    allowed = bool(boundary.get("execution_allowed", False))
    confirm = bool(boundary.get("requires_human_confirm", True))
    if not allowed:
        return "ECHO_BLOCKED"
    if confirm:
        return "ECHO_CHECK"
    return "ECHO_VERIFIED"


def badge_text(label: str) -> str:
    """Map internal label to user-facing display string."""
    mapping = {
        "ECHO_VERIFIED": "ECHO VERIFIED — low bias",
        "ECHO_CHECK": "ECHO CHECK — human confirm",
        "ECHO_BLOCKED": "ECHO BLOCKED — high risk/bias",
    }
    return mapping.get(label, mapping["ECHO_BLOCKED"])


def _utc_now() -> dt.datetime:
    return dt.datetime.now(UTC)


def _now_iso_seconds() -> str:
    return _utc_now().isoformat(timespec="seconds")


def _extract_semantic_evidence(audit: dict[str, Any]) -> dict[str, Any] | None:
    semantic_evidence = audit.get("semantic_evidence")
    if isinstance(semantic_evidence, dict):
        return semantic_evidence
    return None


def build_payload(
    audit: dict[str, Any],
    run_id: str | None = None,
    key_id: str | None = None,
    audience: str | None = None,
    nonce: str | None = None,
    issued_at: str | None = None,
) -> dict[str, Any]:
    """Build Echo Mark v3 payload."""
    boundary = cast(dict[str, Any], audit.get("responsibility_boundary") or {})
    signals = cast(dict[str, Any], boundary.get("signals") or {})

    payload: dict[str, Any] = {
        "schema_version": "echo_mark_v3",
        "key_id": key_id or get_active_key_id(),
        "issued_at": issued_at or _now_iso_seconds(),
        "nonce": nonce or secrets.token_hex(16),
        "label": label_from_boundary(boundary),
        "policy": {
            "ai_recommends": False,
            "liability_mode": str(boundary.get("liability_mode") or "audit-only"),
            "schema_version": str(boundary.get("schema_version") or "1.0"),
        },
        "signals": {
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

    if audience:
        payload["audience"] = audience

    semantic_evidence = _extract_semantic_evidence(audit)
    if semantic_evidence is not None:
        payload["semantic_evidence"] = semantic_evidence

    return payload


def sign_mark(payload: dict[str, Any], secret: str) -> tuple[str, str]:
    """Sign payload using HMAC-SHA256 and return (payload_hash, signature)."""
    payload_hash = sha256_hex(canonical_json(payload))
    return payload_hash, hmac_sha256_hex(secret, payload_hash)


def _ed25519_sign(payload_hash: str, private_key_hex: str) -> str:
    if not NACL_AVAILABLE:
        raise RuntimeError("PyNaCl not installed")
    signer = SigningKey(private_key_hex.encode(), encoder=HexEncoder)
    return str(signer.sign(payload_hash.encode("utf-8")).signature.hex())


def _derive_public_key(private_key_hex: str) -> str | None:
    if not NACL_AVAILABLE:
        return None
    try:
        signing_key = SigningKey(private_key_hex.encode(), encoder=HexEncoder)
        return signing_key.verify_key.encode(HexEncoder).decode()
    except Exception:
        return None


def _resolve_ed_keys(key_id: str, private_key_override: str | None = None) -> tuple[str | None, str | None]:
    if not NACL_AVAILABLE:
        return None, None

    candidate_private = private_key_override
    if not candidate_private:
        private_store = get_ed25519_private_store()
        candidate_private = private_store.get(key_id) or private_store.get("default")

    if not candidate_private:
        return None, None

    return candidate_private, _derive_public_key(candidate_private)


def _build_short_view(payload: dict[str, Any], key_id: str, method: str | None = None) -> dict[str, Any]:
    short = {
        "bias_original": payload["signals"]["bias_original"],
        "bias_final": payload["signals"]["bias_final"],
        "bias_improvement": payload["signals"]["bias_improvement"],
        "reasons": payload["reasons"],
        "key_id": key_id,
    }
    if method:
        short["verification_method"] = method
    return short


def make_echo_mark_dual(
    audit: dict[str, Any],
    hmac_secret: str,
    ed25519_private_key: str,
    key_id: str,
    run_id: str | None = None,
    audience: str | None = None,
) -> dict[str, Any]:
    """Create explicit dual-signature Echo Mark badge."""
    if not NACL_AVAILABLE:
        raise RuntimeError("PyNaCl not installed. Run: pip install pynacl")

    payload = build_payload(audit, run_id=run_id, key_id=key_id, audience=audience)
    payload_hash, signature_hmac = sign_mark(payload, hmac_secret)
    signature_ed25519 = _ed25519_sign(payload_hash, ed25519_private_key)
    public_key = _derive_public_key(ed25519_private_key)

    label = str(payload["label"])
    return {
        "schema_version": "echo_mark_v3",
        "verification_method": "Ed25519+HMAC",
        "label": label,
        "badge_text": badge_text(label),
        "payload": payload,
        "payload_hash": payload_hash,
        "signature": signature_ed25519,
        "signature_hmac": signature_hmac,
        "public_key": public_key,
        "short": _build_short_view(payload, key_id=key_id, method="Ed25519+HMAC"),
    }


def make_echo_mark(
    audit: dict[str, Any],
    secret: str | None = None,
    run_id: str | None = None,
    key_id: str | None = None,
    audience: str | None = None,
) -> dict[str, Any]:
    """Create Echo Mark v3 badge with graceful key fallback behavior."""
    active_key_id = key_id or get_active_key_id()
    payload = build_payload(audit, run_id=run_id, key_id=active_key_id, audience=audience)
    payload_hash = sha256_hex(canonical_json(payload))

    key_store = get_key_store()
    hmac_secret = secret or key_store.get(active_key_id) or key_store.get("default")
    ed_private_key, ed_public_key = _resolve_ed_keys(active_key_id)

    badge: dict[str, Any] = {
        "schema_version": "echo_mark_v3",
        "label": payload["label"],
        "badge_text": badge_text(str(payload["label"])),
        "payload": payload,
        "payload_hash": payload_hash,
        "short": _build_short_view(payload, key_id=active_key_id),
    }

    if hmac_secret:
        badge["signature_hmac"] = hmac_sha256_hex(hmac_secret, payload_hash)

    if ed_private_key and ed_public_key:
        badge["signature"] = _ed25519_sign(payload_hash, ed_private_key)
        badge["public_key"] = ed_public_key
        badge["verification_method"] = "Ed25519+HMAC" if hmac_secret else "Ed25519"
        badge["short"]["verification_method"] = badge["verification_method"]
        return badge

    badge["verification_method"] = "HMAC" if hmac_secret else "UNSIGNED"
    if not hmac_secret:
        badge["error"] = "missing_signing_keys"
    return badge


def make_echo_mark_ed25519(
    audit: dict[str, Any],
    private_key_hex: str,
    key_id: str,
    run_id: str | None = None,
    audience: str | None = None,
) -> dict[str, Any]:
    """Compatibility helper that emits Ed25519-only badge data."""
    if not NACL_AVAILABLE:
        raise RuntimeError("PyNaCl not installed. Run: pip install pynacl")

    payload = build_payload(audit, run_id=run_id, key_id=key_id, audience=audience)
    payload_hash = sha256_hex(canonical_json(payload))
    signature = _ed25519_sign(payload_hash, private_key_hex)
    public_key = _derive_public_key(private_key_hex)

    return {
        "schema_version": "echo_mark_v3",
        "verification_method": "Ed25519",
        "label": payload["label"],
        "badge_text": badge_text(str(payload["label"])),
        "payload": payload,
        "payload_hash": payload_hash,
        "signature": signature,
        "public_key": public_key,
        "short": _build_short_view(payload, key_id=key_id, method="Ed25519"),
    }


def sign_ed25519(payload_hash: str, private_key_hex: str) -> str:
    """Public Ed25519 signing helper."""
    return _ed25519_sign(payload_hash, private_key_hex)


def generate_echo_mark(payload: dict[str, Any], device: str = "", extra_text: str = "") -> dict[str, Any]:
    """Compatibility wrapper used by screenless no-secret paths."""
    _ = (device, extra_text)
    return make_echo_mark(audit=payload)
