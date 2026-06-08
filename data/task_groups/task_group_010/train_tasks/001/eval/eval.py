#!/usr/bin/env python3
import json
import sys
from pathlib import Path


ANSWER_PATH = Path(__file__).resolve().parents[1] / "output" / "answer.json"


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def get_nested(obj, path):
    cur = obj
    for part in path:
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def rounded(value, digits):
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def normalize_trade_package(value):
    if not isinstance(value, list):
        return None
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            return None
        normalized.append(
            {
                "action": item.get("action"),
                "instrument_id": item.get("instrument_id"),
                "notional_usd_m": rounded(item.get("notional_usd_m"), 1),
            }
        )
    return sorted(normalized, key=lambda x: (str(x["instrument_id"]), str(x["action"])))


def exact_fields(prediction, expected, paths):
    for path in paths:
        if get_nested(prediction, path) != get_nested(expected, path):
            return False
    return True


def exact_numeric_fields(prediction, expected, specs):
    for path, digits in specs:
        if rounded(get_nested(prediction, path), digits) != rounded(get_nested(expected, path), digits):
            return False
    return True


def make_point(point_id, description, weight, passed, expected_value, actual_value):
    return {
        "id": point_id,
        "description": description,
        "weight": weight,
        "passed": bool(passed),
        "score": weight if passed else 0,
        "expected": expected_value,
        "actual": actual_value,
    }


def score(prediction, expected):
    expected_trades = normalize_trade_package(expected.get("trade_package"))
    actual_trades = normalize_trade_package(prediction.get("trade_package"))

    points = [
        make_point(
            "SP001",
            "Selected two BUY tickets with correct instrument ids and notionals.",
            3,
            actual_trades == expected_trades,
            expected_trades,
            actual_trades,
        ),
        make_point(
            "SP002",
            "Correct post-trade HY allocation percentage.",
            2,
            exact_numeric_fields(
                prediction,
                expected,
                [(("post_trade_metrics", "hy_allocation_pct"), 2)],
            ),
            get_nested(expected, ("post_trade_metrics", "hy_allocation_pct")),
            get_nested(prediction, ("post_trade_metrics", "hy_allocation_pct")),
        ),
        make_point(
            "SP003",
            "Correct post-trade weighted modified duration.",
            2,
            exact_numeric_fields(
                prediction,
                expected,
                [(("post_trade_metrics", "weighted_modified_duration_years"), 2)],
            ),
            get_nested(expected, ("post_trade_metrics", "weighted_modified_duration_years")),
            get_nested(prediction, ("post_trade_metrics", "weighted_modified_duration_years")),
        ),
        make_point(
            "SP004",
            "Correct HY cap and duration-band pass/fail decisions.",
            2,
            exact_fields(
                prediction,
                expected,
                [
                    ("constraint_checks", "hy_cap_pass"),
                    ("constraint_checks", "duration_band_pass"),
                ],
            ),
            {
                "hy_cap_pass": get_nested(expected, ("constraint_checks", "hy_cap_pass")),
                "duration_band_pass": get_nested(expected, ("constraint_checks", "duration_band_pass")),
            },
            {
                "hy_cap_pass": get_nested(prediction, ("constraint_checks", "hy_cap_pass")),
                "duration_band_pass": get_nested(prediction, ("constraint_checks", "duration_band_pass")),
            },
        ),
        make_point(
            "SP005",
            "Correct selected-issuer, subsector, and watchlist diversification flags.",
            1,
            exact_fields(
                prediction,
                expected,
                [
                    ("constraint_checks", "selected_issuer_diversification_pass"),
                    ("constraint_checks", "selected_subsector_diversification_pass"),
                    ("constraint_checks", "watchlist_avoidance_pass"),
                ],
            ),
            {
                "selected_issuer_diversification_pass": get_nested(
                    expected, ("constraint_checks", "selected_issuer_diversification_pass")
                ),
                "selected_subsector_diversification_pass": get_nested(
                    expected, ("constraint_checks", "selected_subsector_diversification_pass")
                ),
                "watchlist_avoidance_pass": get_nested(expected, ("constraint_checks", "watchlist_avoidance_pass")),
            },
            {
                "selected_issuer_diversification_pass": get_nested(
                    prediction, ("constraint_checks", "selected_issuer_diversification_pass")
                ),
                "selected_subsector_diversification_pass": get_nested(
                    prediction, ("constraint_checks", "selected_subsector_diversification_pass")
                ),
                "watchlist_avoidance_pass": get_nested(prediction, ("constraint_checks", "watchlist_avoidance_pass")),
            },
        ),
        make_point(
            "SP006",
            "Correct sales target segment, energy theme, and source-precedence decision.",
            2,
            exact_fields(
                prediction,
                expected,
                [
                    ("sales_positioning", "target_segment"),
                    ("sales_positioning", "theme"),
                    ("data_precedence",),
                ],
            ),
            {
                "target_segment": get_nested(expected, ("sales_positioning", "target_segment")),
                "theme": get_nested(expected, ("sales_positioning", "theme")),
                "data_precedence": expected.get("data_precedence"),
            },
            {
                "target_segment": get_nested(prediction, ("sales_positioning", "target_segment")),
                "theme": get_nested(prediction, ("sales_positioning", "theme")),
                "data_precedence": prediction.get("data_precedence"),
            },
        ),
    ]
    raw_score = sum(point["score"] for point in points)
    max_score = sum(point["weight"] for point in points)
    return {
        "score": raw_score,
        "max_score": max_score,
        "normalized_score": raw_score / max_score if max_score else 0.0,
        "points": points,
    }


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: eval.py <prediction_json_path>"}, indent=2))
        return 2

    try:
        prediction = load_json(sys.argv[1])
        expected = load_json(ANSWER_PATH)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 1

    print(json.dumps(score(prediction, expected), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
