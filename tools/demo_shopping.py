#!/usr/bin/env python3
"""
Demo B: Shopping Bias Defense

Demonstrates Echo's bias detection, diversity enforcement, and execution gate
on shopping recommendation scenarios.
"""

import json
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from po_core.diversity import Rec, diversify_with_mmr
from po_echo.echo_mark import (
    load_ed25519_keypair,
    load_ed25519_private_key_from_env,
    make_echo_mark,
    make_echo_mark_dual,
)
import os

try:
    from nacl.signing import SigningKey

    ED25519_AVAILABLE = True
except ImportError:
    ED25519_AVAILABLE = False


def load_recommendations(input_file: Path) -> tuple[list[Rec], dict]:
    """Load recommendations from JSON input file."""
    with open(input_file) as f:
        data = json.load(f)

    recs = []
    for r in data["recommendations"]:
        rec = Rec(
            id=r["id"],
            title=r["title"],
            merchant=r["merchant"],
            category=r["category"],
            price=float(r["price"]),
            tags=tuple(r["tags"]),
            utility=r.get("utility", 1.0),  # Default to 1.0 if not specified
            ethics=r.get("ethics", 0.5),    # Default to neutral
            bias_risk=float(r["bias_risk"]),
        )
        recs.append(rec)

    user_policy = data.get("user_policy", {})
    return recs, user_policy


def run_demo_case(case_name: str, input_file: Path, output_dir: Path):
    """Run a single demo case."""
    print(f"\n{'='*60}")
    print(f"Demo Case: {case_name}")
    print(f"{'='*60}")

    # Load input
    recs, user_policy = load_recommendations(input_file)
    print(f"\n📥 Input: {len(recs)} recommendations")
    print(f"   Merchants: {len(set(r.merchant for r in recs))}")
    print(f"   Avg bias_risk: {sum(r.bias_risk for r in recs) / len(recs):.2f}")

    # Run diversity enforcement
    diversify_params = user_policy.get("diversify", {})
    k = diversify_params.get("k", 5)
    lam = diversify_params.get("lam", 0.65)
    min_merchants = diversify_params.get("min_merchants", 2)
    min_price_buckets = diversify_params.get("min_price_buckets", 2)

    result = diversify_with_mmr(
        original=recs,
        counterfactuals=[],  # No counterfactuals in this demo
        k=k,
        lam=lam,
        min_merchants=min_merchants,
        min_price_buckets=min_price_buckets,
    )

    # Print results
    bias_orig = result["commercial_bias_original"]["overall_bias_score"]
    bias_final = result["commercial_bias_final"]["overall_bias_score"]
    boundary = result["responsibility_boundary"]

    print(f"\n📊 Commercial Bias:")
    print(f"   Original: {bias_orig:.2f}")
    print(f"   Final:    {bias_final:.2f}")
    print(f"   Change:   {bias_final - bias_orig:+.2f}")

    print(f"\n🎯 Diversity:")
    print(f"   Merchants: {result['diversity_report_original']['merchants']} → {result['diversity_report_final']['merchants']}")
    print(f"   Price buckets: {result['diversity_report_original']['price_buckets']} → {result['diversity_report_final']['price_buckets']}")

    print(f"\n🛡️ Execution Gate:")
    print(f"   Execution allowed: {boundary['execution_allowed']}")
    print(f"   Requires human confirm: {boundary['requires_human_confirm']}")
    print(f"   AI recommends: {boundary['ai_recommends']}")
    print(f"   Reasons: {', '.join(boundary['reasons'])}")

    # Determine label
    if not boundary['execution_allowed']:
        label = "ECHO_BLOCKED"
    elif not boundary['requires_human_confirm']:
        label = "ECHO_VERIFIED"
    else:
        label = "ECHO_CHECK"

    print(f"\n✅ Label: {label}")

    # Save audit result
    audit_file = output_dir / f"{case_name}.audit.json"
    with open(audit_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n💾 Saved audit: {audit_file}")

    # Create Echo Mark badge
    # Try dual signature (HMAC + Ed25519) if Ed25519 available
    secret = os.getenv("ECHO_MARK_SECRET", "demo-secret-key-16chars")
    private_key = load_ed25519_private_key_from_env()

    if ED25519_AVAILABLE and private_key:
        # Dual signature mode
        badge = make_echo_mark_dual(
            audit=result,
            hmac_secret=secret,
            ed25519_private_key=private_key,
            key_id="v1",
        )
        print(f"   Badge mode: Dual signature (HMAC + Ed25519)")
    else:
        # HMAC-only mode (backward compatible)
        badge = make_echo_mark(
            audit=result,
            secret=secret,
            key_id="v1",
        )
        print(f"   Badge mode: HMAC-only (legacy)")

    badge_file = output_dir / f"{case_name}.badge.json"
    with open(badge_file, 'w') as f:
        json.dump(badge, f, indent=2)
    print(f"💾 Saved badge:  {badge_file}")

    print(f"\n{'='*60}\n")


def main():
    """Run all demo cases."""
    project_root = Path(__file__).resolve().parents[1]
    input_dir = project_root / "examples" / "demo_inputs" / "shopping"
    output_dir = project_root / "runs"

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check for secret
    secret = os.getenv("ECHO_MARK_SECRET")
    if not secret:
        print("⚠️  Warning: ECHO_MARK_SECRET not set. Using demo key.")
        print("   For production, set: export ECHO_MARK_SECRET='your-secret'\n")

    # Run demo cases
    cases = [
        ("high_bias_affiliate", "01_high_bias_affiliate.json"),
        ("clean_multi_merchant", "02_clean_multi_merchant.json"),
        ("mixed_contaminated", "03_mixed_contaminated.json"),
    ]

    for case_name, input_file in cases:
        input_path = input_dir / input_file
        if not input_path.exists():
            print(f"❌ Input file not found: {input_path}")
            continue

        try:
            run_demo_case(case_name, input_path, output_dir)
        except Exception as e:
            print(f"❌ Error in {case_name}: {e}")
            import traceback
            traceback.print_exc()

    print("\n🎉 Demo completed!")
    print(f"📁 Results saved to: {output_dir}")
    print("\nNext steps:")
    print("  1. Review audit results: cat runs/*.audit.json")
    print("  2. Verify badges: python tools/verify_badge.py runs/*.badge.json")
    print("  3. Read demo guide: cat docs/DEMO_SHOPPING.md")


if __name__ == "__main__":
    main()
