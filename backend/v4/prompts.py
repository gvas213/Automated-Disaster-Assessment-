"""Prompts for v4 two-stage chain-of-thought damage assessment.

Research-inspired approach: first describe pre-disaster baseline,
then compare post-disaster against that baseline with diff image guidance.
No binary gate — single-pass classification with all 4 damage levels.
"""

# Stage A: Describe the pre-disaster building to establish baseline
BASELINE_PROMPT = """You are looking at a satellite image of a building BEFORE a hurricane.

The building is indicated by a RED outline. Describe the building briefly:
1. Roof shape, color, and material (if visible)
2. Building footprint and orientation
3. Surrounding context (driveway, trees, neighboring structures)

Keep your description to 2-3 sentences focused on identifying features that would change if the building were damaged. Return ONLY a raw JSON object:
{"description": "your 2-3 sentence description"}"""

# Stage B: Compare post-disaster + diff image against the baseline description
CLASSIFY_PROMPT_TEMPLATE = """You are assessing hurricane damage on a building.

BASELINE (from pre-disaster image): {baseline}

You are now looking at three images:
- Image 1: The building BEFORE the hurricane (for reference)
- Image 2: The building AFTER the hurricane
- Image 3: A DIFFERENCE IMAGE computed by subtracting pre from post (bright pixels = real physical change, dark pixels = nothing changed)

The RED outline marks the target building. The outline is approximate — the building may be slightly offset in the AFTER image.

IMPORTANT — use the difference image to calibrate your assessment:
- If the difference image is mostly DARK around the building → the building likely has no damage or only minor damage, regardless of how the raw images look. Dark means the pixels didn't change.
- If the difference image shows BRIGHT areas on/around the building → those are real physical changes worth examining.
- Brightness OUTSIDE the building (vegetation, roads) is irrelevant — focus on the building footprint.

Step by step:
1. Compare Image 2 to the baseline description. What specific structural changes do you see?
2. Check the difference image. Does it confirm or contradict what you see?
3. Classify the damage.

Damage levels:
- "no-damage": Building looks structurally the same. Roof intact, footprint unchanged. Diff image dark around building.
- "minor-damage": Small localized roof changes, minor debris. Building structurally intact. Diff image shows small bright patches on building.
- "major-damage": Large roof sections missing, partial collapse, heavy debris, structural deformation. Diff image shows large bright areas on building footprint.
- "destroyed": Structure gone, slab only, debris replaces building, or building washed away. Diff image shows building footprint completely changed.

Return ONLY a raw JSON object:
{{"reasoning": "1-2 sentences", "subtype": "no-damage|minor-damage|major-damage|destroyed", "confidence": 1-10}}"""


def build_classify_prompt(baseline_description: str) -> str:
    """Insert the baseline description into the classification prompt."""
    return CLASSIFY_PROMPT_TEMPLATE.format(baseline=baseline_description)
