"""Alert notification payload builder.

Why: ops_summary.py already surfaces has_reported_failures and
has_malformed_artifact as machine-readable flags, but operators and
downstream automation need a standardized notification envelope that
states severity, evidence links, and responsibility boundary explicitly.
This module converts the integrated summary overall flags into that
envelope so tooling can route, log, or suppress alerts deterministically.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Severity mapping.
# Why two levels: FAIL and malformed artifact warrant different initial
# response urgency, but both must remain below human decision authority.
_SEV_REPORTED_FAILURES = "SEV-2"
_SEV_MALFORMED_ARTIFACT = "SEV-3"
_SEV_COMBINED = "SEV-1"
_SEV_NONE = "NONE"


def build_alert_notification(
    summary: dict[str, Any],
    summary_path: str | None = None,
    diff_path: str | None = None,
) -> dict[str, Any]:
    """Convert an integrated summary dict into a notification envelope.

    Args:
        summary: Output of ``build_integrated_summary`` / ``write_integrated_summary``.
        summary_path: Human-readable path of the source summary file (optional).
        diff_path: Human-readable path of the diff file (optional).

    Returns:
        Notification envelope dict with keys:
        - ``has_alert``: bool — True when at least one flag is raised.
        - ``severity``: one of SEV-1 / SEV-2 / SEV-3 / NONE.
        - ``flags``: machine-readable flag breakdown.
        - ``evidence``: links to supporting artifacts.
        - ``responsibility_boundary``: automation vs human scope.
        - ``generated_at_utc``: ISO-8601 timestamp.
    """

    overall = summary.get("overall", {})
    has_failures = bool(overall.get("has_reported_failures"))
    has_malformed = bool(overall.get("has_malformed_artifact"))
    has_alert = has_failures or has_malformed

    if has_failures and has_malformed:
        severity = _SEV_COMBINED
    elif has_failures:
        severity = _SEV_REPORTED_FAILURES
    elif has_malformed:
        severity = _SEV_MALFORMED_ARTIFACT
    else:
        severity = _SEV_NONE

    latest_windows = overall.get("latest_windows", {})

    evidence: dict[str, Any] = {
        "integrated_summary_path": summary_path,
        "diff_path": diff_path,
        "latest_week_id": latest_windows.get("week_id"),
        "latest_month_id": latest_windows.get("month_id"),
    }
    if latest_windows.get("week_id"):
        week_dir = f"reports/audit/{latest_windows['week_id']}"
        evidence["weekly_archive_dir"] = week_dir
        evidence["kpi_delta_ref"] = f"{week_dir}/kpi_delta.md"
        evidence["triage_note_ref"] = f"{week_dir}/triage_note.md"
    if latest_windows.get("month_id"):
        month_dir = f"reports/gift_rehearsal/{latest_windows['month_id']}"
        evidence["monthly_archive_dir"] = month_dir
        evidence["monthly_summary_ref"] = f"{month_dir}/summary.json"

    return {
        "has_alert": has_alert,
        "severity": severity,
        "flags": {
            "has_reported_failures": has_failures,
            "has_malformed_artifact": has_malformed,
        },
        "evidence": evidence,
        "responsibility_boundary": {
            "automation_scope": "異常フラグの検知・通知ペイロード生成まで。",
            "human_scope": "公開停止・リスク受容・対外説明・恒久対策承認は運用者責任。",
        },
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def write_alert_notification(
    root: Path,
    summary: dict[str, Any],
    out_path: Path | None = None,
    summary_path: str | None = None,
    diff_path: str | None = None,
) -> tuple[dict[str, Any], Path]:
    """Build and persist the notification JSON.

    Args:
        root: Repository root (used to compute default ``out_path``).
        summary: Integrated summary dict.
        out_path: Override output path (default: reports/operations/p2_alert_notification.json).
        summary_path: Human-readable source path for evidence.
        diff_path: Human-readable diff path for evidence.

    Returns:
        ``(payload, written_path)`` tuple.
    """
    import json

    if out_path is None:
        out_path = root / "reports" / "operations" / "p2_alert_notification.json"
    elif not out_path.is_absolute():
        out_path = root / out_path

    payload = build_alert_notification(summary, summary_path=summary_path, diff_path=diff_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload, out_path
