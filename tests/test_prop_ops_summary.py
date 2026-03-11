from __future__ import annotations

import tempfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from po_echo.ops_summary import build_integrated_summary


@given(
    st.lists(
        st.tuples(
            st.integers(min_value=2024, max_value=2030),
            st.integers(min_value=1, max_value=53),
        ),
        min_size=1,
        max_size=30,
    )
)
def test_build_integrated_summary_selects_latest_week(week_values: list[tuple[int, int]]) -> None:
    # Why: use a fresh tmpdir per example so hypothesis state doesn't bleed
    # across shrunk examples (function-scoped fixtures are not reset between runs).
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for year, week in week_values:
            (root / "reports" / "audit" / f"{year:04d}-W{week:02d}").mkdir(parents=True, exist_ok=True)

        expected = max(week_values)
        payload = build_integrated_summary(root)

        assert payload["weekly"]["latest_week_id"] == f"{expected[0]:04d}-W{expected[1]:02d}"


@given(
    st.lists(
        st.tuples(
            st.integers(min_value=2024, max_value=2030),
            st.integers(min_value=1, max_value=12),
        ),
        min_size=1,
        max_size=30,
    )
)
def test_build_integrated_summary_selects_latest_month(month_values: list[tuple[int, int]]) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for year, month in month_values:
            month_dir = root / "reports" / "gift_rehearsal" / f"{year:04d}-{month:02d}"
            month_dir.mkdir(parents=True, exist_ok=True)

        expected = max(month_values)
        payload = build_integrated_summary(root)

        assert payload["monthly"]["latest_month_id"] == f"{expected[0]:04d}-{expected[1]:02d}"
