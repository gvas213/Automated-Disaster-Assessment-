"""Mexico earthquake damage assessment — same strategy as main.py (GPT-4.1-mini, PROMPT_V2 style).

Points at the mexico-earthquake dataset instead of hurricane-harvey.
"""

import base64
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI
from dotenv import load_dotenv

# Add parent to path for shared modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from cropping import parse_wkt_polygon, padded_bbox, build_geojson as _build_geojson_base
from accuracy_log import log_accuracy

load_dotenv()
client = OpenAI()

# --- Paths ---
DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mexico-earthquake")
IMAGES_DIR = os.path.join(DATASET_DIR, "img")
JSON_DIR = os.path.join(DATASET_DIR, "json")
CROP_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "cropped")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
GEOJSON_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output-geojson")
os.makedirs(CROP_OUTPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(GEOJSON_OUTPUT_DIR, exist_ok=True)

# --- Prompt (adapted from PROMPT_V2 for earthquake context) ---
PROMPT = """You are given two cropped satellite images of the same area. Image 1 is BEFORE an EARTHQUAKE. Image 2 is AFTER the earthquake.

The RED outline indicates the target structure area, but the AFTER crop/registration may be offset: the same building may have shifted partially or entirely outside the red outline, or the outline may now cover debris/empty ground. Treat this as a valid signal and use surrounding anchors (roads, lot boundaries, vegetation lines, neighboring roofs) to identify the same structure.

Use earthquake damage heuristics:
- Collapse: pancake collapse, partial floor collapse, leaning/tilted structure, rubble pile.
- Roof damage: roof caved in, tiles displaced, holes visible from above.
- Wall failure: exterior walls crumbled, facade fallen, visible interior from above.
- Foundation: building footprint distorted, slab shifted, ground fissures through structure.
- Debris: rubble field replacing structure, scattered concrete/masonry fragments.

Assign:
- no-damage: footprint/roof intact and consistent.
- minor-damage: small cracks visible, minor debris, slight discoloration or small roof changes.
- major-damage: substantial roof collapse, partial structural failure, heavy debris, clear deformation.
- destroyed: structure gone or reduced to rubble; only slab/foundation remains; building pancaked or collapsed entirely.

Return ONLY a raw JSON object:
{"feature_type": "...", "subtype": "..."}"""


def find_quartets() -> list[tuple[str, str, str, str]]:
    """Build list of (pre_image, post_image, pre_json, post_json) tuples for mexico-earthquake."""
    quartets = []
    for fname in sorted(os.listdir(IMAGES_DIR)):
        if not fname.endswith("_pre_disaster.png"):
            continue
        base = fname.replace("_pre_disaster.png", "")
        pre_img = os.path.join(IMAGES_DIR, f"{base}_pre_disaster.png")
        post_img = os.path.join(IMAGES_DIR, f"{base}_post_disaster.png")
        pre_json = os.path.join(JSON_DIR, f"{base}_pre_disaster.json")
        post_json = os.path.join(JSON_DIR, f"{base}_post_disaster.json")

        if all(os.path.exists(p) for p in (pre_img, post_img, pre_json, post_json)):
            quartets.append((pre_img, post_img, pre_json, post_json))

    return quartets


def crop_buildings(pre_img_path, post_img_path, post_json_path, padding: int = 150) -> list[tuple[str, str, str, str]]:
    """Crop each building from pre/post images. Same logic as cropping.py but writes to our local dirs."""
    from PIL import Image, ImageDraw

    with open(post_json_path) as f:
        data = json.load(f)

    features = data["features"]["xy"]
    pre_img = Image.open(pre_img_path)
    post_img = Image.open(post_img_path)
    base = os.path.splitext(os.path.basename(post_img_path))[0].replace("_post_disaster", "")

    img_w, img_h = pre_img.size

    results = []
    for feat in features:
        uid = feat["properties"]["uid"]
        subtype = feat["properties"]["subtype"]
        coords = parse_wkt_polygon(feat["wkt"])
        if not coords:
            continue
        box = padded_bbox(coords, img_w, img_h, padding=padding)
        x_min, y_min = box[0], box[1]

        pre_crop = pre_img.crop(box).copy()
        post_crop = post_img.crop(box).copy()

        # Draw red polygon outline shifted to crop-local coordinates
        local_coords = [(x - x_min, y - y_min) for x, y in coords]
        for crop in (pre_crop, post_crop):
            draw = ImageDraw.Draw(crop)
            draw.polygon(local_coords, outline="red", width=2)

        pre_path = os.path.join(CROP_OUTPUT_DIR, f"{base}_{uid}_pre.png")
        post_path = os.path.join(CROP_OUTPUT_DIR, f"{base}_{uid}_post.png")
        pre_crop.save(pre_path)
        post_crop.save(post_path)
        print(f"  Cropped {subtype}: {uid} -> box {box}")
        results.append((pre_path, post_path, uid, subtype))

    return results


def build_geojson(post_json_path: str, results: list[dict], output_name: str) -> str:
    """Build GeoJSON and save to our local output-geojson dir."""
    with open(post_json_path) as f:
        source = json.load(f)

    lnglat_by_uid = {}
    for feat in source["features"]["lng_lat"]:
        lnglat_by_uid[feat["properties"]["uid"]] = feat["wkt"]

    features = []
    for r in results:
        uid = r["uid"]
        wkt = lnglat_by_uid.get(uid)
        if not wkt:
            continue
        coords = parse_wkt_polygon(wkt)
        if not coords:
            continue
        ring = [[lon, lat] for lon, lat in coords]

        feature = {
            "type": "Feature",
            "properties": {
                "uid": uid,
                "cost_usd": None,
                "damage_type": r["predicted"]["subtype"],
                "description": None,
                "feature_type": r["predicted"]["feature_type"],
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [ring],
            },
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    output_path = os.path.join(GEOJSON_OUTPUT_DIR, f"{output_name}.geojson")
    with open(output_path, "w") as f:
        json.dump(geojson, f, indent=2)

    print(f"GeoJSON saved to {output_path}")
    return output_path


def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def assess_damage(pre_crop_path: str, post_crop_path: str) -> dict:
    pre_b64 = encode_image(pre_crop_path)
    post_b64 = encode_image(post_crop_path)

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": PROMPT},
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


# --- Config ---
QUARTET_WORKERS = 5
BUILDING_WORKERS = 10


def process_building(pre_crop, post_crop, uid, ground_truth, gt_features):
    """Process a single building — called in parallel from process_quartet."""
    print(f"\n  Assessing {uid} (ground truth: {ground_truth})...")
    prediction = assess_damage(pre_crop, post_crop)

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
    }

    print(f"    VLM says: {prediction['feature_type']} / {prediction['subtype']}")
    match = "MATCH" if prediction["subtype"] == ground_truth else "MISMATCH"
    print(f"    {match}")

    return entry


def process_quartet(pre_img, post_img, post_json) -> list[dict]:
    """Process a single quartet: crop buildings, assess damage in parallel, return results."""
    base = os.path.splitext(os.path.basename(post_img))[0].replace("_post_disaster", "")
    print(f"\nProcessing: {base}")

    crops = crop_buildings(pre_img, post_img, post_json)

    with open(post_json) as f:
        gt_data = json.load(f)
    gt_features = {feat["properties"]["uid"]: feat["properties"] for feat in gt_data["features"]["xy"]}

    # Level 1: parallelize buildings within this quartet
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
    output_path = os.path.join(OUTPUT_DIR, f"{base}_vlm_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {output_path}")

    # Save GeoJSON
    build_geojson(post_json, results, f"{base}_vlm_results")

    return results


def main():
    quartets = find_quartets()
    if not quartets:
        print("No mexico-earthquake quartets found.")
        sys.exit(1)
    num_to_process = min(3, len(quartets))

    print(f"Found {len(quartets)} quartets, processing first {num_to_process}.")
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

    # Overall accuracy summary
    if all_results:
        correct = sum(1 for r in all_results if r["given"]["subtype"] == r["predicted"]["subtype"])
        print(f"\nOverall Accuracy: {correct}/{len(all_results)} ({100 * correct / len(all_results):.1f}%)")
        log_accuracy("mexico_earthquake", quartet_results, all_results)


if __name__ == "__main__":
    main()
