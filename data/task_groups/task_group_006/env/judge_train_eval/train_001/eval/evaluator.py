#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "output" / "answer.json"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def rounded(value: Any) -> float | None:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def as_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item) for item in value}


def lines_by_sku(answer: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lines = answer.get("nomination_lines")
    if not isinstance(lines, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for line in lines:
        if isinstance(line, dict) and isinstance(line.get("sku"), str):
            result[line["sku"]] = line
    return result


def same_scalar_fields(actual: dict[str, Any], expected: dict[str, Any], fields: list[str]) -> bool:
    return all(actual.get(field) == expected.get(field) for field in fields)


def same_set_fields(actual: dict[str, Any], expected: dict[str, Any], fields: list[str]) -> bool:
    return all(as_set(actual.get(field)) == as_set(expected.get(field)) for field in fields)


def point(name: str, matched: bool, weight: int) -> dict[str, Any]:
    return {"name": name, "matched": bool(matched), "weight": weight}


def evaluate(prediction: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    pred_lines = lines_by_sku(prediction)
    gold_lines = lines_by_sku(gold)
    pred_summary = prediction.get("program_summary", {})
    gold_summary = gold.get("program_summary", {})
    pred_action = prediction.get("committee_action", {})
    gold_action = gold.get("committee_action", {})

    lmp_pred = pred_lines.get("LMP-228", {})
    lmp_gold = gold_lines["LMP-228"]
    drv_pred = pred_lines.get("DRV-AX17", {})
    drv_gold = gold_lines["DRV-AX17"]

    points = [
        point(
            "scope_and_as_of",
            prediction.get("task_id") == gold.get("task_id")
            and prediction.get("program_id") == gold.get("program_id")
            and prediction.get("as_of_date") == gold.get("as_of_date")
            and as_set(prediction.get("package_line_skus")) == as_set(gold.get("package_line_skus")),
            1,
        ),
        point(
            "program_budget_and_overall_readiness",
            isinstance(pred_summary, dict)
            and pred_summary.get("owner") == gold_summary.get("owner")
            and rounded(pred_summary.get("budget_headroom_usd")) == rounded(gold_summary.get("budget_headroom_usd"))
            and pred_summary.get("overall_readiness") == gold_summary.get("overall_readiness"),
            2,
        ),
        point(
            "lmp_supplier_commercial_and_decision",
            same_scalar_fields(
                lmp_pred,
                lmp_gold,
                [
                    "selected_supplier_id",
                    "nomination_decision",
                    "readiness_status",
                    "primary_requisition_id",
                    "commercial_basis_id",
                ],
            ),
            2,
        ),
        point(
            "drv_supplier_commercial_and_decision",
            same_scalar_fields(
                drv_pred,
                drv_gold,
                [
                    "selected_supplier_id",
                    "nomination_decision",
                    "readiness_status",
                    "primary_requisition_id",
                    "commercial_basis_id",
                ],
            ),
            2,
        ),
        point(
            "lmp_evidence_and_blockers",
            same_set_fields(
                lmp_pred,
                lmp_gold,
                ["package_po_ids", "receipt_evidence_ids", "invoice_exception_ids", "risk_event_ids", "blocker_codes"],
            ),
            2,
        ),
        point(
            "drv_evidence_and_blockers",
            same_set_fields(
                drv_pred,
                drv_gold,
                ["package_po_ids", "receipt_evidence_ids", "invoice_exception_ids", "risk_event_ids", "blocker_codes"],
            ),
            2,
        ),
        point(
            "committee_action",
            isinstance(pred_action, dict)
            and same_set_fields(
                pred_action,
                gold_action,
                ["nominate_now_supplier_ids", "conditional_supplier_ids", "hold_supplier_ids"],
            )
            and pred_action.get("next_owner") == gold_action.get("next_owner")
            and pred_action.get("send_to_committee") == gold_action.get("send_to_committee"),
            1,
        ),
    ]

    max_weight = sum(item["weight"] for item in points)
    earned = sum(item["weight"] for item in points if item["matched"])
    return {
        "score": earned / max_weight if max_weight else 0.0,
        "max_score": 1.0,
        "raw_score": earned,
        "raw_max_score": max_weight,
        "points": points,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"score": 0.0, "max_score": 1.0, "error": "usage: evaluator.py PREDICTION_JSON"}))
        return 2

    try:
        prediction = load_json(Path(sys.argv[1]))
        gold = load_json(GOLD_PATH)
        result = evaluate(prediction, gold)
    except Exception as exc:  # noqa: BLE001 - evaluator should report JSON on malformed submissions.
        result = {"score": 0.0, "max_score": 1.0, "error": str(exc), "points": []}

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
