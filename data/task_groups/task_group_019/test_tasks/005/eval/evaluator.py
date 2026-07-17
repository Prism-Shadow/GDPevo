#!/usr/bin/env python3
"""Evaluator for task_group_019 test_005."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


POINTS = [
    {
        "id": "SP001",
        "weight": 1,
        "goal": "Renewal release metadata and post-boundary exclusion count are exact.",
    },
    {
        "id": "SP002",
        "weight": 2,
        "goal": "Top-two renewal queue cases are in the expected order.",
    },
    {
        "id": "SP003",
        "weight": 3,
        "goal": "Core board-review renewal membership contains the six strongest cases.",
    },
    {
        "id": "SP004",
        "weight": 2,
        "goal": "ALERT, fine, and shared-address manual-review tail cases are exact.",
    },
    {
        "id": "SP005",
        "weight": 2,
        "goal": "Renewal queue method flags for match and label counts are exact.",
    },
    {
        "id": "SP006",
        "weight": 2,
        "goal": "Successor premises target and risk counts are exact.",
    },
    {
        "id": "SP007",
        "weight": 2,
        "goal": "Successor recommendation and verification gaps are exact.",
    },
    {
        "id": "SP008",
        "weight": 2,
        "goal": "Successor standard obligations and premises controls are exact.",
    },
    {
        "id": "SP009",
        "weight": 2,
        "goal": "First-90-day successor inspection checks are exact.",
    },
]


CORE_BOARD = {
    "LIC-RV-2026-0107",
    "LIC-RV-2026-0134",
    "LIC-RV-2026-0112",
    "LIC-RV-2026-0144",
    "LIC-RV-2026-0128",
    "LIC-RV-2026-0138",
}
TAIL_CASES = {
    "LIC-RV-2026-0105",
    "LIC-RV-2026-0110",
    "LIC-RV-2026-0154",
    "LIC-RV-2026-0106",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def as_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def as_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def sorted_strings(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    return sorted(str(item) for item in value)


def queue(doc: dict[str, Any]) -> list[dict[str, Any]]:
    value = doc.get("queue")
    return value if isinstance(value, list) else []


def by_id(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in queue(doc):
        if isinstance(item, dict) and isinstance(item.get("license_id"), str):
            result[item["license_id"]] = item
    return result


def by_rank(doc: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for item in queue(doc):
        if not isinstance(item, dict):
            continue
        rank = to_int(item.get("rank"))
        if rank is not None and rank not in result:
            result[rank] = item
    return result


def ids(doc: dict[str, Any]) -> set[str]:
    return {
        item["license_id"] for item in queue(doc) if isinstance(item, dict) and isinstance(item.get("license_id"), str)
    }


def ranked_ids(doc: dict[str, Any], start: int, end: int) -> list[str | None]:
    ranked = by_rank(doc)
    return [as_str(ranked.get(rank, {}).get("license_id")) for rank in range(start, end + 1)]


def flags(doc: dict[str, Any]) -> dict[str, Any]:
    value = doc.get("method_flags")
    return value if isinstance(value, dict) else {}


def metadata(doc: dict[str, Any]) -> dict[str, Any]:
    f = flags(doc)
    return {
        "release_batch": as_str(f.get("release_batch")),
        "release_boundary": as_str(f.get("release_boundary")),
        "queue_size": to_int(f.get("queue_size")),
        "excluded_post_boundary_count": to_int(f.get("excluded_post_boundary_count")),
        "post_boundary_exclusion_applied": as_bool(f.get("post_boundary_exclusion_applied")),
        "shared_address_records_not_spread": as_bool(f.get("shared_address_records_not_spread")),
    }


def count_flags(doc: dict[str, Any]) -> dict[str, Any]:
    f = flags(doc)
    return {
        "exact_match_count": to_int(f.get("exact_match_count")),
        "close_match_count": to_int(f.get("close_match_count")),
        "shared_address_manual_count": to_int(f.get("shared_address_manual_count")),
        "board_review_count": to_int(f.get("board_review_count")),
        "manual_fine_check_count": to_int(f.get("manual_fine_check_count")),
        "manual_ALERT_check_count": to_int(f.get("manual_ALERT_check_count")),
        "additional_record_check_count": to_int(f.get("additional_record_check_count")),
    }


def row_core(doc: dict[str, Any], license_id: str) -> dict[str, Any]:
    row = by_id(doc).get(license_id, {})
    return {
        "facility_name": as_str(row.get("facility_name")),
        "match_confidence": as_str(row.get("match_confidence")),
        "violation_count_used": to_int(row.get("violation_count_used")),
        "most_recent_date_used": as_str(row.get("most_recent_date_used")),
        "next_step_label": as_str(row.get("next_step_label")),
    }


def successor(doc: dict[str, Any]) -> dict[str, Any]:
    value = doc.get("successor_premises_review")
    return value if isinstance(value, dict) else {}


def risk(doc: dict[str, Any]) -> dict[str, Any]:
    value = successor(doc).get("risk_assessment")
    return value if isinstance(value, dict) else {}


def successor_target_risk(doc: dict[str, Any]) -> dict[str, Any]:
    s = successor(doc)
    r = risk(doc)
    return {
        "review_month": as_str(s.get("review_month")),
        "application_id": as_str(s.get("application_id")),
        "premises_id": as_str(s.get("premises_id")),
        "dba": as_str(s.get("dba")),
        "same_premises_basis": as_str(r.get("same_premises_basis")),
        "prior_licensee": as_str(r.get("prior_licensee")),
        "prior_incident_level": as_str(r.get("prior_incident_level")),
        "incident_count": to_int(r.get("incident_count")),
        "unresolved_incident_count": to_int(r.get("unresolved_incident_count")),
        "high_severity_incident_count": to_int(r.get("high_severity_incident_count")),
        "unresolved_incident_ids": sorted_strings(r.get("unresolved_incident_ids")),
        "high_severity_incident_ids": sorted_strings(r.get("high_severity_incident_ids")),
        "settlement_posture": as_str(r.get("settlement_posture")),
        "successor_risk_classification": as_str(r.get("successor_risk_classification")),
        "overall_risk": as_str(r.get("overall_risk")),
        "current_premises_specific_control_count": to_int(r.get("current_premises_specific_control_count")),
        "standard_obligations_kept_separate": as_bool(r.get("standard_obligations_kept_separate")),
    }


def map_by_key(value: Any, key: str) -> dict[str, dict[str, Any]] | None:
    if not isinstance(value, list):
        return None
    result: dict[str, dict[str, Any]] = {}
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get(key), str):
            return None
        if item[key] in result:
            return None
        result[item[key]] = item
    return result


def gaps(doc: dict[str, Any]) -> dict[str, Any] | None:
    items = map_by_key(successor(doc).get("verification_gaps"), "gap_code")
    if items is None:
        return None
    return {
        code: {"source_ids": sorted_strings(item.get("source_ids")), "status": as_str(item.get("status"))}
        for code, item in sorted(items.items())
    }


def recommendation_and_gaps(doc: dict[str, Any]) -> dict[str, Any]:
    s = successor(doc)
    return {
        "recommendation": as_str(s.get("recommendation")),
        "follow_up_required": as_bool(s.get("follow_up_required")),
        "verification_gaps": gaps(doc),
    }


def standards(doc: dict[str, Any]) -> dict[str, Any] | None:
    items = map_by_key(successor(doc).get("standard_obligations"), "obligation_code")
    if items is None:
        return None
    return {
        code: {
            "source_obligation_id": as_str(item.get("source_obligation_id")),
            "evidence_required": as_str(item.get("evidence_required")),
        }
        for code, item in sorted(items.items())
    }


def controls(doc: dict[str, Any]) -> dict[str, Any] | None:
    items = map_by_key(successor(doc).get("premises_specific_controls"), "control_code")
    if items is None:
        return None
    return {
        code: {
            "source_ids": sorted_strings(item.get("source_ids")),
            "evidence_required": as_str(item.get("evidence_required")),
            "first_90_day_check": as_str(item.get("first_90_day_check")),
        }
        for code, item in sorted(items.items())
    }


def checks(doc: dict[str, Any]) -> list[dict[str, Any]] | None:
    value = successor(doc).get("first_90_day_checks")
    if not isinstance(value, list):
        return None
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            return None
        normalized.append(
            {
                "check_rank": to_int(item.get("check_rank")),
                "check_code": as_str(item.get("check_code")),
                "source_ids": sorted_strings(item.get("source_ids")),
                "timing": as_str(item.get("timing")),
            }
        )
    return sorted(normalized, key=lambda item: (item["check_rank"] is None, item["check_rank"]))


def check_point(point_id: str, pred: dict[str, Any], ans: dict[str, Any]) -> tuple[bool, str]:
    pred_ids = ids(pred)

    if point_id == "SP001":
        passed = metadata(pred) == metadata(ans)
        return passed, "metadata matches" if passed else "metadata differs"

    if point_id == "SP002":
        passed = ranked_ids(pred, 1, 2) == ranked_ids(ans, 1, 2)
        return passed, "top-two ranks match" if passed else "top-two ranks differ"

    if point_id == "SP003":
        passed = CORE_BOARD.issubset(pred_ids) and all(
            row_core(pred, item)["next_step_label"] == row_core(ans, item)["next_step_label"] for item in CORE_BOARD
        )
        return passed, "core board-review cases match" if passed else "core board-review cases differ"

    if point_id == "SP004":
        passed = TAIL_CASES.issubset(pred_ids) and all(
            row_core(pred, item) == row_core(ans, item) for item in TAIL_CASES
        )
        return passed, "tail cases match" if passed else "tail cases differ"

    if point_id == "SP005":
        passed = count_flags(pred) == count_flags(ans)
        return passed, "method count flags match" if passed else "method count flags differ"

    if point_id == "SP006":
        passed = successor_target_risk(pred) == successor_target_risk(ans)
        return passed, "successor target and risk match" if passed else "successor target or risk differs"

    if point_id == "SP007":
        passed = recommendation_and_gaps(pred) == recommendation_and_gaps(ans)
        return (
            passed,
            "successor recommendation and gaps match" if passed else "successor recommendation or gaps differ",
        )

    if point_id == "SP008":
        passed = {"standard_obligations": standards(pred), "premises_specific_controls": controls(pred)} == {
            "standard_obligations": standards(ans),
            "premises_specific_controls": controls(ans),
        }
        return (
            passed,
            "successor obligations and controls match" if passed else "successor obligations or controls differ",
        )

    if point_id == "SP009":
        passed = checks(pred) == checks(ans)
        return passed, "first-90-day checks match" if passed else "first-90-day checks differ"

    return False, "unknown scoring point"


def evaluate(pred: dict[str, Any], ans: dict[str, Any]) -> dict[str, Any]:
    total_weight = sum(int(point["weight"]) for point in POINTS)
    earned = 0
    results = []
    for point in POINTS:
        passed, message = check_point(str(point["id"]), pred, ans)
        weight = int(point["weight"])
        if passed:
            earned += weight
        results.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": weight,
                "passed": passed,
                "earned_weight": weight if passed else 0,
                "message": message,
            }
        )
    return {
        "score": round(earned / total_weight, 6),
        "earned_weight": earned,
        "total_weight": total_weight,
        "points": results,
    }


def main() -> int:
    if len(sys.argv) != 3:
        print(
            json.dumps(
                {"score": 0, "error": "usage: evaluator.py <prediction.json> <answer.json>", "points": []}, indent=2
            )
        )
        return 2
    try:
        pred = load_json(Path(sys.argv[1]))
        ans = load_json(Path(sys.argv[2]))
    except Exception as exc:
        print(json.dumps({"score": 0, "error": f"json_load_failed: {exc}", "points": []}, indent=2))
        return 1
    if not isinstance(pred, dict) or not isinstance(ans, dict):
        print(json.dumps({"score": 0, "error": "prediction and answer must be JSON objects", "points": []}, indent=2))
        return 1
    print(json.dumps(evaluate(pred, ans), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
