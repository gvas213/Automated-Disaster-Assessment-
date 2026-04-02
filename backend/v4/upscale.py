"""Image upscaling for improved VLM detail recognition.

Research shows 2-4x upscaling significantly improves damage classification
accuracy by making subtle structural details more visible to VLMs.
"""

import os

from PIL import Image

UPSCALE_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output_image", "upscaled")
os.makedirs(UPSCALE_OUTPUT_DIR, exist_ok=True)


def upscale_image(input_path: str, scale: int = 2) -> str:
    """Upscale an image using Lanczos resampling.

    Args:
        input_path: Path to the source image.
        scale: Upscale factor (2 = double resolution).

    Returns:
        Path to the saved upscaled image.
    """
    img = Image.open(input_path).convert("RGB")
    new_size = (img.width * scale, img.height * scale)
    upscaled = img.resize(new_size, Image.LANCZOS)

    name = os.path.basename(input_path).replace(".png", f"_up{scale}x.png")
    output_path = os.path.join(UPSCALE_OUTPUT_DIR, name)
    upscaled.save(output_path)
    return output_path
