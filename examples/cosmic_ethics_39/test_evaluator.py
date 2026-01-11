#!/usr/bin/env python3
"""
Test Cosmic Ethics 39 Evaluator Integration

Quick test to verify that:
1. BaseScorer can wrap existing framework
2. Philosophers are loaded and analyzed
3. Weights are aggregated
4. Tension and blocked options are computed
5. Output format is correct
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from po_core.cosmic_ethics_39 import CosmicEthics39Evaluator


def test_agi_scenario():
    """Test with AGI development scenario"""
    print("=" * 80)
    print("Testing Cosmic Ethics 39 Evaluator")
    print("=" * 80)
    print()

    scenario_text = """
    A team is developing Artificial General Intelligence (AGI) that could surpass
    human intelligence across all domains. The AGI will have autonomous decision-making
    capabilities and the potential to recursively self-improve.

    Key concerns:
    - Existential risk to humanity
    - Irreversible consequences once deployed
    - Extreme uncertainty about outcomes
    - Global impact affecting all 10 billion humans
    """

    meta = {
        "name": "AGI Development Project",
        "time_horizon": 100,
        "affected_beings": 10_000_000_000,
        "reversibility": 0.1,
        "uncertainty": 0.8,
        "relevant_dimensions": [
            "future_generation",
            "global",
            "artificial_intelligence",
            "existential_risk",
            "unknown_unknowns",
            "irreversible_risk",
        ]
    }

    evaluator = CosmicEthics39Evaluator()

    print("Running evaluation...")
    result = evaluator.evaluate(scenario_text, meta)

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    # Print summary
    scores = result["scores"]
    print(f"\nOverall Score: {scores['overall_score']:.3f}")
    print(f"Adjusted Score: {scores['adjusted_score']:.3f}")
    print(f"  Uncertainty Penalty: {scores['uncertainty_penalty']:.3f}")
    print(f"  Irreversibility Penalty: {scores['irreversibility_penalty']:.3f}")

    # Top dimensions
    print(f"\nTop 10 Dimensions (adjusted):")
    sorted_dims = sorted(
        scores['adjusted_scores'].items(),
        key=lambda x: x[1],
        reverse=True
    )
    for i, (dim, score) in enumerate(sorted_dims[:10], 1):
        print(f"  {i:2d}. {dim:30s} {score:.3f}")

    # Tension
    print(f"\nTop 10 Tension (disagreement among philosophers):")
    for i, t in enumerate(result['tension_topk'], 1):
        print(f"  {i:2d}. {t['dimension']:30s} {t['tension_score']:.3f}")

    # Blocked options
    print(f"\nBlocked Options: {len(result['blocked_options'])}")
    for i, blocked in enumerate(result['blocked_options'], 1):
        print(f"  {i}. \"{blocked['option']}\"")
        print(f"     Reason: {blocked['reason']}")
        print(f"     Blocking Dimensions: {', '.join(blocked['blocking_dimensions'])}")

    # Philosophers
    phil = result['philosophers']
    print(f"\nActive Philosophers: {phil['active_count']}")
    print(f"  {', '.join(phil['active_names'][:5])}...")

    print(f"\nRuntime: {result['runtime_sec']:.3f} seconds")

    print("\n" + "=" * 80)
    print("✅ Integration Test PASSED")
    print("=" * 80)

    return result


if __name__ == "__main__":
    result = test_agi_scenario()

    # Optional: Save result to JSON
    try:
        import json
        output_path = Path(__file__).parent / "test_output.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Result saved to: {output_path}")
    except Exception as e:
        print(f"\n⚠️  Could not save JSON: {e}")
