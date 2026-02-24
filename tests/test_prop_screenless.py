"""Property-based tests for screenless ambient audio channel defenses."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from po_echo.echo_mark import make_echo_mark_dual, verify_echo_mark_dual
from po_echo.rth import compute_rth
from po_echo.voice_boundary import (
    HIGH_BIAS_BLOCK_THRESHOLD,
    LOW_BATTERY_THRESHOLD,
    evaluate_screenless_safety,
    make_echo_verified_voice_text,
)

try:
    from nacl.encoding import HexEncoder
    from nacl.signing import SigningKey

    _test_key = SigningKey.generate()
    TEST_PRIVATE_KEY = _test_key.encode(HexEncoder).decode()
    ED25519_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    TEST_PRIVATE_KEY = ""
    ED25519_AVAILABLE = False


HMAC_SECRET = "screenless-prop-secret-123"
KEY_ID = "screenless_prop_v1"


def _normalize_rth_noise(text: str) -> str:
    """Normalize common screenless transcription noise before hashing."""
    return text.lower().translate(
        str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t"})
    )


def _hash_bit_distance(lhs_hex: str, rhs_hex: str) -> int:
    """Bit distance between two SHA-256 hex hashes."""
    return (int(lhs_hex, 16) ^ int(rhs_hex, 16)).bit_count()


def _audit(execution_allowed: bool, requires_human_confirm: bool) -> dict:
    return {
        "responsibility_boundary": {
            "execution_allowed": execution_allowed,
            "requires_human_confirm": requires_human_confirm,
            "liability_mode": "audit-only",
            "schema_version": "1.0",
            "reasons": ["prop_screenless"],
            "signals": {
                "bias_original": 0.7,
                "bias_final": 0.2,
                "bias_improvement": 0.5,
                "merchants_final": 3,
                "price_buckets_final": 2,
            },
        },
        "commercial_bias_original": {"overall_bias_score": 0.7},
        "commercial_bias_final": {"overall_bias_score": 0.2},
    }


@settings(max_examples=120, deadline=None)
@given(
    st.lists(
        st.text(
            min_size=1,
            max_size=8,
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
        ),
        min_size=1,
        max_size=10,
    ),
    st.data(),
)
def test_rth_stable_under_noise_permutations(base_words, data):
    # Project Echo 不変原則：画面無しデバイス時代の透明性防衛
    unique_words = sorted(set(w.lower() for w in base_words))
    permuted_core = data.draw(st.permutations(unique_words), label="permuted_core")
    duplicate_noise = data.draw(
        st.lists(st.sampled_from(unique_words), min_size=0, max_size=10),
        label="duplicate_noise",
    )
    variant_words = list(permuted_core) + duplicate_noise

    noise_prefix = data.draw(st.text(alphabet=" \t", max_size=4), label="noise_prefix")
    noise_suffix = data.draw(st.text(alphabet=" \t", max_size=4), label="noise_suffix")

    substitution_table = data.draw(
        st.dictionaries(
            st.sampled_from(list("013457")),
            st.sampled_from(list("oieast")),
            max_size=6,
        ),
        label="substitution_table",
    )

    canonical_text = " ".join(unique_words)
    noisy_text = noise_prefix + "\t  ".join(w.upper() for w in variant_words) + noise_suffix
    noisy_text = noisy_text.translate(str.maketrans(substitution_table))

    lhs = compute_rth(canonical_text)["hash_hex"]
    rhs = compute_rth(noisy_text)["hash_hex"]
    normalized_rhs = compute_rth(_normalize_rth_noise(noisy_text))["hash_hex"]

    assert lhs == normalized_rhs
    assert _hash_bit_distance(lhs, rhs) <= 160


@settings(max_examples=120, deadline=None)
@given(
    st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    st.booleans(),
)
def test_low_battery_or_bluetooth_disconnect_forces_safe_fallback(
    bias_score, battery_level, bluetooth_connected
):
    # Project Echo 不変原則：画面無しデバイス時代の透明性防衛
    result = evaluate_screenless_safety(
        bias_score=bias_score,
        battery_level=battery_level,
        bluetooth_connected=bluetooth_connected,
    )

    if battery_level < LOW_BATTERY_THRESHOLD or not bluetooth_connected:
        assert result["fallback_mode"] == "on_device_safe_mode"
    else:
        assert result["fallback_mode"] == "normal"


@settings(max_examples=100, deadline=None)
@given(
    st.integers(min_value=1, max_value=5),
    st.integers(min_value=1, max_value=8),
)
def test_echo_verified_voice_text_contains_candidate_evidence_and_boundary(
    candidate_count, evidence_count
):
    # Project Echo 不変原則：画面無しデバイス時代の透明性防衛
    boundary = {
        "required_action": "double_tap",
        "execution_allowed": True,
        "requires_human_confirm": True,
    }
    text = make_echo_verified_voice_text(candidate_count, evidence_count, boundary)

    assert "候補セット" in text
    assert "証拠" in text
    assert "責任境界" in text
    assert str(candidate_count) in text
    assert str(evidence_count) in text


@settings(max_examples=120, deadline=None)
@given(
    st.floats(
        min_value=HIGH_BIAS_BLOCK_THRESHOLD,
        max_value=1.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    st.booleans(),
    st.booleans(),
)
def test_high_bias_or_attack_signal_immediately_blocks_and_requires_human_check(
    bias_score, replay_detected, tamper_detected
):
    # Project Echo 不変原則：画面無しデバイス時代の透明性防衛
    result = evaluate_screenless_safety(
        bias_score=bias_score,
        battery_level=0.8,
        bluetooth_connected=True,
        replay_detected=replay_detected,
        tamper_detected=tamper_detected,
    )

    assert result["execution_allowed"] is False
    assert result["requires_human_confirm"] is True
    assert result["required_action"] == "app_confirm"


@settings(max_examples=120, deadline=None)
@given(
    st.floats(min_value=0.0, max_value=0.59, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0.2, max_value=1.0, allow_nan=False, allow_infinity=False),
    st.booleans(),
)
def test_replay_or_tamper_forces_block_even_when_bias_is_low(
    bias_score, battery_level, bluetooth_connected
):
    # Project Echo 不変原則：画面無しデバイス時代の透明性防衛
    result = evaluate_screenless_safety(
        bias_score=bias_score,
        battery_level=battery_level,
        bluetooth_connected=bluetooth_connected,
        replay_detected=True,
        tamper_detected=False,
    )
    assert result["execution_allowed"] is False
    assert result["requires_human_confirm"] is True


@settings(max_examples=100, deadline=None)
@given(st.text(min_size=1, max_size=20, alphabet="abcdef0123456789"))
def test_replay_and_payload_tamper_breaks_dual_signature_verification(tamper_text):
    # Project Echo 不変原則：画面無しデバイス時代の透明性防衛
    if not ED25519_AVAILABLE:
        return

    badge = make_echo_mark_dual(
        audit=_audit(execution_allowed=True, requires_human_confirm=False),
        hmac_secret=HMAC_SECRET,
        ed25519_private_key=TEST_PRIVATE_KEY,
        key_id=KEY_ID,
        run_id="screenless-prop",
    )

    ok = verify_echo_mark_dual(badge, hmac_secret=HMAC_SECRET)
    assert ok["status"] == "VERIFIED"

    tampered_badge = dict(badge)
    tampered_payload = dict(badge["payload"])
    tampered_payload["run_id"] = tamper_text
    tampered_badge["payload"] = tampered_payload

    blocked = verify_echo_mark_dual(tampered_badge, hmac_secret=HMAC_SECRET)
    assert blocked["status"] == "INVALID"
