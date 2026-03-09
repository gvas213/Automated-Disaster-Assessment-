import json
import os
import sys

import torch
from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig

from cropping import find_disaster_quartets, crop_buildings, build_geojson
from prompt import DEFAULT_PROMPT

DISASTER_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "disaster-output")
os.makedirs(DISASTER_OUTPUT_DIR, exist_ok=True)

MODEL_ID = "Qwen/Qwen3-VL-8B-Instruct"
MODEL_CACHE_DIR = os.path.join(os.path.dirname(__file__), "hf_models")


def load_model():
    """Load Qwen3-VL-8B and processor onto GPU."""
    print(f"Loading model: {MODEL_ID} (cache: {MODEL_CACHE_DIR})")
    processor = AutoProcessor.from_pretrained(MODEL_ID, cache_dir=MODEL_CACHE_DIR)

    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL_ID,
        dtype=torch.bfloat16,
        device_map="auto",
        cache_dir=MODEL_CACHE_DIR,
        quantization_config=quantization_config,
    )
    print(f"Model loaded (4-bit quantized) on {model.device}")
    return processor, model


def assess_damage(processor, model, pre_crop_path: str, post_crop_path: str) -> dict:
    """Send pre/post crop pair to the local VLM and parse the JSON response."""
    from PIL import Image

    pre_img = Image.open(pre_crop_path).convert("RGB")
    post_img = Image.open(post_crop_path).convert("RGB")

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": pre_img},
                {"type": "image", "image": post_img},
                {"type": "text", "text": DEFAULT_PROMPT},
            ],
        }
    ]

    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)

    with torch.no_grad():
        generated_ids = model.generate(**inputs, max_new_tokens=256)

    generated_ids_trimmed = [
        out_ids[len(in_ids):]
        for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    raw = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )[0].strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw)


def process_quartet(processor, model, pre_img_path, post_img_path, post_json_path) -> list[dict]:
    """Process a single quartet: crop buildings, assess damage, return results."""
    base = os.path.splitext(os.path.basename(post_img_path))[0].replace("_post_disaster", "")
    print(f"\nProcessing: {base}")

    crops = crop_buildings(pre_img_path, post_img_path, post_json_path)

    with open(post_json_path) as f:
        gt_data = json.load(f)
    gt_features = {feat["properties"]["uid"]: feat["properties"] for feat in gt_data["features"]["xy"]}

    results = []
    for pre_crop, post_crop, uid, ground_truth in crops:
        print(f"\n  Assessing {uid} (ground truth: {ground_truth})...")
        prediction = assess_damage(processor, model, pre_crop, post_crop)

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
    output_path = os.path.join(DISASTER_OUTPUT_DIR, f"{base}_hf_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {output_path}")

    # Save GeoJSON
    build_geojson(post_json_path, results, f"{base}_hf_results")

    return results


def main():
    quartets = find_disaster_quartets()
    if not quartets:
        print("No disaster quartets found.")
        sys.exit(1)

    processor, model = load_model()

    num_to_process = min(5, len(quartets))
    print(f"Found {len(quartets)} quartets, processing first {num_to_process}.")

    # No threading — GPU inference is sequential on one device
    all_results = []
    try:
        for i in range(num_to_process):
            pre_img, post_img, pre_json, post_json = quartets[i]
            results = process_quartet(processor, model, pre_img, post_img, post_json)
            all_results.extend(results)
    except KeyboardInterrupt:
        print("\nInterrupted!")

    # Overall accuracy summary
    if all_results:
        correct = sum(1 for r in all_results if r["given"]["subtype"] == r["predicted"]["subtype"])
        print(f"\nOverall Accuracy: {correct}/{len(all_results)} ({100 * correct / len(all_results):.1f}%)")


if __name__ == "__main__":
    main()
