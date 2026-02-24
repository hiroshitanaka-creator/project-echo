"""Property-based test: cosmic ethics example must not emit recommendation strings."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

RUN_PY = Path(__file__).resolve().parents[1] / "examples" / "cosmic_ethics_39" / "run.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("cosmic_ethics_39_run", RUN_PY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@settings(max_examples=50, deadline=None)
@given(st.integers(min_value=0, max_value=5))
def test_evaluate_scenario_never_returns_recommendation(index: int) -> None:
    """Evaluation result must contain only candidate set, evidence, responsibility boundary."""
    module = _load_module()
    framework = module.CosmicEthicsFramework()
    scenarios = module.create_cosmic_scenarios()
    scenario = scenarios[index]

    result = framework.evaluate_scenario(scenario)

    # Project Echo 不変原則：AIはおすすめしない
    assert "recommendation" not in result
    assert "推奨" not in str(result)
    assert "おすすめ" not in str(result)

    assert "candidate_set" in result
    assert "evidence" in result
    assert "responsibility_boundary" in result
