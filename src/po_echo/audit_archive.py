"""Utilities for P2 weekly audit archive operations.

Why: P2 Sprint-2 requires consistent weekly evidence storage so audits remain
verifiable over time, independent of individual operator habits.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
import re

WEEK_ID_PATTERN = re.compile(r"^\d{4}-W(0[1-9]|[1-4][0-9]|5[0-3])$")


@dataclass(frozen=True)
class WeeklyArchivePaths:
    week_id: str
    base_dir: Path
    benchmark_voice_boundary_log: Path
    benchmark_rth_log: Path
    demo_c_receipt: Path
    registry_snapshot: Path
    triage_note: Path
    manifest: Path
    kpi_delta: Path


@dataclass(frozen=True)
class CommandOutcome:
    name: str
    return_code: int
    status: str


def iso_week_id(value: date | datetime | None = None) -> str:
    """Return ISO week id as YYYY-Www.

    Why: consistent naming keeps evidence discoverable and comparable across
    audit windows.
    """

    if value is None:
        value = datetime.now(timezone.utc)
    if isinstance(value, datetime):
        value = value.date()
    iso_year, iso_week, _ = value.isocalendar()
    return f"{iso_year:04d}-W{iso_week:02d}"


def ensure_weekly_archive(root_dir: Path, week_id: str) -> WeeklyArchivePaths:
    """Create weekly archive directory and return canonical paths."""

    if not WEEK_ID_PATTERN.match(week_id):
        raise ValueError(f"Invalid week_id format: {week_id}")

    base_dir = root_dir / "reports" / "audit" / week_id
    base_dir.mkdir(parents=True, exist_ok=True)

    return WeeklyArchivePaths(
        week_id=week_id,
        base_dir=base_dir,
        benchmark_voice_boundary_log=base_dir / "benchmark_voice_boundary.txt",
        benchmark_rth_log=base_dir / "benchmark_rth.txt",
        demo_c_receipt=base_dir / "demo_c_receipt.json",
        registry_snapshot=base_dir / "registry_snapshot.json",
        triage_note=base_dir / "triage_note.md",
        manifest=base_dir / "manifest.md",
        kpi_delta=base_dir / "kpi_delta.md",
    )


def classify_pytest_outcome(return_code: int, stdout: str, stderr: str) -> str:
    """Classify command outcome for triage notes.

    Why: benchmark jobs may be intentionally skipped in lightweight environments
    (missing optional deps), and should be visible as SKIPPED instead of FAIL.
    """

    if return_code == 0:
        return "PASS"

    merged = f"{stdout}\n{stderr}".lower()
    if return_code == 5 and ("skipped" in merged or "no tests ran" in merged):
        return "SKIPPED"

    return "FAIL"


def has_failures(outcomes: list[CommandOutcome]) -> bool:
    """Return True when any command is classified as FAIL."""

    return any(outcome.status == "FAIL" for outcome in outcomes)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
