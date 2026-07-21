"""Train-only answer scoring for the task_group_014 environment."""

from __future__ import annotations

import math
import re
from typing import Any, Callable


NOTICE = "train-only judge; no rubric details or gold answers are returned"


class JudgeError(ValueError):
    """Raised for rejected judge requests."""


def _norm(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9.]+", "_", str(value).lower()).strip("_")


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return " ".join(_text(v) for v in (value.values() if isinstance(value, dict) else value))
    return str(value).lower()


def _numbers(value: Any) -> list[float]:
    found: list[float] = []
    if isinstance(value, bool) or value is None:
        return found
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, dict):
        for item in value.values():
            found.extend(_numbers(item))
        return found
    if isinstance(value, (list, tuple)):
        for item in value:
            found.extend(_numbers(item))
        return found
    for match in re.findall(r"-?\d+(?:\.\d+)?", str(value).replace(",", "")):
        found.append(float(match))
    return found


def _has_text(answer: Any, *needles: str) -> bool:
    haystack = _text(answer)
    return all(needle.lower() in haystack for needle in needles)


def _has_any(answer: Any, needles: list[str]) -> bool:
    haystack = _text(answer)
    return any(needle.lower() in haystack for needle in needles)


def _has_number(answer: Any, expected: float, tolerance: float = 0.01) -> bool:
    return any(math.isclose(number, expected, abs_tol=tolerance) for number in _numbers(answer))


def _value_for_key(answer: Any, key_terms: list[str]) -> Any:
    if isinstance(answer, dict):
        for key, value in answer.items():
            normalized_key = _norm(key)
            if all(term in normalized_key for term in key_terms):
                return value
            nested = _value_for_key(value, key_terms)
            if nested is not None:
                return nested
    elif isinstance(answer, list):
        for item in answer:
            nested = _value_for_key(item, key_terms)
            if nested is not None:
                return nested
    return None


def _key_has_text(answer: Any, key_terms: list[str], *needles: str) -> bool:
    value = _value_for_key(answer, key_terms)
    return value is not None and _has_text(value, *needles)


def _key_has_number(answer: Any, key_terms: list[str], expected: float, tolerance: float = 0.01) -> bool:
    value = _value_for_key(answer, key_terms)
    return value is not None and _has_number(value, expected, tolerance)


Check = Callable[[Any], bool]


def _score(answer: Any, checks: list[tuple[int, Check]]) -> float:
    total = sum(weight for weight, _ in checks)
    earned = sum(weight for weight, check in checks if check(answer))
    return round(earned / total, 6) if total else 0.0


def _get(answer: Any, *path: str) -> Any:
    current = answer
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _eq_text(value: Any, expected: str) -> bool:
    return _norm(value) == _norm(expected)


def _eq_number(value: Any, expected: float, tolerance: float = 0.01) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isclose(float(value), expected, abs_tol=tolerance)
    )


def _set_eq(value: Any, expected: list[str]) -> bool:
    if not isinstance(value, list):
        return False
    return {_norm(item) for item in value} == {_norm(item) for item in expected}


def _criteria(answer: Any, expected: dict[str, str]) -> bool:
    actual = answer.get("criteria_results")
    if not isinstance(actual, dict):
        return False
    return all(_eq_text(actual.get(key), result) for key, result in expected.items())


def _lines(answer: Any) -> dict[str, dict[str, Any]]:
    lines = answer.get("lines")
    if not isinstance(lines, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for line in lines:
        if isinstance(line, dict) and line.get("line_id"):
            result[str(line["line_id"])] = line
    return result


def _rows(answer: Any) -> dict[str, dict[str, Any]]:
    rows = answer.get("rows")
    if not isinstance(rows, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and row.get("month_id"):
            result[str(row["month_id"])] = row
    return result


def _train_001(answer: Any) -> float:
    checks: list[tuple[int, Check]] = [
        (1, lambda a: _eq_text(a.get("case_id"), "CASE-TR-001") and _eq_text(a.get("route"), "nurse_approval")),
        (2, lambda a: _eq_text(a.get("recommendation"), "approve") and _eq_text(a.get("final_status"), "approved")),
        (
            2,
            lambda a: _eq_text(_get(a, "authorization", "auth_number"), "NPA-2405014")
            and _eq_number(_get(a, "authorization", "approved_units"), 24)
            and a.get("authorization", {}).get("approved_start") == "2026-05-06"
            and a.get("authorization", {}).get("approved_end") == "2026-07-05",
        ),
        (
            1,
            lambda a: _set_eq(_get(a, "authorization", "approved_cpt"), ["97110", "97112", "97530"])
            and _eq_text(_get(a, "authorization", "modifier"), "GP"),
        ),
        (
            2,
            lambda a: _criteria(
                a,
                {"PT-ACTIVE": "met", "PT-DEFICIT": "met", "PT-DX": "met", "PT-POC": "met", "PT-UNITS": "met"},
            ),
        ),
        (
            2,
            lambda a: _set_eq(a.get("evidence_documents"), ["DOC-TR-001-EVAL", "DOC-TR-001-POC"])
            and _set_eq(a.get("excluded_documents"), ["DOC-TR-001-STALE"]),
        ),
        (
            1,
            lambda a: _eq_text(a.get("determination_letter"), "approval")
            and _eq_text(a.get("next_action"), "issue_approval"),
        ),
    ]
    return _score(answer, checks)


def _train_002(answer: Any) -> float:
    checks: list[tuple[int, Check]] = [
        (
            1,
            lambda a: _eq_text(a.get("case_id"), "APPEAL-TR-002")
            and _eq_text(a.get("appeal_id"), "APL-TR-002")
            and _eq_text(a.get("drug"), "Vraylar")
            and _eq_text(a.get("owner"), "appeals-rx"),
        ),
        (
            2,
            lambda a: _eq_text(a.get("appeal_path"), "standard_internal")
            and a.get("expedited") is False
            and a.get("appeal_deadline") == "2026-06-07",
        ),
        (
            2,
            lambda a: _set_eq(a.get("documented_failures"), ["quetiapine"])
            and _set_eq(a.get("undocumented_or_insufficient_failures"), ["lurasidone"]),
        ),
        (
            2,
            lambda a: _criteria(
                a,
                {"DRUG-AUTH": "met", "DRUG-DENIAL": "met", "DRUG-RATIONALE": "met", "DRUG-FAILURES": "partial"},
            ),
        ),
        (
            1,
            lambda a: _set_eq(
                a.get("required_packet_items"),
                [
                    "denial_notice",
                    "member_authorization",
                    "prescriber_rationale",
                    "formulary_failure_evidence",
                    "household_income_proof",
                ],
            ),
        ),
        (
            2,
            lambda a: _set_eq(a.get("missing_packet_items"), ["lurasidone_fill_record", "household_income_proof"])
            and _set_eq(_get(a, "assistance", "missing_fields"), ["household_income_proof"]),
        ),
        (
            1,
            lambda a: _eq_text(_get(a, "assistance", "program_name"), "Vraylar Connect")
            and _eq_text(_get(a, "assistance", "status"), "eligible_missing_information")
            and _eq_text(a.get("next_action"), "request_more_information"),
        ),
    ]
    return _score(answer, checks)


def _train_003(answer: Any) -> float:
    expected_lines = {
        "CL-TR-003-1": ("78452", "TC", 1, 608.0, 760.0, 152.0, "correct_upward"),
        "CL-TR-003-2": ("A9500", None, 2, 288.0, 360.0, 72.0, "correct_upward"),
        "CL-TR-003-3": ("93016", None, 1, 44.0, 55.0, 11.0, "correct_upward"),
    }

    def line_identity(a: Any) -> bool:
        lines = _lines(a)
        if set(lines) != set(expected_lines):
            return False
        for line_id, (cpt, modifier, units, *_rest) in expected_lines.items():
            line = lines[line_id]
            if not (
                _eq_text(line.get("cpt_code"), cpt) and line.get("modifier") == modifier and line.get("units") == units
            ):
                return False
        return True

    def line_amounts(a: Any) -> bool:
        lines = _lines(a)
        if set(lines) != set(expected_lines):
            return False
        for line_id, (_cpt, _modifier, _units, paid, allowed, recovery, disposition) in expected_lines.items():
            line = lines[line_id]
            if not (
                _eq_number(line.get("paid_amount"), paid)
                and _eq_number(line.get("correct_allowed_amount"), allowed)
                and _eq_number(line.get("recovery_amount"), recovery)
                and _eq_text(line.get("disposition"), disposition)
            ):
                return False
        return True

    checks: list[tuple[int, Check]] = [
        (1, lambda a: _eq_text(a.get("claim_id"), "CLAIM-TR-003") and _eq_text(a.get("auth_number"), "NPA-2404980")),
        (
            2,
            lambda a: _eq_text(a.get("benchmark_source"), "Northstar Commercial Imaging Schedule")
            and _eq_text(a.get("benchmark_version"), "2026Q2")
            and _eq_text(a.get("stale_source_rejected"), "Legacy Imaging Export"),
        ),
        (
            3,
            lambda a: _eq_number(a.get("paid_total"), 940.0)
            and _eq_number(a.get("correct_allowed_total"), 1175.0)
            and _eq_number(a.get("recovery_amount"), 235.0),
        ),
        (1, line_identity),
        (3, line_amounts),
        (
            1,
            lambda a: _eq_text(a.get("resubmission_route"), "payment_integrity_correction")
            and _eq_text(a.get("priority"), "standard"),
        ),
    ]
    return _score(answer, checks)


def _train_004(answer: Any) -> float:
    checks: list[tuple[int, Check]] = [
        (
            1,
            lambda a: _eq_text(a.get("case_id"), "P2P-TR-004")
            and _eq_text(a.get("p2p_id"), "P2P-TR-004-E1")
            and _eq_text(a.get("requested_cpt"), "78431"),
        ),
        (
            3,
            lambda a: _eq_text(a.get("p2p_outcome"), "uphold_intended_adverse_decision")
            and _eq_text(a.get("final_status"), "denied"),
        ),
        (2, lambda a: _criteria(a, {"PET-IND": "met", "PET-FACTOR": "not_met"})),
        (
            2,
            lambda a: _set_eq(a.get("unresolved_criteria"), ["PET-FACTOR"])
            and a.get("new_information_changed_review") is False
            and _set_eq(
                a.get("missing_pet_factors"), ["prior_equivocal_spect", "bmi_limitation", "attenuation_artifact"]
            ),
        ),
        (
            1,
            lambda a: _eq_text(a.get("letter_type"), "denial")
            and _eq_text(a.get("recommended_alternative"), "SPECT MPI"),
        ),
        (1, lambda a: a.get("internal_appeal_deadline") == "2026-11-09"),
    ]
    return _score(answer, checks)


def _train_005(answer: Any) -> float:
    expected_rows = {
        "SM-TR-005-MCD": ("medicaid", "97110", 26240.0, -2550.0, 0.9028, True, False, "payer_contract_review"),
        "SM-TR-005-COM": ("commercial", "97530", 31700.0, 13570.0, 1.4281, False, True, "monitor_charge_sensitive"),
        "SM-TR-005-WC": ("workers_comp", "97112", 13520.0, 12240.0, 1.9053, False, True, "monitor_charge_sensitive"),
    }

    def rows_match(a: Any, fields: tuple[str, ...]) -> bool:
        rows = _rows(a)
        if set(rows) != set(expected_rows):
            return False
        for row_id, (segment, cpt, total_cost, margin, ratio, below, charge, action) in expected_rows.items():
            row = rows[row_id]
            checks = {
                "payer_segment": _eq_text(row.get("payer_segment"), segment),
                "cpt_code": _eq_text(row.get("cpt_code"), cpt),
                "total_cost": _eq_number(row.get("total_cost"), total_cost),
                "margin": _eq_number(row.get("margin"), margin),
                "revenue_to_cost_ratio": _eq_number(row.get("revenue_to_cost_ratio"), ratio, 0.0001),
                "below_threshold": row.get("below_threshold") is below,
                "charge_sensitive": row.get("charge_sensitive") is charge,
                "recommended_action": _eq_text(row.get("recommended_action"), action),
            }
            if not all(checks[field] for field in fields):
                return False
        return True

    checks: list[tuple[int, Check]] = [
        (
            1,
            lambda a: _eq_text(a.get("case_id"), "QUEUE-TR-005")
            and a.get("period") == "2026-05"
            and _eq_number(a.get("threshold_revenue_to_cost_ratio"), 1.2, 0.0001),
        ),
        (2, lambda a: rows_match(a, ("payer_segment", "cpt_code", "total_cost", "margin"))),
        (2, lambda a: rows_match(a, ("revenue_to_cost_ratio",))),
        (
            3,
            lambda a: rows_match(a, ("below_threshold",))
            and _set_eq(a.get("below_threshold_segments"), ["medicaid"])
            and _eq_text(a.get("top_issue"), "medicaid_97110"),
        ),
        (
            2,
            lambda a: rows_match(a, ("charge_sensitive",))
            and _set_eq(a.get("charge_sensitive_segments"), ["commercial", "workers_comp"]),
        ),
        (2, lambda a: rows_match(a, ("recommended_action",))),
        (1, lambda a: _eq_number(a.get("gap_to_120pct"), 7798.0)),
    ]
    return _score(answer, checks)


SCORERS: dict[str, Callable[[Any], float]] = {
    "train_001": _train_001,
    "train_002": _train_002,
    "train_003": _train_003,
    "train_004": _train_004,
    "train_005": _train_005,
}


def score_train_answer(task_id: str, answer: Any) -> dict[str, Any]:
    normalized = _norm(task_id)
    if normalized.startswith("test_"):
        raise JudgeError("test task ids are not accepted by this train-only judge")
    if normalized not in SCORERS:
        raise JudgeError("unknown train task id")
    if not isinstance(answer, dict):
        raise JudgeError("answer must be a JSON object")
    score = SCORERS[normalized](answer)
    return {"score": score, "correct": bool(score >= 0.999999), "notice": NOTICE}
