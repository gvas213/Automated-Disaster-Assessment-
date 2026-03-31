DEFAULT_PROMPT = """You are given two cropped satellite images of the same area. The first image is BEFORE a natural disaster. The second image is AFTER the disaster.

The structure to assess is highlighted with a RED outline in both images. Focus on the building/structure inside the red outline and compare its condition before and after.

Return ONLY a raw JSON object (no markdown, no explanation) with these fields:
- "feature_type": the type of structure (e.g. "building", "lot", "land", "farm", "road", "bridge")
- "subtype": the damage level, one of: "no-damage", "minor-damage", "major-damage", "destroyed"

Example:
{"feature_type": "building", "subtype": "minor-damage"}
"""

PROMPT_V1 = """You are given two cropped satellite images of the same area. The first image is BEFORE a HURRICANE. The second image is AFTER the hurricane.

The structure to assess is highlighted with a RED outline in both images. Compare the condition of the same real-world structure before vs after. Note: in the AFTER image, the structure may be partially outside the red outline (shifted/misaligned crop) or missing from within the outline; this can indicate major damage or destruction. Use nearby context (driveways, shadows, roof fragments, debris field) to track the same structure.

Classify hurricane-related damage using these priors:
- No-damage: roof shape/footprint unchanged, no debris or scouring, surroundings similar.
- Minor-damage: small roof changes, minor debris, slight discoloration, limited treefall near the structure.
- Major-damage: large roof loss, exposed interior, partial collapse, heavy debris, clear structural deformation.
- Destroyed: structure footprint largely gone, only slab/foundation remains, debris pile replaces building, or the building is displaced/washed away.

Return ONLY a raw JSON object (no markdown, no explanation) with these fields:
- "feature_type": the type of structure (e.g. "building", "lot", "land", "farm", "road", "bridge")
- "subtype": one of: "no-damage", "minor-damage", "major-damage", "destroyed"

Example:
{"feature_type": "building", "subtype": "minor-damage"}
"""

PROMPT_V2 = """You are given two cropped satellite images of the same area. Image 1 is BEFORE a HURRICANE. Image 2 is AFTER the hurricane.

The RED outline indicates the target structure area, but the AFTER crop/registration may be offset: the same building may have shifted partially or entirely outside the red outline, or the outline may now cover debris/empty ground. Treat this as a valid signal and use surrounding anchors (roads, lot boundaries, vegetation lines, neighboring roofs) to identify the same structure.

Use hurricane damage heuristics (FEMA-style visual cues):
- Wind: missing/peeled roof sections, roof color/texture change, scattered roof panels.
- Storm surge/flooding: scour marks, sediment staining, waterlines, debris deposits, washed-out lots.
- Collapse/displacement: footprint distortion, building moved/rotated, slab-only, debris field.

Assign:
- no-damage: footprint/roof intact and consistent.
- minor-damage: limited roof damage or small debris near roof.
- major-damage: substantial roof loss, partial collapse, major deformation, heavy debris.
- destroyed: footprint gone or replaced by debris/slab; structure not standing; evidence of wash-away/displacement.

Return ONLY a raw JSON object:
{"feature_type": "...", "subtype": "..."}"""

PROMPT_V3 = """You are given two cropped satellite images of the same area. The first is BEFORE a HURRICANE. The second is AFTER the hurricane.

The target is the structure associated with the RED outline. The outline is approximate: in the AFTER image the building may no longer be centered or even inside the outline due to (a) crop misalignment or (b) hurricane damage/displacement. If the outlined region becomes empty, shows slab-only, or contains a debris pile while the building appears shifted nearby, treat that as major damage or destroyed depending on severity.

Decision rules (prioritize strongest evidence):
1) If roof/footprint largely intact -> no-damage.
2) If roof shows small localized loss/patchiness but footprint stable -> minor-damage.
3) If large roof sections missing, footprint deformed, interior exposed, or heavy debris -> major-damage.
4) If structure is gone, slab/foundation remains, debris replaces it, or building washed/displaced -> destroyed.

Return ONLY raw JSON with:
- "feature_type"
- "subtype" in {"no-damage","minor-damage","major-damage","destroyed"}"""

PROMPT_V4 = """You are given two cropped satellite images of the same area. Image A is BEFORE a HURRICANE. Image B is AFTER the hurricane.

Assess the same real-world structure indicated by the RED outline, but do NOT assume the structure will still be fully inside the outline in Image B. The building may be offset, partially outside, or missing; use context to track it (adjacent buildings, road edges, driveway positions, tree lines).

FEMA-inspired priors for hurricane impacts:
- Expect roof damage first (missing shingles/panels), then partial structural collapse, then slab-only/wash-away in severe surge.
- Flood/surge often leaves sediment stains, scoured ground, debris lines; wind leaves scattered debris and roof fragmentation patterns.

Output ONLY a raw JSON object:
- "feature_type": choose best match (usually "building" unless clearly road/bridge/lot/etc.)
- "subtype": "no-damage" | "minor-damage" | "major-damage" | "destroyed"

Example:
{"feature_type":"building","subtype":"major-damage"}"""

FEATURE_DETECTION_PROMPT = """You are given two cropped satellite images of the same area. Image 1 is BEFORE a HURRICANE. Image 2 is AFTER the hurricane.

The RED outline indicates the target structure. The outline is approximate — in the AFTER image the building may be offset or missing due to crop misalignment or actual damage. Use surrounding context (roads, driveways, neighboring roofs, tree lines) to track the same structure.

Examine both images and answer each of the following questions with true or false. Return ONLY a raw JSON object (no markdown, no explanation).

{
  "roof_intact": true/false,           // Is the roof shape/texture largely unchanged between before and after?
  "roof_partial_loss": true/false,     // Are there small/localized sections of the roof missing or peeled?
  "roof_major_loss": true/false,       // Is a large portion (>50%) of the roof missing or stripped?
  "building_displaced": true/false,    // Has the building shifted position or rotated compared to before?
  "building_collapsed": true/false,    // Is there visible structural collapse (walls caved in, footprint deformed)?
  "foundation_only": true/false,       // Is only the slab/foundation remaining where the building was?
  "water_present": true/false,         // Is there standing water, dark blue/green discoloration, or waterlines visible around the structure?
  "debris_minor": true/false,          // Is there minor scattered debris near the structure?
  "debris_heavy": true/false,          // Is there a heavy debris field replacing or surrounding the structure?
  "sediment_staining": true/false,     // Are there mud/sediment stains, scour marks, or flood residue visible?
  "vegetation_damage": true/false,     // Are nearby trees toppled, stripped, or significantly damaged compared to before?
  "structure_gone": true/false,        // Has the structure completely disappeared from the area?
  "feature_type": "..."               // Type of structure: "building", "lot", "road", "bridge", etc.
}"""