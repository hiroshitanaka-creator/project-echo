#!/usr/bin/env python3
"""Generate weekly P2 audit archive artifacts.

Why: automate evidence collection to reduce manual omission risk in P2 operations.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from po_echo.audit_archive import (
    CommandOutcome,
    classify_pytest_outcome,
    ensure_weekly_archive,
    has_failures,
    iso_week_id,
    utc_now_iso,
)
from po_echo.ops_summary import write_integrated_summary


def _run_to_file(cmd: Sequence[str], out_path: Path, env: dict[str, str]) -> tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    out_path.write_text(
        f"$ {' '.join(cmd)}\n\n# stdout\n{result.stdout}\n\n# stderr\n{result.stderr}\n",
        encoding="utf-8",
    )
    return result.returncode, result.stdout, result.stderr


def _initialize_kpi_delta(template_path: Path, out_path: Path, week_id: str, compare_to: str) -> None:
    """Initialize kpi delta report from template while binding header values."""

    template = template_path.read_text(encoding="utf-8")
    template = template.replace("- week_id: `YYYY-Www`", f"- week_id: `{week_id}`")
    template = template.replace("- compared_to: `YYYY-Www`", f"- compared_to: `{compare_to}`")
    out_path.write_text(template, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create weekly audit archive bundle for P2 Sprint-2")
    parser.add_argument("--week-id", help="Override ISO week id (YYYY-Www)")
    parser.add_argument("--root", default=".", help="Repository root path")
    parser.add_argument("--operator", default="automation", help="Operator/team name")
    parser.add_argument("--compare-to", default="<previous week>", help="Compared week id for KPI delta")
    parser.add_argument(
        "--hmac-secret",
        default=os.environ.get("DEMO_C_HMAC_SECRET", ""),
        help="Demo C HMAC secret. Can also be set by DEMO_C_HMAC_SECRET.",
    )
    parser.add_argument(
        "--no-fail-on-fail",
        action="store_true",
        help="Do not return non-zero even when one or more commands are FAIL.",
    )
    parser.add_argument(
        "--integrated-summary-out",
        default="reports/operations/p2_integrated_summary.json",
        help="Path for integrated weekly/monthly summary output.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    week_id = args.week_id or iso_week_id()
    archive = ensure_weekly_archive(root, week_id)

    manifest_tpl = root / "docs" / "templates" / "p2_audit_archive_manifest.md"
    kpi_tpl = root / "docs" / "templates" / "p2_kpi_delta_report.md"
    shutil.copy(manifest_tpl, archive.manifest)
    _initialize_kpi_delta(kpi_tpl, archive.kpi_delta, week_id=week_id, compare_to=args.compare_to)

    env = os.environ.copy()
    env["RUN_PUBLIC_BENCHMARKS"] = "1"

    outcomes: list[CommandOutcome] = []

    rc, stdout, stderr = _run_to_file(
        [sys.executable, "-m", "pytest", "-q", "tests/benchmarks/benchmark_voice_boundary.py"],
        archive.benchmark_voice_boundary_log,
        env,
    )
    outcomes.append(
        CommandOutcome(
            name="benchmark_voice_boundary",
            return_code=rc,
            status=classify_pytest_outcome(rc, stdout, stderr),
        )
    )

    rc, stdout, stderr = _run_to_file(
        [sys.executable, "-m", "pytest", "-q", "tests/benchmarks/benchmark_rth.py"],
        archive.benchmark_rth_log,
        env,
    )
    outcomes.append(
        CommandOutcome(
            name="benchmark_rth",
            return_code=rc,
            status=classify_pytest_outcome(rc, stdout, stderr),
        )
    )

    if args.hmac_secret:
        demo_cmd = [sys.executable, "docs/demo_c_example.py", "--pretty", "--hmac-secret", args.hmac_secret]
    else:
        demo_cmd = [sys.executable, "docs/demo_c_example.py", "--pretty"]
    demo_rc = subprocess.run(demo_cmd, capture_output=True, text=True, env=env)
    archive.demo_c_receipt.write_text(demo_rc.stdout or demo_rc.stderr, encoding="utf-8")
    outcomes.append(
        CommandOutcome(
            name="demo_c_receipt",
            return_code=demo_rc.returncode,
            status="PASS" if demo_rc.returncode == 0 else "FAIL",
        )
    )

    registry = root / ".keys" / "registry.json"
    if registry.exists():
        archive.registry_snapshot.write_text(registry.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        archive.registry_snapshot.write_text("{}\n", encoding="utf-8")

    triage = [
        "# Weekly Audit Triage Note",
        f"- week_id: {week_id}",
        f"- generated_at_utc: {utc_now_iso()}",
        f"- operator: {args.operator}",
        f"- compare_to: {args.compare_to}",
        "",
        "## Command Status",
    ]
    triage.extend([f"- {x.name}: {x.status} (rc={x.return_code})" for x in outcomes])
    triage.append("")
    triage.append("## Responsibility Boundary")
    triage.append("- この記録は監査証跡の収集と一次判定までを責務とする。")
    triage.append("- 公開可否とリスク受容の最終判断は人間オーナー/組織責務とする。")
    archive.triage_note.write_text("\n".join(triage) + "\n", encoding="utf-8")

    had_failures = has_failures(outcomes)
    summary = {
        "week_id": week_id,
        "archive_dir": str(archive.base_dir.relative_to(root)),
        "return_codes": {x.name: x.return_code for x in outcomes},
        "statuses": {x.name: x.status for x in outcomes},
        "overall_status": "FAIL" if had_failures else "PASS_OR_SKIPPED",
    }

    _, integrated_path = write_integrated_summary(root=root, out_path=Path(args.integrated_summary_out))
    summary["integrated_summary_path"] = str(integrated_path.relative_to(root))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if had_failures and not args.no_fail_on_fail:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
