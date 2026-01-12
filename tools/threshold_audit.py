#!/usr/bin/env python3
"""
Threshold Audit Tool

Analyzes all runs/*.json to check if responsibility boundary thresholds
are working as intended. Outputs distribution of:
- adjusted_score
- uncertainty
- reversibility
- max_tension
- execution_allowed
- requires_human_confirm

This helps identify if thresholds are:
- Too conservative (blocking too much)
- Too permissive (allowing too much)
- Just right (3-tier: dangerous→stop, medium→confirm, safe→allow)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RUNS_DIR = Path("runs")


def load_json(path: Path) -> dict[str, Any]:
    """Load JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def extract_signals(result: dict[str, Any]) -> dict[str, Any]:
    """Extract key signals from evaluation result."""
    rb = result.get("responsibility_boundary", {})
    signals = rb.get("signals", {})

    return {
        "adjusted_score": signals.get("adjusted_score", 0.0),
        "uncertainty": signals.get("uncertainty", 0.5),
        "reversibility": signals.get("reversibility", 0.5),
        "max_tension": signals.get("max_tension", 0.0),
        "blocked_count": signals.get("blocked_count", 0),
        "execution_allowed": rb.get("execution_allowed", False),
        "requires_human_confirm": rb.get("requires_human_confirm", True),
        "reasons": rb.get("reasons", []),
        "scenario_name": result.get("scenario", {}).get("meta", {}).get("name", "unknown"),
    }


def analyze_distributions(runs: list[dict[str, Any]]) -> None:
    """Analyze threshold distributions and print summary."""
    if not runs:
        print("No runs found.")
        return

    # Count outcomes
    exec_allowed = sum(1 for r in runs if r["execution_allowed"])
    exec_blocked = len(runs) - exec_allowed
    confirm_required = sum(1 for r in runs if r["requires_human_confirm"])

    print("=" * 80)
    print("THRESHOLD AUDIT REPORT")
    print("=" * 80)
    print()
    print(f"Total runs analyzed: {len(runs)}")
    print(f"Execution allowed: {exec_allowed} ({exec_allowed / len(runs) * 100:.1f}%)")
    print(f"Execution blocked: {exec_blocked} ({exec_blocked / len(runs) * 100:.1f}%)")
    print(f"Human confirm required: {confirm_required} ({confirm_required / len(runs) * 100:.1f}%)")
    print()

    # Distributions
    print("SIGNAL DISTRIBUTIONS")
    print("-" * 80)

    # Adjusted score
    scores = [r["adjusted_score"] for r in runs]
    print(
        f"Adjusted score: min={min(scores):.2f}, max={max(scores):.2f}, avg={sum(scores) / len(scores):.2f}"
    )

    # Uncertainty
    uncertainties = [r["uncertainty"] for r in runs]
    print(
        f"Uncertainty:    min={min(uncertainties):.2f}, max={max(uncertainties):.2f}, avg={sum(uncertainties) / len(uncertainties):.2f}"
    )

    # Reversibility
    reversibilities = [r["reversibility"] for r in runs]
    print(
        f"Reversibility:  min={min(reversibilities):.2f}, max={max(reversibilities):.2f}, avg={sum(reversibilities) / len(reversibilities):.2f}"
    )

    # Max tension
    tensions = [r["max_tension"] for r in runs]
    print(
        f"Max tension:    min={min(tensions):.3f}, max={max(tensions):.3f}, avg={sum(tensions) / len(tensions):.3f}"
    )
    print()

    # Breakdown by execution outcome
    print("BREAKDOWN BY EXECUTION OUTCOME")
    print("-" * 80)

    allowed_runs = [r for r in runs if r["execution_allowed"]]
    blocked_runs = [r for r in runs if not r["execution_allowed"]]

    if allowed_runs:
        allowed_scores = [r["adjusted_score"] for r in allowed_runs]
        print(
            f"Allowed runs ({len(allowed_runs)}): avg_score={sum(allowed_scores) / len(allowed_scores):.2f}"
        )

    if blocked_runs:
        blocked_scores = [r["adjusted_score"] for r in blocked_runs]
        print(
            f"Blocked runs ({len(blocked_runs)}): avg_score={sum(blocked_scores) / len(blocked_scores):.2f}"
        )
    print()

    # Reason frequency
    print("BLOCKING REASON FREQUENCY")
    print("-" * 80)
    reason_counts: dict[str, int] = {}
    for r in runs:
        for reason in r["reasons"]:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    for reason, count in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {reason:40s} {count:3d} ({count / len(runs) * 100:.1f}%)")
    print()

    # Sample cases
    print("SAMPLE CASES")
    print("-" * 80)

    # Most permissive (highest score among blocked)
    if blocked_runs:
        most_permissive = max(blocked_runs, key=lambda x: x["adjusted_score"])
        print(f"Most permissive blocked: {most_permissive['scenario_name']}")
        print(
            f"  Score: {most_permissive['adjusted_score']:.2f}, Reasons: {', '.join(most_permissive['reasons'])}"
        )

    # Most conservative (lowest score among allowed)
    if allowed_runs:
        most_conservative = min(allowed_runs, key=lambda x: x["adjusted_score"])
        print(f"Most conservative allowed: {most_conservative['scenario_name']}")
        print(f"  Score: {most_conservative['adjusted_score']:.2f}")
    print()

    print("=" * 80)
    print("THRESHOLD ASSESSMENT")
    print("=" * 80)

    # Check for issues
    issues = []

    # All blocked? Too conservative
    if exec_blocked == len(runs):
        issues.append("⚠️  ALL runs blocked - thresholds may be TOO CONSERVATIVE")

    # All allowed? Too permissive
    if exec_allowed == len(runs):
        issues.append("⚠️  ALL runs allowed - thresholds may be TOO PERMISSIVE")

    # Narrow score range among blocked
    if blocked_runs and len(blocked_runs) > 1:
        blocked_scores = [r["adjusted_score"] for r in blocked_runs]
        if max(blocked_scores) - min(blocked_scores) < 0.1:
            issues.append("ℹ️  Blocked runs have narrow score range - may need more granularity")

    if issues:
        for issue in issues:
            print(issue)
    else:
        print("✅ Threshold distribution looks reasonable")

    print()
    print("Recommendation:")
    print("- Target: ~60-80% blocked (dangerous), ~10-30% confirm (medium), ~5-10% allowed (safe)")
    print("- Adjust thresholds in _responsibility_boundary() if needed")
    print("=" * 80)


def main() -> None:
    """Main entry point."""
    if not RUNS_DIR.exists():
        print(f"Error: {RUNS_DIR} directory not found")
        return

    json_files = list(RUNS_DIR.glob("*.json"))

    if not json_files:
        print(f"No JSON files found in {RUNS_DIR}")
        return

    print(f"Loading {len(json_files)} run files from {RUNS_DIR}...")

    runs = []
    for path in json_files:
        try:
            result = load_json(path)
            signals = extract_signals(result)
            runs.append(signals)
        except Exception as e:
            print(f"Warning: Failed to process {path}: {e}")

    analyze_distributions(runs)


if __name__ == "__main__":
    main()
