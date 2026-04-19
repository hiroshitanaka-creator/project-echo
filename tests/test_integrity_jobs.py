"""Tests for periodic integrity job helpers."""

from __future__ import annotations

import json
import hashlib

from po_echo.integrity_jobs import verify_public_audit_manifest_file


def test_verify_public_audit_manifest_file_detects_tampering(tmp_path) -> None:
    core_payload = {
        "schema_version": "public_audit_v1",
        "project": "Project Echo",
        "kpi_status": {
            "has_reported_failures": False,
            "has_malformed_artifact": False,
            "has_weekly_and_monthly": True,
        },
        "audit_coverage": {"latest_week_id": "2026-W01", "latest_month_id": "2026-01"},
        "invariant_compliance": {
            "principle": "候補セット＋証拠＋責任境界",
            "candidates_provided": True,
            "evidence_provided": True,
            "responsibility_boundary_provided": True,
        },
    }
    canonical = json.dumps(core_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    checksum = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    manifest = {
        **core_payload,
        "generated_at_utc": "2026-01-01T00:00:00Z",
        "responsibility_boundary": {"automation_scope": "job", "human_scope": "review"},
        "integrity": {"sha256": checksum},
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    ok, _ = verify_public_audit_manifest_file(path)
    assert ok is True

    tampered = dict(manifest)
    tampered["project"] = "tampered-project"
    path.write_text(json.dumps(tampered), encoding="utf-8")

    ok2, _ = verify_public_audit_manifest_file(path)
    assert ok2 is False
