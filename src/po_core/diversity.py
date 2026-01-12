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


def mmr_select(cands: list[Rec], k: int, lam: float = 0.65, seed: int = 0) -> list[Rec]:
    """
    Maximal Marginal Relevance selection.

    Balances utility (quality) and diversity (avoid similar candidates).

    Args:
        cands: Candidate recommendations
        k: Number to select
        lam: Utility weight (1.0=pure utility, 0.0=pure diversity)
        seed: Random seed for determinism

    Returns:
        Selected recommendations (ordered by selection)
    """
    if not cands:
        return []

    rng = random.Random(seed)
    remaining = cands[:]

    # Start with highest utility (break ties randomly)
    remaining.sort(key=lambda r: r.utility, reverse=True)
    top_utility = remaining[0].utility
    tops = [r for r in remaining if abs(r.utility - top_utility) < 1e-9]
    chosen = [rng.choice(tops)]
    remaining = [r for r in remaining if r.id != chosen[0].id]

    # Greedy MMR: pick candidate with best utility/diversity tradeoff
    while remaining and len(chosen) < k:
        best = None
        best_score = -1e9

        for r in remaining:
            # Max similarity to any already chosen
            max_sim = max(similarity(r, c) for c in chosen)

            # MMR score: utility minus similarity penalty
            score = lam * r.utility - (1 - lam) * max_sim

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


def diversify_with_mmr(
    original: list[Rec],
    counterfactuals: list[Rec],
    k: int = 5,
    lam: float = 0.65,
    min_merchants: int = 2,
    min_price_buckets: int = 2,
) -> dict[str, Any]:
    """
    Diversify recommendation set with MMR.

    If initial selection doesn't meet diversity constraints, reduces lambda
    (favors diversity over utility) and retries.

    Returns:
        Dictionary with original_set, counterfactual_set, final_set, diversity_report
    """
    all_candidates = original + counterfactuals

    # Try MMR with default lambda
    selected = mmr_select(all_candidates, k=k, lam=lam)

    # If diversity constraints not met, reduce lambda (favor diversity)
    attempt = 0
    while not enforce_min_diversity(selected, min_merchants, min_price_buckets):
        attempt += 1
        if attempt > 5 or lam <= 0.1:
            # Can't satisfy constraints even with pure diversity
            break
        lam *= 0.8  # Reduce utility weight
        selected = mmr_select(all_candidates, k=k, lam=lam)

    return {
        "original_set": [r.to_dict() for r in original],
        "counterfactual_set": [r.to_dict() for r in counterfactuals],
        "final_set": [r.to_dict() for r in selected],
        "diversity_report_original": diversity_report(original),
        "diversity_report_final": diversity_report(selected),
        "mmr_lambda": lam,
        "diversity_enforced": enforce_min_diversity(selected, min_merchants, min_price_buckets),
    }
