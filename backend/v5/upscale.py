"""Image upscaling for v5 pipeline.

Supports variable scale factors (including 1 = no upscale) so each vote
can see the image at a different resolution.
"""

import os

from PIL import Image

UPSCALE_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output_image", "upscaled_v5")
os.makedirs(UPSCALE_OUTPUT_DIR, exist_ok=True)


def upscale_image(input_path: str, scale: int = 2) -> str:
    """Upscale an image using Lanczos resampling.

    Args:
        input_path: Path to the source image.
        scale: Upscale factor. 1 = no upscale (just copies).

    Returns:
        Path to the saved image.
    """
    img = Image.open(input_path).convert("RGB")
    if scale > 1:
        new_size = (img.width * scale, img.height * scale)
        img = img.resize(new_size, Image.LANCZOS)

    name = os.path.basename(input_path).replace(".png", f"_up{scale}x.png")
    output_path = os.path.join(UPSCALE_OUTPUT_DIR, name)
    img.save(output_path)
    return output_path
