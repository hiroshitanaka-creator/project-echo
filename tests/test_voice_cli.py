"""Smoke tests for po-cosmic voice CLI orchestration."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

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
