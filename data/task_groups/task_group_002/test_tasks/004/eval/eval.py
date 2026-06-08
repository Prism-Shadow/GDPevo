#!/usr/bin/env python3
import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path


EXPECTED_LINES = {
    "FCLINIC-CORE": {
        "article_number": "720201",
        "quantity": 12,
        "unit_price": Decimal("1850.00"),
        "lead_time_days": 28,
        "shelf_life_months": 36,
        "line_total": Decimal("22200.00"),
    },
    "FCLINIC-MAT": {
        "article_number": "720205",
        "quantity": 6,
        "unit_price": Decimal("1425.00"),
        "lead_time_days": 28,
        "shelf_life_months": 30,
        "line_total": Decimal("8550.00"),
    },
    "FCLINIC-WASH": {
        "article_number": "720210",
        "quantity": 6,
        "unit_price": Decimal("980.00"),
        "lead_time_days": 21,
        "shelf_life_months": 30,
        "line_total": Decimal("5880.00"),
    },
}

EXPECTED_FREIGHT = {
    "FR-FC-AIR": {
        "mode": "AIR",
        "freight_cost": Decimal("18480.00"),
        "transit_days": "5-7",
        "valid_until": "2026-06-18",
        "risk_level": "LOW",
        "route_risk_flag": "LOW_RISK",
        "grand_total": Decimal("55110.00"),
    },
    "FR-FC-SEA": {
        "mode": "SEA",
        "freight_cost": Decimal("4100.00"),
        "transit_days": "30-36",
        "valid_until": "2026-06-26",
        "risk_level": "LOW",
        "route_risk_flag": "LOW_RISK",
        "grand_total": Decimal("40730.00"),
    },
    "FR-FC-ROAD": {
        "mode": "ROAD",
        "freight_cost": Decimal("7800.00"),
        "transit_days": "14-20",
        "valid_until": "2026-06-08",
        "risk_level": "MEDIUM",
        "route_risk_flag": "MEDIUM_BORDER_RISK",
        "grand_total": Decimal("44430.00"),
    },
}


def norm(value):
    return str(value).strip().upper()


def normalize_flag(value):
    text = norm(value).replace("-", "_").replace(" ", "_")
    if text in {"MEDIUM_BORDER", "BORDER_MEDIUM", "MEDIUM_BORDER_RISK", "BORDER_RISK_MEDIUM"}:
        return "MEDIUM_BORDER_RISK"
    if text in {"LOW", "LOW_RISK"}:
        return "LOW_RISK"
    return text


def money(value):
    if isinstance(value, bool) or value is None:
        return None
    text = str(value).strip().replace("$", "").replace(",", "")
    try:
        return Decimal(text).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return None


def int_value(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def list_by_key(items, key):
    if not isinstance(items, list):
        return {}
    result = {}
    for item in items:
        if isinstance(item, dict) and item.get(key) is not None:
            result[norm(item.get(key))] = item
    return result


def bool_value(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return None


def add_result(results, point_id, max_score, passed, detail):
    results.append(
        {
            "id": point_id,
            "score": max_score if passed else 0,
            "max_score": max_score,
            "passed": bool(passed),
            "detail": detail,
        }
    )


def main():
    default_path = Path(__file__).resolve().parent / "../output/answer.json"
    candidate_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path
    if not candidate_arg.is_absolute():
        candidate_path = (Path.cwd() / candidate_arg).resolve()
    else:
        candidate_path = candidate_arg.resolve()

    try:
        with candidate_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": 33,
                    "passed": False,
                    "error": f"Could not load candidate JSON: {exc}",
                    "candidate_path": str(candidate_path),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    quote_summary = data.get("quote_summary", {}) if isinstance(data, dict) else {}
    quote_controls = data.get("quote_controls", {}) if isinstance(data, dict) else {}
    lines = list_by_key(data.get("line_items", []), "product_code") if isinstance(data, dict) else {}
    freight = list_by_key(data.get("freight_options", []), "freight_id") if isinstance(data, dict) else {}
    results = []

    line_set_passed = set(lines) == set(EXPECTED_LINES)
    if line_set_passed:
        for product_code, expected in EXPECTED_LINES.items():
            item = lines[product_code]
            line_set_passed = (
                norm(item.get("article_number")) == expected["article_number"]
                and int_value(item.get("lead_time_days")) == expected["lead_time_days"]
                and int_value(item.get("shelf_life_months")) == expected["shelf_life_months"]
                and money(item.get("line_total")) == expected["line_total"]
            )
            if not line_set_passed:
                break
    add_result(
        results,
        "hybrid_module_line_set",
        3,
        line_set_passed,
        "Expected exactly FCLINIC-CORE, FCLINIC-MAT, and FCLINIC-WASH with correct article, lead time, shelf life, and line total fields.",
    )

    quantity_price_passed = set(lines) == set(EXPECTED_LINES)
    if quantity_price_passed:
        for product_code, expected in EXPECTED_LINES.items():
            item = lines[product_code]
            quantity_price_passed = (
                int_value(item.get("quantity")) == expected["quantity"]
                and money(item.get("unit_price")) == expected["unit_price"]
            )
            if not quantity_price_passed:
                break
    add_result(
        results,
        "quantities_and_unit_prices",
        3,
        quantity_price_passed,
        "Expected module quantities 12, 6, 6 and unit prices 1850.00, 1425.00, 980.00.",
    )

    exw_passed = (
        norm(quote_summary.get("quote_id")) == "Q-TE-FC-4560"
        and norm(quote_summary.get("customer_id")) == "CUST-CAREBRIDGE"
        and str(quote_summary.get("quote_date", "")).strip() == "2026-06-01"
        and money(quote_summary.get("exw_subtotal")) == Decimal("36630.00")
    )
    add_result(
        results,
        "exw_subtotal",
        2,
        exw_passed,
        "Expected quote Q-TE-FC-4560 for CUST-CAREBRIDGE dated 2026-06-01 with EXW subtotal 36630.00.",
    )

    freight_totals_passed = set(freight) == set(EXPECTED_FREIGHT)
    if freight_totals_passed:
        for freight_id, expected in EXPECTED_FREIGHT.items():
            item = freight[freight_id]
            freight_totals_passed = (
                norm(item.get("mode")) == expected["mode"]
                and money(item.get("freight_cost")) == expected["freight_cost"]
                and str(item.get("transit_days", "")).strip() == expected["transit_days"]
                and str(item.get("valid_until", "")).strip() == expected["valid_until"]
                and money(item.get("grand_total")) == expected["grand_total"]
            )
            if not freight_totals_passed:
                break
    add_result(
        results,
        "freight_option_grand_totals",
        3,
        freight_totals_passed,
        "Expected FR-FC-AIR 55110.00, FR-FC-SEA 40730.00, and FR-FC-ROAD 44430.00 with matching modes, freight costs, transit ranges, and validity dates.",
    )

    recommendation_passed = norm(quote_controls.get("recommended_mode")) == "SEA"
    add_result(
        results,
        "advisory_transport_recommendation",
        2,
        recommendation_passed,
        "Expected recommended advisory transport mode SEA.",
    )

    controls_passed = (
        norm(quote_controls.get("payment_terms")) == "PREPAY_100"
        and int_value(quote_controls.get("offer_validity_days")) == 30
        and norm(quote_controls.get("quote_basis")) == "EXW_WITH_ADVISORY_FREIGHT"
        and bool_value(quote_controls.get("freight_in_base_total")) is False
    )
    add_result(
        results,
        "quote_controls_payment_validity",
        2,
        controls_passed,
        "Expected PREPAY_100, 30 offer-validity days, EXW_WITH_ADVISORY_FREIGHT, and freight_in_base_total false.",
    )

    no_component_lines = True
    if isinstance(data, dict):
        for key in ("component_lines", "components", "kit_components"):
            if key in data and data.get(key) not in (None, [], {}):
                no_component_lines = False
    component_passed = (
        bool_value(quote_controls.get("component_overexpansion_avoided")) is True
        and no_component_lines
        and set(lines) == set(EXPECTED_LINES)
    )
    add_result(
        results,
        "component_overexpansion_avoidance",
        2,
        component_passed,
        "Expected component_overexpansion_avoided true and no component-level quote lines.",
    )

    road = freight.get("FR-FC-ROAD", {})
    route_risk_passed = (
        norm(road.get("risk_level")) == "MEDIUM"
        and normalize_flag(road.get("route_risk_flag")) == "MEDIUM_BORDER_RISK"
    )
    add_result(
        results,
        "route_risk_flag",
        1,
        route_risk_passed,
        "Expected FR-FC-ROAD risk_level MEDIUM and route_risk_flag MEDIUM_BORDER_RISK.",
    )

    policy_controls = quote_controls.get("policy_controls", {})
    if not isinstance(policy_controls, dict):
        policy_controls = {}
    advisory_scope_passed = (
        norm(policy_controls.get("freight_scope")) == "ADVISORY_ONLY"
        and bool_value(policy_controls.get("base_total_excludes_freight")) is True
    )
    add_result(
        results,
        "advisory_scope_policy_controls",
        5,
        advisory_scope_passed,
        "Expected policy controls freight_scope ADVISORY_ONLY and base_total_excludes_freight true.",
    )

    component_policy_passed = norm(policy_controls.get("component_line_policy")) == "MODULE_LINES_ONLY"
    add_result(
        results,
        "component_line_policy_control",
        5,
        component_policy_passed,
        "Expected policy control component_line_policy MODULE_LINES_ONLY.",
    )

    payment_policy_passed = norm(policy_controls.get("payment_policy_source")) == "NEW_CLIENT_POLICY"
    add_result(
        results,
        "payment_source_policy_control",
        5,
        payment_policy_passed,
        "Expected policy control payment_policy_source NEW_CLIENT_POLICY.",
    )

    score = sum(item["score"] for item in results)
    max_score = sum(item["max_score"] for item in results)
    output = {
        "score": score,
        "max_score": max_score,
        "passed": score == max_score,
        "candidate_path": str(candidate_path),
        "details": results,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
