#!/usr/bin/env python3
import json
import sys
from pathlib import Path


TOTAL_WEIGHT = 13


def default_prediction_path() -> Path:
    return Path(__file__).resolve().parents[1] / "output" / "answer.json"


def load_prediction(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as exc:  # noqa: BLE001 - evaluators report parse/read failures as JSON.
        return None, f"{type(exc).__name__}: {exc}"


def is_bool(value, expected):
    return isinstance(value, bool) and value is expected


def eq_num(value, expected):
    if expected is None:
        return value is None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    return round(float(value), 2) == round(float(expected), 2)


def eq_int(value, expected):
    if expected is None:
        return value is None
    if not isinstance(value, int) or isinstance(value, bool):
        return False
    return value == expected


def eq_str(value, expected):
    if expected is None:
        return value is None
    return isinstance(value, str) and value == expected


def eq_str_set(value, expected):
    return (
        isinstance(value, list)
        and all(isinstance(item, str) for item in value)
        and sorted(value) == sorted(expected)
        and len(value) == len(expected)
    )


def term_by_id(prediction, term_id):
    terms = prediction.get("escalation_terms")
    if not isinstance(terms, list):
        return {}
    matches = [item for item in terms if isinstance(item, dict) and item.get("term_id") == term_id]
    if len(matches) != 1:
        return {}
    return matches[0]


def quant(term):
    value = term.get("quantification")
    return value if isinstance(value, dict) else {}


def aggregate(prediction):
    value = prediction.get("aggregate_risk")
    return value if isinstance(value, dict) else {}


def check_rtf(prediction):
    term = term_by_id(prediction, "RTF")
    q = quant(term)
    return all(
        [
            eq_str(prediction.get("deal_id"), "D-NOVA-674"),
            eq_str(term.get("source_clause_id"), "CL-NOVA-674-001"),
            eq_str(term.get("policy_rule_id"), "PUB-RTF"),
            is_bool(term.get("escalation_required"), True),
            eq_str(term.get("committee_route"), "BOARD_TRANSACTION_COMMITTEE"),
            eq_str(term.get("deviation_code"), "ABOVE_RTF_THRESHOLD"),
            eq_num(q.get("draft_percent"), 6.25),
            eq_num(q.get("policy_threshold_percent"), 5.5),
            eq_num(q.get("deviation_percent"), 0.75),
            eq_int(q.get("draft_amount_dollars"), 53750000),
            eq_int(q.get("excess_amount_dollars"), 6450000),
            eq_int(q.get("exposure_amount_dollars"), 53750000),
            eq_str(q.get("exposure_basis"), "EQUITY_VALUE"),
        ]
    )


def check_fiduciary(prediction):
    term = term_by_id(prediction, "FIDUCIARY_OUT")
    q = quant(term)
    return all(
        [
            eq_str(term.get("source_clause_id"), "CL-NOVA-674-002"),
            eq_str(term.get("policy_rule_id"), "PUB-FIDUCIARY"),
            is_bool(term.get("escalation_required"), True),
            eq_str(term.get("committee_route"), "BOARD_TRANSACTION_COMMITTEE"),
            eq_str(term.get("deviation_code"), "TERMINATION_RIGHT_BLOCKED"),
            eq_str(q.get("exposure_basis"), "NON_QUANTIFIED_LEGAL_RISK"),
        ]
    )


def check_survival(prediction):
    term = term_by_id(prediction, "RW_SURVIVAL")
    q = quant(term)
    return all(
        [
            eq_str(term.get("source_clause_id"), "CL-NOVA-674-003"),
            eq_str(term.get("policy_rule_id"), "PUB-RW-SURVIVAL"),
            is_bool(term.get("escalation_required"), True),
            eq_str(term.get("committee_route"), "BOARD_TRANSACTION_COMMITTEE"),
            eq_str(term.get("deviation_code"), "POST_CLOSING_R_AND_W_SURVIVAL"),
            eq_int(q.get("survival_months"), 18),
            eq_int(q.get("exposure_amount_dollars"), 860000000),
            eq_str(q.get("exposure_basis"), "FULL_EQUITY_VALUE_UNCAPPED"),
        ]
    )


def check_mae(prediction):
    term = term_by_id(prediction, "MAE_CARVEOUTS")
    q = quant(term)
    return all(
        [
            eq_str(term.get("source_clause_id"), "CL-NOVA-674-004"),
            eq_str(term.get("policy_rule_id"), "PUB-MAE"),
            is_bool(term.get("escalation_required"), True),
            eq_str(term.get("committee_route"), "BOARD_TRANSACTION_COMMITTEE"),
            eq_str(term.get("deviation_code"), "RESTRICTED_MAE_CARVEOUTS"),
            eq_str(q.get("exposure_basis"), "NON_QUANTIFIED_LEGAL_RISK"),
            eq_str_set(
                q.get("mae_omitted_carveouts"),
                ["CYBER_INCIDENT", "INDUSTRY", "PANDEMIC"],
            ),
        ]
    )


def check_benchmark_context(prediction):
    rtf_q = quant(term_by_id(prediction, "RTF"))
    fiduciary_q = quant(term_by_id(prediction, "FIDUCIARY_OUT"))
    mae_q = quant(term_by_id(prediction, "MAE_CARVEOUTS"))
    context = aggregate(prediction).get("strategic_context")
    if not isinstance(context, dict):
        return False
    return all(
        [
            eq_str(rtf_q.get("benchmark_id"), "BM-RTF-HEALTHTECH-2026"),
            eq_int(rtf_q.get("benchmark_sample_size"), 28),
            eq_int(rtf_q.get("benchmark_count_above_threshold"), 3),
            eq_str(fiduciary_q.get("benchmark_id"), "BM-FIDUCIARY-PUBLIC-2026"),
            eq_int(fiduciary_q.get("benchmark_sample_size"), 42),
            eq_int(fiduciary_q.get("benchmark_count_above_threshold"), 4),
            eq_str(mae_q.get("benchmark_id"), "BM-MAE-HEALTHCARE-2026"),
            eq_int(mae_q.get("benchmark_sample_size"), 36),
            eq_int(mae_q.get("benchmark_count_above_threshold"), 31),
            is_bool(context.get("benchmark_memo_required"), True),
        ]
    )


def check_recommendations(prediction):
    expected = {
        "FIDUCIARY_OUT": "RESTORE_SUPERIOR_PROPOSAL_TERMINATION_RIGHT",
        "MAE_CARVEOUTS": "RESTORE_FULL_PUBLIC_COMPANY_MAE_CARVEOUTS",
        "RTF": "RTF_POLICY_POSITION",
        "RW_SURVIVAL": "DELETE_POST_CLOSING_R_AND_W_SURVIVAL",
    }
    for term_id, recommendation in expected.items():
        term = term_by_id(prediction, term_id)
        if not all(
            [
                eq_str(term.get("approval_recommendation"), "DO_NOT_APPROVE_AS_DRAFTED"),
                eq_str(term.get("recommendation"), recommendation),
                eq_str(term.get("severity"), "HIGH"),
            ]
        ):
            return False
    return True


def check_aggregate(prediction):
    agg = aggregate(prediction)
    context = agg.get("strategic_context")
    if not isinstance(context, dict):
        return False
    return all(
        [
            eq_str(agg.get("committee_route"), "BOARD_TRANSACTION_COMMITTEE"),
            is_bool(agg.get("approval_required"), True),
            eq_str_set(
                agg.get("committee_members"),
                ["Dr. Elaine Park", "Carla Winthrop", "Mateo Silva"],
            ),
            eq_str(agg.get("risk_tier"), "HIGH"),
            eq_str(agg.get("final_action"), "ESCALATE_AND_RENEGOTIATE_BEFORE_SIGNING"),
            eq_str_set(
                agg.get("primary_driver_term_ids"),
                ["FIDUCIARY_OUT", "MAE_CARVEOUTS", "RTF", "RW_SURVIVAL"],
            ),
            eq_int(agg.get("escalation_term_count"), 4),
            eq_int(agg.get("total_quantified_exposure_dollars"), 913750000),
            eq_int(agg.get("total_policy_excess_dollars"), 866450000),
            eq_str(context.get("batna_code"), "LOWER_RISK_PRIVATE_PLATFORM"),
            eq_str(context.get("batna_leverage"), "MODERATE"),
            eq_str(context.get("ownership_context"), "ACTIVIST_PRESSURE_INDEX_FUNDS"),
            eq_str(context.get("strategic_rationale"), "NEED_PLATFORM_BUT_MARKET_STANDARD_RISK"),
        ]
    )


POINTS = [
    {
        "id": "SP001",
        "weight": 2,
        "goal": "Correct RTF threshold, deviation, dollar amounts, and exposure basis.",
        "check": check_rtf,
    },
    {
        "id": "SP002",
        "weight": 1,
        "goal": "Correct fiduciary-out escalation decision.",
        "check": check_fiduciary,
    },
    {
        "id": "SP003",
        "weight": 1,
        "goal": "Correct R&W survival escalation and full equity-value exposure.",
        "check": check_survival,
    },
    {
        "id": "SP004",
        "weight": 2,
        "goal": "Correct MAE restricted carve-out escalation and omitted carve-out codes.",
        "check": check_mae,
    },
    {
        "id": "SP005",
        "weight": 3,
        "goal": "Correct benchmark and statistical context for RTF, fiduciary-out, and MAE review.",
        "check": check_benchmark_context,
    },
    {
        "id": "SP006",
        "weight": 1,
        "goal": "Correct individual approval recommendations and term recommendations.",
        "check": check_recommendations,
    },
    {
        "id": "SP007",
        "weight": 3,
        "goal": "Correct aggregate risk, quantified totals, strategic context, and committee routing.",
        "check": check_aggregate,
    },
]


def evaluate(prediction, error=None):
    results = []
    earned_weight = 0

    if error is None and isinstance(prediction, dict):
        for point in POINTS:
            passed = bool(point["check"](prediction))
            earned = point["weight"] if passed else 0
            earned_weight += earned
            results.append(
                {
                    "id": point["id"],
                    "goal": point["goal"],
                    "weight": point["weight"],
                    "earned_weight": earned,
                    "passed": passed,
                }
            )
    else:
        for point in POINTS:
            results.append(
                {
                    "id": point["id"],
                    "goal": point["goal"],
                    "weight": point["weight"],
                    "earned_weight": 0,
                    "passed": False,
                }
            )

    return {
        "score": round(earned_weight / TOTAL_WEIGHT, 10),
        "earned_weight": earned_weight,
        "total_weight": TOTAL_WEIGHT,
        "points": results,
        "error": error,
    }


def main():
    prediction_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else default_prediction_path()
    prediction, error = load_prediction(prediction_path)
    print(json.dumps(evaluate(prediction, error), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
