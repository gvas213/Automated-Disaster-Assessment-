"""Prompts for v7 three-stage chain-of-thought damage assessment.

Same 3-stage structure as v6 but prompts updated to leverage the
thresholded diff image: dark = definitely no change, bright = real change.
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

This diff image has been DENOISED: small differences from lighting, compression, and alignment have been removed. What remains is ONLY real physical change:
- BLACK pixels = absolutely nothing changed there
- BRIGHT pixels = real physical change occurred at that exact location

The RED outline marks the target building.

Previous description of the building (from pre-disaster image): {pre_description}

Describe what the diff image shows:
1. Is the area inside the red outline mostly BLACK (no change) or does it have bright spots?
2. If bright spots exist — where exactly? On the roof? Along the edges? Across the entire footprint?
3. How much of the building footprint has bright pixels? A tiny fraction, partial coverage, or most of it?
4. Is there a bright pattern that has shifted relative to the red outline? (indicates building displacement)
5. Are there bright spots in the surrounding area immediately outside the outline?

If the diff is mostly black inside and around the outline, say so clearly — it means the building did not change.

Return ONLY a raw JSON object:
{{"description": "your 3-4 sentence description of what the diff image shows"}}"""


# Stage 3: Evaluate post-disaster image with full context
EVALUATE_POST_PROMPT = """You are assessing hurricane damage on a building by comparing pre- and post-disaster satellite images.

You are looking at THREE images:
- Image 1: The building BEFORE the hurricane
- Image 2: The building AFTER the hurricane
- Image 3: A DENOISED DIFFERENCE IMAGE — only real physical changes show up as bright pixels. Black = nothing changed.

The RED outline marks the target building in all images.

CONTEXT FROM PRIOR ANALYSIS:
- Pre-disaster building: {pre_description}
- Diff image analysis: {diff_description}

THE DIFF IMAGE IS YOUR MOST RELIABLE SIGNAL. Use it as follows:
- If the diff image is mostly BLACK inside the building outline → the building has NOT changed. Classify as "no-damage" regardless of how different the raw images may look (lighting/angle differences are normal).
- If the diff shows SMALL bright patches on part of the roof → minor localized damage.
- If the diff shows LARGE bright areas covering much of the building → major structural change.
- If the diff shows the ENTIRE footprint is bright or the bright pattern has shifted from the outline → building destroyed or displaced.

Now confirm by checking Image 2 against the pre-disaster description:
1. Is the building still inside the red outline, or has it shifted?
2. Has the roof color or texture changed where the diff shows bright spots?
3. Is there debris, ground color change, or missing vegetation where the diff shows changes?

DAMAGE CLASSIFICATION:
- "no-damage": Diff mostly black around building. Building looks the same.
- "minor-damage": Diff shows small bright patches. Minor roof changes or debris visible in post image.
- "major-damage": Diff shows large bright areas on building. Major roof loss, collapse, or heavy debris visible.
- "destroyed": Diff shows entire footprint changed. Building gone, displaced, or replaced by debris.

Return ONLY a raw JSON object:
{{"reasoning": "2-3 sentences explaining what the diff shows and what you see in the post image", "subtype": "no-damage|minor-damage|major-damage|destroyed", "confidence": 1-10}}"""
