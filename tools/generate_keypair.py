#!/usr/bin/env python3
"""
Ed25519 + HMAC key material generator for Echo Mark dual signature.

This tool generates key material for Echo Mark v3 dual-signature mode:
- Ed25519 private/public key pair (asymmetric, public verification)
- HMAC secret (symmetric fallback / internal verification)

Usage:
    python tools/generate_keypair.py --key-id v1 --output .keys/ --registry
    python tools/generate_keypair.py --key-id v2 --output .keys/ --registry --with-hmac
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import secrets
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

try:
    from nacl.encoding import HexEncoder
    from nacl.signing import SigningKey
except ImportError:
    print("Error: PyNaCl not installed. Run: pip install pynacl", file=sys.stderr)
    sys.exit(1)


ALLOWED_KEY_ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")


def validate_key_id(key_id: str) -> None:
    """Validate key_id to keep filenames and registry deterministic and safe."""
    if not key_id:
        raise ValueError("key_id must not be empty")
    if len(key_id) > 64:
        raise ValueError("key_id must be <= 64 characters")
    if key_id.startswith("."):
        raise ValueError("key_id must not start with '.'")
    if any(ch not in ALLOWED_KEY_ID_CHARS for ch in key_id):
        raise ValueError("key_id contains unsupported characters: use [A-Za-z0-9_-]")


def generate_key_material(key_id: str, with_hmac: bool = False) -> dict[str, str | None]:
    """Generate Ed25519 keypair and optional HMAC secret."""
    validate_key_id(key_id)
    private_key = SigningKey.generate()
    public_key = private_key.verify_key

    result: dict[str, str | None] = {
        "key_id": key_id,
        "private_key": private_key.encode(HexEncoder).decode(),
        "public_key": public_key.encode(HexEncoder).decode(),
        "algorithm": "Ed25519",
        "created_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "hmac_secret": None,
        "signature_mode": "ed25519",
    }

    if with_hmac:
        # 32-byte random secret for HMAC-SHA256 usage, hex encoded.
        result["hmac_secret"] = secrets.token_hex(32)
        result["signature_mode"] = "ed25519+hmac"

    return result


def _atomic_write_text(path: Path, text: str) -> None:
    """Atomically write text to avoid partial file writes during interruption."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        tmp.write(text)
        temp_path = Path(tmp.name)
    temp_path.replace(path)


def save_key_material(key_material: dict[str, str | None], output_dir: Path, overwrite: bool = False) -> None:
    """Save generated key material to files with explicit permission boundaries."""
    output_dir.mkdir(parents=True, exist_ok=True)

    key_id = str(key_material["key_id"])
    private_file = output_dir / f"{key_id}.private.key"
    public_file = output_dir / f"{key_id}.public.key"
    hmac_file = output_dir / f"{key_id}.hmac.key"

    targets = [private_file, public_file]
    if key_material.get("hmac_secret"):
        targets.append(hmac_file)

    if not overwrite:
        conflicts = [str(path) for path in targets if path.exists()]
        if conflicts:
            raise FileExistsError(
                "Refusing to overwrite existing files without --overwrite: " + ", ".join(conflicts)
            )

    _atomic_write_text(private_file, f"{key_material['private_key']}\n")
    os.chmod(private_file, 0o600)

    _atomic_write_text(public_file, f"{key_material['public_key']}\n")

    if key_material.get("hmac_secret"):
        _atomic_write_text(hmac_file, f"{key_material['hmac_secret']}\n")
        os.chmod(hmac_file, 0o600)

    # Machine-readable metadata snapshot for auditing and replayable ops.
    metadata_file = output_dir / f"{key_id}.metadata.json"
    _atomic_write_text(metadata_file, json.dumps(key_material, indent=2, ensure_ascii=False) + "\n")

    print("✓ Generated key material:")
    print(f"  Private key: {private_file} (chmod 600 - secret)")
    print(f"  Public key:  {public_file} (public)")
    if key_material.get("hmac_secret"):
        print(f"  HMAC key:    {hmac_file} (chmod 600 - secret)")
    print(f"  Metadata:    {metadata_file}")
    print(f"\n  Public key:  {key_material['public_key']}")
    print(f"  Created at:  {key_material['created_at']}")


def update_registry(
    key_material: dict[str, str | None],
    output_dir: Path,
    status: str = "active",
    overwrite: bool = False,
) -> None:
    """Update public key registry with status lifecycle data."""
    registry_file = output_dir / "registry.json"

    if registry_file.exists():
        with open(registry_file, encoding="utf-8") as f:
            registry = json.load(f)
    else:
        registry = {"keys": []}

    key_id = str(key_material["key_id"])
    existing = [entry for entry in registry.get("keys", []) if entry.get("key_id") == key_id]
    if existing and not overwrite:
        raise FileExistsError(
            f"Key ID '{key_id}' already exists in registry. Re-run with --overwrite to rotate in-place."
        )

    registry["keys"] = [entry for entry in registry.get("keys", []) if entry.get("key_id") != key_id]
    registry["keys"].append(
        {
            "key_id": key_id,
            "public_key": key_material["public_key"],
            "algorithm": key_material["algorithm"],
            "created_at": key_material["created_at"],
            "expires_at": None,
            "status": status,
            "signature_mode": key_material["signature_mode"],
            "hmac_fallback": bool(key_material.get("hmac_secret")),
        }
    )
    registry["keys"].sort(key=lambda entry: entry["created_at"], reverse=True)

    _atomic_write_text(registry_file, json.dumps(registry, indent=2, ensure_ascii=False) + "\n")

    print(f"\n✓ Updated registry: {registry_file}")
    print(f"  Total keys: {len(registry['keys'])}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Ed25519(+HMAC) key material for Echo Mark dual signature",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/generate_keypair.py --key-id v1 --output .keys/ --registry
  python tools/generate_keypair.py --key-id v2 --output .keys/ --registry --with-hmac

Load in shell:
  export ECHO_MARK_PRIVATE_KEY="$(cat .keys/v1.private.key)"
  export ECHO_MARK_PUBLIC_KEY="$(cat .keys/v1.public.key)"
  export ECHO_MARK_SECRET="$(cat .keys/v1.hmac.key)"  # only if --with-hmac
        """,
    )

    parser.add_argument("--key-id", required=True, help="Key identifier (e.g., 'v1', '2026-01')")
    parser.add_argument("--output", type=Path, default=Path(".keys"), help="Output directory")
    parser.add_argument("--registry", action="store_true", help="Update registry.json")
    parser.add_argument(
        "--status",
        default="active",
        choices=["active", "inactive", "revoked"],
        help="Registry status (default: active)",
    )
    parser.add_argument(
        "--with-hmac",
        action="store_true",
        help="Also generate a 32-byte HMAC secret for dual-signature operation",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing key files and registry entry for the same key_id",
    )

    args = parser.parse_args()

    print(f"Generating key material for key_id '{args.key_id}'...")
    key_material = generate_key_material(args.key_id, with_hmac=args.with_hmac)
    save_key_material(key_material, args.output, overwrite=args.overwrite)

    if args.registry:
        update_registry(key_material, args.output, status=args.status, overwrite=args.overwrite)

    print("\n⚠️  SECURITY BOUNDARY:")
    print("  - NEVER commit .keys/ to git")
    print("  - Private/HMAC keys stay issuer-side only")
    print("  - Public key and registry are distribution-safe")
    print("  - Every verifier must independently validate registry + badge")
    print("  - Project Echo 不変原則：テストが落ちたら即修正必須")


if __name__ == "__main__":
    main()
