"""Tests for sentinel.py requirements scanner CLI behavior."""

from __future__ import annotations

import pytest

from po_echo.sentinel import run_audit


def test_run_audit_missing_file_exits_with_error(capsys: pytest.CaptureFixture[str]) -> None:
    """Missing file path must fail gracefully without KeyError."""
    with pytest.raises(SystemExit) as exc_info:
        run_audit("/tmp/this-file-does-not-exist-echo.txt")

    out = capsys.readouterr().out
    assert exc_info.value.code == 1
    assert "[ERROR] File not found" in out
