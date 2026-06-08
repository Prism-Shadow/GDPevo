#!/usr/bin/env python3
"""Evaluator for test_002 Nordic Aquaculture Tech prospecting task."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


TASK_DIR = Path(__file__).resolve().parents[1]
STANDARD_ANSWER = TASK_DIR / "output" / "answer.json"

WEIGHTS = {
    "SP001": 3,
    "SP002": 3,
    "SP003": 2,
    "SP004": 2,
    "SP005": 2,
    "SP006": 1,
    "SP007": 3,
    "SP008": 3,
    "SP009": 3,
}

GOALS = {
    "SP001": "Correct qualified exhibitor set for Nordic Aquaculture Tech.",
    "SP002": "Correct platform labels for each qualified exhibitor.",
    "SP003": "Correct booth, country, and website enrichment.",
    "SP004": "Correct exclusion of service-only and sensor-only near misses.",
    "SP005": "Correct priority tier assignment.",
    "SP006": "Correct platform, priority, qualified, and exclusion aggregate counts.",
    "SP007": "Correct CRM action and existing account id per qualified exhibitor.",
    "SP008": "Correct pipeline estimate per qualified exhibitor.",
    "SP009": "Correct CRM overlap and total estimated pipeline rollup.",
}

PLATFORM_ORDER = ["AUV", "ROV", "Underwater Camera"]


def load_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:  # noqa: BLE001 - report parse errors as score JSON
        return None, f"{type(exc).__name__}: {exc}"


def norm_text(value: Any) -> str:
    return str(value).strip()


def norm_website(value: Any) -> str:
    text = norm_text(value)
    return text[:-1] if text.endswith("/") else text


def by_company_id(rows: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and row.get("company_id") is not None:
            result[norm_text(row.get("company_id"))] = row
    return result


def platform_list(row: dict[str, Any]) -> list[str]:
    values = row.get("platforms")
    if not isinstance(values, list):
        return []
    clean = [norm_text(value) for value in values]
    return sorted(clean, key=lambda item: PLATFORM_ORDER.index(item) if item in PLATFORM_ORDER else 99)


def load_expected() -> dict[str, Any]:
    expected, error = load_json(STANDARD_ANSWER)
    if error or not isinstance(expected, dict):
        raise RuntimeError(f"Cannot load standard answer: {error}")
    return {
        "answer": expected,
        "qualified": by_company_id(expected.get("qualified_exhibitors")),
        "excluded": by_company_id(expected.get("excluded_near_misses")),
    }


def check(prediction: Any) -> dict[str, bool]:
    if not isinstance(prediction, dict):
        return dict.fromkeys(WEIGHTS, False)

    expected = load_expected()
    exp_qualified = expected["qualified"]
    got_qualified = by_company_id(prediction.get("qualified_exhibitors"))
    exp_excluded = expected["excluded"]
    got_excluded = by_company_id(prediction.get("excluded_near_misses"))

    checks: dict[str, bool] = {}

    checks["SP001"] = (
        prediction.get("show_id") == expected["answer"].get("show_id")
        and prediction.get("campaign") == expected["answer"].get("campaign")
        and set(got_qualified) == set(exp_qualified)
    )

    checks["SP002"] = checks["SP001"] and all(
        platform_list(got_qualified[cid]) == platform_list(exp_qualified[cid]) for cid in exp_qualified
    )

    checks["SP003"] = checks["SP001"] and all(
        norm_text(got_qualified[cid].get("booth")) == norm_text(exp_qualified[cid].get("booth"))
        and norm_text(got_qualified[cid].get("country")) == norm_text(exp_qualified[cid].get("country"))
        and norm_website(got_qualified[cid].get("website")) == norm_website(exp_qualified[cid].get("website"))
        for cid in exp_qualified
    )

    checks["SP004"] = set(got_excluded) == set(exp_excluded) and all(
        norm_text(got_excluded[cid].get("exclusion_reason")) == norm_text(exp_excluded[cid].get("exclusion_reason"))
        for cid in exp_excluded
    )

    checks["SP005"] = checks["SP001"] and all(
        norm_text(got_qualified[cid].get("priority_tier")) == norm_text(exp_qualified[cid].get("priority_tier"))
        for cid in exp_qualified
    )

    checks["SP006"] = prediction.get("aggregate_counts") == expected["answer"].get("aggregate_counts")

    checks["SP007"] = checks["SP001"] and all(
        got_qualified[cid].get("crm_account_id") == exp_qualified[cid].get("crm_account_id")
        and norm_text(got_qualified[cid].get("crm_action")) == norm_text(exp_qualified[cid].get("crm_action"))
        for cid in exp_qualified
    )

    checks["SP008"] = checks["SP001"] and all(
        got_qualified[cid].get("pipeline_estimate_usd") == exp_qualified[cid].get("pipeline_estimate_usd")
        for cid in exp_qualified
    )

    got_counts = prediction.get("aggregate_counts") if isinstance(prediction.get("aggregate_counts"), dict) else {}
    exp_counts = expected["answer"].get("aggregate_counts")
    checks["SP009"] = isinstance(exp_counts, dict) and all(
        got_counts.get(key) == exp_counts.get(key)
        for key in (
            "create_account_count",
            "update_existing_count",
            "existing_crm_overlap_count",
            "existing_crm_overlap_account_ids",
            "total_estimated_pipeline_usd",
        )
    )

    return checks


def score(prediction: Any, error: str | None = None) -> dict[str, Any]:
    total_weight = sum(WEIGHTS.values())
    passed = dict.fromkeys(WEIGHTS, False) if error else check(prediction)
    points = []
    total = 0.0
    for sp in WEIGHTS:
        weight = WEIGHTS[sp]
        point_score = weight / total_weight if passed[sp] else 0.0
        total += point_score
        points.append(
            {
                "id": sp,
                "goal": GOALS[sp],
                "weight": weight,
                "passed": bool(passed[sp]),
                "score": round(point_score, 6),
            }
        )
    result = {
        "total_score": round(total, 6),
        "points": points,
    }
    if error:
        result["error"] = error
    return result


def main() -> int:
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else STANDARD_ANSWER
    prediction, error = load_json(prediction_path)
    print(json.dumps(score(prediction, error), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
