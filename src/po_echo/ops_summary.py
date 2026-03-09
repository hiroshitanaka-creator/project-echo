"""P2 operations summary helpers.

Why: Sprint-3 prioritizes observability, so operators need one machine-readable
summary that merges latest weekly and monthly evidence status.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from po_echo.audit_archive import WEEK_ID_PATTERN
from po_echo.gift_rehearsal import MONTH_ID_PATTERN


_WEEK_SORT_PATTERN = re.compile(r"^(\d{4})-W(\d{2})$")
_MONTH_SORT_PATTERN = re.compile(r"^(\d{4})-(\d{2})$")
_DIFF_EXCLUDE_PATHS = {
    "generated_at_utc",
    "responsibility_boundary",
    "output_path",
    "diff_path",
}


@dataclass(frozen=True)
class LabeledPath:
    label: str
    path: Path


def _latest_labeled_subdir(base: Path, matcher: re.Pattern[str], parse: re.Pattern[str]) -> LabeledPath | None:
    if not base.exists():
        return None

    candidates: list[LabeledPath] = []
    for entry in base.iterdir():
        if not entry.is_dir():
            continue
        label = entry.name
        if matcher.match(label):
            candidates.append(LabeledPath(label=label, path=entry))

    if not candidates:
        return None

    # Why: explicit numeric sorting avoids lexicographic pitfalls and keeps
    # latest evidence window deterministic.
    def sort_key(item: LabeledPath) -> tuple[int, int]:
        matched = parse.match(item.label)
        if not matched:
            return (0, 0)
        return int(matched.group(1)), int(matched.group(2))

    return sorted(candidates, key=sort_key)[-1]


def _load_monthly_summary(summary_path: Path) -> dict[str, Any] | None:
    if not summary_path.exists():
        return None
    return json.loads(summary_path.read_text(encoding="utf-8"))


def _read_text_if_exists(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def build_integrated_summary(root: Path) -> dict[str, Any]:
    weekly_latest = _latest_labeled_subdir(
        root / "reports" / "audit", WEEK_ID_PATTERN, _WEEK_SORT_PATTERN
    )
    monthly_latest = _latest_labeled_subdir(
        root / "reports" / "gift_rehearsal", MONTH_ID_PATTERN, _MONTH_SORT_PATTERN
    )

    weekly_payload: dict[str, Any] = {
        "latest_week_id": weekly_latest.label if weekly_latest else None,
        "archive_dir": str(weekly_latest.path.relative_to(root)) if weekly_latest else None,
        "has_triage_note": bool(weekly_latest and (weekly_latest.path / "triage_note.md").exists()),
        "has_manifest": bool(weekly_latest and (weekly_latest.path / "manifest.md").exists()),
        "has_kpi_delta": bool(weekly_latest and (weekly_latest.path / "kpi_delta.md").exists()),
    }

    monthly_summary: dict[str, Any] | None = None
    monthly_summary_error: str | None = None
    if monthly_latest:
        try:
            monthly_summary = _load_monthly_summary(monthly_latest.path / "summary.json")
        except json.JSONDecodeError as exc:
            # Why: observability payload should still be emitted even when one
            # artifact is malformed, so operators can triage quickly.
            monthly_summary_error = f"invalid_summary_json:{exc.msg}"

    weekly_triage = _read_text_if_exists(weekly_latest.path / "triage_note.md") if weekly_latest else None
    monthly_triage = _read_text_if_exists(monthly_latest.path / "triage_note.md") if monthly_latest else None
    monthly_payload: dict[str, Any] = {
        "latest_month_id": monthly_latest.label if monthly_latest else None,
        "archive_dir": str(monthly_latest.path.relative_to(root)) if monthly_latest else None,
        "summary": monthly_summary,
        "summary_error": monthly_summary_error,
        "has_triage_note": bool(monthly_latest and (monthly_latest.path / "triage_note.md").exists()),
        "has_manifest": bool(monthly_latest and (monthly_latest.path / "manifest.md").exists()),
    }

    def triage_contains_fail(triage: str | None) -> bool:
        return bool(triage and "FAIL" in triage)

    return {
        "weekly": weekly_payload,
        "monthly": monthly_payload,
        "overall": {
            "has_weekly_and_monthly": bool(weekly_latest and monthly_latest),
            "has_malformed_artifact": bool(monthly_summary_error),
            "has_reported_failures": triage_contains_fail(weekly_triage) or triage_contains_fail(monthly_triage),
            "latest_windows": {
                "week_id": weekly_payload["latest_week_id"],
                "month_id": monthly_payload["latest_month_id"],
            },
        },
    }


def _flatten_diff_paths(value: Any, prefix: str = "") -> dict[str, Any]:
    if not isinstance(value, dict):
        return {prefix: value} if prefix else {"": value}

    flattened: dict[str, Any] = {}
    for key, nested in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(nested, dict):
            flattened.update(_flatten_diff_paths(nested, path))
        else:
            flattened[path] = nested
    return flattened


def build_integrated_summary_diff(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    """Create machine-readable diff between current and previous integrated summary.

    Why: operators need deterministic delta output to reduce review time during
    weekly/monthly handoffs.
    """

    if previous is None:
        return {
            "has_previous": False,
            "changed": True,
            "changed_field_count": 0,
            "changed_fields": [],
            "previous_latest_windows": None,
            "current_latest_windows": current.get("overall", {}).get("latest_windows"),
            "previous_read_error": None,
        }

    prev_flat = _flatten_diff_paths(previous)
    curr_flat = _flatten_diff_paths(current)
    keys = sorted(set(prev_flat) | set(curr_flat))
    changed_fields = [
        key
        for key in keys
        if key not in _DIFF_EXCLUDE_PATHS and prev_flat.get(key) != curr_flat.get(key)
    ]

    return {
        "has_previous": True,
        "changed": bool(changed_fields),
        "changed_field_count": len(changed_fields),
        "changed_fields": changed_fields,
        "previous_latest_windows": previous.get("overall", {}).get("latest_windows"),
        "current_latest_windows": current.get("overall", {}).get("latest_windows"),
        "previous_read_error": None,
    }


def write_integrated_summary(
    root: Path,
    out_path: Path | None = None,
) -> tuple[dict[str, Any], Path, Path]:
    """Build and write integrated summary JSON.

    Why: weekly/monthly automation should share one write contract so output
    fields stay consistent across operators and scripts.
    """

    if out_path is None:
        out_path = root / "reports" / "operations" / "p2_integrated_summary.json"
    elif not out_path.is_absolute():
        out_path = root / out_path

    previous: dict[str, Any] | None = None
    previous_read_error: str | None = None
    if out_path.exists():
        try:
            previous = json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            previous_read_error = f"invalid_previous_summary_json:{exc.msg}"

    payload = build_integrated_summary(root)
    payload["generated_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    payload["responsibility_boundary"] = {
        "automation_scope": "最新週次/月次証跡の集約と存在確認まで",
        "human_scope": "公開可否・リスク受容・対外説明の最終判断",
    }

    diff_path = out_path.with_name("p2_integrated_summary_diff.json")
    diff_payload = build_integrated_summary_diff(previous=previous, current=payload)
    diff_payload["generated_at_utc"] = payload["generated_at_utc"]
    diff_payload["source_summary_path"] = str(out_path.relative_to(root))
    if previous_read_error:
        diff_payload["previous_read_error"] = previous_read_error

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    diff_path.write_text(json.dumps(diff_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload, out_path, diff_path
