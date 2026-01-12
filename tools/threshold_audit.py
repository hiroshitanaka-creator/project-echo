#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


RUNS_DIR = Path("runs")


def load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get(d: Dict[str, Any], path: List[str], default=None):
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def percentile(xs: List[float], p: float) -> float:
    if not xs:
        return float("nan")
    xs_sorted = sorted(xs)
    idx = int(round((len(xs_sorted) - 1) * p))
    return xs_sorted[max(0, min(idx, len(xs_sorted) - 1))]


def main() -> None:
    files = sorted(RUNS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        print("[audit] no runs found in runs/")
        return

    rows: List[Tuple[str, float, float, float, float, bool, bool, int]] = []

    for f in files:
        r = load(f)

        adj = float(get(r, ["scores", "adjusted_score"], 0.0) or 0.0)
        unc = float(get(r, ["responsibility_boundary", "signals", "uncertainty"], 0.0) or 0.0)
        rev = float(get(r, ["responsibility_boundary", "signals", "reversibility"], 1.0) or 1.0)
        mt = float(get(r, ["responsibility_boundary", "signals", "max_tension"], 0.0) or 0.0)

        allowed = bool(get(r, ["responsibility_boundary", "execution_allowed"], False))
        confirm = bool(get(r, ["responsibility_boundary", "requires_human_confirm"], True))
        blocked_count = int(get(r, ["responsibility_boundary", "signals", "blocked_count"], 0) or 0)

        rows.append((f.name, adj, unc, rev, mt, allowed, confirm, blocked_count))

    adjs = [x[1] for x in rows]
    uncs = [x[2] for x in rows]
    revs = [x[3] for x in rows]
    mts = [x[4] for x in rows]

    allowed_rate = sum(1 for x in rows if x[5]) / len(rows)
    confirm_rate = sum(1 for x in rows if x[6]) / len(rows)

    print("=" * 80)
    print(f"[threshold audit] runs={len(rows)}")
    print("=" * 80)

    def summarize(name: str, xs: List[float]):
        print(
            f"{name:14s}  "
            f"min={min(xs):.2f}  p25={percentile(xs,0.25):.2f}  "
            f"p50={percentile(xs,0.50):.2f}  p75={percentile(xs,0.75):.2f}  "
            f"max={max(xs):.2f}"
        )

    summarize("adjusted_score", adjs)
    summarize("uncertainty", uncs)
    summarize("reversibility", revs)
    summarize("max_tension", mts)

    print()
    print(f"execution_allowed_rate      = {allowed_rate:.2%}")
    print(f"requires_human_confirm_rate = {confirm_rate:.2%}")

    print("\nTop 10 lowest adjusted_score:")
    for name, adj, unc, rev, mt, allowed, confirm, bc in sorted(rows, key=lambda x: x[1])[:10]:
        print(f"- {name:40s} adj={adj:.2f} unc={unc:.2f} rev={rev:.2f} tens={mt:.3f} allowed={allowed} confirm={confirm} blocked={bc}")

    print("\nTop 10 highest max_tension:")
    for name, adj, unc, rev, mt, allowed, confirm, bc in sorted(rows, key=lambda x: x[4], reverse=True)[:10]:
        print(f"- {name:40s} tens={mt:.3f} adj={adj:.2f} unc={unc:.2f} rev={rev:.2f} allowed={allowed} confirm={confirm} blocked={bc}")

    print("\nDone.")


if __name__ == "__main__":
    main()
