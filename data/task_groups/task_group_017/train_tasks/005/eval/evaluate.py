#!/usr/bin/env python3
import json
import sys
from pathlib import Path


WEIGHTS = {
    "matter_id": 1,
    "offsite_post_hold_loss": 3,
    "personal_messaging_source_risks": 3,
    "third_party_waiver_risk": 2,
    "privilege_log_gap": 3,
    "teams_archive_available_source": 2,
    "zero_claim_responsiveness_miscode": 3,
    "category_coverage_and_metrics": 2,
    "action_plan_order": 3,
}

EXPECTED_CATEGORIES = {
    "A": ("preservation_loss", "source_lost", {"RET-ALLOY-BOX-POST"}, "disclose_preservation_issue", 1),
    "B": (
        "underproduced_privilege_corrections",
        "privilege_exposure",
        {"PRIV-ALLOYWORKS-001", "PRIV-ALLOYWORKS-002"},
        "waiver_assessment_and_disclosure",
        2,
    ),
    "C": ("preservation_loss", "source_lost", {"RET-ALLOY-BOX-POST"}, "disclose_preservation_issue", 1),
    "D": (
        "source_gap_with_archive_available",
        "source_missing",
        {"SRC-ALLOY-KLINE-SIGNAL", "SRC-ALLOY-MORENO-SMS", "SRC-ALLOY-TEAMS-ARCHIVE"},
        "collect_personal_device",
        3,
    ),
    "E": ("archive_available", "source_available", {"SRC-ALLOY-TEAMS-ARCHIVE"}, "search_archive", 1),
    "F": (
        "responsiveness_gap",
        "underproduced",
        {
            "DOC-ALLOY-BID-EMAIL-1",
            "DOC-ALLOY-BID-EMAIL-2",
            "QC-ALLOY-ZERO-CLAIM",
            "RET-ALLOY-BOX-POST",
            "SRC-ALLOY-KLINE-SIGNAL",
            "SRC-ALLOY-MORENO-SMS",
        },
        "recode_and_produce",
        4,
    ),
}

EXPECTED_METRICS = {
    "top_risk_count": 6,
    "destroyed_lab_archive_box_count": 6,
    "post_hold_loss_event_count": 1,
    "uncollected_personal_source_count": 2,
    "available_archive_count": 1,
    "miscoded_responsive_doc_count": 2,
    "withheld_privileged_doc_count": 106,
    "logged_privilege_doc_count": 34,
    "unlogged_privilege_doc_count": 72,
    "third_party_waiver_doc_count": 34,
    "miscoded_privileged_doc_count": 0,
    "missing_required_record_count": 0,
    "affected_category_count": 6,
}

EXPECTED_OPEN_CATEGORIES = {"A", "B", "C", "D", "E", "F"}


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
    for item in as_list(records):
        record = as_dict(item)
        if expected_ref in refs_for(record):
            return record
    return {}


def find_action(answer, action_type):
    for item in as_list(answer.get("action_plan")):
        action = as_dict(item)
        if norm_lower(action.get("action_type")) == action_type:
            return action
    return {}


def enum_is(record, key, expected):
    return norm_lower(as_dict(record).get(key)) == expected


def action_ok(answer, action_type, owner, target_refs, categories, rank, max_due_days):
    action = find_action(answer, action_type)
    due_days = int_value(action.get("due_days"))
    checks = {
        "action_found": bool(action),
        "rank": int_value(action.get("rank")) == rank,
        "owner": norm_lower(action.get("owner")) == owner,
        "target_refs": target_refs.issubset(refs_for(action)),
        "affected_categories": categories.issubset(category_set(action.get("affected_categories"))),
        "due_days": due_days is not None and due_days <= max_due_days,
    }
    return all(checks.values()), checks, action


def check_matter_id(answer):
    return norm_upper(answer.get("matter_id")) == "MTR-ALLOYWORKS-GJ", {"actual": answer.get("matter_id")}


def check_offsite_loss(answer):
    risk = find_record(answer.get("top_risks"), "RET-ALLOY-BOX-POST")
    action_pass, action_details, action = action_ok(
        answer,
        "disclose_preservation_issue",
        "outside_counsel",
        {"RET-ALLOY-BOX-POST"},
        {"A", "C", "F"},
        1,
        7,
    )
    checks = {
        "risk_found": bool(risk),
        "rank": int_value(risk.get("priority_rank")) == 1,
        "issue_type": enum_is(risk, "issue_type", "post_hold_loss"),
        "risk_level": enum_is(risk, "risk_level", "critical"),
        "source_status": enum_is(risk, "source_status", "destroyed"),
        "production_impact": enum_is(risk, "production_impact", "source_lost"),
        "categories": category_set(risk.get("affected_categories")) == {"A", "C", "F"},
        "volume": int_value(risk.get("volume_count")) == 6 and enum_is(risk, "volume_unit", "boxes"),
        "recommended_action": enum_is(risk, "recommended_action", "disclose_preservation_issue"),
        "action": action_pass,
    }
    return all(checks.values()), {"checks": checks, "risk": risk, "action": action, "action_checks": action_details}


def check_personal_sources(answer):
    details = {}
    passed = True
    for expected_ref in ("SRC-ALLOY-KLINE-SIGNAL", "SRC-ALLOY-MORENO-SMS"):
        risk = find_record(answer.get("top_risks"), expected_ref)
        checks = {
            "risk_found": bool(risk),
            "issue_type": enum_is(risk, "issue_type", "personal_source_gap"),
            "risk_level": enum_is(risk, "risk_level", "high"),
            "source_status": enum_is(risk, "source_status", "not_collected"),
            "production_impact": enum_is(risk, "production_impact", "source_missing"),
            "categories": category_set(risk.get("affected_categories")) == {"D", "F"},
            "recommended_action": enum_is(risk, "recommended_action", "collect_personal_device"),
        }
        details[expected_ref] = {"checks": checks, "risk": risk}
        passed = passed and all(checks.values())
    action_pass, action_details, action = action_ok(
        answer,
        "collect_personal_device",
        "forensics",
        {"SRC-ALLOY-KLINE-SIGNAL", "SRC-ALLOY-MORENO-SMS"},
        {"D", "F"},
        5,
        14,
    )
    passed = passed and action_pass
    details["action"] = {"checks": action_details, "actual": action}
    return passed, details


def check_waiver(answer):
    risk = find_record(answer.get("top_risks"), "PRIV-ALLOYWORKS-002")
    action_pass, action_details, action = action_ok(
        answer,
        "waiver_assessment_and_disclosure",
        "privilege_counsel",
        {"PRIV-ALLOYWORKS-002"},
        {"B"},
        2,
        7,
    )
    checks = {
        "risk_found": bool(risk),
        "rank": int_value(risk.get("priority_rank")) == 2,
        "issue_type": enum_is(risk, "issue_type", "third_party_waiver"),
        "risk_level": enum_is(risk, "risk_level", "high"),
        "status": enum_is(risk, "status", "protocol_noncompliant"),
        "production_impact": enum_is(risk, "production_impact", "privilege_exposure"),
        "categories": category_set(risk.get("affected_categories")) == {"B"},
        "document_count": int_value(risk.get("document_count")) == 34,
        "withheld_count": int_value(risk.get("withheld_count")) == 34,
        "third_party": norm_lower(risk.get("third_party")) == "third_party_recipient",
        "recommended_action": enum_is(risk, "recommended_action", "waiver_assessment_and_disclosure"),
        "action": action_pass,
    }
    return all(checks.values()), {"checks": checks, "risk": risk, "action": action, "action_checks": action_details}


def check_privilege_log(answer):
    risk = find_record(answer.get("top_risks"), "PRIV-ALLOYWORKS-001")
    action_pass, action_details, action = action_ok(
        answer,
        "supplement_privilege_log",
        "privilege_team",
        {"PRIV-ALLOYWORKS-001"},
        {"B"},
        4,
        10,
    )
    metrics = as_dict(answer.get("metrics"))
    checks = {
        "risk_found": bool(risk),
        "rank": int_value(risk.get("priority_rank")) == 4,
        "issue_type": enum_is(risk, "issue_type", "privilege_log_gap"),
        "status": enum_is(risk, "status", "protocol_noncompliant"),
        "production_impact": enum_is(risk, "production_impact", "withheld_unlogged"),
        "categories": category_set(risk.get("affected_categories")) == {"B"},
        "document_count": int_value(risk.get("document_count")) == 106,
        "withheld_count": int_value(risk.get("withheld_count")) == 106,
        "logged_count": int_value(risk.get("logged_count")) == 34,
        "unlogged_count": int_value(risk.get("unlogged_count")) == 72,
        "metric_unlogged": int_value(metrics.get("unlogged_privilege_doc_count")) == 72,
        "recommended_action": enum_is(risk, "recommended_action", "supplement_privilege_log"),
        "action": action_pass,
    }
    return all(checks.values()), {"checks": checks, "risk": risk, "action": action, "action_checks": action_details}


def check_archive(answer):
    archive = find_record(answer.get("retained_or_available_sources"), "SRC-ALLOY-TEAMS-ARCHIVE")
    action_pass, action_details, action = action_ok(
        answer,
        "search_archive",
        "ediscovery_vendor",
        {"SRC-ALLOY-TEAMS-ARCHIVE"},
        {"D", "E"},
        6,
        14,
    )
    checks = {
        "source_found": bool(archive),
        "source_type": enum_is(archive, "source_type", "teams_archive"),
        "availability": enum_is(archive, "availability_status", "available_archive"),
        "active_system_issue": enum_is(archive, "active_system_issue", "deleted_channel"),
        "categories": category_set(archive.get("affected_categories")) == {"D", "E"},
        "limits_loss": category_set(archive.get("limits_loss_for_categories")) == {"D", "E"},
        "recommended_action": enum_is(archive, "recommended_action", "search_archive"),
        "owner": enum_is(archive, "owner", "ediscovery_vendor"),
        "action": action_pass,
    }
    return all(checks.values()), {
        "checks": checks,
        "source": archive,
        "action": action,
        "action_checks": action_details,
    }


def check_zero_claim(answer):
    risk = find_record(answer.get("top_risks"), "QC-ALLOY-ZERO-CLAIM")
    action_pass, action_details, action = action_ok(
        answer,
        "recode_and_produce",
        "review_qc",
        {"DOC-ALLOY-BID-EMAIL-1", "DOC-ALLOY-BID-EMAIL-2", "QC-ALLOY-ZERO-CLAIM"},
        {"F"},
        3,
        7,
    )
    checks = {
        "risk_found": bool(risk),
        "rank": int_value(risk.get("priority_rank")) == 3,
        "issue_type": enum_is(risk, "issue_type", "responsiveness_miscode"),
        "status": enum_is(risk, "status", "needs_recode"),
        "production_impact": enum_is(risk, "production_impact", "not_produced"),
        "categories": category_set(risk.get("affected_categories")) == {"F"},
        "refs": {"DOC-ALLOY-BID-EMAIL-1", "DOC-ALLOY-BID-EMAIL-2", "QC-ALLOY-ZERO-CLAIM"}.issubset(refs_for(risk)),
        "document_count": int_value(risk.get("document_count")) == 2,
        "recommended_action": enum_is(risk, "recommended_action", "recode_and_produce"),
        "action": action_pass,
    }
    return all(checks.values()), {"checks": checks, "risk": risk, "action": action, "action_checks": action_details}


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
    return category_pass and metrics_pass, {
        "category_coverage_pass": category_pass,
        "metrics_pass": metrics_pass,
        "categories": category_details,
        "metrics": metric_details,
        "actual_metrics": metrics,
    }


def check_action_plan(answer):
    expected = [
        (1, "disclose_preservation_issue", "outside_counsel", {"RET-ALLOY-BOX-POST"}, {"A", "C", "F"}, 7),
        (2, "waiver_assessment_and_disclosure", "privilege_counsel", {"PRIV-ALLOYWORKS-002"}, {"B"}, 7),
        (
            3,
            "recode_and_produce",
            "review_qc",
            {"DOC-ALLOY-BID-EMAIL-1", "DOC-ALLOY-BID-EMAIL-2", "QC-ALLOY-ZERO-CLAIM"},
            {"F"},
            7,
        ),
        (4, "supplement_privilege_log", "privilege_team", {"PRIV-ALLOYWORKS-001"}, {"B"}, 10),
        (
            5,
            "collect_personal_device",
            "forensics",
            {"SRC-ALLOY-KLINE-SIGNAL", "SRC-ALLOY-MORENO-SMS"},
            {"D", "F"},
            14,
        ),
        (6, "search_archive", "ediscovery_vendor", {"SRC-ALLOY-TEAMS-ARCHIVE"}, {"D", "E"}, 14),
    ]
    details = {}
    passed = True
    for rank, action_type, owner, target_refs, categories, max_due_days in expected:
        ok, checks, action = action_ok(answer, action_type, owner, target_refs, categories, rank, max_due_days)
        details[str(rank)] = {"checks": checks, "actual": action}
        passed = passed and ok
    ranks = [int_value(as_dict(item).get("rank")) for item in as_list(answer.get("action_plan"))]
    details["unique_ranks"] = sorted(rank for rank in ranks if rank is not None)
    passed = passed and details["unique_ranks"] == [1, 2, 3, 4, 5, 6]
    return passed, details


CHECKS = {
    "matter_id": check_matter_id,
    "offsite_post_hold_loss": check_offsite_loss,
    "personal_messaging_source_risks": check_personal_sources,
    "third_party_waiver_risk": check_waiver,
    "privilege_log_gap": check_privilege_log,
    "teams_archive_available_source": check_archive,
    "zero_claim_responsiveness_miscode": check_zero_claim,
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
