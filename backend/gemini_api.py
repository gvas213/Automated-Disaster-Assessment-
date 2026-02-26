import json
import os
import sys
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv

from cropping import find_disaster_quartets, crop_buildings

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

DISASTER_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "disaster-output")
os.makedirs(DISASTER_OUTPUT_DIR, exist_ok=True)

DAMAGE_PROMPT = """You are given two cropped satellite images of the same area. The first image is BEFORE a natural disaster. The second image is AFTER the disaster.

The structure to assess is highlighted with a RED outline in both images. Focus on the building/structure inside the red outline and compare its condition before and after.

Return ONLY a raw JSON object (no markdown, no explanation) with these fields:
- "feature_type": the type of structure (e.g. "building", "lot", "land", "farm", "road", "bridge")
- "subtype": the damage level, one of: "no-damage", "minor-damage", "major-damage", "destroyed"

Example:
{"feature_type": "building", "subtype": "minor-damage"}
"""


def assess_damage(pre_crop_path: str, post_crop_path: str) -> dict:
    pre_img = Image.open(pre_crop_path).convert("RGB")
    post_img = Image.open(post_crop_path).convert("RGB")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[DAMAGE_PROMPT, pre_img, post_img],
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

    return results


def main():
    quartets = find_disaster_quartets()
    if not quartets:
        print("No disaster quartets found.")
        sys.exit(1)

    num_to_process = min(5, len(quartets))
    print(f"Found {len(quartets)} quartets, processing first {num_to_process}.")

    all_results = []
    try:
        for i in range(num_to_process):
            pre_img, post_img, pre_json, post_json = quartets[i]
            results = process_quartet(pre_img, post_img, post_json)
            all_results.extend(results)
    except KeyboardInterrupt:
        print("\nInterrupted!")

    # Overall accuracy summary
    if all_results:
        correct = sum(1 for r in all_results if r["given"]["subtype"] == r["predicted"]["subtype"])
        print(f"\nOverall Accuracy: {correct}/{len(all_results)} ({100 * correct / len(all_results):.1f}%)")


if __name__ == "__main__":
    main()
