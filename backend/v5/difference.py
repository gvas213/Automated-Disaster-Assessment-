"""Difference image computation for v5 pipeline.

Three diff methods to give each vote a genuinely different view:
  1. Grayscale + histogram equalization (v4 style)
  2. RGB color diff (preserves color-based damage signals)
  3. Raw grayscale WITHOUT equalization (avoids noise amplification)
"""

import os

import numpy as np
from PIL import Image, ImageOps

DIFF_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output_image", "diff_v5")
os.makedirs(DIFF_OUTPUT_DIR, exist_ok=True)


def _normalize(arr: np.ndarray) -> np.ndarray:
    """Scale array to 0-255 range."""
    if arr.max() > 0:
        return (arr / arr.max() * 255).astype(np.uint8)
    return arr.astype(np.uint8)


def compute_diff_grayscale_equalized(pre_path: str, post_path: str, tag: str = "") -> str:
    """Grayscale absolute diff with histogram equalization (v4 method)."""
    pre = np.array(Image.open(pre_path).convert("L"), dtype=np.float32)
    post = np.array(Image.open(post_path).convert("L"), dtype=np.float32)
    diff = _normalize(np.abs(pre - post))
    img = ImageOps.equalize(Image.fromarray(diff))

    name = _output_name(pre_path, f"diff_gray_eq{tag}")
    out = os.path.join(DIFF_OUTPUT_DIR, name)
    img.save(out)
    return out


def compute_diff_rgb(pre_path: str, post_path: str, tag: str = "") -> str:
    """RGB color absolute diff — preserves color-based damage signals."""
    pre = np.array(Image.open(pre_path).convert("RGB"), dtype=np.float32)
    post = np.array(Image.open(post_path).convert("RGB"), dtype=np.float32)
    diff = _normalize(np.abs(pre - post))
    img = Image.fromarray(diff)

    name = _output_name(pre_path, f"diff_rgb{tag}")
    out = os.path.join(DIFF_OUTPUT_DIR, name)
    img.save(out)
    return out


def compute_diff_grayscale_raw(pre_path: str, post_path: str, tag: str = "") -> str:
    """Raw grayscale absolute diff WITHOUT equalization — avoids noise amplification."""
    pre = np.array(Image.open(pre_path).convert("L"), dtype=np.float32)
    post = np.array(Image.open(post_path).convert("L"), dtype=np.float32)
    diff = _normalize(np.abs(pre - post))
    img = Image.fromarray(diff)

    name = _output_name(pre_path, f"diff_gray_raw{tag}")
    out = os.path.join(DIFF_OUTPUT_DIR, name)
    img.save(out)
    return out


def _output_name(pre_path: str, suffix: str) -> str:
    base = os.path.basename(pre_path)
    for s in ("_pre_up3x.png", "_pre_up2x.png", "_pre.png"):
        if base.endswith(s):
            base = base[: -len(s)]
            break
    return f"{base}_{suffix}.png"
