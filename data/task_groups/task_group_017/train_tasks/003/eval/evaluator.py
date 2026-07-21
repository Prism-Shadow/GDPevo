#!/usr/bin/env python3
import json
import sys
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parents[1]
RUBRIC_PATH = Path(__file__).resolve().with_name("rubric.json")

WEIGHTS = {
    "matter_id": 1,
    "shared_drive_post_hold_loss": 3,
    "laptop_post_hold_loss": 2,
    "third_party_waiver": 2,
    "miscoded_privileged_docs": 2,
    "personal_email_source_gap": 2,
    "category_coverage_and_metrics": 3,
    "action_plan_order": 3,
}

EXPECTED_CATEGORIES = {
    "SEC-1": (
        "preservation_loss",
        "source_lost",
        {"SRC-GRAY-HALE-GMAIL", "SRC-GRAY-HALE-LAPTOP"},
        "disclose_preservation_issue",
        2,
    ),
    "SEC-2": ("preservation_loss", "source_lost", {"RET-GRAY-SHARE-DEL"}, "disclose_preservation_issue", 1),
    "SEC-3": (
        "underproduced_privilege_corrections",
        "privilege_exposure",
        {
            "DOC-GRAY-CASCADE-V3",
            "DOC-GRAY-ORION-DRAFT",
            "PRIV-GRAY-WINSLOW",
            "QC-GRAY-MISCODED-PRIV",
            "RET-GRAY-SHARE-DEL",
            "SRC-GRAY-HALE-GMAIL",
        },
        "waiver_assessment_and_disclosure",
        4,
    ),
    "SEC-4": ("preservation_loss", "source_lost", {"SRC-GRAY-HALE-LAPTOP"}, "disclose_preservation_issue", 1),
}

EXPECTED_METRICS = {
    "top_risk_count": 5,
    "destroyed_lab_archive_box_count": 0,
    "post_hold_loss_event_count": 2,
    "uncollected_personal_source_count": 1,
    "available_archive_count": 0,
    "miscoded_responsive_doc_count": 0,
    "withheld_privileged_doc_count": 0,
    "logged_privilege_doc_count": 0,
    "unlogged_privilege_doc_count": 0,
    "third_party_waiver_doc_count": 3,
    "miscoded_privileged_doc_count": 45,
    "missing_required_record_count": 0,
    "affected_category_count": 4,
}

EXPECTED_OPEN_CATEGORIES = {"SEC-1", "SEC-2", "SEC-3", "SEC-4"}


def norm(value):
    if value is None:
        return ""
    return str(value).strip()


def norm_lower(value):
    return norm(value).lower()


def norm_token(value):
    return norm_lower(value).replace("-", "_").replace(" ", "_")


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
        "risk_id",
        "source_refs",
        "issue_refs",
        "target_refs",
        "source_id",
        "event_id",
        "doc_id",
        "document_id",
        "finding_id",
        "entry_id",
        "target_id",
    ):
        value = record.get(key)
        if isinstance(value, list):
            refs.update(norm(item) for item in value if norm(item))
        elif norm(value):
            refs.add(norm(value))
    return refs


def category_set(value):
    return {norm_upper(item) for item in as_list(value) if norm(item)}


def find_record(records, expected_ref):
    exact_keys = ("risk_id", "source_id", "event_id", "doc_id", "document_id", "finding_id", "entry_id", "target_id")
    for item in as_list(records):
        record = as_dict(item)
        if any(norm(record.get(key)) == expected_ref for key in exact_keys):
            return record
    for item in as_list(records):
        record = as_dict(item)
        if expected_ref in refs_for(record):
            return record
    return {}


def enum_is(record, key, expected):
    return norm_lower(as_dict(record).get(key)) == expected


def enum_in(record, key, expected):
    return norm_token(as_dict(record).get(key)) in {norm_token(value) for value in expected}


def risk_details(risk):
    return {
        "risk_found": bool(risk),
        "issue_type": risk.get("issue_type"),
        "risk_level": risk.get("risk_level"),
        "status": risk.get("status"),
        "source_status": risk.get("source_status"),
        "production_impact": risk.get("production_impact"),
        "affected_categories": sorted(category_set(risk.get("affected_categories"))),
        "source_refs": sorted(refs_for(risk)),
        "document_count": risk.get("document_count"),
        "volume_count": risk.get("volume_count"),
        "volume_unit": risk.get("volume_unit"),
        "withheld_count": risk.get("withheld_count"),
        "logged_count": risk.get("logged_count"),
        "unlogged_count": risk.get("unlogged_count"),
        "third_party": risk.get("third_party"),
        "recommended_action": risk.get("recommended_action"),
    }


def check_matter_id(answer):
    return norm_upper(answer.get("matter_id")) == "MTR-GRAYCLIFF-SEC", {"actual": answer.get("matter_id")}


def check_shared_drive(answer):
    risk = find_record(answer.get("top_risks"), "RET-GRAY-SHARE-DEL")
    checks = {
        "risk_found": bool(risk),
        "rank": int_value(risk.get("priority_rank")) == 1,
        "issue_type": enum_is(risk, "issue_type", "post_hold_loss"),
        "risk_level": enum_is(risk, "risk_level", "critical"),
        "source_status": enum_is(risk, "source_status", "destroyed"),
        "production_impact": enum_is(risk, "production_impact", "source_lost"),
        "categories": category_set(risk.get("affected_categories")) == {"SEC-2", "SEC-3"},
        "refs": {"RET-GRAY-SHARE-DEL", "DOC-GRAY-CASCADE-V3", "DOC-GRAY-ORION-DRAFT"}.issubset(refs_for(risk)),
        "document_count": int_value(risk.get("document_count")) == 2,
        "volume": int_value(risk.get("volume_count")) == 8 and enum_is(risk, "volume_unit", "documents"),
        "recommended_action": enum_is(risk, "recommended_action", "disclose_preservation_issue"),
    }
    return all(checks.values()), {"checks": checks, "details": risk_details(risk)}


def check_laptop(answer):
    risk = find_record(answer.get("top_risks"), "SRC-GRAY-HALE-LAPTOP")
    checks = {
        "risk_found": bool(risk),
        "rank": int_value(risk.get("priority_rank")) == 4,
        "issue_type": enum_is(risk, "issue_type", "post_hold_loss"),
        "risk_level": enum_is(risk, "risk_level", "high"),
        "source_status": enum_is(risk, "source_status", "destroyed"),
        "production_impact": enum_is(risk, "production_impact", "source_lost"),
        "categories": category_set(risk.get("affected_categories")) == {"SEC-1", "SEC-4"},
        "volume": int_value(risk.get("volume_count")) == 1 and enum_is(risk, "volume_unit", "sources"),
        "recommended_action": enum_is(risk, "recommended_action", "disclose_preservation_issue"),
    }
    return all(checks.values()), {"checks": checks, "details": risk_details(risk)}


def check_waiver(answer):
    risk = find_record(answer.get("top_risks"), "PRIV-GRAY-WINSLOW")
    checks = {
        "risk_found": bool(risk),
        "rank": int_value(risk.get("priority_rank")) == 2,
        "issue_type": enum_is(risk, "issue_type", "third_party_waiver"),
        "risk_level": enum_is(risk, "risk_level", "high"),
        "status": enum_is(risk, "status", "protocol_noncompliant"),
        "production_impact": enum_is(risk, "production_impact", "privilege_exposure"),
        "categories": category_set(risk.get("affected_categories")) == {"SEC-3"},
        "document_count": int_value(risk.get("document_count")) == 3,
        "withheld_count": int_value(risk.get("withheld_count")) == 3,
        "logged_count": int_value(risk.get("logged_count")) == 3,
        "third_party": norm_lower(risk.get("third_party")) == "derek winslow",
        "recommended_action": enum_is(risk, "recommended_action", "waiver_assessment_and_disclosure"),
    }
    return all(checks.values()), {"checks": checks, "details": risk_details(risk)}


def check_miscoded_privileged(answer):
    risk = find_record(answer.get("top_risks"), "QC-GRAY-MISCODED-PRIV")
    checks = {
        "risk_found": bool(risk),
        "rank": int_value(risk.get("priority_rank")) == 3,
        "issue_type": enum_is(risk, "issue_type", "privilege_miscoding"),
        "risk_level": enum_is(risk, "risk_level", "high"),
        "status": enum_is(risk, "status", "needs_recode"),
        "production_impact": enum_is(risk, "production_impact", "privilege_exposure"),
        "categories": category_set(risk.get("affected_categories")) == {"SEC-3"},
        "refs": {"PRIV-GRAY-WINSLOW", "QC-GRAY-MISCODED-PRIV"}.issubset(refs_for(risk)),
        "document_count": int_value(risk.get("document_count")) == 45,
        "recommended_action": enum_is(risk, "recommended_action", "privilege_recode_and_log"),
    }
    return all(checks.values()), {"checks": checks, "details": risk_details(risk)}


def check_personal_email(answer):
    risk = find_record(answer.get("top_risks"), "SRC-GRAY-HALE-GMAIL")
    checks = {
        "risk_found": bool(risk),
        "rank": int_value(risk.get("priority_rank")) == 5,
        "issue_type": enum_is(risk, "issue_type", "personal_source_gap"),
        "risk_level": enum_is(risk, "risk_level", "high"),
        "source_status": enum_is(risk, "source_status", "not_collected"),
        "production_impact": enum_is(risk, "production_impact", "source_missing"),
        "categories": category_set(risk.get("affected_categories")) == {"SEC-1", "SEC-3"},
        "volume": int_value(risk.get("volume_count")) == 1 and enum_is(risk, "volume_unit", "sources"),
        "recommended_action": enum_is(risk, "recommended_action", "collect_personal_device"),
    }
    return all(checks.values()), {"checks": checks, "details": risk_details(risk)}


def check_category_coverage_and_metrics(answer):
    category_details = {}
    category_pass = True
    for code, (status, impact, refs, action, issue_count) in EXPECTED_CATEGORIES.items():
        row = {}
        for item in as_list(answer.get("category_coverage")):
            candidate = as_dict(item)
            if norm_upper(candidate.get("category_code")) == code:
                row = candidate
                break
        row_checks = {
            "present": bool(row),
            "status": enum_is(row, "status", status),
            "production_impact": enum_is(row, "production_impact", impact),
            "refs": refs.issubset(refs_for(row)),
            "recommended_action": enum_is(row, "recommended_action", action),
            "open_issue_count": int_value(row.get("open_issue_count")) == issue_count,
        }
        category_details[code] = {"checks": row_checks, "actual": row}
        category_pass = category_pass and all(row_checks.values())

    metrics = as_dict(answer.get("metrics"))
    metric_details = {key: int_value(metrics.get(key)) == expected for key, expected in EXPECTED_METRICS.items()}
    open_categories = category_set(metrics.get("categories_with_open_risk"))
    metric_details["categories_with_open_risk"] = open_categories == EXPECTED_OPEN_CATEGORIES
    metrics_pass = all(metric_details.values())
    no_available_sources = as_list(answer.get("retained_or_available_sources")) == []
    return category_pass and metrics_pass and no_available_sources, {
        "category_coverage_pass": category_pass,
        "metrics_pass": metrics_pass,
        "no_available_sources": no_available_sources,
        "categories": category_details,
        "metrics": metric_details,
        "actual_metrics": metrics,
    }


def find_action(answer, action_type):
    for item in as_list(answer.get("action_plan")):
        action = as_dict(item)
        if norm_lower(action.get("action_type")) == action_type:
            return action
    return {}


def action_ok(answer, rank, action_type, owner, target_refs, categories, max_due_days):
    action = find_action(answer, action_type)
    due_days = int_value(action.get("due_days"))
    checks = {
        "action_found": bool(action),
        "rank": int_value(action.get("rank")) == rank,
        "owner": norm_token(action.get("owner")) == owner,
        "target_refs": target_refs.issubset(refs_for(action)),
        "affected_categories": categories.issubset(category_set(action.get("affected_categories"))),
        "due_days": due_days is not None and due_days <= max_due_days,
    }
    return all(checks.values()), checks, action


def check_action_plan(answer):
    expected = [
        (
            1,
            "disclose_preservation_issue",
            "outside_counsel",
            {"RET-GRAY-SHARE-DEL", "SRC-GRAY-HALE-LAPTOP"},
            {"SEC-1", "SEC-2", "SEC-3", "SEC-4"},
            7,
        ),
        (2, "waiver_assessment_and_disclosure", "privilege_counsel", {"PRIV-GRAY-WINSLOW"}, {"SEC-3"}, 7),
        (3, "privilege_recode_and_log", "review_qc", {"QC-GRAY-MISCODED-PRIV"}, {"SEC-3"}, 7),
        (4, "collect_personal_device", "forensics", {"SRC-GRAY-HALE-GMAIL"}, {"SEC-1", "SEC-3"}, 14),
    ]
    details = {}
    passed = True
    for rank, action_type, owner, refs, categories, max_due_days in expected:
        ok, checks, action = action_ok(answer, rank, action_type, owner, refs, categories, max_due_days)
        details[str(rank)] = {"checks": checks, "actual": action}
        passed = passed and ok
    ranks = [int_value(as_dict(item).get("rank")) for item in as_list(answer.get("action_plan"))]
    details["unique_ranks"] = sorted(rank for rank in ranks if rank is not None)
    passed = passed and details["unique_ranks"] == [1, 2, 3, 4]
    return passed, details


CHECKS = {
    "matter_id": check_matter_id,
    "shared_drive_post_hold_loss": check_shared_drive,
    "laptop_post_hold_loss": check_laptop,
    "third_party_waiver": check_waiver,
    "miscoded_privileged_docs": check_miscoded_privileged,
    "personal_email_source_gap": check_personal_email,
    "category_coverage_and_metrics": check_category_coverage_and_metrics,
    "action_plan_order": check_action_plan,
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


def evaluate(candidate_path):
    try:
        answer = json.loads(Path(candidate_path).read_text(encoding="utf-8"))
    except Exception as exc:
        return zero_result(f"Could not read candidate JSON: {exc}")
    if not isinstance(answer, dict):
        return zero_result("Candidate answer must be a JSON object.")

    rubric = json.loads(RUBRIC_PATH.read_text(encoding="utf-8"))
    rubric_weights = {point["id"]: point["weight"] for point in rubric.get("points", [])}
    weights = rubric_weights or WEIGHTS
    total_weight = sum(weights.values())
    points = []
    score = 0.0
    for point_id, weight in weights.items():
        try:
            passed, details = CHECKS[point_id](answer)
        except Exception as exc:
            passed = False
            details = {"error": f"{type(exc).__name__}: {exc}"}
        earned = weight / total_weight if passed else 0.0
        score += earned
        points.append(
            {
                "id": point_id,
                "weight": weight,
                "assigned_score": weight / total_weight,
                "passed": bool(passed),
                "earned_score": earned,
                "details": details,
            }
        )
    return {"score": score, "max_score": 1.0, "total_weight": total_weight, "points": points, "correct": score == 1.0}


def main():
    candidate = sys.argv[1] if len(sys.argv) > 1 else str(TASK_DIR / "output" / "answer.json")
    print(json.dumps(evaluate(candidate), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
