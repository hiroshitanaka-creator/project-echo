from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_weekly_audit_archive_writes_integrated_summary_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    week_id = "2026-W11"
    integrated_rel = "reports/operations/test_integrated_summary.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/weekly_audit_archive.py",
            "--root",
            str(repo_root),
            "--week-id",
            week_id,
            "--compare-to",
            "2026-W10",
            "--operator",
            "test-ops",
            "--hmac-secret",
            "test-secret",
            "--integrated-summary-out",
            integrated_rel,
            "--no-fail-on-fail",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 0
    summary = json.loads(result.stdout)
    assert summary["week_id"] == week_id
    assert summary["integrated_summary_path"] == integrated_rel

    integrated_path = repo_root / integrated_rel
    integrated_diff_path = repo_root / summary["integrated_summary_diff_path"]
    assert integrated_path.exists()
    assert integrated_diff_path.exists()

    # cleanup for git status expectations
    archive_dir = repo_root / summary["archive_dir"]
    for path in archive_dir.glob("**/*"):
        if path.is_file():
            path.unlink()
    for path in sorted(archive_dir.glob("**/*"), reverse=True):
        if path.is_dir():
            path.rmdir()
    archive_dir.rmdir()

    if integrated_path.exists():
        integrated_path.unlink()
    if integrated_diff_path.exists():
        integrated_diff_path.unlink()
    operations_dir = integrated_path.parent
    if operations_dir.exists() and not any(operations_dir.iterdir()):
        operations_dir.rmdir()
