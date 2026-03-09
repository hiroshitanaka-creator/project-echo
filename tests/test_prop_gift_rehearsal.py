from __future__ import annotations

from datetime import date

from hypothesis import given
from hypothesis import strategies as st

from po_echo.gift_rehearsal import (
    GENERATED_AT_TOKEN,
    MONTH_ID_PATTERN,
    MONTH_ID_TOKEN,
    OPERATOR_TOKEN,
    ensure_monthly_gift_rehearsal,
    iso_month_id,
    render_monthly_manifest,
)


@given(st.dates(min_value=date(2000, 1, 1), max_value=date(2100, 12, 31)))
def test_iso_month_id_matches_pattern(d: date) -> None:
    month_id = iso_month_id(d)
    assert MONTH_ID_PATTERN.match(month_id)


@given(st.integers(min_value=2000, max_value=2100), st.integers(min_value=1, max_value=12))
def test_ensure_monthly_rehearsal_uses_fixed_filename_contract(tmp_path, year: int, month: int) -> None:
    month_id = f"{year:04d}-{month:02d}"
    archive = ensure_monthly_gift_rehearsal(tmp_path, month_id)

    assert archive.base_dir.exists()
    assert archive.command_log.name == "make_xai_gift_command.txt"
    assert archive.summary_json.name == "summary.json"
    assert archive.triage_note.name == "triage_note.md"
    assert archive.manifest.name == "manifest.md"


@given(
    st.from_regex(MONTH_ID_PATTERN, fullmatch=True),
    st.text(min_size=1, max_size=64).filter(lambda s: "`" not in s and "\n" not in s),
)
def test_render_monthly_manifest_binds_required_headers(month_id: str, operator: str) -> None:
    template = "\n".join(["# t", MONTH_ID_TOKEN, GENERATED_AT_TOKEN, OPERATOR_TOKEN])
    rendered = render_monthly_manifest(template, month_id, "2026-03-09T00:00:00Z", operator)

    assert f"- month_id: `{month_id}`" in rendered
    assert "- generated_at_utc: `2026-03-09T00:00:00Z`" in rendered
    assert f"- operator: `{operator}`" in rendered


@given(st.text())
def test_render_monthly_manifest_rejects_missing_tokens(template: str) -> None:
    if MONTH_ID_TOKEN in template and GENERATED_AT_TOKEN in template and OPERATOR_TOKEN in template:
        return

    try:
        render_monthly_manifest(template, "2026-03", "2026-03-09T00:00:00Z", "ops")
    except ValueError:
        pass
    else:
        assert False, "expected ValueError when template misses required tokens"
