"""Tests for po-cosmic device CLI subcommand.

不変原則検証:
    - device コマンドが responsibility_boundary を必ず含む出力を返す
    - high-bias / replay / tamper で execution_allowed = False となる
    - --list-devices / --show-schema が安全に動作する
    - --require-execution-allowed で blocked 時に exit code 3 を返す
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# repo src をパスに追加（CLI 直接 import 用）
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from po_cosmic.cli import main


def _run(argv: list[str]) -> None:
    sys.argv = ["po-cosmic"] + argv
    main()


def test_device_booking_smart_speaker(capsys) -> None:
    """SmartSpeaker booking → medium risk, voice_passphrase。"""
    _run(["device", "--device", "smart_speaker", "--intent", "booking"])
    out = capsys.readouterr().out
    assert "voice_passphrase" in out
    assert "medium" in out
    assert "責任境界" in out


def test_device_payment_smart_watch(capsys) -> None:
    """SmartWatch payment → high risk, app_confirm。"""
    _run(["device", "--device", "smart_watch", "--intent", "payment"])
    out = capsys.readouterr().out
    assert "high" in out
    assert "app_confirm" in out


def test_device_ar_glasses_gaze_confirm(capsys) -> None:
    """ARGlasses booking → medium risk, gaze_confirm。"""
    _run(["device", "--device", "ar_glasses", "--intent", "booking"])
    out = capsys.readouterr().out
    assert "gaze_confirm" in out


def test_device_high_bias_blocks(capsys) -> None:
    """bias_score >= threshold → BLOCKED (execution_allowed=False)。"""
    _run(["device", "--device", "smart_speaker", "--intent", "search", "--bias-score", "0.6"])
    out = capsys.readouterr().out
    assert "BLOCKED" in out


def test_device_replay_blocks(capsys) -> None:
    """--replay-detected → BLOCKED。"""
    _run(["device", "--device", "earworn", "--intent", "search", "--replay-detected"])
    out = capsys.readouterr().out
    assert "BLOCKED" in out


def test_device_tamper_blocks(capsys) -> None:
    """--tamper-detected → BLOCKED。"""
    _run(["device", "--device", "ar_glasses", "--intent", "summary", "--tamper-detected"])
    out = capsys.readouterr().out
    assert "BLOCKED" in out


def test_regression_cli_utility_list_devices_works_without_dummy_intent(capsys) -> None:
    """Regression: --list-devices must not require unrelated --intent arguments."""
    _run(["device", "--list-devices"])
    out = capsys.readouterr().out
    for dev in ("earworn", "smart_speaker", "smart_watch", "ar_glasses"):
        assert dev in out


def test_regression_cli_utility_show_schema_works_without_dummy_intent(capsys) -> None:
    """Regression: --show-schema must not require unrelated --intent arguments."""
    _run(["device", "--show-schema"])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "input_schema" in parsed
    assert "output_schema" in parsed


def test_device_out_writes_json(tmp_path: Path, capsys) -> None:
    """--out でファイルに responsibility_boundary が保存される。"""
    out_file = tmp_path / "device_result.json"
    _run(["device", "--device", "smart_watch", "--intent", "booking", "--out", str(out_file)])
    assert out_file.exists()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    rb = data["responsibility_boundary"]
    assert rb["device"] == "smart_watch"
    assert rb["channel"] == "audio"
    assert "requires_human_confirm" in rb
    assert "execution_allowed" in rb


def test_device_require_execution_allowed_exits_3(capsys) -> None:
    """execution_allowed=False 時に --require-execution-allowed で exit code 3。"""
    with pytest.raises(SystemExit) as exc_info:
        _run([
            "device",
            "--device", "earworn",
            "--intent", "search",
            "--bias-score", "0.9",
            "--require-execution-allowed",
        ])
    assert exc_info.value.code == 3


def test_device_invalid_meta_exits_1(capsys) -> None:
    """--meta に不正 JSON を渡すと exit code 1。"""
    with pytest.raises(SystemExit) as exc_info:
        _run(["device", "--intent", "booking", "--meta", "{invalid json"])
    assert exc_info.value.code == 1


def test_device_requires_intent_for_runtime_path() -> None:
    """Runtime path must still fail closed when --intent is missing."""
    with pytest.raises(SystemExit) as exc_info:
        _run(["device", "--device", "earworn"])
    assert exc_info.value.code == 1


# --- Echo Mark signing tests ---

def test_device_sign_hmac_produces_echo_mark(tmp_path: Path, monkeypatch, capsys) -> None:
    """--sign generates echo_mark in output JSON (HMAC mode)。"""
    import os
    monkeypatch.setenv("ECHO_MARK_SECRET", "test-secret-16chars!")
    out_file = tmp_path / "signed.json"
    _run([
        "device", "--device", "smart_watch", "--intent", "booking",
        "--sign", "--sig-mode", "hmac",
        "--out", str(out_file),
    ])
    assert out_file.exists()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert "echo_mark" in data
    em = data["echo_mark"]
    assert "label" in em
    assert em["label"] in {"ECHO_VERIFIED", "ECHO_CHECK", "ECHO_BLOCKED"}
    assert "payload" in em
    assert "payload_hash" in em
    assert "schema_version" in em
    out = capsys.readouterr().out
    assert "HMAC signature" in out


def test_device_sign_label_blocked_when_execution_blocked(tmp_path: Path, monkeypatch) -> None:
    """高バイアス blocked decision → Echo Mark label は ECHO_BLOCKED。"""
    monkeypatch.setenv("ECHO_MARK_SECRET", "test-secret-16chars!")
    out_file = tmp_path / "signed_blocked.json"
    _run([
        "device", "--device", "smart_speaker", "--intent", "search",
        "--bias-score", "0.8",
        "--sign", "--sig-mode", "hmac",
        "--out", str(out_file),
    ])
    data = json.loads(out_file.read_text(encoding="utf-8"))
    em = data["echo_mark"]
    assert em["label"] == "ECHO_BLOCKED"


def test_device_sign_label_echo_check_for_medium_risk(tmp_path: Path, monkeypatch) -> None:
    """medium risk execution_allowed → Echo Mark label は ECHO_CHECK。"""
    monkeypatch.setenv("ECHO_MARK_SECRET", "test-secret-16chars!")
    out_file = tmp_path / "signed_check.json"
    _run([
        "device", "--device", "smart_speaker", "--intent", "booking",
        "--sign", "--sig-mode", "hmac",
        "--out", str(out_file),
    ])
    data = json.loads(out_file.read_text(encoding="utf-8"))
    rb = data["responsibility_boundary"]
    em = data["echo_mark"]
    # medium risk → requires_human_confirm=True, execution_allowed=True → ECHO_CHECK
    assert rb["execution_allowed"] is True
    assert rb["requires_human_confirm"] is True
    assert em["label"] == "ECHO_CHECK"


def test_device_sign_payload_contains_device_info(tmp_path: Path, monkeypatch) -> None:
    """署名ペイロードの reasons に device/intent が含まれる（監査追跡性）。"""
    monkeypatch.setenv("ECHO_MARK_SECRET", "test-secret-16chars!")
    out_file = tmp_path / "signed_payload.json"
    _run([
        "device", "--device", "ar_glasses", "--intent", "booking",
        "--sign", "--sig-mode", "hmac",
        "--out", str(out_file),
    ])
    data = json.loads(out_file.read_text(encoding="utf-8"))
    em = data["echo_mark"]
    reasons = em["payload"]["reasons"]
    reasons_str = " ".join(reasons)
    assert "device:ar_glasses" in reasons_str
    assert "intent:booking" in reasons_str


def test_device_sign_missing_secret_exits_1(monkeypatch) -> None:
    """ECHO_MARK_SECRET 未設定で --sign → exit code 1。"""
    monkeypatch.delenv("ECHO_MARK_SECRET", raising=False)
    monkeypatch.delenv("ECHO_MARK_KEY_STORE", raising=False)
    with pytest.raises(SystemExit) as exc_info:
        _run([
            "device", "--device", "earworn", "--intent", "booking",
            "--sign", "--sig-mode", "hmac",
        ])
    assert exc_info.value.code == 1
