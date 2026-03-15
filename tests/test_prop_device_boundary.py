"""Property-based tests for device_boundary.py — multi-device adapter invariants.

不変原則検証:
    1. 全デバイスで high-risk → requires_human_confirm = True
    2. 全デバイスで high bias / replay / tamper → execution_allowed = False
    3. 全デバイスで責任境界 dict は必須キーを含む
    4. リスク分類はデバイスに依らず intent/meta で一意に決定される
    5. 登録デバイスすべてで decide_for_device がクラッシュしない
"""

from __future__ import annotations

import pytest

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies

from po_echo.device_boundary import (
    DEVICE_CONFIGS,
    DeviceType,
    decide_for_device,
    list_devices,
)
from po_echo.voice_boundary import CRITICAL_INTENTS, SENSITIVE_INTENTS

_ALL_DEVICES: list[DeviceType] = list_devices()

_DEVICE_ST = st.sampled_from(_ALL_DEVICES)
_INTENT_ST = st.one_of(
    st.sampled_from(sorted(CRITICAL_INTENTS | SENSITIVE_INTENTS | {"search", "summary"})),
    st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Ll", "Lu"))),
)
_BIAS_ST = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
_AMOUNT_ST = st.one_of(st.none(), st.integers(min_value=0, max_value=100_000))


@settings(max_examples=200)
@given(device=_DEVICE_ST, intent=_INTENT_ST, bias=_BIAS_ST, amount=_AMOUNT_ST)
def test_prop_high_risk_always_requires_confirm(
    device: DeviceType, intent: str, bias: float, amount
) -> None:
    """不変原則: どのデバイスでも high-risk intent は requires_human_confirm = True。"""
    meta = {"amount": amount} if amount is not None else None
    decision = decide_for_device(device, intent, meta=meta, bias_score=bias)
    if decision.risk == "high":
        assert decision.requires_human_confirm is True, (
            f"device={device}, intent={intent}: high-risk must require human confirm"
        )


@settings(max_examples=200)
@given(device=_DEVICE_ST, intent=_INTENT_ST)
def test_prop_high_bias_blocks_execution(device: DeviceType, intent: str) -> None:
    """不変原則: どのデバイスでも bias >= デバイス閾値 なら execution_allowed = False。"""
    threshold = DEVICE_CONFIGS[device].high_bias_block_threshold
    # 閾値以上のバイアスを与える
    decision = decide_for_device(device, intent, bias_score=threshold)
    assert decision.execution_allowed is False, (
        f"device={device}: bias >= {threshold} must block execution"
    )
    assert decision.requires_human_confirm is True


@settings(max_examples=150)
@given(device=_DEVICE_ST, intent=_INTENT_ST, bias=_BIAS_ST)
def test_prop_replay_blocks_execution(device: DeviceType, intent: str, bias: float) -> None:
    """不変原則: どのデバイスでも replay_detected = True なら execution_allowed = False。"""
    decision = decide_for_device(device, intent, bias_score=bias, replay_detected=True)
    assert decision.execution_allowed is False
    assert decision.requires_human_confirm is True


@settings(max_examples=150)
@given(device=_DEVICE_ST, intent=_INTENT_ST, bias=_BIAS_ST)
def test_prop_tamper_blocks_execution(device: DeviceType, intent: str, bias: float) -> None:
    """不変原則: どのデバイスでも tamper_detected = True なら execution_allowed = False。"""
    decision = decide_for_device(device, intent, bias_score=bias, tamper_detected=True)
    assert decision.execution_allowed is False
    assert decision.requires_human_confirm is True


@settings(max_examples=200)
@given(device=_DEVICE_ST, intent=_INTENT_ST, bias=_BIAS_ST, amount=_AMOUNT_ST)
def test_prop_responsibility_boundary_contract(
    device: DeviceType, intent: str, bias: float, amount
) -> None:
    """不変原則: 責任境界 dict には必須キーが常に含まれる。"""
    meta = {"amount": amount} if amount is not None else None
    decision = decide_for_device(device, intent, meta=meta, bias_score=bias)
    rb = decision.to_responsibility_boundary()

    required_keys = {
        "channel", "device", "risk", "required_action",
        "execution_allowed", "requires_human_confirm", "reasons",
    }
    missing = required_keys - set(rb.keys())
    assert not missing, f"responsibility_boundary missing keys: {missing}"
    assert rb["channel"] == "audio"
    assert rb["device"] == device
    assert isinstance(rb["reasons"], list)
    assert len(rb["reasons"]) >= 1


@settings(max_examples=200)
@given(intent=_INTENT_ST, bias=_BIAS_ST, amount=_AMOUNT_ST)
def test_prop_risk_classification_device_independent(
    intent: str, bias: float, amount
) -> None:
    """不変原則: リスク分類は intent / meta で決まり、デバイスに依存しない。"""
    meta = {"amount": amount} if amount is not None else None
    risks = {
        device: decide_for_device(device, intent, meta=meta, bias_score=bias).risk
        for device in _ALL_DEVICES
    }
    unique_risks = set(risks.values())
    assert len(unique_risks) == 1, (
        f"Risk classification must be device-independent. Got: {risks}"
    )


@settings(max_examples=100)
@given(device=_DEVICE_ST, intent=_INTENT_ST, bias=_BIAS_ST)
def test_prop_decision_reasons_contain_device_and_intent(
    device: DeviceType, intent: str, bias: float
) -> None:
    """reasons フィールドにデバイス種別と intent が常に含まれる（監査追跡性）。"""
    decision = decide_for_device(device, intent, bias_score=bias)
    reasons_str = " ".join(decision.reasons)
    assert f"device:{device}" in reasons_str
    assert f"intent:{intent}" in reasons_str


def test_all_registered_devices_are_reachable() -> None:
    """すべての登録デバイスで decide_for_device が正常完了する（smoke test）。"""
    for device in _ALL_DEVICES:
        dec = decide_for_device(device, "search", meta={"amount": 500}, bias_score=0.1)
        assert dec.risk in {"low", "medium", "high"}
        assert dec.device == device


def test_smart_speaker_uses_voice_passphrase_for_medium() -> None:
    """SmartSpeaker の medium リスクは voice_passphrase（タッチ不可デバイス制約）。"""
    dec = decide_for_device("smart_speaker", "booking", bias_score=0.0)
    assert dec.risk == "medium"
    assert dec.required_action == "voice_passphrase"


def test_smart_watch_uses_haptic_tap_for_medium() -> None:
    """SmartWatch の medium リスクは haptic_tap（ハプティクス確認）。"""
    dec = decide_for_device("smart_watch", "booking", bias_score=0.0)
    assert dec.risk == "medium"
    assert dec.required_action == "haptic_tap"


def test_ar_glasses_uses_gaze_confirm_for_medium() -> None:
    """ARGlasses の medium リスクは gaze_confirm（視線確認）。"""
    dec = decide_for_device("ar_glasses", "booking", bias_score=0.0)
    assert dec.risk == "medium"
    assert dec.required_action == "gaze_confirm"


def test_smart_speaker_stricter_bias_threshold() -> None:
    """SmartSpeaker は共有空間対応のため bias 閾値が earworn より厳しい。"""
    sp_thresh = DEVICE_CONFIGS["smart_speaker"].high_bias_block_threshold
    ew_thresh = DEVICE_CONFIGS["earworn"].high_bias_block_threshold
    assert sp_thresh <= ew_thresh, (
        "SmartSpeaker (shared space) should have stricter or equal bias threshold"
    )


def test_non_finite_bias_is_blocked_fail_closed() -> None:
    """NaN 入力は fail-closed で execution を必ずブロックする。"""
    for device in _ALL_DEVICES:
        dec = decide_for_device(device, "booking", bias_score="nan")
        assert dec.execution_allowed is False
        assert dec.requires_human_confirm is True
        assert dec.required_action == "app_confirm"
