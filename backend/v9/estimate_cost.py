"""Estimate repair cost (USD) per building and write back into the v9 geojson.

For each feature in disaster-output-geojson/*_v9_openai_results.geojson:
  - If damage_type == "no-damage" -> cost_usd = 0 (no API call)
  - Otherwise, ask OpenAI to estimate repair cost based on damage_type +
    pre_description + reasoning, and write cost_usd in-place.

The geojson files are overwritten.
"""

import glob
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

load_dotenv()
client = OpenAI()

GEOJSON_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "disaster-output-geojson")

MODEL = "gpt-4.1-mini"
FILE_WORKERS = 5
FEATURE_WORKERS = 10

COST_PROMPT = """You are a disaster recovery cost estimator for a residential/commercial building damaged by a hurricane.

Estimate the repair cost in USD based on the following information:

Damage classification: {damage_type}
Building description (pre-disaster): {pre_description}
Damage reasoning: {reasoning}

Reference ranges for typical hurricane damage in the US:
- minor-damage: $2,000 - $20,000 (roof patching, minor debris removal, small repairs)
- major-damage: $20,000 - $150,000 (large roof replacement, partial structural rebuild, significant interior damage)
- destroyed: $150,000 - $500,000+ (full rebuild from foundation)

Pick a single specific USD integer within (or near) the range that best fits the described building and damage. Consider the building's apparent size, type, and materials from the pre-disaster description.

Return ONLY a raw JSON object:
{{"cost_usd": <integer>, "reasoning": "one short sentence"}}"""


def estimate_cost(damage_type: str, pre_description: str, reasoning: str) -> int:
    prompt = COST_PROMPT.format(
        damage_type=damage_type,
        pre_description=pre_description or "No description available.",
        reasoning=reasoning or "No reasoning available.",
    )

    response = client.responses.create(
        model=MODEL,
        input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
    )

    raw = response.output_text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    result = json.loads(raw)
    return int(result["cost_usd"])


def process_feature(feat: dict) -> tuple[str, int | None]:
    """Return (uid, cost_usd) for a single feature. Skips if already has a cost."""
    props = feat["properties"]
    uid = props.get("uid", "unknown")
    damage_type = props.get("damage_type", "no-damage")

    if props.get("cost_usd") is not None:
        return uid, props["cost_usd"]

    if damage_type == "no-damage":
        return uid, 0

    desc = props.get("description") or {}
    if isinstance(desc, str):
        pre_description = desc
        reasoning = ""
    else:
        pre_description = desc.get("pre_description", "")
        reasoning = desc.get("reasoning", "")

    try:
        cost = estimate_cost(damage_type, pre_description, reasoning)
        return uid, cost
    except Exception as e:
        print(f"    {uid}: failed ({e})")
        return uid, None


def process_file(path: str) -> tuple[str, int, int]:
    """Return (path, num_updated, num_features)."""
    with open(path) as f:
        data = json.load(f)

    features = data.get("features", [])
    if not features:
        return path, 0, 0

    uid_to_cost: dict[str, int | None] = {}
    with ThreadPoolExecutor(max_workers=FEATURE_WORKERS) as pool:
        futures = [pool.submit(process_feature, feat) for feat in features]
        for future in as_completed(futures):
            uid, cost = future.result()
            uid_to_cost[uid] = cost

    updated = 0
    for feat in features:
        uid = feat["properties"].get("uid", "unknown")
        cost = uid_to_cost.get(uid)
        if cost is not None:
            feat["properties"]["cost_usd"] = cost
            updated += 1

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    return path, updated, len(features)


def main():
    pattern = os.path.join(GEOJSON_DIR, "*_v9_openai_results.geojson")
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"No geojson files found in {GEOJSON_DIR}")
        sys.exit(1)

    print(f"Found {len(files)} geojson files. Estimating costs with {MODEL}.")
    print(f"Workers: {FILE_WORKERS} files x {FEATURE_WORKERS} features")
    time.sleep(2)

    total_updated = 0
    total_features = 0

    with ThreadPoolExecutor(max_workers=FILE_WORKERS) as pool:
        futures = {pool.submit(process_file, path): path for path in files}
        for future in as_completed(futures):
            path = futures[future]
            try:
                _, updated, count = future.result()
                total_updated += updated
                total_features += count
                print(f"  {os.path.basename(path)}: {updated}/{count} features updated")
            except Exception as e:
                print(f"  ERROR {os.path.basename(path)}: {e}")

    print(f"\nDone. Updated {total_updated}/{total_features} features across {len(files)} files.")


if __name__ == "__main__":
    main()
