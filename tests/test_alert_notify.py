"""Tests for alert_notify helpers.

Why: notification envelope is the contract boundary between automated ops
detection and external routing. We verify severity mapping, flag pass-through,
evidence link generation, and file persistence.
"""

from __future__ import annotations

import json

from po_echo.alert_notify import build_alert_notification, write_alert_notification

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_summary(
    has_reported_failures: bool = False,
    has_malformed_artifact: bool = False,
    week_id: str = "2026-W10",
    month_id: str = "2026-03",
) -> dict:
    return {
        "overall": {
            "has_reported_failures": has_reported_failures,
            "has_malformed_artifact": has_malformed_artifact,
            "has_weekly_and_monthly": True,
            "latest_windows": {
                "week_id": week_id,
                "month_id": month_id,
            },
        },
        "weekly": {},
        "monthly": {},
    }


# ---------------------------------------------------------------------------
# Severity mapping
# ---------------------------------------------------------------------------

def test_no_flags_yields_no_alert() -> None:
    result = build_alert_notification(_make_summary())
    assert result["has_alert"] is False
    assert result["severity"] == "NONE"


def test_reported_failures_only_yields_sev2() -> None:
    result = build_alert_notification(_make_summary(has_reported_failures=True))
    assert result["has_alert"] is True
    assert result["severity"] == "SEV-2"


def test_malformed_only_yields_sev3() -> None:
    result = build_alert_notification(_make_summary(has_malformed_artifact=True))
    assert result["has_alert"] is True
    assert result["severity"] == "SEV-3"


def test_both_flags_yields_sev1() -> None:
    result = build_alert_notification(
        _make_summary(has_reported_failures=True, has_malformed_artifact=True)
    )
    assert result["has_alert"] is True
    assert result["severity"] == "SEV-1"


# ---------------------------------------------------------------------------
# Flags pass-through
# ---------------------------------------------------------------------------

def test_flags_match_input() -> None:
    result = build_alert_notification(_make_summary(has_reported_failures=True))
    assert result["flags"]["has_reported_failures"] is True
    assert result["flags"]["has_malformed_artifact"] is False


# ---------------------------------------------------------------------------
# Evidence links
# ---------------------------------------------------------------------------

def test_evidence_contains_weekly_and_monthly_refs() -> None:
    result = build_alert_notification(_make_summary(), summary_path="reports/operations/p2_integrated_summary.json")
    ev = result["evidence"]
    assert ev["latest_week_id"] == "2026-W10"
    assert ev["latest_month_id"] == "2026-03"
    assert "2026-W10" in ev["weekly_archive_dir"]
    assert "2026-03" in ev["monthly_archive_dir"]
    assert ev["kpi_delta_ref"].endswith("kpi_delta.md")
    assert ev["integrated_summary_path"] == "reports/operations/p2_integrated_summary.json"


def test_evidence_no_week_id_skips_weekly_links() -> None:
    summary = {
        "overall": {
            "has_reported_failures": False,
            "has_malformed_artifact": False,
            "latest_windows": {"week_id": None, "month_id": None},
        }
    }
    result = build_alert_notification(summary)
    assert "weekly_archive_dir" not in result["evidence"]
    assert "monthly_archive_dir" not in result["evidence"]


# ---------------------------------------------------------------------------
# Required envelope keys
# ---------------------------------------------------------------------------

def test_envelope_has_required_keys() -> None:
    result = build_alert_notification(_make_summary())
    for key in ("has_alert", "severity", "flags", "evidence", "responsibility_boundary", "generated_at_utc"):
        assert key in result, f"missing key: {key}"


def test_responsibility_boundary_present() -> None:
    result = build_alert_notification(_make_summary())
    rb = result["responsibility_boundary"]
    assert "automation_scope" in rb
    assert "human_scope" in rb


# ---------------------------------------------------------------------------
# File persistence
# ---------------------------------------------------------------------------

def test_write_alert_notification_creates_file(tmp_path) -> None:
    summary = _make_summary(has_reported_failures=True)
    payload, out_path = write_alert_notification(root=tmp_path, summary=summary)
    assert out_path.exists()
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["has_alert"] is True
    assert written["severity"] == "SEV-2"


def test_write_alert_notification_custom_out(tmp_path) -> None:
    custom = tmp_path / "custom_alert.json"
    payload, out_path = write_alert_notification(root=tmp_path, summary=_make_summary(), out_path=custom)
    assert out_path == custom
    assert custom.exists()
