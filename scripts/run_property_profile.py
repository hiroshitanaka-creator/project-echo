#!/usr/bin/env python3
"""Run property-based tests with PR/nightly profiles.

Profile goals:
- pr: lightweight subset for fast feedback
- nightly: broader property suite for higher assurance
"""

from __future__ import annotations

import argparse
import subprocess
import sys

PR_TARGETS = [
    "tests/test_prop_sentinel_v2.py",
    "tests/test_prop_webhook_dispatch.py",
]

NIGHTLY_TARGETS = [
    "tests/test_prop_*.py",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run property-test profiles (pr/nightly).")
    parser.add_argument(
        "--profile",
        choices=("pr", "nightly"),
        default="pr",
        help="Execution profile (default: pr).",
    )
    args = parser.parse_args()

    targets = PR_TARGETS if args.profile == "pr" else NIGHTLY_TARGETS
    cmd = [sys.executable, "-m", "pytest", "-q", *targets]
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
