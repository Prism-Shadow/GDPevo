#!/usr/bin/env python3
import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path


MAX_SCORE = 14


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def get_path(data, path, default=None):
    cur = data
    for part in path:
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip().upper()


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


def bool_is_true(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "y", "1", "stale", "invalid", "expired"}
    if isinstance(value, (int, float)):
        return value == 1
    return False


def bool_is_false(value):
    if isinstance(value, bool):
        return not value
    if isinstance(value, str):
        return value.strip().lower() in {"false", "no", "n", "0", "valid"}
    if isinstance(value, (int, float)):
        return value == 0
    return False


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
    decisions = data.get("transport_decisions", {})
    raw = decisions.get("freight_options")
    options = list(iter_dicts(raw))
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
    mode_norm = normalize_text(mode)
    id_norm = normalize_text(freight_id)
    for option in freight_options(data):
        option_mode = normalize_text(option.get("mode") or option.get("transport_mode"))
        option_id = normalize_text(option.get("freight_id") or option.get("id") or option.get("quote_id"))
        if id_norm and option_id == id_norm:
            return option
        if mode_norm and option_mode == mode_norm:
            return option
    return {}


def option_value(option, *keys):
    for key in keys:
        if key in option:
            return option[key]
    return None


def risk_value(option):
    return normalize_text(
        option_value(
            option,
            "customs_border_risk",
            "customs_risk",
            "border_risk",
            "risk_level",
            "route_risk",
        )
    )


def validity_value(option):
    return normalize_text(option_value(option, "validity_status", "source_validity", "status"))


def any_nested_true(data, keys):
    if isinstance(data, dict):
        for key, value in data.items():
            if key in keys and bool_is_true(value):
                return True
            if any_nested_true(value, keys):
                return True
    elif isinstance(data, list):
        return any(any_nested_true(item, keys) for item in data)
    return False


def any_nested_text(data, keys, expected):
    expected_norm = normalize_text(expected)
    if isinstance(data, dict):
        for key, value in data.items():
            if key in keys and normalize_text(value) == expected_norm:
                return True
            if any_nested_text(value, keys, expected):
                return True
    elif isinstance(data, list):
        return any(any_nested_text(item, keys, expected) for item in data)
    return False


def add_point(points, name, weight, passed, detail):
    earned = weight if passed else 0
    points.append(
        {
            "name": name,
            "weight": weight,
            "earned": earned,
            "passed": bool(passed),
            "detail": detail,
        }
    )
    return earned


def evaluate(data):
    points = []
    score = 0

    pricing = data.get("pricing", {})
    tier = pricing.get("catalog_tier", {}) if isinstance(pricing.get("catalog_tier"), dict) else {}
    tier_ok = (
        normalize_text(pricing.get("quote_id")) == "Q-TR-LD-5521"
        and normalize_text(pricing.get("customer_id")) == "CUST-GHL"
        and normalize_text(pricing.get("product_code")) == "LD-REAGENT-44"
        and int_equals(pricing.get("confirmed_quantity"), 1000)
        and int_equals(tier.get("min_quantity"), 900)
        and int_equals(tier.get("max_quantity"), 1199)
        and money_equals(tier.get("unit_price_usd"), "76.00")
        and int_equals(tier.get("lead_time_days"), 14)
        and int_equals(tier.get("shelf_life_months"), 18)
        and money_equals(pricing.get("exw_total_usd"), "76000.00")
    )
    score += add_point(
        points,
        "selected catalog tier and EXW total",
        3,
        tier_ok,
        "Expected LD-REAGENT-44 quantity 1000 to use the 900-1199 tier at 76.00 USD, lead time 14 days, shelf life 18 months, EXW total 76000.00.",
    )

    air = find_option(data, mode="AIR", freight_id="FR-LD-AIR")
    sea = find_option(data, mode="SEA", freight_id="FR-LD-SEA")
    road = find_option(data, mode="ROAD", freight_id="FR-LD-ROAD")

    road_validity = validity_value(road)
    air_validity = validity_value(air)
    sea_validity = validity_value(sea)
    road_stale_flag = (
        bool_is_true(option_value(road, "source_is_stale", "is_stale", "stale", "expired"))
        or bool_is_false(option_value(road, "source_is_valid", "valid"))
        or road_validity in {"STALE", "INVALID", "EXPIRED"}
        or bool_is_true(get_path(data, ["client_warnings", "road_quote_invalid_or_stale"]))
    )
    validity_ok = (
        option_value(road, "valid_until", "expires_on") == "2026-05-25"
        and road_stale_flag
        and air_validity in {"VALID", "CURRENT", ""}
        and sea_validity in {"VALID", "CURRENT", ""}
    )
    score += add_point(
        points,
        "source validity and stale road quote flag",
        2,
        validity_ok,
        "Expected FR-LD-ROAD to be marked stale or invalid because it expired on 2026-05-25 before the 2026-06-01 quote date; air and sea should remain valid.",
    )

    risk_ok = risk_value(air) == "LOW" and risk_value(sea) == "LOW" and risk_value(road) == "HIGH"
    score += add_point(
        points,
        "customs/border risk enum",
        2,
        risk_ok,
        "Expected AIR LOW, SEA LOW, and ROAD HIGH customs/border risk.",
    )

    totals_ok = (
        money_equals(option_value(air, "grand_total_usd", "total_usd"), "97400.00")
        and money_equals(option_value(sea, "grand_total_usd", "total_usd"), "81200.00")
        and money_equals(option_value(road, "grand_total_usd", "total_usd"), "80800.00")
    )
    score += add_point(
        points,
        "air/sea/road grand totals",
        3,
        totals_ok,
        "Expected grand totals: AIR 97400.00, SEA 81200.00, ROAD 80800.00.",
    )

    recommendation_ok = normalize_text(get_path(data, ["transport_decisions", "recommended_mode"])) == "SEA"
    score += add_point(
        points,
        "recommendation enum",
        2,
        recommendation_ok,
        "Expected recommended_mode to be SEA.",
    )

    warning_ok = any_nested_true(
        data,
        {"freight_reconfirmation_required", "reconfirmation_required", "requires_reconfirmation"},
    )
    score += add_point(
        points,
        "freight warning",
        1,
        warning_ok,
        "Expected freight reconfirmation_required to be true.",
    )

    policy_ok = any_nested_text(data, {"payment_terms", "terms"}, "NET_30_AFTER_PO")
    score += add_point(
        points,
        "policy terms",
        1,
        policy_ok,
        "Expected payment terms NET_30_AFTER_PO.",
    )

    return {
        "score": score,
        "max_score": MAX_SCORE,
        "score_fraction": round(score / MAX_SCORE, 6),
        "points": points,
    }


def main():
    candidate = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../output/answer.json")
    try:
        data = load_json(candidate)
        result = evaluate(data)
    except Exception as exc:
        result = {
            "score": 0,
            "max_score": MAX_SCORE,
            "score_fraction": 0.0,
            "error": f"{type(exc).__name__}: {exc}",
            "points": [],
        }
    print(json.dumps(result, indent=2, sort_keys=False))


if __name__ == "__main__":
    main()
