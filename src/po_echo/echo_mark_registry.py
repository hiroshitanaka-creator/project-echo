"""Echo Mark v3 key management and registry helpers."""

from __future__ import annotations

import hmac
import json
import os
from pathlib import Path
from typing import Any, cast


def parse_key_store(keys_str: str) -> dict[str, str]:
    """Parse ``key_id=secret;key_id2=secret2`` format."""
    store: dict[str, str] = {}
    for chunk in keys_str.split(";"):
        if "=" not in chunk:
            continue
        key_id, value = chunk.split("=", 1)
        key_id = key_id.strip()
        value = value.strip()
        if key_id and value:
            store[key_id] = value
    return store


def get_key_store() -> dict[str, str]:
    """Load HMAC key store from environment with v1 fallback."""
    store = parse_key_store(os.getenv("ECHO_MARK_KEYS", ""))
    legacy = os.getenv("ECHO_MARK_SECRET", "")
    if legacy:
        store.setdefault("default", legacy)
    return store


def get_ed25519_private_store() -> dict[str, str]:
    """Load Ed25519 private key mapping from environment."""
    store = parse_key_store(os.getenv("ECHO_MARK_ED25519_PRIVATE_KEYS", ""))
    single = os.getenv("ECHO_MARK_PRIVATE_KEY", "")
    if single:
        store.setdefault("default", single)
    return store


def get_ed25519_public_store() -> dict[str, str]:
    """Load Ed25519 public key mapping from environment."""
    store = parse_key_store(os.getenv("ECHO_MARK_ED25519_PUBLIC_KEYS", ""))
    single = os.getenv("ECHO_MARK_PUBLIC_KEY", "")
    if single:
        store.setdefault("default", single)
    return store


def get_active_key_id() -> str:
    """Return active key id for signing."""
    return os.getenv("ECHO_MARK_ACTIVE_KEY_ID", "default")


def load_public_key_registry(registry_path: Path | str = ".keys/registry.json") -> dict[str, Any]:
    """Load public key registry JSON from disk."""
    registry_file = Path(registry_path)
    if not registry_file.exists():
        raise FileNotFoundError(f"Public key registry not found: {registry_file}")

    data = json.loads(registry_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("keys"), list):
        raise ValueError("Invalid public key registry format")
    return cast(dict[str, Any], data)


def find_registry_key_entry(
    key_id: str,
    registry_path: Path | str = ".keys/registry.json",
) -> dict[str, Any] | None:
    """Find registry key entry by key_id with status-aware selection."""
    try:
        registry = load_public_key_registry(registry_path)
    except (FileNotFoundError, ValueError):
        return None

    entries = [entry for entry in registry.get("keys", []) if isinstance(entry, dict)]
    matches = [entry for entry in entries if entry.get("key_id") == key_id]
    if not matches:
        return None

    status_rank = {"active": 0, "inactive": 1, "revoked": 2}
    matches.sort(key=lambda entry: status_rank.get(str(entry.get("status", "active")), 3))
    return cast(dict[str, Any], matches[0])


def get_public_key_from_registry(
    key_id: str,
    registry_path: Path | str = ".keys/registry.json",
) -> str | None:
    """Return registry public key for key_id if key is not revoked."""
    entry = find_registry_key_entry(key_id, registry_path=registry_path)
    if not entry:
        return None
    if str(entry.get("status", "active")) == "revoked":
        return None

    public_key = entry.get("public_key")
    if isinstance(public_key, str) and public_key:
        return public_key
    return None


def verify_key_in_registry(
    key_id: str,
    public_key: str,
    registry_path: Path | str = ".keys/registry.json",
) -> tuple[bool, str]:
    """Verify registry key binding and status."""
    entry = find_registry_key_entry(key_id, registry_path=registry_path)
    if not entry:
        return False, "key_not_found_in_registry"

    status = str(entry.get("status", "active"))
    if status == "revoked":
        return False, "key_revoked"

    registry_key = entry.get("public_key")
    if not isinstance(registry_key, str) or not hmac.compare_digest(registry_key, public_key):
        return False, "public_key_mismatch"

    return True, "key_verified"


def load_ed25519_keypair(key_id: str, keys_dir: Path | str = ".keys") -> dict[str, str]:
    """Load Ed25519 key pair from key directory files."""
    key_dir = Path(keys_dir)
    private_path = key_dir / f"{key_id}.private.key"
    public_path = key_dir / f"{key_id}.public.key"
    return {
        "key_id": key_id,
        "private_key": private_path.read_text(encoding="utf-8").strip(),
        "public_key": public_path.read_text(encoding="utf-8").strip(),
    }


def load_ed25519_private_key_from_env() -> str | None:
    """Compatibility helper for legacy private key env var."""
    return os.getenv("ECHO_MARK_PRIVATE_KEY")


def load_ed25519_public_key_from_env() -> str | None:
    """Compatibility helper for legacy public key env var."""
    return os.getenv("ECHO_MARK_PUBLIC_KEY")


def get_secret_from_env() -> str:
    """Legacy secret loader with minimal guardrails."""
    secret = os.getenv("ECHO_MARK_SECRET", "")
    if not secret:
        raise RuntimeError("ECHO_MARK_SECRET is not set")
    if len(secret) < 16:
        raise RuntimeError("ECHO_MARK_SECRET is too short (min 16 chars recommended)")
    return secret


def summarize_public_key_registry(
    registry_path: Path | str = ".keys/registry.json",
    *,
    active_key_id: str | None = None,
) -> dict[str, Any]:
    """Summarize registry key status for rotation/revocation operations.

    Returns a machine-readable summary suitable for CLI output and CI checks.
    """
    registry = load_public_key_registry(registry_path)
    entries = [entry for entry in registry.get("keys", []) if isinstance(entry, dict)]

    counts = {"active": 0, "inactive": 0, "revoked": 0, "unknown": 0}
    key_ids: list[str] = []
    for entry in entries:
        key_id = entry.get("key_id")
        if isinstance(key_id, str) and key_id:
            key_ids.append(key_id)

        status = str(entry.get("status", "active"))
        if status in counts:
            counts[status] += 1
        else:
            counts["unknown"] += 1

    effective_active = active_key_id or get_active_key_id()
    active_entry = find_registry_key_entry(effective_active, registry_path=registry_path)
    active_status = str(active_entry.get("status")) if active_entry else "missing"

    warnings: list[str] = []
    if active_status == "revoked":
        warnings.append("active_key_is_revoked")
    if active_status == "missing":
        warnings.append("active_key_missing_from_registry")
    if counts["active"] == 0:
        warnings.append("no_active_keys_in_registry")

    return {
        "registry_path": str(Path(registry_path)),
        "active_key_id": effective_active,
        "active_key_status": active_status,
        "counts": counts,
        "total_keys": len(entries),
        "key_ids": sorted(set(key_ids)),
        "warnings": warnings,
    }
