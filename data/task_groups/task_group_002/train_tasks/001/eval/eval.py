#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


EXPECTED = {
    "quote_summary": {
        "confirmed_quantity": 360,
        "unit_price_usd": 118.0,
        "lead_time_days": 28,
        "exw_total_usd": 42480.0,
    },
    "freight_options": {
        "FR-WC-AIR": {
            "mode": "AIR",
            "freight_cost_usd": 16200.0,
            "grand_total_usd": 58680.0,
            "valid_until": "2026-06-18",
        },
        "FR-WC-SEA": {
            "mode": "SEA",
            "freight_cost_usd": 3880.0,
            "grand_total_usd": 46360.0,
            "valid_until": "2026-06-25",
        },
        "FR-WC-ROAD": {
            "mode": "ROAD",
            "risk_level": "MEDIUM",
            "risk_flag": "MEDIUM_BORDER_RISK",
            "valid_until": "2026-06-12",
        },
    },
    "policy_flags": {
        "recommended_mode": "SEA",
        "freight_reconfirmation_required": True,
        "all_freight_options_valid_on_quote_date": True,
        "payment_terms": "NET_30_AFTER_PO",
    },
}


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_path(data, path, default=None):
    current = data
    for part in path:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current


def as_upper(value):
    if value is None:
        return ""
    return str(value).strip().upper()


def money_equal(actual, expected):
    try:
        return math.isclose(float(actual), float(expected), abs_tol=0.005)
    except (TypeError, ValueError):
        return False


def int_equal(actual, expected):
    try:
        return int(actual) == int(expected)
    except (TypeError, ValueError):
        return False


def bool_equal(actual, expected):
    return isinstance(actual, bool) and actual is expected


def normalize_freight_options(candidate):
    raw_options = get_path(candidate, ["freight_options"], [])
    normalized = {}

    if isinstance(raw_options, dict):
        iterable = raw_options.values()
    elif isinstance(raw_options, list):
        iterable = raw_options
    else:
        iterable = []

    for option in iterable:
        if not isinstance(option, dict):
            continue
        freight_id = option.get("freight_id")
        if freight_id:
            normalized[str(freight_id).strip()] = option

    return normalized


def add_result(results, name, weight, passed, expected, observed):
    results.append(
        {
            "name": name,
            "weight": weight,
            "earned": weight if passed else 0,
            "passed": passed,
            "expected": expected,
            "observed": observed,
        }
    )


def evaluate(candidate):
    results = []
    summary = get_path(candidate, ["quote_summary"], {})
    freight = normalize_freight_options(candidate)
    policy = get_path(candidate, ["policy_flags"], {})

    add_result(
        results,
        "quantity_tier_price",
        2,
        int_equal(summary.get("confirmed_quantity"), 360) and money_equal(summary.get("unit_price_usd"), 118.0),
        {"confirmed_quantity": 360, "unit_price_usd": 118.0},
        {
            "confirmed_quantity": summary.get("confirmed_quantity"),
            "unit_price_usd": summary.get("unit_price_usd"),
        },
    )

    add_result(
        results,
        "lead_time_exw",
        2,
        int_equal(summary.get("lead_time_days"), 28) and money_equal(summary.get("exw_total_usd"), 42480.0),
        {"lead_time_days": 28, "exw_total_usd": 42480.0},
        {
            "lead_time_days": summary.get("lead_time_days"),
            "exw_total_usd": summary.get("exw_total_usd"),
        },
    )

    air = freight.get("FR-WC-AIR", {})
    add_result(
        results,
        "air_cost_grand_total",
        2,
        money_equal(air.get("freight_cost_usd"), 16200.0) and money_equal(air.get("grand_total_usd"), 58680.0),
        {"freight_id": "FR-WC-AIR", "freight_cost_usd": 16200.0, "grand_total_usd": 58680.0},
        {
            "freight_id": air.get("freight_id"),
            "freight_cost_usd": air.get("freight_cost_usd"),
            "grand_total_usd": air.get("grand_total_usd"),
        },
    )

    sea = freight.get("FR-WC-SEA", {})
    add_result(
        results,
        "sea_cost_grand_total",
        2,
        money_equal(sea.get("freight_cost_usd"), 3880.0) and money_equal(sea.get("grand_total_usd"), 46360.0),
        {"freight_id": "FR-WC-SEA", "freight_cost_usd": 3880.0, "grand_total_usd": 46360.0},
        {
            "freight_id": sea.get("freight_id"),
            "freight_cost_usd": sea.get("freight_cost_usd"),
            "grand_total_usd": sea.get("grand_total_usd"),
        },
    )

    road = freight.get("FR-WC-ROAD", {})
    add_result(
        results,
        "road_risk_flag",
        2,
        as_upper(road.get("risk_level")) == "MEDIUM" and as_upper(road.get("risk_flag")) == "MEDIUM_BORDER_RISK",
        {"freight_id": "FR-WC-ROAD", "risk_level": "MEDIUM", "risk_flag": "MEDIUM_BORDER_RISK"},
        {
            "freight_id": road.get("freight_id"),
            "risk_level": road.get("risk_level"),
            "risk_flag": road.get("risk_flag"),
        },
    )

    add_result(
        results,
        "recommendation",
        2,
        as_upper(policy.get("recommended_mode")) == "SEA",
        {"recommended_mode": "SEA"},
        {"recommended_mode": policy.get("recommended_mode")},
    )

    validity_passed = (
        air.get("valid_until") == "2026-06-18"
        and sea.get("valid_until") == "2026-06-25"
        and road.get("valid_until") == "2026-06-12"
        and bool_equal(policy.get("freight_reconfirmation_required"), True)
        and bool_equal(policy.get("all_freight_options_valid_on_quote_date"), True)
    )
    add_result(
        results,
        "freight_validity_reconfirmation",
        1,
        validity_passed,
        {
            "valid_until": {
                "FR-WC-AIR": "2026-06-18",
                "FR-WC-SEA": "2026-06-25",
                "FR-WC-ROAD": "2026-06-12",
            },
            "freight_reconfirmation_required": True,
            "all_freight_options_valid_on_quote_date": True,
        },
        {
            "valid_until": {
                "FR-WC-AIR": air.get("valid_until"),
                "FR-WC-SEA": sea.get("valid_until"),
                "FR-WC-ROAD": road.get("valid_until"),
            },
            "freight_reconfirmation_required": policy.get("freight_reconfirmation_required"),
            "all_freight_options_valid_on_quote_date": policy.get("all_freight_options_valid_on_quote_date"),
        },
    )

    add_result(
        results,
        "account_policy_terms",
        1,
        as_upper(policy.get("payment_terms")) == "NET_30_AFTER_PO",
        {"payment_terms": "NET_30_AFTER_PO"},
        {"payment_terms": policy.get("payment_terms")},
    )

    score = sum(item["earned"] for item in results)
    max_score = sum(item["weight"] for item in results)
    return {
        "score": score,
        "max_score": max_score,
        "score_percent": round((score / max_score) * 100, 2) if max_score else 0.0,
        "passed": score == max_score,
        "details": results,
    }


def main():
    candidate_path = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).parent / "../output/answer.json")
    try:
        candidate = load_json(candidate_path)
        result = evaluate(candidate)
    except Exception as exc:
        result = {
            "score": 0,
            "max_score": 14,
            "score_percent": 0.0,
            "passed": False,
            "details": [
                {
                    "name": "load_candidate_json",
                    "weight": 0,
                    "earned": 0,
                    "passed": False,
                    "expected": "Readable JSON file",
                    "observed": f"{type(exc).__name__}: {exc}",
                }
            ],
        }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
