#!/usr/bin/env python3
import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path


MAX_SCORE = 22


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


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip().upper().replace("-", "_").replace(" ", "_")


def normalize_money(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def money_equals(value, expected):
    return normalize_money(value) == Decimal(str(expected)).quantize(Decimal("0.01"))


def int_equals(value, expected):
    try:
        return int(value) == expected
    except (TypeError, ValueError):
        return False


def bool_value(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "y", "1", "valid", "feasible"}:
            return True
        if normalized in {"false", "no", "n", "0", "invalid", "stale", "expired", "infeasible"}:
            return False
        if "not feasible" in normalized or "not_feasible" in normalized:
            return False
        if "feasible" in normalized:
            return True
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
    return None


def iter_dicts(value):
    if isinstance(value, dict):
        for item in value.values():
            if isinstance(item, dict):
                yield item
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item


def freight_options(data):
    raw_options = data.get("freight_options")
    options = list(iter_dicts(raw_options))
    if options:
        return options

    decisions = data.get("transport_decisions", {})
    options = list(iter_dicts(decisions.get("freight_options")))
    if options:
        return options

    fallback = []
    for key in ("air", "sea", "road", "AIR", "SEA", "ROAD"):
        item = decisions.get(key)
        if isinstance(item, dict):
            item = dict(item)
            item.setdefault("mode", key.upper())
            fallback.append(item)
    return fallback


def find_option(data, mode=None, freight_id=None):
    expected_mode = normalize_text(mode)
    expected_id = normalize_text(freight_id)
    for option in freight_options(data):
        option_mode = normalize_text(option_value(option, "mode", "transport_mode"))
        option_id = normalize_text(option_value(option, "freight_id", "id", "quote_id"))
        if expected_id and option_id == expected_id:
            return option
        if expected_mode and option_mode == expected_mode:
            return option
    return {}


def option_value(option, *keys):
    for key in keys:
        if isinstance(option, dict) and key in option:
            return option[key]
    return None


def risk_level(option):
    return normalize_text(
        option_value(
            option,
            "risk_level",
            "route_risk",
            "border_risk",
            "customs_border_risk",
            "customs_risk",
        )
    )


def risk_flag(option):
    return normalize_text(
        option_value(
            option,
            "risk_flag",
            "route_risk_flag",
            "border_risk_flag",
            "customs_border_risk",
            "risk_note",
        )
    )


def feasibility(option):
    return bool_value(
        option_value(
            option,
            "delivery_window_feasible",
            "requested_delivery_window_feasible",
            "feasible_for_requested_delivery_window",
            "feasible",
            "delivery_feasible",
        )
    )


def any_nested_true(data, keys):
    if isinstance(data, dict):
        for key, value in data.items():
            if key in keys and bool_value(value) is True:
                return True
            if any_nested_true(value, keys):
                return True
    elif isinstance(data, list):
        return any(any_nested_true(item, keys) for item in data)
    return False


def any_nested_text_contains(data, keys, required_parts):
    if isinstance(data, dict):
        for key, value in data.items():
            if key in keys:
                normalized = normalize_text(value)
                if all(part in normalized for part in required_parts):
                    return True
            if any_nested_text_contains(value, keys, required_parts):
                return True
    elif isinstance(data, list):
        return any(any_nested_text_contains(item, keys, required_parts) for item in data)
    return False


def add_point(points, name, weight, passed, expected, observed):
    points.append(
        {
            "name": name,
            "weight": weight,
            "earned": weight if passed else 0,
            "passed": bool(passed),
            "expected": expected,
            "observed": observed,
        }
    )


def evaluate(data):
    points = []
    summary = data.get("quote_summary", {})
    policy = data.get("policy_flags", {})
    tier = summary.get("catalog_tier", {}) if isinstance(summary.get("catalog_tier"), dict) else {}

    air = find_option(data, mode="AIR", freight_id="FR-MAT-AIR")
    sea = find_option(data, mode="SEA", freight_id="FR-MAT-SEA")
    road = find_option(data, mode="ROAD", freight_id="FR-MAT-ROAD")

    tier_ok = (
        normalize_text(summary.get("quote_id")) == "Q_TE_MAT_7791"
        and normalize_text(summary.get("customer_id")) == "CUST_MWA"
        and normalize_text(summary.get("product_code")) == "MAT_EMERG_C"
        and int_equals(summary.get("confirmed_quantity"), 640)
        and (not tier or (int_equals(tier.get("min_quantity"), 500) and int_equals(tier.get("max_quantity"), 799)))
        and money_equals(summary.get("unit_price_usd"), "332.00")
        and int_equals(summary.get("lead_time_days"), 28)
        and int_equals(summary.get("shelf_life_months"), 30)
        and money_equals(summary.get("exw_total_usd"), "212480.00")
    )
    add_point(
        points,
        "tier price, lead time, shelf life, and EXW total",
        3,
        tier_ok,
        {
            "quote_id": "Q-TE-MAT-7791",
            "customer_id": "CUST-MWA",
            "product_code": "MAT-EMERG-C",
            "confirmed_quantity": 640,
            "tier": "500-799",
            "unit_price_usd": 332.00,
            "lead_time_days": 28,
            "shelf_life_months": 30,
            "exw_total_usd": 212480.00,
        },
        {
            "quote_id": summary.get("quote_id"),
            "customer_id": summary.get("customer_id"),
            "product_code": summary.get("product_code"),
            "confirmed_quantity": summary.get("confirmed_quantity"),
            "catalog_tier": tier,
            "unit_price_usd": summary.get("unit_price_usd"),
            "lead_time_days": summary.get("lead_time_days"),
            "shelf_life_months": summary.get("shelf_life_months"),
            "exw_total_usd": summary.get("exw_total_usd"),
        },
    )

    freight_totals_ok = (
        money_equals(option_value(air, "freight_cost_usd", "cost_usd", "freight_cost"), "29750.00")
        and money_equals(option_value(air, "grand_total_usd", "total_usd", "exw_plus_freight_usd"), "242230.00")
        and money_equals(option_value(sea, "freight_cost_usd", "cost_usd", "freight_cost"), "7200.00")
        and money_equals(option_value(sea, "grand_total_usd", "total_usd", "exw_plus_freight_usd"), "219680.00")
        and money_equals(option_value(road, "freight_cost_usd", "cost_usd", "freight_cost"), "11900.00")
        and money_equals(option_value(road, "grand_total_usd", "total_usd", "exw_plus_freight_usd"), "224380.00")
    )
    add_point(
        points,
        "three freight costs and grand totals",
        3,
        freight_totals_ok,
        {
            "FR-MAT-AIR": {"freight_cost_usd": 29750.00, "grand_total_usd": 242230.00},
            "FR-MAT-SEA": {"freight_cost_usd": 7200.00, "grand_total_usd": 219680.00},
            "FR-MAT-ROAD": {"freight_cost_usd": 11900.00, "grand_total_usd": 224380.00},
        },
        {
            "FR-MAT-AIR": {
                "freight_cost_usd": option_value(air, "freight_cost_usd", "cost_usd", "freight_cost"),
                "grand_total_usd": option_value(air, "grand_total_usd", "total_usd", "exw_plus_freight_usd"),
            },
            "FR-MAT-SEA": {
                "freight_cost_usd": option_value(sea, "freight_cost_usd", "cost_usd", "freight_cost"),
                "grand_total_usd": option_value(sea, "grand_total_usd", "total_usd", "exw_plus_freight_usd"),
            },
            "FR-MAT-ROAD": {
                "freight_cost_usd": option_value(road, "freight_cost_usd", "cost_usd", "freight_cost"),
                "grand_total_usd": option_value(road, "grand_total_usd", "total_usd", "exw_plus_freight_usd"),
            },
        },
    )

    road_flag = risk_flag(road)
    risk_ok = (
        risk_level(air) == "LOW"
        and risk_level(sea) == "LOW"
        and risk_level(road) == "HIGH"
        and (road_flag == "HIGH_BORDER_RISK" or ("HIGH" in road_flag and "BORDER" in road_flag))
    )
    add_point(
        points,
        "route risk flags",
        3,
        risk_ok,
        {
            "FR-MAT-AIR": {"risk_level": "LOW"},
            "FR-MAT-SEA": {"risk_level": "LOW"},
            "FR-MAT-ROAD": {"risk_level": "HIGH", "risk_flag": "HIGH_BORDER_RISK"},
        },
        {
            "FR-MAT-AIR": {"risk_level": option_value(air, "risk_level", "route_risk")},
            "FR-MAT-SEA": {"risk_level": option_value(sea, "risk_level", "route_risk")},
            "FR-MAT-ROAD": {
                "risk_level": option_value(road, "risk_level", "route_risk", "border_risk"),
                "risk_flag": option_value(road, "risk_flag", "route_risk_flag", "border_risk_flag"),
            },
        },
    )

    recommendation_ok = (
        normalize_text(policy.get("recommended_mode") or get_path(data, ["transport_decisions", "recommended_mode"]))
        == "AIR"
    )
    add_point(
        points,
        "recommended mode",
        2,
        recommendation_ok,
        {"recommended_mode": "AIR"},
        {
            "recommended_mode": policy.get("recommended_mode")
            or get_path(data, ["transport_decisions", "recommended_mode"])
        },
    )

    feasibility_ok = feasibility(air) is True and feasibility(sea) is False and feasibility(road) is True
    add_point(
        points,
        "delivery window feasibility",
        2,
        feasibility_ok,
        {
            "FR-MAT-AIR": True,
            "FR-MAT-SEA": False,
            "FR-MAT-ROAD": True,
        },
        {
            "FR-MAT-AIR": option_value(
                air, "delivery_window_feasible", "requested_delivery_window_feasible", "feasible"
            ),
            "FR-MAT-SEA": option_value(
                sea, "delivery_window_feasible", "requested_delivery_window_feasible", "feasible"
            ),
            "FR-MAT-ROAD": option_value(
                road, "delivery_window_feasible", "requested_delivery_window_feasible", "feasible"
            ),
        },
    )

    warning_text = normalize_text(policy.get("freight_validity_warning"))
    warning_ok = any_nested_true(
        data, {"freight_reconfirmation_required", "reconfirmation_required", "requires_reconfirmation"}
    ) and ("RECONFIRM" in warning_text or bool_value(policy.get("freight_reconfirmation_required")) is True)
    add_point(
        points,
        "freight validity warning",
        1,
        warning_ok,
        {"freight_reconfirmation_required": True, "warning": "Freight rates require reconfirmation at final order."},
        {
            "freight_reconfirmation_required": policy.get("freight_reconfirmation_required"),
            "freight_validity_warning": policy.get("freight_validity_warning"),
        },
    )

    terms_ok = (
        normalize_text(policy.get("payment_terms") or get_path(data, ["pricing", "payment_terms"]))
        == "NET_30_AFTER_PO"
    )
    add_point(
        points,
        "account terms",
        1,
        terms_ok,
        {"payment_terms": "NET_30_AFTER_PO"},
        {"payment_terms": policy.get("payment_terms") or get_path(data, ["pricing", "payment_terms"])},
    )

    all_valid_value = bool_value(policy.get("all_freight_options_valid_on_quote_date"))
    pricing_date = get_path(policy, ["source_date_control", "quote_date_used_for_pricing"]) or policy.get(
        "quote_date_used_for_pricing"
    )
    freight_date = get_path(policy, ["source_date_control", "quote_date_used_for_freight_validity"]) or policy.get(
        "quote_date_used_for_freight_validity"
    )
    pricing_source_ok = any_nested_text_contains(
        data, {"pricing_source", "pricing_source_precedence", "source_precedence"}, {"INTERNAL", "CATALOG"}
    ) or any_nested_text_contains(
        data, {"pricing_source", "pricing_source_precedence", "source_precedence"}, {"INTERNAL", "TIER"}
    )
    source_control_ok = (
        pricing_source_ok
        and pricing_date == "2026-06-01"
        and freight_date == "2026-06-01"
        and all_valid_value is True
        and option_value(air, "valid_until", "expires_on") == "2026-06-20"
        and option_value(sea, "valid_until", "expires_on") == "2026-06-30"
        and option_value(road, "valid_until", "expires_on") == "2026-06-11"
    )
    add_point(
        points,
        "source precedence and source-date control",
        2,
        source_control_ok,
        {
            "pricing_source": "INTERNAL_CATALOG_TIER",
            "quote_date_used_for_freight_validity": "2026-06-01",
            "all_freight_options_valid_on_quote_date": True,
            "valid_until": {
                "FR-MAT-AIR": "2026-06-20",
                "FR-MAT-SEA": "2026-06-30",
                "FR-MAT-ROAD": "2026-06-11",
            },
        },
        {
            "pricing_source": summary.get("pricing_source"),
            "source_date_control": policy.get("source_date_control"),
            "all_freight_options_valid_on_quote_date": policy.get("all_freight_options_valid_on_quote_date"),
            "valid_until": {
                "FR-MAT-AIR": option_value(air, "valid_until", "expires_on"),
                "FR-MAT-SEA": option_value(sea, "valid_until", "expires_on"),
                "FR-MAT-ROAD": option_value(road, "valid_until", "expires_on"),
            },
        },
    )

    controls = policy.get("decision_controls", {}) if isinstance(policy.get("decision_controls"), dict) else {}
    decision_controls_ok = (
        normalize_text(controls.get("delivery_feasibility_basis")) == "LEAD_TIME_PLUS_TRANSIT_ONLY"
        and bool_value(controls.get("risk_separate_from_feasibility")) is True
        and normalize_text(controls.get("recommendation_basis")) == "SERVICE_WINDOW_THEN_RISK_THEN_COST"
    )
    add_point(
        points,
        "decision-control conventions",
        5,
        decision_controls_ok,
        {
            "delivery_feasibility_basis": "LEAD_TIME_PLUS_TRANSIT_ONLY",
            "risk_separate_from_feasibility": True,
            "recommendation_basis": "SERVICE_WINDOW_THEN_RISK_THEN_COST",
        },
        controls,
    )

    score = sum(point["earned"] for point in points)
    return {
        "score": score,
        "max_score": MAX_SCORE,
        "score_percent": round((score / MAX_SCORE) * 100, 2),
        "passed": score == MAX_SCORE,
        "details": points,
    }


def main():
    default_path = Path(__file__).resolve().parent / "../output/answer.json"
    candidate_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path
    try:
        data = load_json(candidate_path)
        result = evaluate(data)
    except Exception as exc:
        result = {
            "score": 0,
            "max_score": MAX_SCORE,
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
    print(json.dumps(result, indent=2, sort_keys=False))


if __name__ == "__main__":
    main()
