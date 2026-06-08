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
    return sorted(normalized, key=lambda item: (str(item["action"]), str(item["instrument_id"])))


def normalize_shortlist(value):
    if not isinstance(value, list):
        return None
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            return None
        normalized.append(
            {
                "rank": item.get("rank"),
                "route_id": item.get("route_id"),
                "decision": item.get("decision"),
                "route_reason": item.get("route_reason"),
            }
        )
    return sorted(normalized, key=lambda item: item["rank"] if isinstance(item["rank"], int) else 999)


def normalize_conflicts(value):
    if not isinstance(value, list):
        return None
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            return None
        normalized.append(
            {
                "instrument_id": item.get("instrument_id"),
                "conflict_type": item.get("conflict_type"),
            }
        )
    return sorted(normalized, key=lambda item: (str(item["instrument_id"]), str(item["conflict_type"])))


def normalize_reason_map(value):
    if not isinstance(value, dict):
        return None
    normalized = {}
    for key, reasons in value.items():
        if not isinstance(reasons, list):
            return None
        normalized[str(key)] = sorted(str(reason) for reason in reasons)
    return {key: normalized[key] for key in sorted(normalized)}


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
    expected_trades = normalize_trade_package(expected.get("selected_trade_package"))
    actual_trades = normalize_trade_package(prediction.get("selected_trade_package"))
    expected_shortlist = normalize_shortlist(expected.get("ranked_package_shortlist"))
    actual_shortlist = normalize_shortlist(prediction.get("ranked_package_shortlist"))
    expected_conflicts = normalize_conflicts(get_nested(expected, ("source_precedence", "conflict_details")))
    actual_conflicts = normalize_conflicts(get_nested(prediction, ("source_precedence", "conflict_details")))
    expected_reasons = normalize_reason_map(expected.get("candidate_rejection_reasons"))
    actual_reasons = normalize_reason_map(prediction.get("candidate_rejection_reasons"))

    post_trade_core_specs = [
        (("post_trade_metrics", "total_market_value_usd_m"), 2),
        (("post_trade_metrics", "gross_trade_notional_usd_m"), 1),
        (("post_trade_metrics", "net_new_cash_usd_m"), 1),
        (("post_trade_metrics", "hy_allocation_pct"), 2),
        (("post_trade_metrics", "weighted_modified_duration_years"), 2),
    ]
    post_trade_secondary_specs = [
        (("post_trade_metrics", "weighted_yield_to_maturity_pct"), 2),
        (("post_trade_metrics", "bluegas_issuer_concentration_pct"), 2),
    ]

    points = [
        make_point(
            "SP001",
            "Correct recommendation type, selected route, action, and primary constraint conflict.",
            3,
            exact_fields(
                prediction,
                expected,
                [
                    ("recommendation", "package_type"),
                    ("recommendation", "primary_action"),
                    ("recommendation", "selected_route_id"),
                    ("recommendation", "primary_constraint_conflict"),
                ],
            ),
            expected.get("recommendation"),
            prediction.get("recommendation"),
        ),
        make_point(
            "SP002",
            "Correct ranked route shortlist with decisions and reason enums.",
            3,
            actual_shortlist == expected_shortlist,
            expected_shortlist,
            actual_shortlist,
        ),
        make_point(
            "SP003",
            "Correct selected trade package with actions and notionals.",
            3,
            actual_trades == expected_trades,
            expected_trades,
            actual_trades,
        ),
        make_point(
            "SP004",
            "Correct current-data source precedence and detailed conflict map.",
            2,
            get_nested(prediction, ("source_precedence", "decision"))
            == get_nested(expected, ("source_precedence", "decision"))
            and actual_conflicts == expected_conflicts,
            expected.get("source_precedence"),
            prediction.get("source_precedence"),
        ),
        make_point(
            "SP005",
            "Correct rejected candidate reason map from current data and policy conventions.",
            3,
            actual_reasons == expected_reasons,
            expected_reasons,
            actual_reasons,
        ),
        make_point(
            "SP006",
            "Correct core post-trade size, cash, HY allocation, and duration metrics.",
            2,
            exact_numeric_fields(prediction, expected, post_trade_core_specs),
            {
                "total_market_value_usd_m": get_nested(expected, ("post_trade_metrics", "total_market_value_usd_m")),
                "gross_trade_notional_usd_m": get_nested(
                    expected, ("post_trade_metrics", "gross_trade_notional_usd_m")
                ),
                "net_new_cash_usd_m": get_nested(expected, ("post_trade_metrics", "net_new_cash_usd_m")),
                "hy_allocation_pct": get_nested(expected, ("post_trade_metrics", "hy_allocation_pct")),
                "weighted_modified_duration_years": get_nested(
                    expected, ("post_trade_metrics", "weighted_modified_duration_years")
                ),
            },
            {
                "total_market_value_usd_m": get_nested(prediction, ("post_trade_metrics", "total_market_value_usd_m")),
                "gross_trade_notional_usd_m": get_nested(
                    prediction, ("post_trade_metrics", "gross_trade_notional_usd_m")
                ),
                "net_new_cash_usd_m": get_nested(prediction, ("post_trade_metrics", "net_new_cash_usd_m")),
                "hy_allocation_pct": get_nested(prediction, ("post_trade_metrics", "hy_allocation_pct")),
                "weighted_modified_duration_years": get_nested(
                    prediction, ("post_trade_metrics", "weighted_modified_duration_years")
                ),
            },
        ),
        make_point(
            "SP007",
            "Correct secondary post-trade yield, BlueGas concentration, and constraint flags.",
            2,
            exact_numeric_fields(prediction, expected, post_trade_secondary_specs)
            and exact_fields(
                prediction,
                expected,
                [
                    ("constraint_checks", "hy_cap_pass"),
                    ("constraint_checks", "duration_band_pass"),
                    ("constraint_checks", "bluegas_issuer_concentration_pass"),
                    ("constraint_checks", "selected_subsector_diversification_pass"),
                    ("constraint_checks", "watchlist_avoidance_pass"),
                    ("constraint_checks", "current_data_override_pass"),
                ],
            ),
            {
                "post_trade_metrics": {
                    "weighted_yield_to_maturity_pct": get_nested(
                        expected, ("post_trade_metrics", "weighted_yield_to_maturity_pct")
                    ),
                    "bluegas_issuer_concentration_pct": get_nested(
                        expected, ("post_trade_metrics", "bluegas_issuer_concentration_pct")
                    ),
                },
                "constraint_checks": expected.get("constraint_checks"),
            },
            {
                "post_trade_metrics": {
                    "weighted_yield_to_maturity_pct": get_nested(
                        prediction, ("post_trade_metrics", "weighted_yield_to_maturity_pct")
                    ),
                    "bluegas_issuer_concentration_pct": get_nested(
                        prediction, ("post_trade_metrics", "bluegas_issuer_concentration_pct")
                    ),
                },
                "constraint_checks": prediction.get("constraint_checks"),
            },
        ),
        make_point(
            "SP008",
            "Correct private-bank client suitability decision and monitoring trigger.",
            1,
            exact_fields(
                prediction,
                expected,
                [
                    ("client_suitability", "client_segment"),
                    ("client_suitability", "suitability_decision"),
                    ("client_suitability", "income_profile"),
                    ("client_suitability", "monitoring_trigger"),
                ],
            ),
            expected.get("client_suitability"),
            prediction.get("client_suitability"),
        ),
        make_point(
            "SP009",
            "Correct sales target segment and energy theme.",
            1,
            exact_fields(
                prediction,
                expected,
                [
                    ("sales_positioning", "target_segment"),
                    ("sales_positioning", "theme"),
                ],
            ),
            expected.get("sales_positioning"),
            prediction.get("sales_positioning"),
        ),
    ]
    raw_score = sum(point["score"] for point in points)
    max_score = sum(point["weight"] for point in points)
    return {
        "score": raw_score,
        "max_score": max_score,
        "normalized_score": round(raw_score / max_score, 6) if max_score else 0.0,
        "points": points,
    }


def main():
    max_score = 20
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": max_score,
                    "normalized_score": 0,
                    "error": "Usage: eval.py <prediction_json_path>",
                },
                indent=2,
            )
        )
        return 2

    try:
        prediction = load_json(sys.argv[1])
        expected = load_json(ANSWER_PATH)
    except Exception as exc:
        print(json.dumps({"score": 0, "max_score": max_score, "normalized_score": 0, "error": str(exc)}, indent=2))
        return 1

    print(json.dumps(score(prediction, expected), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
