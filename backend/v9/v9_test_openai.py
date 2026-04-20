"""v9 Test OpenAI: same pipeline as v9_openai, but runs on the held-out
disaster_harvey_test/ dataset (images/ and json/ subdirs).

3 API calls per building: describe pre, describe masked diff, evaluate post.
Outputs:
  disaster-output/*_v9_test_openai_results.json
  disaster-output-geojson/*_v9_test_openai_results.geojson
  accuracy/v9_test_openai.log
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

from cropping import crop_buildings, build_geojson, parse_wkt_polygon, padded_bbox
from accuracy_log import log_accuracy
from v4.upscale import upscale_image
from v9.difference import compute_difference
from v9.prompts import DESCRIBE_PRE_PROMPT, DESCRIBE_DIFF_PROMPT, EVALUATE_POST_PROMPT

load_dotenv()
client = OpenAI()

BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))
TEST_IMAGES_DIR = os.path.join(BACKEND_DIR, "disaster_harvey_test", "images")
TEST_JSON_DIR = os.path.join(BACKEND_DIR, "disaster_harvey_test", "json")
DISASTER_OUTPUT_DIR = os.path.join(BACKEND_DIR, "disaster-output")
os.makedirs(DISASTER_OUTPUT_DIR, exist_ok=True)

# --- Config ---
MODEL = "gpt-4.1-mini"
UPSCALE_FACTOR = 2
NOISE_THRESHOLD = 50
AMPLIFY_FACTOR = 3.0
QUARTET_WORKERS = 5
BUILDING_WORKERS = 10


def find_test_quartets() -> list[tuple[str, str, str, str]]:
    """Build list of (pre_image, post_image, pre_json, post_json) from the test dataset."""
    quartets = []
    for fname in sorted(os.listdir(TEST_IMAGES_DIR)):
        if not fname.endswith("_pre_disaster.png"):
            continue
        base = fname.replace("_pre_disaster.png", "")
        pre_img = os.path.join(TEST_IMAGES_DIR, f"{base}_pre_disaster.png")
        post_img = os.path.join(TEST_IMAGES_DIR, f"{base}_post_disaster.png")
        pre_json = os.path.join(TEST_JSON_DIR, f"{base}_pre_disaster.json")
        post_json = os.path.join(TEST_JSON_DIR, f"{base}_post_disaster.json")

        if all(os.path.exists(p) for p in (pre_img, post_img, pre_json, post_json)):
            quartets.append((pre_img, post_img, pre_json, post_json))

    return quartets


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


def assess_building(pre_crop: str, post_crop: str, uid: str, local_coords: list[tuple[float, float]]) -> dict:
    """Full v9 three-stage pipeline for one building."""
    pre_up = upscale_image(pre_crop, scale=UPSCALE_FACTOR)
    post_up = upscale_image(post_crop, scale=UPSCALE_FACTOR)

    scaled_coords = [(x * UPSCALE_FACTOR, y * UPSCALE_FACTOR) for x, y in local_coords]

    diff_path = compute_difference(
        pre_up, post_up,
        polygon_coords=scaled_coords,
        noise_threshold=NOISE_THRESHOLD,
        amplify_factor=AMPLIFY_FACTOR,
    )

    try:
        result = call_vlm(DESCRIBE_PRE_PROMPT, [pre_up])
        pre_description = result.get("description", "A building with a roof.")
    except Exception as e:
        print(f"      Stage 1 failed: {e}")
        pre_description = "A building with a roof."
    print(f"      Pre: {pre_description}")

    diff_prompt = DESCRIBE_DIFF_PROMPT.format(pre_description=pre_description)
    try:
        result = call_vlm(diff_prompt, [diff_path])
        diff_description = result.get("description", "Unable to analyze diff image.")
    except Exception as e:
        print(f"      Stage 2 failed: {e}")
        diff_description = "Unable to analyze diff image."
    print(f"      Diff: {diff_description}")

    eval_prompt = EVALUATE_POST_PROMPT.format(
        pre_description=pre_description,
        diff_description=diff_description,
    )
    try:
        result = call_vlm(eval_prompt, [pre_up, post_up, diff_path])
        subtype = result.get("subtype", "no-damage")
        confidence = float(result.get("confidence", 5))
        reasoning = result.get("reasoning", "")
    except Exception as e:
        print(f"      Stage 3 failed: {e}")
        subtype = "no-damage"
        confidence = 5.0
        reasoning = f"error: {e}"

    print(f"      Eval: {reasoning}")

    return {
        "feature_type": "building",
        "subtype": subtype,
        "confidence": confidence,
        "pre_description": pre_description,
        "diff_description": diff_description,
        "reasoning": reasoning,
    }


def extract_building_polygons(post_json_path: str, padding: int = 150) -> dict:
    """Extract local polygon coords for each building from the test post JSON."""
    from PIL import Image as PILImage

    with open(post_json_path) as f:
        data = json.load(f)

    base = os.path.splitext(os.path.basename(post_json_path))[0].replace("_post_disaster", "")
    img_path = os.path.join(TEST_IMAGES_DIR, f"{base}_post_disaster.png")
    img = PILImage.open(img_path)
    img_w, img_h = img.size

    result = {}
    for feat in data["features"]["xy"]:
        uid = feat["properties"]["uid"]
        coords = parse_wkt_polygon(feat["wkt"])
        if not coords:
            continue
        box = padded_bbox(coords, img_w, img_h, padding=padding)
        x_min, y_min = box[0], box[1]
        local_coords = [(x - x_min, y - y_min) for x, y in coords]
        result[uid] = local_coords

    return result


def process_building(pre_crop, post_crop, uid, ground_truth, gt_features, local_coords):
    print(f"\n  Assessing {uid} (ground truth: {ground_truth})...")
    prediction = assess_building(pre_crop, post_crop, uid, local_coords)

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
        "v9_meta": {
            "confidence": prediction["confidence"],
            "pre_description": prediction["pre_description"],
            "diff_description": prediction["diff_description"],
            "reasoning": prediction["reasoning"],
        },
    }

    print(f"    v9_test says: {prediction['subtype']} (conf={prediction['confidence']:.1f})")
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

    building_polygons = extract_building_polygons(post_json)

    results = []
    with ThreadPoolExecutor(max_workers=BUILDING_WORKERS) as pool:
        futures = {}
        for pre_crop, post_crop, uid, ground_truth in crops:
            local_coords = building_polygons.get(uid, [])
            future = pool.submit(
                process_building, pre_crop, post_crop, uid, ground_truth, gt_features, local_coords
            )
            futures[future] = uid

        for future in as_completed(futures):
            uid = futures[future]
            try:
                entry = future.result()
                results.append(entry)
            except Exception as e:
                print(f"\n  ERROR processing building {uid}: {e}")

    output_path = os.path.join(DISASTER_OUTPUT_DIR, f"{base}_v9_test_openai_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {output_path}")

    build_geojson(post_json, results, f"{base}_v9_test_openai_results")

    return results


def main():
    quartets = find_test_quartets()
    if not quartets:
        print(f"No disaster quartets found in {TEST_IMAGES_DIR}")
        sys.exit(1)

    num_to_process = len(quartets)
    print(f"Found {len(quartets)} test quartets, processing all {num_to_process}.")
    print("v9 Test OpenAI: 3-stage CoT + masked diff on held-out disaster_harvey_test set")
    print(f"Model: {MODEL} | Upscale: {UPSCALE_FACTOR}x | Noise threshold: {NOISE_THRESHOLD} | Amplify: {AMPLIFY_FACTOR}x")
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
        log_accuracy("v9_test_openai", quartet_results, all_results)


if __name__ == "__main__":
    main()
