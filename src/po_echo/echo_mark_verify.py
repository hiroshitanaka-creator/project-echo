"""Echo Mark v3 verification and replay-guard utilities."""

from __future__ import annotations

import datetime as dt
import hmac
from pathlib import Path
from typing import Any, TypedDict, cast

from po_echo.echo_mark_core import NACL_AVAILABLE, canonical_json, sha256_hex
from po_echo.echo_mark_registry import (
    find_registry_key_entry,
    get_ed25519_public_store,
    get_key_store,
)

UTC = getattr(dt, "UTC", dt.timezone.utc)

try:
    from nacl.encoding import HexEncoder
    from nacl.exceptions import BadSignatureError
    from nacl.signing import VerifyKey
except ImportError:  # pragma: no cover - depends on environment
    pass


class VerificationChecks(TypedDict):
    """Common verification check shape returned by verification APIs."""

    hash_integrity: bool
    signature_valid: bool
    timestamp_valid: bool
    replay_safe: bool


def verify_mark(
    payload: dict[str, Any],
    payload_hash: str,
    signature: str,
    secret: str | None = None,
    key_store: dict[str, str] | None = None,
) -> bool:
    """Verify HMAC signature against payload and key_id mapping."""
    computed_hash = sha256_hex(canonical_json(payload))
    if not hmac.compare_digest(computed_hash, payload_hash):
        return False

    resolved_secret = secret
    if not resolved_secret:
        store = key_store or get_key_store()
        resolved_secret = store.get(str(payload.get("key_id", "default")))

    if not resolved_secret:
        return False

    expected = hmac.new(
        resolved_secret.encode("utf-8"),
        payload_hash.encode("utf-8"),
        "sha256",
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _ed25519_verify(payload_hash: str, signature_hex: str, public_key_hex: str) -> bool:
    if not NACL_AVAILABLE:
        return False
    try:
        verifier = VerifyKey(public_key_hex.encode(), encoder=HexEncoder)
        verifier.verify(payload_hash.encode("utf-8"), bytes.fromhex(signature_hex))
        return True
    except (BadSignatureError, ValueError, TypeError):
        return False


def validate_timestamp(
    issued_at: str | None,
    now: dt.datetime | None = None,
    max_age_seconds: int = 300,
) -> tuple[bool, str | None]:
    """Validate replay timestamp window."""
    if not issued_at:
        return False, "missing_timestamp"

    try:
        issued_dt = dt.datetime.fromisoformat(issued_at.replace("Z", "+00:00"))
    except Exception as exc:
        return False, f"invalid_timestamp: {exc}"

    current = now or dt.datetime.now(UTC)
    delta_seconds = (current - issued_dt).total_seconds()

    if delta_seconds < 0:
        return False, "timestamp_in_future"
    if delta_seconds > max_age_seconds:
        return False, "timestamp_expired"
    return True, None


def _verification_checks(
    hash_integrity: bool,
    signature_valid: bool,
    timestamp_valid: bool,
    replay_safe: bool,
) -> VerificationChecks:
    return {
        "hash_integrity": hash_integrity,
        "signature_valid": signature_valid,
        "timestamp_valid": timestamp_valid,
        "replay_safe": replay_safe,
    }


def _verification_result(
    status: str,
    reason: str,
    checks: VerificationChecks,
    method: str | None = None,
    key_id: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": status,
        "reason": reason,
        "verification_method": method,
        "checks": checks,
    }
    if key_id is not None:
        result["key_id"] = key_id
    return result


def _resolve_public_key_for_badge(
    badge: dict[str, Any],
    public_keys: dict[str, str] | None,
    registry_path: Path | str = ".keys/registry.json",
) -> tuple[str | None, str | None]:
    """Resolve public key for badge verification.

    Trust resolution order:
    1. Explicit ``public_keys`` map (caller-controlled trust anchor).
       When provided, the inline badge key is intentionally skipped for
       key_ids absent from the map — this prevents self-authenticating badges.
    2. Inline badge public key (only when no explicit map is given).
    3. Environment key store.
    4. File-based key registry.
    """
    payload = cast(dict[str, Any], badge.get("payload") or {})
    key_id = str(payload.get("key_id") or "default")

    if public_keys is not None:
        # Caller supplied an explicit trust store: honour it exclusively.
        # Do NOT fall back to the inline key — that would allow self-signed badges
        # to bypass key-rotation policies.
        if key_id in public_keys:
            return public_keys[key_id], "active"
    else:
        # No explicit trust store: accept the inline key as a convenience fallback.
        inline_public = badge.get("public_key")
        if isinstance(inline_public, str) and inline_public:
            return inline_public, "active"

    env_store = get_ed25519_public_store()
    if key_id in env_store:
        return env_store[key_id], "active"

    entry = find_registry_key_entry(key_id, registry_path=registry_path)
    if not entry:
        return None, None
    status = str(entry.get("status", "active"))
    public_key = entry.get("public_key")
    if not isinstance(public_key, str) or not public_key:
        return None, status
    return public_key, status


def _replay_guard(
    payload: dict[str, Any],
    nonce_cache: set[str] | None,
    now: dt.datetime | None,
    max_age_seconds: int,
) -> tuple[bool, str | None, VerificationChecks]:
    timestamp_ok, timestamp_reason = validate_timestamp(payload.get("issued_at"), now=now, max_age_seconds=max_age_seconds)
    if not timestamp_ok:
        return False, timestamp_reason, _verification_checks(True, False, False, False)

    nonce = str(payload.get("nonce") or "")
    if not nonce:
        return False, "missing_nonce", _verification_checks(True, False, True, False)

    if nonce_cache is not None:
        if nonce in nonce_cache:
            return False, "replay_detected", _verification_checks(True, False, True, False)
        nonce_cache.add(nonce)

    return True, None, _verification_checks(True, False, True, True)


def _resolve_hmac_secret(
    key_id: str,
    hmac_secret: str | None,
    key_store: dict[str, str] | None,
) -> tuple[str | None, dict[str, str]]:
    store = key_store or get_key_store()
    resolved = hmac_secret or store.get(key_id) or store.get("default")
    return resolved, store


def verify_echo_mark(
    badge: dict[str, Any],
    hmac_secret: str | None = None,
    key_store: dict[str, str] | None = None,
    public_keys: dict[str, str] | None = None,
    nonce_cache: set[str] | None = None,
    now: dt.datetime | None = None,
    max_age_seconds: int = 300,
) -> dict[str, Any]:
    """Verify Echo Mark badge with dual-signature and replay protections."""
    try:
        payload = cast(dict[str, Any], badge.get("payload") or {})
        payload_hash = str(badge.get("payload_hash") or "")
        if not payload or not payload_hash:
            return _verification_result(
                "INVALID",
                "missing_payload",
                _verification_checks(False, False, False, False),
            )

        key_id = str(payload.get("key_id") or "default")
        expected_hash = sha256_hex(canonical_json(payload))
        if not hmac.compare_digest(expected_hash, payload_hash):
            return _verification_result(
                "INVALID",
                "payload_tampered",
                _verification_checks(False, False, False, False),
                key_id=key_id,
            )

        replay_ok, replay_reason, replay_checks = _replay_guard(
            payload=payload,
            nonce_cache=nonce_cache,
            now=now,
            max_age_seconds=max_age_seconds,
        )
        if not replay_ok and replay_reason:
            return _verification_result(
                "INVALID",
                replay_reason,
                replay_checks,
                key_id=key_id,
            )

        signature = badge.get("signature")
        if isinstance(signature, str) and signature:
            public_key, key_status = _resolve_public_key_for_badge(badge, public_keys)
            if key_status == "revoked":
                return _verification_result(
                    "INVALID",
                    "key_revoked",
                    _verification_checks(True, False, True, True),
                    key_id=key_id,
                )
            if public_key and _ed25519_verify(payload_hash, signature, public_key):
                return _verification_result(
                    "VERIFIED",
                    "dual_signature_verified",
                    _verification_checks(True, True, True, True),
                    method="Ed25519",
                    key_id=key_id,
                )

        signature_hmac = badge.get("signature_hmac")
        resolved_hmac, resolved_store = _resolve_hmac_secret(key_id, hmac_secret, key_store)
        if isinstance(signature_hmac, str) and resolved_hmac:
            if verify_mark(payload, payload_hash, signature_hmac, secret=resolved_hmac, key_store=resolved_store):
                return _verification_result(
                    "VERIFIED",
                    "hmac_signature_verified",
                    _verification_checks(True, True, True, True),
                    method="HMAC",
                    key_id=key_id,
                )

        return _verification_result(
            "INVALID",
            "signature_invalid",
            _verification_checks(True, False, True, True),
            key_id=key_id,
        )
    except Exception as exc:
        return _verification_result(
            "INVALID",
            f"verification_error: {exc}",
            _verification_checks(False, False, False, False),
        )


def verify_echo_mark_ed25519(badge: dict[str, Any]) -> dict[str, Any]:
    """Compatibility wrapper for Ed25519 verification path."""
    return verify_echo_mark(badge)


def verify_echo_mark_dual(
    badge: dict[str, Any],
    hmac_secret: str | None = None,
    key_store: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Compatibility wrapper for dual-signature verification path."""
    return verify_echo_mark(badge, hmac_secret=hmac_secret, key_store=key_store)


def verify_ed25519(payload_hash: str, signature_hex: str, public_key_hex: str) -> bool:
    """Public Ed25519 verification helper."""
    return _ed25519_verify(payload_hash, signature_hex, public_key_hex)
