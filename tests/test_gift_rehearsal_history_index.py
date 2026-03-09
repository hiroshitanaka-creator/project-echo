from __future__ import annotations

import json

from po_echo.gift_rehearsal import rebuild_gift_rehearsal_history_index


def test_rebuild_history_index_collects_month_records(tmp_path) -> None:
    m1 = tmp_path / "reports" / "gift_rehearsal" / "2026-01"
    m2 = tmp_path / "reports" / "gift_rehearsal" / "2026-03"
    m1.mkdir(parents=True)
    m2.mkdir(parents=True)

    (m1 / "summary.json").write_text(json.dumps({"status": "PASS", "dry_run": False}), encoding="utf-8")
    (m1 / "manifest.md").write_text("# manifest", encoding="utf-8")
    (m1 / "triage_note.md").write_text("# triage", encoding="utf-8")

    (m2 / "summary.json").write_text(json.dumps({"status": "DRY_RUN", "dry_run": True}), encoding="utf-8")
    (m2 / "manifest.md").write_text("# manifest", encoding="utf-8")
    (m2 / "triage_note.md").write_text("# triage", encoding="utf-8")

    payload = rebuild_gift_rehearsal_history_index(tmp_path)

    assert payload["latest_month_id"] == "2026-03"
    assert len(payload["records"]) == 2
    assert payload["records"][1]["status"] == "DRY_RUN"

    index_path = tmp_path / "reports" / "gift_rehearsal" / "history_index.json"
    assert index_path.exists()


def test_rebuild_history_index_marks_invalid_summary_json(tmp_path) -> None:
    month = tmp_path / "reports" / "gift_rehearsal" / "2026-02"
    month.mkdir(parents=True)
    (month / "summary.json").write_text("{bad}", encoding="utf-8")

    payload = rebuild_gift_rehearsal_history_index(tmp_path)

    assert payload["latest_month_id"] == "2026-02"
    assert payload["records"][0]["summary_error"] is not None
