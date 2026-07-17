#!/usr/bin/env python3
"""Atomic weighted evaluator for test_003."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable


EXPECTED = {
    "movement_row_id": "IMR-0000110",
    "movement_id": "MOV-0000110",
    "sku": "SKU-00463",
    "old_quantity_each": -800,
    "new_quantity_each": -40,
    "old_uom_multiplier": 20,
    "new_uom_multiplier": 1,
    "affected_business_rows": 1,
    "audit_rows": 1,
    "correction_status": "APPLIED",
    "pre_available_units": 73,
    "post_available_units": 833,
    "available_units_delta": 760,
    "stockout_risk_sku_ids": [
        "SKU-00413",
        "SKU-00415",
        "SKU-00418",
        "SKU-00466",
        "SKU-00467",
        "SKU-00468",
        "SKU-00471",
        "SKU-00472",
        "SKU-00473",
    ],
    "highest_risk_sku_id": "SKU-00473",
    "stockout_status": "CONTROLLED",
}

POINT_SPECS = [
    ("SP001", "Correct faulty movement-row, movement, and SKU identification.", 3),
    ("SP002", "Correct old and new canonical quantity and UOM multiplier.", 3),
    ("SP003", "Correct guarded business-row, audit-row, and correction-status outcome.", 2),
    ("SP004", "Correct pre-correction available units for the corrected SKU.", 2),
    ("SP005", "Correct post-correction available units and availability delta.", 3),
    ("SP006", "Correct exact ordered post-correction stockout-risk SKU set.", 3),
    ("SP007", "Correct highest-risk SKU identifier.", 2),
    ("SP008", "Correct post-correction stockout status classification.", 1),
]
TOTAL_WEIGHT = sum(weight for _, _, weight in POINT_SPECS)
MISSING = object()


def strict_json_load(path_text: str) -> dict[str, Any] | None:
    if not path_text:
        return None
    try:
        text = Path(path_text).read_text(encoding="utf-8")

        def reject_constant(value: str) -> None:
            raise ValueError(f"invalid JSON constant: {value}")

        value = json.loads(text, parse_constant=reject_constant)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def nested(candidate: dict[str, Any], *path: str) -> Any:
    value: Any = candidate
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return MISSING
        value = value[key]
    return value


def shown(value: Any) -> str:
    if value is MISSING:
        return "<missing>"
    try:
        return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return f"<{type(value).__name__}>"


def is_integer(value: Any, expected: int) -> bool:
    return type(value) is int and value == expected


def is_string(value: Any, expected: str) -> bool:
    return type(value) is str and value == expected


def check_target(candidate: dict[str, Any]) -> tuple[bool, str]:
    actual = {
        "movement_row_id": nested(candidate, "correction_target", "movement_row_id"),
        "movement_id": nested(candidate, "correction_target", "movement_id"),
        "sku": nested(candidate, "correction_target", "sku"),
    }
    passed = all(is_string(actual[key], EXPECTED[key]) for key in actual)
    if passed:
        return True, "All faulty movement and SKU identifiers matched."
    return False, (
        "Expected movement_row_id=IMR-0000110, movement_id=MOV-0000110, "
        f"sku=SKU-00463; received {shown(actual)}."
    )


def check_canonical_values(candidate: dict[str, Any]) -> tuple[bool, str]:
    actual = {
        "old_quantity_each": nested(candidate, "correction_target", "canonical_quantity_each", "old"),
        "new_quantity_each": nested(candidate, "correction_target", "canonical_quantity_each", "new"),
        "old_uom_multiplier": nested(candidate, "correction_target", "canonical_uom_multiplier", "old"),
        "new_uom_multiplier": nested(candidate, "correction_target", "canonical_uom_multiplier", "new"),
    }
    passed = all(is_integer(actual[key], EXPECTED[key]) for key in actual)
    if passed:
        return True, "Both old/new canonical quantity and multiplier pairs matched."
    return False, (
        "Expected quantity -800 -> -40 and multiplier 20 -> 1; "
        f"received {shown(actual)}."
    )


def check_mutation(candidate: dict[str, Any]) -> tuple[bool, str]:
    business_rows = nested(candidate, "mutation_result", "affected_business_rows")
    audit_rows = nested(candidate, "mutation_result", "audit_rows")
    status = nested(candidate, "mutation_result", "correction_status")
    passed = (
        is_integer(business_rows, EXPECTED["affected_business_rows"])
        and is_integer(audit_rows, EXPECTED["audit_rows"])
        and is_string(status, EXPECTED["correction_status"])
    )
    if passed:
        return True, "One business row, one audit row, and APPLIED status all matched."
    return False, (
        "Expected affected_business_rows=1, audit_rows=1, correction_status=APPLIED; "
        f"received rows={shown(business_rows)}, audit={shown(audit_rows)}, status={shown(status)}."
    )


def check_pre_available(candidate: dict[str, Any]) -> tuple[bool, str]:
    actual = nested(candidate, "availability_reconciliation", "pre_correction_available_units")
    passed = is_integer(actual, EXPECTED["pre_available_units"])
    if passed:
        return True, "Pre-correction available units matched integer 73."
    return False, f"Expected pre-correction available units 73; received {shown(actual)}."


def check_post_available(candidate: dict[str, Any]) -> tuple[bool, str]:
    post = nested(candidate, "availability_reconciliation", "post_correction_available_units")
    delta = nested(candidate, "availability_reconciliation", "available_units_delta")
    passed = (
        is_integer(post, EXPECTED["post_available_units"])
        and is_integer(delta, EXPECTED["available_units_delta"])
    )
    if passed:
        return True, "Post-correction available units and delta both matched."
    return False, (
        "Expected post-correction available units 833 and delta 760; "
        f"received post={shown(post)}, delta={shown(delta)}."
    )


def check_risk_set(candidate: dict[str, Any]) -> tuple[bool, str]:
    actual = nested(candidate, "stockout_analysis", "stockout_risk_sku_ids")
    expected = EXPECTED["stockout_risk_sku_ids"]
    valid = isinstance(actual, list) and all(type(item) is str for item in actual)
    unique = valid and len(actual) == len(set(actual))
    passed = unique and actual == expected
    if passed:
        return True, "The exact unique nine-SKU risk set matched in ascending order."
    return False, (
        "Expected the exact unique nine-SKU risk list in ascending order; "
        f"received {shown(actual)}."
    )


def check_highest_risk(candidate: dict[str, Any]) -> tuple[bool, str]:
    actual = nested(candidate, "stockout_analysis", "highest_risk_sku_id")
    passed = is_string(actual, EXPECTED["highest_risk_sku_id"])
    if passed:
        return True, "Highest-risk SKU matched SKU-00473."
    return False, f"Expected highest-risk SKU SKU-00473; received {shown(actual)}."


def check_stockout_status(candidate: dict[str, Any]) -> tuple[bool, str]:
    actual = nested(candidate, "stockout_analysis", "stockout_status")
    passed = is_string(actual, EXPECTED["stockout_status"])
    if passed:
        return True, "Post-correction stockout status matched CONTROLLED."
    return False, f"Expected stockout status CONTROLLED; received {shown(actual)}."


CHECKS: dict[str, Callable[[dict[str, Any]], tuple[bool, str]]] = {
    "SP001": check_target,
    "SP002": check_canonical_values,
    "SP003": check_mutation,
    "SP004": check_pre_available,
    "SP005": check_post_available,
    "SP006": check_risk_set,
    "SP007": check_highest_risk,
    "SP008": check_stockout_status,
}


def evaluate(candidate: dict[str, Any] | None) -> dict[str, Any]:
    points: list[dict[str, Any]] = []
    earned_weight = 0
    for point_id, goal, weight in POINT_SPECS:
        assigned_score = weight / TOTAL_WEIGHT
        if candidate is None:
            passed = False
            details = "Candidate must be a readable JSON object."
        else:
            passed, details = CHECKS[point_id](candidate)
        if passed:
            earned_weight += weight
        points.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": assigned_score,
                "passed": passed,
                "earned_score": assigned_score if passed else 0.0,
                "details": details,
            }
        )
    return {
        "score": earned_weight / TOTAL_WEIGHT,
        "total_weight": TOTAL_WEIGHT,
        "points": points,
    }


def main() -> None:
    candidate_path = sys.argv[1] if len(sys.argv) == 2 else ""
    print(json.dumps(evaluate(strict_json_load(candidate_path)), ensure_ascii=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
