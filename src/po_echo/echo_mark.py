"""Backwards-compatible Echo Mark API surface.

This module intentionally re-exports the legacy public API while
implementation is split across:
- ``echo_mark_core``: payload/signature construction
- ``echo_mark_verify``: verification/replay guards
- ``echo_mark_registry``: key registry/rotation helpers
"""

from po_echo.echo_mark_core import (
    EchoMarkSigningError,
    NACL_AVAILABLE,
    badge_text,
    build_payload,
    canonical_json,
    generate_echo_mark,
    hmac_sha256_hex,
    label_from_boundary,
    make_echo_mark,
    make_echo_mark_dual,
    make_echo_mark_ed25519,
    sha256_hex,
    sign_ed25519,
    sign_mark,
)
from po_echo.echo_mark_registry import (
    get_active_key_id,
    get_key_store,
    get_public_key_from_registry,
    get_secret_from_env,
    load_ed25519_keypair,
    load_ed25519_private_key_from_env,
    load_ed25519_public_key_from_env,
    load_public_key_registry,
    parse_key_store,
    verify_key_in_registry,
)
from po_echo.echo_mark_verify import (
    VerificationChecks,
    validate_timestamp,
    verify_echo_mark,
    verify_echo_mark_dual,
    verify_echo_mark_ed25519,
    verify_ed25519,
    verify_mark,
)

__all__ = [
    "NACL_AVAILABLE",
    "EchoMarkSigningError",
    "VerificationChecks",
    "badge_text",
    "build_payload",
    "canonical_json",
    "generate_echo_mark",
    "get_active_key_id",
    "get_key_store",
    "get_public_key_from_registry",
    "get_secret_from_env",
    "hmac_sha256_hex",
    "label_from_boundary",
    "load_ed25519_keypair",
    "load_ed25519_private_key_from_env",
    "load_ed25519_public_key_from_env",
    "load_public_key_registry",
    "make_echo_mark",
    "make_echo_mark_dual",
    "make_echo_mark_ed25519",
    "parse_key_store",
    "sha256_hex",
    "sign_ed25519",
    "sign_mark",
    "validate_timestamp",
    "verify_echo_mark",
    "verify_echo_mark_dual",
    "verify_echo_mark_ed25519",
    "verify_ed25519",
    "verify_key_in_registry",
    "verify_mark",
]
