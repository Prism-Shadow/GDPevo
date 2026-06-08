#!/usr/bin/env python3
import json
import sys
from pathlib import Path


EXPECTED = json.loads((Path(__file__).resolve().parents[1] / "output" / "answer.json").read_text(encoding="utf-8"))


def norm(value):
    if isinstance(value, list):
        return sorted((norm(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, dict):
        return {key: norm(value[key]) for key in sorted(value)}
    return value


def order_rows(payload):
    rows = payload.get("order_decisions")
    if not isinstance(rows, list):
        return {}
    return {row.get("order_id"): row for row in rows if isinstance(row, dict)}


def order_fields(payload, fields):
    rows = order_rows(payload)
    return {
        order_id: {field: rows.get(order_id, {}).get(field) for field in fields}
        for order_id in sorted(row.get("order_id") for row in EXPECTED["order_decisions"])
    }


def check_order_decisions(pred):
    return order_fields(pred, ["decision"]) == order_fields(EXPECTED, ["decision"])


def check_reason_codes(pred):
    fields = ["reason_codes", "risk_supplier_ids"]
    return norm(order_fields(pred, fields)) == norm(order_fields(EXPECTED, fields))


def check_replenishment_gaps(pred):
    return norm(pred.get("replenishment_gaps")) == norm(EXPECTED.get("replenishment_gaps"))


def check_incident_escalations(pred):
    return norm(pred.get("incident_escalations")) == norm(EXPECTED.get("incident_escalations"))


def check_priority_actions(pred):
    return norm(pred.get("priority_actions")) == norm(EXPECTED.get("priority_actions"))


def check_summary(pred):
    return pred.get("summary") == EXPECTED.get("summary")


def check_integration_sets(pred):
    return (
        set(order_rows(pred)) == set(order_rows(EXPECTED))
        and norm(order_fields(pred, ["shortage_skus", "risk_supplier_ids"]))
        == norm(order_fields(EXPECTED, ["shortage_skus", "risk_supplier_ids"]))
        and norm(pred.get("replenishment_gaps")) == norm(EXPECTED.get("replenishment_gaps"))
        and norm(pred.get("incident_escalations")) == norm(EXPECTED.get("incident_escalations"))
    )


SCORING_POINTS = [
    (
        "SP001_board_identity",
        "Correct board date and wave.",
        1,
        lambda pred: pred.get("board_date") == EXPECTED.get("board_date") and pred.get("wave") == EXPECTED.get("wave"),
    ),
    ("SP002_order_decisions", "Correct per-order decisions.", 3, check_order_decisions),
    ("SP003_reason_codes", "Correct reason codes and risk suppliers.", 3, check_reason_codes),
    ("SP004_shortages", "Correct replenishment gap lines.", 3, check_replenishment_gaps),
    ("SP005_escalations", "Correct incident escalation suppliers.", 2, check_incident_escalations),
    ("SP006_priority_actions", "Correct ranked priority actions.", 2, check_priority_actions),
    ("SP007_counts", "Correct summary counts.", 2, check_summary),
    ("SP008_integration", "Correct integrated decision, shortage, and incident sets.", 2, check_integration_sets),
]


def main():
    if len(sys.argv) != 2:
        print("usage: evaluate.py <prediction.json>", file=sys.stderr)
        return 2
    try:
        pred = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    except Exception as exc:
        total = sum(weight for _, _, weight, _ in SCORING_POINTS)
        print(
            json.dumps(
                {"score": 0.0, "earned_weight": 0, "total_weight": total, "error": str(exc), "scoring_points": []},
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    total = sum(weight for _, _, weight, _ in SCORING_POINTS)
    earned = 0
    results = []
    for point_id, goal, weight, check in SCORING_POINTS:
        try:
            matched = bool(check(pred))
        except Exception:
            matched = False
        if matched:
            earned += weight
        results.append({"id": point_id, "goal": goal, "weight": weight, "matched": matched})
    print(
        json.dumps(
            {
                "score": earned / total if total else 0,
                "earned_weight": earned,
                "total_weight": total,
                "scoring_points": results,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
