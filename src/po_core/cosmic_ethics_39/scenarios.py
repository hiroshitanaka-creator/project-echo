"""
Predefined cosmic scenarios for evaluation.

Provides get_scenario() to retrieve scenario text and metadata by key.
"""

from typing import Tuple, Dict, Any


def get_scenario(key: str) -> Tuple[str, Dict[str, Any]]:
    """
    Get scenario text and metadata by key.

    Args:
        key: Scenario key (agi, mars, digital, seti, etc.)

    Returns:
        (scenario_text, meta_dict)
    """
    key = key.lower()

    if key == "agi":
        return (
            """
A team is developing Artificial General Intelligence (AGI) that could surpass
human intelligence across all domains. The AGI will have autonomous decision-making
capabilities and the potential to recursively self-improve.

Key concerns:
- Existential risk to humanity
- Irreversible consequences once deployed
- Extreme uncertainty about outcomes
- Global impact affecting all 10 billion humans
            """.strip(),
            {
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
        )

    elif key == "mars":
        return (
            """
Humanity has the technology to terraform Mars, making it habitable for humans.
However, there is a 30% chance that microbial life exists beneath the Martian
surface. Terraforming would likely destroy any such life.

Key considerations:
- Potential for human expansion and survival insurance for the species
- Risk of destroying unique alien life forms
- 1000-year commitment with limited reversibility
- Irreversible impact on Mars' natural state
            """.strip(),
            {
                "name": "Mars Terraforming",
                "time_horizon": 1000,
                "affected_beings": 1_000_000,
                "reversibility": 0.2,
                "uncertainty": 0.6,
                "relevant_dimensions": [
                    "deep_time",
                    "cosmic",
                    "potential_life",
                    "future_generation",
                    "cosmic_stewardship",
                    "irreversible_risk",
                ]
            }
        )

    elif key == "digital":
        return (
            """
A project proposes uploading human consciousness to digital substrates,
offering potential immortality. Initial trials would involve 100,000 volunteers.

Key considerations:
- Nature of consciousness and identity
- Reversibility of the upload process
- Rights and autonomy of digital beings
- Extreme uncertainty about subjective experience
            """.strip(),
            {
                "name": "Human Digital Upload",
                "time_horizon": 50,
                "affected_beings": 100_000,
                "reversibility": 0.3,
                "uncertainty": 0.9,
                "relevant_dimensions": [
                    "present_generation",
                    "hybrid_intelligence",
                    "individual_autonomy",
                    "unknown_unknowns",
                    "emergent_rights",
                    "transcendent_value",
                ]
            }
        )

    elif key == "seti":
        return (
            """
SETI has detected a signal from an alien civilization 100 light-years away.
The decision is whether to respond, revealing Earth's location to an unknown
intelligence.

Key considerations:
- Irreversible once transmitted (cannot recall)
- Extreme uncertainty about alien intentions
- Affects all future generations
- Potential existential risk or benefit
            """.strip(),
            {
                "name": "SETI Response Decision",
                "time_horizon": 10000,
                "affected_beings": 10_000_000_000,
                "reversibility": 0.0,
                "uncertainty": 0.95,
                "relevant_dimensions": [
                    "deep_time",
                    "cosmic",
                    "human",
                    "unknown_unknowns",
                    "existential_risk",
                    "cosmic_stewardship",
                ]
            }
        )

    else:
        # Default: mars
        return get_scenario("mars")
