"""
Centralized configuration constants for Project Echo.

All tunable thresholds and parameters should be defined here
to ensure consistency across modules and ease of adjustment.
"""

from __future__ import annotations

# =============================================================================
# Bias Thresholds (from threat_model.md)
# =============================================================================

# Bias level above which execution is blocked (requires human intervention)
HIGH_BIAS_THRESHOLD: float = 0.6

# Bias level below which execution is allowed without confirmation
MEDIUM_BIAS_THRESHOLD: float = 0.4

# Minimum bias improvement to allow execution with confirmation
SIGNIFICANT_IMPROVEMENT_THRESHOLD: float = 0.2

# Bias risk above which recommendations are filtered out
HIGH_BIAS_FILTER_THRESHOLD: float = 0.7
# Fallback lower bound for bias-risk pre-filter when candidate pool is too small
MIN_BIAS_FILTER_THRESHOLD: float = 0.0


# =============================================================================
# Diversity Constraints
# =============================================================================

# Minimum number of distinct merchants in final set
DEFAULT_MIN_MERCHANTS: int = 2

# Minimum number of distinct price buckets in final set
DEFAULT_MIN_PRICE_BUCKETS: int = 2

# Merchant concentration threshold above which monopoly is flagged
MONOPOLY_CONCENTRATION_THRESHOLD: float = 0.6


# =============================================================================
# MMR Algorithm Parameters
# =============================================================================

# Default utility weight (1.0=pure utility, 0.0=pure diversity)
DEFAULT_MMR_LAMBDA: float = 0.65

# Default bias risk penalty coefficient
DEFAULT_MMR_BETA: float = 0.8

# Minimum effective utility to include candidate
MIN_EFFECTIVE_UTILITY: float = 0.1

# Floating point comparison tolerance
FLOAT_TOLERANCE: float = 1e-6


# =============================================================================
# Price Bucketing
# =============================================================================

# Price thresholds for low/mid/high buckets (in yen)
PRICE_LOW_THRESHOLD: float = 5000.0
PRICE_HIGH_THRESHOLD: float = 15000.0


# =============================================================================
# Echo Mark / Signature
# =============================================================================

# Minimum secret length for HMAC
MIN_HMAC_SECRET_LENGTH: int = 16

# Maximum badge age for timestamp validation (seconds)
MAX_BADGE_AGE_SECONDS: int = 30 * 24 * 60 * 60  # 30 days


# =============================================================================
# Audio Channel / Voice Boundary
# =============================================================================

# Default high value threshold for voice transactions (yen)
HIGH_VALUE_THRESHOLD: float = 10000.0

# Timeout for voice confirmation (seconds)
VOICE_CONFIRMATION_TIMEOUT: int = 30
