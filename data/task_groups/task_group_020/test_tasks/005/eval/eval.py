#!/usr/bin/env python3
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
EXPECTED_PATH = SCRIPT_DIR.parent / "output" / "answer.json"

SORT_KEYS = {
    "seller_allocations": "seller_id",
    "required_customer_consents": "contract_name",
    "overridden_clauses": "clause_code",
    "non_overridden_clause_handling": "clause_code",
}

OVERRIDDEN_SUBSTANCE_FIELDS = [
    "clause_code",
    "source_clause_id",
    "source_doc_id",
    "policy_rule_id",
    "override_action",
    "draft_position_code",
    "required_position_code",
]

OVERRIDDEN_ROUTING_FIELDS = [
    "clause_code",
    "approval_required_if_unrevised",
    "approval_body",
    "routing_source_id",
    "unrevised_trigger_code",
]

POINTS = [
    {
        "id": "SP001_DEAL_TERMS_AND_CLOSING_FACTS",
        "weight": 1,
        "goal": "Correct deal terms, allocation math, indemnity values, note/NWC treatment, and closing-risk lookups.",
        "checks": [
            {"label": "deal_id", "path": ("deal_id",)},
            {"label": "deal_terms", "path": ("deal_terms",)},
        ],
    },
    {
        "id": "SP002_EXACT_CONTROLLING_RISK_SOURCE_IDS",
        "weight": 3,
        "goal": "Exact controlling risk-allocation source IDs, excluding calculation-only and stale/template document sources.",
        "checks": [
            {"label": "risk_overrides.policy_id", "path": ("risk_overrides", "policy_id")},
            {"label": "risk_overrides.policy_version", "path": ("risk_overrides", "policy_version")},
            {
                "label": "risk_overrides.source_precedence.source_precedence_code",
                "path": ("risk_overrides", "source_precedence", "source_precedence_code"),
            },
            {
                "label": "risk_overrides.source_precedence.controlling_risk_source_ids",
                "path": ("risk_overrides", "source_precedence", "controlling_risk_source_ids"),
            },
            {"label": "risk_overrides.source_ids", "path": ("risk_overrides", "source_ids")},
            {
                "label": "risk_overrides.source_precedence.rejected_document_source_ids",
                "path": ("risk_overrides", "source_precedence", "rejected_document_source_ids"),
            },
            {"label": "risk_overrides.superseded_source_ids", "path": ("risk_overrides", "superseded_source_ids")},
        ],
    },
    {
        "id": "SP003_EXACT_CONTROLLING_CLAUSE_SOURCE_IDS",
        "weight": 1,
        "goal": "Exact controlling clause source IDs, excluding accepted active clauses and rejecting stale/template clauses.",
        "checks": [
            {
                "label": "risk_overrides.source_precedence.controlling_clause_source_ids",
                "path": ("risk_overrides", "source_precedence", "controlling_clause_source_ids"),
            },
            {
                "label": "risk_overrides.source_precedence.non_overridden_active_clause_ids",
                "path": ("risk_overrides", "source_precedence", "non_overridden_active_clause_ids"),
            },
            {
                "label": "risk_overrides.source_precedence.rejected_template_clause_ids",
                "path": ("risk_overrides", "source_precedence", "rejected_template_clause_ids"),
            },
        ],
    },
    {
        "id": "SP004_EXACT_OVERRIDE_CODES_NO_TEMPLATE_SUPERSEDED",
        "weight": 1,
        "goal": "Exact override code set, excluding TEMPLATE_LANGUAGE_SUPERSEDED, and exact overridden clause-code set.",
        "checks": [
            {"label": "risk_overrides.override_codes", "path": ("risk_overrides", "override_codes")},
            {"label": "risk_overrides.overridden_clause_codes", "path": ("risk_overrides", "overridden_clause_codes")},
        ],
    },
    {
        "id": "SP005_EXACT_NON_OVERRIDDEN_CLAUSE_HANDLING",
        "weight": 1,
        "goal": "Exact handling of reviewed active clauses that are accepted and must not be treated as overrides.",
        "checks": [
            {
                "label": "risk_overrides.non_overridden_clause_codes",
                "path": ("risk_overrides", "non_overridden_clause_codes"),
            },
            {
                "label": "risk_overrides.non_overridden_clause_handling",
                "path": ("risk_overrides", "non_overridden_clause_handling"),
            },
        ],
    },
    {
        "id": "SP006_OVERRIDE_SUBSTANTIVE_POSITIONS",
        "weight": 1,
        "goal": "Correct clause-level override substance: source clauses, policy rules, actions, draft positions, and required positions.",
        "checks": [
            {
                "label": "risk_overrides.overridden_clauses.substantive_fields",
                "extractor": "overridden_clause_substance",
                "context_key": "overridden_clauses",
            },
        ],
    },
    {
        "id": "SP007_APPROVAL_ROUTING_AND_SUMMARY",
        "weight": 1,
        "goal": "Correct approval routing fields and summary for unrevised override triggers.",
        "checks": [
            {
                "label": "risk_overrides.source_precedence.routing_precedence_code",
                "path": ("risk_overrides", "source_precedence", "routing_precedence_code"),
            },
            {
                "label": "risk_overrides.overridden_clauses.routing_fields",
                "extractor": "overridden_clause_routing",
                "context_key": "overridden_clauses",
            },
            {"label": "risk_overrides.approval_summary", "path": ("risk_overrides", "approval_summary")},
        ],
    },
    {
        "id": "SP008_FINAL_SOURCE_PRUNED_DRAFTING_POSTURE",
        "weight": 1,
        "goal": "Correct final drafting posture tied to the exact source-pruned risk and clause override set.",
        "checks": [
            ("risk_overrides", "final_drafting_posture"),
            {
                "label": "risk_overrides.source_precedence.controlling_risk_source_ids",
                "path": ("risk_overrides", "source_precedence", "controlling_risk_source_ids"),
            },
            {
                "label": "risk_overrides.source_precedence.controlling_clause_source_ids",
                "path": ("risk_overrides", "source_precedence", "controlling_clause_source_ids"),
            },
            {"label": "risk_overrides.override_codes", "path": ("risk_overrides", "override_codes")},
            {
                "label": "risk_overrides.non_overridden_clause_handling",
                "path": ("risk_overrides", "non_overridden_clause_handling"),
            },
        ],
    },
]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_path(obj, path):
    cur = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def project_rows(obj, path, fields):
    rows = get_path(obj, path)
    if not isinstance(rows, list):
        return rows
    projected = []
    for row in rows:
        if not isinstance(row, dict):
            projected.append(row)
            continue
        projected.append({field: row.get(field) for field in fields})
    return projected


def extract_value(obj, check):
    if isinstance(check, tuple):
        return get_path(obj, check), ".".join(check), check[-1]

    if "path" in check:
        path = check["path"]
        return get_path(obj, path), check.get("label", ".".join(path)), check.get("context_key", path[-1])

    extractor = check.get("extractor")
    if extractor == "overridden_clause_substance":
        return (
            project_rows(obj, ("risk_overrides", "overridden_clauses"), OVERRIDDEN_SUBSTANCE_FIELDS),
            check["label"],
            check.get("context_key"),
        )
    if extractor == "overridden_clause_routing":
        return (
            project_rows(obj, ("risk_overrides", "overridden_clauses"), OVERRIDDEN_ROUTING_FIELDS),
            check["label"],
            check.get("context_key"),
        )
    raise ValueError(f"Unknown check extractor: {extractor}")


def normalize(value, context_key=None):
    if isinstance(value, dict):
        return {key: normalize(value[key], key) for key in sorted(value)}
    if isinstance(value, list):
        items = [normalize(item) for item in value]
        sort_key = SORT_KEYS.get(context_key)
        if sort_key and all(isinstance(item, dict) and sort_key in item for item in items):
            return sorted(items, key=lambda item: item[sort_key])
        return sorted(items, key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, float):
        return round(value, 2)
    return value


def evaluate(prediction, expected, error=None):
    total_weight = sum(point["weight"] for point in POINTS)
    earned_weight = 0
    results = []

    if error is None and isinstance(prediction, dict):
        for point in POINTS:
            mismatches = []
            for check in point["checks"]:
                actual, label, context_key = extract_value(prediction, check)
                expected_value, _, _ = extract_value(expected, check)
                if normalize(actual, context_key) != normalize(expected_value, context_key):
                    mismatches.append(
                        {
                            "path": label,
                            "expected": expected_value,
                            "actual": actual,
                        }
                    )
            passed = not mismatches
            earned = point["weight"] if passed else 0
            earned_weight += earned
            results.append(
                {
                    "id": point["id"],
                    "goal": point["goal"],
                    "weight": point["weight"],
                    "earned_weight": earned,
                    "passed": passed,
                    "mismatches": mismatches,
                }
            )
    else:
        for point in POINTS:
            results.append(
                {
                    "id": point["id"],
                    "goal": point["goal"],
                    "weight": point["weight"],
                    "earned_weight": 0,
                    "passed": False,
                    "mismatches": [],
                }
            )

    return {
        "score": round(earned_weight / total_weight, 10),
        "earned_weight": earned_weight,
        "total_weight": total_weight,
        "points": results,
        "error": error,
    }


def main():
    prediction_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else EXPECTED_PATH
    try:
        expected = load_json(EXPECTED_PATH)
    except Exception as exc:  # noqa: BLE001 - task evaluators report failures as JSON.
        result = {
            "score": 0.0,
            "earned_weight": 0,
            "total_weight": sum(point["weight"] for point in POINTS),
            "points": [],
            "error": f"Could not load expected answer: {type(exc).__name__}: {exc}",
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    try:
        prediction = load_json(prediction_path)
        error = None
    except Exception as exc:  # noqa: BLE001 - task evaluators report failures as JSON.
        prediction = None
        error = f"Could not parse prediction JSON: {type(exc).__name__}: {exc}"

    print(json.dumps(evaluate(prediction, expected, error), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
