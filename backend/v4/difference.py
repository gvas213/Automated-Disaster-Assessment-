"""Difference image computation for v4 pipeline.

Same core logic as v3 but works on upscaled images and outputs to v4 directory.
"""

import os

import numpy as np
from PIL import Image, ImageOps

DIFF_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output_image", "diff_v4")
os.makedirs(DIFF_OUTPUT_DIR, exist_ok=True)


def compute_difference(pre_path: str, post_path: str, grayscale: bool = True, enhance: bool = True) -> str:
    """Compute absolute difference image between pre and post crops.

    Output filename derived from pre-crop: _pre.png or _pre_up2x.png -> _diff.png

    Returns:
        Path to the saved difference image.
    """
    pre = Image.open(pre_path).convert("RGB")
    post = Image.open(post_path).convert("RGB")

    if grayscale:
        pre_arr = np.array(pre.convert("L"), dtype=np.float32)
        post_arr = np.array(post.convert("L"), dtype=np.float32)
    else:
        pre_arr = np.array(pre, dtype=np.float32)
        post_arr = np.array(post, dtype=np.float32)

    diff_arr = np.abs(pre_arr - post_arr)

    if diff_arr.max() > 0:
        diff_arr = (diff_arr / diff_arr.max() * 255).astype(np.uint8)
    else:
        diff_arr = diff_arr.astype(np.uint8)

    diff_img = Image.fromarray(diff_arr)

    if enhance and grayscale:
        diff_img = ImageOps.equalize(diff_img)

    # Derive name: strip _pre*.png or _post*.png suffix, append _diff.png
    base_name = os.path.basename(pre_path)
    # Handle both _pre.png and _pre_up2x.png
    for suffix in ("_pre_up2x.png", "_pre_up3x.png", "_pre_up4x.png", "_pre.png"):
        if base_name.endswith(suffix):
            base_name = base_name[: -len(suffix)]
            break
    diff_name = f"{base_name}_diff.png"

    output_path = os.path.join(DIFF_OUTPUT_DIR, diff_name)
    diff_img.save(output_path)
    return output_path
