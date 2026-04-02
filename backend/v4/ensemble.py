"""Ensemble voting for v4 pipeline. No binary gate — just severity voting."""

from collections import Counter

DAMAGE_SCALE = ["no-damage", "minor-damage", "major-damage", "destroyed"]


def majority_vote_severity(votes: list[str]) -> str:
    """Return the most common severity label. Ties break toward less damage."""
    counts = Counter(votes)
    ranked = sorted(
        counts.items(),
        key=lambda x: (-x[1], DAMAGE_SCALE.index(x[0]) if x[0] in DAMAGE_SCALE else 99),
    )
    return ranked[0][0]


def calibrate_confidence(subtype: str, confidence: float, threshold: float = 7.0) -> str:
    """Downgrade damage classification by one level if confidence is below threshold."""
    if confidence >= threshold:
        return subtype
    idx = DAMAGE_SCALE.index(subtype) if subtype in DAMAGE_SCALE else 0
    downgraded = max(0, idx - 1)
    return DAMAGE_SCALE[downgraded]
