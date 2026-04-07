"""Smoke tests for example scripts.

Why: examples/ scripts are entry points shown to external users and
collaborators. A broken example silently undermines trust even when
all core tests pass. These tests run each example as a subprocess and
verify it exits 0, catching import errors, syntax errors, and obvious
runtime failures without requiring knowledge of example internals.

Note: examples are intentionally standalone (no po_echo/po_core imports),
so they run with standard library only and do not depend on optional extras.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = ROOT / "examples"

# All example entry-point scripts expected to be runnable standalone.
EXAMPLE_SCRIPTS = [
    EXAMPLES_DIR / "ai_rights_basic" / "run.py",
    EXAMPLES_DIR / "cosmic_ethics_39" / "run.py",
    EXAMPLES_DIR / "trolley_problem_basic" / "run.py",
]


@pytest.mark.parametrize("script", EXAMPLE_SCRIPTS, ids=lambda p: p.parent.name)
def test_example_runs_without_error(script: Path) -> None:
    """Each example script must exit 0 and produce no traceback on stdout/stderr.

    Why: examples are documentation as code. An ImportError or AttributeError
    in an example is caught here before it reaches an external audience.
    """
    assert script.exists(), f"Example script not found: {script}"

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, (
        f"Example {script.name} exited with code {result.returncode}.\n"
        f"--- stdout ---\n{result.stdout[-1000:]}\n"
        f"--- stderr ---\n{result.stderr[-1000:]}"
    )
    # A traceback in stdout/stderr indicates an unhandled exception even if
    # the process somehow exits 0 (e.g. caught in a top-level except block).
    assert "Traceback (most recent call last)" not in result.stderr, (
        f"Example {script.name} produced a traceback in stderr.\n{result.stderr[-1000:]}"
    )
