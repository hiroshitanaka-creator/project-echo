#!/usr/bin/env python3
"""Export a public audit manifest from the latest integrated summary.

Why: external reviewers need a single command to produce a tamper-evident,
redacted audit manifest from internal operational data. This script acts as
the delivery boundary between internal ops tooling and external disclosure.

Usage:
    python scripts/export_public_audit.py
    python scripts/export_public_audit.py --out reports/operations/public_audit_manifest.json
    python scripts/export_public_audit.py --summary-in reports/operations/p2_integrated_summary.json
    python scripts/export_public_audit.py --verify
    python scripts/export_public_audit.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from po_echo.public_audit import verify_public_audit_manifest, write_public_audit_manifest

_DEFAULT_SUMMARY_PATH = _REPO_ROOT / "reports" / "operations" / "p2_integrated_summary.json"
_DEFAULT_OUT_PATH = _REPO_ROOT / "reports" / "operations" / "public_audit_manifest.json"


def _load_summary(summary_path: Path) -> dict:
    if not summary_path.exists():
        print(
            f"[ERROR] integrated summary not found: {summary_path}\n"
            "Run 'python scripts/p2_integrated_summary.py' first.",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        return json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[ERROR] failed to parse summary JSON: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_export(args: argparse.Namespace) -> None:
    summary_path = Path(args.summary_in) if args.summary_in else _DEFAULT_SUMMARY_PATH
    out_path = Path(args.out) if args.out else _DEFAULT_OUT_PATH

    summary = _load_summary(summary_path)
    manifest, written = write_public_audit_manifest(
        _REPO_ROOT,
        summary,
        out_path=out_path,
    )

    if args.json:
        print(json.dumps({"status": "OK", "output_path": str(written.relative_to(_REPO_ROOT))}, ensure_ascii=False))
    else:
        print(f"[OK] public audit manifest written: {written.relative_to(_REPO_ROOT)}")
        print(f"     schema_version : {manifest.get('schema_version')}")
        print(f"     generated_at   : {manifest.get('generated_at_utc')}")
        print(f"     sha256         : {manifest.get('integrity', {}).get('sha256', 'N/A')}")
        has_failures = manifest.get("kpi_status", {}).get("has_reported_failures", False)
        has_malformed = manifest.get("kpi_status", {}).get("has_malformed_artifact", False)
        if has_failures or has_malformed:
            print("[WARN] manifest contains raised KPI flags — review before public release.")

    # Responsibility boundary: this script only generates the manifest.
    # Public release decision is human/organisation responsibility.


def cmd_verify(args: argparse.Namespace) -> None:
    manifest_path = Path(args.out) if args.out else _DEFAULT_OUT_PATH
    if not manifest_path.exists():
        print(f"[ERROR] manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[ERROR] failed to parse manifest JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    ok = verify_public_audit_manifest(manifest)
    if args.json:
        print(json.dumps({"verified": ok, "path": str(manifest_path.relative_to(_REPO_ROOT))}, ensure_ascii=False))
    else:
        status = "[OK] VERIFIED" if ok else "[FAIL] INTEGRITY CHECK FAILED"
        print(f"{status}: {manifest_path.relative_to(_REPO_ROOT)}")

    if not ok:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export or verify a public audit manifest for Project Echo."
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify integrity of an existing manifest instead of generating a new one.",
    )
    parser.add_argument(
        "--summary-in",
        metavar="PATH",
        default=None,
        help="Path to p2_integrated_summary.json (default: reports/operations/p2_integrated_summary.json).",
    )
    parser.add_argument(
        "--out",
        metavar="PATH",
        default=None,
        help="Output path for the manifest (default: reports/operations/public_audit_manifest.json).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON output instead of human-readable text.",
    )

    args = parser.parse_args()

    if args.verify:
        cmd_verify(args)
    else:
        cmd_export(args)


if __name__ == "__main__":
    main()
