#!/usr/bin/env python3
import json
import sys
from pathlib import Path


CASE_IDS = ["MED00005", "MED00006", "MED00007", "MED00008"]


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize(value):
    if isinstance(value, list):
        if all(not isinstance(item, (dict, list)) for item in value):
            return sorted(value)
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(val) for key, val in value.items()}
    return value


def case_map(document):
    rows = document.get("case_actions", [])
    if not isinstance(rows, list):
        return {}
    return {row.get("med_case_id"): row for row in rows if isinstance(row, dict)}


def value_at(node, path):
    current = node
    for part in path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def selected_case_fields(document, selectors):
    mapped = case_map(document)
    results = {}
    for case_id in CASE_IDS:
        row = mapped.get(case_id, {})
        results[case_id] = {name: value_at(row, path) for name, path in selectors.items()}
    return results


def add_point(points, point_id, description, weight, expected, actual):
    passed = normalize(expected) == normalize(actual)
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
        print(
            json.dumps({"score": 0.0, "max_score": 1.0, "error": "Usage: evaluator.py <candidate.json>", "points": []})
        )
        return 2

    try:
        expected = load_json(Path(__file__).resolve().parents[1] / "output" / "answer.json")
        actual = load_json(sys.argv[1])
    except Exception as exc:
        print(json.dumps({"score": 0.0, "max_score": 1.0, "error": str(exc), "points": []}))
        return 1

    points = []

    add_point(
        points,
        "SP001",
        "appeal routing summary, deadline source, and pharmacy flags",
        1,
        {
            "routing": selected_case_fields(
                expected,
                {
                    "viability_decision": ["appeal", "viability_decision"],
                    "turnaround": ["appeal", "turnaround"],
                    "internal_review_next_step": ["appeal", "internal_review_next_step"],
                    "external_review_next_step": ["appeal", "external_review_next_step"],
                    "filing_deadline": ["appeal", "filing_deadline"],
                    "deadline_status": ["appeal", "deadline_status"],
                    "deadline_basis": ["appeal", "deadline_basis"],
                    "appeal_source_flags": ["appeal", "appeal_source_flags"],
                    "pharmacy_clinician_required": ["appeal", "pharmacy_clinician_required"],
                },
            ),
            "pharmacy_clinician_routed": expected.get("program_totals", {}).get("pharmacy_clinician_routed"),
        },
        {
            "routing": selected_case_fields(
                actual,
                {
                    "viability_decision": ["appeal", "viability_decision"],
                    "turnaround": ["appeal", "turnaround"],
                    "internal_review_next_step": ["appeal", "internal_review_next_step"],
                    "external_review_next_step": ["appeal", "external_review_next_step"],
                    "filing_deadline": ["appeal", "filing_deadline"],
                    "deadline_status": ["appeal", "deadline_status"],
                    "deadline_basis": ["appeal", "deadline_basis"],
                    "appeal_source_flags": ["appeal", "appeal_source_flags"],
                    "pharmacy_clinician_required": ["appeal", "pharmacy_clinician_required"],
                },
            ),
            "pharmacy_clinician_routed": actual.get("program_totals", {}).get("pharmacy_clinician_routed")
            if isinstance(actual.get("program_totals"), dict)
            else None,
        },
    )
    add_point(
        points,
        "SP003",
        "missing evidence and policy requirement keys by medication case",
        3,
        selected_case_fields(
            expected,
            {
                "policy_gaps": ["appeal", "policy_gaps"],
                "policy_requirement_keys_missing": ["appeal", "policy_requirement_keys_missing"],
                "policy_evidence_trace": ["appeal", "policy_evidence_trace"],
            },
        ),
        selected_case_fields(
            actual,
            {
                "policy_gaps": ["appeal", "policy_gaps"],
                "policy_requirement_keys_missing": ["appeal", "policy_requirement_keys_missing"],
                "policy_evidence_trace": ["appeal", "policy_evidence_trace"],
            },
        ),
    )
    add_point(
        points,
        "SP004",
        "manufacturer assistance routing summary and docket totals",
        1,
        {
            "assistance": selected_case_fields(
                expected,
                {
                    "program_id": ["assistance", "program_id"],
                    "eligibility_status": ["assistance", "eligibility_status"],
                    "blocking_reasons": ["assistance", "blocking_reasons"],
                    "path_separation": ["path_separation"],
                    "program_owner": ["assistance", "program_owner"],
                    "form_name": ["assistance", "form_name"],
                    "assistance_next_step": ["assistance", "next_step"],
                },
            ),
            "program_totals": expected.get("program_totals"),
        },
        {
            "assistance": selected_case_fields(
                actual,
                {
                    "program_id": ["assistance", "program_id"],
                    "eligibility_status": ["assistance", "eligibility_status"],
                    "blocking_reasons": ["assistance", "blocking_reasons"],
                    "path_separation": ["path_separation"],
                    "program_owner": ["assistance", "program_owner"],
                    "form_name": ["assistance", "form_name"],
                    "assistance_next_step": ["assistance", "next_step"],
                },
            ),
            "program_totals": actual.get("program_totals"),
        },
    )
    add_point(
        points,
        "SP009",
        "manufacturer assistance financial threshold trace",
        3,
        selected_case_fields(expected, {"financial_trace": ["assistance", "financial_trace"]}),
        selected_case_fields(actual, {"financial_trace": ["assistance", "financial_trace"]}),
    )
    add_point(
        points,
        "SP011",
        "complete assistance trace bundle",
        3,
        {
            "assistance_core": selected_case_fields(
                expected,
                {
                    "program_id": ["assistance", "program_id"],
                    "eligibility_status": ["assistance", "eligibility_status"],
                    "blocking_reasons": ["assistance", "blocking_reasons"],
                    "program_owner": ["assistance", "program_owner"],
                    "next_step": ["assistance", "next_step"],
                },
            ),
            "financial_trace": selected_case_fields(expected, {"financial_trace": ["assistance", "financial_trace"]}),
            "document_trace": selected_case_fields(expected, {"document_trace": ["assistance", "document_trace"]}),
        },
        {
            "assistance_core": selected_case_fields(
                actual,
                {
                    "program_id": ["assistance", "program_id"],
                    "eligibility_status": ["assistance", "eligibility_status"],
                    "blocking_reasons": ["assistance", "blocking_reasons"],
                    "program_owner": ["assistance", "program_owner"],
                    "next_step": ["assistance", "next_step"],
                },
            ),
            "financial_trace": selected_case_fields(actual, {"financial_trace": ["assistance", "financial_trace"]}),
            "document_trace": selected_case_fields(actual, {"document_trace": ["assistance", "document_trace"]}),
        },
    )
    add_point(
        points,
        "SP012",
        "complete appeal trace bundle",
        3,
        {
            "appeal_core": selected_case_fields(
                expected,
                {
                    "viability_decision": ["appeal", "viability_decision"],
                    "turnaround": ["appeal", "turnaround"],
                    "internal_review_next_step": ["appeal", "internal_review_next_step"],
                    "external_review_next_step": ["appeal", "external_review_next_step"],
                },
            ),
            "policy_evidence_trace": selected_case_fields(
                expected, {"policy_evidence_trace": ["appeal", "policy_evidence_trace"]}
            ),
            "deadline_basis": selected_case_fields(expected, {"deadline_basis": ["appeal", "deadline_basis"]}),
        },
        {
            "appeal_core": selected_case_fields(
                actual,
                {
                    "viability_decision": ["appeal", "viability_decision"],
                    "turnaround": ["appeal", "turnaround"],
                    "internal_review_next_step": ["appeal", "internal_review_next_step"],
                    "external_review_next_step": ["appeal", "external_review_next_step"],
                },
            ),
            "policy_evidence_trace": selected_case_fields(
                actual, {"policy_evidence_trace": ["appeal", "policy_evidence_trace"]}
            ),
            "deadline_basis": selected_case_fields(actual, {"deadline_basis": ["appeal", "deadline_basis"]}),
        },
    )

    raw_score = sum(point["earned"] for point in points)
    raw_max = sum(point["weight"] for point in points)
    print(
        json.dumps(
            {
                "score": raw_score / raw_max if raw_max else 0.0,
                "max_score": 1.0,
                "raw_score": raw_score,
                "raw_max_score": raw_max,
                "points": points,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
