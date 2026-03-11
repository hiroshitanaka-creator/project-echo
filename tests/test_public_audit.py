"""Unit tests for public_audit module.

Tests cover:
- manifest structure (required keys)
- redaction of internal-only fields
- integrity checksum correctness
- verify_public_audit_manifest round-trip
- edge cases: empty summary values, tampered manifest
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from po_echo.public_audit import (
    PUBLIC_AUDIT_SCHEMA_VERSION,
    build_public_audit_manifest,
    verify_public_audit_manifest,
    write_public_audit_manifest,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_summary(
    *,
    has_failures: bool = False,
    has_malformed: bool = False,
    week_id: str | None = "2026-W10",
    month_id: str | None = "2026-02",
) -> dict:
    return {
        "weekly": {
            "latest_week_id": week_id,
            "archive_dir": "reports/audit/2026-W10",
            "has_triage_note": True,
            "has_manifest": True,
            "has_kpi_delta": True,
        },
        "monthly": {
            "latest_month_id": month_id,
            "archive_dir": "reports/gift_rehearsal/2026-02",
            "summary": {"status": "OK"},
            "summary_error": None,
            "has_triage_note": True,
            "has_manifest": True,
        },
        "overall": {
            "has_weekly_and_monthly": bool(week_id and month_id),
            "has_malformed_artifact": has_malformed,
            "has_reported_failures": has_failures,
            "latest_windows": {"week_id": week_id, "month_id": month_id},
        },
        "generated_at_utc": "2026-03-11T00:00:00Z",
        "responsibility_boundary": {
            "automation_scope": "集約まで",
            "human_scope": "公開可否は人間責任",
        },
    }


# ---------------------------------------------------------------------------
# Structure tests
# ---------------------------------------------------------------------------

def test_manifest_required_keys():
    manifest = build_public_audit_manifest(_make_summary())
    for key in (
        "schema_version",
        "project",
        "kpi_status",
        "audit_coverage",
        "invariant_compliance",
        "generated_at_utc",
        "responsibility_boundary",
        "integrity",
    ):
        assert key in manifest, f"missing key: {key}"


def test_schema_version_matches_constant():
    manifest = build_public_audit_manifest(_make_summary())
    assert manifest["schema_version"] == PUBLIC_AUDIT_SCHEMA_VERSION


def test_kpi_status_fields():
    manifest = build_public_audit_manifest(_make_summary(has_failures=True))
    kpi = manifest["kpi_status"]
    assert kpi["has_reported_failures"] is True
    assert kpi["has_malformed_artifact"] is False
    assert isinstance(kpi["has_weekly_and_monthly"], bool)


def test_audit_coverage_fields():
    manifest = build_public_audit_manifest(_make_summary(week_id="2026-W10", month_id="2026-02"))
    cov = manifest["audit_coverage"]
    assert cov["latest_week_id"] == "2026-W10"
    assert cov["latest_month_id"] == "2026-02"
    assert isinstance(cov["weekly_has_triage_note"], bool)


def test_invariant_compliance_fields():
    manifest = build_public_audit_manifest(_make_summary())
    ic = manifest["invariant_compliance"]
    assert ic["candidates_provided"] is True
    assert ic["evidence_provided"] is True
    assert ic["responsibility_boundary_provided"] is True
    assert "候補セット" in ic["principle"]


def test_responsibility_boundary_in_manifest():
    manifest = build_public_audit_manifest(_make_summary())
    rb = manifest["responsibility_boundary"]
    assert "automation_scope" in rb
    assert "human_scope" in rb


# ---------------------------------------------------------------------------
# Redaction tests
# ---------------------------------------------------------------------------

def test_internal_paths_are_redacted():
    manifest = build_public_audit_manifest(_make_summary())
    manifest_str = json.dumps(manifest)
    for internal_key in ("archive_dir", "output_path", "diff_path", "operator"):
        assert internal_key not in manifest_str, f"found internal key in manifest: {internal_key}"


def test_kpi_flags_preserved_after_redaction():
    manifest = build_public_audit_manifest(_make_summary(has_failures=True, has_malformed=True))
    assert manifest["kpi_status"]["has_reported_failures"] is True
    assert manifest["kpi_status"]["has_malformed_artifact"] is True


# ---------------------------------------------------------------------------
# Integrity tests
# ---------------------------------------------------------------------------

def test_integrity_field_present():
    manifest = build_public_audit_manifest(_make_summary())
    assert "sha256" in manifest["integrity"]
    assert len(manifest["integrity"]["sha256"]) == 64  # hex SHA-256


def test_verify_manifest_roundtrip():
    manifest = build_public_audit_manifest(_make_summary())
    assert verify_public_audit_manifest(manifest) is True


def test_verify_fails_on_tampered_kpi():
    manifest = build_public_audit_manifest(_make_summary())
    manifest["kpi_status"]["has_reported_failures"] = not manifest["kpi_status"]["has_reported_failures"]
    assert verify_public_audit_manifest(manifest) is False


def test_verify_fails_on_missing_integrity():
    manifest = build_public_audit_manifest(_make_summary())
    del manifest["integrity"]
    assert verify_public_audit_manifest(manifest) is False


def test_verify_fails_on_wrong_sha256():
    manifest = build_public_audit_manifest(_make_summary())
    manifest["integrity"]["sha256"] = "a" * 64
    assert verify_public_audit_manifest(manifest) is False


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_windows():
    summary = _make_summary(week_id=None, month_id=None)
    manifest = build_public_audit_manifest(summary)
    cov = manifest["audit_coverage"]
    assert cov["latest_week_id"] is None
    assert cov["latest_month_id"] is None
    assert verify_public_audit_manifest(manifest) is True


def test_raises_on_empty_summary():
    with pytest.raises(ValueError):
        build_public_audit_manifest({})


def test_raises_on_non_dict_summary():
    with pytest.raises(ValueError):
        build_public_audit_manifest("not a dict")  # type: ignore[arg-type]


def test_project_name_propagated():
    manifest = build_public_audit_manifest(_make_summary(), project_name="Echo Test")
    assert manifest["project"] == "Echo Test"


# ---------------------------------------------------------------------------
# Write tests
# ---------------------------------------------------------------------------

def test_write_creates_file(tmp_path: Path):
    summary = _make_summary()
    out_path = tmp_path / "public_audit_manifest.json"
    manifest, written = write_public_audit_manifest(
        tmp_path, summary, out_path=out_path
    )
    assert written == out_path
    assert out_path.exists()
    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == PUBLIC_AUDIT_SCHEMA_VERSION


def test_write_default_path(tmp_path: Path):
    summary = _make_summary()
    _, written = write_public_audit_manifest(tmp_path, summary)
    expected = tmp_path / "reports" / "operations" / "public_audit_manifest.json"
    assert written == expected
    assert written.exists()


def test_written_manifest_passes_verify(tmp_path: Path):
    summary = _make_summary()
    out_path = tmp_path / "audit.json"
    manifest, _ = write_public_audit_manifest(tmp_path, summary, out_path=out_path)
    assert verify_public_audit_manifest(manifest) is True
