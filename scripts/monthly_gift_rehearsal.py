#!/usr/bin/env python3
"""Run monthly xAI Gift package rehearsal and archive evidence.

Why: regular rehearsal keeps external handoff reproducible in P2 operations.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from po_echo.audit_archive import utc_now_iso
from po_echo.gift_rehearsal import (
    ensure_monthly_gift_rehearsal,
    iso_month_id,
    rebuild_gift_rehearsal_history_index,
    render_monthly_manifest,
    validate_manifest_summary_consistency,
)


def _initialize_manifest(template_path: Path, out_path: Path, month_id: str, generated_at_utc: str, operator: str) -> None:
    template = template_path.read_text(encoding="utf-8")
    out_path.write_text(render_monthly_manifest(template, month_id, generated_at_utc, operator), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create monthly xAI Gift rehearsal archive")
    parser.add_argument("--month-id", help="Override month id (YYYY-MM)")
    parser.add_argument("--root", default=".", help="Repository root path")
    parser.add_argument("--operator", default="automation", help="Operator/team name")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate archive and manifest generation only; skip make_xai_gift execution.",
    )
    parser.add_argument(
        "--no-fail-on-fail",
        action="store_true",
        help="Do not return non-zero even when rehearsal command fails.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    month_id = args.month_id or iso_month_id()
    rehearsal = ensure_monthly_gift_rehearsal(root, month_id)

    generated_at = utc_now_iso()
    manifest_tpl = root / "docs" / "templates" / "p2_gift_rehearsal_manifest.md"
    _initialize_manifest(manifest_tpl, rehearsal.manifest, month_id, generated_at, args.operator)

    env = os.environ.copy()
    cmd = [sys.executable, "scripts/make_xai_gift.py", "--out", str(rehearsal.base_dir / "xai_gift")]

    if args.dry_run:
        result_code = 0
        result_stdout = "DRY_RUN: make_xai_gift execution skipped by flag."
        result_stderr = ""
        status = "DRY_RUN"
    else:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        result_code = result.returncode
        result_stdout = result.stdout
        result_stderr = result.stderr
        status = "PASS" if result.returncode == 0 else "FAIL"

    rehearsal.command_log.write_text(
        f"$ {' '.join(cmd)}\n\n# stdout\n{result_stdout}\n\n# stderr\n{result_stderr}\n",
        encoding="utf-8",
    )

    summary = {
        "month_id": month_id,
        "generated_at_utc": generated_at,
        "operator": args.operator,
        "command": cmd,
        "return_code": result_code,
        "status": status,
        "archive_dir": str(rehearsal.base_dir.relative_to(root)),
        "dry_run": bool(args.dry_run),
    }
    manifest_text = rehearsal.manifest.read_text(encoding="utf-8")
    summary["manifest_consistent"] = validate_manifest_summary_consistency(manifest_text, summary)
    history = rebuild_gift_rehearsal_history_index(root)
    summary["history_index_latest_month_id"] = history.get("latest_month_id")
    summary["history_index_records"] = len(history.get("records", []))
    rehearsal.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    triage = [
        "# Monthly Gift Rehearsal Triage Note",
        f"- month_id: {month_id}",
        f"- generated_at_utc: {summary['generated_at_utc']}",
        f"- operator: {args.operator}",
        f"- dry_run: {summary['dry_run']}",
        f"- status: {summary['status']} (rc={result_code})",
        "",
        "## Responsibility Boundary",
        "- この記録は配布パッケージ再生成の実行証跡を保持する責務を持つ。",
        "- 外部共有可否とリスク受容の最終判断は人間オーナー/組織責務とする。",
    ]
    rehearsal.triage_note.write_text("\n".join(triage) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if status == "FAIL" and not args.no_fail_on_fail:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
