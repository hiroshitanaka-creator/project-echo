from __future__ import annotations

"""CI-facing KPI helpers for lightweight benchmark reporting.

Why: keep PR-time KPI evidence in one place so workflows can publish
consistent candidate/evidence/responsibility-boundary summaries without
embedding logic in YAML.
"""

from dataclasses import dataclass

VOICE_10K_TARGET_SECONDS = 0.30
RTH_MAX_TRACKER_ENTRIES = 2000


@dataclass(frozen=True)
class KpiCheck:
    """Result envelope for a single KPI check."""

    name: str
    passed: bool
    observed: float
    target: float
    unit: str
    evidence: str


def evaluate_voice_10k(min_seconds: float) -> KpiCheck:
    """Evaluate voice-boundary 10k runtime KPI."""
    passed = min_seconds < VOICE_10K_TARGET_SECONDS
    return KpiCheck(
        name="voice_boundary_10k_runtime",
        passed=passed,
        observed=min_seconds,
        target=VOICE_10K_TARGET_SECONDS,
        unit="seconds",
        evidence=f"min_seconds={min_seconds:.6f}",
    )


def evaluate_rth_tracker_entries(entries: int, max_entries: int = RTH_MAX_TRACKER_ENTRIES) -> KpiCheck:
    """Evaluate RTH collision-tracker boundedness KPI."""
    passed = entries <= max_entries
    return KpiCheck(
        name="rth_tracker_boundedness",
        passed=passed,
        observed=float(entries),
        target=float(max_entries),
        unit="entries",
        evidence=f"tracker_entries={entries}",
    )


def build_ci_kpi_markdown(checks: list[KpiCheck]) -> str:
    """Build markdown summary for CI step summaries or PR comments."""
    lines = [
        "## CI KPI Quick Check",
        "",
        "候補セット（自動判定）:",
    ]
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        mark = "✅" if check.passed else "❌"
        lines.append(
            f"- {mark} `{check.name}`: {status} (observed={check.observed:.6g} {check.unit}, target<={check.target:.6g} {check.unit})"
        )
        lines.append(f"  - evidence: {check.evidence}")

    lines.extend(
        [
            "",
            "責任境界:",
            "- ここでの自動判定はKPI逸脱の一次検知まで。",
            "- マージ可否・運用エスカレーション判断は人間レビュー責任。",
        ]
    )
    return "\n".join(lines)
