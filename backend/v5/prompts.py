"""Prompts for v5 diverse-input voting.

Three prompt framings per vote:
  1. Standard CoT (balanced)
  2. Conservative ("assume no damage unless clear structural change")
  3. Sensitive ("flag any potential change, even subtle")

Plus the shared baseline prompt from v4.
"""

BASELINE_PROMPT = """You are looking at a satellite image of a building BEFORE a hurricane.

The building is indicated by a RED outline. Describe the building briefly:
1. Roof shape, color, and material (if visible)
2. Building footprint and orientation
3. Surrounding context (driveway, trees, neighboring structures)

Keep your description to 2-3 sentences focused on identifying features that would change if the building were damaged. Return ONLY a raw JSON object:
{"description": "your 2-3 sentence description"}"""


# --- Vote 1: Standard CoT (balanced) ---
CLASSIFY_STANDARD = """You are assessing hurricane damage on a building.

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


# --- Vote 2: Conservative ("assume no damage") ---
CLASSIFY_CONSERVATIVE = """You are assessing hurricane damage on a building. Your job is to be CONSERVATIVE — only classify damage when there is clear, unambiguous structural change.

BASELINE (from pre-disaster image): {baseline}

You are now looking at three images:
- Image 1: The building BEFORE the hurricane (for reference)
- Image 2: The building AFTER the hurricane
- Image 3: A DIFFERENCE IMAGE (bright = real change, dark = unchanged)

The RED outline marks the target building (approximate).

CRITICAL RULES:
- Most buildings survive hurricanes with NO damage. Default assumption is no-damage.
- Lighting changes, shadow angle differences, vegetation color shifts, and slight image alignment offsets are NORMAL between satellite captures — they do NOT indicate damage.
- The difference image may show noise from compression artifacts or seasonal changes. Only large, concentrated bright areas ON the building footprint indicate real structural change.
- Do NOT classify damage unless you can point to a specific physical change (missing roof section, collapsed wall, debris pile, etc.).

Damage levels:
- "no-damage": No clear structural change. This is the DEFAULT — use it unless you have strong evidence otherwise.
- "minor-damage": You can see a specific, localized area of roof damage or a small debris field. The building is structurally intact.
- "major-damage": Large, obvious structural changes — substantial roof loss, visible collapse, heavy debris field on/around the building.
- "destroyed": The building is clearly gone — only slab/foundation, or a debris pile where the building stood.

Return ONLY a raw JSON object:
{{"reasoning": "1-2 sentences", "subtype": "no-damage|minor-damage|major-damage|destroyed", "confidence": 1-10}}"""


# --- Vote 3: Sensitive ("flag subtle changes") ---
CLASSIFY_SENSITIVE = """You are assessing hurricane damage on a building. Your job is to be SENSITIVE — carefully look for any evidence of structural change, even subtle signs.

BASELINE (from pre-disaster image): {baseline}

You are now looking at three images:
- Image 1: The building BEFORE the hurricane (for reference)
- Image 2: The building AFTER the hurricane
- Image 3: A DIFFERENCE IMAGE (bright = real change, dark = unchanged)

The RED outline marks the target building (approximate).

DETECTION GUIDANCE:
- Look carefully at the roof: any change in color, texture, shape, or visible gaps could indicate damage.
- Check the building edges and walls for deformation or collapse.
- Note debris fields, displaced materials, or scour marks around the building.
- Compare the footprint shape — any distortion, rotation, or shrinkage is meaningful.
- The difference image highlights where pixels changed — bright spots on the building are worth investigating.

Damage levels:
- "no-damage": The building and its roof appear identical in pre and post. No structural changes visible.
- "minor-damage": Subtle roof changes (small patches, color shifts suggesting material loss), minor scattered debris.
- "major-damage": Clear structural damage — large roof areas changed, partial collapse visible, heavy debris, footprint deformation.
- "destroyed": Building is gone, replaced by debris/slab, or clearly displaced/washed away.

Return ONLY a raw JSON object:
{{"reasoning": "1-2 sentences", "subtype": "no-damage|minor-damage|major-damage|destroyed", "confidence": 1-10}}"""


def build_classify_prompt(baseline: str, framing: str = "standard") -> str:
    """Build the classification prompt with the baseline description inserted.

    Args:
        baseline: Pre-disaster building description from Stage A.
        framing: One of "standard", "conservative", "sensitive".
    """
    templates = {
        "standard": CLASSIFY_STANDARD,
        "conservative": CLASSIFY_CONSERVATIVE,
        "sensitive": CLASSIFY_SENSITIVE,
    }
    return templates[framing].format(baseline=baseline)
