import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv

from cropping import find_disaster_quartets, crop_buildings, build_geojson
from prompt import PROMPT_V1
from accuracy_log import log_accuracy

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

DISASTER_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "disaster-output")
os.makedirs(DISASTER_OUTPUT_DIR, exist_ok=True)


def assess_damage(pre_crop_path: str, post_crop_path: str) -> dict:
    pre_img = Image.open(pre_crop_path).convert("RGB")
    post_img = Image.open(post_crop_path).convert("RGB")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[PROMPT_V1, pre_img, post_img],
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw)


def process_quartet(pre_img_path, post_img_path, post_json_path) -> list[dict]:
    base = os.path.splitext(os.path.basename(post_img_path))[0].replace("_post_disaster", "")
    print(f"\nProcessing: {base}")

    crops = crop_buildings(pre_img_path, post_img_path, post_json_path)

    with open(post_json_path) as f:
        gt_data = json.load(f)
    gt_features = {feat["properties"]["uid"]: feat["properties"] for feat in gt_data["features"]["xy"]}

    results = []
    for pre_crop, post_crop, uid, ground_truth in crops:
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
        results.append(entry)

        print(f"    VLM says: {prediction['feature_type']} / {prediction['subtype']}")
        match = "MATCH" if prediction["subtype"] == ground_truth else "MISMATCH"
        print(f"    {match}")

    # Save per-quartet results
    output_path = os.path.join(DISASTER_OUTPUT_DIR, f"{base}_gemini_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {output_path}")

    # Save GeoJSON
    build_geojson(post_json_path, results, f"{base}_gemini_results")

    return results


def main():
    quartets = find_disaster_quartets()
    if not quartets:
        print("No disaster quartets found.")
        sys.exit(1)

    num_to_process = min(2, len(quartets))
    print(f"Found {num_to_process} quartets, processing first {num_to_process} across 3 threads.")

    all_results = []
    quartet_results = {}
    pool = ThreadPoolExecutor(max_workers=3)
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
        log_accuracy("gemini_api", quartet_results, all_results)


if __name__ == "__main__":
    main()
