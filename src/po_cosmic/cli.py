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

    # Freedom Pressure (if available)
    # TODO: Add freedom pressure calculation
    # For now, just show placeholder
    print("Freedom Pressure:")
    print("  (not yet implemented)")
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

    # Run evaluation
    evaluator = CosmicEthics39Evaluator()
    result = evaluator.evaluate(scenario_text, meta)

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
    c39.add_argument("--save", action="store_true", help="Save result to runs/ directory")
    c39.add_argument("--out", default=None, help="Explicit output JSON path")

    args = parser.parse_args()

    if args.cmd == "cosmic-39":
        cmd_cosmic39(args)


if __name__ == "__main__":
    main()
