# main_v3 Plan: Highest Accuracy Approach

## Accuracy Analysis

### Scoreboard

| Method | Exact Accuracy | Partial Score | Buildings |
|---|---|---|---|
| **main.py** (GPT-4.1-mini, PROMPT_V2) | **27.4%** (144/525) | **45.5%** | 525 |
| **gemini_api** (Gemini 2.5 Flash, PROMPT_V1) | 22.9% (60/262) | 35.9% | 262 |
| **main_v2** (GPT-4.1-mini, feature detect + algo) | 19.0% (100/525) | — | 525 |

### Ground Truth Distribution (the real problem)

Dataset is **massively imbalanced**:
- **~97% no-damage** (~511 of 525)
- **~2% minor-damage** (~12)
- **<1% major-damage** (~2)
- **0% destroyed** (0)

Hurricane Harvey data where the vast majority of buildings survived. Baseline accuracy of just predicting "no-damage" for everything = ~97%.

### The #1 Problem: Massive False Positive Damage

Every method's biggest failure — predicting damage on undamaged buildings:

**main.py** (run 2, on ~511 no-damage buildings):
- 140 correct (no-damage → no-damage)
- 123 wrong as minor-damage
- 117 wrong as major-damage
- 106 wrong as **destroyed**
- ~25 with garbage subtypes ("footprint gone", "limited roof damage", etc.)

**gemini_api** (on ~250 no-damage buildings):
- 59 correct
- 25 wrong as minor
- 73 wrong as major
- **93 wrong as destroyed** (worst offender)

**main_v2** (on ~511 no-damage buildings):
- 93 correct
- **266 wrong as minor-damage** (worst offender here)
- 97 wrong as major
- 55 wrong as destroyed

### Why v2's Feature Detection Fails

The VLM hallucinates damage on no-damage buildings. Typical false detection:
```
roof_intact: false, roof_partial_loss: true, water_present: true,
debris_minor: true, sediment_staining: true, vegetation_damage: true
```

The VLM misinterprets **normal satellite imagery artifacts** as damage:
- Different sun angles between pre/post → shadow changes → "roof_partial_loss"
- Different capture times → vegetation color shift → "vegetation_damage"
- Normal ground texture → "sediment_staining"
- Any clutter in frame → "debris_minor"
- Slight registration offset → building looks shifted

The deterministic algorithm then faithfully escalates these false features. One false `debris_minor` = minor-damage. One false `roof_partial_loss` + `water_present` = major-damage. It's a **false positive amplifier**.

### Why Gemini is the Most Aggressive

Gemini 2.5 Flash + PROMPT_V1 classifies 93 no-damage buildings as "destroyed." PROMPT_V1 has hurricane-specific language about "washed away" and "debris field replaces building" that Gemini over-triggers on.

### Why main.py is "Best" (But Still Bad)

main.py with PROMPT_V2 has the most balanced error distribution and also returns non-standard subtypes (model "thinking out loud" rather than classifying). Best of three bad approaches but at 27% still far below the 97% you'd get by just guessing no-damage.

### The Prompt Problem

All prompts prime the model to **look for damage**. They describe what each damage level looks like in detail, essentially saying "here's what to find." The VLM then finds what it's looking for — confirmation bias baked into the prompt.

---

## Strategy: Multi-Stage Pipeline with Ensemble Voting

Core insight: **be conservative first, then classify severity only when damage is clear.**

### Stage 1 — Binary Gate: "Is there damage at all?"
- Ask the VLM a simple yes/no: "Does this building show **clear, unambiguous structural change** between pre and post?"
- Prompt explicitly states: "Most buildings survive hurricanes. Differences in lighting, shadows, vegetation color, and slight image alignment are NORMAL and do NOT indicate damage. Only flag damage when you see physical structural change to the building itself."
- Run this 3 times (or across 2 models: GPT-4.1 + Gemini) and require **majority vote for damage**
- If majority says no damage → classify as no-damage, skip stage 2

### Stage 2 — Severity Classification (only for flagged buildings)
- Use a chain-of-thought prompt: "First describe what you see in each image, then describe the specific structural differences, then classify"
- Use GPT-4.1 (full, not mini) for this — it's the harder task and worth the cost
- Use structured output / JSON mode to prevent garbage subtypes
- Run 3 times and take majority vote on severity level

### Stage 3 — Confidence Calibration
- Have the model output a 1-10 confidence score alongside the classification
- If confidence < 7 on anything above no-damage, downgrade by one severity level

### Additional Improvements

1. **Upgrade model**: GPT-4.1 full instead of mini for at least the classification stage
2. **Reduce padding**: 150px may be too much — surrounding area confuses the model. Try 75px or adaptive padding based on building size
3. **Remove the red outline** or make it more subtle — the red polygon may itself be confusing the model (looks like fire/damage)
4. **Anti-hallucination prompt language**: Explicitly list what is NOT damage (shadow changes, color shifts, vegetation seasons, image registration artifacts)
5. **Neighborhood context**: Show the model a few crops from the same satellite tile so it can calibrate — "here's the general area, most buildings look like this"

### Expected Impact

The binary gate alone should catch the ~370 no-damage buildings currently misclassified as damaged. Even if it just recovers half of those, accuracy jumps from 27% to ~60%+. With ensemble voting and confidence calibration on top, 70-80% should be achievable.

---

## Research: What Academics Actually Do (and How It Applies)

### The Standard Approach: Siamese CNNs (not VLMs)

The winning xView2/xBD solutions and most published research use **trained neural networks**, not prompted VLMs:

1. **Siamese U-Nets** — Two shared-weight encoder branches process the pre and post images separately, then the feature maps are **differenced** and decoded into a per-pixel damage classification mask. This is the xView2 1st place approach.
2. **Two-stage pipeline**: First localize buildings (segmentation), then classify damage on the detected buildings.

### Image Preprocessing Techniques Researchers Use

- **Difference images** — Compute the absolute pixel-level difference between pre and post images. This immediately highlights what actually changed and suppresses everything that stayed the same. This directly attacks the artifact problem killing our accuracy (shadows, vegetation, etc. that didn't change get zeroed out).
- **Image registration / ortho-rectification** — Aligning pre/post images precisely so that pixel offsets don't get misread as displacement.
- **Normalization** — Radiometric calibration so different lighting/atmospheric conditions between captures don't create false differences.
- **Grayscale conversion** — Some methods convert to grayscale before differencing to reduce color-based false positives (seasonal vegetation color changes, etc.)
- **PCA on difference images** — Principal Component Analysis to extract the most meaningful change signals from multi-band imagery.
- **Heavy augmentation** — Random crops, flips, rotations, color jitter to handle the massive class imbalance (same problem we have).

### Class Imbalance Handling

This is a known xBD problem. Researchers use:
- Weighted loss functions (oversample damaged buildings)
- Focal loss (penalizes easy no-damage classifications less)
- Balanced mini-batches during training

### Key Takeaway for main_v3: The Difference Image

The **difference image** technique is the single most applicable thing we can adopt without training a model. Instead of sending raw pre/post crops to the VLM:

1. Compute an absolute difference image between pre and post crops
2. Send **three** images to the VLM: pre, post, AND the difference image
3. The difference image will be mostly black/dark where nothing changed, and bright where actual structural changes occurred
4. This gives the VLM a much clearer signal — it can't hallucinate damage where the difference image shows nothing

This is low-hanging fruit and directly attacks the false positive problem.

### Sources

- [xBD: A Dataset for Assessing Building Damage from Satellite Imagery](https://arxiv.org/abs/1911.09296)
- [A simple, strong baseline for building damage detection on the xBD dataset](https://arxiv.org/abs/2401.17271)
- [Microsoft Building Damage Assessment CNN Siamese](https://github.com/microsoft/building-damage-assessment-cnn-siamese)
- [Technical Solution Discussion for Key Challenges - xBD Dataset](https://www.mdpi.com/2072-4292/12/22/3808)
- [Disaster assessment using computer vision and satellite imagery](https://www.frontiersin.org/journals/environmental-science/articles/10.3389/fenvs.2022.969758/full)
- [Deep Learning-Based Change Detection in Remote Sensing Images](https://www.mdpi.com/2072-4292/14/4/871)
- [Satellite Image Deep Learning Techniques](https://github.com/satellite-image-deep-learning/techniques)
- [DisasterAdaptiveNet](https://www.sciencedirect.com/science/article/pii/S1569843225004030)
