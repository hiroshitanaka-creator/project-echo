#!/usr/bin/env python3
"""Lightweight CLI to verify a filled-in KPI alert file has no unfilled placeholders.

Usage:
    python scripts/check_kpi_alert.py reports/audit/2026-W10/kpi_alert.md
    python scripts/check_kpi_alert.py --template docs/templates/p2_kpi_alert.md

Why: prevents silently incomplete alert records from entering the audit trail.
Exits 0 when valid, 1 when unfilled placeholders are detected.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from po_echo.kpi_alert_check import check_kpi_alert_file


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Check a KPI alert file for unfilled placeholder tokens."
    )
    p.add_argument(
        "alert_path",
        type=Path,
        help="Path to the alert markdown file to check.",
    )
    p.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        default=False,
        help="Output result as JSON (default: human-readable).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    path: Path = args.alert_path

    if not path.exists():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        return 2

    result = check_kpi_alert_file(path)

    if args.as_json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        if result.is_valid:
            print(f"OK: {path} — no unfilled placeholders detected.")
        else:
            print(f"FAIL: {path} — {len(result.unfilled_placeholders)} unfilled placeholder(s):")
            for token in result.unfilled_placeholders:
                print(f"  - {token}")

    return 0 if result.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
