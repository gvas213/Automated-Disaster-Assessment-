"""Ensemble voting for v5 diverse-input pipeline.

Key difference from v4: when votes disagree, default toward less damage
(conservative tiebreak) since false positives are the main problem.
"""

from collections import Counter

DAMAGE_SCALE = ["no-damage", "minor-damage", "major-damage", "destroyed"]


def diverse_vote(votes: list[dict]) -> tuple[str, float]:
    """Aggregate diverse votes into a final classification.

    Each vote is {"subtype": str, "confidence": float, "framing": str}.

    Rules:
      - Unanimous agreement → use that classification.
      - Majority agreement (2/3) → use majority classification.
      - All three disagree → pick the least severe (conservative tiebreak).

    Returns:
        (final_subtype, average_confidence)
    """
    subtypes = [v["subtype"] for v in votes]
    confidences = [v["confidence"] for v in votes]
    avg_conf = sum(confidences) / len(confidences) if confidences else 5.0

    counts = Counter(subtypes)
    if len(counts) == 1:
        # Unanimous
        return subtypes[0], avg_conf

    # Check for majority (2+ agree)
    for subtype, count in counts.most_common():
        if count >= 2:
            return subtype, avg_conf

    # All disagree — conservative tiebreak (least severe)
    indices = []
    for s in subtypes:
        if s in DAMAGE_SCALE:
            indices.append(DAMAGE_SCALE.index(s))
        else:
            indices.append(0)
    return DAMAGE_SCALE[min(indices)], avg_conf


def calibrate_confidence(subtype: str, confidence: float, threshold: float = 7.0) -> str:
    """Downgrade damage classification by one level if confidence is below threshold."""
    if confidence >= threshold:
        return subtype
    idx = DAMAGE_SCALE.index(subtype) if subtype in DAMAGE_SCALE else 0
    downgraded = max(0, idx - 1)
    return DAMAGE_SCALE[downgraded]
