#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quick Echo Report
- 入力: runs/*.json の最新 or 指定ファイル
- 出力: reports/latest.md（--out で変更可）
- 署名検証: ECHO_MARK_SECRET があれば VALID/INVALID を表示
- echo_mark モジュールが無くても「ラベルのみ」で動く
"""

from __future__ import annotations
import argparse
import glob
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# ---- optional import (なければラベルのみ運転) -------------------------------
def _try_import_echo_mark():
    try:
        from po_echo.echo_mark import make_echo_mark, verify_mark  # type: ignore
        return make_echo_mark, verify_mark
    except Exception:
        return None, None

MAKE_ECHO_MARK, VERIFY_ECHO_MARK = _try_import_echo_mark()


def _latest_run_json(path: Optional[str]) -> Path:
    if path:
        return Path(path)
    files = sorted(glob.glob("runs/*.json"))
    if not files:
        raise SystemExit("No runs/*.json found. Provide --in explicitly.")
    return Path(files[-1])


def _load_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _save_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def _boundary(run: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(run.get("responsibility_boundary"), dict):
        return run["responsibility_boundary"]
    if isinstance(run.get("audit"), dict) and isinstance(run["audit"].get("responsibility_boundary"), dict):
        return run["audit"]["responsibility_boundary"]
    return {}


def _bias_pair(run: Dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
    o = run.get("commercial_bias_original", {}) or run.get("audit", {}).get("commercial_bias_original", {})
    f = run.get("commercial_bias_final", {}) or run.get("audit", {}).get("commercial_bias_final", {})
    bo = o.get("overall_bias_score", None)
    bf = f.get("overall_bias_score", None)
    try:
        return (float(bo) if bo is not None else None, float(bf) if bf is not None else None)
    except Exception:
        return (None, None)


def _compute_mark(run: Dict[str, Any]) -> Dict[str, Any]:
    secret = os.getenv("ECHO_MARK_SECRET", "").strip()
    # 既存バッジを拾う（任意フィールド）
    for k in ("echo_mark", "badge", "echo_mark_v1"):
        if isinstance(run.get(k), dict) and run[k].get("schema_version") == "echo_mark_v1":
            badge = run[k]
            if secret and VERIFY_ECHO_MARK:
                ok = VERIFY_ECHO_MARK(
                    payload=badge["payload"],
                    payload_hash=badge["payload_hash"],
                    signature=badge["signature"],
                    secret=secret,
                )
                badge = dict(badge)
                badge["verification_status"] = "VALID" if ok else "INVALID"
            else:
                badge = dict(badge)
                badge["verification_status"] = "UNVERIFIED"
            return badge

    # 既存が無い → 生成 or ラベルだけ
    rb = _boundary(run)
    allowed = bool(rb.get("execution_allowed", False))
    confirm = bool(rb.get("requires_human_confirm", True))
    label = "ECHO_BLOCKED" if not allowed else ("ECHO_CHECK" if confirm else "ECHO_VERIFIED")

    if secret and MAKE_ECHO_MARK:
        badge = MAKE_ECHO_MARK(run if "responsibility_boundary" in run else {"audit": run}, secret=secret, run_id=run.get("run_id"))
        badge["verification_status"] = "GENERATED"
        return badge

    # ラベルのみ
    return {
        "schema_version": "echo_mark_v1",
        "label": label,
        "badge_text": "",
        "payload_hash": "",
        "signature": "",
        "verification_status": "UNVERIFIED",
        "short": {},
    }


def _short(x: Any, n: int = 12) -> str:
    s = str(x or "")
    return s if len(s) <= n else s[:n] + "…"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", help="runs JSON (default=latest)")
    ap.add_argument("--out", dest="out", default="reports/latest.md")
    ap.add_argument("--title", dest="title", default=None)
    args = ap.parse_args()

    run_path = _latest_run_json(args.inp)
    run = _load_json(run_path)

    rb = _boundary(run)
    bo, bf = _bias_pair(run)
    reasons = (rb.get("reasons") or []) if isinstance(rb, dict) else []
    mark = _compute_mark(run)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = args.title or f"Echo Report — {run.get('scenario', {}).get('text','(no title)')[:60]}"

    lines = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"_generated: {ts}_")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- **Execution allowed**: `{bool(rb.get('execution_allowed', False))}`")
    lines.append(f"- **Requires human confirm**: `{bool(rb.get('requires_human_confirm', True))}`")
    if bo is not None or bf is not None:
        delta = (bf - bo) if (bo is not None and bf is not None) else None
        lines.append(f"- **Bias**: {bo if bo is not None else 'NA'} → {bf if bf is not None else 'NA'}" + (f" (Δ {delta:+.2f})" if delta is not None else ""))
    if reasons:
        lines.append(f"- **Reasons**: {', '.join(reasons)}")
    lines.append("")

    lines.append("## Echo Mark")
    lines.append(f"- **Label**: `{mark.get('label','')}`")
    if mark.get("badge_text"):
        lines.append(f"- **Badge**: {mark.get('badge_text')}")
    lines.append(f"- **Verification**: `{mark.get('verification_status','UNVERIFIED')}`")
    if mark.get("payload_hash"):
        lines.append(f"- **payload_hash**: `{_short(mark.get('payload_hash'))}`")
    if mark.get("signature"):
        lines.append(f"- **signature**: `{_short(mark.get('signature'))}`")
    short = mark.get("short") or {}
    if ("bias_original" in short) or ("bias_final" in short):
        lines.append(f"- **Bias(short)**: {short.get('bias_original','NA')} → {short.get('bias_final','NA')} (Δ {short.get('bias_improvement','NA')})")
    if short.get("reasons"):
        lines.append(f"- **Reasons(short)**: {', '.join(short.get('reasons'))}")
    lines.append("")

    # 簡易明細（任意）：final_set があれば上位だけ載せる
    final_set = run.get("final_set") or run.get("audit", {}).get("final_set")
    if isinstance(final_set, list) and final_set:
        lines.append("## Final Set (top)")
        for r in final_set[:5]:
            title = r.get("title") or r.get("id") or "(item)"
            price = r.get("price", "NA")
            merchant = r.get("merchant", "NA")
            lines.append(f"- {title} — ¥{price} / {merchant}")
        lines.append("")

    out_path = Path(args.out)
    _save_text(out_path, "\n".join(lines))
    print(f"[report] wrote {out_path}")

if __name__ == "__main__":
    main()