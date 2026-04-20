"""Enhanced difference image for v7.

Key improvement: threshold + amplify.
- Suppress low-variance noise (compression artifacts, slight alignment, lighting)
  by zeroing out pixels below a threshold.
- Blow up the remaining high-variance spots so real damage is unmistakable.

The result: no-damage buildings get a nearly BLACK diff image (clear signal to VLM),
while damaged buildings get bright hotspots exactly where the damage is.
"""

import os

import numpy as np
from PIL import Image

DIFF_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output_image", "diff_v7")
os.makedirs(DIFF_OUTPUT_DIR, exist_ok=True)


def compute_difference(
    pre_path: str,
    post_path: str,
    noise_threshold: int = 30,
    amplify_factor: float = 3.0,
) -> str:
    """Compute thresholded + amplified difference image.

    Args:
        pre_path: Path to pre-disaster image.
        post_path: Path to post-disaster image.
        noise_threshold: Pixel difference values below this are zeroed out.
            Typical satellite noise/compression artifacts are 10-25 levels.
            Default 30 suppresses most noise while preserving real structural changes.
        amplify_factor: Remaining differences are multiplied by this factor
            and clipped to 255. Makes real damage hotspots much brighter.

    Returns:
        Path to saved diff image.
    """
    pre = np.array(Image.open(pre_path).convert("L"), dtype=np.float32)
    post = np.array(Image.open(post_path).convert("L"), dtype=np.float32)

    diff = np.abs(pre - post)

    # Zero out noise below threshold
    diff[diff < noise_threshold] = 0

    # Amplify remaining signal
    diff = np.clip(diff * amplify_factor, 0, 255).astype(np.uint8)

    img = Image.fromarray(diff)

    # Derive output name
    base = os.path.basename(pre_path)
    for suffix in ("_pre_up2x.png", "_pre_up3x.png", "_pre_up4x.png", "_pre.png"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    out = os.path.join(DIFF_OUTPUT_DIR, f"{base}_diff.png")
    img.save(out)
    return out
