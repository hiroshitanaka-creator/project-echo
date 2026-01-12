"""
Echo Diversity Enforcement - Anti-bias through forced diversity

This module implements "diversity noise" to counter commercial bias in recommendations.
Instead of attacking providers, we force diversity into candidate sets to break monopolies.

Core principle: AI doesn't recommend - it breaks bias and presents comparable choices.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


@dataclass
class Rec:
    """Recommendation with bias/ethics signals."""

    id: str
    title: str
    merchant: str
    category: str
    price: float
    tags: tuple[str, ...]
    utility: float  # 0..1 (quality/relevance)
    ethics: float  # 0..1 (ethical score from Cosmic39)
    bias_risk: float  # 0..1 (affiliate/sponsored suspicion)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Rec:
        """Create Rec from dictionary."""
        return cls(
            id=d.get("id", "unknown"),
            title=d.get("title", ""),
            merchant=d.get("merchant", "unknown"),
            category=d.get("category", "general"),
            price=float(d.get("price", 0)),
            tags=tuple(d.get("tags", [])),
            utility=float(d.get("utility", 0.5)),
            ethics=float(d.get("ethics", 0.5)),
            bias_risk=float(d.get("bias_risk", 0.0)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "merchant": self.merchant,
            "category": self.category,
            "price": self.price,
            "tags": list(self.tags),
            "utility": self.utility,
            "ethics": self.ethics,
            "bias_risk": self.bias_risk,
        }


def bucket_price(price: float) -> str:
    """Bucket price into low/mid/high."""
    if price < 5000:
        return "low"
    if price < 15000:
        return "mid"
    return "high"


def similarity(a: Rec, b: Rec) -> float:
    """
    Compute similarity between two recommendations (0..1).

    Higher similarity = more similar (same merchant, category, price, tags).
    This is used by MMR to enforce diversity.
    """
    sim = 0.0

    # Merchant: strongest signal (avoid monopoly)
    if a.merchant == b.merchant:
        sim += 0.4

    # Category
    if a.category == b.category:
        sim += 0.2

    # Price bucket
    if bucket_price(a.price) == bucket_price(b.price):
        sim += 0.2

    # Tag overlap (Jaccard)
    inter = len(set(a.tags) & set(b.tags))
    union = len(set(a.tags) | set(b.tags)) or 1
    sim += 0.2 * (inter / union)

    return min(sim, 1.0)


def mmr_select(cands: list[Rec], k: int, lam: float = 0.65, beta: float = 1.0, seed: int = 0) -> list[Rec]:
    """
    Maximal Marginal Relevance selection with bias penalty.

    Balances utility (quality), bias risk, and diversity (avoid similar candidates).

    Args:
        cands: Candidate recommendations
        k: Number to select
        lam: Utility weight (1.0=pure utility, 0.0=pure diversity)
        beta: Bias risk penalty coefficient (0.0=ignore bias, 1.0=full penalty)
        seed: Random seed for determinism

    Returns:
        Selected recommendations (ordered by selection)

    Note:
        effective_utility = utility - beta * bias_risk
        This prevents high-bias recommendations from dominating output.
    """
    if not cands:
        return []

    rng = random.Random(seed)
    remaining = cands[:]

    def effective_utility(r: Rec) -> float:
        """Compute utility adjusted for bias risk."""
        u = float(r.utility)
        b = float(getattr(r, "bias_risk", 0.0) or 0.0)
        # Clamp to [0, 1] to prevent negative effective utility
        return max(0.0, min(1.0, u - beta * b))

    # Start with highest effective utility (break ties randomly)
    remaining.sort(key=effective_utility, reverse=True)
    top_utility = effective_utility(remaining[0])
    tops = [r for r in remaining if abs(effective_utility(r) - top_utility) < 1e-9]
    chosen = [rng.choice(tops)]
    remaining = [r for r in remaining if r.id != chosen[0].id]

    # Greedy MMR: pick candidate with best utility/diversity tradeoff
    while remaining and len(chosen) < k:
        best = None
        best_score = -1e9

        for r in remaining:
            # Max similarity to any already chosen
            max_sim = max(similarity(r, c) for c in chosen)

            # MMR score: effective utility minus similarity penalty
            score = lam * effective_utility(r) - (1 - lam) * max_sim

            if score > best_score:
                best_score = score
                best = r

        chosen.append(best)
        remaining = [r for r in remaining if r.id != best.id]

    return chosen


def enforce_min_diversity(
    recs: list[Rec], min_merchants: int = 2, min_price_buckets: int = 2
) -> bool:
    """
    Check if recommendations meet minimum diversity constraints.

    Returns:
        True if diversity constraints are satisfied
    """
    merchants = {r.merchant for r in recs}
    buckets = {bucket_price(r.price) for r in recs}

    return (len(merchants) >= min_merchants) and (len(buckets) >= min_price_buckets)


def diversity_report(recs: list[Rec]) -> dict[str, Any]:
    """
    Generate diversity report for recommendation set.

    Reports:
    - Merchant concentration (monopoly risk)
    - Price bucket distribution
    - Average bias risk
    - Tag diversity
    """
    if not recs:
        return {
            "merchants": 0,
            "price_buckets": 0,
            "merchant_concentration": 1.0,
            "avg_bias_risk": 0.0,
            "unique_tags": 0,
        }

    merchants = [r.merchant for r in recs]
    unique_merchants = set(merchants)
    merchant_concentration = max(merchants.count(m) for m in unique_merchants) / len(recs)

    buckets = {bucket_price(r.price) for r in recs}

    all_tags = set()
    for r in recs:
        all_tags.update(r.tags)

    avg_bias = sum(r.bias_risk for r in recs) / len(recs)

    return {
        "merchants": len(unique_merchants),
        "price_buckets": len(buckets),
        "merchant_concentration": merchant_concentration,
        "avg_bias_risk": avg_bias,
        "unique_tags": len(all_tags),
    }


def commercial_bias_score(recs: list[Rec]) -> dict[str, Any]:
    """
    Compute commercial bias score with evidence (receipt).

    Returns weighted evidence of commercial bias:
    - affiliate_risk: Avg bias_risk in recommendations
    - merchant_concentration: Single merchant dominance
    - price_concentration: Single price tier dominance
    - source_diversity: Lack of diverse sources
    - overall_bias_score: Weighted sum (0..1, higher = more biased)
    - evidence: Detailed breakdown for verification (receipt)
    """
    if not recs:
        return {
            "affiliate_risk": 0.0,
            "merchant_concentration": 0.0,
            "price_concentration": 0.0,
            "source_diversity": 1.0,
            "overall_bias_score": 0.0,
            "evidence": {
                "affiliate_evidence": [],
                "merchant_distribution": {},
                "price_bucket_counts": {"low": 0, "mid": 0, "high": 0},
                "total_recommendations": 0,
            },
        }

    # Affiliate risk (average bias_risk)
    affiliate_risk = sum(r.bias_risk for r in recs) / len(recs)

    # Merchant concentration (Herfindahl-Hirschman Index style)
    merchants = [r.merchant for r in recs]
    unique_merchants = set(merchants)
    merchant_shares = [merchants.count(m) / len(recs) for m in unique_merchants]
    merchant_concentration = sum(s**2 for s in merchant_shares)

    # Price concentration (single price bucket dominance)
    buckets = [bucket_price(r.price) for r in recs]
    unique_buckets = set(buckets)
    bucket_shares = [buckets.count(b) / len(recs) for b in unique_buckets]
    price_concentration = sum(s**2 for s in bucket_shares)

    # Source diversity (inverse of merchant count, normalized)
    source_diversity = min(len(unique_merchants) / len(recs), 1.0)

    # Overall bias score (weighted sum)
    # Weights: affiliate=0.4, merchant=0.3, price=0.2, source_diversity=0.1
    overall_bias_score = (
        0.4 * affiliate_risk
        + 0.3 * merchant_concentration
        + 0.2 * price_concentration
        + 0.1 * (1 - source_diversity)
    )

    # Build detailed evidence (receipt)
    # This enables verification: each aggregate score can be reconstructed from evidence

    # 1. Affiliate evidence: bias_risk per recommendation
    affiliate_evidence = [
        {
            "rec_id": r.id,
            "title": r.title,
            "bias_risk": r.bias_risk,
        }
        for r in recs
    ]

    # 2. Merchant distribution: count and share per merchant
    merchant_distribution = {}
    for m in unique_merchants:
        count = merchants.count(m)
        share = count / len(recs)
        merchant_distribution[m] = {
            "count": count,
            "share": share,
            "share_squared": share**2,  # For HHI verification
        }

    # 3. Price bucket counts
    price_bucket_counts = {
        "low": buckets.count("low"),
        "mid": buckets.count("mid"),
        "high": buckets.count("high"),
    }

    # 4. Price bucket shares (for HHI verification)
    price_bucket_shares = {}
    for b in ["low", "mid", "high"]:
        count = price_bucket_counts[b]
        if count > 0:
            share = count / len(recs)
            price_bucket_shares[b] = {
                "count": count,
                "share": share,
                "share_squared": share**2,
            }

    # 5. Price evidence: price per recommendation (for bucket verification)
    price_evidence = [
        {
            "rec_id": r.id,
            "price": r.price,
            "bucket": bucket_price(r.price),
        }
        for r in recs
    ]

    evidence = {
        "affiliate_evidence": affiliate_evidence,
        "merchant_distribution": merchant_distribution,
        "price_bucket_counts": price_bucket_counts,
        "price_bucket_shares": price_bucket_shares,
        "price_evidence": price_evidence,
        "total_recommendations": len(recs),
        "unique_merchants": len(unique_merchants),
    }

    return {
        "affiliate_risk": affiliate_risk,
        "merchant_concentration": merchant_concentration,
        "price_concentration": price_concentration,
        "source_diversity": source_diversity,
        "overall_bias_score": overall_bias_score,
        "evidence": evidence,
    }


def recommendation_boundary(
    bias_original: dict[str, Any],
    bias_final: dict[str, Any],
    diversity_original: dict[str, Any],
    diversity_final: dict[str, Any],
) -> dict[str, Any]:
    """
    Compute responsibility boundary for recommendations.

    Decision logic (PRIORITY ORDER - conservative gate):
    1. FIRST: If bias_final >= 0.6 (high bias) → BLOCK (safety first)
    2. THEN: If bias_original < 0.4 (low bias originally) → allow without confirmation
    3. THEN: If bias_final < 0.4 AND improvement > 0.2 → allow with confirmation
    4. ELSE: Medium bias → allow with confirmation

    Returns:
        responsibility_boundary with execution_allowed, requires_human_confirm, reasons
    """
    bias_orig = bias_original["overall_bias_score"]
    bias_fin = bias_final["overall_bias_score"]
    bias_improvement = bias_orig - bias_fin

    reasons = []
    execution_allowed = False
    requires_human_confirm = True

    # Canonical thresholds (from threat_model.md)
    HIGH_BIAS = 0.6
    MEDIUM_BIAS = 0.4
    SIGNIFICANT_IMPROVEMENT = 0.2

    # PRIORITY 1: High bias final → BLOCK (conservative gate)
    # This check MUST come first to prevent auto-allowing high-bias results
    if bias_fin >= HIGH_BIAS:
        # High bias even after diversification - block
        execution_allowed = False
        requires_human_confirm = True
        reasons.append("high_bias_after_diversification")
    # PRIORITY 2: Low bias originally → allow without confirmation
    elif bias_orig < MEDIUM_BIAS:
        # Low bias originally - allow
        execution_allowed = True
        requires_human_confirm = False
        reasons.append("low_bias_originally")
    # PRIORITY 3: Significant improvement → allow with confirmation
    elif bias_fin < MEDIUM_BIAS and bias_improvement > SIGNIFICANT_IMPROVEMENT:
        # Bias improved significantly - allow with confirmation
        execution_allowed = True
        requires_human_confirm = True
        reasons.append("bias_improved_significantly")
    # PRIORITY 4: Medium bias → allow with confirmation
    else:
        # Medium bias - allow with confirmation
        execution_allowed = True
        requires_human_confirm = True
        reasons.append("medium_bias_requires_confirmation")

    # Check merchant concentration
    if diversity_final["merchant_concentration"] > 0.6:
        reasons.append("merchant_monopoly_detected")
        requires_human_confirm = True

    # Check price diversity
    if diversity_final["price_buckets"] < 2:
        reasons.append("insufficient_price_diversity")
        requires_human_confirm = True

    return {
        "execution_allowed": execution_allowed,
        "requires_human_confirm": requires_human_confirm,
        "ai_recommends": False,  # Policy: never recommend
        "liability_mode": "audit-only",
        "reasons": reasons,
        "signals": {
            "bias_original": bias_orig,
            "bias_final": bias_fin,
            "bias_improvement": bias_improvement,
            "merchants_final": diversity_final["merchants"],
            "price_buckets_final": diversity_final["price_buckets"],
        },
    }


def diversify_with_mmr(
    original: list[Rec],
    counterfactuals: list[Rec],
    k: int = 5,
    lam: float = 0.65,
    beta: float = 1.0,
    min_merchants: int = 2,
    min_price_buckets: int = 2,
) -> dict[str, Any]:
    """
    Diversify recommendation set with MMR and compute responsibility boundary.

    Full execution gate: audit → diversify → boundary decision → final output.

    Args:
        original: Original recommendation set
        counterfactuals: Alternative recommendations for diversification
        k: Number of recommendations to select
        lam: Utility weight (1.0=pure utility, 0.0=pure diversity)
        beta: Bias risk penalty coefficient (0.0=ignore bias, 1.0=full penalty)
        min_merchants: Minimum number of distinct merchants
        min_price_buckets: Minimum number of distinct price tiers

    Returns:
        Complete audit result with bias scores, diversity reports, and responsibility boundary
    """
    # Compute bias scores
    bias_original = commercial_bias_score(original)

    all_candidates = original + counterfactuals

    # Pre-filter: Remove low effective_utility and high-bias candidates (safety gate)
    # Compute effective utility for each candidate
    def effective_utility(r: Rec) -> float:
        u = float(r.utility)
        b = float(getattr(r, "bias_risk", 0.0) or 0.0)
        return max(0.0, min(1.0, u - beta * b))

    # Filter out candidates with effective_utility < 0.1 (too biased/low quality)
    MIN_EFFECTIVE_UTILITY = 0.1
    filtered_candidates = [
        r for r in all_candidates if effective_utility(r) >= MIN_EFFECTIVE_UTILITY
    ]

    # If enough clean candidates exist (>=k), also filter high-bias (>0.7)
    # This ensures bias removal takes priority over merchant diversity
    HIGH_BIAS_THRESHOLD = 0.7
    if len(filtered_candidates) >= k:
        high_quality = [r for r in filtered_candidates if r.bias_risk <= HIGH_BIAS_THRESHOLD]
        if len(high_quality) >= k:
            filtered_candidates = high_quality

    # If filtering removed too many candidates, lower threshold to 0.0 (no filtering)
    if len(filtered_candidates) < k:
        filtered_candidates = [r for r in all_candidates if effective_utility(r) > 0.0]
        # If still not enough, use all (defensive fallback)
        if len(filtered_candidates) < k:
            filtered_candidates = all_candidates

    # Try MMR with default lambda and beta (on filtered candidates)
    selected = mmr_select(filtered_candidates, k=k, lam=lam, beta=beta)

    # If diversity constraints not met, reduce lambda (favor diversity)
    attempt = 0
    while not enforce_min_diversity(selected, min_merchants, min_price_buckets):
        attempt += 1
        if attempt > 5 or lam <= 0.1:
            # Can't satisfy constraints even with pure diversity
            break
        lam *= 0.8  # Reduce utility weight
        selected = mmr_select(filtered_candidates, k=k, lam=lam, beta=beta)

    # Compute final bias and diversity
    bias_final = commercial_bias_score(selected)
    diversity_orig = diversity_report(original)
    diversity_fin = diversity_report(selected)

    # Compute responsibility boundary
    boundary = recommendation_boundary(bias_original, bias_final, diversity_orig, diversity_fin)

    return {
        "original_set": [r.to_dict() for r in original],
        "counterfactual_set": [r.to_dict() for r in counterfactuals],
        "final_set": [r.to_dict() for r in selected],
        "commercial_bias_original": bias_original,
        "commercial_bias_final": bias_final,
        "diversity_report_original": diversity_orig,
        "diversity_report_final": diversity_fin,
        "responsibility_boundary": boundary,
        "mmr_lambda": lam,
        "diversity_enforced": enforce_min_diversity(selected, min_merchants, min_price_buckets),
    }
