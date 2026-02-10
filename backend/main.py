import base64
import json
import os
import sys

from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()
client = OpenAI()

# --- Configuration ---
INPUT_DIR = os.path.join(os.path.dirname(__file__), "test_images")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output_images")
os.makedirs(OUTPUT_DIR, exist_ok=True)

DETECTION_PROMPT = """You are given two images of the same location. The first image is BEFORE a natural disaster. The second image is AFTER the disaster.

Compare both images carefully. Identify all visible damage in the AFTER image by comparing it to the BEFORE image.

For each area of damage, return a JSON array of objects with these fields:
- "label": short description of the damage (e.g. "collapsed roof", "flooded road", "fallen tree", "structural crack", "debris field")
- "severity": one of "minor", "moderate", "severe"
- "box": [x_min, y_min, x_max, y_max] as percentages (0-100) of the AFTER image's width and height

Return ONLY the raw JSON array, no markdown, no explanation. Example:
[{"label": "collapsed roof", "severity": "severe", "box": [10, 5, 45, 30]}, {"label": "flooded road", "severity": "moderate", "box": [0, 60, 100, 95]}]
"""

# Color palette by severity
SEVERITY_COLORS = {
    "minor": (255, 200, 0),     # yellow
    "moderate": (255, 120, 0),  # orange
    "severe": (255, 0, 0),      # red
}
DEFAULT_COLOR = (0, 100, 255)


def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_mime(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    elif ext == ".png":
        return "image/png"
    elif ext == ".webp":
        return "image/webp"
    return "image/jpeg"


def detect_damage(before_path: str, after_path: str) -> list[dict]:
    before_b64 = encode_image(before_path)
    after_b64 = encode_image(after_path)

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": DETECTION_PROMPT},
                {
                    "type": "input_image",
                    "image_url": f"data:{get_mime(before_path)};base64,{before_b64}",
                },
                {
                    "type": "input_image",
                    "image_url": f"data:{get_mime(after_path)};base64,{after_b64}",
                },
            ],
        }],
    )

    raw = response.output_text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw)


def annotate_image(image_path: str, detections: list[dict], output_path: str):
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    try:
        font_size = max(14, int(min(w, h) * 0.02))
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

    for det in detections:
        severity = det.get("severity", "moderate")
        color = SEVERITY_COLORS.get(severity, DEFAULT_COLOR)
        box_pct = det["box"]  # [x_min%, y_min%, x_max%, y_max%]
        x1 = int(box_pct[0] / 100 * w)
        y1 = int(box_pct[1] / 100 * h)
        x2 = int(box_pct[2] / 100 * w)
        y2 = int(box_pct[3] / 100 * h)

        # Draw bounding box
        outline_width = max(2, int(min(w, h) * 0.004))
        draw.rectangle([x1, y1, x2, y2], outline=color, width=outline_width)

        # Draw label with severity
        label = f"{det['label']} [{severity}]"
        bbox = font.getbbox(label)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        padding = 4
        label_y = max(0, y1 - text_h - padding * 2)
        draw.rectangle(
            [x1, label_y, x1 + text_w + padding * 2, label_y + text_h + padding * 2],
            fill=color,
        )
        draw.text((x1 + padding, label_y + padding), label, fill=(255, 255, 255), font=font)

    img.save(output_path)
    print(f"Saved annotated image to {output_path}")


def find_pairs(input_dir: str) -> list[tuple[str, str]]:
    """Find before/after image pairs.

    Expected naming convention:
      <name>_before.jpg  and  <name>_after.jpg
    """
    files = os.listdir(input_dir)
    after_files = [f for f in files if "_after" in f.lower()]
    pairs = []

    for after_file in after_files:
        name, ext = os.path.splitext(after_file)
        base = name.lower().replace("_after", "")

        # Find matching before file
        for f in files:
            fname, fext = os.path.splitext(f)
            if "_before" in f.lower() and fname.lower().replace("_before", "") == base:
                pairs.append((
                    os.path.join(input_dir, f),
                    os.path.join(input_dir, after_file),
                ))
                break

    return pairs


def main():
    pairs = find_pairs(INPUT_DIR)

    if not pairs:
        print(f"No before/after image pairs found in {INPUT_DIR}.")
        print("Expected naming: <name>_before.jpg and <name>_after.jpg")
        print("Example: flood_before.jpg, flood_after.jpg")
        sys.exit(1)

    for before_path, after_path in pairs:
        before_name = os.path.basename(before_path)
        after_name = os.path.basename(after_path)
        output_path = os.path.join(OUTPUT_DIR, f"annotated_{after_name}")

        print(f"\nComparing: {before_name} -> {after_name}")
        detections = detect_damage(before_path, after_path)
        print(f"  Found {len(detections)} damage areas:")
        for det in detections:
            print(f"    - {det['label']} [{det.get('severity', '?')}] at {det['box']}")

        # Annotate only the AFTER image
        annotate_image(after_path, detections, output_path)


if __name__ == "__main__":
    main()
