"""
Echo Mark - Signed badge for recommendation audits

HMAC-SHA256 and Ed25519 based signing system for audit results.
Provides tamper-evident badges: ECHO_VERIFIED, ECHO_CHECK, ECHO_BLOCKED

Schema versions:
- v1: Single secret (ECHO_MARK_SECRET)
- v2: Multi-key support with key_id (ECHO_MARK_KEYS, ECHO_MARK_ACTIVE_KEY_ID)
- v3: Ed25519 + HMAC dual signature (Phase 2 migration)
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
import warnings
from pathlib import Path
from typing import Any, cast

try:
    from nacl.encoding import HexEncoder
    from nacl.exceptions import BadSignatureError
    from nacl.signing import SigningKey, VerifyKey

    NACL_AVAILABLE = True
except ImportError:
    NACL_AVAILABLE = False


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
    store: dict[str, str] = {}
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


# ================================================================================
# Ed25519 Signature Functions (Phase 2: Dual Signature)
# ================================================================================


def load_ed25519_keypair(key_id: str, keys_dir: Path | str = ".keys") -> dict[str, str]:
    """
    Load Ed25519 keypair from files.

    Args:
        key_id: Key identifier (e.g., "v1", "v2")
        keys_dir: Directory containing keypair files

    Returns:
        {
            "key_id": str,
            "private_key": str (hex-encoded),
            "public_key": str (hex-encoded)
        }

    Raises:
        FileNotFoundError: If keypair files not found
        RuntimeError: If PyNaCl not installed
    """
    if not NACL_AVAILABLE:
        raise RuntimeError("PyNaCl not installed. Run: pip install pynacl")

    keys_path = Path(keys_dir)
    private_file = keys_path / f"{key_id}.private.key"
    public_file = keys_path / f"{key_id}.public.key"

    if not private_file.exists():
        raise FileNotFoundError(f"Private key not found: {private_file}")
    if not public_file.exists():
        raise FileNotFoundError(f"Public key not found: {public_file}")

    private_key = private_file.read_text().strip()
    public_key = public_file.read_text().strip()

    return {
        "key_id": key_id,
        "private_key": private_key,
        "public_key": public_key,
    }


def load_ed25519_private_key_from_env() -> str | None:
    """
    Load Ed25519 private key from environment variable.

    Returns:
        Private key (hex-encoded) or None if not set
    """
    return os.getenv("ECHO_MARK_PRIVATE_KEY")


def load_ed25519_public_key_from_env() -> str | None:
    """
    Load Ed25519 public key from environment variable.

    Returns:
        Public key (hex-encoded) or None if not set
    """
    return os.getenv("ECHO_MARK_PUBLIC_KEY")


def sign_ed25519(payload_hash: str, private_key_hex: str) -> str:
    """
    Sign payload hash with Ed25519 private key.

    Args:
        payload_hash: SHA-256 hash (hex-encoded)
        private_key_hex: Ed25519 private key (hex-encoded 32 bytes)

    Returns:
        Signature (hex-encoded 64 bytes)

    Raises:
        RuntimeError: If PyNaCl not installed
    """
    if not NACL_AVAILABLE:
        raise RuntimeError("PyNaCl not installed. Run: pip install pynacl")

    private_key = SigningKey(private_key_hex, encoder=HexEncoder)
    signed = private_key.sign(payload_hash.encode("utf-8"))
    return str(signed.signature.hex())


def verify_ed25519(payload_hash: str, signature_hex: str, public_key_hex: str) -> bool:
    """
    Verify Ed25519 signature.

    Args:
        payload_hash: SHA-256 hash (hex-encoded)
        signature_hex: Ed25519 signature (hex-encoded 64 bytes)
        public_key_hex: Ed25519 public key (hex-encoded 32 bytes)

    Returns:
        True if signature is valid, False otherwise

    Raises:
        RuntimeError: If PyNaCl not installed
    """
    if not NACL_AVAILABLE:
        raise RuntimeError("PyNaCl not installed. Run: pip install pynacl")

    try:
        public_key = VerifyKey(public_key_hex, encoder=HexEncoder)
        signature = bytes.fromhex(signature_hex)
        public_key.verify(payload_hash.encode("utf-8"), signature)
        return True
    except (BadSignatureError, ValueError):
        return False


def make_echo_mark_ed25519(
    audit: dict[str, Any],
    private_key_hex: str,
    key_id: str,
    run_id: str | None = None,
    audience: str | None = None,
) -> dict[str, Any]:
    """
    Generate Echo Mark badge with Ed25519 signature (Phase 2).

    Args:
        audit: Audit result with responsibility_boundary
        private_key_hex: Ed25519 private key (hex-encoded)
        key_id: Key identifier (e.g., "v1")
        run_id: Optional run identifier
        audience: Optional audience restriction

    Returns:
        Echo Mark badge with Ed25519 signature (schema_version: "echo_mark_v3")

    Raises:
        RuntimeError: If PyNaCl not installed
    """
    if not NACL_AVAILABLE:
        raise RuntimeError("PyNaCl not installed. Run: pip install pynacl")

    # Load private key and derive public key
    private_key = SigningKey(private_key_hex, encoder=HexEncoder)
    public_key = private_key.verify_key

    # Build payload (same as v2)
    payload = build_payload(audit, run_id=run_id, key_id=key_id, audience=audience)

    # Compute payload hash
    canon = canonical_json(payload)
    payload_hash = sha256_hex(canon)

    # Sign with Ed25519
    signature = sign_ed25519(payload_hash, private_key_hex)

    # Build badge
    label = payload["label"]
    badge = {
        "schema_version": "echo_mark_v3",
        "verification_method": "Ed25519",
        "label": label,
        "badge_text": badge_text(label),
        "payload": payload,
        "payload_hash": payload_hash,
        "signature": signature,
        "public_key": public_key.encode(HexEncoder).decode(),
        "short": {
            "bias_original": payload["signals"]["bias_original"],
            "bias_final": payload["signals"]["bias_final"],
            "bias_improvement": payload["signals"]["bias_improvement"],
            "reasons": payload["reasons"],
            "key_id": key_id,
            "verification_method": "Ed25519",
        },
    }

    return badge


def make_echo_mark_dual(
    audit: dict[str, Any],
    hmac_secret: str,
    ed25519_private_key: str,
    key_id: str,
    run_id: str | None = None,
    audience: str | None = None,
) -> dict[str, Any]:
    """
    Generate Echo Mark badge with DUAL signatures (HMAC + Ed25519).

    This is Phase 2 of the migration strategy. The badge includes both:
    - HMAC signature (backward compatibility)
    - Ed25519 signature (public verification)

    Args:
        audit: Audit result with responsibility_boundary
        hmac_secret: HMAC secret key
        ed25519_private_key: Ed25519 private key (hex-encoded)
        key_id: Key identifier (e.g., "v1")
        run_id: Optional run identifier
        audience: Optional audience restriction

    Returns:
        Echo Mark badge with dual signatures (schema_version: "echo_mark_v3")

    Raises:
        RuntimeError: If PyNaCl not installed
    """
    if not NACL_AVAILABLE:
        raise RuntimeError("PyNaCl not installed. Run: pip install pynacl")

    # Load private key and derive public key
    private_key = SigningKey(ed25519_private_key, encoder=HexEncoder)
    public_key = private_key.verify_key

    # Build payload
    payload = build_payload(audit, run_id=run_id, key_id=key_id, audience=audience)

    # Compute payload hash
    canon = canonical_json(payload)
    payload_hash = sha256_hex(canon)

    # Generate both signatures
    hmac_sig = hmac_sha256_hex(hmac_secret, payload_hash)
    ed25519_sig = sign_ed25519(payload_hash, ed25519_private_key)

    # Build badge
    label = payload["label"]
    badge = {
        "schema_version": "echo_mark_v3",
        "verification_method": "Ed25519+HMAC",  # Dual mode
        "label": label,
        "badge_text": badge_text(label),
        "payload": payload,
        "payload_hash": payload_hash,
        "signature": ed25519_sig,  # Primary (Ed25519)
        "signature_hmac": hmac_sig,  # Fallback (HMAC)
        "public_key": public_key.encode(HexEncoder).decode(),
        "short": {
            "bias_original": payload["signals"]["bias_original"],
            "bias_final": payload["signals"]["bias_final"],
            "bias_improvement": payload["signals"]["bias_improvement"],
            "reasons": payload["reasons"],
            "key_id": key_id,
            "verification_method": "Ed25519+HMAC",
        },
    }

    return badge


def verify_echo_mark_ed25519(badge: dict[str, Any]) -> dict[str, Any]:
    """
    Verify Echo Mark badge with Ed25519 signature.

    Anyone can call this function - no secret needed!

    Args:
        badge: Echo Mark badge with Ed25519 signature

    Returns:
        {
            "status": "VERIFIED" | "UNVERIFIED" | "INVALID",
            "reason": str,
            "checks": {
                "hash_integrity": bool,
                "signature_valid": bool,
                "schema_valid": bool,
                "timestamp_valid": bool,
            }
        }
    """
    if not NACL_AVAILABLE:
        return {
            "status": "UNVERIFIED",
            "reason": "pynacl_not_installed",
            "checks": {
                "hash_integrity": False,
                "signature_valid": False,
                "schema_valid": False,
                "timestamp_valid": False,
            },
            "note": "PyNaCl not installed. Run: pip install pynacl",
        }

    try:
        # Extract fields
        public_key_hex = badge.get("public_key")
        payload = badge.get("payload")
        payload_hash = badge.get("payload_hash")
        signature_hex = badge.get("signature")

        if not all([public_key_hex, payload, payload_hash, signature_hex]):
            return {
                "status": "INVALID",
                "reason": "missing_required_fields",
                "checks": {
                    "hash_integrity": False,
                    "signature_valid": False,
                    "schema_valid": False,
                    "timestamp_valid": False,
                },
            }

        # Check 1: Hash integrity
        canonical = canonical_json(cast(dict[str, Any], payload))
        expected_hash = sha256_hex(canonical)
        hash_ok = hmac.compare_digest(cast(str, payload_hash), expected_hash)

        if not hash_ok:
            return {
                "status": "INVALID",
                "reason": "payload_tampered",
                "checks": {
                    "hash_integrity": False,
                    "signature_valid": False,
                    "schema_valid": True,
                    "timestamp_valid": False,
                },
            }

        # Check 2: Signature verification
        signature_ok = verify_ed25519(cast(str, payload_hash), cast(str, signature_hex), cast(str, public_key_hex))

        if not signature_ok:
            return {
                "status": "INVALID",
                "reason": "signature_invalid",
                "checks": {
                    "hash_integrity": True,
                    "signature_valid": False,
                    "schema_valid": True,
                    "timestamp_valid": False,
                },
            }

        # Check 3: Timestamp validation (replay attack mitigation)
        timestamp_ok, timestamp_reason = validate_timestamp(cast(dict[str, Any], payload).get("issued_at"))

        # All checks passed!
        return {
            "status": "VERIFIED",
            "reason": "signature_valid",
            "checks": {
                "hash_integrity": True,
                "signature_valid": True,
                "schema_valid": True,
                "timestamp_valid": timestamp_ok,
            },
            "timestamp_warning": None if timestamp_ok else timestamp_reason,
            "note": "Cryptographically verified with Ed25519 public key.",
        }

    except Exception as e:
        return {
            "status": "INVALID",
            "reason": f"verification_error: {str(e)}",
            "checks": {
                "hash_integrity": False,
                "signature_valid": False,
                "schema_valid": False,
                "timestamp_valid": False,
            },
        }


def verify_echo_mark_dual(
    badge: dict[str, Any],
    hmac_secret: str | None = None,
    key_store: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Verify Echo Mark badge with dual signature support (Ed25519 + HMAC).

    Priority:
    1. Try Ed25519 verification first (preferred, public verification)
    2. Fallback to HMAC verification (if secret available)

    Args:
        badge: Echo Mark badge
        hmac_secret: HMAC secret (optional, for fallback)
        key_store: Key store for HMAC v2 (optional)

    Returns:
        {
            "status": "VERIFIED" | "UNVERIFIED" | "INVALID",
            "reason": str,
            "verification_method": "Ed25519" | "HMAC" | None,
            ...
        }
    """
    # Try Ed25519 first (if available)
    if "signature" in badge and "public_key" in badge:
        result = verify_echo_mark_ed25519(badge)
        if result["status"] == "VERIFIED":
            result["verification_method"] = "Ed25519"
            return result
        if result["status"] == "INVALID":
            # Ed25519 failed, try HMAC fallback
            pass

    # Fallback to HMAC (if secret available)
    if hmac_secret or "signature_hmac" in badge:
        payload = badge.get("payload")
        payload_hash = badge.get("payload_hash")
        signature_hmac = badge.get("signature_hmac")

        if all([payload, payload_hash, signature_hmac]):
            hmac_ok = verify_mark(cast(dict[str, Any], payload), cast(str, payload_hash), cast(str, signature_hmac), hmac_secret, key_store)
            if hmac_ok:
                # Timestamp validation
                timestamp_ok, timestamp_reason = validate_timestamp(cast(dict[str, Any], payload).get("issued_at"))

                return {
                    "status": "VERIFIED",
                    "reason": "hmac_signature_valid",
                    "verification_method": "HMAC",
                    "checks": {
                        "hash_integrity": True,
                        "signature_valid": True,
                        "schema_valid": True,
                        "timestamp_valid": timestamp_ok,
                    },
                    "timestamp_warning": None if timestamp_ok else timestamp_reason,
                    "note": "Verified with HMAC (symmetric cryptography). Ed25519 verification failed or not available.",
                }

    # If Ed25519 verification failed but HMAC not available
    if hmac_secret is None and "signature_hmac" not in badge:
        return {
            "status": "UNVERIFIED",
            "reason": "no_secret_for_hmac_fallback",
            "verification_method": None,
            "checks": {
                "hash_integrity": False,
                "signature_valid": False,
                "schema_valid": True,
                "timestamp_valid": False,
            },
            "note": "Ed25519 verification failed and no HMAC secret available for fallback.",
        }

    return {
        "status": "INVALID",
        "reason": "all_verification_methods_failed",
        "verification_method": None,
        "checks": {
            "hash_integrity": False,
            "signature_valid": False,
            "schema_valid": False,
            "timestamp_valid": False,
        },
    }


def validate_timestamp(
    issued_at: str | None,
    max_age_days: int = 30,
) -> tuple[bool, str | None]:
    """
    Validate timestamp for replay attack mitigation.

    Args:
        issued_at: ISO8601 timestamp
        max_age_days: Maximum age in days (default: 30)

    Returns:
        (is_valid, warning_message)
    """
    if not issued_at:
        return False, "missing_timestamp"

    try:
        issued_time = dt.datetime.fromisoformat(issued_at.replace("Z", "+00:00"))
        now = dt.datetime.now(dt.UTC)
        age = now - issued_time

        if age.days > max_age_days:
            return False, f"badge_expired (age: {age.days} days, max: {max_age_days} days)"

        if age.total_seconds() < 0:
            return False, "timestamp_in_future"

        return True, None

    except (ValueError, AttributeError) as e:
        return False, f"invalid_timestamp_format: {str(e)}"


# ================================================================================
# Public Key Registry
# ================================================================================


def load_public_key_registry(registry_path: Path | str = ".keys/registry.json") -> dict[str, Any]:
    """
    Load public key registry from JSON file.

    Args:
        registry_path: Path to registry JSON file

    Returns:
        Registry dict with "keys" list

    Raises:
        FileNotFoundError: If registry file not found
    """
    registry_file = Path(registry_path)

    if not registry_file.exists():
        raise FileNotFoundError(f"Public key registry not found: {registry_file}")

    with open(registry_file) as f:
        return cast(dict[str, Any], json.load(f))


def get_public_key_from_registry(
    key_id: str,
    registry_path: Path | str = ".keys/registry.json",
) -> str | None:
    """
    Get public key from registry by key_id.

    Args:
        key_id: Key identifier (e.g., "v1")
        registry_path: Path to registry JSON file

    Returns:
        Public key (hex-encoded) or None if not found
    """
    try:
        registry = load_public_key_registry(registry_path)
        for key_entry in registry.get("keys", []):
            if key_entry.get("key_id") == key_id:
                # Check if key is active
                status = key_entry.get("status", "active")
                if status == "revoked":
                    warnings.warn(
                        f"Key '{key_id}' is revoked in registry",
                        UserWarning,
                        stacklevel=2,
                    )
                    return None

                return cast("str | None", key_entry.get("public_key"))

        return None

    except FileNotFoundError:
        return None


def generate_echo_mark(
    payload: dict[str, Any],
    device: str = "",
    extra_text: str = "",
) -> dict[str, Any]:
    """
    Generate an unsigned Echo Mark for the given payload (gumdrop/no-secret form).

    Args:
        payload: Audit payload dict
        device: Device type hint (e.g. "gumdrop")
        extra_text: Additional text for display

    Returns:
        Echo Mark dict (unsigned)
    """
    return make_echo_mark(audit=payload)


def verify_key_in_registry(
    key_id: str,
    public_key: str,
    registry_path: Path | str = ".keys/registry.json",
) -> tuple[bool, str]:
    """
    Verify that public key matches registry entry.

    Args:
        key_id: Key identifier
        public_key: Public key to verify (hex-encoded)
        registry_path: Path to registry JSON file

    Returns:
        (is_valid, reason)
    """
    try:
        registry_key = get_public_key_from_registry(key_id, registry_path)

        if registry_key is None:
            return False, "key_not_found_in_registry"

        if registry_key != public_key:
            return False, "public_key_mismatch"

        return True, "key_verified"

    except FileNotFoundError:
        return False, "registry_not_found"
