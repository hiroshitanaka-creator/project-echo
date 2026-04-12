"""Tests for po_echo.hardware_audit_log (hardware-signed transparent log)."""

from __future__ import annotations

import dataclasses

import pytest

from po_echo.hardware_audit_log import (
    AuditLogEntry,
    HardwareAuditLog,
    InclusionReceipt,
    SignedTreeHead,
    SoftwareKeyProvider,
)
from po_echo.merkle_log import leaf_hash


# ---------------------------------------------------------------------------
# SoftwareKeyProvider
# ---------------------------------------------------------------------------


def test_software_key_provider_generate_default_key_id():
    provider = SoftwareKeyProvider.generate()
    assert provider.key_id == "sw-ed25519-v1"


def test_software_key_provider_custom_key_id():
    provider = SoftwareKeyProvider.generate(key_id="device-42")
    assert provider.key_id == "device-42"


def test_software_key_provider_public_key_hex_length():
    """Ed25519 public key is 32 bytes = 64 hex chars."""
    provider = SoftwareKeyProvider.generate()
    assert len(provider.public_key_hex()) == 64


def test_software_key_provider_sign_is_verifiable():
    """Signature produced by SoftwareKeyProvider must verify with its own public key."""
    from nacl.encoding import HexEncoder
    from nacl.signing import VerifyKey

    provider = SoftwareKeyProvider.generate()
    msg = b"test message for audit log"
    sig = provider.sign(msg)
    vk = VerifyKey(provider.public_key_hex().encode(), encoder=HexEncoder)
    vk.verify(msg, sig)  # raises BadSignatureError on failure


def test_software_key_provider_two_instances_differ():
    """Each generate() call produces a distinct key pair."""
    p1 = SoftwareKeyProvider.generate()
    p2 = SoftwareKeyProvider.generate()
    assert p1.public_key_hex() != p2.public_key_hex()


def test_software_key_provider_is_hardware_key_provider():
    """SoftwareKeyProvider must satisfy the HardwareKeyProvider protocol."""
    from po_echo.hardware_audit_log import HardwareKeyProvider

    provider = SoftwareKeyProvider.generate()
    assert isinstance(provider, HardwareKeyProvider)


# ---------------------------------------------------------------------------
# HardwareAuditLog — append
# ---------------------------------------------------------------------------


def test_append_returns_audit_log_entry():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    entry = log.append({"label": "ECHO_VERIFIED", "bias": 0.1})
    assert isinstance(entry, AuditLogEntry)


def test_append_entry_index_starts_at_zero():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    entry = log.append({"x": 1})
    assert entry.index == 0


def test_append_index_increments():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    e0 = log.append({"a": 1})
    e1 = log.append({"b": 2})
    e2 = log.append({"c": 3})
    assert e0.index == 0
    assert e1.index == 1
    assert e2.index == 2


def test_append_entry_key_id_matches_provider():
    provider = SoftwareKeyProvider.generate(key_id="test-device")
    log = HardwareAuditLog(provider)
    entry = log.append({"a": 1})
    assert entry.key_id == "test-device"


def test_append_leaf_hash_hex_is_64_chars():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    entry = log.append({"data": "hello"})
    assert len(entry.leaf_hash_hex) == 64


def test_append_device_sig_hex_is_128_chars():
    """Ed25519 signature is 64 bytes = 128 hex chars."""
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    entry = log.append({"data": "hello"})
    assert len(entry.device_sig_hex) == 128


def test_append_does_not_store_raw_content():
    """Privacy invariant: raw content string must not appear in the entry dict."""
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    secret_value = "topsecretpassword_12345"
    entry = log.append({"secret": secret_value})
    entry_str = str(entry.to_dict())
    assert secret_value not in entry_str


def test_append_different_content_produces_different_leaf_hashes():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    e0 = log.append({"x": 1})
    e1 = log.append({"x": 2})
    assert e0.leaf_hash_hex != e1.leaf_hash_hex


def test_append_same_content_same_salt_same_leaf_hash():
    """Deterministic: same content + same salt → identical leaf hash."""
    salt = b"fixed-salt-32bytes-padding-12345"[:32]
    provider = SoftwareKeyProvider.generate()
    log_a = HardwareAuditLog(provider, salt=salt)
    log_b = HardwareAuditLog(provider, salt=salt)
    e_a = log_a.append({"label": "ECHO_VERIFIED"})
    e_b = log_b.append({"label": "ECHO_VERIFIED"})
    assert e_a.leaf_hash_hex == e_b.leaf_hash_hex


def test_append_same_content_different_salt_different_leaf_hash():
    """Different salt → different leaf hash (privacy protection)."""
    provider = SoftwareKeyProvider.generate()
    log_a = HardwareAuditLog(provider, salt=b"a" * 32)
    log_b = HardwareAuditLog(provider, salt=b"b" * 32)
    e_a = log_a.append({"val": 42})
    e_b = log_b.append({"val": 42})
    assert e_a.leaf_hash_hex != e_b.leaf_hash_hex


def test_entries_returns_all_appended():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    for i in range(5):
        log.append({"i": i})
    assert len(log.entries()) == 5


def test_entries_returns_copy_not_reference():
    """Mutating the returned list must not affect the log's internal state."""
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    log.append({"a": 1})
    entries_ref = log.entries()
    entries_ref.clear()
    assert len(log.entries()) == 1


# ---------------------------------------------------------------------------
# HardwareAuditLog — salt
# ---------------------------------------------------------------------------


def test_salt_is_32_bytes_by_default():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    assert len(log.salt) == 32


def test_custom_salt_is_preserved():
    custom_salt = b"custom-salt-exactly-32-bytes!!!!"[:32]
    log = HardwareAuditLog(SoftwareKeyProvider.generate(), salt=custom_salt)
    assert log.salt == custom_salt


def test_two_logs_default_salts_differ():
    log_a = HardwareAuditLog(SoftwareKeyProvider.generate())
    log_b = HardwareAuditLog(SoftwareKeyProvider.generate())
    assert log_a.salt != log_b.salt


# ---------------------------------------------------------------------------
# HardwareAuditLog — commit
# ---------------------------------------------------------------------------


def test_commit_returns_signed_tree_head():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    log.append({"a": 1})
    sth = log.commit()
    assert isinstance(sth, SignedTreeHead)


def test_commit_tree_size_matches_entry_count():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    for i in range(4):
        log.append({"i": i})
    sth = log.commit()
    assert sth.tree_size == 4


def test_commit_root_hash_hex_is_64_chars():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    log.append({"a": 1})
    sth = log.commit()
    assert len(sth.root_hash_hex) == 64


def test_commit_sig_hex_is_128_chars():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    log.append({"a": 1})
    sth = log.commit()
    assert len(sth.sig_hex) == 128


def test_commit_single_entry_root_equals_leaf_hash():
    """Root of a 1-leaf tree is the leaf hash itself."""
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    entry = log.append({"val": 99})
    sth = log.commit()
    assert sth.root_hash_hex == entry.leaf_hash_hex


def test_commit_empty_log_raises_value_error():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    with pytest.raises(ValueError, match="empty"):
        log.commit()


def test_commit_can_be_called_multiple_times():
    """Each commit() must reflect the current tree."""
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    log.append({"a": 1})
    sth1 = log.commit()
    log.append({"b": 2})
    sth2 = log.commit()
    assert sth1.tree_size == 1
    assert sth2.tree_size == 2
    assert sth1.root_hash_hex != sth2.root_hash_hex


# ---------------------------------------------------------------------------
# HardwareAuditLog — get_receipt
# ---------------------------------------------------------------------------


def test_get_receipt_before_commit_raises():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    log.append({"a": 1})
    with pytest.raises(RuntimeError, match="commit"):
        log.get_receipt(0)


def test_get_receipt_returns_inclusion_receipt():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    log.append({"a": 1})
    log.commit()
    receipt = log.get_receipt(0)
    assert isinstance(receipt, InclusionReceipt)


def test_get_receipt_leaf_index_matches():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    for i in range(3):
        log.append({"i": i})
    log.commit()
    for i in range(3):
        receipt = log.get_receipt(i)
        assert receipt.leaf_index == i


def test_get_receipt_leaf_hash_hex_matches_entry():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    entry = log.append({"x": 7})
    log.commit()
    receipt = log.get_receipt(0)
    assert receipt.leaf_hash_hex == entry.leaf_hash_hex


def test_get_receipt_out_of_range_raises_index_error():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    log.append({"a": 1})
    log.commit()
    with pytest.raises(IndexError):
        log.get_receipt(5)


def test_get_receipt_negative_index_raises_index_error():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    log.append({"a": 1})
    log.commit()
    with pytest.raises(IndexError):
        log.get_receipt(-1)


def test_get_receipt_single_leaf_has_empty_audit_path():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    log.append({"only": "entry"})
    log.commit()
    receipt = log.get_receipt(0)
    assert receipt.audit_path == []


# ---------------------------------------------------------------------------
# End-to-end: verify_receipt
# ---------------------------------------------------------------------------


def test_verify_receipt_single_entry():
    provider = SoftwareKeyProvider.generate()
    log = HardwareAuditLog(provider)
    log.append({"label": "ECHO_VERIFIED"})
    log.commit()
    receipt = log.get_receipt(0)
    assert HardwareAuditLog.verify_receipt(receipt, provider.public_key_hex())


def test_verify_receipt_all_entries_in_7_entry_log():
    provider = SoftwareKeyProvider.generate()
    log = HardwareAuditLog(provider)
    for i in range(7):
        log.append({"i": i, "data": "x" * i})
    log.commit()
    for i in range(7):
        receipt = log.get_receipt(i)
        assert HardwareAuditLog.verify_receipt(receipt, provider.public_key_hex()), (
            f"Verification failed for entry {i}"
        )


def test_verify_receipt_wrong_public_key_fails():
    provider = SoftwareKeyProvider.generate()
    other_provider = SoftwareKeyProvider.generate()
    log = HardwareAuditLog(provider)
    log.append({"a": 1})
    log.commit()
    receipt = log.get_receipt(0)
    assert not HardwareAuditLog.verify_receipt(receipt, other_provider.public_key_hex())


def test_verify_receipt_tampered_root_hash_fails():
    """Tampering the root_hash_hex invalidates the STH signature check."""
    provider = SoftwareKeyProvider.generate()
    log = HardwareAuditLog(provider)
    log.append({"a": 1})
    log.commit()
    receipt = log.get_receipt(0)

    tampered_sth = dataclasses.replace(receipt.sth, root_hash_hex="aa" * 32)
    tampered = dataclasses.replace(receipt, sth=tampered_sth)
    assert not HardwareAuditLog.verify_receipt(tampered, provider.public_key_hex())


def test_verify_receipt_tampered_sig_fails():
    """Replacing the STH signature with garbage fails verification."""
    provider = SoftwareKeyProvider.generate()
    log = HardwareAuditLog(provider)
    log.append({"a": 1})
    log.commit()
    receipt = log.get_receipt(0)

    tampered_sth = dataclasses.replace(receipt.sth, sig_hex="ff" * 64)
    tampered = dataclasses.replace(receipt, sth=tampered_sth)
    assert not HardwareAuditLog.verify_receipt(tampered, provider.public_key_hex())


def test_verify_receipt_tampered_leaf_hash_fails():
    """Tampering the leaf_hash_hex fails the Merkle proof check."""
    provider = SoftwareKeyProvider.generate()
    log = HardwareAuditLog(provider)
    log.append({"a": 1})
    log.append({"b": 2})
    log.commit()
    receipt = log.get_receipt(0)

    tampered = dataclasses.replace(receipt, leaf_hash_hex="bb" * 32)
    assert not HardwareAuditLog.verify_receipt(tampered, provider.public_key_hex())


def test_verify_receipt_tampered_audit_path_fails():
    """Flipping bytes in the audit path fails Merkle proof reconstruction."""
    provider = SoftwareKeyProvider.generate()
    log = HardwareAuditLog(provider)
    for i in range(4):
        log.append({"i": i})
    log.commit()
    receipt = log.get_receipt(1)

    bad_path = [
        bytes(b ^ 0xFF for b in bytes.fromhex(h)).hex()
        for h in receipt.audit_path
    ]
    tampered = dataclasses.replace(receipt, audit_path=bad_path)
    assert not HardwareAuditLog.verify_receipt(tampered, provider.public_key_hex())


# ---------------------------------------------------------------------------
# End-to-end: verify_content_in_receipt
# ---------------------------------------------------------------------------


def test_verify_content_in_receipt_valid():
    provider = SoftwareKeyProvider.generate()
    log = HardwareAuditLog(provider)
    content = {"label": "ECHO_VERIFIED", "bias_final": 0.05, "run_id": "test-001"}
    log.append(content)
    log.commit()
    receipt = log.get_receipt(0)

    assert HardwareAuditLog.verify_content_in_receipt(
        receipt, content, log.salt, provider.public_key_hex()
    )


def test_verify_content_in_receipt_wrong_content_fails():
    provider = SoftwareKeyProvider.generate()
    log = HardwareAuditLog(provider)
    log.append({"label": "ECHO_VERIFIED"})
    log.commit()
    receipt = log.get_receipt(0)

    wrong_content = {"label": "ECHO_BLOCKED"}
    assert not HardwareAuditLog.verify_content_in_receipt(
        receipt, wrong_content, log.salt, provider.public_key_hex()
    )


def test_verify_content_in_receipt_wrong_salt_fails():
    """Without the correct salt the content hash cannot be reproduced."""
    provider = SoftwareKeyProvider.generate()
    log = HardwareAuditLog(provider)
    content = {"val": 123}
    log.append(content)
    log.commit()
    receipt = log.get_receipt(0)

    wrong_salt = b"z" * 32
    assert not HardwareAuditLog.verify_content_in_receipt(
        receipt, content, wrong_salt, provider.public_key_hex()
    )


def test_verify_content_in_receipt_field_order_irrelevant():
    """Canonical JSON serialisation must make field order irrelevant."""
    provider = SoftwareKeyProvider.generate()
    log = HardwareAuditLog(provider)
    content = {"b": 2, "a": 1, "c": 3}
    log.append(content)
    log.commit()
    receipt = log.get_receipt(0)

    # Different insertion order, same keys/values
    content_reordered = {"c": 3, "a": 1, "b": 2}
    assert HardwareAuditLog.verify_content_in_receipt(
        receipt, content_reordered, log.salt, provider.public_key_hex()
    )


# ---------------------------------------------------------------------------
# to_dict serialisation
# ---------------------------------------------------------------------------


def test_entry_to_dict_contains_expected_keys():
    log = HardwareAuditLog(SoftwareKeyProvider.generate())
    entry = log.append({"a": 1})
    d = entry.to_dict()
    assert {"index", "timestamp_ms", "leaf_hash_hex", "device_sig_hex", "key_id", "schema_version"} <= d.keys()


def test_receipt_to_dict_is_json_serialisable():
    import json

    provider = SoftwareKeyProvider.generate()
    log = HardwareAuditLog(provider)
    log.append({"a": 1})
    log.commit()
    receipt = log.get_receipt(0)
    # Should not raise
    json.dumps(receipt.to_dict(), ensure_ascii=False)
