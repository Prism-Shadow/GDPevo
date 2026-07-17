#!/usr/bin/env python3
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
EXPECTED_PATH = SCRIPT_DIR.parent / "output" / "answer.json"


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def get_path(obj, path):
    cur = obj
    for part in path:
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def normalize_scalar(value, expected):
    if isinstance(expected, bool):
        return value if isinstance(value, bool) else {"__type_mismatch__": value}
    if isinstance(expected, int) and not isinstance(expected, bool):
        if isinstance(value, bool):
            return {"__type_mismatch__": value}
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value
    if isinstance(expected, float):
        if isinstance(value, bool):
            return {"__type_mismatch__": value}
        if isinstance(value, (int, float)):
            return round(float(value), 2)
        return value
    if isinstance(expected, list):
        return value if isinstance(value, list) else {"__type_mismatch__": value}
    if isinstance(expected, dict):
        return value if isinstance(value, dict) else {"__type_mismatch__": value}
    return value


def subset_object(data, base_path, expected, keys):
    out = {}
    for key in keys:
        expected_value = get_path(expected, base_path + [key])
        value = get_path(data, base_path + [key])
        out[key] = normalize_scalar(value, expected_value)
    return out


def normalize_list_of_objects(data, path, expected, sort_key, keys):
    expected_items = get_path(expected, path)
    value = get_path(data, path)
    if not isinstance(value, list):
        return {"__type_mismatch__": value}
    sorted_value = sorted(value, key=lambda item: item.get(sort_key, "") if isinstance(item, dict) else "")
    sorted_expected = sorted(expected_items, key=lambda item: item.get(sort_key, ""))
    normalized = []
    for idx, item in enumerate(sorted_value):
        if not isinstance(item, dict):
            normalized.append({"__type_mismatch__": item})
            continue
        expected_item = sorted_expected[idx] if idx < len(sorted_expected) else {}
        normalized_item = {}
        for key in keys:
            normalized_item[key] = normalize_scalar(item.get(key), expected_item.get(key))
        normalized.append(normalized_item)
    return normalized


def normalize_simple_list(data, path):
    value = get_path(data, path)
    if not isinstance(value, list):
        return {"__type_mismatch__": value}
    return sorted(value)


def build_points(prediction, expected):
    points = []

    purchase_keys = [
        "structure",
        "headline_purchase_price_usd",
        "equity_value_usd",
        "cash_at_close_usd",
        "rollover_equity_usd",
        "active_cap_table_source_doc_id",
        "active_cap_table_as_of",
        "per_share_price_usd",
        "per_share_price_basis",
        "price_per_as_converted_percent_point_usd",
    ]
    points.append(
        {
            "id": "SP1_PURCHASE_PRICE_CAP_TABLE",
            "weight": 3,
            "description": "Correct purchase price, consideration mix, active cap table source, per-share availability, and per ownership-point value.",
            "passed": subset_object(prediction, ["deal_terms"], expected, purchase_keys)
            == subset_object(expected, ["deal_terms"], expected, purchase_keys),
        }
    )

    seller_keys = ["seller_name", "role", "ownership_percent", "gross_proceeds_usd"]
    points.append(
        {
            "id": "SP2_SELLER_ALLOCATIONS",
            "weight": 3,
            "description": "Correct seller allocation set from the active cap table.",
            "passed": normalize_list_of_objects(
                prediction, ["seller_allocations"], expected, "seller_name", seller_keys
            )
            == normalize_list_of_objects(expected, ["seller_allocations"], expected, "seller_name", seller_keys),
        }
    )

    escrow_keys = [
        "general_escrow_percent",
        "general_escrow_usd",
        "general_escrow_policy_status",
        "tax_escrow_percent",
        "tax_escrow_usd",
        "tax_escrow_policy_status",
    ]
    points.append(
        {
            "id": "SP3_ESCROW_TAX_ESCROW",
            "weight": 2,
            "description": "Correct general escrow and tax escrow amounts, percentages, and policy status.",
            "passed": subset_object(prediction, ["deal_terms"], expected, escrow_keys)
            == subset_object(expected, ["deal_terms"], expected, escrow_keys),
        }
    )

    nwc_keys = [
        "nwc_target_usd",
        "nwc_collar_usd",
        "nwc_adjustment_mechanic",
        "nwc_collar_percent_of_equity_value",
    ]
    points.append(
        {
            "id": "SP4_NWC_MECHANICS",
            "weight": 2,
            "description": "Correct working capital target, collar, and adjustment mechanic.",
            "passed": subset_object(prediction, ["deal_terms"], expected, nwc_keys)
            == subset_object(expected, ["deal_terms"], expected, nwc_keys),
        }
    )

    consent_keys = ["contract_name", "annual_revenue_usd", "condition_type", "consent_required"]
    consent_passed = normalize_list_of_objects(
        prediction,
        ["closing_flags", "required_material_consents"],
        expected,
        "contract_name",
        consent_keys,
    ) == normalize_list_of_objects(
        expected,
        ["closing_flags", "required_material_consents"],
        expected,
        "contract_name",
        consent_keys,
    ) and get_path(prediction, ["closing_flags", "consent_condition_status"]) == get_path(
        expected, ["closing_flags", "consent_condition_status"]
    )
    points.append(
        {
            "id": "SP5_CONSENT_CONDITIONS",
            "weight": 2,
            "description": "Correct material consent closing conditions.",
            "passed": consent_passed,
        }
    )

    hsr_keys = ["hsr_required", "hsr_condition", "hsr_basis_code"]
    hsr_passed = subset_object(prediction, ["closing_flags"], expected, hsr_keys) == subset_object(
        expected, ["closing_flags"], expected, hsr_keys
    ) and normalize_simple_list(prediction, ["closing_flags", "other_regulatory_approvals"]) == normalize_simple_list(
        expected, ["closing_flags", "other_regulatory_approvals"]
    )
    points.append(
        {
            "id": "SP6_HSR_EXCLUSION",
            "weight": 1,
            "description": "Correct no-HSR conclusion and regulatory approval list.",
            "passed": hsr_passed,
        }
    )

    employment_keys = [
        "founder_employment_agreements_required",
        "employment_agreement_term_months",
        "non_compete_duration_months",
        "non_compete_scope",
        "broad_affiliate_covenant_allowed",
    ]
    employment_passed = subset_object(prediction, ["closing_flags"], expected, employment_keys) == subset_object(
        expected, ["closing_flags"], expected, employment_keys
    ) and normalize_simple_list(prediction, ["closing_flags", "employment_employees"]) == normalize_simple_list(
        expected, ["closing_flags", "employment_employees"]
    )
    points.append(
        {
            "id": "SP7_EMPLOYMENT_NONCOMPETE",
            "weight": 2,
            "description": "Correct founder employment and non-compete terms.",
            "passed": employment_passed,
        }
    )

    return points


def main():
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else EXPECTED_PATH
    try:
        prediction = load_json(prediction_path)
        expected = load_json(EXPECTED_PATH)
        points = build_points(prediction, expected)
        total_weight = sum(point["weight"] for point in points)
        earned_weight = sum(point["weight"] for point in points if point["passed"])
        result = {
            "score": round(earned_weight / total_weight, 10),
            "earned_weight": earned_weight,
            "total_weight": total_weight,
            "points": [
                {
                    "id": point["id"],
                    "weight": point["weight"],
                    "passed": point["passed"],
                    "description": point["description"],
                }
                for point in points
            ],
        }
    except Exception as exc:
        result = {
            "score": 0.0,
            "earned_weight": 0,
            "total_weight": 15,
            "points": [],
            "error": f"{type(exc).__name__}: {exc}",
        }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
