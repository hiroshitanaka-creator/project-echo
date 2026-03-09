from __future__ import annotations

import json

from po_echo.ops_summary import build_integrated_summary, write_integrated_summary


def test_build_integrated_summary_returns_latest_windows(tmp_path) -> None:
    weekly_old = tmp_path / "reports" / "audit" / "2026-W08"
    weekly_new = tmp_path / "reports" / "audit" / "2026-W10"
    monthly_old = tmp_path / "reports" / "gift_rehearsal" / "2026-01"
    monthly_new = tmp_path / "reports" / "gift_rehearsal" / "2026-03"

    weekly_old.mkdir(parents=True)
    weekly_new.mkdir(parents=True)
    monthly_old.mkdir(parents=True)
    monthly_new.mkdir(parents=True)

    (weekly_new / "triage_note.md").write_text("# triage", encoding="utf-8")
    (weekly_new / "manifest.md").write_text("# manifest", encoding="utf-8")
    (weekly_new / "kpi_delta.md").write_text("# kpi", encoding="utf-8")

    summary = {"month_id": "2026-03", "status": "DRY_RUN", "manifest_consistent": True}
    (monthly_new / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (monthly_new / "triage_note.md").write_text("# triage\n- status: PASS", encoding="utf-8")
    (monthly_new / "manifest.md").write_text("# manifest", encoding="utf-8")

    payload = build_integrated_summary(tmp_path)

    assert payload["weekly"]["latest_week_id"] == "2026-W10"
    assert payload["monthly"]["latest_month_id"] == "2026-03"
    assert payload["monthly"]["summary"] == summary
    assert payload["monthly"]["summary_error"] is None
    assert payload["overall"]["has_weekly_and_monthly"] is True
    assert payload["overall"]["has_malformed_artifact"] is False


def test_build_integrated_summary_handles_invalid_monthly_summary_json(tmp_path) -> None:
    weekly = tmp_path / "reports" / "audit" / "2026-W10"
    monthly = tmp_path / "reports" / "gift_rehearsal" / "2026-03"
    weekly.mkdir(parents=True)
    monthly.mkdir(parents=True)

    (weekly / "triage_note.md").write_text("# triage\n- benchmark_voice_boundary: FAIL", encoding="utf-8")
    (monthly / "summary.json").write_text("{not-json}", encoding="utf-8")

    payload = build_integrated_summary(tmp_path)

    assert payload["monthly"]["summary"] is None
    assert payload["monthly"]["summary_error"] is not None
    assert payload["overall"]["has_malformed_artifact"] is True
    assert payload["overall"]["has_reported_failures"] is True


def test_build_integrated_summary_handles_missing_archives(tmp_path) -> None:
    payload = build_integrated_summary(tmp_path)

    assert payload["weekly"]["latest_week_id"] is None
    assert payload["monthly"]["latest_month_id"] is None
    assert payload["overall"]["has_weekly_and_monthly"] is False


def test_write_integrated_summary_writes_default_contract(tmp_path) -> None:
    payload, out_path = write_integrated_summary(tmp_path)

    assert out_path.exists()
    assert out_path.name == "p2_integrated_summary.json"
    assert payload["responsibility_boundary"]["automation_scope"]
    assert payload["generated_at_utc"].endswith("Z")
