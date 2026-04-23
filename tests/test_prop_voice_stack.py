"""Property-based tests for integrated voice stack invariants."""

from __future__ import annotations

import copy

from hypothesis import assume, given, settings
from hypothesis import strategies as st
import pytest

from po_core.diversity import Rec, diversify_with_mmr
from po_echo.ear_handshake import (
    EarHandshakeError,
    EarHandshakeService,
    InMemoryChallengeStore,
    InMemoryDeviceRegistry,
    build_device_response,
)
from po_echo.rth import compute_rth
from po_echo.voice_boundary import classify_risk
from tests.invariant_logging import assert_or_log
from tests.strategies_adversarial import command_session_adversarial

STATE_TRANSITION_INVARIANTS = {
    "never_recommend": "おすすめ禁止: responsibility_boundary.ai_recommends is always False",
    "multiple_candidates": "候補複数提示: candidate set keeps alternatives",
    "boundary_integrity": "責任境界の保持: schema/liability/reasons stay attached",
    "conservative_on_danger": "危険時は保守側判定: danger signal never auto-allows",
}


def _build_recs(session: list[str]) -> tuple[list[Rec], list[Rec], bool]:
    """Build deterministic rec sets from utterances and return danger flag."""
    joined = " ".join(session).lower()
    danger = any(k in joined for k in ["自動", "確定", "中断", "戻る", "違う", "待って"])

    original = [
        Rec("o1", "Safe A", "M1", "voice", 3000, ("food",), 0.80, 0.85, 0.20),
        Rec("o2", "Safe B", "M2", "voice", 5000, ("food",), 0.78, 0.82, 0.25),
        Rec("o3", "Safe C", "M3", "voice", 9000, ("food",), 0.74, 0.80, 0.30),
    ]
    counterfactuals = [
        Rec("c1", "Alt A", "M4", "voice", 4000, ("alt",), 0.72, 0.79, 0.35),
        Rec("c2", "Alt B", "M5", "voice", 7000, ("alt",), 0.70, 0.78, 0.40),
        Rec("c3", "Alt C", "M6", "voice", 11000, ("alt",), 0.68, 0.76, 0.45),
    ]
    if danger:
        # Danger mode: make candidates biased to ensure conservative gate is exercised.
        original = [
            Rec("o1", "Risk A", "Mono", "voice", 15000, ("urgent",), 0.90, 0.40, 0.95),
            Rec("o2", "Risk B", "Mono", "voice", 18000, ("urgent",), 0.88, 0.38, 0.90),
            Rec("o3", "Risk C", "Mono", "voice", 20000, ("urgent",), 0.87, 0.35, 0.92),
        ]
    return original, counterfactuals, danger


def _assert_main_invariants(session: list[str], mode: str) -> None:
    original, counterfactuals, danger = _build_recs(session)
    result = diversify_with_mmr(original, counterfactuals, k=3)
    boundary = result["responsibility_boundary"]

    repro = {"session": session, "danger": danger, "boundary": boundary}
    assert_or_log(
        condition=boundary["ai_recommends"] is False,
        test_name="test_voice_stack_state_transition_invariants",
        mode=mode,
        repro_input=repro,
        message=STATE_TRANSITION_INVARIANTS["never_recommend"],
    )
    assert_or_log(
        condition=len(result["final_set"]) >= 2,
        test_name="test_voice_stack_state_transition_invariants",
        mode=mode,
        repro_input=repro,
        message=STATE_TRANSITION_INVARIANTS["multiple_candidates"],
    )
    assert_or_log(
        condition=(
            boundary.get("schema_version") == "1.0"
            and boundary.get("liability_mode") == "audit-only"
            and isinstance(boundary.get("reasons"), list)
            and len(boundary.get("reasons", [])) > 0
        ),
        test_name="test_voice_stack_state_transition_invariants",
        mode=mode,
        repro_input=repro,
        message=STATE_TRANSITION_INVARIANTS["boundary_integrity"],
    )

    auto_allowed = boundary["execution_allowed"] and not boundary["requires_human_confirm"]
    if danger:
        assert_or_log(
            condition=not auto_allowed,
            test_name="test_voice_stack_state_transition_invariants",
            mode=mode,
            repro_input=repro,
            message=STATE_TRANSITION_INVARIANTS["conservative_on_danger"],
        )


@settings(max_examples=120, deadline=None)
@given(st.floats(min_value=10000, max_value=10_000_000, allow_nan=False, allow_infinity=False))
def test_voice_boundary_amount_high_always_high_risk(amount: float) -> None:
    risk = classify_risk("generic", {"amount": amount})
    assert risk == "high"


@settings(max_examples=120, deadline=None)
@given(st.floats(min_value=1000, max_value=9999.99, allow_nan=False, allow_infinity=False))
def test_voice_boundary_amount_medium_window_maps_to_medium_risk(amount: float) -> None:
    risk = classify_risk("generic", {"amount": amount})
    assert risk == "medium"


@settings(max_examples=100, deadline=None)
@given(st.binary(min_size=32, max_size=32))
def test_ear_handshake_rejects_tampered_signature(master_key: bytes) -> None:
    registry = InMemoryDeviceRegistry()
    registry.register_device(device_id="dev-1", key_id="v1", device_secret=master_key)
    handshake = EarHandshakeService(device_registry=registry, challenge_store=InMemoryChallengeStore())
    challenge = handshake.issue_challenge(device_id="dev-1")
    response = build_device_response(device_secret=master_key, challenge=challenge)
    handshake.verify_response(device_id="dev-1", challenge_id=str(challenge["challenge_id"]), response_hex=response)

    tampered = response[:-1] + ("0" if response[-1] != "0" else "1")
    with pytest.raises(EarHandshakeError):
        handshake.verify_response(
            device_id="dev-1",
            challenge_id=str(challenge["challenge_id"]),
            response_hex=tampered,
        )


@settings(max_examples=100, deadline=None)
@given(st.binary(min_size=32, max_size=32), st.integers(min_value=62, max_value=10_000_000))
def test_ear_handshake_timestamp_expiry_boundary(master_key: bytes, now_s: int) -> None:
    """Why: replay防御の責務境界を固定し、期限切れchallengeの通過を防ぐ。"""
    registry = InMemoryDeviceRegistry()
    registry.register_device(device_id="dev-1", key_id="v1", device_secret=master_key)
    current = {"t": now_s}

    handshake = EarHandshakeService(
        device_registry=registry,
        challenge_store=InMemoryChallengeStore(),
        challenge_ttl_seconds=60,
        time_fn=lambda: current["t"],
    )
    challenge = handshake.issue_challenge(device_id="dev-1")
    response = build_device_response(device_secret=master_key, challenge=challenge)
    current["t"] = now_s + 61
    with pytest.raises(EarHandshakeError):
        handshake.verify_response(device_id="dev-1", challenge_id=str(challenge["challenge_id"]), response_hex=response)


@settings(max_examples=100, deadline=None)
@given(st.binary(min_size=32, max_size=32), st.binary(min_size=16, max_size=16))
def test_ear_handshake_session_key_changes_when_nonce_changes(
    master_key: bytes, replacement_nonce: bytes
) -> None:
    """Why: セッション鍵がchallenge固有であることを保証し、再利用リスクを減らす。"""
    assume(replacement_nonce != b"\x00" * 16)
    registry = InMemoryDeviceRegistry()
    registry.register_device(device_id="dev-1", key_id="v1", device_secret=master_key)
    handshake = EarHandshakeService(device_registry=registry, challenge_store=InMemoryChallengeStore())
    ch1 = handshake.issue_challenge(device_id="dev-1")
    ch2 = copy.deepcopy(ch1)
    ch2["challenge_id"] = "different"
    ch2["nonce"] = replacement_nonce.hex()

    key1 = build_device_response(device_secret=master_key, challenge=ch1)
    key2 = build_device_response(device_secret=master_key, challenge=ch2)

    assert len(key1) == 64
    assert len(key2) == 64
    assert key1 != key2


@settings(max_examples=120, deadline=None)
@given(st.text(min_size=0, max_size=200))
def test_rth_empty_transcript_boundary_and_hash_shape(transcript: str) -> None:
    snap = compute_rth(transcript)
    assert len(snap["robust_hash_hex"]) == 16
    assert all(ch in "0123456789abcdef" for ch in snap["robust_hash_hex"])

    empty = compute_rth("")
    assert empty["hash_hex"] == ""
    assert empty["robust_hash_hex"] == "0" * 16


@settings(max_examples=80, deadline=None, derandomize=True)
@given(command_session_adversarial)
def test_voice_stack_state_transition_invariants_seed_fixed(session: list[str]) -> None:
    _assert_main_invariants(session, mode="seed_fixed")


@settings(max_examples=80, deadline=None)
@given(command_session_adversarial)
def test_voice_stack_state_transition_invariants_normal_mode(session: list[str]) -> None:
    _assert_main_invariants(session, mode="normal")
