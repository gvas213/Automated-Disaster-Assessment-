"""v_client_1: User-facing building damage assessment.

Same pipeline as v9 (3-stage CoT + masked diff + cost estimate) but designed
to be called directly from a FastAPI endpoint. Takes two image paths (before
and after), returns a human-readable result dict.

No ground-truth comparison, no accuracy logging, no batch processing.
Intermediate files go into a per-call temp directory and are cleaned up on exit.
"""

import base64
import json
import os
import sys
import tempfile

from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image, ImageDraw
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from v_client_1.prompts import DESCRIBE_PRE_PROMPT, DESCRIBE_DIFF_PROMPT, EVALUATE_POST_PROMPT, COST_PROMPT

load_dotenv()
client = OpenAI()

MODEL = "gpt-4.1-mini"
UPSCALE_FACTOR = 2
NOISE_THRESHOLD = 50
AMPLIFY_FACTOR = 3.0

DAMAGE_LABELS = {
    "no-damage": "No Damage",
    "minor-damage": "Minor Damage",
    "major-damage": "Major Damage",
    "destroyed": "Destroyed",
}


def _encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _call_vlm(prompt: str, image_paths: list[str]) -> dict:
    content = [{"type": "input_text", "text": prompt}]
    for img_path in image_paths:
        content.append({
            "type": "input_image",
            "image_url": f"data:image/png;base64,{_encode_image(img_path)}",
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


def _upscale(input_path: str, scale: int, out_dir: str) -> str:
    img = Image.open(input_path).convert("RGB")
    upscaled = img.resize((img.width * scale, img.height * scale), Image.LANCZOS)
    name = os.path.splitext(os.path.basename(input_path))[0] + f"_up{scale}x.png"
    out_path = os.path.join(out_dir, name)
    upscaled.save(out_path)
    return out_path


def _compute_diff(
    pre_path: str,
    post_path: str,
    out_dir: str,
    polygon_coords: list[tuple[float, float]] | None = None,
) -> str:
    """Absolute pixel diff, noise-thresholded and amplified.

    If polygon_coords are provided, masks the diff to the polygon interior
    (everything outside is blacked out) and draws a red outline, matching v9
    behaviour. Otherwise uses the full image.
    """
    pre = np.array(Image.open(pre_path).convert("L"), dtype=np.float32)
    post = np.array(Image.open(post_path).convert("L"), dtype=np.float32)

    diff = np.abs(pre - post)
    diff[diff < NOISE_THRESHOLD] = 0
    diff = np.clip(diff * AMPLIFY_FACTOR, 0, 255).astype(np.uint8)

    diff_img = Image.fromarray(diff)

    if polygon_coords:
        mask = Image.new("L", diff_img.size, 0)
        ImageDraw.Draw(mask).polygon(polygon_coords, fill=255)
        diff_img = Image.composite(diff_img, Image.new("L", diff_img.size, 0), mask)

    diff_img = diff_img.convert("RGB")

    if polygon_coords:
        ImageDraw.Draw(diff_img).polygon(polygon_coords, outline="red", width=2)

    out_path = os.path.join(out_dir, "diff.png")
    diff_img.save(out_path)
    return out_path


def _estimate_cost(damage_type: str, pre_description: str, reasoning: str) -> tuple[int, str]:
    if damage_type == "no-damage":
        return 0, "No damage — no repair cost."

    prompt = COST_PROMPT.format(
        damage_type=damage_type,
        pre_description=pre_description or "No description available.",
        reasoning=reasoning or "No reasoning available.",
    )
    response = client.responses.create(
        model=MODEL,
        input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
    )
    raw = response.output_text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]
    result = json.loads(raw)
    return int(result["cost_usd"]), result.get("cost_reasoning", "")


def assess_user_images(
    before_path: str,
    after_path: str,
    polygon_coords: list[tuple[float, float]] | None = None,
) -> dict:
    """Assess hurricane damage from user-uploaded before/after images.

    Args:
        before_path:     Path to the pre-disaster image.
        after_path:      Path to the post-disaster image.
        polygon_coords:  Optional list of (x, y) pixel coordinates marking the
                         building footprint in the original (non-upscaled) image.
                         When provided, the diff is masked to the building interior
                         and a red outline is drawn, matching v9 behaviour.
                         When None, the full image diff is used.

    Returns:
        A dict with human-readable damage assessment and cost estimate,
        ready to be returned directly from a FastAPI endpoint.
    """
    with tempfile.TemporaryDirectory() as tmp:
        # Upscale both images
        pre_up = _upscale(before_path, UPSCALE_FACTOR, tmp)
        post_up = _upscale(after_path, UPSCALE_FACTOR, tmp)

        # Scale polygon coords to match upscaled image, if provided
        scaled_coords = None
        if polygon_coords:
            scaled_coords = [(x * UPSCALE_FACTOR, y * UPSCALE_FACTOR) for x, y in polygon_coords]

        diff_path = _compute_diff(pre_up, post_up, tmp, polygon_coords=scaled_coords)

        # Stage 1: Describe pre-disaster building
        try:
            result = _call_vlm(DESCRIBE_PRE_PROMPT, [pre_up])
            pre_description = result.get("description", "A building with a roof.")
        except Exception as e:
            pre_description = f"Description unavailable ({e})."

        # Stage 2: Describe the diff image
        diff_prompt = DESCRIBE_DIFF_PROMPT.format(pre_description=pre_description)
        try:
            result = _call_vlm(diff_prompt, [diff_path])
            diff_description = result.get("description", "Unable to analyze changes.")
        except Exception as e:
            diff_description = f"Change analysis unavailable ({e})."

        # Stage 3: Evaluate with all three images
        eval_prompt = EVALUATE_POST_PROMPT.format(
            pre_description=pre_description,
            diff_description=diff_description,
        )
        try:
            result = _call_vlm(eval_prompt, [pre_up, post_up, diff_path])
            subtype = result.get("subtype", "no-damage")
            confidence = int(result.get("confidence", 5))
            reasoning = result.get("reasoning", "")
        except Exception as e:
            subtype = "no-damage"
            confidence = 5
            reasoning = f"Evaluation failed ({e})."

        # Stage 4: Estimate repair cost
        try:
            cost_usd, cost_reasoning = _estimate_cost(subtype, pre_description, reasoning)
        except Exception as e:
            cost_usd = None
            cost_reasoning = f"Cost estimation failed ({e})."

    return {
        "damage_level": DAMAGE_LABELS.get(subtype, subtype),
        "confidence": confidence,
        "building_description": pre_description,
        "change_analysis": diff_description,
        "damage_assessment": reasoning,
        "cost_estimate_usd": cost_usd,
        "cost_reasoning": cost_reasoning,
    }
