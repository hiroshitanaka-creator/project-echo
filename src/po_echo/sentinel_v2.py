"""Backward-compatible API surface for sentinel scanner + semantic wrapper.

Distinct concerns are now separated into dedicated modules:
- `po_echo.sentinel_scan`     : AST vendor/secret scanner
- `po_echo.sentinel_semantic` : semantic diversity helper
"""

from __future__ import annotations

from po_echo.sentinel_scan import (
    ALTERNATIVE_MAP,
    HARDCODED_SECRETS,
    VENDOR_RISK_MAP,
    Doberman,
    scan_directory,
)
from po_echo.sentinel_semantic import apply_semantic_diversity

__all__ = [
    "ALTERNATIVE_MAP",
    "HARDCODED_SECRETS",
    "VENDOR_RISK_MAP",
    "Doberman",
    "apply_semantic_diversity",
    "scan_directory",
]


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "."
    scan_directory(target)

