"""Periodic integrity verification helpers for operational jobs."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any


def verify_public_audit_manifest_file(path: Path | str) -> tuple[bool, dict[str, Any]]:
    """Load and verify a public audit manifest JSON file."""
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest must be a JSON object")
    ok = _verify_public_manifest_integrity(payload)
    return ok, payload


def _verify_public_manifest_integrity(manifest: dict[str, Any]) -> bool:
    """Verify manifest checksum with local fallback for runtime compatibility."""
    try:
        # Prefer canonical verifier when importable in current runtime.
        from po_echo.public_audit import verify_public_audit_manifest  # local import by design

        return bool(verify_public_audit_manifest(manifest))
    except Exception:
        stored = (manifest.get("integrity") or {}).get("sha256")
        if not stored:
            return False

        core_payload = {
            k: v
            for k, v in manifest.items()
            if k not in {"generated_at_utc", "responsibility_boundary", "integrity"}
        }
        canonical = json.dumps(core_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return bool(stored == expected)
