#!/usr/bin/env python3
from __future__ import annotations

"""Run lightweight KPI checks and emit markdown for CI/PR visibility."""

import argparse
import json
import logging
import sys
import timeit
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from po_echo.ci_kpi import (
    build_ci_kpi_markdown,
    evaluate_rth_tracker_entries,
    evaluate_voice_10k,
)
from po_echo.rth import CollisionTrackerConfig, RollingTranscriptHash
from po_echo.voice_boundary import classify_risk


logging.getLogger("po_echo.rth").setLevel(logging.ERROR)


def _measure_voice_case_runtime(case_count: int = 10_000) -> float:
    sample_intents = ["search", "booking", "payment", "summary", "itinerary"]

    def _run() -> None:
        for idx in range(case_count):
            intent = sample_intents[idx % len(sample_intents)]
            classify_risk(intent, {"amount": idx % 20_000})

    return min(timeit.Timer(_run).repeat(repeat=3, number=1))


def _measure_rth_tracker_entries(window_count: int = 20_000) -> int:
    rth = RollingTranscriptHash(
        collision_tracker_config=CollisionTrackerConfig(max_seen_count=2_000, ttl_ms=120_000)
    )
    for idx in range(window_count):
        rth.update_text(f"booking window {idx % 1500} amount {idx % 50_000}")
    seen = rth.state.seen_chain_hash_to_feat_fp or {}
    return len(seen)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CI quick KPI checks")
    parser.add_argument("--json-out", type=Path, help="Optional JSON output path")
    parser.add_argument("--md-out", type=Path, help="Optional markdown output path")
    args = parser.parse_args()

    voice_min_s = _measure_voice_case_runtime()
    rth_entries = _measure_rth_tracker_entries()

    checks = [evaluate_voice_10k(voice_min_s), evaluate_rth_tracker_entries(rth_entries)]
    markdown = build_ci_kpi_markdown(checks)

    payload = {
        "checks": [check.__dict__ for check in checks],
        "all_passed": all(check.passed for check in checks),
    }

    if args.json_out:
        args.json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.md_out:
        args.md_out.write_text(markdown + "\n", encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("\n" + markdown)
    return 0 if payload["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
