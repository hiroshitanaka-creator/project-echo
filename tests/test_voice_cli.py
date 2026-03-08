"""Smoke tests for po-cosmic voice CLI orchestration."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLI = ["/root/.pyenv/shims/python3.11", str(ROOT / "bin" / "po-cosmic")]


def _write_audit(path: Path) -> None:
    payload = {
        "final_set": [
            {"title": "A", "merchant": "m1", "price": 1000, "utility": 0.8, "bias_risk": 0.2},
            {"title": "B", "merchant": "m2", "price": 1300, "utility": 0.7, "bias_risk": 0.3},
        ],
        "commercial_bias_original": {"overall_bias_score": 0.42},
        "commercial_bias_final": {"overall_bias_score": 0.21},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _base_env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYENV_VERSION"] = "3.11.14"
    return env


def _env_with_signing_keys() -> dict[str, str]:
    env = _base_env()
    env["ECHO_MARK_SECRET"] = "test-secret-1234567890"
    env["ECHO_MARK_PRIVATE_KEY"] = (
        "1f1e1d1c1b1a19181716151413121110"
        "0f0e0d0c0b0a09080706050403020100"
    )
    return env


def test_voice_cli_fails_for_missing_required_input(tmp_path: Path) -> None:
    audit = tmp_path / "audit.json"
    _write_audit(audit)
    out = tmp_path / "voice.json"

    proc = subprocess.run(
        [*CLI, "voice", "--intent", "search", "--in", str(audit), "--out", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=_base_env(),
    )

    assert proc.returncode != 0
    assert "transcript" in proc.stderr.lower()


def test_voice_cli_fails_when_signing_key_missing(tmp_path: Path) -> None:
    audit = tmp_path / "audit.json"
    _write_audit(audit)
    out = tmp_path / "voice.json"

    env = _base_env()
    env.pop("ECHO_MARK_PRIVATE_KEY", None)
    env["ECHO_MARK_SECRET"] = "test-secret-1234567890"

    proc = subprocess.run(
        [
            *CLI,
            "voice",
            "--intent",
            "search",
            "--transcript",
            "候補を見せて",
            "--meta",
            "{}",
            "--in",
            str(audit),
            "--out",
            str(out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=env,
    )

    assert proc.returncode == 1
    assert "ECHO_MARK_PRIVATE_KEY not set" in proc.stderr


def test_voice_cli_fails_on_dangerous_or_unconfirmed_action(tmp_path: Path) -> None:
    audit = tmp_path / "audit.json"
    _write_audit(audit)
    out = tmp_path / "voice.json"

    proc = subprocess.run(
        [
            *CLI,
            "voice",
            "--intent",
            "payment",
            "--transcript",
            "3万円で支払って",
            "--meta",
            '{"amount": 30000}',
            "--in",
            str(audit),
            "--out",
            str(out),
            "--require-execution-allowed",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=_env_with_signing_keys(),
    )

    assert proc.returncode == 3
    assert "dangerous_or_unconfirmed_action_blocked" in proc.stderr


def test_voice_cli_show_schema_outputs_fixed_contract(tmp_path: Path) -> None:
    """Why: CLI契約を固定し、運用チームがI/O仕様を機械検証できる状態を保つ。"""
    proc = subprocess.run(
        [
            *CLI,
            "voice",
            "--intent",
            "search",
            "--transcript",
            "schema only",
            "--in",
            str(tmp_path / "unused-in.json"),
            "--out",
            str(tmp_path / "unused-out.json"),
            "--show-schema",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=_base_env(),
    )

    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert "input_schema" in payload
    assert "output_schema" in payload
    assert payload["input_schema"].get("type") == "object"
    assert payload["output_schema"].get("type") == "object"


def test_voice_cli_succeeds_for_safe_search_flow(tmp_path: Path) -> None:
    """Why: P1導線として voice サブコマンドが実行可能であることを継続保証する。"""
    audit = tmp_path / "audit.json"
    _write_audit(audit)
    out = tmp_path / "voice.json"

    proc = subprocess.run(
        [
            *CLI,
            "voice",
            "--intent",
            "search",
            "--transcript",
            "候補を比較したい",
            "--meta",
            "{}",
            "--in",
            str(audit),
            "--out",
            str(out),
            "--simulate-ok",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=_env_with_signing_keys(),
    )

    if proc.returncode != 0 and "PyNaCl not installed" in proc.stderr:
        # Why: subprocess側の実行Pythonに依存が無い環境では、成功系検証を安全にスキップする。
        pytest.skip("PyNaCl missing in CLI runtime interpreter")

    assert proc.returncode == 0
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data.get("candidate_set"), list)
    assert len(data["candidate_set"]) >= 1
    assert isinstance(data.get("evidence"), list)
    assert data.get("responsibility_boundary", {}).get("ai_recommends") is False
    assert "voice" == data.get("responsibility_boundary", {}).get("channel")
    assert isinstance(data.get("echo_mark"), dict)
