"""Tests for echo_mark_registry operational summary helpers."""

from __future__ import annotations

import json

from po_echo.echo_mark_registry import summarize_public_key_registry


def test_summarize_public_key_registry_reports_warning_for_revoked_active_key(tmp_path) -> None:
    keys_dir = tmp_path / ".keys"
    keys_dir.mkdir()
    registry_path = keys_dir / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "keys": [
                    {"key_id": "k1", "public_key": "aa", "status": "revoked"},
                    {"key_id": "k2", "public_key": "bb", "status": "active"},
                ]
            }
        ),
        encoding="utf-8",
    )

    summary = summarize_public_key_registry(registry_path, active_key_id="k1")
    assert summary["active_key_status"] == "revoked"
    assert "active_key_is_revoked" in summary["warnings"]
    assert summary["counts"]["active"] == 1
    assert summary["counts"]["revoked"] == 1
