"""Echo Mark v3 signing and verification utilities.

This module provides canonical payload construction, dual-signature generation
(HMAC + Ed25519), replay protection, and key-rotation-aware verification.

Design constraints:
- Preserve existing public APIs used by CLI/tests.
- Prefer Ed25519 as primary verification while retaining HMAC fallback.
- Avoid crashes in verification paths; return structured INVALID/VERIFIED results.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from typing import Any, TypedDict, cast

UTC = dt.UTC

try:
    from nacl.encoding import HexEncoder
    from nacl.exceptions import BadSignatureError
    from nacl.signing import SigningKey, VerifyKey

    NACL_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on environment
    NACL_AVAILABLE = False


class VerificationChecks(TypedDict):
    """Common verification check shape returned by verification APIs."""

    hash_integrity: bool
    signature_valid: bool
    timestamp_valid: bool
    replay_safe: bool


def canonical_json(obj: dict[str, Any]) -> str:
    """Return deterministic JSON text.

    Args:
        obj: Source object.

    Returns:
        Canonical JSON string with sorted keys and no insignificant whitespace.
    """
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(s: str) -> str:
    """Return SHA-256 hex digest for UTF-8 input text."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def hmac_sha256_hex(secret: str, message_hex: str) -> str:
    """Return HMAC-SHA256 hex digest.

    Args:
        secret: Shared secret.
        message_hex: Payload hash string.

    Returns:
        HMAC signature as hex.
    """
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
    """Extract semantic evidence map while preserving existing integration."""
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
    """Build Echo Mark v3 payload.

    Args:
        audit: Audit object that includes responsibility boundary and signals.
        run_id: Optional run identifier override.
        key_id: Optional key id override.
        audience: Optional audience lock.
        nonce: Optional nonce override for deterministic tests.
        issued_at: Optional issued-at timestamp override.

    Returns:
        Canonical payload dictionary with ``schema_version='echo_mark_v3'``.
    """
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


def parse_key_store(keys_str: str) -> dict[str, str]:
    """Parse ``key_id=secret;key_id2=secret2`` format."""
    store: dict[str, str] = {}
    for chunk in keys_str.split(";"):
        if "=" not in chunk:
            continue
        key_id, value = chunk.split("=", 1)
        key_id = key_id.strip()
        value = value.strip()
        if key_id and value:
            store[key_id] = value
    return store


def get_key_store() -> dict[str, str]:
    """Load HMAC key store from environment with v1 fallback."""
    store = parse_key_store(os.getenv("ECHO_MARK_KEYS", ""))
    legacy = os.getenv("ECHO_MARK_SECRET", "")
    if legacy:
        store.setdefault("default", legacy)
    return store


def _get_ed25519_private_store() -> dict[str, str]:
    store = parse_key_store(os.getenv("ECHO_MARK_ED25519_PRIVATE_KEYS", ""))
    single = os.getenv("ECHO_MARK_PRIVATE_KEY", "")
    if single:
        store.setdefault("default", single)
    return store


def _get_ed25519_public_store() -> dict[str, str]:
    store = parse_key_store(os.getenv("ECHO_MARK_ED25519_PUBLIC_KEYS", ""))
    single = os.getenv("ECHO_MARK_PUBLIC_KEY", "")
    if single:
        store.setdefault("default", single)
    return store


def get_active_key_id() -> str:
    """Return active key id for signing."""
    return os.getenv("ECHO_MARK_ACTIVE_KEY_ID", "default")


def sign_mark(payload: dict[str, Any], secret: str) -> tuple[str, str]:
    """Sign payload using HMAC-SHA256 and return (payload_hash, signature)."""
    payload_hash = sha256_hex(canonical_json(payload))
    return payload_hash, hmac_sha256_hex(secret, payload_hash)


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

    expected = hmac_sha256_hex(resolved_secret, payload_hash)
    return hmac.compare_digest(expected, signature)


def _ed25519_sign(payload_hash: str, private_key_hex: str) -> str:
    """Sign payload hash with Ed25519.

    Raises:
        RuntimeError: If PyNaCl is unavailable.
        ValueError: If key material is malformed.
    """
    if not NACL_AVAILABLE:
        raise RuntimeError("PyNaCl not installed")
    signer = SigningKey(private_key_hex.encode(), encoder=HexEncoder)
    return signer.sign(payload_hash.encode("utf-8")).signature.hex()


def _ed25519_verify(payload_hash: str, signature_hex: str, public_key_hex: str) -> bool:
    """Verify Ed25519 signature and return boolean validity."""
    if not NACL_AVAILABLE:
        return False
    try:
        verifier = VerifyKey(public_key_hex.encode(), encoder=HexEncoder)
        verifier.verify(payload_hash.encode("utf-8"), bytes.fromhex(signature_hex))
        return True
    except (BadSignatureError, ValueError, TypeError):
        return False


def _derive_public_key(private_key_hex: str) -> str | None:
    """Derive public key from private key hex, returning None on malformed key."""
    if not NACL_AVAILABLE:
        return None
    try:
        signing_key = SigningKey(private_key_hex.encode(), encoder=HexEncoder)
        return signing_key.verify_key.encode(HexEncoder).decode()
    except Exception:
        return None


def _resolve_ed_keys(key_id: str, private_key_override: str | None = None) -> tuple[str | None, str | None]:
    """Resolve Ed25519 private/public key pair for signing by key id."""
    if not NACL_AVAILABLE:
        return None, None

    candidate_private = private_key_override
    if not candidate_private:
        private_store = _get_ed25519_private_store()
        candidate_private = private_store.get(key_id) or private_store.get("default")

    if not candidate_private:
        return None, None

    return candidate_private, _derive_public_key(candidate_private)


def _build_short_view(payload: dict[str, Any], key_id: str, method: str | None = None) -> dict[str, Any]:
    """Build compact display object used across badge variants."""
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
    """Create explicit dual-signature Echo Mark badge.

    Raises:
        RuntimeError: If Ed25519 support is unavailable.
    """
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
    """Create Echo Mark v3 badge with graceful key fallback behavior.

    Ed25519 is preferred when private key material is available. HMAC remains
    for compatibility and migration support.
    """
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
    """Compatibility helper that emits Ed25519-only badge data.

    Raises:
        RuntimeError: If Ed25519 support is unavailable.
    """
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


def validate_timestamp(
    issued_at: str | None,
    now: dt.datetime | None = None,
    max_age_seconds: int = 300,
) -> tuple[bool, str | None]:
    """Validate replay timestamp window.

    Args:
        issued_at: ISO8601 issued-at timestamp.
        now: Optional current time override.
        max_age_seconds: Maximum allowed age.

    Returns:
        ``(is_valid, reason_or_none)``.
    """
    if not issued_at:
        return False, "missing_timestamp"

    try:
        issued_dt = dt.datetime.fromisoformat(issued_at.replace("Z", "+00:00"))
    except Exception as exc:
        return False, f"invalid_timestamp: {exc}"

    current = now or _utc_now()
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
    """Create normalized verification checks payload."""
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
    """Create normalized verification result dictionary."""
    result: dict[str, Any] = {
        "status": status,
        "reason": reason,
        "verification_method": method,
        "checks": checks,
    }
    if key_id is not None:
        result["key_id"] = key_id
    return result


def load_public_key_registry(registry_path: Path | str = ".keys/registry.json") -> dict[str, Any]:
    """Load public key registry JSON from disk.

    Raises:
        FileNotFoundError: When registry file does not exist.
        ValueError: When registry JSON shape is invalid.
    """
    registry_file = Path(registry_path)
    if not registry_file.exists():
        raise FileNotFoundError(f"Public key registry not found: {registry_file}")

    data = json.loads(registry_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("keys"), list):
        raise ValueError("Invalid public key registry format")
    return cast(dict[str, Any], data)


def _find_registry_key_entry(
    key_id: str,
    registry_path: Path | str = ".keys/registry.json",
) -> dict[str, Any] | None:
    """Find registry key entry by key_id with status-aware selection.

    Priority order for same key_id:
    1) active
    2) inactive
    3) revoked (last, because it is non-verifiable)
    """
    try:
        registry = load_public_key_registry(registry_path)
    except (FileNotFoundError, ValueError):
        return None

    entries = [entry for entry in registry.get("keys", []) if isinstance(entry, dict)]
    matches = [entry for entry in entries if entry.get("key_id") == key_id]
    if not matches:
        return None

    status_rank = {"active": 0, "inactive": 1, "revoked": 2}
    matches.sort(key=lambda entry: status_rank.get(str(entry.get("status", "active")), 3))
    return cast(dict[str, Any], matches[0])


def get_public_key_from_registry(
    key_id: str,
    registry_path: Path | str = ".keys/registry.json",
) -> str | None:
    """Return registry public key for key_id if key is not revoked."""
    entry = _find_registry_key_entry(key_id, registry_path=registry_path)
    if not entry:
        return None
    if str(entry.get("status", "active")) == "revoked":
        return None

    public_key = entry.get("public_key")
    if isinstance(public_key, str) and public_key:
        return public_key
    return None


def _resolve_public_key_for_badge(
    badge: dict[str, Any],
    public_keys: dict[str, str] | None,
    registry_path: Path | str = ".keys/registry.json",
) -> tuple[str | None, str | None]:
    """Resolve public key and status for key-id-aware verification."""
    payload = cast(dict[str, Any], badge.get("payload") or {})
    key_id = str(payload.get("key_id") or "default")

    if public_keys and key_id in public_keys:
        return public_keys[key_id], "active"

    inline_public = badge.get("public_key")
    if isinstance(inline_public, str) and inline_public:
        return inline_public, "active"

    env_store = _get_ed25519_public_store()
    if key_id in env_store:
        return env_store[key_id], "active"

    entry = _find_registry_key_entry(key_id, registry_path=registry_path)
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
    """Validate timestamp and nonce replay constraints."""
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
    """Resolve HMAC secret using explicit value, key_store, and env fallback."""
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
    """Verify Echo Mark badge with dual-signature and replay protections.

    Verification order:
    1. Payload hash integrity.
    2. Replay guards (timestamp + nonce).
    3. Ed25519 verification (primary).
    4. HMAC verification (fallback).

    Returns:
        Structured result with status/reason/checks.
    """
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


def verify_key_in_registry(
    key_id: str,
    public_key: str,
    registry_path: Path | str = ".keys/registry.json",
) -> tuple[bool, str]:
    """Verify registry key binding and status.

    Returns:
        ``(is_valid, reason)`` where reason is one of:
        - key_not_found_in_registry
        - key_revoked
        - public_key_mismatch
        - key_verified
    """
    entry = _find_registry_key_entry(key_id, registry_path=registry_path)
    if not entry:
        return False, "key_not_found_in_registry"

    status = str(entry.get("status", "active"))
    if status == "revoked":
        return False, "key_revoked"

    registry_key = entry.get("public_key")
    if not isinstance(registry_key, str) or not hmac.compare_digest(registry_key, public_key):
        return False, "public_key_mismatch"

    return True, "key_verified"


def load_ed25519_keypair(key_id: str, keys_dir: Path | str = ".keys") -> dict[str, str]:
    """Load Ed25519 key pair from key directory files.

    Raises:
        FileNotFoundError: If required key files are missing.
    """
    key_dir = Path(keys_dir)
    private_path = key_dir / f"{key_id}.private.key"
    public_path = key_dir / f"{key_id}.public.key"
    return {
        "key_id": key_id,
        "private_key": private_path.read_text(encoding="utf-8").strip(),
        "public_key": public_path.read_text(encoding="utf-8").strip(),
    }


def load_ed25519_private_key_from_env() -> str | None:
    """Compatibility helper for legacy private key env var."""
    return os.getenv("ECHO_MARK_PRIVATE_KEY")


def load_ed25519_public_key_from_env() -> str | None:
    """Compatibility helper for legacy public key env var."""
    return os.getenv("ECHO_MARK_PUBLIC_KEY")


def sign_ed25519(payload_hash: str, private_key_hex: str) -> str:
    """Public Ed25519 signing helper."""
    return _ed25519_sign(payload_hash, private_key_hex)


def verify_ed25519(payload_hash: str, signature_hex: str, public_key_hex: str) -> bool:
    """Public Ed25519 verification helper."""
    return _ed25519_verify(payload_hash, signature_hex, public_key_hex)


def get_secret_from_env() -> str:
    """Legacy secret loader with minimal guardrails.

    Raises:
        RuntimeError: If secret is missing or too short.
    """
    secret = os.getenv("ECHO_MARK_SECRET", "")
    if not secret:
        raise RuntimeError("ECHO_MARK_SECRET is not set")
    if len(secret) < 16:
        raise RuntimeError("ECHO_MARK_SECRET is too short (min 16 chars recommended)")
    return secret


def generate_echo_mark(payload: dict[str, Any], device: str = "", extra_text: str = "") -> dict[str, Any]:
    """Compatibility wrapper used by screenless no-secret paths."""
    _ = (device, extra_text)
    return make_echo_mark(audit=payload)
