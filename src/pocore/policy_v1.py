"""Policy v1 thresholds and safe override context manager."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Iterator


@dataclass(frozen=True)
class PolicyV1:
    """Static thresholds for policy simulation."""

    unknown_block: int = 2
    time_pressure_days: int = 3


POLICY = PolicyV1()
_ACTIVE_POLICY = POLICY


def get_policy() -> PolicyV1:
    """Return currently active policy thresholds."""
    return _ACTIVE_POLICY


@contextmanager
def override_policy(
    *, unknown_block: int | None = None, time_pressure_days: int | None = None
) -> Iterator[PolicyV1]:
    """Temporarily override policy thresholds and always restore defaults."""
    global _ACTIVE_POLICY
    previous = _ACTIVE_POLICY
    updated = replace(
        previous,
        unknown_block=unknown_block if unknown_block is not None else previous.unknown_block,
        time_pressure_days=(
            time_pressure_days
            if time_pressure_days is not None
            else previous.time_pressure_days
        ),
    )
    _ACTIVE_POLICY = updated
    try:
        yield updated
    finally:
        _ACTIVE_POLICY = previous
