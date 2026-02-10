import base64
import json
import os
import sys

from openai import OpenAI
from dotenv import load_dotenv

from cropping import find_disaster_quartets, crop_buildings

load_dotenv()
client = OpenAI()

DISASTER_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "disaster-output")
os.makedirs(DISASTER_OUTPUT_DIR, exist_ok=True)

DAMAGE_PROMPT = """You are given two cropped satellite images of the same building/structure. The first image is BEFORE a natural disaster. The second image is AFTER the disaster.

Compare both images carefully and assess the damage to this structure.

Return ONLY a raw JSON object (no markdown, no explanation) with these fields:
- "feature_type": the type of structure (e.g. "building", "lot", "land", "farm", "road", "bridge")
- "subtype": the damage level, one of: "no-damage", "minor-damage", "major-damage", "destroyed"

Example:
{"feature_type": "building", "subtype": "minor-damage"}
"""


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
                {"type": "input_text", "text": DAMAGE_PROMPT},
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


def main():
    quartets = find_disaster_quartets()
    if not quartets:
        print("No disaster quartets found.")
        sys.exit(1)

    # Test with first quartet only (to save credits)
    pre_img, post_img, pre_json, post_json = quartets[0]
    base = os.path.splitext(os.path.basename(post_img))[0].replace("_post_disaster", "")
    print(f"Processing: {base}")

    # Crop buildings
    crops = crop_buildings(pre_img, post_img, post_json)

    # Load ground truth JSON for the given data
    with open(post_json) as f:
        gt_data = json.load(f)
    gt_features = {feat["properties"]["uid"]: feat["properties"] for feat in gt_data["features"]["xy"]}

    # Send each cropped pair to the VLM
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

    # Save results to disaster-output/
    output_path = os.path.join(DISASTER_OUTPUT_DIR, f"{base}_vlm_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")

    # Quick accuracy summary
    correct = sum(1 for r in results if r["given"]["subtype"] == r["predicted"]["subtype"])
    print(f"Accuracy: {correct}/{len(results)} ({100 * correct / len(results):.1f}%)")


if __name__ == "__main__":
    main()
