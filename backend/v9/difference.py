"""Masked difference image for v9.

Key change from v8: everything OUTSIDE the building polygon is blacked out.
The VLM only sees changes inside the building footprint — no surrounding
noise from neighboring buildings, roads, or vegetation.

The red outline is still drawn so the VLM knows the boundary.
"""

import os

import numpy as np
from PIL import Image, ImageDraw

DIFF_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output_image", "diff_v9")
os.makedirs(DIFF_OUTPUT_DIR, exist_ok=True)


def compute_difference(
    pre_path: str,
    post_path: str,
    polygon_coords: list[tuple[float, float]] | None = None,
    noise_threshold: int = 50,
    amplify_factor: float = 3.0,
) -> str:
    """Compute masked, thresholded, amplified difference image.

    Everything outside the polygon is blacked out. Only changes inside the
    building footprint survive.

    Args:
        pre_path: Path to pre-disaster image.
        post_path: Path to post-disaster image.
        polygon_coords: List of (x, y) tuples for the building polygon in
            crop-local coordinates. Used for both masking and red outline.
        noise_threshold: Pixel differences below this are zeroed out.
        amplify_factor: Remaining differences multiplied by this and clipped to 255.

    Returns:
        Path to saved diff image.
    """
    pre = np.array(Image.open(pre_path).convert("L"), dtype=np.float32)
    post = np.array(Image.open(post_path).convert("L"), dtype=np.float32)

    diff = np.abs(pre - post)

    # Zero out noise
    diff[diff < noise_threshold] = 0

    # Amplify remaining signal
    diff = np.clip(diff * amplify_factor, 0, 255).astype(np.uint8)

    diff_img = Image.fromarray(diff)

    # Mask everything outside the polygon to black
    if polygon_coords:
        mask = Image.new("L", diff_img.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.polygon(polygon_coords, fill=255)
        # Apply mask: keep pixels inside polygon, black outside
        masked = Image.composite(diff_img, Image.new("L", diff_img.size, 0), mask)
        diff_img = masked

    # Convert to RGB for red outline
    diff_img = diff_img.convert("RGB")

    # Draw red outline on top
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
