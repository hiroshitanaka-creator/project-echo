from __future__ import annotations

from po_echo.ci_kpi import (
    build_ci_kpi_markdown,
    evaluate_rth_tracker_entries,
    evaluate_voice_10k,
)


def test_evaluate_voice_10k_threshold() -> None:
    assert evaluate_voice_10k(0.29).passed is True
    assert evaluate_voice_10k(0.30).passed is False


def test_evaluate_rth_tracker_entries_threshold() -> None:
    assert evaluate_rth_tracker_entries(2000).passed is True
    assert evaluate_rth_tracker_entries(2001).passed is False


def test_build_ci_kpi_markdown_contains_boundary() -> None:
    checks = [evaluate_voice_10k(0.20), evaluate_rth_tracker_entries(1500)]
    markdown = build_ci_kpi_markdown(checks)
    assert "候補セット" in markdown
    assert "evidence:" in markdown
    assert "責任境界" in markdown
