from __future__ import annotations

import logging

from typing import get_args

from po_echo.voice_boundary import FieldName, _safe_float, classify_risk, get_voice_boundary_policy


def test_safe_float_warning_is_emitted_for_invalid_amount(caplog) -> None:
    """不正なamount入力時に警告ログを出しつつ動作継続する。"""
    with caplog.at_level(logging.WARNING):
        risk = classify_risk("search", {"amount": "not-a-number"})

    assert risk == "low"
    assert any("voice_boundary_invalid_float field=amount" in m for m in caplog.messages)


def test_voice_boundary_10k_collision_profile_is_stable() -> None:
    """10,000件スキャンでriskバケット衝突プロファイルが想定内で安定する。"""
    n = 10_000
    policies = [get_voice_boundary_policy(bias_score=i / n, is_gumdrop=True) for i in range(n)]

    risks = {p["risk"] for p in policies}
    assert risks == {"low", "medium", "high"}
    assert all(p["required_action"] in {"none", "double_tap", "app_confirm"} for p in policies)
    assert all(p["is_gumdrop"] is True for p in policies)


def test_safe_float_field_name_literal_enum_is_complete() -> None:
    """FieldName Literalに現在運用で使用するフィールドが列挙されている。"""
    assert set(get_args(FieldName)) == {"amount", "bias_score", "battery_level"}
    assert _safe_float("0.5", default=0.0, field_name="bias_score") == 0.5
