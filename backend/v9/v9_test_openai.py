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
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import openai
from openai import OpenAI
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from cropping import crop_buildings, build_geojson, parse_wkt_polygon, padded_bbox
from accuracy_log import log_accuracy
from v4.upscale import upscale_image
from v9.difference import compute_difference
from v9.prompts import DESCRIBE_PRE_PROMPT, DESCRIBE_DIFF_PROMPT, EVALUATE_POST_PROMPT, COST_PROMPT

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


class _StopProcessing(Exception):
    """Raised on rate-limit / insufficient-quota to halt the pipeline cleanly."""


_stop_event = threading.Event()
_stop_reason: list[str | None] = [None]


def _trigger_stop(reason: str) -> None:
    if not _stop_event.is_set():
        _stop_reason[0] = reason
        _stop_event.set()
        print(f"\n!! STOP SIGNAL: {reason}")


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
    if _stop_event.is_set():
        raise _StopProcessing(_stop_reason[0] or "stop signal")

    content = [{"type": "input_text", "text": prompt}]
    for img_path in image_paths:
        b64 = encode_image(img_path)
        content.append({
            "type": "input_image",
            "image_url": f"data:image/png;base64,{b64}",
        })

    try:
        response = client.responses.create(
            model=MODEL,
            input=[{"role": "user", "content": content}],
        )
    except openai.RateLimitError as e:
        _trigger_stop(f"RateLimitError / insufficient_quota: {e}")
        raise _StopProcessing(str(e)) from e

    raw = response.output_text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw)


def estimate_cost(damage_type: str, pre_description: str, reasoning: str) -> tuple[int, str]:
    """Call VLM to estimate repair cost in USD. Returns (cost_usd, cost_reasoning)."""
    if damage_type == "no-damage":
        return 0, "No damage — no repair cost."

    if _stop_event.is_set():
        raise _StopProcessing(_stop_reason[0] or "stop signal")

    prompt = COST_PROMPT.format(
        damage_type=damage_type,
        pre_description=pre_description or "No description available.",
        reasoning=reasoning or "No reasoning available.",
    )
    try:
        response = client.responses.create(
            model=MODEL,
            input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        )
    except openai.RateLimitError as e:
        _trigger_stop(f"RateLimitError / insufficient_quota: {e}")
        raise _StopProcessing(str(e)) from e
    raw = response.output_text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]
    result = json.loads(raw)
    return int(result["cost_usd"]), result.get("cost_reasoning", "")


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
    except _StopProcessing:
        raise
    except Exception as e:
        print(f"      Stage 1 failed: {e}")
        pre_description = "A building with a roof."
    print(f"      Pre: {pre_description}")

    diff_prompt = DESCRIBE_DIFF_PROMPT.format(pre_description=pre_description)
    try:
        result = call_vlm(diff_prompt, [diff_path])
        diff_description = result.get("description", "Unable to analyze diff image.")
    except _StopProcessing:
        raise
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
    except _StopProcessing:
        raise
    except Exception as e:
        print(f"      Stage 3 failed: {e}")
        subtype = "no-damage"
        confidence = 5.0
        reasoning = f"error: {e}"

    print(f"      Eval: {reasoning}")

    # Stage 4: Estimate repair cost
    try:
        cost_usd, cost_reasoning = estimate_cost(subtype, pre_description, reasoning)
    except _StopProcessing:
        raise
    except Exception as e:
        print(f"      Stage 4 (cost) failed: {e}")
        cost_usd, cost_reasoning = None, f"error: {e}"
    print(f"      Cost: ${cost_usd:,}" if cost_usd is not None else "      Cost: estimation failed")

    return {
        "feature_type": "building",
        "subtype": subtype,
        "confidence": confidence,
        "pre_description": pre_description,
        "diff_description": diff_description,
        "reasoning": reasoning,
        "cost_usd": cost_usd,
        "cost_reasoning": cost_reasoning,
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
        "cost_usd": prediction["cost_usd"],
        "v9_meta": {
            "confidence": prediction["confidence"],
            "pre_description": prediction["pre_description"],
            "diff_description": prediction["diff_description"],
            "reasoning": prediction["reasoning"],
            "cost_reasoning": prediction["cost_reasoning"],
        },
    }

    print(f"    v9_test says: {prediction['subtype']} (conf={prediction['confidence']:.1f})")
    match = "MATCH" if prediction["subtype"] == ground_truth else "MISMATCH"
    print(f"    Ground truth: {ground_truth} -> {match}")

    return entry


def process_quartet(pre_img, post_img, post_json) -> list[dict]:
    base = os.path.splitext(os.path.basename(post_img))[0].replace("_post_disaster", "")
    print(f"\nProcessing: {base}")

    if _stop_event.is_set():
        raise _StopProcessing(_stop_reason[0] or "stop signal")

    crops = crop_buildings(pre_img, post_img, post_json)

    with open(post_json) as f:
        gt_data = json.load(f)
    gt_features = {feat["properties"]["uid"]: feat["properties"] for feat in gt_data["features"]["xy"]}

    building_polygons = extract_building_polygons(post_json)

    results = []
    stop_hit = False
    pool = ThreadPoolExecutor(max_workers=BUILDING_WORKERS)
    try:
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
            except _StopProcessing:
                stop_hit = True
                for f in futures:
                    f.cancel()
                break
            except Exception as e:
                print(f"\n  ERROR processing building {uid}: {e}")
    finally:
        pool.shutdown(wait=True, cancel_futures=True)

    if stop_hit:
        print(f"  Quartet {base} aborted ({len(results)} buildings completed before stop).")
        raise _StopProcessing(_stop_reason[0] or "stop signal")

    output_path = os.path.join(DISASTER_OUTPUT_DIR, f"{base}_v9_test_openai_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {output_path}")

    build_geojson(post_json, results, f"{base}_v9_test_openai_results")

    return results


def _is_quartet_done(post_img: str) -> bool:
    """A quartet is considered done if its results JSON is already on disk."""
    base = os.path.splitext(os.path.basename(post_img))[0].replace("_post_disaster", "")
    output_path = os.path.join(DISASTER_OUTPUT_DIR, f"{base}_v9_test_openai_results.json")
    return os.path.exists(output_path)


def main():
    all_quartets = find_test_quartets()
    if not all_quartets:
        print(f"No disaster quartets found in {TEST_IMAGES_DIR}")
        sys.exit(1)

    # Resume: skip quartets whose results JSON already exists on disk.
    quartets = [q for q in all_quartets if not _is_quartet_done(q[1])]
    skipped = len(all_quartets) - len(quartets)

    if not quartets:
        print(f"All {len(all_quartets)} quartets already have results on disk — nothing to do.")
        sys.exit(0)

    num_to_process = len(quartets)
    print(f"Found {len(all_quartets)} test quartets. Skipping {skipped} already completed. Processing {num_to_process}.")
    print("v9 Test OpenAI: 3-stage CoT + masked diff on held-out disaster_harvey_test set")
    print(f"Model: {MODEL} | Upscale: {UPSCALE_FACTOR}x | Noise threshold: {NOISE_THRESHOLD} | Amplify: {AMPLIFY_FACTOR}x")
    print(f"Workers: {QUARTET_WORKERS} quartets x {BUILDING_WORKERS} buildings")
    time.sleep(2)

    all_results = []
    quartet_results = {}
    stopped = False

    pool = ThreadPoolExecutor(max_workers=QUARTET_WORKERS)
    futures: dict = {}
    try:
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
            except _StopProcessing:
                stopped = True
                print(f"\n!! Aborting: rate limit / insufficient credits detected while processing {name}")
                for f in futures:
                    f.cancel()
                break
            except Exception as e:
                print(f"\nERROR processing {name}: {e}")
    except KeyboardInterrupt:
        print("\nInterrupted! Cancelling pending tasks...")
        for future in futures:
            future.cancel()
        pool.shutdown(wait=False, cancel_futures=True)
        stopped = True
    finally:
        pool.shutdown(wait=True, cancel_futures=True)

    print(f"\n{'='*60}")
    if stopped:
        reason = _stop_reason[0] or "user interrupt"
        print(f"RUN ABORTED: {reason}")
    print(f"Quartets finished: {len(quartet_results)}/{num_to_process}")

    if all_results:
        correct = sum(1 for r in all_results if r["given"]["subtype"] == r["predicted"]["subtype"])
        total = len(all_results)
        print(f"Overall Accuracy: {correct}/{total} ({100 * correct / total:.1f}%)")
        log_accuracy("v9_test_openai", quartet_results, all_results)
    else:
        print("No building results collected — nothing to log.")

    if stopped:
        sys.exit(1)


if __name__ == "__main__":
    main()
