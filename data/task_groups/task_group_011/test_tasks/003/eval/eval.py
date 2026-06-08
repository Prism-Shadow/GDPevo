#!/usr/bin/env python3
"""Exact-match evaluator for test_003."""

from __future__ import annotations

import json
import sys
from pathlib import Path


POINTS = [
    ("SP001", 3, "posture"),
    ("SP002", 2, "GA benchmark metrics"),
    ("SP003", 2, "peer comparison with AL/FL/TN"),
    ("SP004", 2, "capacity and risk interpretation"),
    ("SP005", 2, "required checklist gates"),
    ("SP006", 2, "added operating controls"),
    ("SP007", 1, "escalation triggers"),
]


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def as_set(value):
    if not isinstance(value, list):
        return None
    return set(value)


def normalize_trigger_list(value):
    if not isinstance(value, list):
        return None
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            return None
        normalized.append(
            {
                "trigger_id": item.get("trigger_id"),
                "condition": item.get("condition"),
                "owner": item.get("owner"),
            }
        )
    return sorted(normalized, key=lambda row: (row["trigger_id"] or "", row["condition"] or "", row["owner"] or ""))


def exact_int_metrics(value):
    if not isinstance(value, dict):
        return None
    keys = [
        "state_code",
        "benchmark_version",
        "delinquency_bps",
        "loan_to_share_pct",
        "roaa_bps",
        "positive_net_income_pct",
    ]
    result = {}
    for key in keys:
        if key not in value:
            return None
        if key.endswith("_bps") or key.endswith("_pct"):
            try:
                result[key] = int(value[key])
            except (TypeError, ValueError):
                return None
        else:
            result[key] = value[key]
    return result


def peer_comparison(value):
    if not isinstance(value, dict):
        return None
    return {
        "peer_states": sorted(value.get("peer_states", [])) if isinstance(value.get("peer_states"), list) else None,
        "target_vs_us": value.get("target_vs_us"),
        "target_vs_peer_median": value.get("target_vs_peer_median"),
    }


def interpretation(value):
    if not isinstance(value, dict):
        return None
    return {
        "capacity_status": value.get("capacity_status"),
        "external_risk_status": value.get("external_risk_status"),
        "risk_tolerance": value.get("risk_tolerance"),
        "committee_message": value.get("committee_message"),
    }


def check_point(point_id, pred, ans):
    if point_id == "SP001":
        return pred.get("segment_id") == ans.get("segment_id") and pred.get("posture") == ans.get("posture")
    if point_id == "SP002":
        return exact_int_metrics(pred.get("state_metrics")) == exact_int_metrics(ans.get("state_metrics"))
    if point_id == "SP003":
        return peer_comparison(pred.get("peer_comparison")) == peer_comparison(ans.get("peer_comparison"))
    if point_id == "SP004":
        return interpretation(pred.get("interpretation")) == interpretation(ans.get("interpretation"))
    if point_id == "SP005":
        return as_set(pred.get("controls", {}).get("required_checklist_gates")) == as_set(
            ans.get("controls", {}).get("required_checklist_gates")
        )
    if point_id == "SP006":
        return as_set(pred.get("controls", {}).get("added_operating_controls")) == as_set(
            ans.get("controls", {}).get("added_operating_controls")
        )
    if point_id == "SP007":
        return normalize_trigger_list(pred.get("escalation_triggers")) == normalize_trigger_list(
            ans.get("escalation_triggers")
        )
    return False


def main(argv):
    if len(argv) != 2:
        print(json.dumps({"score": 0.0, "max_score": 1.0, "error": "usage: eval.py prediction.json"}))
        return 2

    pred_path = Path(argv[1])
    answer_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"

    try:
        pred = load_json(pred_path)
        ans = load_json(answer_path)
    except Exception as exc:
        points = [{"id": pid, "passed": False, "weight": weight} for pid, weight, _ in POINTS]
        print(json.dumps({"score": 0.0, "max_score": 1.0, "points": points, "error": str(exc)}))
        return 0

    total_weight = sum(weight for _, weight, _ in POINTS)
    point_results = []
    earned = 0
    for point_id, weight, description in POINTS:
        passed = bool(check_point(point_id, pred, ans))
        if passed:
            earned += weight
        point_results.append({"id": point_id, "passed": passed, "weight": weight, "description": description})

    score = round(earned / total_weight, 10)
    print(json.dumps({"score": score, "max_score": 1.0, "points": point_results}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
