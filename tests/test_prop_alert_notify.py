"""Property-based tests for alert_notify.

Why: the notification envelope is a machine-readable contract consumed by
downstream routing tooling. Properties verify that severity mapping,
flag consistency, and responsibility_boundary are invariant across all
possible summary payloads operators might produce.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from po_echo.alert_notify import build_alert_notification

_VALID_SEVERITIES = {"SEV-1", "SEV-2", "SEV-3", "NONE"}
_REQUIRED_KEYS = {"has_alert", "severity", "flags", "evidence", "responsibility_boundary", "generated_at_utc"}


def _summary_strategy() -> st.SearchStrategy[dict]:
    """Generate arbitrary integrated summary payloads."""
    return st.fixed_dictionaries({
        "overall": st.fixed_dictionaries({
            "has_reported_failures": st.booleans(),
            "has_malformed_artifact": st.booleans(),
            "has_weekly_and_monthly": st.booleans(),
            "latest_windows": st.fixed_dictionaries({
                "week_id": st.one_of(st.none(), st.from_regex(r"\d{4}-W\d{2}", fullmatch=True)),
                "month_id": st.one_of(st.none(), st.from_regex(r"\d{4}-\d{2}", fullmatch=True)),
            }),
        }),
    })


@given(_summary_strategy())
def test_severity_always_in_valid_set(summary: dict) -> None:
    """Why: downstream routers pattern-match on severity; unknown values break routing."""
    result = build_alert_notification(summary)
    assert result["severity"] in _VALID_SEVERITIES


@given(_summary_strategy())
def test_has_alert_iff_any_flag_true(summary: dict) -> None:
    """Why: has_alert is the primary gate for alerting pipelines."""
    result = build_alert_notification(summary)
    overall = summary["overall"]
    expected = overall["has_reported_failures"] or overall["has_malformed_artifact"]
    assert result["has_alert"] is expected


@given(_summary_strategy())
def test_severity_none_when_no_flags(summary: dict) -> None:
    """Why: NONE must be returned when system is healthy so routers can suppress notifications."""
    overall = summary["overall"]
    if not overall["has_reported_failures"] and not overall["has_malformed_artifact"]:
        result = build_alert_notification(summary)
        assert result["severity"] == "NONE"
        assert result["has_alert"] is False


@given(_summary_strategy())
def test_severity_sev1_only_when_both_flags(summary: dict) -> None:
    """Why: SEV-1 must require both flags simultaneously."""
    result = build_alert_notification(summary)
    if result["severity"] == "SEV-1":
        assert summary["overall"]["has_reported_failures"] is True
        assert summary["overall"]["has_malformed_artifact"] is True


@given(_summary_strategy())
def test_envelope_always_has_required_keys(summary: dict) -> None:
    """Why: any missing key would silently break consumer tooling."""
    result = build_alert_notification(summary)
    missing = _REQUIRED_KEYS - set(result)
    assert missing == set(), f"missing keys: {missing}"


@given(_summary_strategy())
def test_flags_match_summary_flags(summary: dict) -> None:
    """Why: flag pass-through must be lossless for audit trail accuracy."""
    result = build_alert_notification(summary)
    assert result["flags"]["has_reported_failures"] is summary["overall"]["has_reported_failures"]
    assert result["flags"]["has_malformed_artifact"] is summary["overall"]["has_malformed_artifact"]


@given(_summary_strategy())
def test_responsibility_boundary_always_present_and_non_empty(summary: dict) -> None:
    """Why: responsibility_boundary is an invariant from AGENT.md — it must never be omitted."""
    result = build_alert_notification(summary)
    rb = result["responsibility_boundary"]
    assert isinstance(rb, dict)
    assert len(rb) >= 2
    assert "automation_scope" in rb
    assert "human_scope" in rb


@settings(max_examples=50)
@given(
    _summary_strategy(),
    st.one_of(st.none(), st.text(min_size=1, max_size=80)),
    st.one_of(st.none(), st.text(min_size=1, max_size=80)),
)
def test_summary_path_and_diff_path_stored_in_evidence(
    summary: dict, summary_path: str | None, diff_path: str | None
) -> None:
    """Why: evidence links must faithfully carry caller-provided paths."""
    result = build_alert_notification(summary, summary_path=summary_path, diff_path=diff_path)
    ev = result["evidence"]
    assert ev.get("integrated_summary_path") == summary_path
    assert ev.get("diff_path") == diff_path
