#!/usr/bin/env python3
"""
Ed25519 Keypair Generator

Generate Ed25519 keypair for Echo Mark signing.

Usage:
    python tools/generate_keypair.py --key-id v1 --output .keys/
    python tools/generate_keypair.py --key-id v2 --output .keys/ --registry

Output:
    .keys/<key_id>.private.key  (KEEP SECRET - chmod 600)
    .keys/<key_id>.public.key   (safe to share)
    .keys/registry.json         (public key registry, optional)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

try:
    from nacl.encoding import HexEncoder
    from nacl.signing import SigningKey
except ImportError:
    print("Error: PyNaCl not installed. Run: pip install pynacl", file=sys.stderr)
    sys.exit(1)


def generate_keypair(key_id: str) -> dict[str, str]:
    """
    Generate Ed25519 keypair.

    Returns:
        {
            "key_id": "v1",
            "private_key": "hex-encoded 32 bytes",
            "public_key": "hex-encoded 32 bytes",
            "algorithm": "Ed25519",
            "created_at": "ISO8601 timestamp"
        }
    """
    # Generate private key
    private_key = SigningKey.generate()

    # Derive public key
    public_key = private_key.verify_key

    return {
        "key_id": key_id,
        "private_key": private_key.encode(HexEncoder).decode(),
        "public_key": public_key.encode(HexEncoder).decode(),
        "algorithm": "Ed25519",
        "created_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
    }


def save_keypair(keypair: dict[str, str], output_dir: Path) -> None:
    """Save keypair to files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    key_id = keypair["key_id"]
    private_file = output_dir / f"{key_id}.private.key"
    public_file = output_dir / f"{key_id}.public.key"

    # Save private key (chmod 600)
    private_file.write_text(keypair["private_key"] + "\n")
    os.chmod(private_file, 0o600)

    # Save public key (readable)
    public_file.write_text(keypair["public_key"] + "\n")

    print("✓ Generated Ed25519 keypair:")
    print(f"  Private key: {private_file} (chmod 600 - KEEP SECRET)")
    print(f"  Public key:  {public_file} (safe to share)")
    print(f"\n  Public key:  {keypair['public_key']}")
    print(f"  Created at:  {keypair['created_at']}")


def update_registry(keypair: dict[str, str], output_dir: Path, status: str = "active") -> None:
    """Update public key registry."""
    registry_file = output_dir / "registry.json"

    # Load existing registry
    if registry_file.exists():
        with open(registry_file) as f:
            registry = json.load(f)
    else:
        registry = {"keys": []}

    # Check if key_id already exists
    existing = [k for k in registry["keys"] if k["key_id"] == keypair["key_id"]]
    if existing:
        print(f"\n⚠️  Key ID '{keypair['key_id']}' already exists in registry")
        response = input("Overwrite? (y/N): ")
        if response.lower() != "y":
            print("Aborted.")
            return
        # Remove existing entry
        registry["keys"] = [k for k in registry["keys"] if k["key_id"] != keypair["key_id"]]

    # Add new key
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

    # Sort by created_at (newest first)
    registry["keys"].sort(key=lambda k: k["created_at"], reverse=True)

    # Save registry
    with open(registry_file, "w") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Updated registry: {registry_file}")
    print(f"  Total keys: {len(registry['keys'])}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Ed25519 keypair for Echo Mark signing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate keypair for key_id 'v1'
  python tools/generate_keypair.py --key-id v1 --output .keys/

  # Generate and update registry
  python tools/generate_keypair.py --key-id v2 --output .keys/ --registry

  # Load keypair in shell
  export ECHO_MARK_PRIVATE_KEY="$(cat .keys/v1.private.key)"
  export ECHO_MARK_PUBLIC_KEY="$(cat .keys/v1.public.key)"
        """,
    )

    parser.add_argument(
        "--key-id",
        required=True,
        help="Key identifier (e.g., 'v1', 'v2', '2026-01')",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".keys"),
        help="Output directory (default: .keys/)",
    )
    parser.add_argument(
        "--registry",
        action="store_true",
        help="Update public key registry (registry.json)",
    )
    parser.add_argument(
        "--status",
        default="active",
        choices=["active", "inactive", "revoked"],
        help="Key status for registry (default: active)",
    )

    args = parser.parse_args()

    # Generate keypair
    print(f"Generating Ed25519 keypair for key_id '{args.key_id}'...")
    keypair = generate_keypair(args.key_id)

    # Save keypair
    save_keypair(keypair, args.output)

    # Update registry (optional)
    if args.registry:
        update_registry(keypair, args.output, args.status)

    # Security reminder
    print("\n⚠️  SECURITY REMINDER:")
    print("  - NEVER commit .keys/ to git (add to .gitignore)")
    print("  - NEVER share private key files")
    print("  - Public keys are safe to share")
    print("  - Private key has restricted permissions (chmod 600)")


if __name__ == "__main__":
    main()
