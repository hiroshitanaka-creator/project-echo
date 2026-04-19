"""Periodic job: verify tamper integrity of public audit manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from po_echo.integrity_jobs import verify_public_audit_manifest_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify public audit manifest checksum for tamper detection."
    )
    parser.add_argument(
        "--manifest",
        default="reports/operations/public_audit_manifest.json",
        help="Path to public audit manifest JSON.",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}")
        raise SystemExit(2)

    ok, payload = verify_public_audit_manifest_file(manifest_path)
    generated_at = payload.get("generated_at_utc", "unknown")
    if ok:
        print(f"OK: manifest integrity verified ({manifest_path}) generated_at={generated_at}")
        raise SystemExit(0)

    print(f"FAIL: manifest integrity mismatch ({manifest_path}) generated_at={generated_at}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()

