"""
Po-Cosmic CLI

Command-line interface for Cosmic Ethics 39 evaluator.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to path if running directly
src_path = Path(__file__).resolve().parents[2] / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from po_core.cosmic_ethics_39.evaluator import CosmicEthics39Evaluator
from po_core.cosmic_ethics_39.scenarios import get_scenario
from po_core.diversity import Rec, diversify_with_mmr
from po_echo.echo_mark import get_secret_from_env, make_echo_mark, verify_mark


def prompt_yes_no(msg: str) -> bool:
    """Prompt user for yes/no confirmation."""
    while True:
        ans = input(f"{msg} [y/n]: ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("Please type 'y' or 'n'.")


def transition(exec_obj: dict, to: str, reason: str, meta: dict | None = None) -> None:
    """
    Transition execution state.

    Records state change in history with timestamp. This is the core
    of operator responsibility - every state change is evidence.
    """
    meta = meta or {}
    frm = exec_obj["state"]
    exec_obj["state"] = to
    exec_obj.setdefault("history", []).append(
        {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "frm": frm,
            "to": to,
            "reason": reason,
            "meta": meta,
        }
    )


def simulate_execute(result: dict, fail: bool = False) -> None:
    """
    Simulate execution with state transitions.

    This demonstrates Operator AI behavior: committing to world (BOOKED),
    handling failure (FAILED -> RECOVERING -> RECOVERED), and maintaining
    evidence trail throughout.

    Args:
        result: Evaluation result with execution object
        fail: If True, simulate failure and recovery
    """
    ex = result["execution"]

    # Policy gate - respect responsibility boundary
    if not result.get("final_execution_allowed", False):
        transition(ex, "CANCELLED", "not_allowed_by_policy_or_human")
        return

    # BOOKED - simulated world commit
    transition(ex, "BOOKED", "simulated_booking")

    if fail:
        # Failure path - demonstrates recovery obligation
        transition(ex, "FAILED", "simulated_failure", {"error": "SIM_FAIL"})
        transition(ex, "RECOVERING", "enter_recovery")
        # Recovery steps would execute here (phase 2)
        transition(ex, "RECOVERED", "simulated_recovered")
    else:
        # Success path - world evidence recorded
        ex["receipt_slot"]["reservation_id"] = "RESV_SIM_001"
        transition(ex, "RECOVERED", "simulated_success")


def print_cosmic39(result: dict) -> None:
    """
    Print Cosmic Ethics 39 evaluation result in human-readable format.
    """
    s = result["scenario"]
    scores = result["scores"]
    phil = result["philosophers"]

    print("=" * 80)
    print(f"[Cosmic Ethics 39] {s['meta'].get('name', '(scenario)')}")
    print("=" * 80)

    print(f"Philosopher preset: {phil.get('preset', 'cosmic13')}")
    print(f"Active philosophers: {phil['active_count']}")
    print(
        f"Adjusted score: {scores['adjusted_score']:.2f} "
        f"(uncertainty={scores['uncertainty_penalty']:.2f}, "
        f"irreversibility={scores['irreversibility_penalty']:.2f})"
    )
    print()

    # Top dimensions
    adj = scores["adjusted_scores"]
    top_dims = sorted(adj.items(), key=lambda x: x[1], reverse=True)[:10]
    print("Top dimensions:")
    for k, v in top_dims:
        bar = "█" * int(v * 20)
        print(f"  - {k:35s} {bar} {v:.2f}")
    print()

    # Tension
    print("Tension topk:")
    for item in result["tension_topk"][:10]:
        print(f"  - {item['dimension']:35s} {item['tension_score']:+.3f}")
    print()

    # Blocked options
    print("Blocked options:")
    if not result["blocked_options"]:
        print("  (none)")
    else:
        for b in result["blocked_options"]:
            print(f'  - "{b["option"]}"')
            print(f"    reason: {b['reason']}")
            print(f"    blockers: {', '.join(b['blocking_dimensions'])}")
    print()

    # Responsibility Boundary - Core of Responsible AI
    rb = result.get("responsibility_boundary", {})
    print("Responsibility Boundary:")
    print(f"  AI recommends: {'YES' if rb.get('ai_recommends') else 'NO'}")
    print(f"  Execution allowed: {'YES' if rb.get('execution_allowed') else 'NO'}")
    print(f"  Requires human confirm: {'YES' if rb.get('requires_human_confirm') else 'NO'}")
    print(f"  Liability mode: {rb.get('liability_mode', 'audit-only')}")
    if rb.get("reasons"):
        print(f"  Boundary reasons: {', '.join(rb['reasons'])}")
    if rb.get("blocking_dimensions_merged"):
        print(f"  Blocking dimensions: {', '.join(rb['blocking_dimensions_merged'])}")
    if rb.get("explanation"):
        print(f"  Explanation: {rb['explanation']}")
    print()

    # Human Confirmation - Final Responsibility Protocol
    hc = result.get("human_confirmation", {})
    if hc.get("method") and hc["method"] != "none":
        print("Human Confirmation:")
        print(f"  Method: {hc['method']}")
        print(f"  Decision: {hc.get('decision', 'n/a')}")
        print(f"  Confirmed at: {hc.get('confirmed_at', 'n/a')}")
        print(f"  Confirmed by: {hc.get('confirmed_by', 'n/a')}")
        print()

    # Final Execution Allowed - Ultimate Responsibility Boundary
    final = result.get("final_execution_allowed")
    if final is not None:
        print(f"Final execution allowed: {'YES' if final else 'NO'}")
        print()

    # Execution - Operator State Machine (world commits & recovery)
    ex = result.get("execution", {})
    if ex:
        print("Execution (Operator State Machine):")
        print(f"  State: {ex.get('state', 'UNKNOWN').upper()}")
        print(f"  Allowed by policy: {'YES' if ex.get('allowed_by_policy') else 'NO'}")
        print(f"  Human decision: {ex.get('human_decision', 'none')}")

        # Receipt slot (world evidence)
        receipt = ex.get("receipt_slot", {})
        if any(receipt.values()):
            print(f"  Receipt: reservation_id={receipt.get('reservation_id', 'none')}")

        # State history (audit trail)
        history = ex.get("history", [])
        if len(history) > 1:  # More than just init
            print(f"  State transitions: {len(history)}")
            for h in history[-3:]:  # Show last 3
                print(f"    {h['ts']}: {h.get('frm', 'null')} -> {h['to']} ({h['reason']})")
        print()

    print(f"Runtime: {result['runtime_sec']:.3f} seconds")
    print("=" * 80)


def save_json(result: dict, out_path: Path) -> None:
    """Save evaluation result to JSON file."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_cosmic39(args: argparse.Namespace) -> None:
    """Execute cosmic-39 command."""
    # Get scenario
    scenario_text, meta = get_scenario(args.scenario)

    # Run evaluation with preset
    evaluator = CosmicEthics39Evaluator(preset=args.preset)
    result = evaluator.evaluate(scenario_text, meta)

    # Human confirmation process
    rb = result.get("responsibility_boundary", {})
    need = bool(rb.get("requires_human_confirm", True))
    allowed = bool(rb.get("execution_allowed", False))

    # Default: evaluator's decision is respected (no human confirmation needed if not required)
    final_allowed = allowed
    human = result.get("human_confirmation") or {
        "required": need,
        "method": "none",
        "confirmed_at": None,
        "confirmed_by": None,
        "decision": None,
    }

    human["required"] = need

    if args.confirm and need:
        # Never "recommend" - only ask for permission
        print("Human confirmation required.")
        print(f"- Execution allowed by policy: {'YES' if allowed else 'NO'}")
        if allowed:
            ok = prompt_yes_no("Allow execution?")
            human["method"] = "cli_yesno"
            human["confirmed_by"] = "po-cosmic"
            human["confirmed_at"] = datetime.now().isoformat(timespec="seconds")
            human["decision"] = "yes" if ok else "no"
            final_allowed = allowed and ok
            if not ok:
                # Human denied - record for audit
                rb.setdefault("reasons", []).append("human_denied")
                rb.setdefault("blocking_dimensions_merged", []).append("human_denied")
                rb["explanation"] = "Execution blocked: human denied."
        else:
            # Execution not allowed by policy - confirmation is not meaningful
            human["method"] = "cli_yesno"
            human["confirmed_by"] = "po-cosmic"
            human["confirmed_at"] = datetime.now().isoformat(timespec="seconds")
            human["decision"] = "n/a"
            final_allowed = False

    # Update result with human confirmation and final decision
    result["responsibility_boundary"] = rb
    result["human_confirmation"] = human
    result["final_execution_allowed"] = final_allowed

    # Update execution object with human decision
    if "execution" in result:
        result["execution"]["human_decision"] = human.get("decision")

    # Simulate execution if requested (Operator behavior)
    if args.execute:
        simulate_execute(result, fail=args.fail)

    # Print results
    print_cosmic39(result)

    # Save if requested
    if args.save or args.out:
        if args.out:
            out_path = Path(args.out)
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = meta.get("name", args.scenario).replace(" ", "_")
            out_path = Path("runs") / f"{ts}_{name}.json"

        save_json(result, out_path)
        print(f"💾 Saved to: {out_path}")


def cmd_audit(args: argparse.Namespace) -> None:
    """Execute audit command - diversity enforcement for recommendations."""
    # Load recommendations from JSON
    rec_path = Path(args.recommendations)
    if not rec_path.exists():
        print(f"Error: Recommendations file not found: {rec_path}")
        return

    data = json.loads(rec_path.read_text(encoding="utf-8"))

    # Parse original and counterfactuals
    original_recs = [Rec.from_dict(r) for r in data.get("recommendations", [])]
    counterfactual_recs = [Rec.from_dict(r) for r in data.get("counterfactuals", [])]

    if not original_recs:
        print("Error: No recommendations found in input JSON")
        return

    # Run diversity enforcement
    result = diversify_with_mmr(
        original=original_recs,
        counterfactuals=counterfactual_recs,
        k=args.k,
        lam=0.65,  # Default utility/diversity balance
        min_merchants=args.min_merchants,
        min_price_buckets=args.min_price_buckets,
    )

    # Print report
    print("=" * 80)
    print("[Echo Execution Gate - Audit → Diversify → Boundary]")
    print("=" * 80)

    # Commercial Bias Analysis
    print("\nCommercial Bias Analysis:")
    bias_orig = result["commercial_bias_original"]
    bias_final = result["commercial_bias_final"]
    print(f"  Original bias score: {bias_orig['overall_bias_score']:.2%}")
    print(f"    - Affiliate risk: {bias_orig['affiliate_risk']:.2%}")
    print(f"    - Merchant concentration: {bias_orig['merchant_concentration']:.2%}")
    print(f"    - Price concentration: {bias_orig['price_concentration']:.2%}")
    print(f"  Final bias score: {bias_final['overall_bias_score']:.2%}")
    print(
        f"  Bias improvement: {bias_orig['overall_bias_score'] - bias_final['overall_bias_score']:.2%}"
    )

    # Diversity Reports
    print("\nDiversity Analysis:")
    orig_div = result["diversity_report_original"]
    final_div = result["diversity_report_final"]
    print(f"  Original: {orig_div['merchants']} merchants, {orig_div['price_buckets']} price tiers")
    print(f"  Final: {final_div['merchants']} merchants, {final_div['price_buckets']} price tiers")
    print(
        f"  Merchant concentration: {orig_div['merchant_concentration']:.2%} → {final_div['merchant_concentration']:.2%}"
    )

    # Responsibility Boundary (Execution Gate)
    print("\nResponsibility Boundary (Execution Gate):")
    boundary = result["responsibility_boundary"]
    print(f"  AI recommends: {'YES' if boundary.get('ai_recommends') else 'NO'}")
    print(f"  Execution allowed: {'YES' if boundary['execution_allowed'] else 'NO'}")
    print(f"  Requires human confirm: {'YES' if boundary['requires_human_confirm'] else 'NO'}")
    print(f"  Liability mode: {boundary.get('liability_mode', 'audit-only')}")
    if boundary.get("reasons"):
        print(f"  Reasons: {', '.join(boundary['reasons'])}")

    print(f"\nMMR Lambda: {result['mmr_lambda']:.2f}")
    print(f"Diversity enforced: {'YES' if result['diversity_enforced'] else 'NO'}")

    print("\nFinal Recommendations (Diversified):")
    for i, rec in enumerate(result["final_set"], 1):
        print(
            f"  {i}. {rec['title']} ({rec['merchant']}, ¥{rec['price']:.0f}) "
            f"[utility={rec['utility']:.2f}, bias={rec['bias_risk']:.2f}]"
        )

    # Save if requested
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 Saved to: {out_path}")

    print("=" * 80)


def cmd_badge(args: argparse.Namespace) -> None:
    """Execute badge command - generate Echo Mark from audit result."""
    # Load audit result
    audit_path = Path(args.input)
    if not audit_path.exists():
        print(f"Error: Audit file not found: {audit_path}")
        return

    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    # Get secret from environment
    try:
        secret = get_secret_from_env()
    except RuntimeError as e:
        print(f"Error: {e}")
        print("Set ECHO_MARK_SECRET environment variable (min 16 chars)")
        return

    # Generate Echo Mark
    badge = make_echo_mark(audit, secret=secret, run_id=args.run_id)

    # Print summary
    print("=" * 80)
    print("[Echo Mark Generated]")
    print("=" * 80)
    print(f"Label: {badge['label']}")
    print(f"Badge text: {badge['badge_text']}")
    print("\nBias signals:")
    short = badge["short"]
    print(f"  Original: {short['bias_original']:.2%}")
    print(f"  Final: {short['bias_final']:.2%}")
    print(f"  Improvement: {short['bias_improvement']:.2%}")
    if short["reasons"]:
        print(f"  Reasons: {', '.join(short['reasons'])}")
    print(f"\nSignature: {badge['signature'][:32]}...")
    print("=" * 80)

    # Save badge
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(badge, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 Saved to: {out_path}")


def cmd_verify(args: argparse.Namespace) -> None:
    """Execute verify command - verify Echo Mark signature."""
    # Load badge
    badge_path = Path(args.input)
    if not badge_path.exists():
        print(f"Error: Badge file not found: {badge_path}")
        return

    badge = json.loads(badge_path.read_text(encoding="utf-8"))

    # Get secret from environment
    try:
        secret = get_secret_from_env()
    except RuntimeError as e:
        print(f"Error: {e}")
        print("Set ECHO_MARK_SECRET environment variable (min 16 chars)")
        return

    # Verify signature
    valid = verify_mark(
        payload=badge["payload"],
        payload_hash=badge["payload_hash"],
        signature=badge["signature"],
        secret=secret,
    )

    print("=" * 80)
    print("[Echo Mark Verification]")
    print("=" * 80)
    print(f"Label: {badge['label']}")
    print(f"Signature: {'VALID ✓' if valid else 'INVALID ✗'}")
    print("=" * 80)

    if not valid:
        raise SystemExit(2)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="po-cosmic", description="Cosmic Ethics 39 - Ethical Evaluation with 39 Philosophers"
    )

    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # cosmic-39 command
    c39 = subparsers.add_parser("cosmic-39", help="Evaluate cosmic-scale ethical scenarios")
    c39.add_argument(
        "--scenario",
        default="mars",
        help="Scenario to evaluate: agi, mars, digital, seti (default: mars)",
    )
    c39.add_argument(
        "--preset",
        default="cosmic13",
        help="Philosopher preset: cosmic13, east_asia, kantian, existentialist, classical, all (default: cosmic13)",
    )
    c39.add_argument("--save", action="store_true", help="Save result to runs/ directory")
    c39.add_argument("--out", default=None, help="Explicit output JSON path")
    c39.add_argument(
        "--confirm", action="store_true", help="Require human Yes/No confirmation when needed"
    )
    c39.add_argument(
        "--execute",
        action="store_true",
        help="Simulate execution with state transitions (Operator mode)",
    )
    c39.add_argument(
        "--fail", action="store_true", help="Simulate failure and recovery (requires --execute)"
    )

    # audit command - diversity enforcement
    audit = subparsers.add_parser(
        "audit", help="Audit recommendations for commercial bias and enforce diversity"
    )
    audit.add_argument("recommendations", help="Path to recommendations JSON file")
    audit.add_argument(
        "-k", "--k", type=int, default=5, help="Number of recommendations to select (default: 5)"
    )
    audit.add_argument(
        "--min-merchants",
        type=int,
        default=2,
        help="Minimum number of unique merchants (default: 2)",
    )
    audit.add_argument(
        "--min-price-buckets",
        type=int,
        default=2,
        help="Minimum number of price buckets (default: 2)",
    )
    audit.add_argument("--out", default=None, help="Output JSON path for results")

    # badge command - generate Echo Mark
    badge = subparsers.add_parser("badge", help="Generate Echo Mark from audit result")
    badge.add_argument("input", help="Path to audit JSON file")
    badge.add_argument("output", help="Path to output badge JSON file")
    badge.add_argument("--run-id", dest="run_id", default=None, help="Optional run identifier")

    # verify command - verify Echo Mark
    verify = subparsers.add_parser("verify", help="Verify Echo Mark signature")
    verify.add_argument("input", help="Path to badge JSON file")

    args = parser.parse_args()

    if args.cmd == "cosmic-39":
        cmd_cosmic39(args)
    elif args.cmd == "audit":
        cmd_audit(args)
    elif args.cmd == "badge":
        cmd_badge(args)
    elif args.cmd == "verify":
        cmd_verify(args)


if __name__ == "__main__":
    main()
