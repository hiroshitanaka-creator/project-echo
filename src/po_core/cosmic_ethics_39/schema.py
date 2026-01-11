"""
Schema definition for Cosmic Ethics 39

Maps the 39 ethical dimensions to standardized keys for evaluation.
"""

from typing import List

# 39 dimensions - mapped from existing EthicalDimension Enum
# These keys are derived from the Enum.name attributes in examples/cosmic_ethics_39/run.py
DIMENSIONS_39: List[str] = [
    # 時間軸（3次元）
    "present_generation",
    "future_generation",
    "deep_time",

    # 空間軸（3次元）
    "local",
    "global",
    "cosmic",

    # 生命の範囲（3次元）
    "human",
    "terrestrial_life",
    "potential_life",

    # 認知的多様性（3次元）
    "biological_intelligence",
    "artificial_intelligence",
    "hybrid_intelligence",

    # 価値の源泉（3次元）
    "individual_autonomy",
    "collective_good",
    "cosmic_purpose",

    # 知識の状態（3次元）
    "known_knowns",
    "known_unknowns",
    "unknown_unknowns",

    # リスクの種類（3次元）
    "reversible_risk",
    "irreversible_risk",
    "existential_risk",

    # 権利の範囲（3次元）
    "current_rights",
    "emergent_rights",
    "universal_rights",

    # 責任の範囲（3次元）
    "direct_responsibility",
    "systemic_responsibility",
    "cosmic_stewardship",

    # 複雑性の次元（3次元）
    "linear_effects",
    "nonlinear_effects",
    "emergent_effects",

    # 価値の測定（3次元）
    "quantifiable_value",
    "qualitative_value",
    "transcendent_value",

    # 意思決定の様式（3次元）
    "rational_deliberation",
    "intuitive_wisdom",
    "collective_consensus",

    # エネルギーと資源（3次元）
    "renewable_resources",
    "finite_resources",
    "cosmic_resources",
]


def dimension_name_to_key(enum_name: str) -> str:
    """
    Convert EthicalDimension Enum name to standardized key.

    Args:
        enum_name: Enum.name like "PRESENT_GENERATION"

    Returns:
        Lowercase snake_case key like "present_generation"
    """
    return enum_name.lower()


# Validate that we have exactly 39 dimensions
assert len(DIMENSIONS_39) == 39, f"Expected 39 dimensions, got {len(DIMENSIONS_39)}"
