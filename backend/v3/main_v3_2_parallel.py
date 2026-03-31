"""main_v3.2: Maximum parallelism — all levels parallelized.

Parallelism:
  Level 0 — Quartets in parallel (outer pool)
  Level 1 — Buildings within a quartet in parallel (inner pool)
  Level 2 — Gate votes and severity votes in parallel (vote pool)
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
from v3.difference import compute_difference
from v3.prompts import BINARY_GATE_PROMPT, SEVERITY_PROMPT
from v3.ensemble import majority_vote_binary, majority_vote_severity, calibrate_confidence

load_dotenv()
client = OpenAI()

DISASTER_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "disaster-output")
os.makedirs(DISASTER_OUTPUT_DIR, exist_ok=True)

# --- Config ---
GATE_MODEL = "gpt-4.1-mini"
GATE_VOTES = 3
SEVERITY_MODEL = "gpt-4.1-mini"
SEVERITY_VOTES = 3
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


def run_binary_gate(pre_path: str, post_path: str, diff_path: str) -> bool:
    """Stage 1: 3 gate calls in parallel, majority vote."""
    images = [pre_path, post_path, diff_path]

    with ThreadPoolExecutor(max_workers=GATE_VOTES) as vote_pool:
        futures = [
            vote_pool.submit(call_vlm, GATE_MODEL, BINARY_GATE_PROMPT, images)
            for _ in range(GATE_VOTES)
        ]

        votes = []
        for f in futures:
            try:
                result = f.result()
                votes.append(bool(result.get("damaged", False)))
            except Exception as e:
                print(f"      Gate call failed: {e}")
                votes.append(False)

    damaged = majority_vote_binary(votes)
    print(f"      Gate votes: {votes} -> {'DAMAGED' if damaged else 'NO-DAMAGE'}")
    return damaged


def run_severity_classification(pre_path: str, post_path: str, diff_path: str) -> tuple[str, float]:
    """Stage 2+3: 3 severity calls in parallel, majority vote + calibration."""
    images = [pre_path, post_path, diff_path]

    with ThreadPoolExecutor(max_workers=SEVERITY_VOTES) as vote_pool:
        futures = [
            vote_pool.submit(call_vlm, SEVERITY_MODEL, SEVERITY_PROMPT, images)
            for _ in range(SEVERITY_VOTES)
        ]

        votes = []
        confidences = []
        for f in futures:
            try:
                result = f.result()
                subtype = result.get("subtype", "minor-damage")
                confidence = float(result.get("confidence", 5))
                reasoning = result.get("reasoning", "")
                votes.append(subtype)
                confidences.append(confidence)
                if reasoning:
                    print(f"      Reasoning: {reasoning}")
            except Exception as e:
                print(f"      Severity call failed: {e}")
                votes.append("minor-damage")
                confidences.append(5.0)

    raw_severity = majority_vote_severity(votes)
    avg_confidence = sum(confidences) / len(confidences) if confidences else 5.0
    final_severity = calibrate_confidence(raw_severity, avg_confidence, CONFIDENCE_THRESHOLD)

    print(f"      Severity votes: {votes} (avg conf: {avg_confidence:.1f})")
    if final_severity != raw_severity:
        print(f"      Calibrated: {raw_severity} -> {final_severity} (low confidence)")

    return final_severity, avg_confidence


def assess_building(pre_crop: str, post_crop: str, uid: str) -> dict:
    diff_path = compute_difference(pre_crop, post_crop)

    is_damaged = run_binary_gate(pre_crop, post_crop, diff_path)

    if not is_damaged:
        return {
            "feature_type": "building",
            "subtype": "no-damage",
            "confidence": 10.0,
            "gate_passed": False,
        }

    severity, confidence = run_severity_classification(pre_crop, post_crop, diff_path)

    return {
        "feature_type": "building",
        "subtype": severity,
        "confidence": confidence,
        "gate_passed": True,
    }


def process_building(pre_crop, post_crop, uid, ground_truth, gt_features):
    """Process a single building — called in parallel from process_quartet."""
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
        "v3_meta": {
            "gate_passed": prediction["gate_passed"],
            "confidence": prediction["confidence"],
        },
    }

    print(f"    v3.2 says: {prediction['subtype']} (gate={'PASSED' if prediction['gate_passed'] else 'BLOCKED'}, conf={prediction['confidence']:.1f})")
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

    # Level 1: parallelize buildings
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

    # Save per-quartet results
    output_path = os.path.join(DISASTER_OUTPUT_DIR, f"{base}_v3_2_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {output_path}")

    build_geojson(post_json, results, f"{base}_v3_2_results")

    return results


def main():
    quartets = find_disaster_quartets()
    if not quartets:
        print("No disaster quartets found.")
        sys.exit(1)

    num_to_process = min(3, len(quartets))
    print(f"Found {len(quartets)} quartets, processing first {num_to_process}.")
    print("v3.2 pipeline: v3 + parallel buildings + parallel votes")
    print(f"Gate model: {GATE_MODEL} | Severity model: {SEVERITY_MODEL}")
    print(f"Workers: {QUARTET_WORKERS} quartets x {BUILDING_WORKERS} buildings x {GATE_VOTES}/{SEVERITY_VOTES} votes")
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
        gated = sum(1 for r in all_results if r["v3_meta"]["gate_passed"])
        print(f"\n{'='*60}")
        print(f"Overall Accuracy: {correct}/{total} ({100 * correct / total:.1f}%)")
        print(f"Gate passed: {gated}/{total} ({100 * gated / total:.1f}%) — rest classified as no-damage")
        log_accuracy("main_v3_2", quartet_results, all_results)


if __name__ == "__main__":
    main()
