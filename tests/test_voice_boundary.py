from __future__ import annotations

import logging
from typing import get_args

import pytest

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies

from po_core.diversity import Rec, diversify_with_mmr
from po_echo.voice_boundary import (
    FieldName,
    ScreenlessSafetyConfig,
    _safe_float,
    classify_risk,
    evaluate_screenless_safety,
    get_voice_boundary_policy,
)
from tests.invariant_logging import assert_or_log
from tests.strategies_adversarial import command_session_adversarial

STATE_TRANSITION_INVARIANTS = {
    "never_recommend": "おすすめ禁止",
    "multiple_candidates": "候補複数提示",
    "boundary_integrity": "責任境界の保持",
    "conservative_on_danger": "危険時は保守側判定",
}


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


def _assert_boundary_invariants_for_session(session: list[str], mode: str) -> None:
    joined = " ".join(session).lower()
    danger = any(k in joined for k in ["中断", "戻る", "違う", "自動", "確定"])

    recs = [
        Rec("r1", "A", "M1", "cat", 4000, ("tag",), 0.8, 0.9, 0.2),
        Rec("r2", "B", "M2", "cat", 6000, ("tag",), 0.79, 0.88, 0.25),
        Rec("r3", "C", "M3", "cat", 8000, ("tag",), 0.77, 0.85, 0.3),
        Rec("r4", "D", "M4", "cat", 10000, ("tag",), 0.75, 0.83, 0.35),
    ]
    if danger:
        recs = [
            Rec("r1", "Risk A", "Mono", "cat", 16000, ("tag",), 0.9, 0.4, 0.95),
            Rec("r2", "Risk B", "Mono", "cat", 17000, ("tag",), 0.88, 0.35, 0.9),
            Rec("r3", "Risk C", "Mono", "cat", 18000, ("tag",), 0.87, 0.34, 0.92),
        ]

    result = diversify_with_mmr(recs, [], k=min(3, len(recs)))
    boundary = result["responsibility_boundary"]
    repro = {"session": session, "danger": danger, "boundary": boundary}

    assert_or_log(
        condition=boundary["ai_recommends"] is False,
        test_name="test_voice_boundary_state_transition_invariants",
        mode=mode,
        repro_input=repro,
        message=STATE_TRANSITION_INVARIANTS["never_recommend"],
    )
    assert_or_log(
        condition=len(result["final_set"]) >= 2,
        test_name="test_voice_boundary_state_transition_invariants",
        mode=mode,
        repro_input=repro,
        message=STATE_TRANSITION_INVARIANTS["multiple_candidates"],
    )
    assert_or_log(
        condition=(
            boundary.get("schema_version") == "1.0"
            and boundary.get("liability_mode") == "audit-only"
            and len(boundary.get("reasons", [])) > 0
        ),
        test_name="test_voice_boundary_state_transition_invariants",
        mode=mode,
        repro_input=repro,
        message=STATE_TRANSITION_INVARIANTS["boundary_integrity"],
    )
    if danger:
        auto_allowed = boundary["execution_allowed"] and not boundary["requires_human_confirm"]
        assert_or_log(
            condition=not auto_allowed,
            test_name="test_voice_boundary_state_transition_invariants",
            mode=mode,
            repro_input=repro,
            message=STATE_TRANSITION_INVARIANTS["conservative_on_danger"],
        )


@settings(max_examples=60, deadline=None, derandomize=True)
@given(command_session_adversarial)
def test_voice_boundary_state_transition_invariants_seed_fixed(session: list[str]) -> None:
    _assert_boundary_invariants_for_session(session, mode="seed_fixed")


@settings(max_examples=60, deadline=None)
@given(command_session_adversarial)
def test_voice_boundary_state_transition_invariants_normal_mode(session: list[str]) -> None:
    _assert_boundary_invariants_for_session(session, mode="normal")
