#!/usr/bin/env python3
"""
Generate Markdown report from latest run JSON.

Reads the most recent JSON from runs/ and generates reports/latest.md
with comparison to previous run if available.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

RUNS_DIR = Path("runs")
REPORTS_DIR = Path("reports")
OUT_MD = REPORTS_DIR / "latest.md"


def _try_import_echo_mark():
    try:
        from po_echo.echo_mark import make_echo_mark, verify_mark  # type: ignore

        return make_echo_mark, verify_mark
    except Exception:
        return None, None


MAKE_ECHO_MARK, VERIFY_ECHO_MARK = _try_import_echo_mark()


def _get_env_secret() -> str | None:
    s = os.getenv("ECHO_MARK_SECRET", "").strip()
    return s if s else None


def _extract_audit_obj(run: dict) -> dict | None:
    """
    Accepts either:
      - run itself (if it already matches audit schema)
      - run["audit"] (if nested)
    Minimal requirement: responsibility_boundary exists.
    """
    if isinstance(run.get("responsibility_boundary"), dict):
        return run
    if isinstance(run.get("audit"), dict) and isinstance(
        run["audit"].get("responsibility_boundary"), dict
    ):
        return run["audit"]
    return None


def _extract_existing_badge(run: dict) -> dict | None:
    """
    If you already saved badge inside run, support it:
      - run["echo_mark"]
      - run["badge"]
      - run["echo_mark_v1"]
    """
    for k in ("echo_mark", "badge", "echo_mark_v1"):
        if isinstance(run.get(k), dict) and run[k].get("schema_version") == "echo_mark_v1":
            return run[k]
    # nested case
    if isinstance(run.get("audit"), dict):
        for k in ("echo_mark", "badge", "echo_mark_v1"):
            v = run["audit"].get(k)
            if isinstance(v, dict) and v.get("schema_version") == "echo_mark_v1":
                return v
    return None


def _compute_or_verify_echo_mark(run: dict) -> dict | None:
    """
    Returns a dict with:
      - label, badge_text, payload_hash, signature, verification_status, short fields
    Does NOT mutate input.
    """
    audit = _extract_audit_obj(run)
    if audit is None:
        return None

    secret = _get_env_secret()
    existing = _extract_existing_badge(run)

    # If we cannot import mark module, still show label-only if possible
    if MAKE_ECHO_MARK is None or VERIFY_ECHO_MARK is None:
        rb = audit.get("responsibility_boundary", {})
        allowed = bool(rb.get("execution_allowed", False))
        confirm = bool(rb.get("requires_human_confirm", True))
        label = "ECHO_BLOCKED" if not allowed else ("ECHO_CHECK" if confirm else "ECHO_VERIFIED")
        return {
            "schema_version": "echo_mark_v1",
            "label": label,
            "badge_text": "",
            "payload_hash": "",
            "signature": "",
            "verification_status": "UNAVAILABLE",
            "short": {},
        }

    # secretなし → 表示だけ（UNVERIFIED）
    if not secret:
        # if existing exists, show it as UNVERIFIED
        if existing:
            return {
                "schema_version": "echo_mark_v1",
                "label": existing.get("label"),
                "badge_text": existing.get("badge_text", ""),
                "payload_hash": existing.get("payload_hash", ""),
                "signature": existing.get("signature", ""),
                "verification_status": "UNVERIFIED",
                "short": existing.get("short", {}),
            }
        # else compute label from boundary only
        rb = audit.get("responsibility_boundary", {})
        allowed = bool(rb.get("execution_allowed", False))
        confirm = bool(rb.get("requires_human_confirm", True))
        label = "ECHO_BLOCKED" if not allowed else ("ECHO_CHECK" if confirm else "ECHO_VERIFIED")
        return {
            "schema_version": "echo_mark_v1",
            "label": label,
            "badge_text": "",
            "payload_hash": "",
            "signature": "",
            "verification_status": "UNVERIFIED",
            "short": {},
        }

    # secretあり
    if existing:
        # Support both v1 (secret param) and v2 (key_store lookup)
        ok = VERIFY_ECHO_MARK(
            payload=existing["payload"],
            payload_hash=existing["payload_hash"],
            signature=existing["signature"],
            secret=secret,  # v1 compat
        )
        return {
            "schema_version": existing.get("schema_version", "echo_mark_v1"),
            "label": existing.get("label"),
            "badge_text": existing.get("badge_text", ""),
            "payload_hash": existing.get("payload_hash", ""),
            "signature": existing.get("signature", ""),
            "verification_status": "VALID" if ok else "INVALID",
            "short": existing.get("short", {}),
        }

    # no existing → generate (treated VALID by construction)
    # v2 is now default in make_echo_mark
    badge = MAKE_ECHO_MARK(audit, run_id=audit.get("run_id"))
    return {
        "schema_version": badge.get("schema_version", "echo_mark_v2"),
        "label": badge.get("label"),
        "badge_text": badge.get("badge_text", ""),
        "payload_hash": badge.get("payload_hash", ""),
        "signature": badge.get("signature", ""),
        "verification_status": "GENERATED",
        "short": badge.get("short", {}),
    }


def _short_hex(s: str, n: int = 12) -> str:
    if not s:
        return ""
    s = str(s)
    return s[:n] + "…" if len(s) > n else s


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

    # Echo Mark
    mark = _compute_or_verify_echo_mark(run)
    lines.append("### Echo Mark")
    if not mark:
        lines.append("_not available_")
        lines.append("")
    else:
        lines.append(f"- **Label**: `{mark.get('label', '')}`")
        if mark.get("badge_text"):
            lines.append(f"- **Badge**: {mark.get('badge_text')}")
        short = mark.get("short") or {}
        if ("bias_original" in short) or ("bias_final" in short):
            lines.append(
                f"- **Bias**: {short.get('bias_original', 'NA')} → {short.get('bias_final', 'NA')} "
                f"(Δ {short.get('bias_improvement', 'NA')})"
            )
        if short.get("reasons"):
            lines.append(f"- **Reasons**: {', '.join(short.get('reasons'))}")
        lines.append(f"- **Verification**: `{mark.get('verification_status', '')}`")
        lines.append(f"- **payload_hash**: `{_short_hex(mark.get('payload_hash', ''))}`")
        lines.append(f"- **signature**: `{_short_hex(mark.get('signature', ''))}`")
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
    parser = argparse.ArgumentParser(description="Generate Markdown report from latest run JSON")
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Also save timestamped report in reports/YYYYMMDD_HHMMSS_scenario.md",
    )
    args = parser.parse_args()

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

    report_content = "\n".join(lines)

    # Write latest.md
    OUT_MD.write_text(report_content, encoding="utf-8")
    print(f"[report] wrote {OUT_MD}")

    # Archive if requested
    if args.archive:
        scenario_name = safe_get(latest, ["scenario", "meta", "name"], "scenario")
        safe_name = str(scenario_name).replace(" ", "_").replace("/", "_")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = REPORTS_DIR / f"{ts}_{safe_name}.md"
        archive_path.write_text(report_content, encoding="utf-8")
        print(f"[report] archived {archive_path}")


if __name__ == "__main__":
    main()
