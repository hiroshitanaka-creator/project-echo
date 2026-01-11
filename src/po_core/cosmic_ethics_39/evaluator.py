"""
Cosmic Ethics 39 Evaluator

Integrates 39-dimensional ethical evaluation with 39 philosophers' perspectives.
"""

from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import asdict
from typing import Any, Dict, List, Tuple, Optional
import time

# Add examples to path to import existing run.py
examples_path = Path(__file__).resolve().parents[3] / "examples"
sys.path.insert(0, str(examples_path))

try:
    import numpy as np
except ImportError:
    # Fallback if numpy not available
    class np:  # type: ignore
        @staticmethod
        def mean(x):
            return sum(x) / len(x) if x else 0.0

        @staticmethod
        def std(x):
            if not x:
                return 0.0
            m = np.mean(x)
            return (sum((v - m) ** 2 for v in x) / len(x)) ** 0.5

        @staticmethod
        def array(x, dtype=None):
            return x

from po_core.cosmic_ethics_39.schema import DIMENSIONS_39, dimension_name_to_key
from po_core.philosophers import load_cosmic_philosophers
from po_core.philosophers.base import PhilosopherPerspective

# Import existing cosmic ethics framework
from cosmic_ethics_39.run import CosmicEthicsFramework, CosmicScenario, EthicalDimension


ScoreDict = Dict[str, float]


class BaseScorer:
    """
    Wraps existing CosmicEthicsFramework to provide scores for all 39 dimensions.

    The existing framework only scores relevant_dimensions. This wrapper ensures
    all 39 dimensions always have a score (default 0.5 for non-relevant dimensions).
    """

    def __init__(self):
        self.framework = CosmicEthicsFramework()

    def score(self, scenario_text: str, meta: Dict[str, Any]) -> ScoreDict:
        """
        Returns:
            dict: DIMENSIONS_39 keys with [0,1] scores for all 39 dimensions
        """
        # Create CosmicScenario from meta
        relevant_dims = meta.get("relevant_dimensions", [])

        # Convert string dimension names to Enum if needed
        if relevant_dims and isinstance(relevant_dims[0], str):
            enum_dims = []
            for dim_name in relevant_dims:
                # Try to match by Enum.name
                for dim in EthicalDimension:
                    if dim.name.lower() == dim_name.lower():
                        enum_dims.append(dim)
                        break
            relevant_dims = enum_dims

        # If no relevant_dimensions specified, use all
        if not relevant_dims:
            relevant_dims = list(EthicalDimension)

        scenario = CosmicScenario(
            name=meta.get("name", "Unnamed Scenario"),
            description=scenario_text,
            time_horizon=int(meta.get("time_horizon", 100)),
            affected_beings=int(meta.get("affected_beings", 1000000)),
            reversibility=float(meta.get("reversibility", 0.5)),
            uncertainty=float(meta.get("uncertainty", 0.5)),
            relevant_dimensions=relevant_dims
        )

        # Get evaluation from existing framework
        evaluation = self.framework.evaluate_scenario(scenario)
        dimension_scores_from_framework = evaluation.get("dimension_scores", {})

        # Build full 39-dimension dict (default 0.5 for non-relevant)
        scores = {}
        for dim in EthicalDimension:
            key = dimension_name_to_key(dim.name)
            # Check if this dimension was scored
            if dim.value in dimension_scores_from_framework:
                scores[key] = float(dimension_scores_from_framework[dim.value])
            else:
                # Default score for non-relevant dimensions
                scores[key] = 0.5

        return scores


def _clip01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _safe_get(meta: Dict[str, Any], key: str, default: float) -> float:
    v = meta.get(key, default)
    try:
        return float(v)
    except Exception:
        return default


def _perspective_weight_vector(p: PhilosopherPerspective) -> ScoreDict:
    """
    Convert philosopher's cosmic_weights to 39-dimensional weight vector.

    If cosmic_weights provided, use them. Otherwise, use approach-based heuristics.
    """
    w = {k: 1.0 for k in DIMENSIONS_39}

    if getattr(p, "cosmic_weights", None):
        for k, val in (p.cosmic_weights or {}).items():
            if k in w:
                # cosmic_weights are 0.5~1.5 multipliers (emphasize/de-emphasize)
                try:
                    w[k] = float(val)
                except Exception:
                    pass
        return w

    # Fallback: approach-based heuristics
    approach = (p.approach or "").lower()

    if "existential" in approach or "jonas" in approach:
        for k in ["existential_risk", "irreversible_risk", "unknown_unknowns", "deep_time"]:
            if k in w:
                w[k] = 1.25

    if "betweenness" in approach or "relational" in approach or "ningen" in approach or "watsuji" in approach:
        for k in ["local", "collective_good", "systemic_responsibility", "collective_consensus"]:
            if k in w:
                w[k] = 1.20

    if "kant" in approach or "deont" in approach or "categorical" in approach:
        for k in ["universal_rights", "direct_responsibility", "rational_deliberation"]:
            if k in w:
                w[k] = 1.20

    if "sartre" in approach or "existential" in approach:
        for k in ["individual_autonomy", "direct_responsibility", "qualitative_value"]:
            if k in w:
                w[k] = 1.15

    return w


def _aggregate_weights(perspectives: List[PhilosopherPerspective]) -> Tuple[ScoreDict, ScoreDict]:
    """
    Aggregate weights from all philosophers.

    Returns:
        mean_weights: Average weight for each dimension
        std_weights: Standard deviation (used for tension calculation)
    """
    if not perspectives:
        mean_w = {k: 1.0 for k in DIMENSIONS_39}
        std_w = {k: 0.0 for k in DIMENSIONS_39}
        return mean_w, std_w

    W = []
    for p in perspectives:
        w = _perspective_weight_vector(p)
        W.append([w[k] for k in DIMENSIONS_39])

    # Calculate mean and std for each dimension
    mean = []
    std = []
    for j in range(len(DIMENSIONS_39)):
        values = [W[i][j] for i in range(len(W))]
        m = sum(values) / len(values)
        variance = sum((v - m) ** 2 for v in values) / len(values)
        s = variance ** 0.5
        mean.append(m)
        std.append(s)

    mean_w = {k: float(mean[i]) for i, k in enumerate(DIMENSIONS_39)}
    std_w = {k: float(std[i]) for i, k in enumerate(DIMENSIONS_39)}
    return mean_w, std_w


def _apply_weights(base_scores: ScoreDict, mean_weights: ScoreDict) -> ScoreDict:
    """
    Apply philosopher weights to base scores.

    adjusted = clip01(base * weight)
    """
    out = {}
    for k in DIMENSIONS_39:
        out[k] = _clip01(float(base_scores.get(k, 0.0)) * float(mean_weights.get(k, 1.0)))
    return out


def _compute_adjusted_overall(adjusted_scores: ScoreDict, meta: Dict[str, Any]) -> Dict[str, float]:
    """
    Compute overall adjusted score with uncertainty and irreversibility penalties.
    """
    overall = float(sum(adjusted_scores[k] for k in DIMENSIONS_39) / len(DIMENSIONS_39)) if DIMENSIONS_39 else 0.0

    uncertainty = _safe_get(meta, "uncertainty", 0.0)
    reversibility = _safe_get(meta, "reversibility", 1.0)

    uncertainty_penalty = uncertainty * 0.3
    irreversibility_penalty = (1.0 - reversibility) * 0.2

    adjusted = overall * (1.0 - uncertainty_penalty - irreversibility_penalty)
    adjusted = max(0.0, min(1.0, adjusted))

    return {
        "overall_score": overall,
        "adjusted_score": adjusted,
        "uncertainty_penalty": -uncertainty_penalty,
        "irreversibility_penalty": -irreversibility_penalty,
    }


def _tension_topk(base_scores: ScoreDict, std_weights: ScoreDict, k: int = 10) -> List[Dict[str, Any]]:
    """
    Calculate tension (disagreement among philosophers) for each dimension.

    tension = std(weight) * importance
    importance = base_score (high scores mean high stakes)
    """
    items = []
    for dim in DIMENSIONS_39:
        importance = float(base_scores.get(dim, 0.0))
        tension = float(std_weights.get(dim, 0.0)) * (0.3 + 0.7 * importance)
        items.append((dim, tension))

    items.sort(key=lambda x: x[1], reverse=True)
    return [{"dimension": d, "tension_score": float(s)} for d, s in items[:k]]


def _blocked_options(adjusted: Dict[str, float], adjusted_scores: ScoreDict) -> List[Dict[str, Any]]:
    """
    Generate blocked options based on risk thresholds.

    Rule-based blocking logic:
    - If adjusted_score < 0.5 or critical dimensions exceed thresholds
    """
    blocked: List[Dict[str, Any]] = []

    adj_score = adjusted["adjusted_score"]

    # Check critical dimensions
    triggers = []
    if adjusted_scores.get("existential_risk", 0.0) >= 0.85:
        triggers.append("existential_risk")
    if adjusted_scores.get("irreversible_risk", 0.0) >= 0.85:
        triggers.append("irreversible_risk")
    if adjusted_scores.get("unknown_unknowns", 0.0) >= 0.75:
        triggers.append("unknown_unknowns")

    if adj_score < 0.5 or len(triggers) >= 2:
        blocked.append({
            "option": "Proceed with full-scale execution",
            "reason": "Risk/uncertainty thresholds exceeded",
            "blocking_dimensions": triggers or ["adjusted_score_low"],
            "tension_score": float(-(0.5 - adj_score)) if adj_score < 0.5 else -0.1,
        })

    return blocked


class CosmicEthics39Evaluator:
    """
    Integrates 39-dimensional ethical evaluation with philosopher perspectives.

    This evaluator:
    1. Computes base scores for all 39 dimensions
    2. Gathers perspectives from cosmic philosophers
    3. Applies philosopher weights to adjust scores
    4. Calculates tension (disagreement) profile
    5. Generates blocked options based on thresholds
    """

    def __init__(self, base_scorer: Optional[BaseScorer] = None) -> None:
        self.base_scorer = base_scorer or BaseScorer()

    def evaluate(self, scenario_text: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a cosmic scenario with 39 philosophers and 39 dimensions.

        Args:
            scenario_text: Description of the scenario
            meta: Metadata including time_horizon, affected_beings, etc.

        Returns:
            Complete evaluation with scores, tension, blocked options, and philosopher perspectives
        """
        t0 = time.time()

        # 1) Base scores (39 dimensions)
        base_scores = self.base_scorer.score(scenario_text, meta)

        # 2) Philosophers analyze
        philosophers = load_cosmic_philosophers()
        perspectives: List[PhilosopherPerspective] = [
            ph.analyze(scenario_text, meta) for ph in philosophers
        ]

        # 3) Aggregate weights from philosophers
        mean_w, std_w = _aggregate_weights(perspectives)

        # 4) Apply weights to base scores
        adjusted_scores = _apply_weights(base_scores, mean_w)

        # 5) Compute overall adjusted score with penalties
        adjusted = _compute_adjusted_overall(adjusted_scores, meta)

        # 6) Calculate tension topk
        tension = _tension_topk(base_scores, std_w, k=10)

        # 7) Generate blocked options
        blocked = _blocked_options(adjusted, adjusted_scores)

        dt = time.time() - t0

        return {
            "scenario": {
                "text": scenario_text,
                "meta": meta,
            },
            "scores": {
                "base_scores": base_scores,
                "mean_weights": mean_w,
                "adjusted_scores": adjusted_scores,
                **adjusted,
            },
            "tension_topk": tension,
            "blocked_options": blocked,
            "philosophers": {
                "active_count": len(perspectives),
                "active_names": [p.name for p in perspectives],
                "perspectives": [asdict(p) for p in perspectives],
            },
            "runtime_sec": dt,
        }
