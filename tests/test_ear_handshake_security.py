from __future__ import annotations

import pytest

from po_echo.ear_handshake import (
    EarHandshakeError,
    EarHandshakeService,
    InMemoryChallengeStore,
    InMemoryDeviceRegistry,
    build_device_response,
)


def _service(secret_hex: str = "11" * 32) -> tuple[EarHandshakeService, bytes]:
    secret = bytes.fromhex(secret_hex)
    registry = InMemoryDeviceRegistry()
    registry.register_device(device_id="device-1", key_id="v1", device_secret=secret)
    return EarHandshakeService(device_registry=registry, challenge_store=InMemoryChallengeStore()), secret


def test_unknown_device_rejected_on_issue() -> None:
    service, _ = _service()
    with pytest.raises(EarHandshakeError, match="unknown_device"):
        service.issue_challenge(device_id="missing")


def test_caller_secret_cannot_authenticate_registered_device() -> None:
    service, _ = _service()
    challenge = service.issue_challenge(device_id="device-1")
    attacker_secret = bytes.fromhex("22" * 32)
    forged = build_device_response(device_secret=attacker_secret, challenge=challenge)
    with pytest.raises(EarHandshakeError, match="invalid_response"):
        service.verify_response(
            device_id="device-1",
            challenge_id=str(challenge["challenge_id"]),
            response_hex=forged,
        )


def test_challenge_one_time_use_replay_rejected() -> None:
    service, secret = _service()
    challenge = service.issue_challenge(device_id="device-1")
    response = build_device_response(device_secret=secret, challenge=challenge)
    service.verify_response(device_id="device-1", challenge_id=str(challenge["challenge_id"]), response_hex=response)

    with pytest.raises(EarHandshakeError, match="challenge_already_used"):
        service.verify_response(device_id="device-1", challenge_id=str(challenge["challenge_id"]), response_hex=response)


def test_challenge_expiry_rejected() -> None:
    now = {"v": 1000}
    secret = bytes.fromhex("11" * 32)
    registry = InMemoryDeviceRegistry()
    registry.register_device(device_id="device-1", key_id="v1", device_secret=secret)
    service = EarHandshakeService(
        device_registry=registry,
        challenge_store=InMemoryChallengeStore(),
        challenge_ttl_seconds=60,
        time_fn=lambda: now["v"],
    )

    challenge = service.issue_challenge(device_id="device-1")
    response = build_device_response(device_secret=secret, challenge=challenge)
    now["v"] = 1061
    with pytest.raises(EarHandshakeError, match="challenge_expired"):
        service.verify_response(device_id="device-1", challenge_id=str(challenge["challenge_id"]), response_hex=response)


def test_challenge_bound_to_device_id() -> None:
    secret = bytes.fromhex("11" * 32)
    registry = InMemoryDeviceRegistry()
    registry.register_device(device_id="device-1", key_id="v1", device_secret=secret)
    registry.register_device(device_id="device-2", key_id="v1", device_secret=secret)
    service = EarHandshakeService(device_registry=registry, challenge_store=InMemoryChallengeStore())

    challenge = service.issue_challenge(device_id="device-1")
    response = build_device_response(device_secret=secret, challenge=challenge)
    with pytest.raises(EarHandshakeError, match="challenge_device_mismatch"):
        service.verify_response(device_id="device-2", challenge_id=str(challenge["challenge_id"]), response_hex=response)


def test_malformed_response_rejected() -> None:
    service, _ = _service()
    challenge = service.issue_challenge(device_id="device-1")
    with pytest.raises(EarHandshakeError, match="malformed_response"):
        service.verify_response(device_id="device-1", challenge_id=str(challenge["challenge_id"]), response_hex="zzz")
