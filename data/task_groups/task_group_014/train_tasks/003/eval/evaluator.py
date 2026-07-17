#!/usr/bin/env python3
import json
import sys
from pathlib import Path


CASE_IDS = ["MED00001", "MED00002", "MED00003", "MED00004"]


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def case_map(doc):
    cases = doc.get("medication_cases", [])
    if not isinstance(cases, list):
        return {}
    return {case.get("med_case_id"): case for case in cases if isinstance(case, dict)}


def get_case_fields(doc, selectors):
    mapped = case_map(doc)
    result = {}
    for case_id in CASE_IDS:
        case = mapped.get(case_id, {})
        values = {}
        for key, path in selectors.items():
            node = case
            for part in path:
                node = node.get(part) if isinstance(node, dict) else None
            values[key] = node
        result[case_id] = values
    return result


def normalize_lists(obj):
    if isinstance(obj, list):
        if all(not isinstance(item, (dict, list)) for item in obj):
            return sorted(obj)
        return [normalize_lists(item) for item in obj]
    if isinstance(obj, dict):
        return {key: normalize_lists(value) for key, value in obj.items()}
    return obj


def add_point(points, point_id, description, weight, expected, actual):
    passed = normalize_lists(actual) == normalize_lists(expected)
    points.append(
        {
            "id": point_id,
            "description": description,
            "weight": weight,
            "earned": weight if passed else 0,
            "passed": passed,
            "expected": expected,
            "actual": actual,
        }
    )


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"score": 0, "max_score": 1, "error": "usage: evaluator.py prediction.json"}))
        return 2

    prediction_path = Path(sys.argv[1])
    expected_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"

    try:
        expected = load_json(expected_path)
        actual = load_json(prediction_path)
    except Exception as exc:
        print(json.dumps({"score": 0, "max_score": 1, "error": str(exc)}))
        return 1

    points = []

    add_point(
        points,
        "SP001",
        "payer appeal eligibility status by medication case",
        3,
        get_case_fields(expected, {"eligibility_status": ["appeal", "eligibility_status"]}),
        get_case_fields(actual, {"eligibility_status": ["appeal", "eligibility_status"]}),
    )
    add_point(
        points,
        "SP002",
        "missing or failed drug-policy requirements by medication case",
        2,
        get_case_fields(expected, {"missing_policy_requirements": ["appeal", "missing_policy_requirements"]}),
        get_case_fields(actual, {"missing_policy_requirements": ["appeal", "missing_policy_requirements"]}),
    )
    add_point(
        points,
        "SP003",
        "expedited appeal classification by medication case",
        2,
        get_case_fields(expected, {"expedited_classification": ["appeal", "expedited_classification"]}),
        get_case_fields(actual, {"expedited_classification": ["appeal", "expedited_classification"]}),
    )
    add_point(
        points,
        "SP004",
        "manufacturer assistance eligibility, program, and blocking reasons",
        2,
        get_case_fields(
            expected,
            {
                "program_id": ["assistance", "program_id"],
                "eligibility_status": ["assistance", "eligibility_status"],
                "blocking_reasons": ["assistance", "blocking_reasons"],
            },
        ),
        get_case_fields(
            actual,
            {
                "program_id": ["assistance", "program_id"],
                "eligibility_status": ["assistance", "eligibility_status"],
                "blocking_reasons": ["assistance", "blocking_reasons"],
            },
        ),
    )
    add_point(
        points,
        "SP005",
        "required assistance form and program owner",
        1,
        get_case_fields(
            expected, {"program_owner": ["assistance", "program_owner"], "form_name": ["assistance", "form_name"]}
        ),
        get_case_fields(
            actual, {"program_owner": ["assistance", "program_owner"], "form_name": ["assistance", "form_name"]}
        ),
    )
    add_point(
        points,
        "SP006",
        "separate appeal path from assistance path with correct next steps",
        2,
        get_case_fields(
            expected,
            {
                "appeal_next_step": ["appeal", "next_step"],
                "assistance_next_step": ["assistance", "next_step"],
                "path_separation": ["path_separation"],
            },
        ),
        get_case_fields(
            actual,
            {
                "appeal_next_step": ["appeal", "next_step"],
                "assistance_next_step": ["assistance", "next_step"],
                "path_separation": ["path_separation"],
            },
        ),
    )
    add_point(
        points,
        "SP007",
        "appeal filing deadline and timeliness status",
        1,
        get_case_fields(
            expected,
            {"filing_deadline": ["appeal", "filing_deadline"], "deadline_status": ["appeal", "deadline_status"]},
        ),
        get_case_fields(
            actual,
            {"filing_deadline": ["appeal", "filing_deadline"], "deadline_status": ["appeal", "deadline_status"]},
        ),
    )
    add_point(
        points,
        "SP008",
        "appeal and assistance summary totals",
        1,
        {"appeal_summary": expected.get("appeal_summary"), "assistance_summary": expected.get("assistance_summary")},
        {"appeal_summary": actual.get("appeal_summary"), "assistance_summary": actual.get("assistance_summary")},
    )

    earned = sum(point["earned"] for point in points)
    max_raw = sum(point["weight"] for point in points)
    print(
        json.dumps(
            {
                "score": earned / max_raw if max_raw else 0,
                "max_score": 1,
                "earned_raw": earned,
                "max_raw": max_raw,
                "points": points,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
