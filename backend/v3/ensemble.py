"""Ensemble voting and confidence calibration for VLM predictions."""

from collections import Counter

DAMAGE_SCALE = ["no-damage", "minor-damage", "major-damage", "destroyed"]


def majority_vote_binary(votes: list[bool]) -> bool:
    """Return True (damaged) if ANY vote says damaged. Loose filter — stage 2 verifies."""
    return any(votes)


def majority_vote_severity(votes: list[str]) -> str:
    """Return the most common severity label. Ties break toward less damage."""
    counts = Counter(votes)
    # Sort by count descending, then by damage scale ascending (less damage wins ties)
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
