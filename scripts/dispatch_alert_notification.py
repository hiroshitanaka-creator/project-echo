#!/usr/bin/env python3
"""Dispatch an alert notification JSON from the integrated ops summary.

Reads reports/operations/p2_integrated_summary.json (or a specified path),
converts overall.has_reported_failures / has_malformed_artifact into a
standardized notification envelope, and writes
reports/operations/p2_alert_notification.json.

Why: downstream tooling (webhook, log shipper, PagerDuty, etc.) needs a
single, stable notification contract rather than digging into the full
summary payload. This script is the seam between internal ops state and
external alert routing.

Usage:
    python scripts/dispatch_alert_notification.py
    python scripts/dispatch_alert_notification.py --summary-in reports/operations/p2_integrated_summary.json
    python scripts/dispatch_alert_notification.py --out /tmp/alert.json
    python scripts/dispatch_alert_notification.py --json  # print to stdout
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

from po_echo.alert_notify import write_alert_notification


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convert integrated ops summary flags into a notification envelope."
    )
    p.add_argument(
        "--summary-in",
        type=Path,
        default=None,
        help=(
            "Path to the integrated summary JSON "
            "(default: reports/operations/p2_integrated_summary.json)."
        ),
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "Output path for notification JSON "
            "(default: reports/operations/p2_alert_notification.json)."
        ),
    )
    p.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        default=False,
        help="Also print notification JSON to stdout.",
    )
    p.add_argument(
        "--fail-on-alert",
        action="store_true",
        default=False,
        help="Exit with code 1 when has_alert is True.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    summary_path: Path = (
        args.summary_in
        if args.summary_in is not None
        else REPO_ROOT / "reports" / "operations" / "p2_integrated_summary.json"
    )

    if not summary_path.exists():
        print(f"ERROR: summary not found: {summary_path}", file=sys.stderr)
        print(
            "Hint: run `python scripts/p2_integrated_summary.py` first.",
            file=sys.stderr,
        )
        return 2

    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid summary JSON: {exc}", file=sys.stderr)
        return 2

    diff_path_str = summary.get("diff_path")
    summary_path_str = str(summary_path.relative_to(REPO_ROOT)) if summary_path.is_relative_to(REPO_ROOT) else str(summary_path)

    payload, out_path = write_alert_notification(
        root=REPO_ROOT,
        summary=summary,
        out_path=args.out,
        summary_path=summary_path_str,
        diff_path=diff_path_str,
    )

    result_doc = {
        "notification_path": str(out_path.relative_to(REPO_ROOT)),
        "has_alert": payload["has_alert"],
        "severity": payload["severity"],
        "flags": payload["flags"],
        "generated_at_utc": payload["generated_at_utc"],
    }

    if args.as_json:
        print(json.dumps(result_doc, ensure_ascii=False, indent=2))
    else:
        status = f"ALERT ({payload['severity']})" if payload["has_alert"] else "OK (no alert)"
        print(f"{status}: notification written to {out_path.relative_to(REPO_ROOT)}")

    return 1 if (args.fail_on_alert and payload["has_alert"]) else 0


if __name__ == "__main__":
    sys.exit(main())
