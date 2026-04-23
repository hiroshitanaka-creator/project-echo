"""Ear Handshake security model with explicit trust boundaries.

This module is the canonical Python implementation for device challenge-response.
Verifier trust anchors are **registered devices in a trusted registry**; caller input
is never treated as trusted key material.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
import uuid
from dataclasses import dataclass
from typing import Protocol

DEVICE_SECRET_LEN_BYTES = 32
DEFAULT_CHALLENGE_TTL_SECONDS = 60
DEFAULT_SESSION_TTL_SECONDS = 300


class EarHandshakeError(RuntimeError):
    """Domain error for challenge/response/session failures."""


@dataclass(frozen=True)
class RegisteredDevice:
    """Trusted device material loaded from a verifier-owned registry."""

    device_id: str
    key_id: str
    device_secret: bytes


@dataclass(frozen=True)
class ChallengeRecord:
    """Stored one-time challenge bound to a specific trusted device."""

    challenge_id: str
    device_id: str
    key_id: str
    nonce: bytes
    issued_at: int
    expires_at: int
    consumed: bool = False


@dataclass(frozen=True)
class VerifiedSession:
    """Session established only after successful challenge verification."""

    session_id: str
    device_id: str
    key_id: str
    challenge_id: str
    session_key: str
    authenticated_at: int
    expires_at: int


class DeviceRegistry(Protocol):
    def get_device(self, device_id: str) -> RegisteredDevice | None: ...


class ChallengeStore(Protocol):
    def put(self, record: ChallengeRecord) -> None: ...

    def get(self, challenge_id: str) -> ChallengeRecord | None: ...

    def mark_consumed(self, challenge_id: str) -> None: ...


class InMemoryDeviceRegistry(DeviceRegistry):
    def __init__(self) -> None:
        self._devices: dict[str, RegisteredDevice] = {}

    def register_device(self, *, device_id: str, key_id: str, device_secret: bytes) -> RegisteredDevice:
        _validate_device_secret(device_secret)
        if not device_id:
            raise ValueError("device_id is required")
        device = RegisteredDevice(device_id=device_id, key_id=key_id, device_secret=device_secret)
        self._devices[device_id] = device
        return device

    def get_device(self, device_id: str) -> RegisteredDevice | None:
        return self._devices.get(device_id)


class InMemoryChallengeStore(ChallengeStore):
    def __init__(self) -> None:
        self._records: dict[str, ChallengeRecord] = {}

    def put(self, record: ChallengeRecord) -> None:
        self._records[record.challenge_id] = record

    def get(self, challenge_id: str) -> ChallengeRecord | None:
        return self._records.get(challenge_id)

    def mark_consumed(self, challenge_id: str) -> None:
        record = self._records.get(challenge_id)
        if record is None:
            raise EarHandshakeError("challenge_not_found")
        self._records[challenge_id] = ChallengeRecord(
            challenge_id=record.challenge_id,
            device_id=record.device_id,
            key_id=record.key_id,
            nonce=record.nonce,
            issued_at=record.issued_at,
            expires_at=record.expires_at,
            consumed=True,
        )


def _validate_device_secret(device_secret: bytes) -> None:
    if not isinstance(device_secret, bytes):
        raise TypeError("device secret must be bytes")
    if len(device_secret) != DEVICE_SECRET_LEN_BYTES:
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

    msg = _message(device_id=device_id, challenge_id=challenge_id, nonce=nonce, issued_at=issued_at)
    return hmac.new(device_secret, msg, hashlib.sha256).hexdigest()
