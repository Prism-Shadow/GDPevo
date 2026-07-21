#!/usr/bin/env python3
import json
import sys
from pathlib import Path


WEIGHTS = {
    "P01_lab_archive_post_hold_loss": 3,
    "P02_personal_phone_gap": 2,
    "P03_cloud_archive_available": 2,
    "P04_investor_complaint_miscoding": 3,
    "P05_privilege_log_arithmetic": 3,
    "P06_third_party_waiver": 2,
    "P07_miscoded_privileged_docs": 2,
    "P08_missing_qa_audit": 2,
    "P09_category_coverage_and_metrics": 2,
    "P10_top_risk_ranking_and_action_plan": 3,
}

EXPECTED_CATEGORIES = {
    "VL-B": ("preservation_loss", "source_lost", {"RET-VIREO-LAB-POST"}, "disclose_preservation_issue", 1),
    "VL-C": ("missing_required_record", "missing_record", {"RET-VIREO-AUDIT-MISSING"}, "locate_missing_record", 1),
    "VL-D": (
        "source_gap_with_archive_available",
        "source_missing",
        {"SRC-VIREO-ARCHIVE", "SRC-VIREO-CHEN-PHONE"},
        "collect_personal_device",
        2,
    ),
    "VL-E": ("archive_available", "source_available", {"SRC-VIREO-ARCHIVE"}, "search_archive", 1),
    "VL-G": ("privilege_log_gap", "withheld_unlogged", {"PRIV-VIREO-LOG-GAP"}, "supplement_privilege_log", 1),
    "VL-H": (
        "mixed_preservation_and_missing_record",
        "source_lost",
        {"RET-VIREO-AUDIT-MISSING", "RET-VIREO-LAB-POST"},
        "disclose_preservation_issue",
        2,
    ),
    "VL-I": (
        "underproduced_privilege_corrections",
        "recode_needed",
        {"DOC-VIREO-INVESTOR-MISCODE", "PRIV-VIREO-THIRD-PARTY", "QC-VIREO-MISCODED-PRIV"},
        "recode_and_produce",
        3,
    ),
    "VL-J": ("personal_source_gap", "source_missing", {"SRC-VIREO-CHEN-PHONE"}, "collect_personal_device", 1),
}

EXPECTED_METRICS = {
    "top_risk_count": 7,
    "destroyed_lab_archive_box_count": 3,
    "post_hold_loss_event_count": 1,
    "uncollected_personal_source_count": 1,
    "available_archive_count": 1,
    "miscoded_responsive_doc_count": 1,
    "withheld_privileged_doc_count": 1755,
    "logged_privilege_doc_count": 702,
    "unlogged_privilege_doc_count": 1053,
    "third_party_waiver_doc_count": 3,
    "miscoded_privileged_doc_count": 29,
    "missing_required_record_count": 1,
    "affected_category_count": 8,
}

EXPECTED_OPEN_CATEGORIES = {"VL-B", "VL-C", "VL-D", "VL-E", "VL-G", "VL-H", "VL-I", "VL-J"}

EXPECTED_RISK_ORDER = [
    "RET-VIREO-LAB-POST",
    "PRIV-VIREO-THIRD-PARTY",
    "DOC-VIREO-INVESTOR-MISCODE",
    "PRIV-VIREO-LOG-GAP",
    "QC-VIREO-MISCODED-PRIV",
    "SRC-VIREO-CHEN-PHONE",
    "RET-VIREO-AUDIT-MISSING",
]

EXPECTED_ACTIONS = [
    ("disclose_preservation_issue", "outside_counsel", {"RET-VIREO-LAB-POST"}, {"VL-B", "VL-H"}, 3),
    ("waiver_assessment_and_disclosure", "privilege_counsel", {"PRIV-VIREO-THIRD-PARTY"}, {"VL-I"}, 3),
    ("recode_and_produce", "review_qc", {"DOC-VIREO-INVESTOR-MISCODE"}, {"VL-I"}, 5),
    ("supplement_privilege_log", "privilege_team", {"PRIV-VIREO-LOG-GAP"}, {"VL-G"}, 5),
    ("privilege_recode_and_log", "review_qc", {"QC-VIREO-MISCODED-PRIV"}, {"VL-I"}, 5),
    ("collect_personal_device", "forensics", {"SRC-VIREO-CHEN-PHONE"}, {"VL-D", "VL-J"}, 7),
    ("locate_missing_record", "compliance_audit", {"RET-VIREO-AUDIT-MISSING"}, {"VL-C", "VL-H"}, 7),
    ("search_archive", "ediscovery_vendor", {"SRC-VIREO-ARCHIVE"}, {"VL-D", "VL-E"}, 10),
]


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


def id_set(value):
    return {norm(item) for item in as_list(value) if norm(item)}


def category_set(value):
    return {norm_upper(item) for item in as_list(value) if norm(item)}


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
        "defect_id",
        "finding_id",
        "entry_id",
        "target_id",
    ):
        value = record.get(key)
        if isinstance(value, list):
            refs.update(id_set(value))
        elif norm(value):
            refs.add(norm(value))
    return refs


def find_record(records, expected_ref):
    exact_keys = (
        "risk_id",
        "source_id",
        "event_id",
        "doc_id",
        "document_id",
        "defect_id",
        "finding_id",
        "entry_id",
        "target_id",
    )
    for item in as_list(records):
        record = as_dict(item)
        if any(norm(record.get(key)) == expected_ref for key in exact_keys):
            return record
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


def action_ok(answer, action_type, owner, target_refs, categories, max_due_days):
    action = find_action(answer, action_type)
    due_days = int_value(action.get("due_days"))
    owner_aliases = {
        "ediscovery_vendor": {"ediscovery_vendor", "forensics"},
        "forensics": {"forensics", "ediscovery_vendor"},
        "review_qc": {"review_qc", "review_vendor", "privilege_team"},
        "privilege_team": {"privilege_team", "privilege_counsel"},
        "privilege_counsel": {"privilege_counsel", "outside_counsel"},
        "outside_counsel": {"outside_counsel", "privilege_counsel"},
        "compliance_audit": {"compliance_audit", "records_management"},
    }
    checks = {
        "action_found": bool(action),
        "owner": norm_token(action.get("owner")) in owner_aliases.get(owner, {owner}),
        "target_refs": target_refs.issubset(refs_for(action)),
        "affected_categories": categories.issubset(category_set(action.get("affected_categories"))),
        "due_days": due_days is not None and due_days <= max_due_days,
    }
    return all(checks.values()), checks


def enum_is(record, key, expected):
    return norm_lower(as_dict(record).get(key)) == expected


def enum_in(record, key, expected_values):
    return norm_token(as_dict(record).get(key)) in {norm_token(value) for value in expected_values}


def risk_base_details(risk):
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


def check_lab_archive(answer):
    risk = find_record(answer.get("top_risks"), "RET-VIREO-LAB-POST")
    action_pass, action_details = action_ok(
        answer,
        "disclose_preservation_issue",
        "outside_counsel",
        {"RET-VIREO-LAB-POST"},
        {"VL-B", "VL-H"},
        7,
    )
    checks = {
        "risk_found": bool(risk),
        "issue_type": enum_is(risk, "issue_type", "post_hold_loss"),
        "risk_level": enum_is(risk, "risk_level", "critical"),
        "source_status": enum_is(risk, "source_status", "destroyed"),
        "production_impact": enum_is(risk, "production_impact", "source_lost"),
        "categories": category_set(risk.get("affected_categories")) == {"VL-B", "VL-H"},
        "volume_count": int_value(risk.get("volume_count")) == 3,
        "volume_unit": enum_is(risk, "volume_unit", "boxes"),
        "recommended_action": enum_is(risk, "recommended_action", "disclose_preservation_issue"),
    }
    details = risk_base_details(risk)
    details["action"] = action_details
    return all(checks.values()), {"checks": checks, "details": details}


def check_personal_phone(answer):
    risk = find_record(answer.get("top_risks"), "SRC-VIREO-CHEN-PHONE")
    action_pass, action_details = action_ok(
        answer,
        "collect_personal_device",
        "forensics",
        {"SRC-VIREO-CHEN-PHONE"},
        {"VL-D", "VL-J"},
        14,
    )
    checks = {
        "risk_found": bool(risk),
        "issue_type": enum_is(risk, "issue_type", "personal_source_gap"),
        "risk_level": enum_is(risk, "risk_level", "high"),
        "source_status": enum_is(risk, "source_status", "not_collected"),
        "production_impact": enum_is(risk, "production_impact", "source_missing"),
        "categories": category_set(risk.get("affected_categories")) == {"VL-D", "VL-J"},
        "volume_count": int_value(risk.get("volume_count")) == 1,
        "recommended_action": enum_is(risk, "recommended_action", "collect_personal_device"),
    }
    details = risk_base_details(risk)
    details["action"] = action_details
    return all(checks.values()), {"checks": checks, "details": details}


def check_archive(answer):
    archive = find_record(answer.get("retained_or_available_sources"), "SRC-VIREO-ARCHIVE")
    action_pass, action_details = action_ok(
        answer,
        "search_archive",
        "ediscovery_vendor",
        {"SRC-VIREO-ARCHIVE"},
        {"VL-D", "VL-E"},
        14,
    )
    checks = {
        "source_found": bool(archive),
        "source_type": enum_is(archive, "source_type", "cloud_mail_archive"),
        "availability_status": enum_is(archive, "availability_status", "available_archive"),
        "active_system_issue": enum_is(archive, "active_system_issue", "purged_custodian_mail"),
        "affected_categories": category_set(archive.get("affected_categories")) == {"VL-D", "VL-E"},
        "limits_loss_for_categories": category_set(archive.get("limits_loss_for_categories")) == {"VL-D", "VL-E"},
        "recommended_action": enum_is(archive, "recommended_action", "search_archive"),
        "owner": enum_in(archive, "owner", {"ediscovery_vendor", "forensics"}),
    }
    return all(checks.values()), {"checks": checks, "source": archive, "action": action_details}


def check_investor_miscoding(answer):
    risk = find_record(answer.get("top_risks"), "DOC-VIREO-INVESTOR-MISCODE")
    action_pass, action_details = action_ok(
        answer,
        "recode_and_produce",
        "review_qc",
        {"DOC-VIREO-INVESTOR-MISCODE"},
        {"VL-I"},
        7,
    )
    checks = {
        "risk_found": bool(risk),
        "issue_type": enum_is(risk, "issue_type", "responsiveness_miscode"),
        "risk_level": enum_in(risk, "risk_level", {"high", "medium"}),
        "status": enum_is(risk, "status", "needs_recode"),
        "production_impact": enum_is(risk, "production_impact", "not_produced"),
        "categories": category_set(risk.get("affected_categories")) == {"VL-I"},
        "document_count": int_value(risk.get("document_count")) == 1,
        "recommended_action": enum_is(risk, "recommended_action", "recode_and_produce"),
    }
    details = risk_base_details(risk)
    details["action"] = action_details
    return all(checks.values()), {"checks": checks, "details": details}


def check_privilege_log(answer):
    risk = find_record(answer.get("top_risks"), "PRIV-VIREO-LOG-GAP")
    metrics = as_dict(answer.get("metrics"))
    action_pass, action_details = action_ok(
        answer,
        "supplement_privilege_log",
        "privilege_team",
        {"PRIV-VIREO-LOG-GAP"},
        {"VL-G"},
        7,
    )
    checks = {
        "risk_found": bool(risk),
        "issue_type": enum_is(risk, "issue_type", "privilege_log_gap"),
        "status": enum_in(risk, "status", {"protocol_noncompliant", "open", "incomplete_log"}),
        "production_impact": enum_is(risk, "production_impact", "withheld_unlogged"),
        "categories": category_set(risk.get("affected_categories")) == {"VL-G"},
        "document_count": int_value(risk.get("document_count")) == 1755,
        "withheld_count": int_value(risk.get("withheld_count")) == 1755,
        "logged_count": int_value(risk.get("logged_count")) == 702,
        "unlogged_count": int_value(risk.get("unlogged_count")) == 1053,
        "metric_unlogged": int_value(metrics.get("unlogged_privilege_doc_count")) == 1053,
        "recommended_action": enum_is(risk, "recommended_action", "supplement_privilege_log"),
    }
    details = risk_base_details(risk)
    details["metrics"] = {
        "withheld_privileged_doc_count": metrics.get("withheld_privileged_doc_count"),
        "logged_privilege_doc_count": metrics.get("logged_privilege_doc_count"),
        "unlogged_privilege_doc_count": metrics.get("unlogged_privilege_doc_count"),
    }
    details["action"] = action_details
    return all(checks.values()), {"checks": checks, "details": details}


def check_third_party_waiver(answer):
    risk = find_record(answer.get("top_risks"), "PRIV-VIREO-THIRD-PARTY")
    action_pass, action_details = action_ok(
        answer,
        "waiver_assessment_and_disclosure",
        "privilege_counsel",
        {"PRIV-VIREO-THIRD-PARTY"},
        {"VL-I"},
        7,
    )
    checks = {
        "risk_found": bool(risk),
        "issue_type": enum_is(risk, "issue_type", "third_party_waiver"),
        "risk_level": enum_in(risk, "risk_level", {"high", "medium"}),
        "production_impact": enum_is(risk, "production_impact", "privilege_exposure"),
        "categories": category_set(risk.get("affected_categories")) == {"VL-I"},
        "document_count": int_value(risk.get("document_count")) == 3,
        "withheld_count": int_value(risk.get("withheld_count")) == 3,
        "third_party": norm_token(risk.get("third_party")) == "outside_cro",
        "recommended_action": enum_is(risk, "recommended_action", "waiver_assessment_and_disclosure"),
    }
    details = risk_base_details(risk)
    details["action"] = action_details
    return all(checks.values()), {"checks": checks, "details": details}


def check_miscoded_privileged(answer):
    risk = find_record(answer.get("top_risks"), "QC-VIREO-MISCODED-PRIV")
    action_pass, action_details = action_ok(
        answer,
        "privilege_recode_and_log",
        "review_qc",
        {"QC-VIREO-MISCODED-PRIV"},
        {"VL-I"},
        7,
    )
    checks = {
        "risk_found": bool(risk),
        "issue_type": enum_is(risk, "issue_type", "privilege_miscoding"),
        "risk_level": enum_is(risk, "risk_level", "high"),
        "status": enum_is(risk, "status", "needs_recode"),
        "production_impact": enum_is(risk, "production_impact", "privilege_exposure"),
        "categories": category_set(risk.get("affected_categories")) == {"VL-I"},
        "source_refs": {"QC-VIREO-MISCODED-PRIV"}.issubset(refs_for(risk)),
        "document_count": int_value(risk.get("document_count")) == 29,
        "recommended_action": enum_is(risk, "recommended_action", "privilege_recode_and_log"),
    }
    details = risk_base_details(risk)
    details["action"] = action_details
    return all(checks.values()), {"checks": checks, "details": details}


def check_missing_audit(answer):
    risk = find_record(answer.get("top_risks"), "RET-VIREO-AUDIT-MISSING")
    action_pass, action_details = action_ok(
        answer,
        "locate_missing_record",
        "compliance_audit",
        {"RET-VIREO-AUDIT-MISSING"},
        {"VL-C", "VL-H"},
        14,
    )
    checks = {
        "risk_found": bool(risk),
        "issue_type": enum_is(risk, "issue_type", "missing_required_record"),
        "risk_level": enum_in(risk, "risk_level", {"high", "medium"}),
        "status": enum_is(risk, "status", "should_exist_missing"),
        "source_status": enum_is(risk, "source_status", "should_exist_missing"),
        "production_impact": enum_is(risk, "production_impact", "missing_record"),
        "categories": category_set(risk.get("affected_categories")) == {"VL-C", "VL-H"},
        "volume_count": int_value(risk.get("volume_count")) == 1,
        "volume_unit": enum_is(risk, "volume_unit", "report"),
        "recommended_action": enum_is(risk, "recommended_action", "locate_missing_record"),
    }
    details = risk_base_details(risk)
    details["action"] = action_details
    return all(checks.values()), {"checks": checks, "details": details}


def check_category_coverage_and_metrics(answer):
    category_details = {}
    category_pass = True
    for code, (status, impact, refs, action, issue_count) in EXPECTED_CATEGORIES.items():
        row = None
        for item in as_list(answer.get("category_coverage")):
            candidate = as_dict(item)
            if norm_upper(candidate.get("category_code")) == code:
                row = candidate
                break
        row = row or {}
        row_checks = {
            "present": bool(row),
            "status": enum_is(row, "status", status),
            "production_impact": enum_is(row, "production_impact", impact),
            "refs": refs.issubset(refs_for(row)),
            "recommended_action": enum_is(row, "recommended_action", action),
            "open_issue_count": int_value(row.get("open_issue_count")) == issue_count,
        }
        category_details[code] = {
            "passed": all(row_checks.values()),
            "checks": row_checks,
            "actual": {
                "status": row.get("status"),
                "production_impact": row.get("production_impact"),
                "issue_refs": sorted(refs_for(row)),
                "recommended_action": row.get("recommended_action"),
                "open_issue_count": row.get("open_issue_count"),
            },
        }
        category_pass = category_pass and all(row_checks.values())

    metrics = as_dict(answer.get("metrics"))
    metric_details = {}
    metrics_pass = True
    for key, expected in EXPECTED_METRICS.items():
        actual = int_value(metrics.get(key))
        metric_pass = actual == expected
        metric_details[key] = {"expected": expected, "actual": metrics.get(key), "passed": metric_pass}
        metrics_pass = metrics_pass and metric_pass
    open_categories = category_set(metrics.get("categories_with_open_risk"))
    metric_details["categories_with_open_risk"] = {
        "expected": sorted(EXPECTED_OPEN_CATEGORIES),
        "actual": sorted(open_categories),
        "passed": open_categories == EXPECTED_OPEN_CATEGORIES,
    }
    metrics_pass = metrics_pass and open_categories == EXPECTED_OPEN_CATEGORIES

    return category_pass and metrics_pass, {
        "category_coverage_pass": category_pass,
        "metrics_pass": metrics_pass,
        "categories": category_details,
        "metrics": metric_details,
    }


def risks_by_rank(answer):
    by_rank = {}
    duplicate_rank = False
    for item in as_list(answer.get("top_risks")):
        risk = as_dict(item)
        rank = int_value(risk.get("priority_rank"))
        if rank is None:
            continue
        if rank in by_rank:
            duplicate_rank = True
        by_rank[rank] = risk
    return by_rank, duplicate_rank


def actions_by_rank(answer):
    by_rank = {}
    duplicate_rank = False
    for item in as_list(answer.get("action_plan")):
        action = as_dict(item)
        rank = int_value(action.get("rank"))
        if rank is None:
            continue
        if rank in by_rank:
            duplicate_rank = True
        by_rank[rank] = action
    return by_rank, duplicate_rank


def check_top_ranking_and_actions(answer):
    risk_rank_map, duplicate_risk_rank = risks_by_rank(answer)
    risk_details = {}
    risk_order_pass = not duplicate_risk_rank
    for rank, expected_id in enumerate(EXPECTED_RISK_ORDER, start=1):
        risk = risk_rank_map.get(rank, {})
        rank_pass = expected_id in refs_for(risk)
        risk_details[str(rank)] = {
            "expected": expected_id,
            "actual_refs": sorted(refs_for(risk)),
            "passed": rank_pass,
        }
        risk_order_pass = risk_order_pass and rank_pass

    action_rank_map, duplicate_action_rank = actions_by_rank(answer)
    action_details = {}
    action_order_pass = not duplicate_action_rank
    for rank, (action_type, owner, target_refs, categories, max_due_days) in enumerate(EXPECTED_ACTIONS, start=1):
        action = find_action(answer, action_type) or action_rank_map.get(rank, {})
        due_days = int_value(action.get("due_days"))
        owner_aliases = {
            "ediscovery_vendor": {"ediscovery_vendor", "forensics"},
            "forensics": {"forensics", "ediscovery_vendor"},
            "review_qc": {"review_qc", "review_vendor", "privilege_team"},
            "privilege_team": {"privilege_team", "privilege_counsel"},
            "privilege_counsel": {"privilege_counsel", "outside_counsel"},
            "outside_counsel": {"outside_counsel", "privilege_counsel"},
            "compliance_audit": {"compliance_audit", "records_management"},
        }
        checks = {
            "action_type": norm_lower(action.get("action_type")) == action_type,
            "owner": norm_token(action.get("owner")) in owner_aliases.get(owner, {owner}),
            "target_refs": target_refs.issubset(refs_for(action)),
            "affected_categories": categories.issubset(category_set(action.get("affected_categories"))),
            "due_days": due_days is not None and due_days <= max_due_days * 2,
        }
        action_details[str(rank)] = {
            "expected_action_type": action_type,
            "checks": checks,
            "actual": {
                "action_type": action.get("action_type"),
                "owner": action.get("owner"),
                "target_refs": sorted(refs_for(action)),
                "affected_categories": sorted(category_set(action.get("affected_categories"))),
                "due_days": action.get("due_days"),
            },
        }
        action_order_pass = action_order_pass and all(checks.values())

    return risk_order_pass and action_order_pass, {
        "duplicate_risk_rank": duplicate_risk_rank,
        "duplicate_action_rank": duplicate_action_rank,
        "risk_order_pass": risk_order_pass,
        "action_order_pass": action_order_pass,
        "risk_order": risk_details,
        "action_order": action_details,
    }


CHECKS = {
    "P01_lab_archive_post_hold_loss": check_lab_archive,
    "P02_personal_phone_gap": check_personal_phone,
    "P03_cloud_archive_available": check_archive,
    "P04_investor_complaint_miscoding": check_investor_miscoding,
    "P05_privilege_log_arithmetic": check_privilege_log,
    "P06_third_party_waiver": check_third_party_waiver,
    "P07_miscoded_privileged_docs": check_miscoded_privileged,
    "P08_missing_qa_audit": check_missing_audit,
    "P09_category_coverage_and_metrics": check_category_coverage_and_metrics,
    "P10_top_risk_ranking_and_action_plan": check_top_ranking_and_actions,
}


def zero_result(error_message):
    total_weight = sum(WEIGHTS.values())
    points = []
    for point_id, weight in WEIGHTS.items():
        assigned = weight / total_weight
        points.append(
            {
                "id": point_id,
                "weight": weight,
                "assigned_score": assigned,
                "passed": False,
                "earned_score": 0.0,
                "details": {"error": error_message},
            }
        )
    return {
        "score": 0.0,
        "max_score": 1.0,
        "total_weight": total_weight,
        "points": points,
        "error": error_message,
    }


def evaluate(answer):
    total_weight = sum(WEIGHTS.values())
    points = []
    total_score = 0.0
    for point_id, check in CHECKS.items():
        weight = WEIGHTS[point_id]
        assigned = weight / total_weight
        try:
            passed, details = check(answer)
        except Exception as exc:  # Keep evaluator diagnostic instead of crashing on malformed structures.
            passed = False
            details = {"error": f"check failed: {exc}"}
        earned = assigned if passed else 0.0
        total_score += earned
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
    return {
        "score": total_score,
        "max_score": 1.0,
        "total_weight": total_weight,
        "points": points,
    }


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
