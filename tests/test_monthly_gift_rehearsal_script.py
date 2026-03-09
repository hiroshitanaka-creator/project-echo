from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_monthly_gift_rehearsal_dry_run_generates_consistent_summary(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    month_id = "2026-07"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/monthly_gift_rehearsal.py",
            "--root",
            str(repo_root),
            "--month-id",
            month_id,
            "--operator",
            "test-ops",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )
    assert result.returncode == 0

    summary = json.loads(result.stdout)
    assert summary["month_id"] == month_id
    assert summary["status"] == "DRY_RUN"
    assert summary["dry_run"] is True
    assert summary["manifest_consistent"] is True

    archive_dir = repo_root / summary["archive_dir"]
    summary_path = archive_dir / "summary.json"
    manifest_path = archive_dir / "manifest.md"
    triage_path = archive_dir / "triage_note.md"

    assert summary_path.exists()
    assert manifest_path.exists()
    assert triage_path.exists()
    assert "- dry_run: True" in triage_path.read_text(encoding="utf-8")

    # keep repository clean for git status expectations
    for path in archive_dir.glob("**/*"):
        if path.is_file():
            path.unlink()
    for path in sorted(archive_dir.glob("**/*"), reverse=True):
        if path.is_dir():
            path.rmdir()
    archive_dir.rmdir()
