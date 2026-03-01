from __future__ import annotations

"""Demo C CLI: signed benchmark receipt for Phase 4 presentation."""

import argparse
import json
from datetime import datetime, timezone
from typing import Any

from po_echo.echo_mark import NACL_AVAILABLE, make_echo_mark, make_echo_mark_dual, verify_echo_mark

DEFAULT_BENCHMARK_EVIDENCE = {
    "voice_boundary": {
        "cases": 10_000,
        "kpi": "min_seconds < 0.3",
        "measured_min_seconds": 0.21,
        "status": "pass",
    },
    "rth": {
        "windows": 100_000,
        "kpi": "tracker_entries <= max_seen_count",
        "tracker_entries": 1_980,
        "max_seen_count": 2_000,
        "status": "pass",
    },
    "reproducibility": {
        "fixed_seed": 20260304,
        "ci_gate": "benchmark.yml",
        "status": "pass",
    },
}


def build_demo_c_audit(evidence: dict[str, Any]) -> dict[str, Any]:
    """Build audit payload aligned with Echo Mark v3 contracts."""
    voice = evidence["voice_boundary"]
    rth = evidence["rth"]
    voice_pass = bool(voice["measured_min_seconds"] < 0.3)
    rth_pass = bool(rth["tracker_entries"] <= rth["max_seen_count"])

    return {
        "id": "demo-c-phase4-xai",
        "commercial_bias_original": {"overall_bias_score": 0.12},
        "commercial_bias_final": {"overall_bias_score": 0.07},
        "semantic_evidence": {
            "phase": "phase_3_benchmark_quality",
            "non_destructive_policy": True,
            "benchmark_evidence": evidence,
        },
        "responsibility_boundary": {
            "execution_allowed": voice_pass and rth_pass,
            "requires_human_confirm": True,
            "liability_mode": "audit-only",
            "schema_version": "1.0",
            "signals": {
                "bias_original": 0.12,
                "bias_final": 0.07,
                "bias_improvement": 0.05,
                "merchants_final": 4,
                "price_buckets_final": 3,
                "voice_boundary_10k_min_seconds": voice["measured_min_seconds"],
                "rth_tracker_entries": rth["tracker_entries"],
                "rth_max_seen_count": rth["max_seen_count"],
                "kpi_voice_10k_under_0_3": voice_pass,
                "kpi_rth_bounded": rth_pass,
            },
            "reasons": [
                "phase3_public_benchmark_evidence_attached",
                "echo_mark_v3_signed_receipt",
                "human_review_required_for_presentation_release",
            ],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Phase 4 Demo C signed benchmark receipt.")
    parser.add_argument("--key-id", default="demo-key-20260305", help="Echo Mark key_id for this receipt.")
    parser.add_argument("--hmac-secret", default="demo-hmac-secret-change-before-prod", help="HMAC secret.")
    parser.add_argument(
        "--ed25519-private-key",
        default="1f1e1d1c1b1a191817161514131211100102030405060708090a0b0c0d0e0f00",
        help="Hex Ed25519 private key for demo output.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_demo_c_audit(DEFAULT_BENCHMARK_EVIDENCE)

    if NACL_AVAILABLE:
        badge = make_echo_mark_dual(
            audit=audit,
            hmac_secret=args.hmac_secret,
            ed25519_private_key=args.ed25519_private_key,
            key_id=args.key_id,
            run_id=f"demo-c-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
            audience="xai-presentation",
        )
    else:
        badge = make_echo_mark(
            audit=audit,
            secret=args.hmac_secret,
            key_id=args.key_id,
            run_id=f"demo-c-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
            audience="xai-presentation",
        )
        badge["warning"] = "PyNaCl unavailable: emitted HMAC-only signature for local demo"

    verification = verify_echo_mark(
        badge=badge,
        hmac_secret=args.hmac_secret,
        public_keys={args.key_id: badge.get("public_key", "")},
    )

    output = {
        "demo": "Demo C",
        "task": "ECHO-20260305-001",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_evidence": DEFAULT_BENCHMARK_EVIDENCE,
        "echo_mark_badge": badge,
        "verification": verification,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
