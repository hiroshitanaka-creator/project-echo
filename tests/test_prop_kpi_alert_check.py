"""Property-based tests for kpi_alert_check.

Why: the fill-check is a safety-critical guardrail — false negatives (valid
returning True when placeholders exist) would silently corrupt audit records.
Property tests cover arbitrary text compositions beyond fixed examples.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from po_echo.kpi_alert_check import (
    _COMPILED,
    check_kpi_alert_text,
)

# All known placeholder token descriptions in the compiled pattern list.
_ALL_DESCS = [desc for desc, _ in _COMPILED]


@given(st.text())
def test_arbitrary_text_without_placeholders_is_valid_or_invalid_consistently(text: str) -> None:
    """Why: check_kpi_alert_text must not raise for any arbitrary input."""
    result = check_kpi_alert_text(text)
    # Consistency: is_valid must reflect unfilled_placeholders.
    assert result.is_valid == (len(result.unfilled_placeholders) == 0)


@given(st.text())
def test_unfilled_placeholders_is_always_subset_of_known_descs(text: str) -> None:
    """Why: reported token descriptions must come from the compiled pattern list only."""
    result = check_kpi_alert_text(text)
    for desc in result.unfilled_placeholders:
        assert desc in _ALL_DESCS, f"unknown placeholder description: {desc!r}"


@given(st.text())
def test_no_duplicate_unfilled_placeholders(text: str) -> None:
    """Why: duplicate reports would inflate severity counts."""
    result = check_kpi_alert_text(text)
    assert len(result.unfilled_placeholders) == len(set(result.unfilled_placeholders))


@settings(max_examples=200)
@given(
    st.text(min_size=0, max_size=500).filter(
        lambda t: not any(pat.search(t) for _, pat in _COMPILED)
    )
)
def test_text_without_any_known_token_is_valid(clean_text: str) -> None:
    """Why: text with no placeholder tokens must always be marked valid."""
    result = check_kpi_alert_text(clean_text)
    assert result.is_valid is True
    assert result.unfilled_placeholders == []


@given(st.text(min_size=0, max_size=200), st.text(min_size=0, max_size=200))
def test_concatenation_validity_is_monotone(prefix: str, suffix: str) -> None:
    """Why: adding more text cannot convert an invalid result into a valid one
    (validity can only decrease or stay equal as content is added, not increase).
    Checks that prefix+suffix is at least as invalid as either part alone.
    """
    combined = prefix + suffix
    result_prefix = check_kpi_alert_text(prefix)
    result_suffix = check_kpi_alert_text(suffix)
    result_combined = check_kpi_alert_text(combined)

    # Every placeholder found in prefix or suffix must also appear in combined.
    all_found = set(result_prefix.unfilled_placeholders) | set(result_suffix.unfilled_placeholders)
    for desc in all_found:
        assert desc in result_combined.unfilled_placeholders


@given(st.from_regex(r"[A-Za-z0-9 \-_]{1,100}", fullmatch=True))
def test_plain_ascii_text_is_valid(text: str) -> None:
    """Why: normal operational text (log lines, prose) must never trigger placeholders."""
    result = check_kpi_alert_text(text)
    assert result.is_valid is True
