#!/usr/bin/env python3
"""
Generate Markdown report from latest run JSON.

Reads the most recent JSON from runs/ and generates reports/latest.md
with comparison to previous run if available.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RUNS_DIR = Path("runs")
REPORTS_DIR = Path("reports")
OUT_MD = REPORTS_DIR / "latest.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_latest_two_runs(runs_dir: Path) -> tuple[Path | None, Path | None]:
    files = sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    latest = files[0] if len(files) >= 1 else None
    prev = files[1] if len(files) >= 2 else None
    return latest, prev


def topk_items(d: dict[str, float], k: int = 10) -> list[tuple[str, float]]:
    return sorted(d.items(), key=lambda x: x[1], reverse=True)[:k]


def md_table(rows: list[tuple[str, str, str]], header: tuple[str, str, str]) -> str:
    # 3列固定の簡易テーブル
    out = []
    out.append(f"| {header[0]} | {header[1]} | {header[2]} |")
    out.append("|---|---:|---:|")
    for a, b, c in rows:
        out.append(f"| {a} | {b} | {c} |")
    return "\n".join(out)


def fmt_f(x: float, nd: int = 2) -> str:
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return "NA"


def safe_get(d: dict[str, Any], keys: list[str], default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def render_run_section(run: dict[str, Any], title: str) -> str:
    scenario_name = safe_get(run, ["scenario", "meta", "name"], "(scenario)")
    adjusted_score = safe_get(run, ["scores", "adjusted_score"], None)
    overall_score = safe_get(run, ["scores", "overall_score"], None)
    up = safe_get(run, ["scores", "uncertainty_penalty"], None)
    ip = safe_get(run, ["scores", "irreversibility_penalty"], None)

    active_count = safe_get(run, ["philosophers", "active_count"], 0)
    blocked = safe_get(run, ["blocked_options"], []) or []
    tension = safe_get(run, ["tension_topk"], []) or []
    adjusted_scores = safe_get(run, ["scores", "adjusted_scores"], {}) or {}

    top_dims = topk_items({k: float(v) for k, v in adjusted_scores.items()}, k=10)

    lines = []
    lines.append(f"## {title}")
    lines.append("")
    lines.append(f"**Scenario**: {scenario_name}")
    lines.append("")
    lines.append(
        f"- Adjusted score: **{fmt_f(adjusted_score)}** (overall={fmt_f(overall_score)}, "
        f"uncertainty={fmt_f(up)}, irreversibility={fmt_f(ip)})"
    )
    lines.append(f"- Active philosophers: **{active_count}**")
    lines.append("")

    # Top dimensions
    lines.append("### Top dimensions (adjusted)")
    rows3 = [(k, fmt_f(v), "") for k, v in top_dims]
    lines.append(md_table(rows3, ("dimension", "score", "")))
    lines.append("")

    # Tension
    lines.append("### Tension topk")
    if tension:
        rows3 = []
        for t in tension[:10]:
            rows3.append((str(t.get("dimension")), fmt_f(t.get("tension_score", 0.0), 3), ""))
        lines.append(md_table(rows3, ("dimension", "tension", "")))
    else:
        lines.append("_none_")
    lines.append("")

    # Blocked
    lines.append("### Blocked options")
    if not blocked:
        lines.append("_none_")
    else:
        for b in blocked:
            lines.append(f"- **{b.get('option', '(option)')}**")
            lines.append(f"  - reason: {b.get('reason', '')}")
            lines.append(f"  - blockers: {b.get('blocking_dimensions', [])}")
    lines.append("")
    return "\n".join(lines)


def render_diff(latest: dict[str, Any], prev: dict[str, Any]) -> str:
    # スコア差分
    a1 = safe_get(latest, ["scores", "adjusted_score"], 0.0) or 0.0
    a0 = safe_get(prev, ["scores", "adjusted_score"], 0.0) or 0.0
    delta = float(a1) - float(a0)

    # top dims 差分（最新top10のうち、前回との差）
    d1 = safe_get(latest, ["scores", "adjusted_scores"], {}) or {}
    d0 = safe_get(prev, ["scores", "adjusted_scores"], {}) or {}

    top1 = topk_items({k: float(v) for k, v in d1.items()}, k=10)

    rows = []
    for k, v1 in top1:
        v0 = float(d0.get(k, 0.0))
        rows.append((k, fmt_f(v1), fmt_f(v1 - v0)))

    blocked1 = safe_get(latest, ["blocked_options"], []) or []
    blocked0 = safe_get(prev, ["blocked_options"], []) or []
    b1 = [b.get("option", "") for b in blocked1]
    b0 = [b.get("option", "") for b in blocked0]

    lines = []
    lines.append("## Diff vs previous run")
    lines.append("")
    lines.append(
        f"- Adjusted score delta: **{fmt_f(delta, 3)}** (latest={fmt_f(a1)}, prev={fmt_f(a0)})"
    )
    lines.append("")
    lines.append("### Top dimensions delta (latest top10)")
    lines.append(md_table(rows, ("dimension", "latest", "Δ")))
    lines.append("")
    lines.append("### Blocked options delta")
    lines.append(f"- latest: {b1 if b1 else 'none'}")
    lines.append(f"- prev: {b0 if b0 else 'none'}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    latest_path, prev_path = find_latest_two_runs(RUNS_DIR)
    if latest_path is None:
        OUT_MD.write_text("# latest report\n\nNo runs found in `runs/`.\n", encoding="utf-8")
        print(f"[report] no runs found. wrote {OUT_MD}")
        return

    latest = load_json(latest_path)
    prev = load_json(prev_path) if prev_path else None

    lines = []
    lines.append("# Po_core Cosmic Ethics 39 — Latest Report")
    lines.append("")
    lines.append(f"- latest file: `{latest_path}`")
    if prev_path:
        lines.append(f"- previous file: `{prev_path}`")
    lines.append("")

    lines.append(render_run_section(latest, "Latest run"))

    if prev:
        lines.append(render_diff(latest, prev))
        lines.append(render_run_section(prev, "Previous run"))

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report] wrote {OUT_MD}")


if __name__ == "__main__":
    main()
