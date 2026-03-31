"""Prompts for main_v3 multi-stage damage assessment pipeline."""

# Stage 1: Conservative binary gate
# Designed to minimize false positives by being explicit about what is NOT damage.
BINARY_GATE_PROMPT = """You are comparing two satellite images of the SAME building. Image 1 is BEFORE a hurricane. Image 2 is AFTER. Image 3 is a DIFFERENCE IMAGE showing pixel-level changes (bright = change, dark = no change).

Your ONLY task: could this building have sustained physical structural damage?

These are NOT damage (ignore them):
- Lighting/shadow differences (different sun angle between captures)
- Vegetation color changes (seasonal, lighting, or growth)
- Slight image misalignment (building appears shifted by a few pixels)
- Ground color or texture changes unrelated to the structure
- Clouds, haze, or atmospheric differences
- The red outline annotation itself

These ARE damage:
- Roof visibly torn, missing sections, or stripped
- Building footprint deformed, collapsed, or gone
- Debris pile where a building was
- Only foundation/slab remaining
- Building physically displaced or rotated

Use the difference image (Image 3) to guide you — bright areas around the building indicate real change. If the difference image is mostly dark/uniform around the building, the building is likely undamaged.

If there is ANY reasonable suspicion of structural damage, answer YES. A later stage will verify.

Return ONLY a raw JSON object:
{"damaged": true/false}"""

# Stage 2: Chain-of-thought severity classification
# Only invoked on buildings that passed the binary gate.
SEVERITY_PROMPT = """You are assessing hurricane damage severity on a building that has been confirmed to have visible structural damage.

Image 1: BEFORE the hurricane
Image 2: AFTER the hurricane
Image 3: DIFFERENCE IMAGE (bright pixels = change, dark = unchanged)

The RED outline marks the target building. The outline is approximate — the building may be slightly offset in the AFTER image.

Step by step:
1. Describe the building's roof and structure in the BEFORE image.
2. Describe the building's roof and structure in the AFTER image.
3. Describe what the difference image reveals — where are the brightest changes concentrated?
4. Based on the structural changes, classify the damage.

Damage scale:
- "no-damage": No visible structural change. The building looks the same before and after. Differences are only lighting, shadows, or vegetation.
- "minor-damage": Small/localized roof loss, minor debris, slight discoloration. Building is structurally intact.
- "major-damage": Large roof sections missing, partial collapse, heavy debris, clear structural deformation. Building is standing but severely compromised.
- "destroyed": Structure gone, only slab/foundation remains, debris replaces building, or building washed away/displaced.

Return ONLY a raw JSON object:
{"reasoning": "brief 1-2 sentence reasoning", "subtype": "no-damage|minor-damage|major-damage|destroyed", "confidence": 1-10}"""
