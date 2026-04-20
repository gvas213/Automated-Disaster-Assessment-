"""v5 OpenAI: Diverse-input voting damage assessment.

Each of 3 votes gets genuinely different inputs:
  Vote 1: 2x upscale, grayscale+equalized diff, 150px padding, standard prompt
  Vote 2: no upscale, RGB color diff, 75px padding, conservative prompt
  Vote 3: 3x upscale, raw grayscale diff, 250px padding, sensitive prompt

Pipeline per building:
  1. Crop at 3 different paddings (75, 150, 250)
  2. Upscale each at different factors (1x, 2x, 3x)
  3. Compute different diff images per vote
  4. Stage A: Baseline description (1 call, shared across votes)
  5. Stage B: 3 diverse classify calls
  6. Diverse vote aggregation + confidence calibration
"""

import base64
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from cropping import find_disaster_quartets, crop_buildings, build_geojson
from accuracy_log import log_accuracy
from v5.upscale import upscale_image
from v5.difference import (
    compute_diff_grayscale_equalized,
    compute_diff_rgb,
    compute_diff_grayscale_raw,
)
from v5.prompts import BASELINE_PROMPT, build_classify_prompt
from v5.ensemble import diverse_vote, calibrate_confidence

load_dotenv()
client = OpenAI()

DISASTER_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "disaster-output")
os.makedirs(DISASTER_OUTPUT_DIR, exist_ok=True)

# --- Config ---
MODEL = "gpt-4.1-mini"
CONFIDENCE_THRESHOLD = 7.0
QUARTET_WORKERS = 3
BUILDING_WORKERS = 5

# Vote configurations: (padding, upscale_factor, divff_method, prompt_framing)
VOTE_CONFIGS = [
    {"padding": 150, "upscale": 2, "diff_fn": compute_diff_grayscale_equalized, "framing": "standard"},
    {"padding": 75,  "upscale": 1, "diff_fn": compute_diff_rgb,                 "framing": "conservative"},
    {"padding": 250, "upscale": 3, "diff_fn": compute_diff_grayscale_raw,       "framing": "sensitive"},
]


def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def call_vlm(prompt: str, image_paths: list[str]) -> dict:
    content = [{"type": "input_text", "text": prompt}]
    for img_path in image_paths:
        b64 = encode_image(img_path)
        content.append({
            "type": "input_image",
            "image_url": f"data:image/png;base64,{b64}",
        })

    response = client.responses.create(
        model=MODEL,
        input=[{"role": "user", "content": content}],
    )

    raw = response.output_text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw)


def get_baseline(pre_path: str) -> str:
    """Stage A: Describe the pre-disaster building (shared across votes)."""
    pre_up = upscale_image(pre_path, scale=2)
    try:
        result = call_vlm(BASELINE_PROMPT, [pre_up])
        return result.get("description", "A building with a roof and surrounding vegetation.")
    except Exception as e:
        print(f"      Baseline call failed: {e}")
        return "A building with a roof and surrounding vegetation."


def run_vote(vote_idx: int, config: dict, pre_crop: str, post_crop: str, baseline: str, uid: str) -> dict:
    """Run a single diverse vote."""
    tag = f"_v{vote_idx}"

    # Upscale
    pre_up = upscale_image(pre_crop, scale=config["upscale"])
    post_up = upscale_image(post_crop, scale=config["upscale"])

    # Diff
    diff_path = config["diff_fn"](pre_up, post_up, tag=tag)

    # Classify
    prompt = build_classify_prompt(baseline, framing=config["framing"])

    try:
        result = call_vlm(prompt, [pre_up, post_up, diff_path])
        subtype = result.get("subtype", "no-damage")
        confidence = float(result.get("confidence", 5))
        reasoning = result.get("reasoning", "")
    except Exception as e:
        print(f"      Vote {vote_idx} failed: {e}")
        subtype = "no-damage"
        confidence = 5.0
        reasoning = f"error: {e}"

    return {
        "subtype": subtype,
        "confidence": confidence,
        "framing": config["framing"],
        "reasoning": reasoning,
    }


def assess_building(crops_by_padding: dict, uid: str) -> dict:
    """Full v5 pipeline for one building.

    Args:
        crops_by_padding: {padding: (pre_crop_path, post_crop_path)}
        uid: Building UID.
    """
    # Use the default padding crop for baseline
    default_pre, _ = crops_by_padding[150]
    baseline = get_baseline(default_pre)
    print(f"      Baseline: {baseline}")

    # Run 3 diverse votes
    votes = []
    for i, config in enumerate(VOTE_CONFIGS):
        pre_crop, post_crop = crops_by_padding[config["padding"]]
        vote = run_vote(i, config, pre_crop, post_crop, baseline, uid)
        votes.append(vote)
        print(f"      Vote {i} ({config['framing']}, pad={config['padding']}, up={config['upscale']}x): "
              f"{vote['subtype']} (conf={vote['confidence']:.1f})")
        if vote["reasoning"]:
            print(f"        Reasoning: {vote['reasoning']}")

    # Aggregate
    raw_subtype, avg_conf = diverse_vote(votes)
    final_subtype = calibrate_confidence(raw_subtype, avg_conf, CONFIDENCE_THRESHOLD)

    if final_subtype != raw_subtype:
        print(f"      Calibrated: {raw_subtype} -> {final_subtype} (avg conf={avg_conf:.1f})")

    return {
        "feature_type": "building",
        "subtype": final_subtype,
        "confidence": avg_conf,
        "baseline": baseline,
        "votes": [{"framing": v["framing"], "subtype": v["subtype"], "confidence": v["confidence"]} for v in votes],
    }


def process_building(crops_by_padding, uid, ground_truth, gt_features):
    print(f"\n  Assessing {uid} (ground truth: {ground_truth})...")
    prediction = assess_building(crops_by_padding, uid)

    given = gt_features[uid]
    entry = {
        "uid": uid,
        "given": {
            "feature_type": given["feature_type"],
            "subtype": given["subtype"],
        },
        "predicted": {
            "feature_type": prediction["feature_type"],
            "subtype": prediction["subtype"],
        },
        "v5_meta": {
            "confidence": prediction["confidence"],
            "baseline": prediction["baseline"],
            "votes": prediction["votes"],
        },
    }

    print(f"    v5 says: {prediction['subtype']} (conf={prediction['confidence']:.1f})")
    match = "MATCH" if prediction["subtype"] == ground_truth else "MISMATCH"
    print(f"    Ground truth: {ground_truth} -> {match}")

    return entry


def process_quartet(pre_img, post_img, post_json) -> list[dict]:
    base = os.path.splitext(os.path.basename(post_img))[0].replace("_post_disaster", "")
    print(f"\nProcessing: {base}")

    # Crop at all 3 padding levels
    paddings = sorted(set(c["padding"] for c in VOTE_CONFIGS))
    crops_by_padding = {}
    for pad in paddings:
        crops_by_padding[pad] = crop_buildings(pre_img, post_img, post_json, padding=pad)

    with open(post_json) as f:
        gt_data = json.load(f)
    gt_features = {feat["properties"]["uid"]: feat["properties"] for feat in gt_data["features"]["xy"]}

    # Build per-building dict: uid -> {padding: (pre_crop, post_crop)}
    # All padding levels produce the same UIDs in the same order
    building_crops = {}
    for i, (pre_crop, post_crop, uid, ground_truth) in enumerate(crops_by_padding[paddings[0]]):
        building_crops[uid] = {
            "ground_truth": ground_truth,
            "crops": {},
        }
        for pad in paddings:
            pre_c, post_c, _, _ = crops_by_padding[pad][i]
            building_crops[uid]["crops"][pad] = (pre_c, post_c)

    results = []
    with ThreadPoolExecutor(max_workers=BUILDING_WORKERS) as pool:
        futures = {}
        for uid, data in building_crops.items():
            future = pool.submit(
                process_building, data["crops"], uid, data["ground_truth"], gt_features
            )
            futures[future] = uid

        for future in as_completed(futures):
            uid = futures[future]
            try:
                entry = future.result()
                results.append(entry)
            except Exception as e:
                print(f"\n  ERROR processing building {uid}: {e}")

    output_path = os.path.join(DISASTER_OUTPUT_DIR, f"{base}_v5_openai_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {output_path}")

    build_geojson(post_json, results, f"{base}_v5_openai_results")

    return results


def main():
    quartets = find_disaster_quartets()
    if not quartets:
        print("No disaster quartets found.")
        sys.exit(1)

    num_to_process = min(3, len(quartets))
    print(f"Found {len(quartets)} quartets, processing first {num_to_process}.")
    print("v5 OpenAI: diverse-input voting (3 diff methods, 3 paddings, 3 upscales, 3 prompt framings)")
    print(f"Model: {MODEL}")
    print(f"Workers: {QUARTET_WORKERS} quartets x {BUILDING_WORKERS} buildings")
    for i, c in enumerate(VOTE_CONFIGS):
        print(f"  Vote {i}: pad={c['padding']}, up={c['upscale']}x, diff={c['diff_fn'].__name__}, prompt={c['framing']}")
    time.sleep(2)

    all_results = []
    quartet_results = {}

    pool = ThreadPoolExecutor(max_workers=QUARTET_WORKERS)
    try:
        futures = {}
        for i in range(num_to_process):
            pre_img, post_img, pre_json, post_json = quartets[i]
            future = pool.submit(process_quartet, pre_img, post_img, post_json)
            futures[future] = os.path.basename(post_img)

        for future in as_completed(futures):
            name = futures[future]
            try:
                results = future.result()
                all_results.extend(results)
                quartet_results[name] = results
            except Exception as e:
                print(f"\nERROR processing {name}: {e}")
    except KeyboardInterrupt:
        print("\nInterrupted! Cancelling pending tasks...")
        for future in futures:
            future.cancel()
        pool.shutdown(wait=False, cancel_futures=True)
        sys.exit(1)
    finally:
        pool.shutdown(wait=True)

    if all_results:
        correct = sum(1 for r in all_results if r["given"]["subtype"] == r["predicted"]["subtype"])
        total = len(all_results)
        print(f"\n{'='*60}")
        print(f"Overall Accuracy: {correct}/{total} ({100 * correct / total:.1f}%)")
        log_accuracy("v5_openai", quartet_results, all_results)


if __name__ == "__main__":
    main()
