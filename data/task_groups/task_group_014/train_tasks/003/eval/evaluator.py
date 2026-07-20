#!/usr/bin/env python3
import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path


EXPECTED_LINES = [
    {
        "line_id": "CL-TR-003-1",
        "cpt_code": "78452",
        "modifier": "TC",
        "units": 1,
        "paid_amount": "608.00",
        "correct_allowed_amount": "760.00",
        "recovery_amount": "152.00",
        "disposition": "correct_upward",
    },
    {
        "line_id": "CL-TR-003-2",
        "cpt_code": "A9500",
        "modifier": None,
        "units": 2,
        "paid_amount": "288.00",
        "correct_allowed_amount": "360.00",
        "recovery_amount": "72.00",
        "disposition": "correct_upward",
    },
    {
        "line_id": "CL-TR-003-3",
        "cpt_code": "93016",
        "modifier": None,
        "units": 1,
        "paid_amount": "44.00",
        "correct_allowed_amount": "55.00",
        "recovery_amount": "11.00",
        "disposition": "correct_upward",
    },
]

EXPECTED_BASIS_AUDIT = {
    "source_precedence": "effective_benchmark_by_plan_modifier_and_date",
    "precedence_record_order": [
        "bm-tr-003-78452",
        "bm-tr-003-a9500",
        "bm-tr-003-93016",
        "bm-old-78452",
    ],
    "controlling_record_ids": [
        "cl-tr-003-1",
        "cl-tr-003-2",
        "cl-tr-003-3",
        "bm-tr-003-78452",
        "bm-tr-003-a9500",
        "bm-tr-003-93016",
    ],
    "exception_record_ids": ["bm-old-78452"],
}

RUBRIC = [
    ("identity", 1, "Correct claim, case, and authorization identity."),
    ("benchmark", 2, "Correct current benchmark source/version and stale source rejection."),
    ("totals", 3, "Correct paid total, correct allowed total, and recovery amount."),
    ("line_identity", 1, "Correct line-level CPT, modifier, units, and stable ordering."),
    ("line_amounts", 3, "Correct line-level paid, corrected allowed, recovery, and dispositions."),
    ("routing", 1, "Correct resubmission route and standard priority."),
    ("business_basis_audit", 1, "Correct business basis-audit source, controlling records, and exception records."),
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
    return text.lower() if text else None


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


def lower_string_list(value):
    if not isinstance(value, list):
        return None
    return [norm_text(item).lower() for item in value if norm_text(item) is not None]


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
        "claim_id": norm_id(answer.get("claim_id")) == "CLAIM-TR-003",
        "case_id": norm_id(answer.get("case_id")) == "CLAIM-TR-003",
        "auth_number": norm_id(answer.get("auth_number")) == "NPA-2404980",
    }
    return all(checks.values()), checks


def check_benchmark(answer):
    checks = {
        "benchmark_source": norm_text(answer.get("benchmark_source")) == "Northstar Commercial Imaging Schedule",
        "benchmark_version": norm_text(answer.get("benchmark_version")) == "2026Q2",
        "stale_source_rejected": norm_text(answer.get("stale_source_rejected")) == "Legacy Imaging Export",
    }
    return all(checks.values()), checks


def check_totals(answer):
    correct_allowed = get_first(answer, ["correct_allowed_total", "corrected_allowed_total", "allowed_total"])
    checks = {
        "paid_total": cents_equal(answer.get("paid_total"), "940.00"),
        "correct_allowed_total": cents_equal(correct_allowed, "1175.00"),
        "recovery_amount": cents_equal(answer.get("recovery_amount"), "235.00"),
    }
    return all(checks.values()), checks


def check_line_identity(answer):
    lines = get_lines(answer)
    checks = {
        "line_count": len(lines) == len(EXPECTED_LINES),
        "line_order": [norm_id(line.get("line_id")) if isinstance(line, dict) else None for line in lines]
        == [line["line_id"] for line in EXPECTED_LINES],
        "line_fields": {},
    }
    per_line_ok = True
    for idx, expected in enumerate(EXPECTED_LINES):
        candidate = lines[idx] if idx < len(lines) and isinstance(lines[idx], dict) else {}
        line_checks = {
            "line_id": norm_id(candidate.get("line_id")) == expected["line_id"],
            "cpt_code": norm_id(candidate.get("cpt_code")) == expected["cpt_code"],
            "modifier": norm_modifier(candidate.get("modifier")) == expected["modifier"],
            "units": as_int(candidate.get("units")) == expected["units"],
        }
        checks["line_fields"][expected["line_id"]] = line_checks
        per_line_ok = per_line_ok and all(line_checks.values())
    return checks["line_count"] and checks["line_order"] and per_line_ok, checks


def check_line_amounts(answer):
    lines = get_lines(answer)
    by_id = {
        norm_id(line.get("line_id")): line for line in lines if isinstance(line, dict) and norm_id(line.get("line_id"))
    }
    checks = {
        "exact_line_ids": set(by_id) == {line["line_id"] for line in EXPECTED_LINES},
        "line_amount_fields": {},
    }
    per_line_ok = True
    for expected in EXPECTED_LINES:
        candidate = by_id.get(expected["line_id"], {})
        correct_allowed = get_first(
            candidate, ["correct_allowed_amount", "corrected_allowed_amount", "allowed_amount"]
        )
        line_checks = {
            "paid_amount": cents_equal(candidate.get("paid_amount"), expected["paid_amount"]),
            "correct_allowed_amount": cents_equal(correct_allowed, expected["correct_allowed_amount"]),
            "recovery_amount": cents_equal(candidate.get("recovery_amount"), expected["recovery_amount"]),
            "disposition": norm_enum(candidate.get("disposition")) == expected["disposition"],
        }
        checks["line_amount_fields"][expected["line_id"]] = line_checks
        per_line_ok = per_line_ok and all(line_checks.values())
    return checks["exact_line_ids"] and per_line_ok, checks


def check_routing(answer):
    checks = {
        "resubmission_route": norm_enum(answer.get("resubmission_route")) == "payment_integrity_correction",
        "priority": norm_enum(answer.get("priority")) == "standard",
    }
    return all(checks.values()), checks


def check_basis_audit(answer):
    audit = answer.get("basis_audit") if isinstance(answer, dict) else None
    actual = {
        "source_precedence": norm_enum(audit.get("source_precedence")) if isinstance(audit, dict) else None,
        "precedence_record_order": lower_string_list(audit.get("precedence_record_order"))
        if isinstance(audit, dict)
        else None,
        "controlling_record_ids": lower_string_list(audit.get("controlling_record_ids"))
        if isinstance(audit, dict)
        else None,
        "exception_record_ids": lower_string_list(audit.get("exception_record_ids"))
        if isinstance(audit, dict)
        else None,
    }
    return actual == EXPECTED_BASIS_AUDIT, {"expected": EXPECTED_BASIS_AUDIT, "actual": actual}


CHECKS = {
    "identity": check_identity,
    "benchmark": check_benchmark,
    "totals": check_totals,
    "line_identity": check_line_identity,
    "line_amounts": check_line_amounts,
    "routing": check_routing,
    "business_basis_audit": check_basis_audit,
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
