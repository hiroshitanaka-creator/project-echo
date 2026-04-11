"""Regression tests for po-cosmic badge CLI argument contracts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLI = [sys.executable, str(ROOT / "bin" / "po-cosmic")]


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


def _env_with_hmac_key() -> dict[str, str]:
    env = _base_env()
    env["ECHO_MARK_SECRET"] = "test-secret-1234567890"
    return env


def test_badge_cli_accepts_documented_in_out_aliases(tmp_path: Path) -> None:
    """Regression: docs use --in/--out, so CLI must accept them."""
    audit = tmp_path / "audit.json"
    badge = tmp_path / "badge.json"
    _write_audit(audit)

    proc = subprocess.run(
        [*CLI, "badge", "--in", str(audit), "--out", str(badge)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=_env_with_hmac_key(),
    )

    if "cannot import name 'StrEnum'" in proc.stderr:
        pytest.skip("CLI runtime interpreter is Python <3.11 in this environment")

    assert proc.returncode == 0, proc.stderr
    assert badge.exists()


def test_badge_cli_positional_args_still_work(tmp_path: Path) -> None:
    """Backward compatibility: existing positional usage must remain valid."""
    audit = tmp_path / "audit.json"
    badge = tmp_path / "badge.json"
    _write_audit(audit)

    proc = subprocess.run(
        [*CLI, "badge", str(audit), str(badge)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=_env_with_hmac_key(),
    )

    if "cannot import name 'StrEnum'" in proc.stderr:
        pytest.skip("CLI runtime interpreter is Python <3.11 in this environment")

    assert proc.returncode == 0, proc.stderr
    assert badge.exists()


def test_badge_cli_accepts_mixed_flag_input_and_positional_output(tmp_path: Path) -> None:
    """Regression: `--in` plus one positional should treat positional as output."""
    audit = tmp_path / "audit.json"
    badge = tmp_path / "badge.json"
    _write_audit(audit)

    proc = subprocess.run(
        [*CLI, "badge", "--in", str(audit), str(badge)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=_env_with_hmac_key(),
    )

    if "cannot import name 'StrEnum'" in proc.stderr:
        pytest.skip("CLI runtime interpreter is Python <3.11 in this environment")

    assert proc.returncode == 0, proc.stderr
    assert badge.exists()


def test_badge_cli_rejects_conflicting_positional_and_flag_paths(tmp_path: Path) -> None:
    """Conflicting duplicate path inputs must fail closed instead of guessing."""
    audit = tmp_path / "audit.json"
    out_a = tmp_path / "badge-a.json"
    out_b = tmp_path / "badge-b.json"
    _write_audit(audit)

    proc = subprocess.run(
        [
            *CLI,
            "badge",
            str(audit),
            str(out_a),
            "--out",
            str(out_b),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=_env_with_hmac_key(),
    )

    if "cannot import name 'StrEnum'" in proc.stderr:
        pytest.skip("CLI runtime interpreter is Python <3.11 in this environment")

    assert proc.returncode == 1
    assert "ambiguous badge output path" in proc.stderr
