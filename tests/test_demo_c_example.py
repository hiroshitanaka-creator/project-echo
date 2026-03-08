"""Tests for Demo C signed receipt CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_C = [sys.executable, str(ROOT / "docs" / "demo_c_example.py")]


def test_demo_c_requires_explicit_signing_key() -> None:
    proc = subprocess.run(
        [*DEMO_C],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert proc.returncode != 0
    assert "Missing signing key material" in proc.stderr


def test_demo_c_hmac_mode_emits_verifiable_receipt() -> None:
    proc = subprocess.run(
        [*DEMO_C, "--hmac-secret", "test-secret-123", "--pretty"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload.get("demo") == "Demo C"
    assert payload.get("task") == "ECHO-20260305-002"
    assert payload.get("verification", {}).get("status") == "VERIFIED"
    assert payload.get("echo_mark_badge", {}).get("verification_method") in {"HMAC", "Ed25519+HMAC"}
