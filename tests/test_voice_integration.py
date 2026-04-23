"""Python API-level integration tests for the voice orchestration pipeline.

Why these tests exist:
- test_voice_cli.py tests the CLI layer via subprocess (black-box).
- test_prop_voice_stack.py tests individual units via property-based fuzzing.
- This file fills the gap: exercising run_voice_flow() directly at the Python
  API level with multiple intent/metadata scenarios, verifying that the full
  pipeline (ear handshake → execution gate → echo mark) produces a schema-
  stable output and respects the responsibility boundary contract across
  diverse inputs.

Coverage goals:
- Low-risk intent (search): full pipeline succeeds, output schema complete.
- Medium-risk intent (booking + simulate_ok): execution_allowed=True with confirm.
- High-risk intent (payment, high amount): execution blocked without simulate_ok.
- require_execution_allowed=True raises VoiceFlowError on blocked actions.
- Output always contains all five schema keys.
- Echo Mark always has schema_version and signature fields.
"""

from __future__ import annotations

from copy import deepcopy

import pytest

_PYNACL_MISSING = False
try:
    import nacl  # noqa: F401
except ImportError:
    _PYNACL_MISSING = True

pytestmark = pytest.mark.skipif(
    _PYNACL_MISSING,
    reason="PyNaCl not installed; voice integration tests require Ed25519 support",
)

from po_echo.execution_gate import InMemorySessionStore, gate_audio  # noqa: E402
from po_echo.ear_handshake import (  # noqa: E402
    EarHandshakeAuthenticator,
    InMemoryChallengeStore,
    InMemoryDeviceTrustStore,
    sign_challenge_response,
)
from po_echo.voice_orchestration import VoiceFlowError, VoiceFlowInput, run_voice_flow  # noqa: E402

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_HMAC_SECRET = "test-secret-1234567890"
_ED25519_KEY = "1f1e1d1c1b1a191817161514131211100f0e0d0c0b0a09080706050403020100"

_AUDIT_BASE: dict = {
    "final_set": [
        {
            "title": "Option A",
            "merchant": "m1",
            "price": 3000,
            "utility": 0.80,
            "bias_risk": 0.20,
            "category": "food",
            "tags": ["popular"],
        },
        {
            "title": "Option B",
            "merchant": "m2",
            "price": 5000,
            "utility": 0.72,
            "bias_risk": 0.25,
            "category": "food",
            "tags": ["budget"],
        },
    ],
    "commercial_bias_original": {"overall_bias_score": 0.40},
    "commercial_bias_final": {"overall_bias_score": 0.22},
}

_OUTPUT_SCHEMA_KEYS = (
    "candidate_set",
    "evidence",
    "responsibility_boundary",
    "voice_text",
    "echo_mark",
)


def _make_payload(**kwargs: object) -> VoiceFlowInput:
    defaults: dict[str, object] = {
        "intent": "search",
        "transcript": "候補を比較したい",
        "metadata": {},
        "simulate_ok": True,
        "device_id": "device-main",
    }
    defaults.update(kwargs)
    return VoiceFlowInput(**defaults)  # type: ignore[arg-type]


def _run(**kwargs: object) -> dict:
    trust_store = kwargs.pop("trust_store", None) or InMemoryDeviceTrustStore()
    challenge_store = kwargs.pop("challenge_store", None) or InMemoryChallengeStore()
    session_store = kwargs.pop("session_store", None)
    audit = kwargs.pop("audit", _AUDIT_BASE)
    payload_kwargs = {k: v for k, v in kwargs.items() if k in VoiceFlowInput.__dataclass_fields__}
    run_kwargs = {k: v for k, v in kwargs.items() if k not in VoiceFlowInput.__dataclass_fields__}
    payload = _make_payload(**payload_kwargs)

    device_secret = bytes.fromhex(
        payload.device_secret_hex or "11" * 32
    )
    trust_store.register_device(device_id=payload.device_id, device_secret=device_secret, key_id="v1")
    auth = EarHandshakeAuthenticator(trust_store=trust_store, challenge_store=challenge_store)
    challenge = auth.issue_challenge(device_id=payload.device_id)
    response_sig = sign_challenge_response(device_secret=device_secret, challenge=challenge)
    payload = VoiceFlowInput(
        intent=payload.intent,
        transcript=payload.transcript,
        metadata=payload.metadata,
        simulate_ok=payload.simulate_ok,
        run_id=payload.run_id,
        key_id=payload.key_id,
        device_id=payload.device_id,
        challenge=challenge,
        challenge_response_sig_hex=response_sig,
        session_id=payload.session_id,
        device_secret_hex=payload.device_secret_hex,
    )
    return run_voice_flow(
        audit=audit,  # type: ignore[arg-type]
        payload=payload,
        hmac_secret=_HMAC_SECRET,
        ed25519_private_key=_ED25519_KEY,
        trust_store=trust_store,
        challenge_store=challenge_store,
        session_store=session_store,
        **run_kwargs,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Output schema completeness
# ---------------------------------------------------------------------------


def test_search_intent_output_schema_complete() -> None:
    """Low-risk search intent must produce all five required output keys."""
    result = _run(intent="search", transcript="商品を探しています", metadata={})
    for key in _OUTPUT_SCHEMA_KEYS:
        assert key in result, f"Missing required output key: {key!r}"


def test_output_candidate_set_is_list() -> None:
    result = _run(intent="search", transcript="候補を見せて", metadata={})
    assert isinstance(result["candidate_set"], list)
    assert len(result["candidate_set"]) >= 1


def test_output_evidence_is_list_of_dicts() -> None:
    result = _run(intent="search", transcript="候補を見せて", metadata={})
    assert isinstance(result["evidence"], list)
    assert all(isinstance(e, dict) for e in result["evidence"])


def test_output_voice_text_is_nonempty_string() -> None:
    result = _run(intent="search", transcript="候補を見せて", metadata={})
    assert isinstance(result["voice_text"], str)
    assert len(result["voice_text"]) > 0


# ---------------------------------------------------------------------------
# Echo Mark schema
# ---------------------------------------------------------------------------


def test_echo_mark_has_required_fields() -> None:
    result = _run(intent="search", transcript="候補を見せて", metadata={})
    badge = result["echo_mark"]
    assert isinstance(badge, dict)
    assert "schema_version" in badge
    assert "signature" in badge or "hmac_signature" in badge, (
        "echo_mark must have at least one signature field"
    )


def test_echo_mark_schema_version_is_v3() -> None:
    result = _run(intent="search", transcript="候補を見せて", metadata={})
    assert result["echo_mark"].get("schema_version") == "echo_mark_v3"


# ---------------------------------------------------------------------------
# Responsibility boundary contract
# ---------------------------------------------------------------------------


def test_responsibility_boundary_channel_is_audio() -> None:
    """Voice flow must always tag the channel as 'audio'."""
    result = _run(intent="search", transcript="候補を見せて", metadata={})
    rb = result["responsibility_boundary"]
    assert rb.get("channel") == "audio", f"Expected channel='audio', got {rb.get('channel')!r}"


def test_responsibility_boundary_has_required_fields() -> None:
    """Responsibility boundary must always contain the required structural fields.

    Why: voice boundary contract — channel, execution_allowed, requires_human_confirm,
    and reasons must be present for downstream callers and audit consumers.
    """
    result = _run(intent="search", transcript="候補を見せて", metadata={})
    rb = result["responsibility_boundary"]
    for field in ("channel", "execution_allowed", "requires_human_confirm", "reasons"):
        assert field in rb, f"Missing required boundary field: {field!r}"
    assert isinstance(rb["reasons"], list)


# ---------------------------------------------------------------------------
# Risk classification and execution gate
# ---------------------------------------------------------------------------


def test_low_risk_search_allows_execution() -> None:
    """Search intent with no high-value metadata should allow execution."""
    result = _run(intent="search", transcript="商品比較", metadata={}, simulate_ok=True)
    rb = result["responsibility_boundary"]
    assert rb.get("execution_allowed") is True


def test_high_risk_payment_blocks_execution_without_simulate_ok() -> None:
    """Payment intent with high amount (>=10000) must block execution."""
    result = _run(
        intent="payment",
        transcript="3万円で支払って",
        metadata={"amount": 30000},
        simulate_ok=False,
    )
    rb = result["responsibility_boundary"]
    assert rb.get("execution_allowed") is False, (
        "High-value payment must be blocked without user confirmation"
    )


def test_require_execution_allowed_raises_on_blocked() -> None:
    """require_execution_allowed=True must raise VoiceFlowError on high-risk intent."""
    payload = _make_payload(
        intent="payment",
        transcript="5万円で支払って",
        metadata={"amount": 50000},
        simulate_ok=False,
    )
    with pytest.raises(VoiceFlowError, match="dangerous_or_unconfirmed_action_blocked"):
        _run(
            audit=_AUDIT_BASE,
            intent=payload.intent,
            transcript=payload.transcript,
            metadata=payload.metadata,
            simulate_ok=payload.simulate_ok,
            require_execution_allowed=True,
        )


def test_unknown_device_is_rejected() -> None:
    trust_store = InMemoryDeviceTrustStore()
    challenge_store = InMemoryChallengeStore()
    fake_challenge = {
        "challenge_id": "deadbeef",
        "device_id": "unknown",
        "nonce": "00" * 16,
        "ts": 1,
        "expires_at": 2,
        "key_id": "v1",
    }
    payload = _make_payload(
        device_id="unknown",
        challenge=fake_challenge,
        challenge_response_sig_hex="00" * 32,
    )
    with pytest.raises(VoiceFlowError, match="ear handshake verification failed"):
        run_voice_flow(
            audit=_AUDIT_BASE,
            payload=payload,
            hmac_secret=_HMAC_SECRET,
            ed25519_private_key=_ED25519_KEY,
            trust_store=trust_store,
            challenge_store=challenge_store,
        )


def test_booking_with_simulate_ok_allows_execution() -> None:
    """Booking intent with simulate_ok=True should pass the execution gate."""
    result = _run(
        intent="booking",
        transcript="土曜夜2名で予約したい",
        metadata={"amount": 8000},
        simulate_ok=True,
    )
    rb = result["responsibility_boundary"]
    assert rb.get("execution_allowed") is True


@pytest.mark.parametrize(
    ("bias_final", "meta"),
    [
        (0.72, {}),
        (0.21, {"replay_detected": True}),
        (0.21, {"tamper_detected": True}),
    ],
)
def test_live_voice_path_enforces_screenless_block_conditions(
    bias_final: float,
    meta: dict[str, object],
) -> None:
    """Live voice flow must block high-bias/replay/tamper even with simulate_ok=True."""
    audit = deepcopy(_AUDIT_BASE)
    audit["commercial_bias_final"] = {"overall_bias_score": bias_final}
    result = _run(
        intent="search",
        transcript="候補を比較したい",
        metadata=meta,
        simulate_ok=True,
        audit=audit,
    )
    rb = result["responsibility_boundary"]
    assert rb["execution_allowed"] is False
    assert rb["requires_human_confirm"] is True
    assert "screenless_guard" in rb["reasons"]


def test_blocked_upstream_boundary_stays_blocked_in_voice_flow() -> None:
    """Upstream blocked audit must never be relaxed by low-risk voice intent."""
    blocked_audit = deepcopy(_AUDIT_BASE)
    blocked_audit["responsibility_boundary"] = {
        "schema_version": "1.0",
        "execution_allowed": False,
        "requires_human_confirm": True,
        "ai_recommends": False,
        "liability_mode": "audit-only",
        "reasons": ["high_bias_after_diversification"],
        "signals": {
            "bias_original": 0.91,
            "bias_final": 0.72,
            "bias_improvement": 0.19,
            "merchants_final": 1,
            "price_buckets_final": 1,
        },
    }
    payload = _make_payload(
        intent="search", transcript="候補を探して", metadata={}, simulate_ok=True
    )

    result = _run(
        audit=blocked_audit,
        intent=payload.intent,
        transcript=payload.transcript,
        metadata=payload.metadata,
        simulate_ok=payload.simulate_ok,
    )
    rb = result["responsibility_boundary"]
    assert rb["execution_allowed"] is False
    assert rb["requires_human_confirm"] is True
    assert rb["required_action"] != "none"
    assert "high_bias_after_diversification" in rb["reasons"]


def test_gate_audio_preserves_upstream_boundary_metadata_and_signals() -> None:
    """Audio gate must merge with upstream boundary instead of replacing it."""
    upstream = {
        "schema_version": "1.0",
        "execution_allowed": False,
        "requires_human_confirm": True,
        "ai_recommends": False,
        "liability_mode": "audit-only",
        "reasons": ["merchant_monopoly_detected"],
        "signals": {
            "bias_original": 0.8,
            "bias_final": 0.65,
            "bias_improvement": 0.15,
            "merchants_final": 1,
            "price_buckets_final": 1,
        },
    }
    audit = {**_AUDIT_BASE, "responsibility_boundary": upstream}
    result = gate_audio(
        audit=audit,
        intent="search",
        meta={},
        transcript_tail="候補を比較したい",
        simulate_user_ok=True,
    )
    rb = result["responsibility_boundary"]

    assert rb["execution_allowed"] is False
    assert rb["schema_version"] == "1.0"
    assert rb["ai_recommends"] is False
    assert rb["liability_mode"] == "audit-only"
    assert rb["signals"] == upstream["signals"]
    assert "merchant_monopoly_detected" in rb["reasons"]
    assert rb["required_action"] != "none"


def test_voice_path_echo_mark_payload_keeps_nonzero_upstream_signals() -> None:
    """Echo Mark from voice flow must keep non-zero upstream boundary signals."""
    audit = deepcopy(_AUDIT_BASE)
    audit["responsibility_boundary"] = {
        "schema_version": "1.0",
        "execution_allowed": True,
        "requires_human_confirm": False,
        "ai_recommends": False,
        "liability_mode": "audit-only",
        "reasons": ["low_bias_originally"],
        "signals": {
            "bias_original": 0.44,
            "bias_final": 0.12,
            "bias_improvement": 0.32,
            "merchants_final": 4,
            "price_buckets_final": 3,
        },
    }
    payload = _make_payload(
        intent="search", transcript="候補を見せて", metadata={}, simulate_ok=True
    )
    result = _run(
        audit=audit,
        intent=payload.intent,
        transcript=payload.transcript,
        metadata=payload.metadata,
        simulate_ok=payload.simulate_ok,
    )
    signals = result["echo_mark"]["payload"]["signals"]
    assert signals["bias_improvement"] == pytest.approx(0.32)
    assert signals["merchants_final"] == 4
    assert signals["price_buckets_final"] == 3


def test_required_action_promoted_when_confirmation_required_upstream() -> None:
    """If confirmation is required, required_action must not remain 'none'."""
    audit = deepcopy(_AUDIT_BASE)
    audit["responsibility_boundary"] = {
        "schema_version": "1.0",
        "execution_allowed": True,
        "requires_human_confirm": True,
        "required_action": "none",
        "ai_recommends": False,
        "liability_mode": "audit-only",
        "reasons": ["medium_bias_requires_confirmation"],
        "signals": {
            "bias_original": 0.5,
            "bias_final": 0.35,
            "bias_improvement": 0.15,
            "merchants_final": 2,
            "price_buckets_final": 2,
        },
    }
    result = _run(
        intent="search", transcript="候補を比較したい", metadata={}, simulate_ok=True, audit=audit
    )
    rb = result["responsibility_boundary"]
    assert rb["requires_human_confirm"] is True
    assert rb["required_action"] != "none"


# ---------------------------------------------------------------------------
# Evidence audit trail
# ---------------------------------------------------------------------------


def test_evidence_contains_ear_handshake_entry() -> None:
    """Evidence must include an ear handshake entry for traceability."""
    result = _run(intent="search", transcript="候補を見せて", metadata={})
    evidence_types = [e.get("type") for e in result["evidence"]]
    assert "ear_handshake" in evidence_types, (
        f"ear_handshake evidence missing; got types: {evidence_types}"
    )


def test_evidence_contains_echo_mark_entry() -> None:
    result = _run(intent="search", transcript="候補を見せて", metadata={})
    evidence_types = [e.get("type") for e in result["evidence"]]
    assert "echo_mark" in evidence_types, f"echo_mark evidence missing; got types: {evidence_types}"


def test_ear_handshake_replay_challenge_rejected() -> None:
    trust_store = InMemoryDeviceTrustStore()
    challenge_store = InMemoryChallengeStore()
    device_secret = bytes.fromhex("22" * 32)
    trust_store.register_device(device_id="d1", device_secret=device_secret)
    auth = EarHandshakeAuthenticator(trust_store=trust_store, challenge_store=challenge_store)

    challenge = auth.issue_challenge(device_id="d1")
    sig = sign_challenge_response(device_secret=device_secret, challenge=challenge)
    assert auth.verify_response(device_id="d1", challenge=challenge, response_sig_hex=sig) is True
    assert auth.verify_response(device_id="d1", challenge=challenge, response_sig_hex=sig) is False


def test_ear_handshake_expired_challenge_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    trust_store = InMemoryDeviceTrustStore()
    challenge_store = InMemoryChallengeStore()
    device_secret = bytes.fromhex("33" * 32)
    trust_store.register_device(device_id="d2", device_secret=device_secret)
    auth = EarHandshakeAuthenticator(
        trust_store=trust_store,
        challenge_store=challenge_store,
        challenge_ttl_seconds=1,
    )

    with monkeypatch.context() as m:
        m.setattr("po_echo.ear_handshake.time.time", lambda: 1000.0)
        challenge = auth.issue_challenge(device_id="d2")
        sig = sign_challenge_response(device_secret=device_secret, challenge=challenge)
    with monkeypatch.context() as m:
        m.setattr("po_echo.ear_handshake.time.time", lambda: 1003.0)
        assert auth.verify_response(device_id="d2", challenge=challenge, response_sig_hex=sig) is False


def test_session_continuity_persists_rth_in_same_session() -> None:
    session_store = InMemorySessionStore()
    first = _run(
        transcript="土曜夜に予約",
        metadata={},
        session_id="session-a",
        session_store=session_store,
    )
    second = _run(
        transcript="予算一万円以下",
        metadata={},
        session_id="session-a",
        session_store=session_store,
    )
    first_hash = first["responsibility_boundary"]["rth_snapshot"]["hash_hex"]
    second_hash = second["responsibility_boundary"]["rth_snapshot"]["hash_hex"]
    assert first_hash != second_hash
    assert second["responsibility_boundary"]["session_id"] == "session-a"


def test_new_session_starts_clean_rth_state() -> None:
    session_store = InMemorySessionStore()
    a = _run(transcript="同じ入力", metadata={}, session_id="s-1", session_store=session_store)
    b = _run(transcript="同じ入力", metadata={}, session_id="s-2", session_store=session_store)
    assert (
        a["responsibility_boundary"]["rth_snapshot"]["hash_hex"]
        == b["responsibility_boundary"]["rth_snapshot"]["hash_hex"]
    )


def test_duplicate_transcript_in_same_session_is_detected() -> None:
    session_store = InMemorySessionStore()
    _run(transcript="同じ入力", metadata={}, session_id="dup", session_store=session_store)
    second = _run(transcript="同じ入力", metadata={}, session_id="dup", session_store=session_store)
    rb = second["responsibility_boundary"]
    assert rb["execution_allowed"] is False
    assert "session_transcript_replay_detected" in rb["reasons"]


def test_rth_evidence_exposes_snapshot_only_not_raw_text() -> None:
    result = _run(transcript="機密の文言", metadata={}, session_id="safe-ev")
    snapshot = result["responsibility_boundary"]["rth_snapshot"]
    assert "hash_hex" in snapshot
    assert "last_text" not in snapshot
