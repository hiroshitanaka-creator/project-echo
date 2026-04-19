#!/usr/bin/env python3
"""Verify tamper-evidence of public audit manifest.

Intended for periodic job execution (cron/CI scheduler).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from po_echo.public_audit import verify_public_audit_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify public audit manifest integrity checksum.")
    parser.add_argument(
        "--manifest",
        default="reports/operations/public_audit_manifest.json",
        help="Path to public audit manifest JSON.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON result.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"[ERROR] manifest not found: {manifest_path}", file=sys.stderr)
        raise SystemExit(2)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ok = verify_public_audit_manifest(manifest)
    result = {"manifest_path": str(manifest_path), "integrity_ok": bool(ok)}

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[PUBLIC_AUDIT] {manifest_path} integrity_ok={ok}")

    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
