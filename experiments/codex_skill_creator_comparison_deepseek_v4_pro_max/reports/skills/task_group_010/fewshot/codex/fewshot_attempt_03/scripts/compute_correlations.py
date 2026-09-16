#!/usr/bin/env python3
"""Deterministic Pearson correlation from Asteria index-level JSON.

Usage:
  python3 compute_correlations.py <levels.json> <index_ids.txt>

  levels.json: a JSON array of objects with keys "index_id" and "levels".
    Each "levels" is an array of {"date": "...", "level": number}.
    Dates must be monthly, consecutive, and shared across all index_ids.

  index_ids.txt: one index_id per line (the subset to correlate).

Output (stdout): JSON object with keys:
  - "return_observations": number of monthly-return periods
  - "pairs": array of {"pair_id": [id_a, id_b], "correlation": float}
    Sorted by pair_id alphabetically, then correlation descending.
    Each pair_id is already alphabetical.
"""

import json
import math
import sys


def load_index_levels(raw: list) -> dict[str, list[float]]:
    """Return {index_id: [level_0, level_1, ...]} in date order."""
    out: dict[str, list[float]] = {}
    for entry in raw:
        iid = entry["index_id"]
        levels = [pt["level"] for pt in entry["levels"]]
        out[iid] = levels
    return out


def monthly_simple_returns(levels: list[float]) -> list[float]:
    """Simple return r_t = (L_t / L_{t-1}) - 1 for each consecutive pair."""
    return [(levels[i] / levels[i - 1]) - 1.0 for i in range(1, len(levels))]


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n != len(ys) or n < 2:
        return float("nan")
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return float("nan")
    return cov / (sx * sy)


def main():
    if len(sys.argv) != 3:
        print("Usage: compute_correlations.py <levels.json> <index_ids.txt>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        raw_levels = json.load(f)
    with open(sys.argv[2]) as f:
        target_ids = [line.strip() for line in f if line.strip()]

    level_map = load_index_levels(raw_levels)

    # Check all target ids present and have same observation count
    obs = None
    returns_map: dict[str, list[float]] = {}
    for iid in target_ids:
        if iid not in level_map:
            print(f"Missing index_id: {iid}", file=sys.stderr)
            sys.exit(1)
        rets = monthly_simple_returns(level_map[iid])
        if obs is None:
            obs = len(rets)
        elif len(rets) != obs:
            print(f"Observation count mismatch for {iid}", file=sys.stderr)
            sys.exit(1)
        returns_map[iid] = rets

    # Correlate all pairs
    pairs = []
    sorted_ids = sorted(target_ids)
    for i in range(len(sorted_ids)):
        for j in range(i + 1, len(sorted_ids)):
            a, b = sorted_ids[i], sorted_ids[j]
            r = pearson(returns_map[a], returns_map[b])
            pairs.append({"pair_id": [a, b], "correlation": round(r, 3)})

    print(json.dumps({"return_observations": obs, "pairs": pairs}, indent=2))


if __name__ == "__main__":
    main()
