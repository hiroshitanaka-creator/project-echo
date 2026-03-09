"""Utilities for monthly xAI Gift Package rehearsal operations.

Why: P2 Sprint-2 requires routine rehearsal logs so external sharing remains
reproducible without relying on individual memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
import re

MONTH_ID_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

MONTH_ID_TOKEN = "- month_id: `YYYY-MM`"
GENERATED_AT_TOKEN = "- generated_at_utc: `<set-by-script>`"
OPERATOR_TOKEN = "- operator: `<team-or-person>`"


@dataclass(frozen=True)
class MonthlyGiftRehearsalPaths:
    month_id: str
    base_dir: Path
    command_log: Path
    summary_json: Path
    triage_note: Path
    manifest: Path


def iso_month_id(value: date | datetime | None = None) -> str:
    """Return month id as YYYY-MM for monthly rehearsal directories."""

    if value is None:
        value = datetime.now(timezone.utc)
    if isinstance(value, datetime):
        value = value.date()
    return f"{value.year:04d}-{value.month:02d}"


def ensure_monthly_gift_rehearsal(root_dir: Path, month_id: str) -> MonthlyGiftRehearsalPaths:
    """Create monthly rehearsal directory and return canonical file paths."""

    if not MONTH_ID_PATTERN.match(month_id):
        raise ValueError(f"Invalid month_id format: {month_id}")

    base_dir = root_dir / "reports" / "gift_rehearsal" / month_id
    base_dir.mkdir(parents=True, exist_ok=True)
    return MonthlyGiftRehearsalPaths(
        month_id=month_id,
        base_dir=base_dir,
        command_log=base_dir / "make_xai_gift_command.txt",
        summary_json=base_dir / "summary.json",
        triage_note=base_dir / "triage_note.md",
        manifest=base_dir / "manifest.md",
    )


def render_monthly_manifest(template: str, month_id: str, generated_at_utc: str, operator: str) -> str:
    """Render monthly manifest text from canonical template tokens.

    Why: forcing token presence avoids silently writing malformed manifests when
    templates drift.
    """

    required_tokens = (MONTH_ID_TOKEN, GENERATED_AT_TOKEN, OPERATOR_TOKEN)
    if any(token not in template for token in required_tokens):
        raise ValueError("Manifest template is missing one or more required tokens")

    rendered = template.replace(MONTH_ID_TOKEN, f"- month_id: `{month_id}`")
    rendered = rendered.replace(GENERATED_AT_TOKEN, f"- generated_at_utc: `{generated_at_utc}`")
    rendered = rendered.replace(OPERATOR_TOKEN, f"- operator: `{operator}`")
    return rendered


def parse_manifest_headers(manifest_text: str) -> dict[str, str]:
    """Parse canonical manifest header values from markdown text."""

    patterns = {
        "month_id": re.compile(r"^- month_id: `([^`]+)`$", re.MULTILINE),
        "generated_at_utc": re.compile(r"^- generated_at_utc: `([^`]+)`$", re.MULTILINE),
        "operator": re.compile(r"^- operator: `([^`]+)`$", re.MULTILINE),
    }
    headers: dict[str, str] = {}
    for key, pattern in patterns.items():
        match = pattern.search(manifest_text)
        if not match:
            raise ValueError(f"Manifest header missing required field: {key}")
        headers[key] = match.group(1)
    return headers


def validate_manifest_summary_consistency(manifest_text: str, summary: dict[str, object]) -> bool:
    """Return True when manifest headers match summary values."""

    headers = parse_manifest_headers(manifest_text)
    return (
        headers["month_id"] == str(summary.get("month_id", ""))
        and headers["generated_at_utc"] == str(summary.get("generated_at_utc", ""))
        and headers["operator"] == str(summary.get("operator", ""))
    )
