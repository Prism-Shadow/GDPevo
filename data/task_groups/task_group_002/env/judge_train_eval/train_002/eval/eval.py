#!/usr/bin/env python3
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path


CENT = Decimal("0.01")

EXPECTED_LINES = {
    "IEHK-BASIC": {
        "article_number": "500101",
        "quantity": 10,
        "unit_price": Decimal("2420.00"),
        "lead_time_days": 21,
        "shelf_life_months": 36,
        "line_total": Decimal("24200.00"),
    },
    "IEHK-SUPP-A": {
        "article_number": "500102",
        "quantity": 1,
        "unit_price": Decimal("1380.00"),
        "lead_time_days": 21,
        "shelf_life_months": 30,
        "line_total": Decimal("1380.00"),
    },
    "IEHK-SUPP-B": {
        "article_number": "500103",
        "quantity": 1,
        "unit_price": Decimal("1525.00"),
        "lead_time_days": 28,
        "shelf_life_months": 30,
        "line_total": Decimal("1525.00"),
    },
    "IEHK-TRAUMA": {
        "article_number": "500110",
        "quantity": 1,
        "unit_price": Decimal("3100.00"),
        "lead_time_days": 35,
        "shelf_life_months": 24,
        "line_total": Decimal("3100.00"),
    },
    "IEHK-MALARIA": {
        "article_number": "500115",
        "quantity": 1,
        "unit_price": Decimal("1880.00"),
        "lead_time_days": 28,
        "shelf_life_months": 24,
        "line_total": Decimal("1880.00"),
    },
}

EXPECTED_GRAND_TOTAL = Decimal("32185.00")
MAX_SCORE = 18


def money(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        value = value.strip().replace("$", "").replace(",", "")
    try:
        return Decimal(str(value)).quantize(CENT)
    except (InvalidOperation, ValueError):
        return None


def as_int(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def nested(data, *keys):
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def first_present(data, paths):
    for path in paths:
        value = nested(data, *path)
        if value is not None:
            return value
    return None


def line_code(line):
    for key in ("product_code", "module_code", "sku", "item_code"):
        value = line.get(key)
        if value:
            return str(value)
    return None


def build_line_map(data):
    lines = data.get("line_items", [])
    if not isinstance(lines, list):
        return {}, []
    line_map = {}
    codes = []
    for line in lines:
        if not isinstance(line, dict):
            codes.append(None)
            continue
        code = line_code(line)
        codes.append(code)
        if code is not None:
            line_map[code] = line
    return line_map, codes


def bool_is_true(value):
    return value is True


def add_check(checks, check_id, weight, passed, message):
    checks.append(
        {
            "id": check_id,
            "weight": weight,
            "earned": weight if passed else 0,
            "passed": bool(passed),
            "message": message,
        }
    )


def score_candidate(data):
    checks = []
    line_map, codes = build_line_map(data)
    expected_codes = set(EXPECTED_LINES)

    line_set_ok = set(codes) == expected_codes and len(codes) == len(expected_codes)
    article_numbers_ok = all(
        str(line_map.get(code, {}).get("article_number", "")) == expected["article_number"]
        for code, expected in EXPECTED_LINES.items()
    )
    add_check(
        checks,
        "module_line_set",
        3,
        line_set_ok and article_numbers_ok,
        "Expected exactly the five requested IEHK module lines with matching article numbers and no component lines.",
    )

    quantities_ok = all(
        as_int(line_map.get(code, {}).get("quantity")) == expected["quantity"]
        for code, expected in EXPECTED_LINES.items()
    )
    add_check(
        checks,
        "quantities",
        2,
        quantities_ok,
        "Expected module quantities: IEHK-BASIC 10, all other requested modules 1.",
    )

    unit_prices_ok = all(
        money(line_map.get(code, {}).get("unit_price")) == expected["unit_price"]
        for code, expected in EXPECTED_LINES.items()
    )
    add_check(
        checks,
        "unit_prices_from_catalog",
        3,
        unit_prices_ok,
        "Expected catalog unit prices for all requested modules.",
    )

    line_totals_ok = all(
        money(line_map.get(code, {}).get("line_total")) == expected["line_total"]
        for code, expected in EXPECTED_LINES.items()
    )
    grand_total = first_present(data, [("quote_controls", "grand_total"), ("grand_total",)])
    grand_total_ok = money(grand_total) == EXPECTED_GRAND_TOTAL
    add_check(
        checks,
        "line_totals_and_grand_total",
        3,
        line_totals_ok and grand_total_ok,
        "Expected all line totals and grand total 32185.00.",
    )

    lead_and_shelf_ok = all(
        as_int(line_map.get(code, {}).get("lead_time_days")) == expected["lead_time_days"]
        and as_int(line_map.get(code, {}).get("shelf_life_months")) == expected["shelf_life_months"]
        for code, expected in EXPECTED_LINES.items()
    )
    add_check(
        checks,
        "shelf_life_and_lead_time",
        2,
        lead_and_shelf_ok,
        "Expected lead-time days and shelf-life months for every module line.",
    )

    quote_basis = first_present(
        data, [("quote_header", "quote_basis"), ("quote_controls", "quote_basis"), ("quote_basis",)]
    )
    freight_excluded = first_present(data, [("quote_controls", "freight_excluded"), ("freight_excluded",)])
    exw_ok = quote_basis == "EXW_ONLY" and bool_is_true(freight_excluded)
    add_check(
        checks,
        "exw_and_freight_exclusion",
        2,
        exw_ok,
        "Expected quote_basis EXW_ONLY and freight_excluded true.",
    )

    payment_terms = first_present(data, [("quote_controls", "payment_terms"), ("payment_terms",)])
    validity_days = first_present(data, [("quote_controls", "offer_validity_days"), ("offer_validity_days",)])
    controls_ok = payment_terms == "PREPAY_100" and as_int(validity_days) == 30
    add_check(
        checks,
        "new_client_payment_and_validity",
        2,
        controls_ok,
        "Expected PREPAY_100 and 30 offer validity days for the new NGO client.",
    )

    who_required = first_present(
        data,
        [
            ("quote_controls", "who_documentation_required"),
            ("who_documentation_required",),
            ("quote_controls", "who_help_link_required"),
        ],
    )
    add_check(
        checks,
        "who_documentation_flag",
        1,
        bool_is_true(who_required),
        "Expected who_documentation_required true.",
    )

    earned = sum(check["earned"] for check in checks)
    return {
        "score": earned,
        "max_score": MAX_SCORE,
        "percentage": round(earned / MAX_SCORE, 6),
        "checks": checks,
    }


def main():
    candidate_path = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "../output/answer.json"
    )
    candidate_path = candidate_path.expanduser()
    try:
        with candidate_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        result = {
            "score": 0,
            "max_score": MAX_SCORE,
            "percentage": 0.0,
            "candidate_path": str(candidate_path),
            "error": f"Could not read candidate JSON: {exc}",
            "checks": [],
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1

    if not isinstance(data, dict):
        result = {
            "score": 0,
            "max_score": MAX_SCORE,
            "percentage": 0.0,
            "candidate_path": str(candidate_path),
            "error": "Candidate JSON must be an object.",
            "checks": [],
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1

    result = score_candidate(data)
    result["candidate_path"] = str(candidate_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
