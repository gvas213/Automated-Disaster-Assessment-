"""v4 OpenAI: Two-stage CoT damage assessment with upscaling and diff images.

Pipeline (no gate):
  1. Upscale pre/post crops (2x Lanczos)
  2. Compute difference image on upscaled crops
  3. Stage A: VLM describes pre-disaster building (baseline)
  4. Stage B: VLM compares post + diff against baseline, classifies damage (3x vote)
  5. Confidence calibration

Parallelism: Level 1 (buildings in parallel within quartets)
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
from v4.upscale import upscale_image
from v4.difference import compute_difference
from v4.prompts import BASELINE_PROMPT, build_classify_prompt
from v4.ensemble import majority_vote_severity, calibrate_confidence

load_dotenv()
client = OpenAI()

DISASTER_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "disaster-output")
os.makedirs(DISASTER_OUTPUT_DIR, exist_ok=True)

# --- Config ---
MODEL = "gpt-4.1-mini"
CLASSIFY_VOTES = 3
UPSCALE_FACTOR = 2
CONFIDENCE_THRESHOLD = 7.0
QUARTET_WORKERS = 5
BUILDING_WORKERS = 10


def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def call_vlm(model: str, prompt: str, image_paths: list[str]) -> dict:
    content = [{"type": "input_text", "text": prompt}]
    for img_path in image_paths:
        b64 = encode_image(img_path)
        content.append({
            "type": "input_image",
            "image_url": f"data:image/png;base64,{b64}",
        })

    response = client.responses.create(
        model=model,
        input=[{"role": "user", "content": content}],
    )

    raw = response.output_text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw)


def get_baseline(pre_upscaled: str) -> str:
    """Stage A: Describe the pre-disaster building."""
    try:
        result = call_vlm(MODEL, BASELINE_PROMPT, [pre_upscaled])
        return result.get("description", "A building with a roof and surrounding vegetation.")
    except Exception as e:
        print(f"      Baseline call failed: {e}")
        return "A building with a roof and surrounding vegetation."


def classify_damage(baseline: str, pre_upscaled: str, post_upscaled: str, diff_path: str) -> tuple[str, float]:
    """Stage B: Classify damage with 3x voting against baseline description."""
    prompt = build_classify_prompt(baseline)
    votes = []
    confidences = []

    for _ in range(CLASSIFY_VOTES):
        try:
            result = call_vlm(MODEL, prompt, [pre_upscaled, post_upscaled, diff_path])
            subtype = result.get("subtype", "no-damage")
            confidence = float(result.get("confidence", 5))
            reasoning = result.get("reasoning", "")
            votes.append(subtype)
            confidences.append(confidence)
            if reasoning:
                print(f"      Reasoning: {reasoning}")
        except Exception as e:
            print(f"      Classify call failed: {e}")
            votes.append("no-damage")
            confidences.append(5.0)

    raw_severity = majority_vote_severity(votes)
    avg_confidence = sum(confidences) / len(confidences) if confidences else 5.0
    final_severity = calibrate_confidence(raw_severity, avg_confidence, CONFIDENCE_THRESHOLD)

    print(f"      Votes: {votes} (avg conf: {avg_confidence:.1f})")
    if final_severity != raw_severity:
        print(f"      Calibrated: {raw_severity} -> {final_severity} (low confidence)")

    return final_severity, avg_confidence


def assess_building(pre_crop: str, post_crop: str, uid: str) -> dict:
    """Full v4 pipeline for one building."""
    pre_up = upscale_image(pre_crop, scale=UPSCALE_FACTOR)
    post_up = upscale_image(post_crop, scale=UPSCALE_FACTOR)
    diff_path = compute_difference(pre_up, post_up)

    baseline = get_baseline(pre_up)
    print(f"      Baseline: {baseline}")

    severity, confidence = classify_damage(baseline, pre_up, post_up, diff_path)

    return {
        "feature_type": "building",
        "subtype": severity,
        "confidence": confidence,
        "baseline": baseline,
    }


def process_building(pre_crop, post_crop, uid, ground_truth, gt_features):
    print(f"\n  Assessing {uid} (ground truth: {ground_truth})...")
    prediction = assess_building(pre_crop, post_crop, uid)

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
        "v4_meta": {
            "confidence": prediction["confidence"],
            "baseline": prediction["baseline"],
        },
    }

    print(f"    v4 says: {prediction['subtype']} (conf={prediction['confidence']:.1f})")
    match = "MATCH" if prediction["subtype"] == ground_truth else "MISMATCH"
    print(f"    Ground truth: {ground_truth} -> {match}")

    return entry


def process_quartet(pre_img, post_img, post_json) -> list[dict]:
    base = os.path.splitext(os.path.basename(post_img))[0].replace("_post_disaster", "")
    print(f"\nProcessing: {base}")

    crops = crop_buildings(pre_img, post_img, post_json)

    with open(post_json) as f:
        gt_data = json.load(f)
    gt_features = {feat["properties"]["uid"]: feat["properties"] for feat in gt_data["features"]["xy"]}

    results = []
    with ThreadPoolExecutor(max_workers=BUILDING_WORKERS) as building_pool:
        futures = {}
        for pre_crop, post_crop, uid, ground_truth in crops:
            future = building_pool.submit(
                process_building, pre_crop, post_crop, uid, ground_truth, gt_features
            )
            futures[future] = uid

        for future in as_completed(futures):
            uid = futures[future]
            try:
                entry = future.result()
                results.append(entry)
            except Exception as e:
                print(f"\n  ERROR processing building {uid}: {e}")

    output_path = os.path.join(DISASTER_OUTPUT_DIR, f"{base}_v4_openai_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {output_path}")

    build_geojson(post_json, results, f"{base}_v4_openai_results")

    return results


def main():
    quartets = find_disaster_quartets()
    if not quartets:
        print("No disaster quartets found.")
        sys.exit(1)

    num_to_process = min(3, len(quartets))
    print(f"Found {len(quartets)} quartets, processing first {num_to_process}.")
    print("v4 OpenAI: upscale + diff + baseline description + CoT classification (3x vote)")
    print(f"Model: {MODEL} | Upscale: {UPSCALE_FACTOR}x | Votes: {CLASSIFY_VOTES}")
    print(f"Workers: {QUARTET_WORKERS} quartets x {BUILDING_WORKERS} buildings")
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
        log_accuracy("v4_openai", quartet_results, all_results)


if __name__ == "__main__":
    main()
