#!/usr/bin/env python3
"""Generate integrated P2 weekly/monthly archive summary.

Why: Sprint-3 observability requires one machine-readable report that merges
latest weekly audit and monthly gift rehearsal status.
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

from po_echo.ops_summary import write_integrated_summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Create integrated P2 operations summary")
    parser.add_argument("--root", default=".", help="Repository root path")
    parser.add_argument(
        "--out",
        default="reports/operations/p2_integrated_summary.json",
        help="Output JSON file path (relative to root if not absolute)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = root / out_path
    summary, out_path, diff_path = write_integrated_summary(root=root, out_path=out_path)
    summary["output_path"] = str(out_path.relative_to(root))
    summary["diff_path"] = str(diff_path.relative_to(root))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
