from __future__ import annotations

from pathlib import Path

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-assign CI gate markers from file patterns.

    Keeps CI gate meaning stable while avoiding workflow-level test file enumeration.
    """
    for item in items:
        p = Path(str(item.fspath))
        name = p.name

        if name in {"test_smoke.py", "test_examples_smoke.py"}:
            item.add_marker("smoke")
        if name == "test_invariants.py":
            item.add_marker("invariants")
        if name.startswith("test_prop_"):
            item.add_marker("prop_core")
        if name.startswith("test_device_") or name.startswith("test_voice_"):
            item.add_marker("kpi_quick")
        if "benchmarks" in p.parts:
            item.add_marker("heavy")
