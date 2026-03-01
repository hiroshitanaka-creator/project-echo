from __future__ import annotations

import logging
from typing import get_args

import pytest

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies

from po_echo.voice_boundary import (
    FieldName,
    ScreenlessSafetyConfig,
    _safe_float,
    classify_risk,
    evaluate_screenless_safety,
    get_voice_boundary_policy,
)


def test_safe_float_warning_is_emitted_for_invalid_amount(caplog) -> None:
    """不正なamount入力時に警告ログを出しつつ動作継続する。"""
    with caplog.at_level(logging.WARNING):
        risk = classify_risk("search", {"amount": "not-a-number"})

    assert risk == "low"
    assert any("voice_boundary_invalid_float field=amount" in m for m in caplog.messages)


@settings(max_examples=300)
@given(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
def test_voice_boundary_collision_profile_is_stable(bias_score: float) -> None:
    """多数スキャンでriskバケット衝突プロファイルが想定内で安定する。"""
    policy = get_voice_boundary_policy(bias_score=bias_score, is_gumdrop=True)
    assert policy["risk"] in {"low", "medium", "high"}
    assert policy["required_action"] in {"none", "double_tap", "app_confirm"}
    assert policy["is_gumdrop"] is True


def test_safe_float_field_name_literal_enum_is_complete() -> None:
    """FieldName Literalに現在運用で使用するフィールドが列挙されている。"""
    assert set(get_args(FieldName)) == {"amount", "bias_score", "battery_level"}
    assert _safe_float("0.5", default=0.0, field_name="bias_score") == 0.5


@settings(max_examples=250)
@given(
    amount=st.one_of(
        st.none(),
        st.integers(min_value=-100_000, max_value=100_000),
        st.floats(min_value=0.0, max_value=200_000.0, allow_nan=False, allow_infinity=False),
        st.text(min_size=0, max_size=10),
    ),
    bias_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    battery_level=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    bluetooth_connected=st.booleans(),
    replay_detected=st.booleans(),
    tamper_detected=st.booleans(),
)
def test_screenless_semantic_delta_amount_edge_cases(
    amount,
    bias_score: float,
    battery_level: float,
    bluetooth_connected: bool,
    replay_detected: bool,
    tamper_detected: bool,
) -> None:
    """semantic_delta + amount + screenless複合条件でも安全判定が破綻しない。"""
    risk = classify_risk("semantic_delta", {"amount": amount})
    decision = evaluate_screenless_safety(
        bias_score=bias_score,
        battery_level=battery_level,
        bluetooth_connected=bluetooth_connected,
        replay_detected=replay_detected,
        tamper_detected=tamper_detected,
        config=ScreenlessSafetyConfig(),
    )

    assert risk in {"low", "medium", "high"}
    assert decision["fallback_mode"] in {"normal", "on_device_safe_mode"}
    if replay_detected or tamper_detected or bias_score >= ScreenlessSafetyConfig().high_bias_block_threshold:
        assert decision["execution_allowed"] is False
        assert decision["required_action"] == "app_confirm"
