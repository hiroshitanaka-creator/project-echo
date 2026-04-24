"""Ear-handshake: registered-device challenge/response authentication.

Production invariants:
- Trust anchor is server-side registered device secret (never caller-supplied secret).
- Challenge issuance and verification are split phases.
- Challenges are device-bound, expiring, and single-use.
- Session material is derived only after successful verification.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
import uuid
import warnings
from dataclasses import dataclass
from typing import Protocol

DEVICE_SECRET_LEN_BYTES = 32
DEFAULT_CHALLENGE_TTL_SECONDS = 60
DEFAULT_SESSION_TTL_SECONDS = 15 * 60


class EarHandshakeError(RuntimeError):
    """Domain error for ear-handshake verification failures."""


@dataclass(frozen=True)
class TrustedDevice:
    device_id: str
    key_id: str
    device_secret: bytes


@dataclass(frozen=True)
class ChallengeRecord:
    challenge_id: str
    device_id: str
    key_id: str
    nonce: bytes
    issued_at: int
    expires_at: int
    consumed: bool = False


@dataclass(frozen=True)
class VerifiedSession:
    session_id: str
    device_id: str
    key_id: str
    challenge_id: str
    session_key: str
    authenticated_at: int
    expires_at: int


class DeviceRegistry(Protocol):
    def get_device(self, device_id: str) -> TrustedDevice | None: ...


class ChallengeStore(Protocol):
    def put(self, record: ChallengeRecord) -> None: ...

    def get(self, challenge_id: str) -> ChallengeRecord | None: ...

    def mark_consumed(self, challenge_id: str) -> None: ...


class DeviceTrustStore(Protocol):
    def get_device_secret(self, *, device_id: str) -> bytes | None: ...


class InMemoryDeviceRegistry:
    def __init__(self) -> None:
        self._by_id: dict[str, TrustedDevice] = {}

    def register_device(self, *, device_id: str, key_id: str = "v1", device_secret: bytes) -> None:
        _validate_device_secret(device_secret)
        if not device_id:
            raise ValueError("device_id is required")
        self._by_id[device_id] = TrustedDevice(device_id=device_id, key_id=key_id, device_secret=device_secret)

    def get_device(self, device_id: str) -> TrustedDevice | None:
        return self._by_id.get(device_id)


class InMemoryDeviceTrustStore(InMemoryDeviceRegistry):
    """Compatibility trust-store facade backed by registered device records."""

    def get_device_secret(self, *, device_id: str) -> bytes | None:
        device = self.get_device(device_id)
        return device.device_secret if device else None

    def get_key_id(self, *, device_id: str) -> str:
        device = self.get_device(device_id)
        return device.key_id if device else "v1"


class InMemoryChallengeStore:
    def __init__(self) -> None:
        self._by_id: dict[str, ChallengeRecord] = {}

    def put(self, record: ChallengeRecord) -> None:
        self._by_id[record.challenge_id] = record

    def get(self, challenge_id: str) -> ChallengeRecord | None:
        return self._by_id.get(challenge_id)

    def mark_consumed(self, challenge_id: str) -> None:
        record = self._by_id.get(challenge_id)
        if record is None:
            return
        self._by_id[challenge_id] = ChallengeRecord(
            challenge_id=record.challenge_id,
            device_id=record.device_id,
            key_id=record.key_id,
            nonce=record.nonce,
            issued_at=record.issued_at,
            expires_at=record.expires_at,
            consumed=True,
        )

    # Backward compatible names
    def save(self, challenge: ChallengeRecord) -> None:
        self.put(challenge)

    def mark_used(self, *, challenge_id: str) -> None:
        self.mark_consumed(challenge_id)


class EarHandshakeService:
    """Verifier-side service with strict challenge lifecycle and device binding."""

    def __init__(
        self,
        *,
        device_registry: DeviceRegistry,
        challenge_store: ChallengeStore,
        challenge_ttl_seconds: int = DEFAULT_CHALLENGE_TTL_SECONDS,
        session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
        time_fn: callable | None = None,
    ) -> None:
        self._device_registry = device_registry
        self._challenge_store = challenge_store
        self._challenge_ttl_seconds = challenge_ttl_seconds
        self._session_ttl_seconds = session_ttl_seconds
        self._time_fn = time_fn or (lambda: time.time())

    def issue_challenge(self, *, device_id: str) -> dict[str, str | int]:
        device = self._device_registry.get_device(device_id)
        if device is None:
            raise EarHandshakeError("unknown_device")

        now = int(self._time_fn())
        record = ChallengeRecord(
            challenge_id=uuid.uuid4().hex,
            device_id=device.device_id,
            key_id=device.key_id,
            nonce=os.urandom(16),
            issued_at=now,
            expires_at=now + self._challenge_ttl_seconds,
        )
        self._challenge_store.put(record)
        return {
            "challenge_id": record.challenge_id,
            "device_id": record.device_id,
            "key_id": record.key_id,
            "nonce": record.nonce.hex(),
            "issued_at": record.issued_at,
            "ts": record.issued_at,
            "expires_at": record.expires_at,
        }

    def verify_response(self, *, device_id: str, challenge_id: str, response_hex: str) -> VerifiedSession:
        if not challenge_id or not device_id:
            raise EarHandshakeError("malformed_response")

        record = self._challenge_store.get(challenge_id)
        if record is None:
            raise EarHandshakeError("challenge_not_found")
        if record.device_id != device_id:
            raise EarHandshakeError("challenge_device_mismatch")
        if record.consumed:
            raise EarHandshakeError("challenge_already_used")

        now = int(self._time_fn())
        if now > record.expires_at:
            raise EarHandshakeError("challenge_expired")

        device = self._device_registry.get_device(device_id)
        if device is None:
            raise EarHandshakeError("unknown_device")

        try:
            bytes.fromhex(response_hex)
        except ValueError as exc:
            raise EarHandshakeError("malformed_response") from exc

        expected = hmac.new(
            device.device_secret,
            _challenge_message(
                device_id=device.device_id,
                challenge_id=record.challenge_id,
                nonce=record.nonce,
                issued_at=record.issued_at,
            ),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, response_hex):
            raise EarHandshakeError("invalid_response")

        self._challenge_store.mark_consumed(challenge_id)
        session_key = hmac.new(
            device.device_secret,
            b"session|" + _challenge_message(device.device_id, record.challenge_id, record.nonce, record.issued_at),
            hashlib.sha256,
        ).hexdigest()
        return VerifiedSession(
            session_id=uuid.uuid4().hex,
            device_id=device.device_id,
            key_id=device.key_id,
            challenge_id=record.challenge_id,
            session_key=session_key,
            authenticated_at=now,
            expires_at=now + self._session_ttl_seconds,
        )


class EarHandshakeAuthenticator:
    """Compatibility wrapper preserving bool-returning API for existing callers."""

    def __init__(
        self,
        *,
        trust_store: DeviceTrustStore,
        challenge_store: InMemoryChallengeStore,
        challenge_ttl_seconds: int = DEFAULT_CHALLENGE_TTL_SECONDS,
    ) -> None:
        registry = InMemoryDeviceRegistry()
        if isinstance(trust_store, InMemoryDeviceTrustStore):
            registry = trust_store
        else:
            raise ValueError("trust_store must be InMemoryDeviceTrustStore for this runtime")

        self._service = EarHandshakeService(
            device_registry=registry,
            challenge_store=challenge_store,
            challenge_ttl_seconds=challenge_ttl_seconds,
        )

    def issue_challenge(self, *, device_id: str) -> dict[str, str | int]:
        return self._service.issue_challenge(device_id=device_id)

    def verify_response(self, *, device_id: str, challenge: dict, response_sig_hex: str) -> bool:
        challenge_id = str(challenge.get("challenge_id", ""))
        try:
            self._service.verify_response(device_id=device_id, challenge_id=challenge_id, response_hex=response_sig_hex)
        except EarHandshakeError:
            return False
        return True

    def derive_session_key(self, *, device_id: str, challenge: dict) -> str:
        challenge_id = str(challenge.get("challenge_id", ""))
        nonce = bytes.fromhex(str(challenge.get("nonce", "")))
        issued_at = int(challenge.get("issued_at", challenge.get("ts", 0)))
        device = self._service._device_registry.get_device(device_id)
        if device is None:
            raise ValueError("unknown_device")
        msg = _challenge_message(device.device_id, challenge_id, nonce, issued_at)
        return hmac.new(device.device_secret, b"session|" + msg, hashlib.sha256).hexdigest()


def _validate_device_secret(device_secret: bytes) -> None:
    if not isinstance(device_secret, bytes):
        raise TypeError("device_secret must be bytes")
    if len(device_secret) != DEVICE_SECRET_LEN_BYTES:
        raise ValueError(f"device secret must be {DEVICE_SECRET_LEN_BYTES} bytes, got {len(device_secret)}")


def _challenge_message(device_id: str, challenge_id: str, nonce: bytes, issued_at: int) -> bytes:
    return b"|".join([
        device_id.encode("utf-8"),
        challenge_id.encode("utf-8"),
        nonce,
        issued_at.to_bytes(8, "big"),
    ])


def build_device_response(*, device_secret: bytes, challenge: dict[str, str | int]) -> str:
    _validate_device_secret(device_secret)
    try:
        challenge_id = str(challenge["challenge_id"])
        device_id = str(challenge["device_id"])
        nonce = bytes.fromhex(str(challenge["nonce"]))
        issued_at = int(challenge.get("issued_at", challenge["ts"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise EarHandshakeError("malformed_challenge") from exc

    return hmac.new(
        device_secret,
        _challenge_message(device_id=device_id, challenge_id=challenge_id, nonce=nonce, issued_at=issued_at),
        hashlib.sha256,
    ).hexdigest()


def sign_challenge_response(*, device_secret: bytes, challenge: dict) -> str:
    return build_device_response(device_secret=device_secret, challenge=challenge)


# Legacy test-only helpers retained for compatibility (not used in production paths).
def new_device(master_key: bytes | None = None) -> dict:
    warnings.warn(
        "new_device() is a legacy helper and must not be used in production; use EarHandshakeService.",
        DeprecationWarning,
        stacklevel=2,
    )
    if master_key is not None:
        _validate_device_secret(master_key)
    return {"key_id": "v1", "device_secret": master_key or os.urandom(DEVICE_SECRET_LEN_BYTES)}


def issue_challenge(device: dict) -> dict:
    warnings.warn(
        "issue_challenge(device) is a legacy helper and must not be used in production; use EarHandshakeService.issue_challenge().",
        DeprecationWarning,
        stacklevel=2,
    )
    challenge = {
        "challenge_id": uuid.uuid4().hex,
        "device_id": "legacy",
        "nonce": os.urandom(16).hex(),
        "ts": int(time.time()),
    }
    challenge["sig_hex"] = sign_challenge_response(device_secret=device["device_secret"], challenge=challenge)
    return challenge


def verify_response(device: dict, challenge: dict) -> bool:
    warnings.warn(
        "verify_response(device, challenge) is a legacy helper and must not be used in production; use EarHandshakeService.verify_response().",
        DeprecationWarning,
        stacklevel=2,
    )
    try:
        expected = sign_challenge_response(device_secret=device["device_secret"], challenge=challenge)
    except (KeyError, ValueError, TypeError):
        return False
    return hmac.compare_digest(expected, str(challenge.get("sig_hex", "")))


def derive_session_key(device: dict, challenge: dict) -> str:
    warnings.warn(
        "derive_session_key(device, challenge) is a legacy helper and must not be used in production; use VerifiedSession.session_key from EarHandshakeService.",
        DeprecationWarning,
        stacklevel=2,
    )
    nonce = bytes.fromhex(str(challenge["nonce"]))
    challenge_id = str(challenge.get("challenge_id", "legacy")).encode("utf-8")
    material = nonce + challenge_id + device["device_secret"]
    return hmac.new(device["device_secret"], material, hashlib.sha256).hexdigest()
