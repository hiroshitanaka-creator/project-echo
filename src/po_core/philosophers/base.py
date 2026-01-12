"""
Base Philosopher Class

Abstract base class for all philosophical reasoning modules.
Each philosopher provides a unique perspective for analyzing and generating meaning.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PhilosopherPerspective:
    """
    Perspective from a philosopher for Cosmic Ethics 39 / Po_core integration.

    This bridges the gap between individual philosopher reasoning and
    the cosmic ethics evaluation framework.
    """

    name: str
    approach: str
    reasoning: str

    # Cosmic Ethics 39 dimension weights (optional)
    # Maps dimension names to weights (0.0-1.0)
    cosmic_weights: dict[str, float] | None = None

    # FreedomPressureTensor integration (optional)
    # Maps pressure dimensions to values
    freedom_pressure: dict[str, float] | None = None

    # Tension profile - which dimensions conflict
    tension_elements: list | None = field(default_factory=list)

    # Blocked options - what this philosopher would reject
    blocked_options: list | None = field(default_factory=list)

    # Additional notes or commentary
    notes: str | None = None

    # Raw reasoning result from the philosopher
    raw_result: dict[str, Any] | None = None


class Philosopher(ABC):
    """
    Abstract base class for all philosophers.

    Each philosopher must implement their own reasoning method that reflects
    their unique philosophical perspective.
    """

    def __init__(self, name: str, description: str) -> None:
        """
        Initialize a philosopher.

        Args:
            name: The philosopher's name
            description: A brief description of their philosophical approach
        """
        self.name = name
        self.description = description
        self._context: dict[str, Any] = {}

    @abstractmethod
    def reason(self, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Generate philosophical reasoning for the given prompt.

        Args:
            prompt: The input text to reason about
            context: Optional context information

        Returns:
            A dictionary containing:
                - reasoning: The philosophical analysis
                - perspective: The philosopher's unique viewpoint
                - tension: Identified tensions or contradictions
                - metadata: Additional reasoning metadata
        """
        pass

    def analyze(self, prompt: str, context: dict[str, Any] | None = None) -> PhilosopherPerspective:
        """
        Analyze prompt and return perspective for Cosmic Ethics 39 integration.

        This method wraps reason() and adds cosmic_weights and freedom_pressure
        for integration with the ethical framework.

        Args:
            prompt: The input text to analyze
            context: Optional context information

        Returns:
            PhilosopherPerspective with cosmic weights and freedom pressure
        """
        # Call the philosopher's reasoning method
        result = self.reason(prompt, context)

        # Extract basic information
        reasoning = result.get("reasoning", "")
        approach = result.get("perspective", self.description)
        metadata = result.get("metadata", {})

        # Extract tension if present
        tension = result.get("tension", {})
        tension_elements = tension.get("elements", []) if isinstance(tension, dict) else []

        # Compute cosmic weights and freedom pressure
        # Subclasses can override _compute_cosmic_weights and _compute_freedom_pressure
        cosmic_weights = self._compute_cosmic_weights(result, context)
        freedom_pressure = self._compute_freedom_pressure(result, context)
        blocked_options = self._compute_blocked_options(result, context)

        return PhilosopherPerspective(
            name=self.name,
            approach=approach,
            reasoning=reasoning,
            cosmic_weights=cosmic_weights,
            freedom_pressure=freedom_pressure,
            tension_elements=tension_elements,
            blocked_options=blocked_options,
            notes=metadata.get("approach", ""),
            raw_result=result,
        )

    def _compute_cosmic_weights(
        self, result: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, float] | None:
        """
        Compute Cosmic Ethics 39 dimension weights from reasoning result.

        Override this method in subclasses to provide philosopher-specific weights.

        Args:
            result: The result from reason()
            context: Optional context

        Returns:
            Dictionary mapping dimension names to weights (0.0-1.0)
        """
        # Default: return None, subclasses should override
        return None

    def _compute_freedom_pressure(
        self, result: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, float] | None:
        """
        Compute FreedomPressureTensor values from reasoning result.

        Override this method in subclasses to provide philosopher-specific pressure.

        Args:
            result: The result from reason()
            context: Optional context

        Returns:
            Dictionary mapping pressure dimensions to values
        """
        # Default: return None, subclasses should override
        return None

    def _compute_blocked_options(
        self, result: dict[str, Any], context: dict[str, Any] | None = None
    ) -> list:
        """
        Compute which options this philosopher would block/reject.

        Override this method in subclasses to provide philosopher-specific blocking.

        Args:
            result: The result from reason()
            context: Optional context

        Returns:
            List of blocked options with reasons
        """
        # Default: return empty list, subclasses should override
        return []

    def __repr__(self) -> str:
        """String representation of the philosopher."""
        return f"{self.__class__.__name__}(name='{self.name}')"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"🧠 {self.name}: {self.description}"
