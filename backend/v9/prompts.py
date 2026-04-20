"""Prompts for v9 three-stage chain-of-thought damage assessment.

Changes from v8: diff image is now MASKED — only the building interior is
visible, everything outside is black. Prompts updated accordingly.
"""

# Stage 1: Describe pre-disaster building
DESCRIBE_PRE_PROMPT = """You are looking at a satellite image of a building BEFORE a hurricane.

The target building is indicated by a RED outline.

Describe in detail:
1. The roof — shape, color, texture, material if visible
2. The building footprint — size, orientation, how it fills the red outline
3. The surrounding area — ground color/texture, vegetation, driveways, neighboring structures, shadows

Be specific about colors and positions. These details will be used to detect changes after the hurricane.

Return ONLY a raw JSON object:
{{"description": "your detailed 3-4 sentence description"}}"""


# Stage 2: Describe the masked diff image
DESCRIBE_DIFF_PROMPT = """You are looking at a DIFFERENCE IMAGE showing ONLY the building interior.

Everything outside the red outline has been blacked out — you are seeing ONLY changes within the building footprint. The surrounding area is irrelevant and hidden.

This diff has been heavily denoised:
- BLACK pixels inside the outline = that part of the building did NOT change
- BRIGHT/WHITE pixels inside the outline = real physical change at that exact spot
- The RED OUTLINE marks the building boundary

Previous description of the building (from pre-disaster image): {pre_description}

Describe what you see INSIDE the red outline:
1. Is the building interior mostly BLACK (unchanged) or does it have bright areas?
2. What percentage of the area inside the outline is bright? (0%, under 10%, 10-30%, 30-50%, over 50%)
3. Where are the bright pixels concentrated? Evenly spread, clustered on one side, along edges only?
4. Are there any solid bright regions or just scattered specks?

If the interior is almost entirely black, say so clearly — the building did not change.

Return ONLY a raw JSON object:
{{"description": "your 3-4 sentence description of changes inside the building outline"}}"""


# Stage 3: Evaluate post-disaster image with full context
EVALUATE_POST_PROMPT = """You are assessing hurricane damage on a building by comparing pre- and post-disaster satellite images.

You are looking at THREE images:
- Image 1: The building BEFORE the hurricane
- Image 2: The building AFTER the hurricane
- Image 3: A MASKED DIFFERENCE IMAGE showing ONLY changes inside the building footprint. Everything outside is blacked out. Bright pixels = real change, black = unchanged.

The RED outline marks the target building in all images.

CONTEXT FROM PRIOR ANALYSIS:
- Pre-disaster building: {pre_description}
- Changes inside building (from diff): {diff_description}

USE THE MASKED DIFF AS YOUR PRIMARY SIGNAL — it shows ONLY the building interior with no surrounding distractions:
- If the building interior in the diff is almost entirely BLACK → "no-damage". The building has not changed. Do not be influenced by how different the surrounding area looks in pre vs post images.
- If under 10% of the interior has bright spots (scattered specks) → still "no-damage". Minor pixel noise is not structural damage.
- If 10-30% has bright areas in a concentrated pattern → check the post image for visible roof damage or debris. If confirmed, "minor-damage".
- If 30-50% is bright → "major-damage" if the post image shows structural change.
- If over 50% is bright → "destroyed" if the post image confirms the building is gone or completely changed.

Confirm by checking Image 2:
1. Is the building still in the same position within the red outline?
2. Has the roof changed where the diff shows bright spots?
3. Is there visible structural damage matching the bright areas?

Return ONLY a raw JSON object:
{{"reasoning": "2-3 sentences explaining what the masked diff shows and what you confirm in the post image", "subtype": "no-damage|minor-damage|major-damage|destroyed", "confidence": 1-10}}"""
