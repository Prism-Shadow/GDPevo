#!/usr/bin/env python3
"""Resolve an allocation view from signal score, prior view, and policy thresholds.

Determines:
  - view (OW / N / UW) from score threshold comparison
  - conviction (HIGH / MEDIUM / LOW) from absolute score thresholds
  - change (UP / DOWN / UNCHANGED) from prior view rank comparison
  - rationale_code taken from the macro-signal record

Usage:
  python3 resolve_allocation_view.py \\
    --signal-score 0.48 \\
    --prior-view N \\
    --policy-json '{"allocation_mapping": {"view_score_thresholds": {...}}}'
"""

import argparse
import json
import sys


VIEW_RANK = {"OW": 1, "N": 0, "UW": -1}


def resolve_view(score, thresholds):
    ow_min = float(thresholds.get("OW_min", 0.35))
    uw_max = float(thresholds.get("UW_max", -0.35))
    if score >= ow_min:
        return "OW"
    elif score <= uw_max:
        return "UW"
    else:
        return "N"


def resolve_conviction(score, thresholds):
    high_min = float(thresholds.get("HIGH_abs_min", 0.70))
    med_min = float(thresholds.get("MEDIUM_abs_min", 0.35))
    abs_s = abs(score)
    if abs_s >= high_min:
        return "HIGH"
    elif abs_s >= med_min:
        return "MEDIUM"
    else:
        return "LOW"


def resolve_change(current_view, prior_view):
    cr = VIEW_RANK.get(current_view, 0)
    pr = VIEW_RANK.get(prior_view, 0)
    if cr > pr:
        return "UP"
    elif cr < pr:
        return "DOWN"
    else:
        return "UNCHANGED"


def main():
    parser = argparse.ArgumentParser(description="Resolve allocation view from signal and policy.")
    parser.add_argument("--signal-score", required=True, type=float, help="Signal score")
    parser.add_argument("--prior-view", required=True, help="Prior quarter view (OW/N/UW)")
    parser.add_argument("--policy-json", required=True, help="Policy JSON string with allocation_mapping")
    args = parser.parse_args()

    try:
        policy = json.loads(args.policy_json)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}", file=sys.stderr)
        sys.exit(1)

    am = policy.get("allocation_mapping", {})
    vst = am.get("view_score_thresholds", {})
    ct = am.get("conviction_thresholds", {})

    view = resolve_view(args.signal_score, vst)
    conviction = resolve_conviction(args.signal_score, ct)
    change = resolve_change(view, args.prior_view)

    out = {
        "view": view,
        "conviction": conviction,
        "change": change,
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
