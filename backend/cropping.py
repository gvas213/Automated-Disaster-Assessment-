import json
import os
import re

from PIL import Image

DISASTER_IMAGES_DIR = os.path.join(os.path.dirname(__file__), "disaster-images")
DISASTER_JSON_DIR = os.path.join(os.path.dirname(__file__), "disaster-json")
CROP_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "cropped")
os.makedirs(CROP_OUTPUT_DIR, exist_ok=True)


def find_disaster_quartets() -> list[tuple[str, str, str, str]]:
    """Build list of (pre_image, post_image, pre_json, post_json) tuples."""
    quartets = []
    for fname in sorted(os.listdir(DISASTER_IMAGES_DIR)):
        if not fname.endswith("_pre_disaster.png"):
            continue
        base = fname.replace("_pre_disaster.png", "")
        pre_img = os.path.join(DISASTER_IMAGES_DIR, f"{base}_pre_disaster.png")
        post_img = os.path.join(DISASTER_IMAGES_DIR, f"{base}_post_disaster.png")
        pre_json = os.path.join(DISASTER_JSON_DIR, f"{base}_pre_disaster.json")
        post_json = os.path.join(DISASTER_JSON_DIR, f"{base}_post_disaster.json")

        if all(os.path.exists(p) for p in (pre_img, post_img, pre_json, post_json)):
            quartets.append((pre_img, post_img, pre_json, post_json))

    return quartets


def parse_wkt_polygon(wkt: str) -> list[tuple[float, float]]:
    """Extract (x, y) coordinate pairs from a WKT POLYGON string."""
    match = re.search(r"POLYGON \(\((.+?)\)\)", wkt)
    if not match:
        return []
    coords = []
    for pair in match.group(1).split(","):
        x, y = pair.strip().split()
        coords.append((float(x), float(y)))
    return coords


def bbox_from_coords(coords: list[tuple[float, float]]) -> tuple[int, int, int, int]:
    """Return (x_min, y_min, x_max, y_max) bounding box from polygon coords."""
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return int(min(xs)), int(min(ys)), int(max(xs)) + 1, int(max(ys)) + 1


def crop_buildings(pre_img_path, post_img_path, post_json_path) -> list[tuple[str, str, str, str]]:
    """Crop each building from pre/post images using xy polygons in the post JSON.

    Returns list of (pre_crop_path, post_crop_path, uid, ground_truth_subtype).
    """
    with open(post_json_path) as f:
        data = json.load(f)

    features = data["features"]["xy"]
    pre_img = Image.open(pre_img_path)
    post_img = Image.open(post_img_path)
    base = os.path.splitext(os.path.basename(post_img_path))[0].replace("_post_disaster", "")

    results = []
    for feat in features:
        uid = feat["properties"]["uid"]
        subtype = feat["properties"]["subtype"]
        coords = parse_wkt_polygon(feat["wkt"])
        if not coords:
            continue
        box = bbox_from_coords(coords)

        pre_crop = pre_img.crop(box)
        post_crop = post_img.crop(box)

        pre_path = os.path.join(CROP_OUTPUT_DIR, f"{base}_{uid}_pre.png")
        post_path = os.path.join(CROP_OUTPUT_DIR, f"{base}_{uid}_post.png")
        pre_crop.save(pre_path)
        post_crop.save(post_path)
        print(f"  Cropped {subtype}: {uid} -> box {box}")
        results.append((pre_path, post_path, uid, subtype))

    return results


if __name__ == "__main__":
    quartets = find_disaster_quartets()
    pre_image, post_image, pre_json, post_json = quartets[0]
    print(f"Testing with: {os.path.basename(post_image)}")
    crop_buildings(pre_image, post_image, post_json)
    print(f"Crops saved to {CROP_OUTPUT_DIR}")
