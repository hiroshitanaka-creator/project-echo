#!/usr/bin/env python3
"""Echo Mark v3 key management utility.

Capabilities:
- Generate Ed25519 keypair (+ optional HMAC secret) for dual signature mode.
- Update key registry with explicit active/inactive/revoked status handling.
- Rotate keys robustly with atomic registry writes and status transitions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import secrets
import sys
from pathlib import Path
from typing import Any, cast

try:
    from nacl.encoding import HexEncoder
    from nacl.signing import SigningKey
except ImportError:
    print("Error: PyNaCl not installed. Run: pip install pynacl", file=sys.stderr)
    sys.exit(1)

KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
VALID_STATUS = {"active", "inactive", "revoked"}
UTC = getattr(dt, "UTC", dt.timezone.utc)


def validate_key_id(key_id: str) -> str:
    """Validate key id for file/registry safety.

    Args:
        key_id: Candidate key identifier.

    Returns:
        Normalized key identifier.

    Raises:
        ValueError: If key id is not permitted.
    """
    if not KEY_ID_PATTERN.fullmatch(key_id):
        raise ValueError(
            "Invalid key_id. Use 1-64 chars: alnum, dot, underscore, hyphen; "
            "must start with alnum."
        )
    return key_id


def _validate_status(status: str) -> str:
    if status not in VALID_STATUS:
        raise ValueError(f"Invalid status '{status}'. Must be one of {sorted(VALID_STATUS)}")
    return status


def _write_secret_file(path: Path, value: str) -> None:
    old_umask = os.umask(0o177)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    finally:
        os.umask(old_umask)

    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(value + "\n")


def _write_registry_atomic(registry_path: Path, registry: dict[str, Any]) -> None:
    """Atomically write registry JSON to avoid partial updates.

    Args:
        registry_path: Destination registry path.
        registry: Registry payload.
    """
    tmp_path = registry_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp_path, registry_path)


def generate_keypair(key_id: str) -> dict[str, str]:
    """Generate Ed25519 keypair metadata.

    Args:
        key_id: Logical key identifier.

    Returns:
        Keypair record with key_id/private_key/public_key/algorithm/created_at.
    """
    safe_key_id = validate_key_id(key_id)
    private_key = SigningKey.generate()
    public_key = private_key.verify_key
    return {
        "key_id": safe_key_id,
        "private_key": private_key.encode(HexEncoder).decode(),
        "public_key": public_key.encode(HexEncoder).decode(),
        "algorithm": "Ed25519",
        "created_at": dt.datetime.now(UTC).isoformat(timespec="seconds"),
    }


def generate_hmac_secret() -> str:
    """Generate 256-bit HMAC secret in hex format."""
    return secrets.token_hex(32)


def save_keypair(keypair: dict[str, str], output_dir: Path) -> dict[str, Path]:
    """Save keypair files with secure permissions.

    Args:
        keypair: Generated keypair record.
        output_dir: Destination key directory.

    Returns:
        File path map for saved private/public keys.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    key_id = keypair["key_id"]
    private_file = output_dir / f"{key_id}.private.key"
    public_file = output_dir / f"{key_id}.public.key"

    _write_secret_file(private_file, keypair["private_key"])
    public_file.write_text(keypair["public_key"] + "\n", encoding="utf-8")

    return {"private_file": private_file, "public_file": public_file}


def save_hmac_secret(key_id: str, output_dir: Path, secret: str) -> Path:
    """Save HMAC secret file with strict permissions."""
    output_dir.mkdir(parents=True, exist_ok=True)
    secret_file = output_dir / f"{key_id}.hmac.secret"
    _write_secret_file(secret_file, secret)
    return secret_file


def _load_registry(registry_file: Path) -> dict[str, Any]:
    """Load registry JSON with shape validation.

    Args:
        registry_file: Registry file path.

    Returns:
        Parsed registry object.

    Raises:
        ValueError: If registry format is invalid.
    """
    if not registry_file.exists():
        return {"keys": []}

    registry = json.loads(registry_file.read_text(encoding="utf-8"))
    if not isinstance(registry, dict) or "keys" not in registry or not isinstance(registry["keys"], list):
        raise ValueError("Invalid registry format. Expected object with list field: keys")

    for entry in registry["keys"]:
        if not isinstance(entry, dict):
            raise ValueError("Invalid registry format. Each key entry must be an object")
        status = str(entry.get("status", "active"))
        _validate_status(status)

    return cast(dict[str, Any], registry)


def _normalize_registry(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize registry key list sorted by creation time descending."""
    keys = cast(list[dict[str, Any]], registry.get("keys", []))
    return sorted(keys, key=lambda k: str(k.get("created_at", "")), reverse=True)


def _set_previous_active_status(keys: list[dict[str, Any]], new_status: str) -> None:
    """Apply status transition to currently active keys."""
    for entry in keys:
        if str(entry.get("status", "active")) == "active":
            entry["status"] = new_status
            entry["rotated_at"] = dt.datetime.now(UTC).isoformat(timespec="seconds")


def update_registry(
    keypair: dict[str, str],
    output_dir: Path,
    status: str = "active",
    force: bool = False,
    deactivate_existing_active: bool = False,
    previous_active_status: str = "inactive",
) -> None:
    """Upsert registry key with robust status management.

    Args:
        keypair: Keypair metadata to register.
        output_dir: Key output directory containing registry.
        status: Status for inserted/updated key.
        force: Overwrite same key id if present.
        deactivate_existing_active: Whether to transition existing active keys.
        previous_active_status: Transition target for previous active keys.

    Raises:
        ValueError: If registry is invalid or update parameters conflict.
    """
    status = _validate_status(status)
    previous_active_status = _validate_status(previous_active_status)
    if not deactivate_existing_active and previous_active_status != "inactive":
        raise ValueError("previous_active_status requires deactivate_existing_active=True")

    registry_file = output_dir / "registry.json"
    registry = _load_registry(registry_file)
    keys = _normalize_registry(registry)

    existing = [entry for entry in keys if entry.get("key_id") == keypair["key_id"]]
    if existing and not force:
        raise ValueError(
            f"Key ID '{keypair['key_id']}' already exists in registry. "
            "Use --force to overwrite."
        )

    if deactivate_existing_active:
        _set_previous_active_status(keys, new_status=previous_active_status)

    keys = [entry for entry in keys if entry.get("key_id") != keypair["key_id"]]
    keys.append(
        {
            "key_id": keypair["key_id"],
            "public_key": keypair["public_key"],
            "algorithm": keypair["algorithm"],
            "created_at": keypair["created_at"],
            "expires_at": None,
            "status": status,
        }
    )

    registry["keys"] = sorted(keys, key=lambda k: str(k.get("created_at", "")), reverse=True)
    _write_registry_atomic(registry_file, registry)


def rotate_keypair(
    key_id: str,
    output_dir: Path,
    with_hmac_secret: bool = True,
    previous_active_status: str = "inactive",
) -> None:
    """Rotate active key material and update registry safely.

    Args:
        key_id: New active key id.
        output_dir: Target key directory.
        with_hmac_secret: Whether to emit new HMAC secret.
        previous_active_status: New status for former active keys.

    Raises:
        ValueError: If key_id/status is invalid.
    """
    previous_active_status = _validate_status(previous_active_status)

    keypair = generate_keypair(key_id)
    paths = save_keypair(keypair, output_dir)
    hmac_path = save_hmac_secret(key_id, output_dir, generate_hmac_secret()) if with_hmac_secret else None

    update_registry(
        keypair,
        output_dir=output_dir,
        status="active",
        force=False,
        deactivate_existing_active=True,
        previous_active_status=previous_active_status,
    )

    print(f"✓ Rotated active key to '{key_id}'")
    print(f"  Private key: {paths['private_file']}")
    print(f"  Public key:  {paths['public_file']}")
    if hmac_path:
        print(f"  HMAC secret: {hmac_path}")
    print(f"  Previous active status: {previous_active_status}")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Echo Mark v3 Ed25519/HMAC key utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen = subparsers.add_parser("generate", help="Generate keypair and optionally update registry")
    gen.add_argument("--key-id", required=True)
    gen.add_argument("--output", type=Path, default=Path(".keys"))
    gen.add_argument("--registry", action="store_true")
    gen.add_argument("--status", default="active", choices=sorted(VALID_STATUS))
    gen.add_argument("--force", action="store_true")
    gen.add_argument("--hmac-secret", action="store_true")

    rot = subparsers.add_parser("rotate", help="Rotate active key and update registry")
    rot.add_argument("--key-id", required=True)
    rot.add_argument("--output", type=Path, default=Path(".keys"))
    rot.add_argument("--no-hmac-secret", action="store_true")
    rot.add_argument(
        "--previous-active-status",
        default="inactive",
        choices=sorted(VALID_STATUS),
        help="Status assigned to previous active keys (inactive or revoked recommended)",
    )

    args = parser.parse_args()

    try:
        if args.command == "generate":
            keypair = generate_keypair(args.key_id)
            paths = save_keypair(keypair, args.output)
            print(f"✓ Generated Ed25519 keypair: {args.key_id}")
            print(f"  Private key: {paths['private_file']}")
            print(f"  Public key:  {paths['public_file']}")

            hmac_path: Path | None = None
            if args.hmac_secret:
                hmac_path = save_hmac_secret(args.key_id, args.output, generate_hmac_secret())
                print(f"  HMAC secret: {hmac_path}")

            if args.registry:
                update_registry(
                    keypair=keypair,
                    output_dir=args.output,
                    status=args.status,
                    force=args.force,
                )
                print(f"✓ Updated registry: {args.output / 'registry.json'}")
        else:
            rotate_keypair(
                key_id=args.key_id,
                output_dir=args.output,
                with_hmac_secret=not args.no_hmac_secret,
                previous_active_status=args.previous_active_status,
            )

        print("\nEnvironment export example:")
        print("  export ECHO_MARK_ACTIVE_KEY_ID=<key_id>")
        print("  export ECHO_MARK_ED25519_PRIVATE_KEYS='k1=<private_hex>;k2=<private_hex>'")
        print("  export ECHO_MARK_KEYS='k1=<hmac_secret>;k2=<hmac_secret>'")
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
