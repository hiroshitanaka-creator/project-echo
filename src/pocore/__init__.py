"""Deprecated compatibility module for legacy ``pocore`` imports."""

from __future__ import annotations

import warnings

from po_core import *  # noqa: F401,F403

from .policy_v1 import POLICY, override_policy

warnings.warn(
    "`pocore` is deprecated. Use `po_core` instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["POLICY", "override_policy"]
