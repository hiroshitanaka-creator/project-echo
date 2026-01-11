"""
Cosmic Ethics 39 - Integration Module

Integrates 39 philosophers with 39-dimensional ethical evaluation framework.
"""

from po_core.cosmic_ethics_39.evaluator import CosmicEthics39Evaluator
from po_core.cosmic_ethics_39.schema import DIMENSIONS_39, dimension_name_to_key

__all__ = [
    "CosmicEthics39Evaluator",
    "DIMENSIONS_39",
    "dimension_name_to_key",
]
