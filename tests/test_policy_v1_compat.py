from __future__ import annotations

import po_core.policy_v1 as new_policy
import pocore.policy_v1 as legacy_policy


def test_policy_value_and_identity_match() -> None:
    assert legacy_policy.POLICY == new_policy.POLICY
    assert legacy_policy.POLICY is new_policy.POLICY


def test_override_policy_from_po_core_is_visible_via_pocore() -> None:
    assert legacy_policy.get_policy() == new_policy.POLICY
    with new_policy.override_policy(unknown_block=9, time_pressure_days=7):
        assert new_policy.get_policy().unknown_block == 9
        assert legacy_policy.get_policy().unknown_block == 9
        assert legacy_policy.get_policy().time_pressure_days == 7
    assert legacy_policy.get_policy() == new_policy.POLICY


def test_override_policy_from_pocore_is_visible_via_po_core() -> None:
    assert new_policy.get_policy() == new_policy.POLICY
    with legacy_policy.override_policy(unknown_block=5):
        assert legacy_policy.get_policy().unknown_block == 5
        assert new_policy.get_policy().unknown_block == 5
        assert new_policy.get_policy().time_pressure_days == new_policy.POLICY.time_pressure_days
    assert new_policy.get_policy() == new_policy.POLICY
