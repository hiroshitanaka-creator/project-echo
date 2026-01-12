"""
Smoke tests for Cosmic Ethics 39

Basic tests to ensure critical components can be imported and instantiated.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))


def test_imports():
    """Test that core modules can be imported."""
    from po_core.cosmic_ethics_39.evaluator import CosmicEthics39Evaluator
    from po_core.cosmic_ethics_39.schema import DIMENSIONS_39
    from po_core.philosophers import load_all_philosophers, load_cosmic_philosophers

    assert CosmicEthics39Evaluator is not None
    assert len(DIMENSIONS_39) == 39
    assert load_all_philosophers is not None
    assert load_cosmic_philosophers is not None


def test_evaluator_instantiation():
    """Test that evaluator can be instantiated."""
    from po_core.cosmic_ethics_39.evaluator import CosmicEthics39Evaluator

    evaluator = CosmicEthics39Evaluator()
    assert evaluator is not None
    assert evaluator.base_scorer is not None


def test_philosophers_loading():
    """Test that philosophers can be loaded."""
    from po_core.philosophers import load_all_philosophers, load_cosmic_philosophers

    all_phil = load_all_philosophers()
    cosmic_phil = load_cosmic_philosophers()

    assert len(all_phil) == 39
    assert len(cosmic_phil) > 0
    assert len(cosmic_phil) <= len(all_phil)


def test_scenario_loading():
    """Test that scenarios can be loaded."""
    from po_core.cosmic_ethics_39.scenarios import get_scenario

    agi_text, agi_meta = get_scenario("agi")
    mars_text, mars_meta = get_scenario("mars")

    assert agi_text is not None
    assert agi_meta["name"] == "AGI Development Project"
    assert mars_meta["name"] == "Mars Terraforming"


def test_basic_evaluation():
    """Test that a basic evaluation can be performed."""
    from po_core.cosmic_ethics_39.evaluator import CosmicEthics39Evaluator
    from po_core.cosmic_ethics_39.scenarios import get_scenario

    evaluator = CosmicEthics39Evaluator()
    scenario_text, meta = get_scenario("agi")

    result = evaluator.evaluate(scenario_text, meta)

    # Check result structure
    assert "scenario" in result
    assert "scores" in result
    assert "tension_topk" in result
    assert "blocked_options" in result
    assert "philosophers" in result

    # Check scores
    assert "adjusted_score" in result["scores"]
    assert 0.0 <= result["scores"]["adjusted_score"] <= 1.0

    # Check philosophers
    assert result["philosophers"]["active_count"] > 0
