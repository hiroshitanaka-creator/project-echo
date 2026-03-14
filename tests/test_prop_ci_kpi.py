from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from po_echo.ci_kpi import (
    build_ci_kpi_markdown,
    evaluate_rth_tracker_entries,
    evaluate_voice_10k,
)


@given(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
def test_prop_voice_threshold_monotonic(seconds: float) -> None:
    check = evaluate_voice_10k(seconds)
    assert check.passed is (seconds < 0.30)


@given(st.integers(min_value=0, max_value=10_000))
def test_prop_rth_threshold_monotonic(entries: int) -> None:
    check = evaluate_rth_tracker_entries(entries)
    assert check.passed is (entries <= 2000)


@given(
    st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    st.integers(min_value=0, max_value=10_000),
)
def test_prop_markdown_contains_responsibility_boundary(seconds: float, entries: int) -> None:
    # PR comment に責任境界が必ず含まれることを検証する（不変原則）
    checks = [evaluate_voice_10k(seconds), evaluate_rth_tracker_entries(entries)]
    md = build_ci_kpi_markdown(checks)
    assert "責任境界" in md, "PR comment markdown must contain responsibility boundary"


@given(
    st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    st.integers(min_value=0, max_value=10_000),
)
def test_prop_markdown_pass_fail_consistent_with_checks(seconds: float, entries: int) -> None:
    # PR comment の PASS/FAIL 表示が KpiCheck.passed と一致することを検証する
    vc = evaluate_voice_10k(seconds)
    rc = evaluate_rth_tracker_entries(entries)
    md = build_ci_kpi_markdown([vc, rc])
    if vc.passed:
        assert "✅" in md
    else:
        assert "❌" in md


@given(
    st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    st.integers(min_value=0, max_value=10_000),
)
def test_prop_markdown_contains_evidence(seconds: float, entries: int) -> None:
    # PR comment に evidence キーワードが必ず含まれることを検証する
    checks = [evaluate_voice_10k(seconds), evaluate_rth_tracker_entries(entries)]
    md = build_ci_kpi_markdown(checks)
    assert "evidence" in md, "PR comment markdown must contain evidence links"
