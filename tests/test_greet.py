"""
Tests for Japanese greeting module.

AGENT.md 準拠: すべての新機能は property-based test 必須（Hypothesis使用）
property-based tests are skipped when hypothesis is not installed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from po_cosmic.greet import greet

try:
    from hypothesis import given
    from hypothesis import strategies as st

    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False


def test_greet_no_name() -> None:
    """Anonymous greeting always returns こんにちは！"""
    assert greet() == "こんにちは！"
    assert greet("") == "こんにちは！"


def test_greet_with_name() -> None:
    """Named greeting contains the name and こんにちは."""
    result = greet("田中")
    assert "こんにちは" in result
    assert "田中" in result


@pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
def test_greet_named_contains_konnichiwa() -> None:
    """Property: any non-empty name produces a greeting containing こんにちは."""

    @given(st.text(min_size=1))  # type: ignore[name-defined]
    def _inner(name: str) -> None:
        result = greet(name)
        assert "こんにちは" in result

    _inner()


@pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
def test_greet_named_contains_name() -> None:
    """Property: any non-empty name appears verbatim in the greeting."""

    @given(st.text(min_size=1))  # type: ignore[name-defined]
    def _inner(name: str) -> None:
        result = greet(name)
        assert name in result

    _inner()


@pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
def test_greet_always_returns_string() -> None:
    """Property: greet always returns a non-empty string for any input."""

    @given(st.text())  # type: ignore[name-defined]
    def _inner(name: str) -> None:
        result = greet(name)
        assert isinstance(result, str)
        assert len(result) > 0

    _inner()
