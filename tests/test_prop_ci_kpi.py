from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from po_echo.ci_kpi import evaluate_rth_tracker_entries, evaluate_voice_10k


@given(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
def test_prop_voice_threshold_monotonic(seconds: float) -> None:
    check = evaluate_voice_10k(seconds)
    assert check.passed is (seconds < 0.30)


@given(st.integers(min_value=0, max_value=10_000))
def test_prop_rth_threshold_monotonic(entries: int) -> None:
    check = evaluate_rth_tracker_entries(entries)
    assert check.passed is (entries <= 2000)
