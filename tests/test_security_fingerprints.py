from __future__ import annotations

from po_echo.security_fingerprints import fingerprint_session_key


def test_fingerprint_is_deterministic_for_same_key() -> None:
    session_key = "a" * 64
    fp1 = fingerprint_session_key(session_key)
    fp2 = fingerprint_session_key(session_key)
    assert fp1 == fp2


def test_fingerprint_differs_for_different_keys() -> None:
    fp1 = fingerprint_session_key("a" * 64)
    fp2 = fingerprint_session_key("b" * 64)
    assert fp1 != fp2


def test_fingerprint_is_not_raw_key_or_partial_fragment() -> None:
    session_key = "1234567890abcdef" * 4
    fp = fingerprint_session_key(session_key)

    assert fp != session_key
    assert fp not in session_key
    assert session_key[:16] not in fp
    assert session_key[-16:] not in fp
    assert len(fp) == 32


def test_fingerprint_rejects_empty_input() -> None:
    try:
        fingerprint_session_key("")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for empty session_key")
