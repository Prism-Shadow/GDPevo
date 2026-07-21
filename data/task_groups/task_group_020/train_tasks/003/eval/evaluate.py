#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


EXPECTED_TERMS = {
    "reverse_termination_fee": "TERM_PRJ_LYRA_01",
    "fiduciary_out": "TERM_PRJ_LYRA_02",
    "rw_survival": "TERM_PRJ_LYRA_03",
    "mae_carveouts": "TERM_PRJ_LYRA_04",
}

POINTS = [
    ("out_of_policy_term_set", 3),
    ("rtf_threshold_delta_benchmark", 3),
    ("fiduciary_out_deviation_mitigation", 2),
    ("survival_exposure", 2),
    ("mae_restricted_carveouts", 2),
    ("recommendations_per_term", 2),
    ("aggregate_exposure_summary", 2),
    ("memo_routing_dates", 1),
]


def load_answer(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:
        return None, str(exc)


def norm_text(value):
    return str(value).strip().lower()


def norm_set(values):
    if not isinstance(values, list):
        return set()
    return {norm_text(v) for v in values}


def number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if math.isfinite(float(value)):
            return float(value)
    if isinstance(value, str):
        try:
            parsed = float(value.strip())
        except ValueError:
            return None
        if math.isfinite(parsed):
            return parsed
    return None


def eq_num(value, expected, places=2):
    parsed = number(value)
    if parsed is None:
        return False
    return round(parsed, places) == round(float(expected), places)


def eq_int(value, expected):
    parsed = number(value)
    if parsed is None:
        return False
    return int(round(parsed)) == int(expected)


def get_path(obj, path):
    cur = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def terms_by_category(answer):
    terms = answer.get("escalation_terms")
    if not isinstance(terms, list):
        return {}
    result = {}
    for term in terms:
        if not isinstance(term, dict):
            continue
        category = norm_text(term.get("category"))
        if category:
            result[category] = term
    return result


def check_term_set(answer):
    terms = terms_by_category(answer)
    categories = set(terms)
    ids = {norm_text(term.get("term_id")) for term in terms.values()}
    expected_ids = {v.lower() for v in EXPECTED_TERMS.values()}
    no_distractor = "termination_fee" not in categories and "term_prj_lyra_05" not in ids
    statuses_ok = all(norm_text(terms[c].get("issue_status")) == "out_of_policy" for c in EXPECTED_TERMS if c in terms)
    ok = categories == set(EXPECTED_TERMS) and ids == expected_ids and no_distractor and statuses_ok
    return ok, {
        "categories": sorted(categories),
        "term_ids": sorted(ids),
        "expected_categories": sorted(EXPECTED_TERMS),
        "expected_term_ids": sorted(expected_ids),
        "no_distractor": no_distractor,
        "statuses_ok": statuses_ok,
    }


def check_rtf(answer):
    term = terms_by_category(answer).get("reverse_termination_fee", {})
    checks = {
        "term_id": norm_text(term.get("term_id")) == "term_prj_lyra_01",
        "draft_percent": eq_num(get_path(term, ["draft_metric", "value"]), 5.5),
        "draft_amount": eq_int(get_path(term, ["draft_metric", "amount"]), 61600000),
        "threshold_percent": eq_num(get_path(term, ["policy_metric", "threshold_value"]), 4.0),
        "threshold_amount": eq_int(get_path(term, ["policy_metric", "threshold_amount"]), 44800000),
        "delta_percent": eq_num(get_path(term, ["delta", "percent_points"]), 1.5),
        "delta_amount": eq_int(get_path(term, ["delta", "amount"]), 16800000),
        "benchmark_sample": eq_int(get_path(term, ["benchmark", "sample_size"]), 42),
        "benchmark_median": eq_num(get_path(term, ["benchmark", "median"]), 3.2),
        "benchmark_upper_quartile": eq_num(get_path(term, ["benchmark", "upper_quartile"]), 4.1),
        "benchmark_position": norm_text(get_path(term, ["benchmark", "position"])) == "above_upper_quartile",
    }
    return all(checks.values()), checks


def check_fiduciary(answer):
    term = terms_by_category(answer).get("fiduciary_out", {})
    required_conditions = norm_set(term.get("required_conditions"))
    required_triggers = norm_set(get_path(term, ["policy_metric", "required_triggers"]))
    removed_triggers = norm_set(get_path(term, ["delta", "removed_triggers"]))
    checks = {
        "term_id": norm_text(term.get("term_id")) == "term_prj_lyra_02",
        "missing_intervening_event": get_path(term, ["draft_metric", "missing_intervening_event_trigger"]) is True,
        "match_right": eq_int(get_path(term, ["draft_metric", "match_right_business_days"]), 5),
        "required_triggers": required_triggers == {"superior_proposal", "intervening_event"},
        "removed_trigger": removed_triggers == {"intervening_event"},
        "mitigation_conditions": {
            "restore_intervening_event_trigger",
            "keep_5_business_day_match_right",
            "preserve_board_fiduciary_compliance",
        }.issubset(required_conditions),
    }
    return all(checks.values()), checks


def check_survival(answer):
    term = terms_by_category(answer).get("rw_survival", {})
    conditions = norm_set(term.get("required_conditions"))
    checks = {
        "term_id": norm_text(term.get("term_id")) == "term_prj_lyra_03",
        "fundamental_months": eq_int(get_path(term, ["draft_metric", "fundamental_months"]), 24),
        "general_months": eq_int(get_path(term, ["draft_metric", "general_months"]), 18),
        "threshold_months": eq_int(get_path(term, ["policy_metric", "threshold_value"]), 15),
        "fundamental_delta": eq_int(get_path(term, ["delta", "fundamental_months"]), 9),
        "general_delta": eq_int(get_path(term, ["delta", "general_months"]), 3),
        "benchmark_sample": eq_int(get_path(term, ["benchmark", "sample_size"]), 39),
        "benchmark_median": eq_num(get_path(term, ["benchmark", "median"]), 15),
        "benchmark_upper_quartile": eq_num(get_path(term, ["benchmark", "upper_quartile"]), 18),
        "exposure_type": norm_text(get_path(term, ["exposure", "type"])) == "indemnity_leakage",
        "exposure_low": eq_int(get_path(term, ["exposure", "low"]), 8960000),
        "exposure_high": eq_int(get_path(term, ["exposure", "high"]), 31360000),
        "condition": "reduce_all_rep_survival_to_15_months" in conditions,
    }
    return all(checks.values()), checks


def check_mae(answer):
    term = terms_by_category(answer).get("mae_carveouts", {})
    restricted = norm_set(get_path(term, ["draft_metric", "restricted_carveouts"]))
    approved_groups = norm_set(get_path(term, ["policy_metric", "approved_carveout_groups"]))
    conditions = norm_set(term.get("required_conditions"))
    checks = {
        "term_id": norm_text(term.get("term_id")) == "term_prj_lyra_04",
        "added_count": eq_int(get_path(term, ["draft_metric", "added_count"]), 3),
        "threshold_count": eq_int(get_path(term, ["policy_metric", "threshold_value"]), 2),
        "excess_count": eq_int(get_path(term, ["delta", "excess_count"]), 1),
        "restricted_carveouts": restricted
        == {
            "law_or_gaap_changes",
            "pandemic_public_health_emergency",
            "industry_wide_biotech_changes",
        },
        "approved_groups": approved_groups
        == {
            "general_economic_or_financial_market_conditions",
            "natural_disasters_or_acts_of_terrorism",
        },
        "conditions": {
            "add_disproportionate_effects_exception",
            "remove_or_narrow_law_or_gaap_carveout",
            "remove_or_narrow_pandemic_public_health_carveout",
        }.issubset(conditions),
    }
    return all(checks.values()), checks


def check_recommendations(answer):
    terms = terms_by_category(answer)
    expected = {
        "reverse_termination_fee": "approve_with_conditions",
        "fiduciary_out": "reject",
        "rw_survival": "approve_with_conditions",
        "mae_carveouts": "approve_with_conditions",
    }
    found = {category: norm_text(terms.get(category, {}).get("recommendation")) for category in expected}
    return found == expected, {"found": found, "expected": expected}


def check_aggregate(answer):
    summary = answer.get("aggregate_summary", {})
    risk_counts = summary.get("risk_counts", {}) if isinstance(summary, dict) else {}
    checks = {
        "escalated_count": eq_int(summary.get("escalated_term_count"), 4),
        "excluded_term": norm_set(summary.get("excluded_in_policy_terms")) == {"term_prj_lyra_05"},
        "excluded_category": norm_set(summary.get("excluded_in_policy_categories")) == {"termination_fee"},
        "risk_counts": (
            isinstance(risk_counts, dict)
            and eq_int(risk_counts.get("HIGH"), 3)
            and eq_int(risk_counts.get("MEDIUM"), 1)
            and eq_int(risk_counts.get("LOW"), 0)
        ),
        "exposure_low": eq_int(summary.get("aggregate_quantified_exposure_low"), 25760000),
        "exposure_high": eq_int(summary.get("aggregate_quantified_exposure_high"), 81760000),
        "components_included": norm_set(summary.get("included_exposure_components"))
        == {"closing_certainty", "indemnity_leakage"},
        "components_excluded": "transition_disruption" in norm_set(summary.get("excluded_exposure_components")),
        "rtf_excess_amount": eq_int(summary.get("rtf_excess_amount"), 16800000),
        "overall_recommendation": norm_text(summary.get("overall_recommendation")) == "approve_with_conditions",
        "priority": [norm_text(x) for x in summary.get("negotiation_priority", [])]
        == [
            "fiduciary_out",
            "reverse_termination_fee",
            "mae_carveouts",
            "rw_survival",
        ],
    }
    return all(checks.values()), checks


def check_routing(answer):
    memo = answer.get("memo", {})
    checks = {
        "task_id": norm_text(answer.get("task_id")) == "train_003",
        "deal_id": norm_text(answer.get("deal_id")) == "prj_lyra",
        "prepared_for": norm_text(memo.get("prepared_for")) == "m&a committee",
        "client": memo.get("client_name") == "Verdantis Therapeutics plc",
        "project": memo.get("project_name") == "Project Lyra",
        "target": memo.get("target_name") == "Lyra Oncology Platform",
        "counterparty": memo.get("counterparty_name") == "Calyx Biologics Inc.",
        "policy": memo.get("policy_id") == "POL_MA_2025_A",
        "signing_date": memo.get("signing_date") == "2025-07-02",
        "meeting_date": memo.get("meeting_date") == "2025-07-14",
        "currency": memo.get("currency") == "USD",
        "basis": norm_text(memo.get("value_basis")) == "equity value",
        "headline_value": eq_int(memo.get("headline_value"), 1120000000),
    }
    return all(checks.values()), checks


CHECKS = {
    "out_of_policy_term_set": check_term_set,
    "rtf_threshold_delta_benchmark": check_rtf,
    "fiduciary_out_deviation_mitigation": check_fiduciary,
    "survival_exposure": check_survival,
    "mae_restricted_carveouts": check_mae,
    "recommendations_per_term": check_recommendations,
    "aggregate_exposure_summary": check_aggregate,
    "memo_routing_dates": check_routing,
}


def main():
    answer_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("answer.json")
    answer, error = load_answer(answer_path)
    total_weight = sum(weight for _, weight in POINTS)
    results = []

    if answer is None:
        for name, weight in POINTS:
            assigned = weight / total_weight
            results.append(
                {
                    "name": name,
                    "weight": weight,
                    "assigned_score": assigned,
                    "passed": False,
                    "earned_score": 0.0,
                    "details": {"error": error},
                }
            )
    else:
        for name, weight in POINTS:
            assigned = weight / total_weight
            passed, details = CHECKS[name](answer)
            results.append(
                {
                    "name": name,
                    "weight": weight,
                    "assigned_score": assigned,
                    "passed": bool(passed),
                    "earned_score": assigned if passed else 0.0,
                    "details": details,
                }
            )

    score = sum(point["earned_score"] for point in results)
    print(
        json.dumps(
            {
                "score": round(score, 10),
                "max_score": 1.0,
                "total_raw_weight": total_weight,
                "points": results,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
