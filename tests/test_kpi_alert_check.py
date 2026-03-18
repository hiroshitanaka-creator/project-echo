"""Tests for kpi_alert_check helpers.

Why: fill-check is a critical guardrail to prevent incomplete alert records.
We verify both positive (placeholder detected) and negative (clean file) paths,
plus boundary cases for individual token patterns.
"""

from __future__ import annotations

import pytest

from po_echo.kpi_alert_check import (
    check_kpi_alert_file,
    check_kpi_alert_text,
)

# ---------------------------------------------------------------------------
# Baseline: the unfilled template must itself fail the check.
# ---------------------------------------------------------------------------

_TEMPLATE_TEXT = """\
# P2 KPI Alert（初動テンプレート）

## 1) Alert Header
- alert_id: `ALERT-YYYYMMDD-XXX`
- week_id: `YYYY-Www`
- detected_at_utc: `<set-by-operator>`
- severity: `SEV-1|SEV-2|SEV-3`
- detector: `automation|operator`

## 2) Trigger
- metric_name: `<voice_boundary_min_seconds | rth_tracker_entries | demo_c_verification_status | ...>`
- observed_value: `<value>`
- threshold: `<value>`
- comparison: `< | > | >= | <= | ==`
- result: `BREACH`

## 6) Triage Outcome
- disposition: `mitigated | monitoring | blocked`
- mitigation_owner: `<name/team>`
- next_review_at_utc: `<timestamp>`
- notes:
  - `<short note 1>`
  - `<short note 2>`
"""

_FILLED_TEXT = """\
# P2 KPI Alert（初動テンプレート）

## 1) Alert Header
- alert_id: `ALERT-20260310-001`
- week_id: `2026-W10`
- detected_at_utc: `2026-03-10T09:00:00Z`
- severity: `SEV-2`
- detector: `automation`

## 2) Trigger
- metric_name: `voice_boundary_min_seconds`
- observed_value: `0.35`
- threshold: `0.3`
- comparison: `>`
- result: `BREACH`

## 6) Triage Outcome
- disposition: `monitoring`
- mitigation_owner: `ops-team`
- next_review_at_utc: `2026-03-11T09:00:00Z`
- notes:
  - `Increased latency observed after dependency upgrade.`
  - `Rollback window open.`
"""


def test_template_itself_is_invalid() -> None:
    result = check_kpi_alert_text(_TEMPLATE_TEXT)
    assert result.is_valid is False
    assert len(result.unfilled_placeholders) > 0


def test_filled_alert_is_valid() -> None:
    result = check_kpi_alert_text(_FILLED_TEXT)
    assert result.is_valid is True
    assert result.unfilled_placeholders == []


def test_result_to_dict_keys() -> None:
    result = check_kpi_alert_text(_FILLED_TEXT, path="reports/audit/2026-W10/kpi_alert.md")
    d = result.to_dict()
    assert "is_valid" in d
    assert "unfilled_placeholders" in d
    assert "checked_path" in d
    assert "responsibility_boundary" in d
    assert d["checked_path"] == "reports/audit/2026-W10/kpi_alert.md"


# ---------------------------------------------------------------------------
# Individual placeholder detection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("token,expected_desc", [
    ("ALERT-YYYYMMDD-XXX", "alert_id_placeholder"),
    ("YYYY-Www", "week_id_placeholder"),
    ("<set-by-operator>", "detected_at_placeholder"),
    ("SEV-1|SEV-2|SEV-3", "severity_placeholder"),
    ("automation|operator", "detector_placeholder"),
    ("<value>", "observed_value_placeholder"),
    ("mitigated | monitoring | blocked", "disposition_placeholder"),
    ("<name/team>", "mitigation_owner_placeholder"),
    ("<timestamp>", "next_review_placeholder"),
    ("<short note 1>", "notes_placeholder"),
])
def test_individual_placeholder_detected(token: str, expected_desc: str) -> None:
    text = f"some text with unfilled token: `{token}` here"
    result = check_kpi_alert_text(text)
    assert result.is_valid is False
    assert expected_desc in result.unfilled_placeholders


def test_empty_text_is_valid() -> None:
    # An empty file has no placeholders → passes the mechanical check.
    result = check_kpi_alert_text("")
    assert result.is_valid is True


# ---------------------------------------------------------------------------
# File-based check
# ---------------------------------------------------------------------------

def test_check_kpi_alert_file_valid(tmp_path) -> None:
    p = tmp_path / "kpi_alert.md"
    p.write_text(_FILLED_TEXT, encoding="utf-8")
    result = check_kpi_alert_file(p)
    assert result.is_valid is True
    assert result.checked_path == str(p)


def test_check_kpi_alert_file_invalid(tmp_path) -> None:
    p = tmp_path / "kpi_alert.md"
    p.write_text(_TEMPLATE_TEXT, encoding="utf-8")
    result = check_kpi_alert_file(p)
    assert result.is_valid is False
    assert len(result.unfilled_placeholders) > 0
