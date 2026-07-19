#!/usr/bin/env python3
import json
import sys
from pathlib import Path


WEIGHTS = {
    "SP001": 2,
    "SP002": 3,
    "SP003": 3,
    "SP004": 2,
    "SP005": 2,
    "SP006": 1,
    "SP007": 3,
}

EXPECTED_METRICS = {
    "withheld_privilege_docs": 840,
    "logged_privilege_docs": 365,
    "unlogged_privilege_docs": 475,
    "waived_privilege_doc_count": 5,
    "miscoded_responsive_doc_count": 1,
    "personal_email_gap_source_count": 0,
    "personal_phone_partial_source_count": 0,
    "nonready_category_count": 2,
}


def norm(value):
    if value is None:
        return ""
    return str(value).strip()


def norm_lower(value):
    return norm(value).lower()


def norm_upper(value):
    return norm(value).upper()


def as_list(value):
    return value if isinstance(value, list) else []


def as_dict(value):
    return value if isinstance(value, dict) else {}


def int_value(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        try:
            parsed = float(text)
        except ValueError:
            return None
        if parsed.is_integer():
            return int(parsed)
    return None


def refs_for(record):
    record = as_dict(record)
    refs = set()
    for key in (
        "issue_id",
        "correction_id",
        "action_id",
        "record_refs",
        "blocking_refs",
        "target_refs",
        "source_refs",
        "document_id",
        "doc_id",
        "finding_id",
        "defect_id",
    ):
        value = record.get(key)
        if isinstance(value, list):
            refs.update(norm(item) for item in value if norm(item))
        elif norm(value):
            refs.add(norm(value))
    return refs


def categories_for(record):
    record = as_dict(record)
    value = record.get("category_impacts", record.get("affected_categories"))
    return {norm_upper(item) for item in as_list(value) if norm(item)}


def find_record(records, expected_ref):
    for item in as_list(records):
        record = as_dict(item)
        if expected_ref in refs_for(record):
            return record
    return {}


def find_action(answer, action_type, target_ref=None):
    for item in as_list(answer.get("priority_actions")):
        action = as_dict(item)
        if norm_lower(action.get("action_type")) != action_type:
            continue
        if target_ref is not None and target_ref not in refs_for(action):
            continue
        return action
    return {}


def enum_is(record, key, expected):
    return norm_lower(as_dict(record).get(key)) == expected


def check_readiness(answer):
    statuses = {}
    for row in as_list(answer.get("readiness_statuses")):
        item = as_dict(row)
        statuses[norm_upper(item.get("category_code"))] = item
    sec_c = statuses.get("SEC-C", {})
    sec_d = statuses.get("SEC-D", {})
    metrics = as_dict(answer.get("metrics"))
    checks = {
        "matter_id": norm_upper(answer.get("matter_id")) == "MTR-NORTHBAY-SEC",
        "sec_c_present": bool(sec_c),
        "sec_c_status": enum_is(sec_c, "readiness_status", "not_ready_multiple_blockers"),
        "sec_c_impact": enum_is(sec_c, "production_impact", "multiple_impacts"),
        "sec_c_refs": {"DOC-NORTH-TRIAL-RISK", "PRIV-NORTH-CONSULTANT"}.issubset(refs_for(sec_c)),
        "sec_d_present": bool(sec_d),
        "sec_d_status": enum_is(sec_d, "readiness_status", "not_ready_privilege_log_incomplete"),
        "sec_d_impact": enum_is(sec_d, "production_impact", "withheld_unlogged"),
        "sec_d_refs": {"PRIV-NORTH-LOG-GAP", "QC-NORTH-MISCODED-PRIV"}.issubset(refs_for(sec_d)),
        "production_ready_false": metrics.get("production_ready") is False,
    }
    return all(checks.values()), {"checks": checks}


def check_responsive_miscoding(answer):
    issue = find_record(answer.get("issue_ledger"), "DOC-NORTH-TRIAL-RISK")
    action = find_action(answer, "recode_and_produce", "DOC-NORTH-TRIAL-RISK")
    checks = {
        "issue_found": bool(issue),
        "issue_type": enum_is(issue, "issue_type", "responsive_miscoding"),
        "status": enum_is(issue, "issue_status", "confirmed"),
        "category": categories_for(issue) == {"SEC-C"},
        "document_count": int_value(issue.get("document_count")) == 1,
        "current_coding": enum_is(issue, "current_coding", "nonresponsive"),
        "produced_status": enum_is(issue, "produced_status", "not_produced"),
        "disposition": enum_is(issue, "corrected_disposition", "responsive_produce"),
        "recommended_action": enum_is(issue, "recommended_action", "recode_and_produce"),
        "action": bool(action)
        and norm_lower(action.get("owner")) == "review_qc"
        and int_value(action.get("priority_rank")) == 1,
    }
    return all(checks.values()), {"checks": checks, "issue": issue, "action": action}


def check_privilege_log(answer):
    issue = find_record(answer.get("issue_ledger"), "PRIV-NORTH-LOG-GAP")
    correction = find_record(answer.get("privilege_corrections"), "PRIV-NORTH-LOG-GAP")
    action = find_action(answer, "supplement_privilege_log", "PRIV-NORTH-LOG-GAP")
    metrics = as_dict(answer.get("metrics"))
    checks = {
        "issue_found": bool(issue),
        "correction_found": bool(correction),
        "issue_type": enum_is(issue, "issue_type", "privilege_log_gap"),
        "status": enum_is(issue, "issue_status", "incomplete_log"),
        "category": categories_for(issue) == {"SEC-D"} and categories_for(correction) == {"SEC-D"},
        "withheld": int_value(issue.get("withheld_count")) == 840
        and int_value(correction.get("withheld_count")) == 840,
        "logged": int_value(issue.get("logged_count")) == 365 and int_value(correction.get("logged_count")) == 365,
        "unlogged": int_value(issue.get("unlogged_count")) == 475
        and int_value(correction.get("unlogged_count")) == 475,
        "metric_unlogged": int_value(metrics.get("unlogged_privilege_docs")) == 475,
        "action": bool(action) and norm_lower(action.get("owner")) == "privilege_team",
    }
    return all(checks.values()), {"checks": checks, "issue": issue, "correction": correction, "action": action}


def check_waiver(answer):
    issue = find_record(answer.get("issue_ledger"), "PRIV-NORTH-CONSULTANT")
    correction = find_record(answer.get("privilege_corrections"), "PRIV-NORTH-CONSULTANT")
    action = find_action(answer, "waiver_assessment_and_disclosure", "PRIV-NORTH-CONSULTANT")
    checks = {
        "issue_found": bool(issue),
        "correction_found": bool(correction),
        "issue_type": enum_is(issue, "issue_type", "third_party_waiver"),
        "status": enum_is(issue, "issue_status", "waived") and enum_is(correction, "privilege_status", "waived"),
        "category": categories_for(issue) == {"SEC-C"} and categories_for(correction) == {"SEC-C"},
        "count": int_value(issue.get("document_count")) == 5 and int_value(correction.get("document_count")) == 5,
        "third_party": norm_lower(issue.get("third_party")) == "trial_consultant"
        and norm_lower(correction.get("third_party")) == "trial_consultant",
        "action": bool(action) and norm_lower(action.get("owner")) == "privilege_counsel",
    }
    return all(checks.values()), {"checks": checks, "issue": issue, "correction": correction, "action": action}


def check_privilege_cleanup(answer):
    over = find_record(answer.get("privilege_corrections"), "PRIV-NORTH-CC-BIZ")
    miscoded = find_record(answer.get("privilege_corrections"), "QC-NORTH-MISCODED-PRIV")
    miscoded_issue = find_record(answer.get("issue_ledger"), "QC-NORTH-MISCODED-PRIV")
    checks = {
        "overdesignation_found": bool(over),
        "overdesignation_type": enum_is(over, "correction_type", "downgrade")
        and enum_is(over, "privilege_status", "over_designated"),
        "overdesignation_count": int_value(over.get("document_count")) == 27,
        "overdesignation_category": categories_for(over) == {"SEC-C"},
        "miscoded_found": bool(miscoded) and bool(miscoded_issue),
        "miscoded_type": enum_is(miscoded, "correction_type", "privilege_recode"),
        "miscoded_count": int_value(miscoded.get("document_count")) == 31
        and int_value(miscoded_issue.get("document_count")) == 31,
        "miscoded_category": categories_for(miscoded) == {"SEC-D"} and categories_for(miscoded_issue) == {"SEC-D"},
        "actions": bool(find_action(answer, "qc_remediation", "PRIV-NORTH-CC-BIZ"))
        and bool(find_action(answer, "qc_remediation", "QC-NORTH-MISCODED-PRIV")),
    }
    return all(checks.values()), {"checks": checks, "overdesignation": over, "miscoded": miscoded}


def check_metrics(answer):
    metrics = as_dict(answer.get("metrics"))
    checks = {key: int_value(metrics.get(key)) == value for key, value in EXPECTED_METRICS.items()}
    checks["production_ready"] = metrics.get("production_ready") is False
    return all(checks.values()), {"checks": checks, "metrics": metrics}


def check_actions(answer):
    expected = [
        (1, "recode_and_produce", "review_qc", {"DOC-NORTH-TRIAL-RISK"}, {"SEC-C"}),
        (2, "supplement_privilege_log", "privilege_team", {"PRIV-NORTH-LOG-GAP"}, {"SEC-D"}),
        (3, "waiver_assessment_and_disclosure", "privilege_counsel", {"PRIV-NORTH-CONSULTANT"}, {"SEC-C"}),
        (4, "qc_remediation", "review_qc", {"QC-NORTH-MISCODED-PRIV"}, {"SEC-D"}),
        (5, "qc_remediation", "privilege_team", {"PRIV-NORTH-CC-BIZ"}, {"SEC-C"}),
    ]
    details = {}
    passed = True
    ranks = []
    for rank, action_type, owner, refs, categories in expected:
        action = find_action(answer, action_type, next(iter(refs)))
        checks = {
            "present": bool(action),
            "rank": int_value(action.get("priority_rank")) == rank,
            "owner": norm_lower(action.get("owner")) == owner,
            "refs": refs.issubset(refs_for(action)),
            "categories": categories.issubset(categories_for(action)),
        }
        ranks.append(int_value(action.get("priority_rank")))
        details[str(rank)] = {"checks": checks, "actual": action}
        passed = passed and all(checks.values())
    passed = passed and sorted(ranks) == [1, 2, 3, 4, 5]
    details["unique_ranks"] = sorted(ranks)
    return passed, details


CHECKS = {
    "SP001": check_readiness,
    "SP002": check_responsive_miscoding,
    "SP003": check_privilege_log,
    "SP004": check_waiver,
    "SP005": check_privilege_cleanup,
    "SP006": check_metrics,
    "SP007": check_actions,
}


def zero_result(error_message):
    total_weight = sum(WEIGHTS.values())
    return {
        "score": 0.0,
        "max_score": 1.0,
        "total_weight": total_weight,
        "points": [
            {
                "id": point_id,
                "weight": weight,
                "assigned_score": weight / total_weight,
                "passed": False,
                "earned_score": 0.0,
                "details": {"error": error_message},
            }
            for point_id, weight in WEIGHTS.items()
        ],
        "error": error_message,
    }


def evaluate(answer):
    total_weight = sum(WEIGHTS.values())
    points = []
    score = 0.0
    for point_id, check in CHECKS.items():
        weight = WEIGHTS[point_id]
        assigned = weight / total_weight
        try:
            passed, details = check(answer)
        except Exception as exc:
            passed = False
            details = {"error": f"check failed: {exc}"}
        earned = assigned if passed else 0.0
        score += earned
        points.append(
            {
                "id": point_id,
                "weight": weight,
                "assigned_score": assigned,
                "passed": bool(passed),
                "earned_score": earned,
                "details": details,
            }
        )
    return {"score": score, "max_score": 1.0, "total_weight": total_weight, "points": points}


def main():
    if len(sys.argv) > 2:
        print(json.dumps(zero_result("usage: evaluate.py [candidate_answer_json]"), indent=2, sort_keys=True))
        return 2
    candidate_path = (
        Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).resolve().parents[1] / "output" / "answer.json"
    )
    try:
        with candidate_path.open("r", encoding="utf-8") as handle:
            answer = json.load(handle)
    except Exception as exc:
        print(json.dumps(zero_result(f"could not load candidate JSON: {exc}"), indent=2, sort_keys=True))
        return 0
    if not isinstance(answer, dict):
        print(json.dumps(zero_result("candidate JSON must be an object"), indent=2, sort_keys=True))
        return 0
    print(json.dumps(evaluate(answer), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
