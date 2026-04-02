# v4: Two-Stage CoT Damage Assessment

## What's Different from v3

| | v3 | v4 |
|---|---|---|
| Gate | Binary yes/no → too tight or too loose | **None** — single-pass with all 4 damage levels |
| Upscaling | No | **2x Lanczos** before VLM (research shows +3% accuracy) |
| Prompting | One prompt classifies directly | **Two-stage**: describe pre-disaster baseline → compare post against it |
| Diff image | On raw crops | On **upscaled** crops (more detail in diff) |
| API calls/building | 3 gate + 3 severity = 6 | 1 baseline + 3 classify = **4** (cheaper) |
| no-damage handling | Gate decides (broken) | VLM sees all 4 options every time, diff image calibrates |

## Why v3's Gate Failed

- Too conservative (majority vote) → 0% recall on damaged buildings, ~97% accuracy by just predicting no-damage
- Too loose (any vote) → everything passes, VLM over-predicts damage on undamaged buildings
- Binary decisions don't work well — the VLM needs to weigh evidence across a spectrum, not make a yes/no call

## v4 Approach (Research-Backed)

Based on:
- [From Pixels to Semantics (arXiv 2603.22768)](https://arxiv.org/abs/2603.22768) — two-stage VLM prompting, super-resolution
- [Structural Damage Detection Using AI Super Resolution and VLM (arXiv 2508.17130)](https://arxiv.org/abs/2508.17130) — baseline description before comparison

Key ideas:
1. **Upscale first** — subtle roof damage invisible at raw resolution becomes visible at 2x
2. **Establish baseline** — VLM describes the building from the pre-disaster image alone, preventing bias from seeing both images simultaneously
3. **Classify against baseline** — the classification prompt includes the baseline description, diff image, and explicit guidance on how to interpret diff brightness
4. **No gate** — all 4 damage levels available every time, diff image naturally calibrates (dark = no change = no damage)

## Data Flow

```
For each quartet (parallel across QUARTET_WORKERS):
  crop_buildings() via cropping.py
       ↓
  For each building (parallel across BUILDING_WORKERS):
       ↓
    ┌─ 1. UPSCALE (upscale.py)
    │    pre_crop.png  → pre_crop_up2x.png   (2x Lanczos)
    │    post_crop.png → post_crop_up2x.png
    │
    ├─ 2. DIFFERENCE IMAGE (difference.py)
    │    |pre_up2x - post_up2x| → grayscale → histogram equalize
    │    → diff.png (bright = real change, dark = nothing)
    │
    ├─ 3. STAGE A: BASELINE (1 API call)
    │    Send: pre_up2x only
    │    Prompt: "Describe this building's roof, footprint, surroundings"
    │    Returns: "White-roofed residential building with south-facing driveway..."
    │
    ├─ 4. STAGE B: CLASSIFY (3 API calls, sequential)
    │    Send: pre_up2x + post_up2x + diff.png
    │    Prompt includes baseline description + CoT instructions:
    │      "Compare post to baseline → check diff image → classify"
    │    Each call returns: {subtype, confidence, reasoning}
    │    Majority vote on subtype, average confidence
    │
    └─ 5. CONFIDENCE CALIBRATION
         If avg confidence < 7.0 → downgrade one level
         e.g. major-damage @ 5.5 confidence → minor-damage
         ↓
    Final: {feature_type, subtype, confidence, baseline}
       ↓
  Save JSON results + GeoJSON
  Log to accuracy/
```

## Parallelism

```
ThreadPool (QUARTET_WORKERS=5)
  └── process_quartet()
        └── ThreadPool (BUILDING_WORKERS=10)
              └── process_building()
                    └── 1 baseline call + 3 classify calls (sequential)
```

Max concurrent API calls: 5 × 10 = 50 (manageable for rate limits).

## Files

| File | Purpose |
|---|---|
| `upscale.py` | 2x Lanczos image upscaling, saves to `output_image/upscaled/` |
| `difference.py` | Absolute diff on upscaled crops, saves to `output_image/diff_v4/` |
| `prompts.py` | Baseline prompt + classify prompt template with CoT |
| `ensemble.py` | Majority vote severity + confidence calibration (no gate) |
| `v4_gemini.py` | Gemini 2.5 Flash implementation |
| `v4_openai.py` | GPT-4.1-mini implementation |

## Running

```bash
cd backend
uv run python v4/v4_gemini.py
uv run python v4/v4_openai.py
```

Logs go to `accuracy/v4_gemini.log` and `accuracy/v4_openai.log`.
