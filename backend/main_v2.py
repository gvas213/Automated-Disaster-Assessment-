import base64
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from openai import OpenAI
from dotenv import load_dotenv

from cropping import find_disaster_quartets, crop_buildings, build_geojson
from prompt import FEATURE_DETECTION_PROMPT
from accuracy_log import log_accuracy

load_dotenv()
client = OpenAI()

DISASTER_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "disaster-output")
os.makedirs(DISASTER_OUTPUT_DIR, exist_ok=True)


def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def detect_features(pre_crop_path: str, post_crop_path: str) -> dict:
    """Ask VLM to detect visual features (true/false) instead of classifying damage directly."""
    pre_b64 = encode_image(pre_crop_path)
    post_b64 = encode_image(post_crop_path)

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": FEATURE_DETECTION_PROMPT},
                {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{pre_b64}",
                },
                {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{post_b64}",
                },
            ],
        }],
    )

    raw = response.output_text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw)


def classify_damage(features: dict) -> str:
    """Deterministic algorithm: map boolean features to a damage classification.

    Priority order (highest severity wins):
    1. destroyed  - structure gone, foundation only, or building displaced + heavy debris
    2. major-damage - large roof loss, collapse, heavy debris, or flooding + structural issues
    3. minor-damage - partial roof loss, minor debris, water/sediment, or vegetation damage
    4. no-damage   - everything looks intact
    """
    # --- destroyed ---
    if features.get("structure_gone"):
        return "destroyed"
    if features.get("foundation_only"):
        return "destroyed"
    if features.get("building_displaced") and features.get("debris_heavy"):
        return "destroyed"
    if features.get("building_collapsed") and features.get("debris_heavy"):
        return "destroyed"

    # --- major-damage ---
    if features.get("building_collapsed"):
        return "major-damage"
    if features.get("roof_major_loss"):
        return "major-damage"
    if features.get("debris_heavy"):
        return "major-damage"
    if features.get("building_displaced"):
        return "major-damage"
    if features.get("water_present") and features.get("roof_partial_loss"):
        return "major-damage"

    # --- minor-damage ---
    if features.get("roof_partial_loss"):
        return "minor-damage"
    if features.get("debris_minor"):
        return "minor-damage"
    if features.get("water_present"):
        return "minor-damage"
    if features.get("sediment_staining"):
        return "minor-damage"
    if features.get("vegetation_damage") and not features.get("roof_intact"):
        return "minor-damage"

    # --- no-damage ---
    return "no-damage"


def process_quartet(pre_img, post_img, post_json) -> list[dict]:
    """Process a single quartet: crop buildings, detect features, classify damage."""
    base = os.path.splitext(os.path.basename(post_img))[0].replace("_post_disaster", "")
    print(f"\nProcessing: {base}")

    crops = crop_buildings(pre_img, post_img, post_json)

    with open(post_json) as f:
        gt_data = json.load(f)
    gt_features = {feat["properties"]["uid"]: feat["properties"] for feat in gt_data["features"]["xy"]}

    results = []
    for pre_crop, post_crop, uid, ground_truth in crops:
        print(f"\n  Detecting features for {uid} (ground truth: {ground_truth})...")
        features = detect_features(pre_crop, post_crop)
        damage = classify_damage(features)

        given = gt_features[uid]
        entry = {
            "uid": uid,
            "given": {
                "feature_type": given["feature_type"],
                "subtype": given["subtype"],
            },
            "predicted": {
                "feature_type": features.get("feature_type", "building"),
                "subtype": damage,
            },
            "detected_features": {k: v for k, v in features.items() if k != "feature_type"},
        }
        results.append(entry)

        print(f"    Features: { {k: v for k, v in features.items() if v is True and k != 'feature_type'} }")
        print(f"    Algorithm says: {damage}")
        match = "MATCH" if damage == ground_truth else "MISMATCH"
        print(f"    Ground truth: {ground_truth} -> {match}")

    # Save per-quartet results
    output_path = os.path.join(DISASTER_OUTPUT_DIR, f"{base}_v2_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {output_path}")

    # Save GeoJSON
    build_geojson(post_json, results, f"{base}_v2_results")

    return results


def main():
    quartets = find_disaster_quartets()
    if not quartets:
        print("No disaster quartets found.")
        sys.exit(1)
    print(f"Found {min(3, len(quartets))} quartets, processing across 15 threads.")
    print("Using feature-detection + algorithmic classification (v2)")
    time.sleep(2)
    num_to_process = min(3, len(quartets))

    all_results = []
    quartet_results = {}
    pool = ThreadPoolExecutor(max_workers=15)
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

    # Overall accuracy summary
    if all_results:
        correct = sum(1 for r in all_results if r["given"]["subtype"] == r["predicted"]["subtype"])
        total = len(all_results)
        print(f"\nOverall Accuracy: {correct}/{total} ({100 * correct / total:.1f}%)")

        # Per-category breakdown
        from collections import Counter
        confusion = Counter()
        for r in all_results:
            confusion[(r["given"]["subtype"], r["predicted"]["subtype"])] += 1
        print("\nConfusion (ground_truth -> predicted):")
        for (gt, pred), count in sorted(confusion.items()):
            marker = "OK" if gt == pred else "  "
            print(f"  {marker} {gt:>15} -> {pred:<15} x{count}")

        # Feature frequency
        feature_counts = Counter()
        for r in all_results:
            for k, v in r["detected_features"].items():
                if v is True:
                    feature_counts[k] += 1
        print("\nFeature detection frequency:")
        for feat, count in feature_counts.most_common():
            print(f"  {feat}: {count}/{total}")

        log_accuracy("main_v2", quartet_results, all_results)


if __name__ == "__main__":
    main()
