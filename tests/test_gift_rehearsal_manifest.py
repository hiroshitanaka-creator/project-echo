from __future__ import annotations

import pytest

from po_echo.gift_rehearsal import (
    GENERATED_AT_TOKEN,
    MONTH_ID_TOKEN,
    OPERATOR_TOKEN,
    parse_manifest_headers,
    render_monthly_manifest,
    validate_manifest_summary_consistency,
)


def test_render_monthly_manifest_replaces_all_tokens() -> None:
    template = "\n".join([MONTH_ID_TOKEN, GENERATED_AT_TOKEN, OPERATOR_TOKEN])
    rendered = render_monthly_manifest(template, "2026-05", "2026-05-01T00:00:00Z", "ops-team")

    assert "- month_id: `2026-05`" in rendered
    assert "- generated_at_utc: `2026-05-01T00:00:00Z`" in rendered
    assert "- operator: `ops-team`" in rendered


def test_render_monthly_manifest_requires_tokens() -> None:
    with pytest.raises(ValueError):
        render_monthly_manifest("# empty", "2026-05", "2026-05-01T00:00:00Z", "ops-team")


def test_parse_manifest_headers_extracts_required_fields() -> None:
    manifest = "\n".join([
        "# Manifest",
        "- month_id: `2026-05`",
        "- generated_at_utc: `2026-05-01T00:00:00Z`",
        "- operator: `ops-team`",
    ])
    headers = parse_manifest_headers(manifest)

    assert headers == {
        "month_id": "2026-05",
        "generated_at_utc": "2026-05-01T00:00:00Z",
        "operator": "ops-team",
    }


def test_parse_manifest_headers_rejects_missing_field() -> None:
    with pytest.raises(ValueError):
        parse_manifest_headers("- month_id: `2026-05`")


def test_validate_manifest_summary_consistency() -> None:
    manifest = "\n".join([
        "- month_id: `2026-05`",
        "- generated_at_utc: `2026-05-01T00:00:00Z`",
        "- operator: `ops-team`",
    ])
    summary = {
        "month_id": "2026-05",
        "generated_at_utc": "2026-05-01T00:00:00Z",
        "operator": "ops-team",
    }

    assert validate_manifest_summary_consistency(manifest, summary) is True

    summary["operator"] = "another"
    assert validate_manifest_summary_consistency(manifest, summary) is False
