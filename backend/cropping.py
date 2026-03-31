import json
import os
import re

from PIL import Image, ImageDraw

DISASTER_IMAGES_DIR = os.path.join(os.path.dirname(__file__), "disaster-images")
DISASTER_JSON_DIR = os.path.join(os.path.dirname(__file__), "disaster-json")
CROP_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output_image")
GEOJSON_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "disaster-output-geojson")
os.makedirs(CROP_OUTPUT_DIR, exist_ok=True)
os.makedirs(GEOJSON_OUTPUT_DIR, exist_ok=True)


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


def padded_bbox(
    coords: list[tuple[float, float]],
    img_width: int,
    img_height: int,
    # decrease padding | change outline
    padding: int = 150,
    min_size: int = 150,
) -> tuple[int, int, int, int]:
    """Return padded (x_min, y_min, x_max, y_max) bounding box, clamped to image bounds."""
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    x_min, y_min = int(min(xs)) - padding, int(min(ys)) - padding
    x_max, y_max = int(max(xs)) + 1 + padding, int(max(ys)) + 1 + padding

    # Enforce minimum crop size (expand from center)
    w, h = x_max - x_min, y_max - y_min
    if w < min_size:
        cx = (x_min + x_max) // 2
        x_min, x_max = cx - min_size // 2, cx + min_size // 2
    if h < min_size:
        cy = (y_min + y_max) // 2
        y_min, y_max = cy - min_size // 2, cy + min_size // 2

    return max(0, x_min), max(0, y_min), min(img_width, x_max), min(img_height, y_max)


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

    img_w, img_h = pre_img.size

    results = []
    for feat in features:
        uid = feat["properties"]["uid"]
        subtype = feat["properties"]["subtype"]
        coords = parse_wkt_polygon(feat["wkt"])
        if not coords:
            continue
        box = padded_bbox(coords, img_w, img_h)
        x_min, y_min = box[0], box[1]

        pre_crop = pre_img.crop(box).copy()
        post_crop = post_img.crop(box).copy()

        # Draw red polygon outline shifted to crop-local coordinates
        local_coords = [(x - x_min, y - y_min) for x, y in coords]
        for crop in (pre_crop, post_crop):
            draw = ImageDraw.Draw(crop)
            draw.polygon(local_coords, outline="red", width=2)

        pre_path = os.path.join(CROP_OUTPUT_DIR, f"{base}_{uid}_pre.png")
        post_path = os.path.join(CROP_OUTPUT_DIR, f"{base}_{uid}_post.png")
        pre_crop.save(pre_path)
        post_crop.save(post_path)
        print(f"  Cropped {subtype}: {uid} -> box {box}")
        results.append((pre_path, post_path, uid, subtype))

    return results


def build_geojson(post_json_path: str, results: list[dict], output_name: str) -> str:
    """Build a GeoJSON FeatureCollection from VLM results + source lng_lat polygons.

    Args:
        post_json_path: Path to the source post-disaster JSON (has lng_lat features).
        results: List of prediction dicts with uid, predicted.feature_type, predicted.subtype.
        output_name: Filename (without extension) for the output geojson.

    Returns:
        Path to the saved .geojson file.
    """
    with open(post_json_path) as f:
        source = json.load(f)

    # Build uid -> lng_lat WKT lookup
    lnglat_by_uid = {}
    for feat in source["features"]["lng_lat"]:
        lnglat_by_uid[feat["properties"]["uid"]] = feat["wkt"]

    features = []
    for r in results:
        uid = r["uid"]
        wkt = lnglat_by_uid.get(uid)
        if not wkt:
            continue

        coords = parse_wkt_polygon(wkt)
        if not coords:
            continue

        # GeoJSON polygon: list of rings, each ring is list of [lon, lat]
        ring = [[lon, lat] for lon, lat in coords]

        feature = {
            "type": "Feature",
            "properties": {
                "uid": uid,
                "cost_usd": None,
                "damage_type": r["predicted"]["subtype"],
                "description": None,
                "feature_type": r["predicted"]["feature_type"],
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [ring],
            },
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    output_path = os.path.join(GEOJSON_OUTPUT_DIR, f"{output_name}.geojson")
    with open(output_path, "w") as f:
        json.dump(geojson, f, indent=2)

    print(f"GeoJSON saved to {output_path}")
    return output_path


if __name__ == "__main__":
    quartets = find_disaster_quartets()
    pre_image, post_image, pre_json, post_json = quartets[0]
    print(f"Testing with: {os.path.basename(post_image)}")
    crop_buildings(pre_image, post_image, post_json)
    print(f"Crops saved to {CROP_OUTPUT_DIR}")
