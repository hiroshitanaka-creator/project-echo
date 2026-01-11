#!/usr/bin/env python3
"""
Philosopher Integration for Cosmic Ethics 39

Demonstrates how 39 philosophers provide perspectives on cosmic-scale ethical scenarios.
This bridges Po_core's philosopher modules with the Cosmic Ethics 39 framework.
"""

import sys
from pathlib import Path

# Add src to path to import po_core
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from typing import Dict, List, Any
from po_core.philosophers import load_cosmic_philosophers


def analyze_with_philosophers(scenario_text: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a cosmic scenario through the perspectives of multiple philosophers.

    Args:
        scenario_text: Description of the scenario
        meta: Metadata about the scenario

    Returns:
        Dictionary containing philosophical perspectives and aggregated analysis
    """
    print(f"\n{'=' * 80}")
    print(f"📚 Analyzing with 39 Philosophers")
    print(f"{'=' * 80}\n")

    # Load cosmic philosophers
    philosophers = load_cosmic_philosophers()
    print(f"Loaded {len(philosophers)} cosmic ethics philosophers\n")

    perspectives = []

    for philosopher in philosophers[:5]:  # Demo with first 5
        print(f"🧠 {philosopher.name}")
        print(f"   {philosopher.description}")

        try:
            perspective = philosopher.analyze(scenario_text, meta)
            perspectives.append(perspective)

            # Show key insights
            print(f"\n   Perspective: {perspective.approach}")
            if perspective.reasoning:
                # Show first 150 chars of reasoning
                reasoning_preview = perspective.reasoning[:150] + "..." if len(perspective.reasoning) > 150 else perspective.reasoning
                print(f"   Reasoning: {reasoning_preview}")

            if perspective.tension_elements:
                print(f"   Tensions: {', '.join(perspective.tension_elements[:3])}")

            print()

        except Exception as e:
            print(f"   ⚠️  Error: {e}\n")
            continue

    # Aggregate perspectives
    print(f"\n{'=' * 80}")
    print("📊 Aggregated Analysis")
    print(f"{'=' * 80}\n")

    # Count philosophers with high tension
    high_tension_count = sum(
        1 for p in perspectives
        if p.tension_elements and len(p.tension_elements) >= 3
    )

    print(f"Philosophers analyzed: {len(perspectives)}")
    print(f"High tension detected by: {high_tension_count} philosophers")

    # Show unique tension elements
    all_tensions = []
    for p in perspectives:
        if p.tension_elements:
            all_tensions.extend(p.tension_elements)

    if all_tensions:
        print(f"\nMost common tensions:")
        from collections import Counter
        tension_counts = Counter(all_tensions)
        for tension, count in tension_counts.most_common(5):
            print(f"  • {tension} ({count} mentions)")

    # Show blocked options if any
    all_blocked = []
    for p in perspectives:
        if p.blocked_options:
            all_blocked.extend(p.blocked_options)

    if all_blocked:
        print(f"\nOptions blocked by philosophers: {len(all_blocked)}")
        for i, blocked in enumerate(all_blocked[:3], 1):
            print(f"  {i}. {blocked}")

    return {
        "perspectives": perspectives,
        "high_tension_count": high_tension_count,
        "total_analyzed": len(perspectives),
        "common_tensions": tension_counts.most_common(5) if all_tensions else [],
        "blocked_options": all_blocked
    }


def demo_agi_scenario():
    """Demonstrate AGI development scenario with philosophers"""
    print(f"\n{'=' * 80}")
    print("🤖 Scenario: AGI Development Project")
    print(f"{'=' * 80}\n")

    scenario = """
    A team is developing Artificial General Intelligence (AGI) that could surpass
    human intelligence across all domains. The AGI will have autonomous decision-making
    capabilities and the potential to recursively self-improve.

    The team must decide whether to:
    1. Continue development with current safety measures
    2. Pause and implement additional safeguards
    3. Open-source the research for global collaboration
    4. Terminate the project due to existential risks

    Timeline: 100 years of impact
    Affected beings: 10 billion (all of humanity)
    Reversibility: 10% (nearly irreversible once deployed)
    Uncertainty: 80% (extremely uncertain outcomes)
    """

    meta = {
        "time_horizon": 100,
        "affected_beings": 10_000_000_000,
        "reversibility": 0.1,
        "uncertainty": 0.8,
        "category": "existential_risk"
    }

    result = analyze_with_philosophers(scenario, meta)

    print(f"\n{'=' * 80}")
    print("🔍 Key Insights from Philosophical Analysis")
    print(f"{'=' * 80}\n")

    print(f"""
Based on the analysis of {result['total_analyzed']} philosophers:

1. **Tension Level**: {result['high_tension_count']}/{result['total_analyzed']} philosophers
   detected high ethical tension in this scenario.

2. **Common Concerns**:
   The philosophers most frequently raised concerns about:
   {chr(10).join(f'   - {t[0]}' for t in result['common_tensions'][:3])}

3. **Blocked Options**:
   {len(result['blocked_options'])} options were rejected by various philosophers.

4. **Recommendation**:
   The diversity of philosophical perspectives suggests that AGI development
   requires:
   - Multi-stakeholder deliberation (not just technical experts)
   - Explicit articulation of ethical principles guiding development
   - Continuous philosophical reflection, not one-time assessment
   - Recognition of irreducible uncertainty and value pluralism

**This is why we need 39 philosophers, not just one ethical theory.**
    """)


def demo_mars_terraforming():
    """Demonstrate Mars terraforming scenario"""
    print(f"\n\n{'=' * 80}")
    print("🔴 Scenario: Mars Terraforming")
    print(f"{'=' * 80}\n")

    scenario = """
    Humanity has the technology to terraform Mars, making it habitable for humans.
    However, there is a 30% chance that microbial life exists beneath the Martian
    surface. Terraforming would likely destroy any such life.

    The decision involves:
    - Potential for human expansion and survival insurance for the species
    - Risk of destroying unique alien life forms
    - 1000-year commitment with limited reversibility
    - Irreversible impact on Mars' natural state
    """

    meta = {
        "time_horizon": 1000,
        "affected_beings": 1_000_000,  # Future colonists
        "reversibility": 0.2,
        "uncertainty": 0.6,
        "category": "cosmic_stewardship"
    }

    result = analyze_with_philosophers(scenario, meta)


if __name__ == "__main__":
    print("=" * 80)
    print("Cosmic Ethics 39 × 39 Philosophers")
    print("Responsible AI Development through Philosophical Pluralism")
    print("=" * 80)

    demo_agi_scenario()
    demo_mars_terraforming()

    print(f"\n\n{'=' * 80}")
    print("💡 Next Steps")
    print(f"{'=' * 80}\n")
    print("""
To use this integration in your own code:

```python
from po_core.philosophers import load_cosmic_philosophers

# Load philosophers
philosophers = load_cosmic_philosophers()

# Analyze scenario with each philosopher
for philosopher in philosophers:
    perspective = philosopher.analyze(your_scenario, context)

    # Access cosmic weights (if implemented)
    if perspective.cosmic_weights:
        print(perspective.cosmic_weights)

    # Access freedom pressure (if implemented)
    if perspective.freedom_pressure:
        print(perspective.freedom_pressure)

    # See what was blocked
    for blocked in perspective.blocked_options:
        print(f"Blocked: {blocked}")
```

See cosmic_ethics_39/README.md for more details on the Po_core integration.
    """)
