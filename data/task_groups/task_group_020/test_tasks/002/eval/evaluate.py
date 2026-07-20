#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


WEIGHTS = {
    "out_of_policy_term_set": 2,
    "rtf_math_and_benchmark": 3,
    "fiduciary_out_mitigation": 2,
    "survival_exposure": 2,
    "mae_carveout_classification": 2,
    "term_recommendations": 2,
    "aggregate_exposure_and_context": 2,
    "routing_and_dates": 1,
}

EXPECTED_CATEGORIES = [
    "fiduciary_out",
    "mae_carveouts",
    "reverse_termination_fee",
    "rw_survival",
]

EXPECTED_TERM_IDS = {
    "reverse_termination_fee": "TERM_PRJ_VEGA_01",
    "fiduciary_out": "TERM_PRJ_VEGA_02",
    "rw_survival": "TERM_PRJ_VEGA_03",
    "mae_carveouts": "TERM_PRJ_VEGA_04",
}


def load_answer(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def as_list(value):
    return value if isinstance(value, list) else []


def norm_str(value):
    return value.strip() if isinstance(value, str) else value


def sorted_strings(value):
    return sorted(norm_str(v) for v in as_list(value))


def string_set(value):
    return {norm_str(v) for v in as_list(value) if isinstance(norm_str(v), str)}


def num_eq(actual, expected, places=None):
    if actual is None:
        return False
    try:
        actual_num = float(actual)
    except (TypeError, ValueError):
        return False
    if places is not None:
        return round(actual_num, places) == round(float(expected), places)
    return math.isclose(actual_num, float(expected), rel_tol=0, abs_tol=1e-9)


def int_eq(actual, expected):
    if isinstance(actual, bool):
        return False
    try:
        return int(actual) == int(expected) and float(actual) == float(int(actual))
    except (TypeError, ValueError):
        return False


def bool_eq(actual, expected):
    return isinstance(actual, bool) and actual is expected


def terms_by_category(answer):
    result = {}
    for term in as_list(answer.get("escalation_terms")):
        if isinstance(term, dict):
            category = term.get("category")
            if isinstance(category, str) and category not in result:
                result[category] = term
    return result


def list_of_dicts_by_key(items, key):
    result = {}
    for item in as_list(items):
        if isinstance(item, dict) and isinstance(item.get(key), str):
            result[item[key]] = item
    return result


def exposure_components_by_kind(items):
    result = {}
    for item in as_list(items):
        if not isinstance(item, dict):
            continue
        label = str(item.get("component", "")).lower().replace("_", " ")
        if "closing" in label and "certainty" in label:
            result.setdefault("closing_certainty_high", item)
        elif ("rtf" in label or "reverse termination" in label) and ("excess" in label or "policy" in label):
            result.setdefault("rtf_policy_excess", item)
        elif ("survival" in label or "indemnity" in label) and ("leakage" in label or "survival" in label):
            result.setdefault("survival_indemnity_leakage_high", item)
    return result


def has_all(values, expected):
    return set(expected).issubset(string_set(values))


def priority_order(terms):
    ranked = []
    for category, term in terms.items():
        rank = term.get("priority_rank")
        if int_eq(rank, rank):
            ranked.append((int(rank), category))
    return [category for _rank, category in sorted(ranked)]


def fiduciary_resolution_ok(term):
    expected_conditions = [
        "restore_full_board_change_process",
        "restore_intervening_event_trigger",
        "restore_required_match_right",
    ]
    if term.get("recommendation") == "reject":
        return True
    return (
        term.get("recommendation") == "approve_with_conditions"
        and term.get("risk_rating") == "HIGH"
        and has_all(term.get("condition_codes"), expected_conditions)
    )


def check_out_of_policy_term_set(answer, terms):
    categories = sorted(terms.keys())
    summary = answer.get("aggregate_summary", {}) if isinstance(answer.get("aggregate_summary"), dict) else {}
    summary_categories = sorted_strings(summary.get("out_of_policy_categories"))
    ids_ok = all(terms.get(cat, {}).get("term_id") == term_id for cat, term_id in EXPECTED_TERM_IDS.items())
    statuses_ok = all(
        terms.get(cat, {}).get("policy_status") in {"out_of_policy", "restricted_escalation"}
        for cat in EXPECTED_CATEGORIES
    )
    no_distractors = "termination_fee" not in categories and "voting_agreements" not in categories
    strict_summary_ok = summary_categories == EXPECTED_CATEGORIES
    strict_out_of_policy = sorted(
        cat for cat in EXPECTED_CATEGORIES if terms.get(cat, {}).get("policy_status") == "out_of_policy"
    )
    status_summary_ok = (
        summary_categories == strict_out_of_policy
        and terms.get("fiduciary_out", {}).get("policy_status") == "restricted_escalation"
    )
    passed = (
        categories == EXPECTED_CATEGORIES
        and (strict_summary_ok or status_summary_ok)
        and ids_ok
        and statuses_ok
        and no_distractors
    )
    return passed, {
        "categories": categories,
        "summary_categories": summary_categories,
        "ids_ok": ids_ok,
        "statuses_ok": statuses_ok,
        "no_distractors": no_distractors,
        "summary_ok": strict_summary_ok or status_summary_ok,
    }


def check_rtf_math_and_benchmark(_answer, terms):
    term = terms.get("reverse_termination_fee", {})
    analysis = term.get("rtf_analysis", {}) if isinstance(term.get("rtf_analysis"), dict) else {}
    checks = {
        "draft_percent_points": num_eq(analysis.get("draft_percent_points"), 4.8, 2),
        "policy_threshold_percent_points": num_eq(analysis.get("policy_threshold_percent_points"), 4.0, 2),
        "deviation_percent_points": num_eq(analysis.get("deviation_percent_points"), 0.8, 2),
        "equity_value_usd": int_eq(analysis.get("equity_value_usd"), 980000000),
        "draft_amount_usd": int_eq(analysis.get("draft_amount_usd"), 47040000),
        "policy_max_amount_usd": int_eq(analysis.get("policy_max_amount_usd"), 39200000),
        "policy_excess_amount_usd": int_eq(analysis.get("policy_excess_amount_usd"), 7840000),
        "benchmark_median_percent_points": num_eq(analysis.get("benchmark_median_percent_points"), 3.2, 2),
        "benchmark_upper_quartile_percent_points": num_eq(
            analysis.get("benchmark_upper_quartile_percent_points"), 4.1, 2
        ),
        "draft_vs_upper_quartile_percent_points": num_eq(
            analysis.get("draft_vs_upper_quartile_percent_points"), 0.7, 2
        ),
    }
    return all(checks.values()), checks


def check_fiduciary_out_mitigation(_answer, terms):
    term = terms.get("fiduciary_out", {})
    analysis = term.get("fiduciary_out_analysis", {}) if isinstance(term.get("fiduciary_out_analysis"), dict) else {}
    expected_changes = [
        "board_change_process_limited_to_superior_proposal",
        "intervening_event_trigger_removed",
    ]
    expected_conditions = [
        "restore_full_board_change_process",
        "restore_intervening_event_trigger",
        "restore_required_match_right",
    ]
    allowed_changes = expected_changes + ["match_right_shortened_or_missing"]
    change_codes = string_set(analysis.get("change_codes"))
    checks = {
        "risk_rating": term.get("risk_rating") == "HIGH",
        "change_codes": set(expected_changes).issubset(change_codes) and change_codes.issubset(set(allowed_changes)),
        "required_match_right_business_days": int_eq(analysis.get("required_match_right_business_days"), 5),
        "condition_codes": has_all(term.get("condition_codes"), expected_conditions),
    }
    return all(checks.values()), checks


def check_survival_exposure(_answer, terms):
    term = terms.get("rw_survival", {})
    analysis = term.get("survival_analysis", {}) if isinstance(term.get("survival_analysis"), dict) else {}
    checks = {
        "risk_rating": term.get("risk_rating") == "MEDIUM",
        "fundamental_survival_months": int_eq(analysis.get("fundamental_survival_months"), 21),
        "general_survival_months": int_eq(analysis.get("general_survival_months"), 17),
        "policy_threshold_months": int_eq(analysis.get("policy_threshold_months"), 15),
        "fundamental_deviation_months": int_eq(analysis.get("fundamental_deviation_months"), 6),
        "general_deviation_months": int_eq(analysis.get("general_deviation_months"), 2),
        "benchmark_median_months": num_eq(analysis.get("benchmark_median_months"), 15.0, 1),
        "benchmark_upper_quartile_months": num_eq(analysis.get("benchmark_upper_quartile_months"), 18.0, 1),
        "exposure_low_usd": int_eq(analysis.get("exposure_low_usd"), 7840000),
        "exposure_high_usd": int_eq(analysis.get("exposure_high_usd"), 27440000),
        "condition_codes": sorted_strings(term.get("condition_codes")) == ["reduce_all_rep_survival_to_policy"],
    }
    return all(checks.values()), checks


def check_mae_carveout_classification(_answer, terms):
    term = terms.get("mae_carveouts", {})
    analysis = term.get("mae_analysis", {}) if isinstance(term.get("mae_analysis"), dict) else {}
    carveouts = list_of_dicts_by_key(analysis.get("carveout_classifications"), "carveout_code")
    expected = {
        "clinical_trial_hold": ("target_specific_regulatory_risk", "delete"),
        "pandemic": ("restricted_general_event", "narrow_with_disproportionate_effect_carveback"),
        "sector_wide_regulatory_change": (
            "restricted_industry_event",
            "narrow_with_disproportionate_effect_carveback",
        ),
    }
    class_checks = {
        code: (
            carveouts.get(code, {}).get("classification") == cls
            and carveouts.get(code, {}).get("recommended_disposition") == disposition
        )
        for code, (cls, disposition) in expected.items()
    }
    checks = {
        "risk_rating": term.get("risk_rating") == "HIGH",
        "additional_carveout_count": int_eq(analysis.get("additional_carveout_count"), 3),
        "policy_threshold_count": int_eq(analysis.get("policy_threshold_count"), 2),
        "count_delta": int_eq(analysis.get("count_delta"), 1),
        "condition_codes": sorted_strings(term.get("condition_codes"))
        == [
            "add_disproportionate_effect_carveback",
            "delete_clinical_trial_hold_carveout",
        ],
        "carveout_codes": sorted(carveouts.keys()) == sorted(expected.keys()),
        "classifications": all(class_checks.values()),
    }
    checks.update({f"classification_{k}": v for k, v in class_checks.items()})
    return all(checks.values()), checks


def check_term_recommendations(_answer, terms):
    expected_recommendations = {
        "reverse_termination_fee": "approve_with_conditions",
        "rw_survival": "approve_with_conditions",
        "mae_carveouts": "approve_with_conditions",
    }
    expected_priority = {
        "fiduciary_out": 1,
        "reverse_termination_fee": 2,
        "mae_carveouts": 3,
        "rw_survival": 4,
    }
    recommendation_checks = {
        cat: terms.get(cat, {}).get("recommendation") == rec for cat, rec in expected_recommendations.items()
    }
    recommendation_checks["fiduciary_out"] = fiduciary_resolution_ok(terms.get("fiduciary_out", {}))
    priority_checks = {
        cat: int_eq(terms.get(cat, {}).get("priority_rank"), rank) for cat, rank in expected_priority.items()
    }
    ordered_categories = priority_order(terms)
    exact_priority_ok = all(priority_checks.values())
    flexible_priority_ok = set(ordered_categories[:4]) == set(EXPECTED_CATEGORIES) and (
        ordered_categories[:1] == ["fiduciary_out"]
        or set(ordered_categories[:2]) == {"fiduciary_out", "reverse_termination_fee"}
    )
    checks = {
        "recommendations": all(recommendation_checks.values()),
        "priority_ranks": exact_priority_ok or flexible_priority_ok,
        "approval_required_all_terms": all(
            terms.get(cat, {}).get("approval_required") == "M&A Committee" for cat in EXPECTED_CATEGORIES
        ),
    }
    passed = checks["recommendations"] and checks["priority_ranks"] and checks["approval_required_all_terms"]
    checks.update({f"recommendation_{k}": v for k, v in recommendation_checks.items()})
    checks.update({f"priority_{k}": v for k, v in priority_checks.items()})
    return passed, checks


def check_aggregate_exposure_and_context(answer, _terms):
    summary = answer.get("aggregate_summary", {}) if isinstance(answer.get("aggregate_summary"), dict) else {}
    components = exposure_components_by_kind(summary.get("exposure_components"))
    expected_components = {
        "closing_certainty_high": 44100000,
        "rtf_policy_excess": 7840000,
        "survival_indemnity_leakage_high": 27440000,
    }
    component_checks = {
        key: int_eq(components.get(key, {}).get("amount_usd"), value) for key, value in expected_components.items()
    }
    checks = {
        "escalation_count": int_eq(summary.get("escalation_count"), 4),
        "restricted_term_count": int_eq(summary.get("restricted_term_count"), 4),
        "approve_with_conditions_count": int_eq(summary.get("approve_with_conditions_count"), 3),
        "reject_count": int_eq(summary.get("reject_count"), 1),
        "legal_blocker_count": int_eq(summary.get("legal_blocker_count"), 1),
        "highest_priority_category": summary.get("highest_priority_category") == "fiduciary_out",
        "aggregate_quantified_exposure_usd": int_eq(summary.get("aggregate_quantified_exposure_usd"), 79380000),
        "exposure_component_keys": sorted(components.keys()) == sorted(expected_components.keys()),
        "exposure_component_amounts": all(component_checks.values()),
        "largest_support_holder_pct": num_eq(summary.get("largest_support_holder_pct"), 0.3410, 4),
        "voting_agreement_policy_threshold_pct": num_eq(summary.get("voting_agreement_policy_threshold_pct"), 0.35, 4),
        "voting_agreement_policy_breach": bool_eq(summary.get("voting_agreement_policy_breach"), False),
        "strategic_pressure_flag": bool_eq(summary.get("strategic_pressure_flag"), True),
        "strategic_pressure_reason_code": summary.get("strategic_pressure_reason_code") == "rival_bidder_active",
    }
    checks.update({f"component_{k}": v for k, v in component_checks.items()})
    return all(checks.values()), checks


def check_routing_and_dates(answer, _terms):
    routing = answer.get("routing", {}) if isinstance(answer.get("routing"), dict) else {}
    prepared_for = routing.get("prepared_for")
    checks = {
        "deal_id": answer.get("deal_id") == "PRJ_VEGA",
        "package_type": routing.get("package_type") == "committee_escalation",
        "prepared_for": isinstance(prepared_for, str) and "M&A Committee" in prepared_for,
        "approval_required": routing.get("approval_required") == "M&A Committee",
        "policy_id": routing.get("policy_id") == "POL_MA_2025_A",
        "project_name": routing.get("project_name") == "Project Vega",
        "client_name": routing.get("client_name") == "Verdantis Therapeutics plc",
        "counterparty_name": routing.get("counterparty_name") == "Vega BioSystems Inc.",
        "signing_date": routing.get("signing_date") == "2025-10-03",
        "meeting_date": routing.get("meeting_date") == "2025-10-16",
    }
    return all(checks.values()), checks


CHECKS = {
    "out_of_policy_term_set": check_out_of_policy_term_set,
    "rtf_math_and_benchmark": check_rtf_math_and_benchmark,
    "fiduciary_out_mitigation": check_fiduciary_out_mitigation,
    "survival_exposure": check_survival_exposure,
    "mae_carveout_classification": check_mae_carveout_classification,
    "term_recommendations": check_term_recommendations,
    "aggregate_exposure_and_context": check_aggregate_exposure_and_context,
    "routing_and_dates": check_routing_and_dates,
}


def evaluate(path):
    try:
        answer = load_answer(path)
    except Exception as exc:
        total = sum(WEIGHTS.values())
        points = [
            {
                "id": point_id,
                "weight": weight,
                "assigned_score": weight / total,
                "passed": False,
                "earned_score": 0,
                "details": {"error": f"could not load JSON: {exc}"},
            }
            for point_id, weight in WEIGHTS.items()
        ]
        return {"score": 0, "points": points, "max_score": 1}

    if not isinstance(answer, dict):
        answer = {}

    terms = terms_by_category(answer)
    total = sum(WEIGHTS.values())
    points = []
    score = 0.0

    for point_id, check in CHECKS.items():
        weight = WEIGHTS[point_id]
        assigned = weight / total
        try:
            passed, details = check(answer, terms)
        except Exception as exc:
            passed, details = False, {"error": str(exc)}
        earned = assigned if passed else 0
        score += earned
        points.append(
            {
                "id": point_id,
                "weight": weight,
                "assigned_score": assigned,
                "passed": passed,
                "earned_score": earned,
                "details": details,
            }
        )

    return {"score": score, "points": points, "max_score": 1}


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("answer.json")
    result = evaluate(path)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
