"""Ear-Handshake: trusted device authentication with explicit trust boundary.

Security model:
- Device authenticity depends on a server-side trust store (registered device IDs).
- Request-supplied secrets are never accepted as production trust anchors.
- Challenge issuance and challenge verification are separated phases.
- Challenges expire quickly and are single-use (replay rejected).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from typing import Protocol

DEVICE_SECRET_LEN_BYTES = 32
DEFAULT_CHALLENGE_TTL_SECONDS = 60


class DeviceTrustStore(Protocol):
    """Trust anchor abstraction for registered device identities."""

    def get_device_secret(self, *, device_id: str) -> bytes | None:
        """Return trusted secret for device_id, or None when unknown."""


@dataclass(frozen=True)
class TrustedDevice:
    """Trusted device record."""

    device_id: str
    key_id: str
    device_secret: bytes


class InMemoryDeviceTrustStore:
    """In-memory trust store used by tests and local single-process runs."""

    def __init__(self) -> None:
        self._by_device_id: dict[str, TrustedDevice] = {}

    def register_device(self, *, device_id: str, device_secret: bytes, key_id: str = "v1") -> None:
        _validate_device_secret(device_secret)
        if not device_id:
            raise ValueError("device_id is required")
        self._by_device_id[device_id] = TrustedDevice(
            device_id=device_id,
            key_id=key_id,
            device_secret=device_secret,
        )

    def get_device_secret(self, *, device_id: str) -> bytes | None:
        rec = self._by_device_id.get(device_id)
        return rec.device_secret if rec else None

    def get_key_id(self, *, device_id: str) -> str:
        rec = self._by_device_id.get(device_id)
        return rec.key_id if rec else "v1"


@dataclass(frozen=True)
class IssuedChallenge:
    """Challenge tracked server-side until used/expired."""

    challenge_id: str
    device_id: str
    nonce_hex: str
    ts: int
    expires_at: int
    used: bool = False


class InMemoryChallengeStore:
    """In-memory challenge lifecycle tracker."""

    def __init__(self) -> None:
        self._by_id: dict[str, IssuedChallenge] = {}

    def save(self, challenge: IssuedChallenge) -> None:
        self._by_id[challenge.challenge_id] = challenge

    def get(self, *, challenge_id: str) -> IssuedChallenge | None:
        return self._by_id.get(challenge_id)

    def mark_used(self, *, challenge_id: str) -> None:
        challenge = self._by_id.get(challenge_id)
        if challenge is None:
            return
        self._by_id[challenge_id] = IssuedChallenge(
            challenge_id=challenge.challenge_id,
            device_id=challenge.device_id,
            nonce_hex=challenge.nonce_hex,
            ts=challenge.ts,
            expires_at=challenge.expires_at,
            used=True,
        )

    def get(self, challenge_id: str) -> ChallengeRecord | None: ...

def _validate_device_secret(master_key: bytes) -> None:
    if not isinstance(master_key, bytes):
        raise TypeError("device master_key must be bytes")
    if len(master_key) != DEVICE_SECRET_LEN_BYTES:
        raise ValueError(
            f"device secret must be {DEVICE_SECRET_LEN_BYTES} bytes, got {len(device_secret)}"
        )


def _message(device_id: str, challenge_id: str, nonce: bytes, issued_at: int) -> bytes:
    return b"|".join(
        [
            device_id.encode("utf-8"),
            challenge_id.encode("utf-8"),
            nonce,
            issued_at.to_bytes(8, "big"),
        ]
    )


class EarHandshakeService:
    """Verifier-side challenge/response service using trusted stores."""

    def __init__(
        self,
        *,
        device_registry: DeviceRegistry,
        challenge_store: ChallengeStore,
        challenge_ttl_seconds: int = DEFAULT_CHALLENGE_TTL_SECONDS,
        session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
        time_fn: callable = time.time,
    ) -> None:
        self._device_registry = device_registry
        self._challenge_store = challenge_store
        self._challenge_ttl_seconds = challenge_ttl_seconds
        self._session_ttl_seconds = session_ttl_seconds
        self._time_fn = time_fn

    def issue_challenge(self, *, device_id: str) -> dict[str, str | int]:
        device = self._device_registry.get_device(device_id)
        if device is None:
            raise EarHandshakeError("unknown_device")

        now = int(self._time_fn())
        challenge_id = uuid.uuid4().hex
        nonce = os.urandom(16)
        record = ChallengeRecord(
            challenge_id=challenge_id,
            device_id=device.device_id,
            key_id=device.key_id,
            nonce=nonce,
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
            "expires_at": record.expires_at,
        }

    def verify_response(
        self,
        *,
        device_id: str,
        challenge_id: str,
        response_hex: str,
    ) -> VerifiedSession:
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

        msg = _message(
            device_id=device.device_id,
            challenge_id=record.challenge_id,
            nonce=record.nonce,
            issued_at=record.issued_at,
        )
        expected = hmac.new(device.device_secret, msg, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, response_hex):
            raise EarHandshakeError("invalid_response")

        self._challenge_store.mark_consumed(challenge_id)
        session_key = hmac.new(
            device.device_secret,
            b"session|" + msg,
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


def build_device_response(*, device_secret: bytes, challenge: dict[str, str | int]) -> str:
    """Device-side helper for tests/clients to compute challenge proof."""
    _validate_device_secret(device_secret)
    try:
        challenge_id = str(challenge["challenge_id"])
        device_id = str(challenge["device_id"])
        nonce = bytes.fromhex(str(challenge["nonce"]))
        issued_at = int(challenge["issued_at"])
    except (KeyError, ValueError, TypeError) as exc:
        raise EarHandshakeError("malformed_challenge") from exc

def new_device(master_key: bytes | None = None) -> dict:
    """Legacy helper for tests: create local device material."""
    if master_key is not None:
        _validate_device_secret(master_key)

    return {
        "key_id": "v1",
        "device_secret": master_key or os.urandom(DEVICE_SECRET_LEN_BYTES),
    }


def sign_challenge_response(*, device_secret: bytes, challenge: dict) -> str:
    """Sign challenge fields as the device response."""
    _validate_device_secret(device_secret)
    nonce = bytes.fromhex(str(challenge["nonce"]))
    ts = int(challenge["ts"])
    challenge_id = str(challenge["challenge_id"]).encode("utf-8")
    msg = nonce + ts.to_bytes(8, "big") + challenge_id
    return hmac.new(device_secret, msg, hashlib.sha256).hexdigest()


class EarHandshakeAuthenticator:
    """Canonical ear-handshake flow bound to trusted device registry."""

    def __init__(
        self,
        *,
        trust_store: DeviceTrustStore,
        challenge_store: InMemoryChallengeStore,
        challenge_ttl_seconds: int = DEFAULT_CHALLENGE_TTL_SECONDS,
    ) -> None:
        self._trust_store = trust_store
        self._challenge_store = challenge_store
        self._challenge_ttl_seconds = challenge_ttl_seconds

    def issue_challenge(self, *, device_id: str) -> dict:
        device_secret = self._trust_store.get_device_secret(device_id=device_id)
        if device_secret is None:
            raise ValueError("unknown_device")

        now = int(time.time())
        challenge = IssuedChallenge(
            challenge_id=os.urandom(16).hex(),
            device_id=device_id,
            nonce_hex=os.urandom(16).hex(),
            ts=now,
            expires_at=now + self._challenge_ttl_seconds,
        )
        self._challenge_store.save(challenge)

        key_id = "v1"
        if isinstance(self._trust_store, InMemoryDeviceTrustStore):
            key_id = self._trust_store.get_key_id(device_id=device_id)

        return {
            "challenge_id": challenge.challenge_id,
            "device_id": challenge.device_id,
            "nonce": challenge.nonce_hex,
            "ts": challenge.ts,
            "expires_at": challenge.expires_at,
            "key_id": key_id,
        }

    def verify_response(self, *, device_id: str, challenge: dict, response_sig_hex: str) -> bool:
        if not response_sig_hex or not isinstance(response_sig_hex, str):
            return False

        device_secret = self._trust_store.get_device_secret(device_id=device_id)
        if device_secret is None:
            return False

        challenge_id = str(challenge.get("challenge_id", ""))
        if not challenge_id:
            return False

        issued = self._challenge_store.get(challenge_id=challenge_id)
        if issued is None:
            return False

        if issued.device_id != device_id:
            return False

        now = int(time.time())
        if issued.used or now > issued.expires_at:
            return False

        # Challenge fields are verified against the server-tracked challenge, not
        # against arbitrary request-supplied values.
        if (
            str(challenge.get("nonce", "")) != issued.nonce_hex
            or int(challenge.get("ts", -1)) != issued.ts
            or str(challenge.get("device_id", "")) != issued.device_id
        ):
            return False

        expected_sig_hex = sign_challenge_response(device_secret=device_secret, challenge=challenge)
        if not hmac.compare_digest(expected_sig_hex, response_sig_hex):
            return False

        self._challenge_store.mark_used(challenge_id=challenge_id)
        return True

    def derive_session_key(self, *, device_id: str, challenge: dict) -> str:
        device_secret = self._trust_store.get_device_secret(device_id=device_id)
        if device_secret is None:
            raise ValueError("unknown_device")

        nonce = bytes.fromhex(str(challenge["nonce"]))
        challenge_id = str(challenge["challenge_id"]).encode("utf-8")
        material = nonce + challenge_id + device_secret
        return hmac.new(device_secret, material, hashlib.sha256).hexdigest()


def issue_challenge(device: dict) -> dict:
    """Legacy helper for local-only tests (not trusted-device auth)."""
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
    """Legacy helper for local-only tests (not trusted-device auth)."""
    try:
        nonce = bytes.fromhex(challenge["nonce"])
        ts = int(challenge["ts"])
    except (KeyError, TypeError, ValueError):
        return False

    if abs(int(time.time()) - ts) > 60:
        return False

    msg = nonce + ts.to_bytes(8, "big")
    sig = hmac.new(device["device_secret"], msg, hashlib.sha256).digest().hex()
    return hmac.compare_digest(sig, str(challenge.get("sig_hex", "")))


def derive_session_key(device: dict, challenge: dict) -> str:
    """Legacy helper for local-only tests."""
    nonce = bytes.fromhex(challenge["nonce"])
    material = nonce + device["device_secret"]
    return hmac.new(device["device_secret"], material, hashlib.sha256).hexdigest()
