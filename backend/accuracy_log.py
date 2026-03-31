import os
from datetime import datetime
from collections import Counter

ACCURACY_DIR = os.path.join(os.path.dirname(__file__), "accuracy")
os.makedirs(ACCURACY_DIR, exist_ok=True)

# Damage levels ordered by severity (index = severity rank)
DAMAGE_SCALE = ["no-damage", "minor-damage", "major-damage", "destroyed"]

# Partial credit: exact match = 1.0, off-by-1 = 0.5, off-by-2 = 0.25, off-by-3 = 0.0
PARTIAL_CREDIT = {0: 1.0, 1: 0.5, 2: 0.25, 3: 0.0}


def calc_partial_score(given: str, predicted: str) -> float:
    if given not in DAMAGE_SCALE or predicted not in DAMAGE_SCALE:
        return 1.0 if given == predicted else 0.0
    distance = abs(DAMAGE_SCALE.index(given) - DAMAGE_SCALE.index(predicted))
    return PARTIAL_CREDIT[distance]


def log_accuracy(script_name: str, quartet_results: dict[str, list[dict]], all_results: list[dict]):
    """Write accuracy log for a run.

    Args:
        script_name: e.g. "main" or "main_v2"
        quartet_results: {quartet_name: [result_dicts, ...]}
        all_results: flat list of all result dicts
    """
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    log_path = os.path.join(ACCURACY_DIR, f"{script_name}.log")

    total = len(all_results)
    correct = sum(1 for r in all_results if r["given"]["subtype"] == r["predicted"]["subtype"])
    accuracy_pct = (100 * correct / total) if total else 0
    partial_total = sum(calc_partial_score(r["given"]["subtype"], r["predicted"]["subtype"]) for r in all_results)
    partial_pct = (100 * partial_total / total) if total else 0

    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"Run: {timestamp}  |  Script: {script_name}")
    lines.append(f"Quartets: {len(quartet_results)}  |  Buildings: {total}")
    lines.append(f"Exact Accuracy:   {correct}/{total} ({accuracy_pct:.1f}%)")
    lines.append(f"Partial Score:    {partial_total:.1f}/{total} ({partial_pct:.1f}%)")
    lines.append(f"  (exact=1.0, off-by-1=0.5, off-by-2=0.25, off-by-3=0.0)")
    lines.append(f"{'-'*60}")

    # Per-quartet breakdown
    for name in sorted(quartet_results.keys()):
        results = quartet_results[name]
        q_total = len(results)
        q_correct = sum(1 for r in results if r["given"]["subtype"] == r["predicted"]["subtype"])
        q_pct = (100 * q_correct / q_total) if q_total else 0
        q_partial = sum(calc_partial_score(r["given"]["subtype"], r["predicted"]["subtype"]) for r in results)
        q_partial_pct = (100 * q_partial / q_total) if q_total else 0
        lines.append(f"  {name}: exact {q_correct}/{q_total} ({q_pct:.1f}%) | partial {q_partial:.1f}/{q_total} ({q_partial_pct:.1f}%)")

    # Confusion matrix
    confusion = Counter()
    for r in all_results:
        confusion[(r["given"]["subtype"], r["predicted"]["subtype"])] += 1
    lines.append(f"{'-'*60}")
    lines.append("Confusion (ground_truth -> predicted):")
    for (gt, pred), count in sorted(confusion.items()):
        marker = "OK" if gt == pred else "  "
        lines.append(f"  {marker} {gt:>15} -> {pred:<15} x{count}")

    lines.append("")

    with open(log_path, "a") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nAccuracy log appended to {log_path}")
