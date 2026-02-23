#!/usr/bin/env python3
"""
Ed25519 + HMAC key material generator for Echo Mark dual signature.

Usage:
    python tools/generate_keypair.py --key-id v1 --output .keys/ --registry
    python tools/generate_keypair.py --key-id 2026-01 --output .keys/ --registry --hmac-secret
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
from typing import Any

try:
    from nacl.encoding import HexEncoder
    from nacl.signing import SigningKey
except ImportError:
    print("Error: PyNaCl not installed. Run: pip install pynacl", file=sys.stderr)
    sys.exit(1)

KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def validate_key_id(key_id: str) -> str:
    """Validate key_id format for safe file and registry handling."""
    if not KEY_ID_PATTERN.fullmatch(key_id):
        raise ValueError(
            "Invalid key_id. Use 1-64 chars: alnum, dot, underscore, hyphen; "
            "must start with alnum."
        )
    return key_id


def _write_secret_file(path: Path, value: str) -> None:
    """Write secret material with owner-only permissions."""
    old_umask = os.umask(0o177)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    finally:
        os.umask(old_umask)

    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(value + "\n")


def _write_text_file(path: Path, value: str) -> None:
    path.write_text(value + "\n", encoding="utf-8")


def generate_keypair(key_id: str) -> dict[str, str]:
    """Generate Ed25519 keypair material."""
    normalized_key_id = validate_key_id(key_id)
    private_key = SigningKey.generate()
    public_key = private_key.verify_key

    return {
        "key_id": normalized_key_id,
        "private_key": private_key.encode(HexEncoder).decode(),
        "public_key": public_key.encode(HexEncoder).decode(),
        "algorithm": "Ed25519",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }


def generate_hmac_secret() -> str:
    """Generate 256-bit HMAC secret in hex for dual signature mode."""
    return secrets.token_hex(32)


def save_keypair(keypair: dict[str, str], output_dir: Path) -> dict[str, Path]:
    """Save keypair to files with explicit permission boundaries."""
    output_dir.mkdir(parents=True, exist_ok=True)

    key_id = keypair["key_id"]
    private_file = output_dir / f"{key_id}.private.key"
    public_file = output_dir / f"{key_id}.public.key"

    _write_secret_file(private_file, keypair["private_key"])
    _write_text_file(public_file, keypair["public_key"])

    print("✓ Generated Ed25519 keypair:")
    print(f"  Private key: {private_file} (chmod 600 - secret)")
    print(f"  Public key:  {public_file} (shareable)")
    print(f"  Created at:  {keypair['created_at']}")

    return {
        "private_file": private_file,
        "public_file": public_file,
    }


def save_hmac_secret(key_id: str, output_dir: Path, secret: str) -> Path:
    """Save HMAC secret for dual signature operation."""
    output_dir.mkdir(parents=True, exist_ok=True)
    secret_file = output_dir / f"{key_id}.hmac.secret"
    _write_secret_file(secret_file, secret)
    print(f"✓ Generated HMAC secret: {secret_file} (chmod 600 - secret)")
    return secret_file


def update_registry(
    keypair: dict[str, str], output_dir: Path, status: str = "active", force: bool = False
) -> None:
    """Update public key registry without interactive prompts."""
    registry_file = output_dir / "registry.json"

    if registry_file.exists():
        with open(registry_file, encoding="utf-8") as f:
            registry: dict[str, Any] = json.load(f)
    else:
        registry = {"keys": []}

    if not isinstance(registry, dict) or "keys" not in registry or not isinstance(registry["keys"], list):
        raise ValueError("Invalid registry format. Expected object with list field: keys")

    existing = [k for k in registry["keys"] if k.get("key_id") == keypair["key_id"]]
    if existing and not force:
        raise ValueError(
            f"Key ID '{keypair['key_id']}' already exists in registry. "
            "Use --force to overwrite."
        )

    registry["keys"] = [k for k in registry["keys"] if k.get("key_id") != keypair["key_id"]]
    registry["keys"].append(
        {
            "key_id": keypair["key_id"],
            "public_key": keypair["public_key"],
            "algorithm": keypair["algorithm"],
            "created_at": keypair["created_at"],
            "expires_at": None,
            "status": status,
        }
    )
    registry["keys"].sort(key=lambda k: k.get("created_at", ""), reverse=True)

    with open(registry_file, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"✓ Updated registry: {registry_file}")
    print(f"  Total keys: {len(registry['keys'])}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Ed25519 + optional HMAC secret for Echo Mark dual signature",
    )
    parser.add_argument("--key-id", required=True, help="Key identifier")
    parser.add_argument("--output", type=Path, default=Path(".keys"), help="Output directory")
    parser.add_argument("--registry", action="store_true", help="Update public key registry")
    parser.add_argument(
        "--status",
        default="active",
        choices=["active", "inactive", "revoked"],
        help="Key status in registry",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing key_id in registry")
    parser.add_argument(
        "--hmac-secret",
        action="store_true",
        help="Generate HMAC secret file for dual signature mode",
    )

    args = parser.parse_args()

    try:
        print(f"Generating Ed25519 keypair for key_id '{args.key_id}'...")
        keypair = generate_keypair(args.key_id)
        paths = save_keypair(keypair, args.output)

        if args.hmac_secret:
            hmac_secret = generate_hmac_secret()
            hmac_path = save_hmac_secret(keypair["key_id"], args.output, hmac_secret)
        else:
            hmac_path = None

        if args.registry:
            update_registry(keypair, args.output, args.status, force=args.force)

        print("\nSecurity boundaries:")
        print("  - Never commit private key or HMAC secret files")
        print("  - Public key + registry remain auditable and shareable")
        print("  - Keep secret files in access-controlled storage")

        print("\nEnvironment export example:")
        print(f"  export ECHO_MARK_PRIVATE_KEY=\"$(cat {paths['private_file']})\"")
        if hmac_path is not None:
            print(f"  export ECHO_MARK_SECRET=\"$(cat {hmac_path})\"")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
