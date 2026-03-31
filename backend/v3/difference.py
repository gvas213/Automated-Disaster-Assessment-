"""Difference image computation for pre/post disaster crop pairs.

Computes absolute pixel-level difference images that highlight what actually
changed between pre and post captures, suppressing artifacts like shadow
changes, vegetation color shifts, and lighting differences.
"""

import os

import numpy as np
from PIL import Image, ImageOps

DIFF_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output_image", "diff")
os.makedirs(DIFF_OUTPUT_DIR, exist_ok=True)


def compute_difference(
    pre_crop_path: str,
    post_crop_path: str,
    grayscale: bool = True,
    enhance: bool = True,
) -> str:
    """Compute absolute difference image between pre and post crops.

    Output filename is derived from the pre-crop filename with "_pre" replaced
    by "_diff" (e.g. hurricane-harvey_00000003_abc123_pre.png -> ..._diff.png).

    Args:
        pre_crop_path: Path to pre-disaster crop.
        post_crop_path: Path to post-disaster crop.
        grayscale: Convert to grayscale before differencing to reduce
                   color-based false positives (vegetation seasons, etc.)
        enhance: Apply histogram equalization to boost subtle differences.

    Returns:
        Path to the saved difference image.
    """
    pre = Image.open(pre_crop_path).convert("RGB")
    post = Image.open(post_crop_path).convert("RGB")

    if grayscale:
        pre_arr = np.array(pre.convert("L"), dtype=np.float32)
        post_arr = np.array(post.convert("L"), dtype=np.float32)
    else:
        pre_arr = np.array(pre, dtype=np.float32)
        post_arr = np.array(post, dtype=np.float32)

    # Absolute difference
    diff_arr = np.abs(pre_arr - post_arr)

    # Normalize to 0-255
    if diff_arr.max() > 0:
        diff_arr = (diff_arr / diff_arr.max() * 255).astype(np.uint8)
    else:
        diff_arr = diff_arr.astype(np.uint8)

    diff_img = Image.fromarray(diff_arr)

    # Histogram equalization to make subtle changes more visible
    if enhance and grayscale:
        diff_img = ImageOps.equalize(diff_img)

    # Derive name from pre-crop: ..._pre.png -> ..._diff.png
    diff_name = os.path.basename(pre_crop_path).replace("_pre.png", "_diff.png")
    output_path = os.path.join(DIFF_OUTPUT_DIR, diff_name)
    diff_img.save(output_path)
    return output_path
