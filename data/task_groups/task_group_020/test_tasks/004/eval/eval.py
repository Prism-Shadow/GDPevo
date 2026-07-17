#!/usr/bin/env python3
"""Evaluator for task_group_020 test_004."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable


TASK_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PREDICTION = TASK_DIR / "output" / "answer.json"
TOTAL_WEIGHT = 11


def load_prediction(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return None, f"Prediction file not found: {path}"
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON: {exc}"
    if not isinstance(data, dict):
        return None, "Top-level prediction must be a JSON object."
    return data, None


def term_index(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    terms = data.get("reviewed_terms", [])
    if not isinstance(terms, list):
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for term in terms:
        if not isinstance(term, dict):
            continue
        term_id = term.get("term_id")
        if isinstance(term_id, str) and term_id not in indexed:
            indexed[term_id] = term
    return indexed


def committee_packet(data: dict[str, Any]) -> dict[str, Any]:
    packet = data.get("committee_packet", {})
    return packet if isinstance(packet, dict) else {}


def quant(term: dict[str, Any]) -> dict[str, Any]:
    value = term.get("quantification", {})
    return value if isinstance(value, dict) else {}


def is_bool(value: Any, expected: bool) -> bool:
    return isinstance(value, bool) and value is expected


def is_int(value: Any, expected: int | None) -> bool:
    if expected is None:
        return value is None
    if isinstance(value, bool):
        return False
    try:
        return int(value) == expected and float(value) == float(expected)
    except (TypeError, ValueError):
        return False


def is_num(value: Any, expected: float | None, decimals: int = 2) -> bool:
    if expected is None:
        return value is None
    if isinstance(value, bool):
        return False
    try:
        return round(float(value), decimals) == round(float(expected), decimals)
    except (TypeError, ValueError):
        return False


def is_str_set(value: Any, expected: set[str]) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) for item in value)
        and set(value) == expected
        and len(value) == len(expected)
    )


def escalation_terms_from_review(data: dict[str, Any]) -> set[str]:
    result = set()
    for term_id, term in term_index(data).items():
        if term.get("escalation_required") is True:
            result.add(term_id)
    return result


def within_terms_from_review(data: dict[str, Any]) -> set[str]:
    result = set()
    for term_id, term in term_index(data).items():
        if term.get("escalation_required") is False and term.get("review_status") in {
            "WITHIN_PLAYBOOK",
            "WITHIN_PLAYBOOK_FALLBACK",
        }:
            result.add(term_id)
    return result


def term_core(
    term: dict[str, Any],
    *,
    clause_id: str | None,
    policy_rule_id: str | None,
    status: str,
    escalation_required: bool,
    route: str,
    deviation: str,
) -> bool:
    return (
        term.get("source_clause_id") == clause_id
        and term.get("policy_rule_id") == policy_rule_id
        and term.get("review_status") == status
        and is_bool(term.get("escalation_required"), escalation_required)
        and term.get("committee_route") == route
        and term.get("deviation_code") == deviation
    )


def check_escalation_required_set(data: dict[str, Any]) -> bool:
    terms = term_index(data)
    packet = committee_packet(data)
    expected = {"GOVERNANCE", "INDEMNITY_CAP", "ROLLOVER"}
    return (
        escalation_terms_from_review(data) == expected
        and is_str_set(packet.get("terms_requiring_escalation"), expected)
        and is_int(packet.get("escalation_term_count"), 3)
        and term_core(
            terms.get("ROLLOVER", {}),
            clause_id="CL-KEPLER-155-003",
            policy_rule_id="HYB-ROLLOVER",
            status="ESCALATION_REQUIRED",
            escalation_required=True,
            route="INVESTMENT_COMMITTEE",
            deviation="ABOVE_ROLLOVER_MISMATCH_THRESHOLD",
        )
        and term_core(
            terms.get("INDEMNITY_CAP", {}),
            clause_id="CL-KEPLER-155-004",
            policy_rule_id="HYB-CAP",
            status="ESCALATION_REQUIRED",
            escalation_required=True,
            route="INVESTMENT_COMMITTEE",
            deviation="ABOVE_CAP_THRESHOLD",
        )
        and term_core(
            terms.get("GOVERNANCE", {}),
            clause_id="CL-KEPLER-155-005",
            policy_rule_id="HYB-GOVERNANCE",
            status="ESCALATION_REQUIRED",
            escalation_required=True,
            route="INVESTMENT_COMMITTEE",
            deviation="FOUNDER_ORDINARY_COURSE_VETO",
        )
    )


def check_within_playbook_set(data: dict[str, Any]) -> bool:
    terms = term_index(data)
    packet = committee_packet(data)
    expected = {"ESCROW", "NONCOMPETE", "TAX_ESCROW"}
    return (
        within_terms_from_review(data) == expected
        and is_str_set(packet.get("terms_within_playbook"), expected)
        and is_int(packet.get("within_playbook_term_count"), 3)
        and term_core(
            terms.get("ESCROW", {}),
            clause_id="CL-KEPLER-155-001",
            policy_rule_id="HYB-ESCROW",
            status="WITHIN_PLAYBOOK_FALLBACK",
            escalation_required=False,
            route="NO_COMMITTEE_ROUTE",
            deviation="WITHIN_ESCROW_FALLBACK",
        )
        and term_core(
            terms.get("TAX_ESCROW", {}),
            clause_id="CL-KEPLER-155-002",
            policy_rule_id="HYB-ESCROW",
            status="WITHIN_PLAYBOOK",
            escalation_required=False,
            route="NO_COMMITTEE_ROUTE",
            deviation="WITHIN_TAX_ESCROW_RANGE",
        )
        and term_core(
            terms.get("NONCOMPETE", {}),
            clause_id="CL-KEPLER-155-006",
            policy_rule_id=None,
            status="WITHIN_PLAYBOOK_FALLBACK",
            escalation_required=False,
            route="NO_COMMITTEE_ROUTE",
            deviation="WITHIN_NONCOMPETE_FALLBACK",
        )
    )


def check_dollar_exposures(data: dict[str, Any]) -> bool:
    terms = term_index(data)
    escrow = quant(terms.get("ESCROW", {}))
    tax = quant(terms.get("TAX_ESCROW", {}))
    rollover = quant(terms.get("ROLLOVER", {}))
    cap = quant(terms.get("INDEMNITY_CAP", {}))
    return (
        is_num(escrow.get("draft_percent"), 12.0)
        and is_int(escrow.get("draft_amount_usd"), 17520000)
        and is_int(escrow.get("excess_amount_usd"), 0)
        and is_num(tax.get("draft_percent"), 2.0)
        and is_int(tax.get("draft_amount_usd"), 2920000)
        and is_int(tax.get("excess_amount_usd"), 0)
        and rollover.get("calculation_base") == "ROLLOVER_EQUITY_VALUE"
        and is_num(rollover.get("draft_percent"), 3.5)
        and is_num(rollover.get("policy_threshold_percent"), 2.0)
        and is_num(rollover.get("deviation_percent"), 1.5)
        and is_int(rollover.get("draft_amount_usd"), 1400000)
        and is_int(rollover.get("fallback_amount_usd"), 800000)
        and is_int(rollover.get("excess_amount_usd"), 600000)
        and is_int(rollover.get("exposure_amount_usd"), 1400000)
        and cap.get("calculation_base") == "HEADLINE_VALUE"
        and is_num(cap.get("draft_percent"), 15.0)
        and is_num(cap.get("fallback_percent"), 12.5)
        and is_num(cap.get("policy_threshold_percent"), 12.5)
        and is_num(cap.get("deviation_percent"), 2.5)
        and is_int(cap.get("draft_amount_usd"), 21900000)
        and is_int(cap.get("fallback_amount_usd"), 18250000)
        and is_int(cap.get("excess_amount_usd"), 3650000)
        and is_int(cap.get("exposure_amount_usd"), 21900000)
    )


def check_committee_routing(data: dict[str, Any]) -> bool:
    packet = committee_packet(data)
    return (
        data.get("deal_id") == "D-KEPLER-155"
        and data.get("review_type") == "BUYER_HYBRID_REVIEW_ESCALATION"
        and data.get("currency") == "USD"
        and packet.get("policy_id") == "P-HYBRID-INVEST-2026"
        and packet.get("committee_route") == "INVESTMENT_COMMITTEE"
        and is_bool(packet.get("approval_required"), True)
        and is_str_set(packet.get("committee_members"), {"Ruth Hall", "Devin Cho", "Mika Stone"})
        and packet.get("committee_source_doc_id") == "DOC-KEPLER155-COMMITTEE-07"
    )


def check_recommendations(data: dict[str, Any]) -> bool:
    terms = term_index(data)
    expected = {
        "ESCROW": ("NO_APPROVAL_NEEDED", "ACCEPT_WITHIN_FALLBACK", "MEDIUM"),
        "GOVERNANCE": ("APPROVE_WITH_CONDITIONS", "REMOVE_ORDINARY_COURSE_VETOES", "HIGH"),
        "INDEMNITY_CAP": ("APPROVE_WITH_CONDITIONS", "CAP_REQUIRED_POSITION", "HIGH"),
        "NONCOMPETE": ("NO_APPROVAL_NEEDED", "ACCEPT_WITHIN_FALLBACK", "LOW"),
        "ROLLOVER": ("APPROVE_WITH_CONDITIONS", "ROLLOVER_REQUIRED_POSITION", "HIGH"),
        "TAX_ESCROW": ("NO_APPROVAL_NEEDED", "ACCEPT_AS_DRAFTED", "LOW"),
    }
    for term_id, (approval, position, severity) in expected.items():
        term = terms.get(term_id, {})
        if not (
            term.get("approval_recommendation") == approval
            and term.get("recommended_position") == position
            and term.get("severity") == severity
        ):
            return False
    return True


def normalize_conditions(value: Any) -> set[tuple[str, str]] | None:
    if not isinstance(value, list):
        return None
    normalized: set[tuple[str, str]] = set()
    for item in value:
        if not isinstance(item, dict):
            return None
        condition_id = item.get("condition_id")
        term_id = item.get("term_id")
        required_state = item.get("required_state")
        if condition_id is not None and not isinstance(condition_id, str):
            return None
        if not all(isinstance(part, str) for part in (term_id, required_state)):
            return None
        normalized.add((term_id, required_state))
    return normalized


def check_approval_conditions(data: dict[str, Any]) -> bool:
    packet = committee_packet(data)
    expected = {
        ("INDEMNITY_CAP", "CAP_CONDITION_POSITION"),
        ("GOVERNANCE", "REMOVE_BUDGET_AND_ORDINARY_COURSE_DEBT_VETOES"),
        ("ROLLOVER", "ROLLOVER_CONDITION_POSITION_OR_PRICE_REDUCTION"),
    }
    return normalize_conditions(packet.get("approval_conditions")) == expected


def check_aggregate_risk(data: dict[str, Any]) -> bool:
    packet = committee_packet(data)
    context = packet.get("strategic_context")
    if not isinstance(context, dict):
        return False
    return (
        is_int(packet.get("reviewed_term_count"), 6)
        and packet.get("aggregate_risk_tier") == "HIGH"
        and packet.get("final_action") == "ESCALATE_AND_RENEGOTIATE_BEFORE_SIGNING"
        and is_str_set(packet.get("primary_driver_term_ids"), {"GOVERNANCE", "INDEMNITY_CAP", "ROLLOVER"})
        and is_int(packet.get("total_quantified_exposure_usd"), 23300000)
        and is_int(packet.get("total_policy_excess_usd"), 4250000)
        and context.get("batna_code") == "LOWER_HEADLINE_PRICE_AVAILABLE"
        and context.get("ownership_context") == "FOUNDER_GOVERNANCE_PRESSURE"
        and context.get("strategic_rationale") == "CONTROL_INVESTMENT_WITH_MEANINGFUL_ROLLOVER"
        and is_bool(context.get("benchmark_memo_required"), True)
    )


POINTS: list[tuple[str, int, str, Callable[[dict[str, Any]], bool]]] = [
    (
        "SP001",
        1,
        "Correct escalation-required term set and term-level escalation flags.",
        check_escalation_required_set,
    ),
    ("SP002", 3, "Correct within-playbook fallback term set and non-escalation flags.", check_within_playbook_set),
    ("SP003", 3, "Correct dollar exposure and policy excess calculations.", check_dollar_exposures),
    ("SP004", 1, "Correct investment committee routing and member set.", check_committee_routing),
    ("SP005", 1, "Correct negotiated fallback recommendations for reviewed terms.", check_recommendations),
    ("SP006", 1, "Correct approval conditions for committee packet.", check_approval_conditions),
    ("SP007", 1, "Correct aggregate risk tier, action, totals, and strategic context.", check_aggregate_risk),
]


def zero_result(error: str) -> dict[str, Any]:
    return {
        "score": 0.0,
        "raw_score": 0,
        "max_raw_score": TOTAL_WEIGHT,
        "error": error,
        "point_results": [
            {
                "point_id": point_id,
                "description": description,
                "weight": weight,
                "passed": False,
                "raw_earned": 0,
                "normalized_earned": 0.0,
            }
            for point_id, weight, description, _ in POINTS
        ],
    }


def evaluate(path: Path) -> dict[str, Any]:
    data, error = load_prediction(path)
    if error is not None or data is None:
        return zero_result(error or "Unable to load prediction.")

    raw_score = 0
    point_results = []
    for point_id, weight, description, check in POINTS:
        passed = bool(check(data))
        earned = weight if passed else 0
        raw_score += earned
        point_results.append(
            {
                "point_id": point_id,
                "description": description,
                "weight": weight,
                "passed": passed,
                "raw_earned": earned,
                "normalized_earned": round(earned / TOTAL_WEIGHT, 10),
            }
        )

    return {
        "score": round(raw_score / TOTAL_WEIGHT, 10),
        "raw_score": raw_score,
        "max_raw_score": TOTAL_WEIGHT,
        "point_results": point_results,
    }


def main() -> int:
    prediction_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_PREDICTION
    result = evaluate(prediction_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
