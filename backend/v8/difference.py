"""Enhanced difference image for v8.

Changes from v7:
- Higher noise threshold (50) — only real structural shifts show as bright
- Red polygon outline drawn onto the diff image so VLM knows the target area
- No histogram equalization, no color diff — clean grayscale threshold+amplify
"""

import os

import numpy as np
from PIL import Image, ImageDraw

DIFF_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output_image", "diff_v8")
os.makedirs(DIFF_OUTPUT_DIR, exist_ok=True)


def compute_difference(
    pre_path: str,
    post_path: str,
    polygon_coords: list[tuple[float, float]] | None = None,
    noise_threshold: int = 50,
    amplify_factor: float = 3.0,
) -> str:
    """Compute thresholded + amplified difference image with red outline.

    Args:
        pre_path: Path to pre-disaster image.
        post_path: Path to post-disaster image.
        polygon_coords: List of (x, y) tuples for the building polygon in
            crop-local coordinates. If provided, drawn as red outline on diff.
        noise_threshold: Pixel differences below this are zeroed out.
            Set to 50 (up from 30 in v7) — only significant color/structural
            shifts survive. Similar color ranges stay black.
        amplify_factor: Remaining differences multiplied by this and clipped to 255.

    Returns:
        Path to saved diff image.
    """
    pre = np.array(Image.open(pre_path).convert("L"), dtype=np.float32)
    post = np.array(Image.open(post_path).convert("L"), dtype=np.float32)

    diff = np.abs(pre - post)

    # Zero out noise — higher threshold means only real shifts appear
    diff[diff < noise_threshold] = 0

    # Amplify remaining signal
    diff = np.clip(diff * amplify_factor, 0, 255).astype(np.uint8)

    # Convert to RGB so we can draw a red outline
    diff_img = Image.fromarray(diff).convert("RGB")

    # Draw red polygon outline
    if polygon_coords:
        draw = ImageDraw.Draw(diff_img)
        draw.polygon(polygon_coords, outline="red", width=2)

    # Derive output name
    base = os.path.basename(pre_path)
    for suffix in ("_pre_up2x.png", "_pre_up3x.png", "_pre_up4x.png", "_pre.png"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    out = os.path.join(DIFF_OUTPUT_DIR, f"{base}_diff.png")
    diff_img.save(out)
    return out
