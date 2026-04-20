"""Prompts for v8 three-stage chain-of-thought damage assessment.

Changes from v7:
- Diff image now has a red outline — prompts mention it
- Prompts emphasize: only assess damage INSIDE the red outline
- Higher threshold means diff is cleaner — prompts reinforce trust in it
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


# Stage 2: Describe the diff image
DESCRIBE_DIFF_PROMPT = """You are looking at a DIFFERENCE IMAGE between pre- and post-hurricane satellite captures.

This diff image has been heavily denoised: only significant physical changes appear as bright pixels. Minor variations from lighting, compression, and alignment have been completely removed.
- BLACK pixels = nothing changed
- BRIGHT/WHITE pixels = real physical change at that location
- The RED OUTLINE marks the target building — focus ONLY on what's inside this outline

Previous description of the building (from pre-disaster image): {pre_description}

Describe what the diff image shows INSIDE the red outline:
1. Is the area inside the red outline mostly BLACK (no change) or does it have bright spots?
2. If bright spots exist inside the outline — where are they? On the roof? Edges? Entire footprint?
3. What proportion of the area inside the outline has bright pixels? Almost none, a small fraction, roughly half, or most of it?
4. Has a bright pattern shifted or moved relative to the red outline? (indicates building displacement)

Ignore any brightness OUTSIDE the red outline — we are only assessing the building inside it.

If the area inside the outline is mostly black, say so clearly — it means the building did not change.

Return ONLY a raw JSON object:
{{"description": "your 3-4 sentence description of what the diff shows inside the red outline"}}"""


# Stage 3: Evaluate post-disaster image with full context
EVALUATE_POST_PROMPT = """You are assessing hurricane damage on a building by comparing pre- and post-disaster satellite images.

You are looking at THREE images:
- Image 1: The building BEFORE the hurricane
- Image 2: The building AFTER the hurricane
- Image 3: A DENOISED DIFFERENCE IMAGE with a RED OUTLINE marking the target building. Only real physical changes appear as bright pixels. Black = no change.

IMPORTANT: You are ONLY assessing damage to the building INSIDE the red outline. Ignore changes outside the outline.

CONTEXT FROM PRIOR ANALYSIS:
- Pre-disaster building: {pre_description}
- Diff image analysis: {diff_description}

THE DIFF IMAGE IS YOUR MOST RELIABLE SIGNAL:
- If the diff is mostly BLACK inside the red outline → the building has NOT changed. Classify as "no-damage" even if the raw pre/post images look slightly different (lighting and angle differences between satellite captures are normal and have been filtered out).
- If the diff shows SMALL bright patches inside the outline → check the post image to confirm minor roof damage or debris.
- If the diff shows LARGE bright areas inside the outline → major structural change confirmed.
- If the diff shows the ENTIRE area inside the outline is bright or the bright pattern has shifted away from the outline → building destroyed or displaced.

Confirm by checking Image 2 against the pre-disaster description:
1. Is the building still centered in the red outline, or has it shifted?
2. Has the roof color or texture changed where the diff shows bright spots?
3. Is there visible structural damage matching the diff's bright areas?

DAMAGE CLASSIFICATION:
- "no-damage": Diff mostly black inside outline. Building unchanged.
- "minor-damage": Diff shows small bright patches inside outline. Minor roof changes or small debris visible in post image.
- "major-damage": Diff shows large bright areas inside outline. Major roof loss, collapse, or heavy debris visible.
- "destroyed": Diff shows entire outline area is bright. Building gone, displaced, or replaced by debris.

Return ONLY a raw JSON object:
{{"reasoning": "2-3 sentences explaining what the diff shows inside the outline and what you see in the post image", "subtype": "no-damage|minor-damage|major-damage|destroyed", "confidence": 1-10}}"""
