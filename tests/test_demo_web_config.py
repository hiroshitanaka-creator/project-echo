"""Validate demo_web startup config fails closed without env secrets."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _pythonpath_with_repo_src(repo_root: Path) -> str:
    src = str(repo_root / "src")
    existing = os.environ.get("PYTHONPATH", "")
    return src if not existing else f"{src}{os.pathsep}{existing}"


def test_demo_web_import_fails_when_required_env_missing() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.pop("ECHO_MARK_SECRET", None)
    env.pop("ECHO_MARK_PRIVATE_KEY", None)
    env["PYTHONPATH"] = _pythonpath_with_repo_src(repo_root)

    proc = subprocess.run(
        [sys.executable, "-c", "import tools.demo_web"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode != 0
    assert "Missing required environment variable(s)" in proc.stderr
    assert "ECHO_MARK_SECRET" in proc.stderr
    assert "ECHO_MARK_PRIVATE_KEY" in proc.stderr


def test_demo_web_import_does_not_raise_missing_env_when_required_env_set() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["ECHO_MARK_SECRET"] = "a" * 32
    env["ECHO_MARK_PRIVATE_KEY"] = "b" * 64
    env["PYTHONPATH"] = _pythonpath_with_repo_src(repo_root)

    proc = subprocess.run(
        [sys.executable, "-c", "import tools.demo_web"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert "Missing required environment variable(s)" not in proc.stderr
