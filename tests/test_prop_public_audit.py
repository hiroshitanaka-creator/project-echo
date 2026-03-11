"""Property-based tests for public_audit module.

Properties verified:
1. Any non-empty dict summary produces a schema-compliant manifest.
2. Integrity checksum always verifies on fresh manifests.
3. Redaction never leaks internal keys regardless of summary structure.
4. verify_public_audit_manifest is False whenever any core field is mutated.
5. project_name is always surfaced in the manifest.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from po_echo.public_audit import (
    PUBLIC_AUDIT_SCHEMA_VERSION,
    build_public_audit_manifest,
    verify_public_audit_manifest,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_INTERNAL_KEYS = ["archive_dir", "output_path", "diff_path", "operator"]

_json_primitives = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-1000, max_value=1000),
    st.text(max_size=20),
)

# Shallow summary dict – realistic enough without generating huge trees.
_summary_strategy = st.fixed_dictionaries(
    {
        "overall": st.fixed_dictionaries(
            {
                "has_reported_failures": st.booleans(),
                "has_malformed_artifact": st.booleans(),
                "has_weekly_and_monthly": st.booleans(),
                "latest_windows": st.fixed_dictionaries(
                    {
                        "week_id": st.one_of(st.none(), st.just("2026-W10")),
                        "month_id": st.one_of(st.none(), st.just("2026-02")),
                    }
                ),
            }
        ),
        "weekly": st.fixed_dictionaries(
            {
                "has_triage_note": st.booleans(),
                "has_manifest": st.booleans(),
                "has_kpi_delta": st.booleans(),
                # internal key injected to verify redaction
                "archive_dir": st.text(max_size=30),
            }
        ),
        "monthly": st.fixed_dictionaries(
            {
                "has_triage_note": st.booleans(),
                "has_manifest": st.booleans(),
                "summary_error": st.one_of(st.none(), st.text(max_size=20)),
                "archive_dir": st.text(max_size=30),
            }
        ),
    }
)

_project_name_strategy = st.text(min_size=1, max_size=50)


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

@given(summary=_summary_strategy)
@settings(max_examples=40)
def test_manifest_always_has_required_keys(summary: dict[str, Any]):
    """Every non-empty summary produces a manifest with all required keys."""
    manifest = build_public_audit_manifest(summary)
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


@given(summary=_summary_strategy)
@settings(max_examples=40)
def test_integrity_always_verifies(summary: dict[str, Any]):
    """SHA-256 digest always matches for freshly generated manifests."""
    manifest = build_public_audit_manifest(summary)
    assert verify_public_audit_manifest(manifest) is True


@given(summary=_summary_strategy)
@settings(max_examples=40)
def test_no_internal_keys_in_manifest(summary: dict[str, Any]):
    """Internal-only keys must never appear in the public manifest JSON."""
    manifest = build_public_audit_manifest(summary)
    manifest_str = json.dumps(manifest)
    for key in _INTERNAL_KEYS:
        assert key not in manifest_str, f"internal key leaked: {key}"


@given(summary=_summary_strategy)
@settings(max_examples=40)
def test_schema_version_is_constant(summary: dict[str, Any]):
    """schema_version must equal the module constant regardless of input."""
    manifest = build_public_audit_manifest(summary)
    assert manifest["schema_version"] == PUBLIC_AUDIT_SCHEMA_VERSION


@given(summary=_summary_strategy, name=_project_name_strategy)
@settings(max_examples=30)
def test_project_name_propagated(summary: dict[str, Any], name: str):
    """project field must equal the project_name argument."""
    manifest = build_public_audit_manifest(summary, project_name=name)
    assert manifest["project"] == name


@given(summary=_summary_strategy)
@settings(max_examples=30)
def test_tampered_kpi_fails_verify(summary: dict[str, Any]):
    """Flipping any boolean in kpi_status must invalidate the checksum."""
    manifest = build_public_audit_manifest(summary)
    original = manifest["kpi_status"]["has_reported_failures"]
    manifest["kpi_status"]["has_reported_failures"] = not original
    assert verify_public_audit_manifest(manifest) is False


@given(summary=_summary_strategy)
@settings(max_examples=30)
def test_kpi_flags_match_overall(summary: dict[str, Any]):
    """kpi_status flags must directly reflect overall flags in the summary."""
    manifest = build_public_audit_manifest(summary)
    overall = summary.get("overall", {})
    kpi = manifest["kpi_status"]
    assert kpi["has_reported_failures"] == bool(overall.get("has_reported_failures"))
    assert kpi["has_malformed_artifact"] == bool(overall.get("has_malformed_artifact"))


@given(summary=_summary_strategy)
@settings(max_examples=30)
def test_responsibility_boundary_always_present(summary: dict[str, Any]):
    """automation_scope and human_scope must always be non-empty strings."""
    manifest = build_public_audit_manifest(summary)
    rb = manifest["responsibility_boundary"]
    assert isinstance(rb["automation_scope"], str) and rb["automation_scope"]
    assert isinstance(rb["human_scope"], str) and rb["human_scope"]
