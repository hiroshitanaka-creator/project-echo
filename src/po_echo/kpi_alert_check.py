"""KPI alert template fill-check helpers.

Why: p2_kpi_alert.md contains placeholder tokens that operators must replace
before an alert is considered actionable. Leaving placeholders unfilled
causes silent record-keeping failures and delays triage. This module
detects unfilled tokens mechanically so the check can run in CI or as a
lightweight pre-commit hook.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

# Placeholder patterns that must NOT appear in a filled-in alert file.
# Each entry is a (token_description, regex_pattern) pair.
# Why we use regex: some placeholders have pipe-separated alternatives
# (e.g. "SEV-1|SEV-2|SEV-3") which look like a literal string in markdown
# but signal an unfilled choice.
_UNFILLED_PATTERNS: Sequence[tuple[str, str]] = [
    ("alert_id_placeholder", r"ALERT-YYYYMMDD-XXX"),
    ("week_id_placeholder", r"YYYY-Www"),
    ("detected_at_placeholder", r"<set-by-operator>"),
    ("severity_placeholder", r"SEV-1\|SEV-2\|SEV-3"),
    ("detector_placeholder", r"automation\|operator"),
    ("metric_name_placeholder", r"<voice_boundary_min_seconds \| rth_tracker_entries \| demo_c_verification_status \| \.\.\.>"),
    ("observed_value_placeholder", r"<value>"),
    ("comparison_placeholder", r"< \| > \| >= \| <= \| =="),
    ("disposition_placeholder", r"mitigated \| monitoring \| blocked"),
    ("mitigation_owner_placeholder", r"<name/team>"),
    ("next_review_placeholder", r"<timestamp>"),
    ("notes_placeholder", r"<short note \d+>"),
]

_COMPILED: list[tuple[str, re.Pattern[str]]] = [
    (desc, re.compile(pattern))
    for desc, pattern in _UNFILLED_PATTERNS
]


@dataclass(frozen=True)
class KpiAlertCheckResult:
    """Result of a single KPI alert fill-check.

    Attributes:
        is_valid: True only when no unfilled placeholders remain.
        unfilled_placeholders: list of token descriptions that still match.
        checked_path: source file that was checked (may be None for in-memory checks).
        responsibility_boundary: human-readable scope of this automation.
    """

    is_valid: bool
    unfilled_placeholders: list[str] = field(default_factory=list)
    checked_path: str | None = None
    responsibility_boundary: str = (
        "記入漏れの機械検出まで。アラート内容の妥当性判断は運用者責任。"
    )

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "unfilled_placeholders": self.unfilled_placeholders,
            "checked_path": self.checked_path,
            "responsibility_boundary": self.responsibility_boundary,
        }


def check_kpi_alert_text(text: str, path: str | None = None) -> KpiAlertCheckResult:
    """Check *text* for unfilled placeholder tokens.

    Args:
        text: Contents of a filled-in KPI alert markdown file.
        path: Optional human-readable path for reporting.

    Returns:
        KpiAlertCheckResult with is_valid=True when no placeholders remain.
    """
    found: list[str] = []
    for desc, pattern in _COMPILED:
        if pattern.search(text):
            found.append(desc)

    return KpiAlertCheckResult(
        is_valid=not found,
        unfilled_placeholders=found,
        checked_path=path,
    )


def check_kpi_alert_file(path: Path) -> KpiAlertCheckResult:
    """Load *path* and delegate to :func:`check_kpi_alert_text`."""
    text = path.read_text(encoding="utf-8")
    return check_kpi_alert_text(text, path=str(path))
