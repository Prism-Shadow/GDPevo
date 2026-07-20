#!/usr/bin/env python3
import json
import sys
from pathlib import Path


WEIGHTS = {
    "issue_set_and_statuses": 2,
    "indemnity_cap_and_basket": 3,
    "survival_knowledge_and_escrow": 2,
    "materiality_scrape_position": 1,
    "consent_and_hsr_blockers": 2,
    "material_contract_blockers": 2,
    "final_positions_and_priority": 2,
    "risk_totals": 2,
}

GOALS = {
    "issue_set_and_statuses": "Correct buyer SPA issue set and statuses.",
    "indemnity_cap_and_basket": "Correct indemnity cap and basket treatment.",
    "survival_knowledge_and_escrow": "Correct survival, knowledge, and escrow treatment.",
    "materiality_scrape_position": "Correct materiality scrape position.",
    "consent_and_hsr_blockers": "Correct consent and HSR blockers.",
    "material_contract_blockers": "Correct material-contract blockers.",
    "final_positions_and_priority": "Correct final positions and priority order.",
    "risk_totals": "Correct risk totals.",
}

EXPECTED_ISSUES = {
    "indemnity_cap_and_basket": {
        "status": "draft_below_playbook",
        "risk_rating": "HIGH",
        "recommended_action": "revise",
        "final_position": "raise_cap_to_at_least_fallback",
        "priority_rank": 4,
    },
    "survival_and_knowledge": {
        "status": "draft_below_playbook",
        "risk_rating": "MEDIUM",
        "recommended_action": "revise",
        "final_position": "seek_18_months_or_condition_15_on_escrow",
        "priority_rank": 5,
    },
    "materiality_scrape": {
        "status": "in_policy",
        "risk_rating": "MEDIUM",
        "recommended_action": "accept",
        "final_position": "accept_breach_only_fallback",
        "priority_rank": 7,
    },
    "escrow_holdback_release": {
        "status": "missing_required_term",
        "risk_rating": "MEDIUM",
        "recommended_action": "add",
        "final_position": "add_10_percent_escrow_with_unresolved_agent_and_release",
        "priority_rank": 6,
    },
    "consent_closing_condition": {
        "status": "draft_below_playbook",
        "risk_rating": "HIGH",
        "recommended_action": "revise",
        "final_position": "require_all_material_consents",
        "priority_rank": 1,
    },
    "hsr_condition": {
        "status": "missing_required_term",
        "risk_rating": "HIGH",
        "recommended_action": "add",
        "final_position": "add_hsr_clearance_condition",
        "priority_rank": 2,
    },
    "material_contracts": {
        "status": "missing_required_term",
        "risk_rating": "HIGH",
        "recommended_action": "add",
        "final_position": "require_specific_contract_consents",
        "priority_rank": 3,
    },
}


def load_candidate(path):
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def issue_map(answer):
    rows = answer.get("position_matrix")
    if not isinstance(rows, list):
        return {}, ["position_matrix is not a list"]
    seen = {}
    errors = []
    for row in rows:
        if not isinstance(row, dict):
            errors.append("position_matrix contains a non-object row")
            continue
        issue_id = row.get("issue_id")
        if not isinstance(issue_id, str):
            errors.append("position_matrix row missing string issue_id")
            continue
        if issue_id in seen:
            errors.append(f"duplicate issue_id {issue_id}")
        seen[issue_id] = row
    return seen, errors


def blocker_map(answer):
    rows = answer.get("closing_blockers")
    if not isinstance(rows, list):
        return {}, ["closing_blockers is not a list"]
    seen = {}
    errors = []
    for row in rows:
        if not isinstance(row, dict):
            errors.append("closing_blockers contains a non-object row")
            continue
        blocker_id = row.get("blocker_id")
        if not isinstance(blocker_id, str):
            errors.append("closing_blockers row missing string blocker_id")
            continue
        if blocker_id in seen:
            errors.append(f"duplicate blocker_id {blocker_id}")
        seen[blocker_id] = row
    return seen, errors


def eq(row, key, expected):
    return row.get(key) == expected


def num_eq(row, key, expected):
    value = row.get(key)
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return round(float(value), 4) == round(float(expected), 4)


def int_eq(row, key, expected):
    value = row.get(key)
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return int(round(float(value))) == expected


def set_eq(row, key, expected):
    value = row.get(key)
    if not isinstance(value, list):
        return False
    return sorted(value) == sorted(expected)


def all_issue_basics(matrix):
    checks = []
    checks.append(sorted(matrix.keys()) == sorted(EXPECTED_ISSUES.keys()))
    for issue_id, expected in EXPECTED_ISSUES.items():
        row = matrix.get(issue_id, {})
        checks.extend(row.get(k) == v for k, v in expected.items() if k != "priority_rank")
    return all(checks)


def check_indemnity(matrix):
    row = matrix.get("indemnity_cap_and_basket", {})
    return all(
        [
            set_eq(row, "source_term_ids", ["TERM_PRJ_ASTER_01"]),
            eq(row, "status", "draft_below_playbook"),
            eq(row, "risk_rating", "HIGH"),
            eq(row, "recommended_action", "revise"),
            eq(row, "final_position", "raise_cap_to_at_least_fallback"),
            num_eq(row, "draft_percent", 8.0),
            num_eq(row, "preferred_percent", 12.0),
            num_eq(row, "fallback_percent", 10.0),
            int_eq(row, "draft_amount_usd", 29200000),
            int_eq(row, "fallback_amount_usd", 36500000),
            int_eq(row, "preferred_amount_usd", 43800000),
            int_eq(row, "shortfall_to_fallback_usd", 7300000),
            int_eq(row, "shortfall_to_preferred_usd", 14600000),
            int_eq(row, "special_indemnity_amount_usd", 12000000),
            int_eq(row, "privacy_finding_amount_usd", 4380000),
            eq(row, "basket_status", "not_found_in_current_records"),
        ]
    )


def check_survival_knowledge_escrow(matrix):
    survival = matrix.get("survival_and_knowledge", {})
    escrow = matrix.get("escrow_holdback_release", {})
    return all(
        [
            set_eq(survival, "source_term_ids", ["TERM_PRJ_ASTER_02"]),
            eq(survival, "status", "draft_below_playbook"),
            eq(survival, "recommended_action", "revise"),
            eq(survival, "final_position", "seek_18_months_or_condition_15_on_escrow"),
            int_eq(survival, "draft_months", 15),
            int_eq(survival, "preferred_months", 18),
            int_eq(survival, "fallback_months", 15),
            eq(survival, "knowledge_qualifier_status", "not_found_in_current_records"),
            set_eq(escrow, "source_term_ids", []),
            eq(escrow, "status", "missing_required_term"),
            eq(escrow, "recommended_action", "add"),
            eq(escrow, "final_position", "add_10_percent_escrow_with_unresolved_agent_and_release"),
            num_eq(escrow, "fallback_percent", 10.0),
            int_eq(escrow, "fallback_amount_usd", 36500000),
            int_eq(escrow, "shortfall_to_fallback_usd", 36500000),
            eq(escrow, "escrow_agent_status", "not_found_in_current_records"),
            eq(escrow, "release_status", "not_found_in_current_records"),
        ]
    )


def check_materiality(matrix):
    row = matrix.get("materiality_scrape", {})
    return all(
        [
            set_eq(row, "source_term_ids", ["TERM_PRJ_ASTER_03"]),
            eq(row, "status", "in_policy"),
            eq(row, "risk_rating", "MEDIUM"),
            eq(row, "recommended_action", "accept"),
            eq(row, "final_position", "accept_breach_only_fallback"),
        ]
    )


def check_consent_hsr(matrix, blockers):
    consent = matrix.get("consent_closing_condition", {})
    hsr = matrix.get("hsr_condition", {})
    required_blockers = {
        "CNS_PRJ_ASTER_01": ("required_consent", "HIGH", 20075000, "obtain_consent"),
        "CNS_PRJ_ASTER_03": ("required_consent", "LOW", 850000, "obtain_consent"),
        "REG_PRJ_ASTER_HSR": ("regulatory_clearance", "HIGH", None, "obtain_clearance"),
    }
    blocker_checks = []
    for blocker_id, (blocker_type, risk, amount, action) in required_blockers.items():
        row = blockers.get(blocker_id, {})
        blocker_checks.append(eq(row, "blocker_type", blocker_type))
        blocker_checks.append(eq(row, "risk_rating", risk))
        blocker_checks.append(eq(row, "must_be_satisfied_before_closing", True))
        blocker_checks.append(eq(row, "required_action", action))
        if amount is None:
            blocker_checks.append(row.get("amount_at_risk_usd") is None)
        else:
            blocker_checks.append(int_eq(row, "amount_at_risk_usd", amount))
    return all(
        [
            set_eq(consent, "source_term_ids", ["TERM_PRJ_ASTER_04"]),
            eq(consent, "status", "draft_below_playbook"),
            eq(consent, "risk_rating", "HIGH"),
            eq(consent, "recommended_action", "revise"),
            eq(consent, "final_position", "require_all_material_consents"),
            int_eq(consent, "draft_contract_count", 10),
            set_eq(consent, "required_consent_ids", ["CNS_PRJ_ASTER_01", "CNS_PRJ_ASTER_03"]),
            set_eq(consent, "excluded_from_draft", ["payer_gateway_agreements"]),
            eq(hsr, "status", "missing_required_term"),
            eq(hsr, "hsr_required", True),
            eq(hsr, "hell_or_high_water_required", False),
            eq(hsr, "final_position", "add_hsr_clearance_condition"),
            all(blocker_checks),
        ]
    )


def check_material_contracts(matrix, blockers, totals):
    row = matrix.get("material_contracts", {})
    expected_contracts = ["MAT_PRJ_ASTER_01", "MAT_PRJ_ASTER_03"]
    blocker_checks = []
    for blocker_id, revenue in {
        "MAT_PRJ_ASTER_01": 31025000,
        "MAT_PRJ_ASTER_03": 9490000,
    }.items():
        b = blockers.get(blocker_id, {})
        blocker_checks.extend(
            [
                eq(b, "blocker_type", "material_contract_consent"),
                eq(b, "related_contract_id", blocker_id),
                eq(b, "must_be_satisfied_before_closing", True),
                eq(b, "risk_rating", "HIGH"),
                int_eq(b, "annual_revenue_usd", revenue),
                eq(b, "required_action", "add_closing_condition"),
            ]
        )
    return all(
        [
            eq(row, "status", "missing_required_term"),
            eq(row, "risk_rating", "HIGH"),
            eq(row, "recommended_action", "add"),
            eq(row, "final_position", "require_specific_contract_consents"),
            set_eq(row, "required_contract_ids", expected_contracts),
            set_eq(row, "excluded_contract_ids", ["MAT_PRJ_ASTER_02"]),
            int_eq(totals, "material_contract_revenue_requiring_consent_usd", 40515000),
            all(blocker_checks),
        ]
    )


def check_priority(matrix):
    return all(
        int_eq(matrix.get(issue_id, {}), "priority_rank", expected["priority_rank"])
        and eq(matrix.get(issue_id, {}), "final_position", expected["final_position"])
        for issue_id, expected in EXPECTED_ISSUES.items()
    )


def check_risk_totals(answer):
    totals = answer.get("risk_totals", {})
    if not isinstance(totals, dict):
        return False
    expected_ints = {
        "headline_purchase_price_usd": 365000000,
        "position_issue_count": 7,
        "out_of_policy_issue_count": 6,
        "draft_below_playbook_count": 3,
        "missing_required_term_count": 3,
        "high_risk_issue_count": 4,
        "closing_blocker_count": 5,
        "required_consent_amount_at_risk_usd": 20925000,
        "material_contract_revenue_requiring_consent_usd": 40515000,
        "indemnity_cap_shortfall_to_fallback_usd": 7300000,
        "indemnity_cap_shortfall_to_preferred_usd": 14600000,
        "total_modeled_exposure_low_usd": 9855000,
        "total_modeled_exposure_high_usd": 33214999,
    }
    return all(int_eq(totals, key, value) for key, value in expected_ints.items()) and eq(
        totals, "highest_modeled_exposure_category", "closing_certainty"
    )


def evaluate(answer):
    matrix, matrix_errors = issue_map(answer)
    blockers, blocker_errors = blocker_map(answer)
    totals = answer.get("risk_totals", {}) if isinstance(answer.get("risk_totals"), dict) else {}

    checks = {
        "issue_set_and_statuses": answer.get("deal_id") == "PRJ_ASTER"
        and not matrix_errors
        and all_issue_basics(matrix),
        "indemnity_cap_and_basket": check_indemnity(matrix),
        "survival_knowledge_and_escrow": check_survival_knowledge_escrow(matrix),
        "materiality_scrape_position": check_materiality(matrix),
        "consent_and_hsr_blockers": not blocker_errors and check_consent_hsr(matrix, blockers),
        "material_contract_blockers": not blocker_errors and check_material_contracts(matrix, blockers, totals),
        "final_positions_and_priority": check_priority(matrix),
        "risk_totals": check_risk_totals(answer),
    }

    max_score = sum(WEIGHTS.values())
    points = []
    raw_earned = 0
    for name, weight in WEIGHTS.items():
        passed = bool(checks[name])
        assigned = weight / max_score
        if passed:
            raw_earned += weight
        points.append(
            {
                "id": name,
                "name": name,
                "goal": GOALS[name],
                "weight": weight,
                "assigned_score": assigned,
                "passed": passed,
                "earned_score": assigned if passed else 0,
                "raw_earned": weight if passed else 0,
            }
        )

    return {
        "score": raw_earned / max_score,
        "points": points,
        "max_score": max_score,
        "raw_score": raw_earned,
        "diagnostics": {
            "matrix_errors": matrix_errors,
            "blocker_errors": blocker_errors,
        },
    }


def main():
    if len(sys.argv) > 2:
        raise SystemExit("usage: evaluate.py [candidate_answer.json]")
    path = sys.argv[1] if len(sys.argv) == 2 else "answer.json"
    try:
        answer = load_candidate(path)
        result = evaluate(answer)
    except Exception as exc:
        result = {
            "score": 0.0,
            "points": [
                {
                    "id": name,
                    "name": name,
                    "goal": GOALS[name],
                    "weight": weight,
                    "assigned_score": weight / sum(WEIGHTS.values()),
                    "passed": False,
                    "earned_score": 0,
                    "raw_earned": 0,
                }
                for name, weight in WEIGHTS.items()
            ],
            "max_score": sum(WEIGHTS.values()),
            "raw_score": 0,
            "error": str(exc),
        }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
