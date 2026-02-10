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

DETECTION_PROMPT = """Analyze this image and identify every piece of clothing or accessory worn by anyone in the image.

For each item, return a JSON array of objects with these fields:
- "label": short name of the clothing item (e.g. "red jacket", "blue jeans", "white sneakers")
- "box": [x_min, y_min, x_max, y_max] as percentages (0-100) of the image width and height

Return ONLY the raw JSON array, no markdown, no explanation. Example:
[{"label": "red jacket", "box": [10, 5, 45, 60]}, {"label": "blue jeans", "box": [15, 55, 42, 95]}]
"""

# Color palette for annotations
COLORS = [
    (255, 0, 0),
    (0, 200, 0),
    (0, 100, 255),
    (255, 165, 0),
    (200, 0, 200),
    (0, 200, 200),
    (255, 255, 0),
    (128, 0, 255),
]


def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def detect_clothing(image_path: str) -> list[dict]:
    ext = os.path.splitext(image_path)[1].lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
    b64 = encode_image(image_path)

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": DETECTION_PROMPT},
                {"type": "input_image", "image_url": f"data:{mime};base64,{b64}"},
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

    # Try to load a readable font, fall back to default
    try:
        font_size = max(14, int(min(w, h) * 0.02))
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

    for i, det in enumerate(detections):
        color = COLORS[i % len(COLORS)]
        box_pct = det["box"]  # [x_min%, y_min%, x_max%, y_max%]
        x1 = int(box_pct[0] / 100 * w)
        y1 = int(box_pct[1] / 100 * h)
        x2 = int(box_pct[2] / 100 * w)
        y2 = int(box_pct[3] / 100 * h)

        # Draw bounding box
        outline_width = max(2, int(min(w, h) * 0.003))
        draw.rectangle([x1, y1, x2, y2], outline=color, width=outline_width)

        # Draw label background
        label = det["label"]
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


def main():
    images = [
        f for f in os.listdir(INPUT_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]

    if not images:
        print(f"No images found in {INPUT_DIR}. Add some images and try again.")
        sys.exit(1)

    for filename in images:
        input_path = os.path.join(INPUT_DIR, filename)
        output_path = os.path.join(OUTPUT_DIR, f"annotated_{filename}")

        print(f"\nProcessing: {filename}")
        detections = detect_clothing(input_path)
        print(f"  Found {len(detections)} clothing items:")
        for det in detections:
            print(f"    - {det['label']} at {det['box']}")

        annotate_image(input_path, detections, output_path)


if __name__ == "__main__":
    main()
