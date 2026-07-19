#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


EXPECTED_TERMS = {
    "reverse_termination_fee": "TERM_PRJ_ROOK_01",
    "voting_agreements": "TERM_PRJ_ROOK_03",
    "mae_carveouts": "TERM_PRJ_ROOK_04",
}

POINTS = [
    ("waiver_term_set", 3),
    ("threshold_delta_exposure_calculations", 3),
    ("recommendation_choices", 2),
    ("concession_ranking", 2),
    ("batna_deal_certainty_flags", 2),
    ("aggregate_risk_summary", 2),
    ("committee_conditions", 2),
    ("final_posture_and_routing", 1),
]


def load_answer(path):
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:
        return None, str(exc)


def norm_text(value):
    return str(value).strip().lower()


def norm_set(values):
    if not isinstance(values, list):
        return set()
    return {norm_text(v) for v in values}


def component_labels(values):
    if not isinstance(values, list):
        return []
    return [norm_text(value).replace("_", " ") for value in values]


def any_component(values, *required_fragments):
    labels = component_labels(values)
    return any(all(fragment in label for fragment in required_fragments) for label in labels)


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
    if isinstance(value, bool):
        return int(value) == int(expected)
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


def rows_by_category(answer):
    rows = answer.get("waiver_matrix")
    if not isinstance(rows, list):
        return {}
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        category = norm_text(row.get("category"))
        if category:
            result[category] = row
    return result


def excluded_noncommittee_ok(answer):
    rows = rows_by_category(answer)
    termination = rows.get("termination_fee")
    if termination is None:
        return True
    summary = answer.get("aggregate_summary", {})
    excluded_terms = norm_set(summary.get("excluded_noncommittee_terms")) if isinstance(summary, dict) else set()
    excluded_categories = (
        norm_set(summary.get("excluded_noncommittee_categories")) if isinstance(summary, dict) else set()
    )
    return (
        norm_text(termination.get("term_id")) == "term_prj_rook_02"
        and termination.get("waiver_required") is False
        and norm_text(termination.get("issue_status"))
        in {"noncommittee_item", "excluded_noncommittee", "not_committee_item"}
        and "term_prj_rook_02" in excluded_terms
        and "termination_fee" in excluded_categories
    )


def check_waiver_term_set(answer):
    rows = rows_by_category(answer)
    categories = set(rows)
    ids = {norm_text(row.get("term_id")) for row in rows.values()}
    expected_ids = {term_id.lower() for term_id in EXPECTED_TERMS.values()}
    statuses_ok = all(
        norm_text(rows.get(category, {}).get("issue_status")) in {"out_of_policy", "restricted"}
        for category in EXPECTED_TERMS
    )
    waivers_ok = all(rows.get(category, {}).get("waiver_required") is True for category in EXPECTED_TERMS)
    no_noncommittee = "termination_fee" not in categories and "term_prj_rook_02" not in ids
    noncommittee_ok = no_noncommittee or excluded_noncommittee_ok(answer)
    excluded_ok = norm_set(get_path(answer, ["aggregate_summary", "excluded_noncommittee_terms"])) == {
        "term_prj_rook_02"
    } and norm_set(get_path(answer, ["aggregate_summary", "excluded_noncommittee_categories"])) == {"termination_fee"}
    ok = (
        set(EXPECTED_TERMS).issubset(categories)
        and expected_ids.issubset(ids)
        and (ids - expected_ids).issubset({"term_prj_rook_02"})
        and statuses_ok
        and waivers_ok
        and noncommittee_ok
        and excluded_ok
    )
    return ok, {
        "categories": sorted(categories),
        "term_ids": sorted(ids),
        "expected_categories": sorted(EXPECTED_TERMS),
        "expected_term_ids": sorted(expected_ids),
        "statuses_ok": statuses_ok,
        "waivers_ok": waivers_ok,
        "no_noncommittee": no_noncommittee,
        "noncommittee_ok": noncommittee_ok,
        "excluded_ok": excluded_ok,
    }


def check_thresholds(answer):
    rows = rows_by_category(answer)
    rtf = rows.get("reverse_termination_fee", {})
    voting = rows.get("voting_agreements", {})
    mae = rows.get("mae_carveouts", {})
    rtf_checks = {
        "draft_percent": eq_num(get_path(rtf, ["draft_metric", "value"]), 4.2),
        "draft_amount": eq_int(get_path(rtf, ["draft_metric", "amount_usd"]), 31920000),
        "threshold_percent": eq_num(get_path(rtf, ["policy_metric", "threshold_value"]), 4.0),
        "threshold_amount": eq_int(get_path(rtf, ["policy_metric", "threshold_amount_usd"]), 30400000),
        "delta_percent": eq_num(get_path(rtf, ["delta", "percent_points"]), 0.2),
        "delta_amount": eq_int(get_path(rtf, ["delta", "amount_usd"]), 1520000),
        "benchmark_sample": eq_int(get_path(rtf, ["benchmark", "sample_size"]), 42),
        "benchmark_median": eq_num(get_path(rtf, ["benchmark", "median"]), 3.2),
        "benchmark_upper_quartile": eq_num(get_path(rtf, ["benchmark", "upper_quartile"]), 4.1),
        "benchmark_position": norm_text(get_path(rtf, ["benchmark", "position"])) == "above_upper_quartile",
        "exposure_low": eq_int(get_path(rtf, ["exposure", "low_usd"]), 11400000),
        "exposure_high": eq_int(get_path(rtf, ["exposure", "high_usd"]), 34200000),
        "exposure_source": norm_text(get_path(rtf, ["exposure", "source_estimate_id"])) == "rsk_prj_rook_01",
    }
    voting_checks = {
        "draft_percent": eq_num(get_path(voting, ["draft_metric", "value"]), 41.0),
        "threshold_percent": eq_num(get_path(voting, ["policy_metric", "threshold_value"]), 35.0),
        "delta_percent": eq_num(get_path(voting, ["delta", "percent_points"]), 6.0),
        "total_shares": eq_int(get_path(voting, ["draft_metric", "total_fully_diluted_shares"]), 45400000),
        "locked_shares": eq_int(get_path(voting, ["draft_metric", "locked_share_count"]), 18614000),
        "policy_max_shares": eq_int(get_path(voting, ["policy_metric", "policy_max_locked_shares"]), 15890000),
        "excess_shares": eq_int(get_path(voting, ["delta", "excess_locked_shares"]), 2724000),
    }
    mae_checks = {
        "added_count": eq_int(get_path(mae, ["draft_metric", "added_count"]), 2),
        "threshold_count": eq_int(get_path(mae, ["policy_metric", "threshold_value"]), 2),
        "excess_count": (
            eq_int(get_path(mae, ["delta", "excess_count"]), 0)
            or (
                eq_int(get_path(mae, ["delta", "excess_count"]), 2)
                and eq_int(get_path(mae, ["delta", "unapproved_carveout_count"]), 2)
            )
        ),
        "unapproved_count": eq_int(get_path(mae, ["delta", "unapproved_carveout_count"]), 2),
        "restricted": norm_set(get_path(mae, ["draft_metric", "restricted_carveouts"]))
        == {
            "autonomous_vehicle_regulation",
            "supply_chain_disruption",
        },
        "approved_groups": norm_set(get_path(mae, ["policy_metric", "approved_carveout_groups"]))
        == {
            "general_economic_or_financial_market_conditions",
            "natural_disasters_or_acts_of_terrorism",
        },
    }
    checks = {"rtf": rtf_checks, "voting": voting_checks, "mae": mae_checks}
    return all(all(group.values()) for group in checks.values()), checks


def check_recommendations(answer):
    rows = rows_by_category(answer)
    found = {
        category: {
            "recommendation": norm_text(rows.get(category, {}).get("recommendation")),
            "risk_rating": norm_text(rows.get(category, {}).get("risk_rating")).upper(),
            "concession_posture": norm_text(rows.get(category, {}).get("concession_posture")),
        }
        for category in EXPECTED_TERMS
    }
    expected = {
        "reverse_termination_fee": {
            "recommendation": "approve_with_conditions",
            "risk_rating": "MEDIUM",
            "concession_posture": "tradeable_if_capped",
        },
        "voting_agreements": {
            "recommendation": "reject",
            "risk_rating": "HIGH",
            "concession_posture": "must_fix",
        },
        "mae_carveouts": {
            "recommendation": "approve_with_conditions",
            "risk_rating": "MEDIUM",
            "concession_posture": "tradeable_if_narrowed",
        },
    }
    checks = {}
    for category, expected_values in expected.items():
        row = found.get(category, {})
        risk_ok = row.get("risk_rating") == expected_values["risk_rating"]
        if category == "mae_carveouts":
            risk_ok = risk_ok or row.get("risk_rating") == "HIGH"
        checks[category] = (
            row.get("recommendation") == expected_values["recommendation"]
            and risk_ok
            and row.get("concession_posture") == expected_values["concession_posture"]
        )
    return all(checks.values()), {"found": found, "expected": expected, "checks": checks}


def check_sequence(answer):
    sequence = answer.get("negotiation_sequence")
    if not isinstance(sequence, list):
        return False, {"error": "negotiation_sequence is not a list"}
    simplified = []
    for row in sequence:
        if not isinstance(row, dict):
            continue
        simplified.append(
            (
                int(number(row.get("rank")) or -1),
                norm_text(row.get("category")),
                norm_text(row.get("term_id")),
                norm_text(row.get("priority_type")),
                norm_text(row.get("recommended_action")),
            )
        )
    filtered = [row for row in simplified if row[1] != "termination_fee"]
    expected = [
        (1, "voting_agreements", "term_prj_rook_03", "legal_blocker", "reduce_to_policy_threshold"),
        (2, "reverse_termination_fee", "term_prj_rook_01", "economic_concession", "cap_at_policy"),
        (3, "mae_carveouts", "term_prj_rook_04", "definition_concession", "narrow_and_add_exception"),
    ]
    flexible_ok = (
        len(filtered) >= 3
        and filtered[0][1] == "voting_agreements"
        and filtered[0][2] == "term_prj_rook_03"
        and filtered[0][3] == "legal_blocker"
        and filtered[0][4] in {"reduce_to_policy_threshold", "reject_as_drafted"}
        and {filtered[1][1], filtered[2][1]} == {"reverse_termination_fee", "mae_carveouts"}
        and all(
            (row[1] != "reverse_termination_fee" or (row[2] == "term_prj_rook_01" and row[4] == "cap_at_policy"))
            and (row[1] != "mae_carveouts" or (row[2] == "term_prj_rook_04" and row[4] == "narrow_and_add_exception"))
            for row in filtered[1:3]
        )
        and ("termination_fee" not in {row[1] for row in simplified} or excluded_noncommittee_ok(answer))
    )
    return simplified == expected or flexible_ok, {"found": simplified, "filtered": filtered, "expected": expected}


def check_flags(answer):
    flags = get_path(answer, ["aggregate_summary", "deal_certainty_flags"])
    if not isinstance(flags, dict):
        return False, {"error": "deal_certainty_flags is not an object"}
    expected = {
        "hsr_required": True,
        "industry_review_required": True,
        "hell_or_high_water_required": False,
        "required_closing_consents_present": True,
        "top_customer_consent_high_risk": True,
        "support_agreement_above_policy": True,
        "topping_bid_deterrence_rationale_present": True,
        "counterparty_timing_pressure_present": True,
        "must_fix_legal_blocker_present": True,
        "economic_terms_tradeable_if_capped": True,
    }
    found = {key: flags.get(key) for key in expected}
    return found == expected, {"found": found, "expected": expected}


def check_aggregate(answer):
    summary = answer.get("aggregate_summary", {})
    risk_counts = summary.get("risk_counts", {}) if isinstance(summary, dict) else {}
    included = summary.get("included_exposure_components")
    excluded = summary.get("excluded_exposure_components")
    closing_included = any_component(included, "closing", "certainty")
    rtf_included = (
        any_component(included, "rtf")
        or any_component(included, "reverse", "termination")
        or any_component(included, "reverse", "fee")
    )
    company_included = any_component(included, "company", "fee") or any_component(included, "company", "termination")
    company_excluded = any_component(excluded, "company", "fee") or any_component(excluded, "company", "termination")
    standard_exposure = eq_int(summary.get("aggregate_quantified_exposure_low_usd"), 11400000) and eq_int(
        summary.get("aggregate_quantified_exposure_high_usd"), 34200000
    )
    closing_plus_rtf_exposure = (
        eq_int(summary.get("aggregate_quantified_exposure_low_usd"), 12920000)
        and eq_int(summary.get("aggregate_quantified_exposure_high_usd"), 35720000)
        and rtf_included
        and company_excluded
        and not company_included
    )
    checks = {
        "waiver_count": eq_int(summary.get("waiver_term_count"), 3),
        "risk_counts": (
            isinstance(risk_counts, dict)
            and (
                (eq_int(risk_counts.get("HIGH"), 1) and eq_int(risk_counts.get("MEDIUM"), 2))
                or (
                    eq_int(summary.get("waiver_term_count"), 3)
                    and eq_int(risk_counts.get("HIGH"), 2)
                    and eq_int(risk_counts.get("MEDIUM"), 1)
                    and company_excluded
                    and not company_included
                )
            )
            and eq_int(risk_counts.get("LOW"), 0)
        ),
        "exposure_low": standard_exposure or closing_plus_rtf_exposure,
        "exposure_high": standard_exposure or closing_plus_rtf_exposure,
        "included_components": closing_included and not company_included,
        "excluded_components": (
            any_component(excluded, "indemnity", "leakage")
            and any_component(excluded, "transition", "disruption")
            and (standard_exposure or company_excluded)
        ),
        "rtf_excess": eq_int(summary.get("reverse_termination_fee_excess_amount_usd"), 1520000),
        "company_fee_excess": eq_int(summary.get("company_termination_fee_excess_amount_usd"), 3040000),
        "required_consent_amount": eq_int(summary.get("required_closing_consent_amount_at_risk_usd"), 42650000),
        "material_contract_revenue": eq_int(summary.get("material_contract_revenue_requiring_consent_usd"), 84360000),
    }
    return all(checks.values()), checks


def check_conditions(answer):
    rows = rows_by_category(answer)
    expected_by_category = {
        "voting_agreements": {
            "cap_support_agreements_at_35_percent",
            "exclude_unaffiliated_minority_holders_from_lockup",
            "preserve_board_fiduciary_flexibility",
        },
        "reverse_termination_fee": {
            "cap_reverse_termination_fee_at_30400000",
            "reduce_reverse_termination_fee_to_4_percent",
            "align_regulatory_remedy_covenant_without_hell_or_high_water",
        },
        "mae_carveouts": {
            "add_disproportionate_effects_exception",
            "narrow_autonomous_vehicle_regulation_carveout",
            "narrow_supply_chain_disruption_carveout",
        },
    }
    term_checks = {
        category: expected.issubset(norm_set(rows.get(category, {}).get("required_conditions")))
        for category, expected in expected_by_category.items()
    }
    aggregate_expected = set().union(*expected_by_category.values())
    aggregate_ok = aggregate_expected.issubset(
        norm_set(get_path(answer, ["aggregate_summary", "committee_conditions"]))
    )
    condition_text_raw = " ".join(norm_set(get_path(answer, ["aggregate_summary", "committee_conditions"])))
    condition_text = condition_text_raw.replace("_", " ")
    semantic_conditions = {
        "voting_agreements": (
            (
                "support" in condition_text
                or "lock" in condition_text
                or "voting" in condition_text
                or "term prj rook 03" in condition_text
                or "term_prj_rook_03" in condition_text_raw
            )
            and ("35" in condition_text or "policy" in condition_text or "cap" in condition_text)
        ),
        "reverse_termination_fee": (
            "rtf" in condition_text
            or "reverse termination" in condition_text
            or "reverse fee" in condition_text
            or "term prj rook 01" in condition_text
            or "term_prj_rook_01" in condition_text_raw
        )
        and ("4" in condition_text or "policy" in condition_text or "cap" in condition_text),
        "mae_carveouts": (
            (
                "mae" in condition_text
                or "term prj rook 04" in condition_text
                or "term_prj_rook_04" in condition_text_raw
            )
            and (
                "narrow" in condition_text
                or "approved" in condition_text
                or "carveout" in condition_text
                or "exception" in condition_text
            )
        ),
    }
    company_fee_condition = (
        "company" in condition_text
        or "term_prj_rook_02" in condition_text_raw
        or ("termination_fee_at_3" in condition_text_raw and "reverse" not in condition_text)
    )
    semantic_ok = all(semantic_conditions.values()) and (not company_fee_condition or excluded_noncommittee_ok(answer))
    return (all(term_checks.values()) and aggregate_ok) or semantic_ok, {
        "term_checks": term_checks,
        "aggregate_ok": aggregate_ok,
        "semantic_conditions": semantic_conditions,
        "company_fee_condition": company_fee_condition,
    }


def check_posture_routing(answer):
    memo = answer.get("memo", {})
    summary = answer.get("aggregate_summary", {})
    action = norm_text(summary.get("committee_action"))
    condition_text = " ".join(norm_set(summary.get("committee_conditions")))
    condition_text_normalized = condition_text.replace("_", " ")
    flexible_action = (
        ("approve" in action or "approval" in action)
        and ("lock" in action or "support" in action)
        and ("fee" in action or "economic" in action or "rtf" in action or "reverse" in action)
        and (
            "mae" in action
            or "narrow" in action
            or "mae" in condition_text
            or "term prj rook 04" in condition_text_normalized
            or "approved" in condition_text_normalized
            or "carveout" in condition_text_normalized
        )
        and ("company" not in action or excluded_noncommittee_ok(answer))
    )
    checks = {
        "task_id": norm_text(answer.get("task_id")) == "test_005",
        "deal_id": norm_text(answer.get("deal_id")) == "prj_rook",
        "prepared_for": norm_text(memo.get("prepared_for")) == "m&a committee",
        "client": memo.get("client_name") == "Rook Mobility plc",
        "project": memo.get("project_name") == "Project Rook",
        "target": memo.get("target_name") == "Rook Autonomous Fleet",
        "counterparty": memo.get("counterparty_name") == "AnchorGate Partners",
        "policy": memo.get("policy_id") == "POL_MA_2025_A",
        "signing_date": memo.get("signing_date") == "2026-01-09",
        "meeting_date": memo.get("meeting_date") == "2026-01-23",
        "currency": memo.get("currency") == "USD",
        "basis": norm_text(memo.get("value_basis")) == "equity value",
        "headline": eq_int(memo.get("headline_value_usd"), 760000000),
        "overall": norm_text(summary.get("overall_recommendation")) == "approve_with_conditions",
        "posture": norm_text(summary.get("final_negotiation_posture"))
        == "hold_legal_line_on_lockup_trade_economic_terms",
        "committee_action": (
            "approve capped rtf" in action
            and "reject voting lock-up above policy" in action
            and "refer company termination fee to general counsel" in action
        )
        or flexible_action,
    }
    return all(checks.values()), checks


CHECKS = {
    "waiver_term_set": check_waiver_term_set,
    "threshold_delta_exposure_calculations": check_thresholds,
    "recommendation_choices": check_recommendations,
    "concession_ranking": check_sequence,
    "batna_deal_certainty_flags": check_flags,
    "aggregate_risk_summary": check_aggregate,
    "committee_conditions": check_conditions,
    "final_posture_and_routing": check_posture_routing,
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
                    "id": name,
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
                    "id": name,
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
