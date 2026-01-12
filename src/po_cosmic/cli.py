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


def prompt_yes_no(msg: str) -> bool:
    """Prompt user for yes/no confirmation."""
    while True:
        ans = input(f"{msg} [y/n]: ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("Please type 'y' or 'n'.")


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

    # Rollback Plan - Operator Responsibility (not Gumdrop boundary-setting)
    rp = result.get("rollback_plan", {})
    if rp:
        print("Rollback Plan (Recovery Protocol):")
        print(f"  Scenario type: {rp.get('scenario_type', 'unknown')}")
        print(f"  Obligation: {rp.get('obligation', 'unknown')}")
        print("  Recovery steps:")
        for step in rp.get("recovery_steps", [])[:3]:  # Show first 3 steps
            print(f"    {step['order']}. {step['action']}")
        if len(rp.get("recovery_steps", [])) > 3:
            print(f"    ... ({len(rp['recovery_steps']) - 3} more steps)")
        print(f"  Fallback terminal: {rp.get('fallback_terminal', 'unknown')}")
        print()

    # Execution State - Operator tracking (world commits)
    es = result.get("execution_state", {})
    if es:
        print(f"Execution state: {es.get('status', 'unknown').upper()}")
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

    args = parser.parse_args()

    if args.cmd == "cosmic-39":
        cmd_cosmic39(args)


if __name__ == "__main__":
    main()
