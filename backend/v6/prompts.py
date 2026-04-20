"""Prompts for v6 three-stage chain-of-thought damage assessment.

Stage 1: Describe the pre-disaster building (what does it look like now?)
Stage 2: Describe the diff image (what actually changed between captures?)
Stage 3: Evaluate the post-disaster image using stages 1+2 as context, classify damage.

No gate, no voting. One clean pass per building.
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
DESCRIBE_DIFF_PROMPT = """You are looking at a DIFFERENCE IMAGE computed by subtracting a pre-disaster satellite image from a post-disaster satellite image of the same area.

How to read this image:
- DARK/BLACK pixels = nothing changed between pre and post
- BRIGHT/WHITE pixels = something physically changed at that location
- The RED outline marks where the target building is

Previous description of the building (from pre-disaster image): {pre_description}

Describe what the diff image shows:
1. Is the area inside the red outline mostly dark (unchanged) or does it have bright regions?
2. If bright regions exist inside the outline — where are they? (roof area, edges, entire footprint?)
3. Has the bright pattern shifted or moved relative to the red outline? (this could mean the building displaced)
4. What about the area immediately surrounding the outline — any bright changes in the ground, vegetation, or neighboring structures?

Be factual about what you see. Do not guess at damage yet.

Return ONLY a raw JSON object:
{{"description": "your 3-4 sentence description of changes visible in the diff image"}}"""


# Stage 3: Evaluate post-disaster image with full context
EVALUATE_POST_PROMPT = """You are assessing hurricane damage on a building by comparing pre-disaster and post-disaster satellite images.

You are looking at THREE images:
- Image 1: The building BEFORE the hurricane
- Image 2: The building AFTER the hurricane
- Image 3: A DIFFERENCE IMAGE (bright = changed, dark = unchanged)

The RED outline marks the target building in all images.

CONTEXT FROM ANALYSIS:
- Pre-disaster building: {pre_description}
- Changes detected in diff image: {diff_description}

Now examine Image 2 (the AFTER image) carefully. Compare it to the pre-disaster description and the diff analysis:

KEY THINGS TO CHECK:
1. Is the building still inside the red outline, or has it shifted/moved? If the roof that was inside the outline is now partially or fully outside it, that indicates displacement.
2. Has the roof color or texture changed? A different color/texture where the roof was = roof damage or loss.
3. Has the surrounding ground color changed? New brown/grey areas, debris scatter, mud/sediment, or missing vegetation compared to before.
4. Is the building footprint the same shape and size? Shrinkage or distortion = collapse.
5. Is the building simply gone? Only slab/foundation visible where building was.

DAMAGE CLASSIFICATION:
- "no-damage": Building looks the same as before. Roof intact, same position in outline, surroundings similar.
- "minor-damage": Small changes — slight roof discoloration, minor debris nearby, small vegetation loss. Building structurally intact and in same position.
- "major-damage": Significant changes — large roof sections different color/missing, building partially shifted from outline, heavy debris, major ground color change around building, partial collapse.
- "destroyed": Building gone or completely changed — slab only, building fully displaced from outline, debris field replaces structure, footprint unrecognizable.

Return ONLY a raw JSON object:
{{"reasoning": "2-3 sentences explaining what you see and how it compares to the pre-disaster state", "subtype": "no-damage|minor-damage|major-damage|destroyed", "confidence": 1-10}}"""
