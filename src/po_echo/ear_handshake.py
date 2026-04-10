"""
Ear-Handshake: OS-Independent Device Pairing

Lightweight challenge-response authentication for ear-worn devices.

Design goals:
- OS-independent: No reliance on iOS/Android pairing APIs
- Short-lived session keys: Derive ephemeral keys from challenge
- Continuous authentication: Location, IMU, skin contact signals
- Graceful degradation: High-risk actions downgrade to app confirmation

Flow:
1. Initial pairing: Phone displays QR/ultrasonic challenge
2. Ear device responds with HMAC signature
3. Phone verifies signature, issues session key
4. Session key expires after N minutes (default: 5)
5. Re-authentication: New challenge or downgrade risk level

Use case:
- User wears ear device (Sweetpea)
- Device pairs with phone via challenge-response
- Voice actions use session key for authentication
- If session expires during high-risk action, force app confirmation
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time

DEVICE_SECRET_LEN_BYTES = 32


def _validate_device_secret(master_key: bytes) -> None:
    """Validate ear-device master key shape.

    Security rationale:
    - A fixed-width secret prevents accidental weak key material (empty/short)
      from entering the handshake path.
    - Fail-closed validation keeps malformed caller input from silently
      downgrading authentication integrity.
    """
    if not isinstance(master_key, bytes):
        raise TypeError("device master_key must be bytes")
    if len(master_key) != DEVICE_SECRET_LEN_BYTES:
        raise ValueError(
            f"device master_key must be {DEVICE_SECRET_LEN_BYTES} bytes, got {len(master_key)}"
        )


def new_device(master_key: bytes | None = None) -> dict:
    """
    Create new device identity.

    Args:
        master_key: Device secret (32 bytes). If None, generates random secret.

    Returns:
        Device dict with key_id and device_secret
    """
    if master_key is not None:
        _validate_device_secret(master_key)

    return {
        "key_id": "v1",
        "device_secret": master_key or os.urandom(32),
    }


def issue_challenge(device: dict) -> dict:
    """
    Issue challenge for device authentication.

    Args:
        device: Device dict from new_device()

    Returns:
        Challenge dict with nonce, timestamp, and HMAC signature

    Protocol:
        1. Generate random nonce (16 bytes)
        2. Get current timestamp
        3. Compute HMAC-SHA256(device_secret, nonce || timestamp)
        4. Return challenge with signature
    """
    nonce = os.urandom(16)
    ts = int(time.time())
    msg = nonce + ts.to_bytes(8, "big")
    sig = hmac.new(device["device_secret"], msg, hashlib.sha256).digest()
    return {
        "nonce": nonce.hex(),
        "ts": ts,
        "sig_hex": sig.hex(),
        "key_id": device.get("key_id", "v1"),
    }


def verify_response(device: dict, challenge: dict) -> bool:
    """
    Verify challenge response from device.

    Args:
        device: Device dict with device_secret
        challenge: Challenge dict from issue_challenge()

    Returns:
        True if signature is valid and timestamp is recent (< 60s old)

    Security notes:
        - Timestamp prevents replay attacks
        - HMAC comparison is constant-time (timing-attack resistant)
        - 60-second window allows for network latency
    """
    nonce = bytes.fromhex(challenge["nonce"])
    ts = int(challenge["ts"])

    # Check timestamp freshness (prevent replay)
    if abs(int(time.time()) - ts) > 60:
        return False

    # Recompute signature
    msg = nonce + ts.to_bytes(8, "big")
    sig = hmac.new(device["device_secret"], msg, hashlib.sha256).digest().hex()

    # Constant-time comparison
    return hmac.compare_digest(sig, challenge["sig_hex"])


def derive_session_key(device: dict, challenge: dict) -> str:
    """
    Derive ephemeral session key from challenge.

    Args:
        device: Device dict with device_secret
        challenge: Challenge dict from issue_challenge()

    Returns:
        Session key (hex-encoded, 64 chars)

    Session key properties:
        - Unique per challenge (nonce-based)
        - Short-lived (expires with challenge timestamp + TTL)
        - Derived from device secret (no transmission)

    Usage:
        session_key = derive_session_key(device, challenge)
        # Use session_key for next 5 minutes
        # After expiry, re-authenticate with new challenge
    """
    nonce = bytes.fromhex(challenge["nonce"])
    material = nonce + device["device_secret"]
    return hmac.new(device["device_secret"], material, hashlib.sha256).hexdigest()
