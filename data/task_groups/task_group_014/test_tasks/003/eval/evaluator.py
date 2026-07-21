#!/usr/bin/env python3
import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path


EXPECTED_LINES = {
    "CL-TE-003-1": {
        "line_id": "CL-TE-003-1",
        "cpt_code": "29881",
        "modifier": "RT",
        "units": 1,
        "paid_amount": "1660.00",
        "correct_allowed_amount": "2420.00",
        "recovery_amount": "760.00",
        "disposition": "correct_upward",
    },
    "CL-TE-003-2": {
        "line_id": "CL-TE-003-2",
        "cpt_code": "29881",
        "modifier": "59",
        "units": 1,
        "paid_amount": "350.00",
        "correct_allowed_amount": "0.00",
        "recovery_amount": "-350.00",
        "disposition": "deny_unsupported_modifier",
    },
}

EXPECTED_ORDER = ["CL-TE-003-1", "CL-TE-003-2"]

EXPECTED_BASIS_AUDIT = {
    "source_precedence": "effective_benchmark_by_plan_modifier_and_date",
    "precedence_record_order": [
        "bm-te-003-29881rt",
        "bm-te-003-2988159",
        "cl-te-003-2",
    ],
    "controlling_record_ids": [
        "cl-te-003-1",
        "cl-te-003-2",
        "bm-te-003-29881rt",
        "bm-te-003-2988159",
    ],
    "exception_record_ids": [
        "cl-te-003-2",
    ],
}

RUBRIC = [
    ("identity", 1, "Correct claim, case, and authorization identity."),
    (
        "benchmark_workers_comp_context",
        2,
        "Correct benchmark source/version and workers-comp plan context.",
    ),
    ("totals", 3, "Correct paid total, corrected allowed total, and net recovery."),
    (
        "line_1_correction",
        2,
        "Correct line 1 upward correction amount and disposition.",
    ),
    (
        "line_2_modifier_denial",
        2,
        "Correct line 2 unsupported-modifier denial and negative recovery.",
    ),
    ("routing_priority", 1, "Correct resubmission route and priority."),
    (
        "basis_source_precedence",
        3,
        "Correct business source-precedence basis.",
    ),
    (
        "basis_precedence_record_order",
        3,
        "Correct source-precedence record order.",
    ),
    (
        "basis_controlling_records",
        1,
        "Correct controlling claim line and benchmark record IDs.",
    ),
    (
        "basis_exception_records",
        2,
        "Correct exception record IDs for unsupported modifier handling.",
    ),
]


def norm_text(value):
    if value is None:
        return None
    return str(value).strip()


def norm_id(value):
    text = norm_text(value)
    return text.upper() if text else None


def norm_enum(value):
    text = norm_text(value)
    if not text:
        return None
    return text.lower().replace("-", "_").replace(" ", "_")


def norm_modifier(value):
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() in {"null", "none", "n/a", "na"}:
        return None
    return text.upper()


def as_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            return int(text)
    return None


def as_cents(value):
    if isinstance(value, bool) or value is None:
        return None
    text = str(value).strip().replace("$", "").replace(",", "")
    if text == "":
        return None
    try:
        amount = Decimal(text)
    except InvalidOperation:
        return None
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def cents_equal(value, expected):
    parsed = as_cents(value)
    return parsed is not None and parsed == Decimal(expected)


def get_first(mapping, keys):
    if not isinstance(mapping, dict):
        return None
    for key in keys:
        if key in mapping:
            return mapping.get(key)
    return None


def get_lines(answer):
    lines = answer.get("lines") if isinstance(answer, dict) else None
    return lines if isinstance(lines, list) else []


def audit_value(answer, key):
    audit = answer.get("basis_audit") if isinstance(answer, dict) else None
    if not isinstance(audit, dict):
        return None
    return audit.get(key)


def norm_string_list(value):
    if not isinstance(value, list):
        return None
    result = []
    for item in value:
        text = norm_text(item)
        if text is None:
            return None
        result.append(text.upper())
    return result


def norm_lower_list(value):
    if not isinstance(value, list):
        return None
    result = []
    for item in value:
        text = norm_text(item)
        if text is None:
            return None
        result.append(text.lower())
    return result


def line_map(answer):
    result = {}
    for line in get_lines(answer):
        if not isinstance(line, dict):
            continue
        line_id = norm_id(line.get("line_id"))
        if line_id:
            result[line_id] = line
    return result


def load_candidate(path):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(data, dict):
        return None, "Top-level JSON value must be an object."
    return data, None


def check_identity(answer):
    checks = {
        "claim_id": norm_id(answer.get("claim_id")) == "CLAIM-TE-003",
        "case_id": norm_id(answer.get("case_id")) == "CLAIM-TE-003",
        "auth_number": norm_id(answer.get("auth_number")) == "NPA-2406121",
    }
    return all(checks.values()), checks


def check_benchmark_workers_comp_context(answer):
    checks = {
        "benchmark_source": norm_text(answer.get("benchmark_source")) == "Northstar WC Surgery Schedule",
        "benchmark_version": norm_text(answer.get("benchmark_version")) == "2026",
        "plan_type": norm_enum(answer.get("plan_type")) == "workers_comp",
    }
    return all(checks.values()), checks


def check_totals(answer):
    correct_allowed = get_first(
        answer,
        ["correct_allowed_total", "corrected_allowed_total", "allowed_total"],
    )
    checks = {
        "paid_total": cents_equal(answer.get("paid_total"), "2010.00"),
        "correct_allowed_total": cents_equal(correct_allowed, "2420.00"),
        "recovery_amount": cents_equal(answer.get("recovery_amount"), "410.00"),
    }
    return all(checks.values()), checks


def check_line(line, expected):
    correct_allowed = get_first(
        line,
        ["correct_allowed_amount", "corrected_allowed_amount", "allowed_amount"],
    )
    checks = {
        "line_id": norm_id(line.get("line_id")) == expected["line_id"],
        "cpt_code": norm_id(line.get("cpt_code")) == expected["cpt_code"],
        "modifier": norm_modifier(line.get("modifier")) == expected["modifier"],
        "units": as_int(line.get("units")) == expected["units"],
        "paid_amount": cents_equal(line.get("paid_amount"), expected["paid_amount"]),
        "correct_allowed_amount": cents_equal(
            correct_allowed,
            expected["correct_allowed_amount"],
        ),
        "recovery_amount": cents_equal(line.get("recovery_amount"), expected["recovery_amount"]),
        "disposition": norm_enum(line.get("disposition")) == expected["disposition"],
    }
    return all(checks.values()), checks


def check_line_1_correction(answer):
    lines_by_id = line_map(answer)
    line = lines_by_id.get("CL-TE-003-1", {})
    line_ok, line_checks = check_line(line, EXPECTED_LINES["CL-TE-003-1"])
    order = [norm_id(line.get("line_id")) if isinstance(line, dict) else None for line in get_lines(answer)]
    order_ok = order == EXPECTED_ORDER
    return line_ok and order_ok, {"line": line_checks, "line_order": order, "expected_order": EXPECTED_ORDER}


def check_line_2_modifier_denial(answer):
    lines_by_id = line_map(answer)
    line = lines_by_id.get("CL-TE-003-2", {})
    line_ok, line_checks = check_line(line, EXPECTED_LINES["CL-TE-003-2"])
    exact_line_set = set(lines_by_id) == set(EXPECTED_LINES)
    return line_ok and exact_line_set, {"line": line_checks, "line_ids": sorted(lines_by_id)}


def check_routing_priority(answer):
    checks = {
        "resubmission_route": norm_enum(answer.get("resubmission_route")) == "payment_integrity_correction",
        "priority": norm_enum(answer.get("priority")) == "standard",
    }
    return all(checks.values()), checks


def check_basis_source_precedence(answer):
    actual = norm_enum(audit_value(answer, "source_precedence"))
    expected = EXPECTED_BASIS_AUDIT["source_precedence"]
    return actual == expected, {"actual": actual, "expected": expected}


def check_basis_controlling_records(answer):
    actual = norm_lower_list(audit_value(answer, "controlling_record_ids"))
    expected = EXPECTED_BASIS_AUDIT["controlling_record_ids"]
    return actual == expected, {"actual": actual, "expected": expected}


def check_basis_precedence_record_order(answer):
    actual = norm_lower_list(audit_value(answer, "precedence_record_order"))
    expected = EXPECTED_BASIS_AUDIT["precedence_record_order"]
    return actual == expected, {"actual": actual, "expected": expected}


def check_basis_exception_records(answer):
    actual = norm_lower_list(audit_value(answer, "exception_record_ids"))
    return actual == EXPECTED_BASIS_AUDIT["exception_record_ids"], {
        "actual": actual,
        "expected": EXPECTED_BASIS_AUDIT["exception_record_ids"],
    }


CHECKS = {
    "identity": check_identity,
    "benchmark_workers_comp_context": check_benchmark_workers_comp_context,
    "totals": check_totals,
    "line_1_correction": check_line_1_correction,
    "line_2_modifier_denial": check_line_2_modifier_denial,
    "routing_priority": check_routing_priority,
    "basis_source_precedence": check_basis_source_precedence,
    "basis_precedence_record_order": check_basis_precedence_record_order,
    "basis_controlling_records": check_basis_controlling_records,
    "basis_exception_records": check_basis_exception_records,
}


def score_answer(answer, parse_error=None):
    total_weight = sum(weight for _, weight, _ in RUBRIC)
    points = []
    earned_weight = 0

    for point_id, weight, goal in RUBRIC:
        if parse_error:
            passed = False
            details = {"parse_error": parse_error}
        else:
            passed, details = CHECKS[point_id](answer)
        if passed:
            earned_weight += weight
        assigned_score = weight / total_weight
        points.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": assigned_score,
                "passed": bool(passed),
                "earned_score": assigned_score if passed else 0,
                "details": details,
            }
        )

    return {
        "score": earned_weight / total_weight,
        "points": points,
        "total_weight": total_weight,
    }


def main():
    default_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"
    candidate_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path
    answer, parse_error = load_candidate(candidate_path)
    result = score_answer(answer or {}, parse_error=parse_error)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
