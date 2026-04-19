#!/usr/bin/env python3
"""Audit Echo Mark public-key registry for rotation hygiene.

Usage:
  python scripts/audit_key_registry.py
  python scripts/audit_key_registry.py --registry .keys/registry.json --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from po_echo.echo_mark_registry import audit_public_key_registry_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Echo Mark key registry health.")
    parser.add_argument(
        "--registry",
        default=".keys/registry.json",
        help="Path to public key registry JSON (default: .keys/registry.json).",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON result.")
    args = parser.parse_args()

    report = audit_public_key_registry_file(args.registry)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        summary = report.get("summary", {})
        print(f"[REGISTRY] checked_at={report.get('checked_at_utc')}")
        print(
            "  total={total_keys} active={active_count} revoked={revoked_count} expired={expired_count} duplicate_key_id={duplicate_key_id_count}".format(
                **summary
            )
        )
        findings = report.get("findings", [])
        if findings:
            print(f"  findings={', '.join(findings)}")
        else:
            print("  findings=none")

    if not bool(report.get("ok")):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
