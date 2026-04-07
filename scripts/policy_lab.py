#!/usr/bin/env python3
"""Policy Lab v1: threshold perturbation report generator."""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from po_core.policy_v1 import POLICY, get_policy, override_policy


@dataclass
class CaseFeature:
    unknowns_count: int | None
    stakeholders_count: int | None
    days_to_deadline: int | None


def _load_yaml(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(raw)
        return data if isinstance(data, dict) else {}
    except ModuleNotFoundError:
        # Fallback: JSON is valid YAML subset; supports JSON-formatted .yaml files.
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}


def _list_scenarios(scenarios_dir: Path) -> list[Path]:
    files = sorted(scenarios_dir.glob("*.yaml"))
    if not files:
        return []
    preferred = [f for f in files if f.with_name(f"{f.stem}_expected.json").exists()]
    return preferred or files


def _extract_features(case: dict[str, Any]) -> CaseFeature:
    return CaseFeature(
        unknowns_count=case.get("unknowns_count") or case.get("features", {}).get("unknowns_count"),
        stakeholders_count=case.get("stakeholders_count")
        or case.get("features", {}).get("stakeholders_count"),
        days_to_deadline=case.get("days_to_deadline")
        or case.get("features", {}).get("days_to_deadline"),
    )


def _simulate_recommendation(case: dict[str, Any], now: str, seed: int) -> dict[str, Any]:
    feature = _extract_features(case)
    policy = get_policy()
    unknowns = feature.unknowns_count or 0
    deadline = feature.days_to_deadline
    rng = random.Random(f"{case.get('case_id', '')}:{now}:{seed}")

    rules_fired: list[str] = []
    status = "allow"
    arbitration_code = "ARB_PASS"
    confidence = round(0.65 + rng.random() * 0.25, 4)

    if unknowns >= policy.unknown_block:
        status = "hold"
        arbitration_code = "ARB_UNKNOWN_BLOCK"
        rules_fired.append("RULE_UNKNOWN_BLOCK")
        confidence = round(0.35 + rng.random() * 0.2, 4)
    elif deadline is not None and deadline <= policy.time_pressure_days:
        status = "escalate"
        arbitration_code = "ARB_TIME_PRESSURE"
        rules_fired.append("RULE_TIME_PRESSURE")
        confidence = round(0.45 + rng.random() * 0.2, 4)

    options = case.get("options") or []
    option_id = options[0].get("id") if options and isinstance(options[0], dict) else None

    return {
        "arbitration_code": arbitration_code,
        "recommendation": {
            "status": status,
            "confidence": confidence,
            "recommended_option_id": option_id,
        },
        "ethics": {"rules_fired": rules_fired},
    }


def _build_traceability_index(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    data = _load_yaml(path)
    index: dict[str, list[str]] = {}
    for row in data.get("traceability", []):
        req = row.get("requirement_id")
        for ref in row.get("code_refs", []):
            if req and ref:
                index.setdefault(str(ref), []).append(str(req))
    return index


def _reqs_for_codes(index: dict[str, list[str]], codes: list[str]) -> list[str]:
    out: set[str] = set()
    for code in codes:
        out.update(index.get(code, []))
    return sorted(out)


def run_case(case_path: Path, now: str, seed: int) -> dict[str, Any]:
    data = _load_yaml(case_path)
    case_id = str(data.get("case_id") or case_path.stem)
    features = _extract_features(data)
    result = _simulate_recommendation(data, now=now, seed=seed)
    return {
        "case_stem": case_path.stem,
        "case_id": case_id,
        "title": data.get("title", case_path.stem),
        "features": asdict(features),
        "arbitration_code": result["arbitration_code"],
        "recommendation": result["recommendation"],
        "ethics": result["ethics"],
        "policy_snapshot": {
            "UNKNOWN_BLOCK": get_policy().unknown_block,
            "TIME_PRESSURE_DAYS": get_policy().time_pressure_days,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unknown-block", type=int, default=POLICY.unknown_block)
    ap.add_argument("--time-pressure-days", type=int, default=POLICY.time_pressure_days)
    ap.add_argument("--now", default="2026-01-01T00:00:00Z")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--scenarios-dir", default="scenarios/")
    ap.add_argument("--output-dir", default="reports/policy_lab/")
    ap.add_argument("--compare-baseline", action="store_true")
    args = ap.parse_args()

    scenarios_dir = Path(args.scenarios_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    trace_index = _build_traceability_index(Path("docs/traceability/traceability_v1.yaml"))
    scenario_paths = _list_scenarios(scenarios_dir)

    baseline_map: dict[str, dict[str, Any]] = {}
    if args.compare_baseline:
        with override_policy(
            unknown_block=POLICY.unknown_block,
            time_pressure_days=POLICY.time_pressure_days,
        ):
            for sp in scenario_paths:
                item = run_case(sp, now=args.now, seed=args.seed)
                baseline_map[item["case_id"]] = item

    cases: list[dict[str, Any]] = []
    with override_policy(
        unknown_block=args.unknown_block,
        time_pressure_days=args.time_pressure_days,
    ):
        for sp in scenario_paths:
            item = run_case(sp, now=args.now, seed=args.seed)
            codes = [item["arbitration_code"], *item["ethics"].get("rules_fired", [])]
            item["related_requirements"] = _reqs_for_codes(trace_index, codes)

            if args.compare_baseline:
                base = baseline_map.get(item["case_id"])
                changed_codes: list[str] = []
                if base:
                    if base["arbitration_code"] != item["arbitration_code"]:
                        changed_codes += [base["arbitration_code"], item["arbitration_code"]]
                    if base["ethics"].get("rules_fired", []) != item["ethics"].get("rules_fired", []):
                        changed_codes += base["ethics"].get("rules_fired", []) + item["ethics"].get(
                            "rules_fired", []
                        )
                item["baseline_diff"] = {
                    "arbitration_code": [
                        base["arbitration_code"] if base else None,
                        item["arbitration_code"],
                    ],
                    "recommendation": {
                        "status": [
                            base["recommendation"]["status"] if base else None,
                            item["recommendation"]["status"],
                        ],
                        "confidence": [
                            base["recommendation"]["confidence"] if base else None,
                            item["recommendation"]["confidence"],
                        ],
                        "recommended_option_id": [
                            base["recommendation"]["recommended_option_id"] if base else None,
                            item["recommendation"]["recommended_option_id"],
                        ],
                    },
                    "rules_fired": [
                        base["ethics"].get("rules_fired", []) if base else [],
                        item["ethics"].get("rules_fired", []),
                    ],
                    "impacted_requirements": _reqs_for_codes(trace_index, list(set(changed_codes))),
                }
            cases.append(item)

    changed_cases = [
        c
        for c in cases
        if c.get("baseline_diff")
        and (
            c["baseline_diff"]["arbitration_code"][0] != c["baseline_diff"]["arbitration_code"][1]
            or c["baseline_diff"]["recommendation"]["status"][0]
            != c["baseline_diff"]["recommendation"]["status"][1]
            or c["baseline_diff"]["recommendation"]["recommended_option_id"][0]
            != c["baseline_diff"]["recommendation"]["recommended_option_id"][1]
            or c["baseline_diff"]["rules_fired"][0] != c["baseline_diff"]["rules_fired"][1]
        )
    ]

    req_counter = Counter(
        req
        for c in changed_cases
        for req in c.get("baseline_diff", {}).get("impacted_requirements", [])
    )

    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    tag = f"{stamp}_ub{args.unknown_block}_tp{args.time_pressure_days}"

    payload = {
        "meta": {
            "generated_at_utc": stamp,
            "policy_variant": {
                "UNKNOWN_BLOCK": args.unknown_block,
                "TIME_PRESSURE_DAYS": args.time_pressure_days,
            },
            "compare_baseline": args.compare_baseline,
            "scenario_selection": "prefer *_expected.json pair when present; otherwise all *.yaml",
            "scenarios_count": len(cases),
            "changed_cases_count": len(changed_cases),
        },
        "cases": cases,
        "impacted_requirements_ranking": req_counter.most_common(),
    }

    json_path = output_dir / f"{tag}.json"
    md_path = output_dir / f"{tag}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Policy Lab v1 Report",
        "",
        f"- Scenarios changed: **{len(changed_cases)} / {len(cases)}**",
        f"- Variant policy: UNKNOWN_BLOCK={args.unknown_block}, TIME_PRESSURE_DAYS={args.time_pressure_days}",
        "",
        "## Changed cases",
    ]
    if changed_cases:
        for c in changed_cases:
            b = c["baseline_diff"]
            lines.append(
                f"- {c['case_id']}: {b['arbitration_code'][0]} -> {b['arbitration_code'][1]}, "
                f"status {b['recommendation']['status'][0]} -> {b['recommendation']['status'][1]}"
            )
    else:
        lines.append("- (no changes)")

    lines += ["", "## impacted_requirements frequency ranking"]
    if req_counter:
        lines += [f"- {req}: {count}" for req, count in req_counter.most_common()]
    else:
        lines.append("- (none)")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Generated: {json_path}")
    print(f"Generated: {md_path}")


if __name__ == "__main__":
    main()
