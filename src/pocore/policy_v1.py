"""Backwards-compatible policy_v1 wrapper.

Legacy imports from ``pocore.policy_v1`` are kept for compatibility,
but implementation is sourced from ``po_core.policy_v1``.
"""

from __future__ import annotations

from po_core.policy_v1 import POLICY, PolicyV1, get_policy, override_policy

__all__ = ["PolicyV1", "POLICY", "get_policy", "override_policy"]
