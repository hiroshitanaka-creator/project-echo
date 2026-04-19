"""Tests for Echo Mark registry audit helpers."""

from __future__ import annotations

import datetime as dt

from po_echo.echo_mark_registry import audit_public_key_registry


def test_audit_public_key_registry_detects_multiple_active_keys() -> None:
    registry = {
        "keys": [
            {"key_id": "k1", "public_key": "aa", "status": "active", "expires_at": None},
            {"key_id": "k2", "public_key": "bb", "status": "active", "expires_at": None},
        ]
    }
    report = audit_public_key_registry(registry)
    assert report["ok"] is False
    assert "multiple_active_keys" in report["findings"]
    assert report["summary"]["active_count"] == 2


def test_audit_public_key_registry_detects_expired_and_duplicate_key_ids() -> None:
    now = dt.datetime(2026, 4, 19, tzinfo=dt.timezone.utc)
    registry = {
        "keys": [
            {"key_id": "k1", "public_key": "aa", "status": "active", "expires_at": "2020-01-01T00:00:00Z"},
            {"key_id": "k1", "public_key": "bb", "status": "inactive", "expires_at": "not-a-date"},
        ]
    }
    report = audit_public_key_registry(registry, now=now)
    assert report["ok"] is False
    assert "duplicate_key_id_entries" in report["findings"]
    assert "expired_or_invalid_expiry_entries" in report["findings"]
    assert report["summary"]["expired_count"] == 2
