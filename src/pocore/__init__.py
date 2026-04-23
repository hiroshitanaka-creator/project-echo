"""Backwards-compatibility shim — use ``po_core`` for all new code.

``policy_v1`` has been migrated to ``po_core.policy_v1``.
This package re-exports from ``po_core`` so that any remaining legacy
callers continue to work, but new code should import directly from
``po_core``.
"""

from __future__ import annotations

from po_core import *  # noqa: F401,F403
from .policy_v1 import POLICY, override_policy  # noqa: F401

__all__ = ["POLICY", "override_policy"]
