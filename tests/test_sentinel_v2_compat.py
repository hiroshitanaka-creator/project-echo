"""Compatibility tests for sentinel_v2 public API after module split."""

from __future__ import annotations

from po_echo import sentinel_v2


def test_sentinel_v2_exports_expected_symbols() -> None:
    """Backward-compatible symbols should remain available from sentinel_v2."""
    for name in (
        "Doberman",
        "scan_directory",
        "apply_semantic_diversity",
        "VENDOR_RISK_MAP",
        "ALTERNATIVE_MAP",
        "HARDCODED_SECRETS",
    ):
        assert hasattr(sentinel_v2, name), f"missing compatibility export: {name}"
