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

_OUTPUT_SCHEMA_KEYS = ("candidate_set", "evidence", "responsibility_boundary", "voice_text", "echo_mark")


def _make_payload(**kwargs: object) -> VoiceFlowInput:
    defaults: dict = {
        "intent": "search",
        "transcript": "候補を比較したい",
        "metadata": {},
        "simulate_ok": True,
    }
    defaults.update(kwargs)
    return VoiceFlowInput(**defaults)  # type: ignore[arg-type]


def _run(**kwargs: object) -> dict:
    payload_kwargs = {k: v for k, v in kwargs.items() if k in VoiceFlowInput.__dataclass_fields__}
    run_kwargs = {k: v for k, v in kwargs.items() if k not in VoiceFlowInput.__dataclass_fields__}
    payload = _make_payload(**payload_kwargs)
    return run_voice_flow(
        audit=_AUDIT_BASE,
        payload=payload,
        hmac_secret=_HMAC_SECRET,
        ed25519_private_key=_ED25519_KEY,
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


def test_responsibility_boundary_ai_never_recommends() -> None:
    """Invariant: ai_recommends must always be False."""
    result = _run(intent="search", transcript="候補を見せて", metadata={})
    rb = result["responsibility_boundary"]
    assert rb.get("ai_recommends") is False, "Invariant violated: ai_recommends must be False"


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
        run_voice_flow(
            audit=_AUDIT_BASE,
            payload=payload,
            hmac_secret=_HMAC_SECRET,
            ed25519_private_key=_ED25519_KEY,
            require_execution_allowed=True,
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
    assert "echo_mark" in evidence_types, (
        f"echo_mark evidence missing; got types: {evidence_types}"
    )
