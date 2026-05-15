"""Prompts for v_client_1 three-stage chain-of-thought damage assessment.

Images are individual building crops — the whole image is the building.
No polygon masking or red outline; the diff image covers the full crop.
"""

# Stage 1: Describe pre-disaster building
DESCRIBE_PRE_PROMPT = """You are looking at a satellite image of a building BEFORE a hurricane.

The image shows a single building crop.

Describe in detail:
1. The roof — shape, color, texture, material if visible
2. The building footprint — size and orientation
3. The surrounding area — ground color/texture, vegetation, driveways, neighboring structures, shadows

Be specific about colors and positions. These details will be used to detect changes after the hurricane.

Return ONLY a raw JSON object:
{{"description": "your detailed 3-4 sentence description"}}"""


# Stage 2: Describe the diff image
DESCRIBE_DIFF_PROMPT = """You are looking at a DIFFERENCE IMAGE between a pre-disaster and post-disaster satellite image of a single building.

This diff has been heavily denoised:
- BLACK pixels = that area did NOT change
- BRIGHT/WHITE pixels = real physical change at that exact spot

Previous description of the building (from pre-disaster image): {pre_description}

Describe what you see:
1. Is the image mostly BLACK (unchanged) or does it have bright areas?
2. What percentage of the image is bright? (0%, under 10%, 10-30%, 30-50%, over 50%)
3. Where are the bright pixels concentrated? Evenly spread, clustered on one side, along edges only?
4. Are there any solid bright regions or just scattered specks?

If the image is almost entirely black, say so clearly — the building did not change.

Return ONLY a raw JSON object:
{{"description": "your 3-4 sentence description of changes"}}"""


# Stage 3: Evaluate post-disaster image with full context
COST_PROMPT = """You are a disaster recovery cost estimator for a building damaged by a hurricane.

Estimate the repair cost in USD based on the following:

Damage classification: {damage_type}
Building description (pre-disaster): {pre_description}
Damage reasoning: {reasoning}

Reference ranges for typical hurricane damage in the US:
- minor-damage: $2,000 - $20,000 (roof patching, minor debris removal, small repairs)
- major-damage: $20,000 - $150,000 (large roof replacement, partial structural rebuild, significant interior damage)
- destroyed: $150,000 - $500,000+ (full rebuild from foundation)

Pick a single specific USD integer within (or near) the range that best fits the building's apparent size, type, and materials.

Return ONLY a raw JSON object:
{{"cost_usd": <integer>, "cost_reasoning": "one short sentence"}}"""


EVALUATE_POST_PROMPT = """You are assessing hurricane damage on a building by comparing pre- and post-disaster satellite images.

You are looking at THREE images:
- Image 1: The building BEFORE the hurricane
- Image 2: The building AFTER the hurricane
- Image 3: A DIFFERENCE IMAGE showing where pixels changed. Bright pixels = real change, black = unchanged.

CONTEXT FROM PRIOR ANALYSIS:
- Pre-disaster building: {pre_description}
- Changes detected in diff: {diff_description}

USE THE DIFF AS YOUR PRIMARY SIGNAL:
- If the diff is almost entirely BLACK → "no-damage". The building has not changed.
- If under 10% has bright spots (scattered specks) → still "no-damage". Minor pixel noise is not structural damage.
- If 10-30% has bright areas in a concentrated pattern → check the post image for visible roof damage or debris. If confirmed, "minor-damage".
- If 30-50% is bright → "major-damage" if the post image shows structural change.
- If over 50% is bright → "destroyed" if the post image confirms the building is gone or completely changed.

Confirm by checking Image 2:
1. Is the building still present and in the same position?
2. Has the roof changed where the diff shows bright spots?
3. Is there visible structural damage matching the bright areas?

Return ONLY a raw JSON object:
{{"reasoning": "2-3 sentences explaining what the diff shows and what you confirm in the post image", "subtype": "no-damage|minor-damage|major-damage|destroyed", "confidence": 1-10}}"""
