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


def rows_by_supplier(payload):
    rows = payload.get("supplier_decisions")
    if not isinstance(rows, list):
        return {}
    return {row.get("supplier_id"): row for row in rows if isinstance(row, dict)}


def row_fields(payload, fields):
    rows = rows_by_supplier(payload)
    return {
        supplier_id: {field: rows.get(supplier_id, {}).get(field) for field in fields}
        for supplier_id in sorted(row.get("supplier_id") for row in EXPECTED["supplier_decisions"])
    }


def held_po_by_supplier(payload):
    rows = rows_by_supplier(payload)
    return {
        supplier_id: rows.get(supplier_id, {}).get("held_po_ids")
        for supplier_id in sorted(row.get("supplier_id") for row in EXPECTED["supplier_decisions"])
    }


def check_supplier_identity(pred):
    return row_fields(pred, ["supplier_id", "supplier_name"]) == row_fields(EXPECTED, ["supplier_id", "supplier_name"])


def check_incident_counts(pred):
    fields = ["recent_incident_count", "recent_rma_count", "severe_or_critical_count", "open_incident_count"]
    return row_fields(pred, fields) == row_fields(EXPECTED, fields)


def check_quality_status(pred):
    return row_fields(pred, ["quality_status"]) == row_fields(EXPECTED, ["quality_status"])


def check_incident_skus(pred):
    fields = ["affected_skus", "sample_incident_ids"]
    return norm(row_fields(pred, fields)) == norm(row_fields(EXPECTED, fields))


def check_decisions(pred):
    return row_fields(pred, ["decision"]) == row_fields(EXPECTED, ["decision"])


def check_po_holds(pred):
    return norm(pred.get("held_po_ids")) == norm(EXPECTED.get("held_po_ids")) and norm(
        held_po_by_supplier(pred)
    ) == norm(held_po_by_supplier(EXPECTED))


def check_summary(pred):
    return norm(pred.get("release_supplier_ids")) == norm(EXPECTED.get("release_supplier_ids")) and pred.get(
        "summary"
    ) == EXPECTED.get("summary")


SCORING_POINTS = [
    (
        "SP001_window",
        "Correct analysis window.",
        1,
        lambda pred: pred.get("analysis_window") == EXPECTED.get("analysis_window"),
    ),
    ("SP002_supplier_ids", "Correct reviewed supplier identities.", 2, check_supplier_identity),
    ("SP003_incident_counts", "Correct recent incident/RMA/severity/open counts.", 3, check_incident_counts),
    ("SP004_quality_status", "Correct supplier quality statuses.", 2, check_quality_status),
    ("SP005_incident_skus", "Correct affected SKU and sample incident sets.", 2, check_incident_skus),
    ("SP006_decisions", "Correct controlled replenishment decisions.", 3, check_decisions),
    ("SP007_po_holds", "Correct held PO ids.", 3, check_po_holds),
    ("SP008_summary", "Correct release suppliers and summary rollups.", 2, check_summary),
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
