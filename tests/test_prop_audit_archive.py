from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from po_echo.audit_archive import (
    WEEK_ID_PATTERN,
    CommandOutcome,
    classify_pytest_outcome,
    ensure_weekly_archive,
    has_failures,
    iso_week_id,
)


@given(st.dates(min_value=date(2000, 1, 1), max_value=date(2100, 12, 31)))
def test_iso_week_id_matches_canonical_pattern(d: date) -> None:
    week_id = iso_week_id(d)
    assert WEEK_ID_PATTERN.match(week_id)


@given(st.integers(min_value=2000, max_value=2100), st.integers(min_value=1, max_value=53))
def test_ensure_weekly_archive_uses_fixed_filename_contract(year: int, week: int) -> None:
    with tempfile.TemporaryDirectory() as td:
        week_id = f"{year:04d}-W{week:02d}"
        archive = ensure_weekly_archive(Path(td), week_id)

        assert archive.base_dir.exists()
        assert archive.benchmark_voice_boundary_log.name == "benchmark_voice_boundary.txt"
        assert archive.benchmark_rth_log.name == "benchmark_rth.txt"
        assert archive.demo_c_receipt.name == "demo_c_receipt.json"
        assert archive.registry_snapshot.name == "registry_snapshot.json"
        assert archive.triage_note.name == "triage_note.md"


@given(st.text(), st.text())
def test_classify_pytest_outcome_marks_success_as_pass(stdout: str, stderr: str) -> None:
    assert classify_pytest_outcome(0, stdout, stderr) == "PASS"


@given(st.text(), st.text())
def test_classify_pytest_outcome_marks_pytest_skip_exit_as_skipped(stdout: str, stderr: str) -> None:
    combined = f"{stdout}\n{stderr}\n1 skipped"
    assert classify_pytest_outcome(5, combined, "") == "SKIPPED"


@given(st.integers().filter(lambda n: n not in {0, 5}), st.text(), st.text())
def test_classify_pytest_outcome_other_nonzero_is_fail(rc: int, stdout: str, stderr: str) -> None:
    assert classify_pytest_outcome(rc, stdout, stderr) == "FAIL"


@given(
    st.lists(
        st.sampled_from(["PASS", "SKIPPED", "FAIL"]),
        min_size=1,
        max_size=20,
    )
)
def test_has_failures_matches_status_membership(statuses: list[str]) -> None:
    outcomes = [CommandOutcome(name=f"cmd-{idx}", return_code=0, status=status) for idx, status in enumerate(statuses)]
    assert has_failures(outcomes) is ("FAIL" in statuses)
