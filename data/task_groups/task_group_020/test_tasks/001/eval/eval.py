#!/usr/bin/env python3
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
EXPECTED_PATH = SCRIPT_DIR.parent / "output" / "answer.json"
MISSING = object()


POINTS = [
    {
        "id": "SP1_SOURCE_PRECEDENCE_CONTROLLED_SOURCES",
        "weight": 3,
        "description": "Correct controlling source decisions, rejected stale/template sources, active clause IDs, and superseded source IDs.",
        "checks": [
            ("source_precedence",),
        ],
    },
    {
        "id": "SP2_DRAFTING_POSTURE_ENUMS",
        "weight": 1,
        "description": "Correct controlled drafting posture fields transferred from buyer-side term population and policy-check work.",
        "checks": [
            ("drafting_positions",),
        ],
    },
    {
        "id": "SP3_POLICY_CHECKS_CURRENT_STATUS",
        "weight": 3,
        "description": "Correct policy rule IDs, approval categories, current status, approval summary, and conditional trigger set.",
        "checks": [
            ("policy_checks", "policy_id"),
            ("policy_checks", "policy_version"),
            ("policy_checks", "checks"),
            ("policy_checks", "policy_summary"),
        ],
    },
    {
        "id": "SP4_CONDITIONAL_ESCALATION_RISK_POSTURE",
        "weight": 1,
        "description": "Correct risk posture, non-triggered thresholds, conditional escalation details, and risk-memo override source IDs.",
        "checks": [
            ("closing_flags", "risk_posture_flags"),
            ("policy_checks", "risk_memo_overrides"),
        ],
    },
    {
        "id": "SP5_CONSENT_HSR_SOURCE_SELECTION",
        "weight": 1,
        "description": "Correct material consent, post-closing notice, HSR, regulatory approval, and source-document treatment.",
        "checks": [
            ("closing_flags", "required_material_consents"),
            ("closing_flags", "post_closing_notice_items"),
            ("closing_flags", "consent_condition_status"),
            ("closing_flags", "hsr_required"),
            ("closing_flags", "hsr_condition"),
            ("closing_flags", "hsr_basis_code"),
            ("closing_flags", "hsr_source_doc_id"),
            ("closing_flags", "other_regulatory_approvals"),
        ],
    },
    {
        "id": "SP6_EMPLOYMENT_NONCOMPETE_SOURCE_SELECTION",
        "weight": 1,
        "description": "Correct employment, non-compete, transition-service, IP-confirmation, and supporting source-document fields.",
        "checks": [
            ("closing_flags", "founder_employment_agreements_required"),
            ("closing_flags", "employment_agreement_term_months"),
            ("closing_flags", "employment_employees"),
            ("closing_flags", "employment_source_doc_id"),
            ("closing_flags", "non_compete_duration_months"),
            ("closing_flags", "non_compete_scope"),
            ("closing_flags", "broad_affiliate_covenant_allowed"),
            ("closing_flags", "transition_services_required"),
            ("closing_flags", "ip_assignment_confirmation_required"),
        ],
    },
    {
        "id": "SP7_ACTIVE_CAP_TABLE_ALLOCATION_MATH",
        "weight": 1,
        "description": "Correct Lumen deal economics, controlling active cap table, per-share availability, and seller allocation set.",
        "checks": [
            ("deal_terms", "deal_id"),
            ("deal_terms", "structure"),
            ("deal_terms", "target"),
            ("deal_terms", "buyer"),
            ("deal_terms", "seller_group"),
            ("deal_terms", "signing_date"),
            ("deal_terms", "outside_closing_date"),
            ("deal_terms", "headline_purchase_price_usd"),
            ("deal_terms", "equity_value_usd"),
            ("deal_terms", "cash_at_close_usd"),
            ("deal_terms", "rollover_equity_usd"),
            ("deal_terms", "seller_note_usd"),
            ("deal_terms", "earnout_usd"),
            ("deal_terms", "active_cap_table_source_doc_id"),
            ("deal_terms", "active_cap_table_as_of"),
            ("deal_terms", "per_share_price_usd"),
            ("deal_terms", "per_share_price_basis"),
            ("deal_terms", "price_per_as_converted_percent_point_usd"),
            ("seller_allocations",),
        ],
    },
    {
        "id": "SP8_ESCROW_NWC_VALUE_POLICY_MATH",
        "weight": 1,
        "description": "Correct escrow, cap, basket, de minimis, and working-capital mechanics with controlled policy status.",
        "checks": [
            ("deal_terms", "general_escrow_percent"),
            ("deal_terms", "general_escrow_usd"),
            ("deal_terms", "general_escrow_policy_status"),
            ("deal_terms", "tax_escrow_percent"),
            ("deal_terms", "tax_escrow_usd"),
            ("deal_terms", "tax_escrow_policy_status"),
            ("deal_terms", "indemnity_cap_percent"),
            ("deal_terms", "indemnity_cap_usd"),
            ("deal_terms", "basket_percent"),
            ("deal_terms", "basket_usd"),
            ("deal_terms", "basket_type"),
            ("deal_terms", "de_minimis_usd"),
            ("deal_terms", "nwc_target_usd"),
            ("deal_terms", "nwc_collar_usd"),
            ("deal_terms", "nwc_adjustment_mechanic"),
            ("deal_terms", "nwc_collar_percent_of_equity_value"),
        ],
    },
]


SORT_KEYS = {
    "checks": "check_id",
    "conditional_escalation_details": "trigger_code",
    "decisions": "decision_id",
    "required_material_consents": "contract_name",
    "seller_allocations": "seller_name",
}


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_path(obj, path):
    cur = obj
    for part in path:
        if not isinstance(cur, dict) or part not in cur:
            return MISSING
        cur = cur[part]
    return cur


def normalize(value, context_key=None):
    if value is MISSING:
        return {"__missing__": True}
    if isinstance(value, dict):
        return {key: normalize(value[key], key) for key in sorted(value)}
    if isinstance(value, list):
        items = [normalize(item) for item in value]
        sort_key = SORT_KEYS.get(context_key)
        if sort_key and all(isinstance(item, dict) and sort_key in item for item in items):
            return sorted(items, key=lambda item: item[sort_key])
        return sorted(items, key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, float):
        return round(value, 2)
    return value


def display_value(value):
    if value is MISSING:
        return "__MISSING__"
    return value


def score_prediction(prediction, expected):
    total_weight = sum(point["weight"] for point in POINTS)
    earned_weight = 0
    point_results = []

    for point in POINTS:
        mismatches = []
        for path in point["checks"]:
            expected_value = get_path(expected, path)
            actual_value = get_path(prediction, path)
            if normalize(actual_value, path[-1]) != normalize(expected_value, path[-1]):
                mismatches.append(
                    {
                        "path": ".".join(path),
                        "expected": display_value(expected_value),
                        "actual": display_value(actual_value),
                    }
                )
        passed = not mismatches
        if passed:
            earned_weight += point["weight"]
        point_results.append(
            {
                "id": point["id"],
                "weight": point["weight"],
                "passed": passed,
                "description": point["description"],
                "mismatches": mismatches,
            }
        )

    return {
        "score": round(earned_weight / total_weight, 10),
        "earned_weight": earned_weight,
        "total_weight": total_weight,
        "points": point_results,
    }


def main():
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else EXPECTED_PATH
    total_weight = sum(point["weight"] for point in POINTS)
    try:
        prediction = load_json(prediction_path)
        expected = load_json(EXPECTED_PATH)
        result = score_prediction(prediction, expected)
    except Exception as exc:
        result = {
            "score": 0.0,
            "earned_weight": 0,
            "total_weight": total_weight,
            "points": [],
            "error": f"{type(exc).__name__}: {exc}",
        }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
