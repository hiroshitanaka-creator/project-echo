from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from po_echo.ops_summary import build_integrated_summary_diff


@given(
    st.dictionaries(keys=st.text(min_size=1, max_size=10), values=st.integers(), max_size=10),
    st.dictionaries(keys=st.text(min_size=1, max_size=10), values=st.integers(), max_size=10),
)
def test_build_integrated_summary_diff_changed_count_matches_field_list(
    previous_values: dict[str, int],
    current_values: dict[str, int],
) -> None:
    previous = {"weekly": previous_values, "overall": {"latest_windows": {"week_id": None, "month_id": None}}}
    current = {"weekly": current_values, "overall": {"latest_windows": {"week_id": None, "month_id": None}}}

    diff = build_integrated_summary_diff(previous=previous, current=current)

    assert diff["changed_field_count"] == len(diff["changed_fields"])
    assert diff["changed"] == (diff["changed_field_count"] > 0)
