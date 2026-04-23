"""Security-safe, deterministic fingerprints for traceability evidence."""

from __future__ import annotations

import hashlib

_SESSION_KEY_FINGERPRINT_DOMAIN = b"project-echo:session-key-fingerprint:v1:"
_SESSION_KEY_FINGERPRINT_HEX_LEN = 32  # 16-byte truncated SHA-256 digest.


def fingerprint_session_key(session_key: str) -> str:
    """Return a one-way traceability token for a session key.

    This intentionally returns a domain-separated hash-based fingerprint, not a
    raw/partial key fragment, so evidence remains traceable without exposing
    secret-adjacent material.
    """
    if not isinstance(session_key, str) or not session_key:
        raise ValueError("session_key must be a non-empty string")

    digest_hex = hashlib.sha256(
        _SESSION_KEY_FINGERPRINT_DOMAIN + session_key.encode("utf-8")
    ).hexdigest()
    return digest_hex[:_SESSION_KEY_FINGERPRINT_HEX_LEN]
