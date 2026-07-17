#!/usr/bin/env python3
"""Exact-match evaluator for task_group_019 train_004."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_DECISIONS = {
    "CA-2026-0013": {
        "determination": "HOLD",
        "reason_codes": ["ADVERSE_PRIOR_REGISTRATION", "UNRESOLVED_PENALTY"],
        "manual_followup_required": True,
    },
    "CA-2026-0014": {
        "determination": "HOLD",
        "reason_codes": ["BOND_CANCELLED"],
        "manual_followup_required": True,
    },
    "CA-2026-0015": {
        "determination": "APPROVE",
        "reason_codes": ["NO_DEFICIENCY"],
        "manual_followup_required": False,
    },
    "CA-2026-0016": {
        "determination": "HOLD",
        "reason_codes": ["INSURANCE_VERIFY"],
        "manual_followup_required": True,
    },
    "CA-2026-0017": {
        "determination": "HOLD",
        "reason_codes": ["FIELD_NOTE_HOLD"],
        "manual_followup_required": True,
    },
    "CA-2026-0018": {
        "determination": "HOLD",
        "reason_codes": ["BOND_SHORTFALL"],
        "manual_followup_required": True,
    },
    "CA-2026-0019": {
        "determination": "HOLD",
        "reason_codes": ["INSURANCE_VERIFY", "UNRESOLVED_PENALTY"],
        "manual_followup_required": True,
    },
    "CA-2026-0020": {
        "determination": "HOLD",
        "reason_codes": ["UNRESOLVED_PENALTY"],
        "manual_followup_required": True,
    },
    "CA-2026-0021": {
        "determination": "HOLD",
        "reason_codes": ["EXPERIENCE_VERIFY", "UNRESOLVED_PENALTY"],
        "manual_followup_required": True,
    },
    "CA-2026-0022": {
        "determination": "HOLD",
        "reason_codes": ["CORRESPONDENCE_HOLD", "FINANCIAL_STATEMENT_MISSING"],
        "manual_followup_required": True,
    },
    "CA-2026-0023": {
        "determination": "APPROVE",
        "reason_codes": ["NO_DEFICIENCY"],
        "manual_followup_required": False,
    },
}

EXPECTED_ORDER = list(EXPECTED_DECISIONS)

EXPECTED_MANUAL = {
    "CA-2026-0013": ["PRIOR_REGISTRATION_FILE_REVIEW", "PENALTY_LEDGER_REVIEW"],
    "CA-2026-0014": ["BOND_REPLACEMENT_REQUIRED"],
    "CA-2026-0016": ["CARRIER_VERIFICATION_REQUIRED"],
    "CA-2026-0017": ["INSPECTOR_CLEARANCE_REQUIRED"],
    "CA-2026-0018": ["BOND_INCREASE_REQUIRED"],
    "CA-2026-0019": ["INSURANCE_REPLACEMENT_REQUIRED", "PENALTY_LEDGER_REVIEW"],
    "CA-2026-0020": ["PENALTY_LEDGER_REVIEW"],
    "CA-2026-0021": ["PENALTY_LEDGER_REVIEW", "EXPERIENCE_DOCUMENTATION_REQUIRED"],
    "CA-2026-0022": ["FINANCIAL_STATEMENT_REQUIRED", "MATERIAL_CORRESPONDENCE_REVIEW"],
}

EXPECTED_SUMMARY = {
    "total_applications": 11,
    "determination_counts": {"APPROVE": 2, "HOLD": 9, "DENY": 0},
    "q1_2026_bulletin_changed_application_ids": ["CA-2026-0018"],
    "q1_2026_bulletin_changed_count": 1,
    "manual_followup_count": 9,
}


def load_prediction(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:  # noqa: BLE001 - evaluator should report any load failure.
        return None, f"Could not load JSON: {exc}"


def decision_map(prediction: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = prediction.get("application_decisions")
    if not isinstance(rows, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("application_id"), str):
            result[row["application_id"]] = row
    return result


def manual_map(prediction: dict[str, Any]) -> dict[str, list[str]]:
    rows = prediction.get("manual_followup")
    if not isinstance(rows, list):
        return {}
    result: dict[str, list[str]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("application_id"), str):
            continue
        codes = row.get("followup_reason_codes")
        result[row["application_id"]] = codes if isinstance(codes, list) else []
    return result


def exact_decision(row: dict[str, Any] | None, expected: dict[str, Any]) -> bool:
    return (
        isinstance(row, dict)
        and row.get("determination") == expected["determination"]
        and row.get("reason_codes") == expected["reason_codes"]
        and row.get("manual_followup_required") is expected["manual_followup_required"]
    )


def add_point(points: list[dict[str, Any]], point_id: str, goal: str, weight: int, matched: bool) -> None:
    points.append(
        {
            "id": point_id,
            "goal": goal,
            "weight": weight,
            "earned_weight": weight if matched else 0,
            "matched": matched,
        }
    )


def evaluate(prediction: Any) -> dict[str, Any]:
    points: list[dict[str, Any]] = []
    if not isinstance(prediction, dict):
        add_point(points, "SP0", "Prediction is a JSON object.", 1, False)
        return score(points)

    decisions = decision_map(prediction)
    manual = manual_map(prediction)
    rows = prediction.get("application_decisions")
    row_order = (
        [row.get("application_id") for row in rows]
        if isinstance(rows, list) and all(isinstance(row, dict) for row in rows)
        else []
    )

    add_point(
        points,
        "SP1",
        "Target batch and complete application decision list are present in application_id order.",
        1,
        prediction.get("batch_id") == "HS-2026-Q1B" and row_order == EXPECTED_ORDER,
    )

    add_point(
        points,
        "SP2",
        "Adverse prior registration and unresolved-penalty holds are correctly classified.",
        2,
        all(
            exact_decision(decisions.get(app_id), EXPECTED_DECISIONS[app_id])
            for app_id in ["CA-2026-0013", "CA-2026-0020", "CA-2026-0021"]
        ),
    )

    add_point(
        points,
        "SP3",
        "Cancelled-bond and short-bond applications receive the correct hold reasons.",
        2,
        all(
            exact_decision(decisions.get(app_id), EXPECTED_DECISIONS[app_id])
            for app_id in ["CA-2026-0014", "CA-2026-0018"]
        ),
    )

    add_point(
        points,
        "SP4",
        "Insurance verification and replacement cases are correctly held.",
        2,
        all(
            exact_decision(decisions.get(app_id), EXPECTED_DECISIONS[app_id])
            for app_id in ["CA-2026-0016", "CA-2026-0019"]
        ),
    )

    add_point(
        points,
        "SP5",
        "Field-note and correspondence/documentation holds are correctly classified.",
        2,
        all(
            exact_decision(decisions.get(app_id), EXPECTED_DECISIONS[app_id])
            for app_id in ["CA-2026-0017", "CA-2026-0022"]
        ),
    )

    add_point(
        points,
        "SP6",
        "Clean approval set is exactly the two no-deficiency applications.",
        2,
        all(
            exact_decision(decisions.get(app_id), EXPECTED_DECISIONS[app_id])
            for app_id in ["CA-2026-0015", "CA-2026-0023"]
        )
        and sorted(app_id for app_id, row in decisions.items() if row.get("determination") == "APPROVE")
        == ["CA-2026-0015", "CA-2026-0023"],
    )

    add_point(
        points,
        "SP7",
        "Manual follow-up IDs and controlled follow-up reasons match the review queue.",
        3,
        manual == EXPECTED_MANUAL,
    )

    add_point(
        points,
        "SP8",
        "Rule-change summary counts and Q1 2026 bulletin-changed application set are correct.",
        2,
        prediction.get("rule_change_summary") == EXPECTED_SUMMARY,
    )

    return score(points)


def score(points: list[dict[str, Any]]) -> dict[str, Any]:
    total = sum(point["weight"] for point in points)
    earned = sum(point["earned_weight"] for point in points)
    return {
        "score": earned / total if total else 0.0,
        "earned_weight": earned,
        "total_weight": total,
        "scoring_points": points,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: evaluator.py <prediction.json>", file=sys.stderr)
        return 2
    prediction, error = load_prediction(Path(argv[1]))
    if error is not None:
        result = score(
            [
                {
                    "id": "SP0",
                    "goal": error,
                    "weight": 1,
                    "earned_weight": 0,
                    "matched": False,
                }
            ]
        )
    else:
        result = evaluate(prediction)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
