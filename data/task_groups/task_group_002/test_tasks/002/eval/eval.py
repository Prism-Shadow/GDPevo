#!/usr/bin/env python3
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path


CENT = Decimal("0.01")

EXPECTED_LINES = {
    "CHOL-BASIC": ("610101", 8, "1180.00", 14, 24, "9440.00"),
    "CHOL-IV": ("610105", 4, "760.00", 14, 18, "3040.00"),
    "CHOL-WASH": ("610110", 3, "920.00", 21, 24, "2760.00"),
    "CHOL-LAB": ("610115", 2, "1460.00", 28, 18, "2920.00"),
    "CHOL-ORS": ("610120", 12, "210.00", 10, 30, "2520.00"),
}


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


def norm_enum(value):
    if value is None:
        return None
    return str(value).strip().upper()


def nested(data, *keys):
    cur = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def line_map(data):
    out = {}
    for item in data.get("line_items", []):
        if isinstance(item, dict) and item.get("product_code"):
            out[str(item["product_code"])] = item
    return out


def add(checks, check_id, weight, passed, message):
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
    lines = line_map(data)

    add(
        checks,
        "module_only_line_set",
        2,
        set(lines) == set(EXPECTED_LINES)
        and len(data.get("line_items", [])) == len(EXPECTED_LINES)
        and all(str(lines[c].get("article_number", "")) == v[0] for c, v in EXPECTED_LINES.items()),
        "Expected exactly the five requested commercial module lines and matching article numbers.",
    )

    add(
        checks,
        "quantities",
        1,
        all(as_int(lines.get(c, {}).get("quantity")) == v[1] for c, v in EXPECTED_LINES.items()),
        "Expected consolidated module quantities, including CHOL-ORS quantity 12.",
    )

    add(
        checks,
        "catalog_prices_and_line_totals",
        2,
        all(
            money(lines.get(c, {}).get("unit_price")) == Decimal(v[2])
            and money(lines.get(c, {}).get("line_total")) == Decimal(v[5])
            for c, v in EXPECTED_LINES.items()
        ),
        "Expected catalog unit prices and line totals for every module.",
    )

    add(
        checks,
        "grand_total",
        1,
        money(nested(data, "quote_controls", "grand_total")) == Decimal("20680.00"),
        "Expected grand total 20680.00.",
    )

    add(
        checks,
        "shelf_life_and_lead_time",
        1,
        all(
            as_int(lines.get(c, {}).get("lead_time_days")) == v[3]
            and as_int(lines.get(c, {}).get("shelf_life_months")) == v[4]
            for c, v in EXPECTED_LINES.items()
        ),
        "Expected lead-time days and shelf-life months from the catalog.",
    )

    controls = data.get("quote_controls", {})
    header = data.get("quote_header", {})
    add(
        checks,
        "commercial_scope_controls",
        3,
        norm_enum(header.get("quote_basis")) == "EXW_ONLY"
        and controls.get("freight_excluded") is True
        and norm_enum(controls.get("payment_terms")) == "PREPAY_100"
        and as_int(controls.get("offer_validity_days")) == 30,
        "Expected EXW-only scope, freight excluded, PREPAY_100, and 30-day validity.",
    )

    add(
        checks,
        "granularity_and_component_controls",
        4,
        controls.get("duplicate_rfq_normalized") is True
        and norm_enum(controls.get("line_granularity")) == "MODULE_LINES"
        and norm_enum(controls.get("component_pricing_action")) == "EXCLUDE_COMPONENTS",
        "Expected duplicate normalization, module-line granularity, and component exclusion.",
    )

    add(
        checks,
        "policy_source_controls",
        4,
        norm_enum(controls.get("payment_policy_source")) == "NEW_CLIENT_POLICY"
        and norm_enum(controls.get("quote_scope_policy")) == "INDICATIVE_EXW_NO_DESTINATION"
        and norm_enum(controls.get("total_basis")) == "CATALOG_LINE_SUM_ONLY",
        "Expected the correct payment, quote-scope, and total-basis policy controls.",
    )

    earned = sum(c["earned"] for c in checks)
    max_score = sum(c["weight"] for c in checks)
    return {
        "score": earned,
        "max_score": max_score,
        "score_fraction": round(earned / max_score, 6),
        "passed": earned == max_score,
        "checks": checks,
    }


def main():
    if len(sys.argv) > 2:
        raise SystemExit("Usage: eval.py [candidate_answer.json]")
    candidate = (
        Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).resolve().parents[1] / "output" / "answer.json"
    )
    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
        result = score_candidate(data)
    except Exception as exc:
        result = {
            "score": 0,
            "max_score": 18,
            "score_fraction": 0.0,
            "passed": False,
            "parse_error": str(exc),
            "checks": [],
        }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
