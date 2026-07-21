#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parents[1]
RUBRIC_PATH = Path(__file__).resolve().with_name("rubric.json")


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def resolve_candidate_path(raw_path):
    if raw_path is None:
        return TASK_DIR / "output" / "answer.json"
    path = Path(raw_path)
    if path.is_dir():
        return path / "answer.json"
    return path


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def norm_text(value):
    return str(value).strip().lower()


def norm_id(value):
    return str(value).strip().upper()


def ids_from(value):
    return {norm_id(item) for item in as_list(value) if str(item).strip()}


def int_value(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            return int(text)
    return None


def bool_value(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = norm_text(value)
        if text == "true":
            return True
        if text == "false":
            return False
    return None


def record_refs(record):
    refs = set()
    for key in (
        "finding_id",
        "source_refs",
        "target_refs",
        "source_ref",
        "target_ref",
        "doc_id",
        "document_id",
        "document_ids",
        "qc_id",
        "privilege_id",
        "entry_id",
    ):
        refs.update(ids_from(record.get(key)))
    return refs


def find_record(records, ref_id):
    target = norm_id(ref_id)
    for record in as_list(records):
        if isinstance(record, dict) and target in record_refs(record):
            return record
    return {}


def enum_is(record, key, expected):
    return norm_text(record.get(key)) == expected


def enum_in(record, key, expected_values):
    return norm_text(record.get(key)) in set(expected_values)


def has_refs(record, expected_refs, key=None):
    refs = ids_from(record.get(key)) if key else record_refs(record)
    return set(map(norm_id, expected_refs)).issubset(refs)


def has_categories(record, expected_categories, exact=False):
    actual = ids_from(record.get("category_impacts"))
    expected = set(map(norm_id, expected_categories))
    return actual == expected if exact else expected.issubset(actual)


def metric(answer, key):
    metrics = answer.get("metrics", {})
    if not isinstance(metrics, dict):
        return None
    return metrics.get(key)


def category_record(answer, category_code):
    target = norm_id(category_code)
    for record in as_list(answer.get("category_statuses")):
        if isinstance(record, dict) and norm_id(record.get("category_code")) == target:
            return record
    return {}


def action_matches(action, action_type, owner, target_refs, category_impacts=None):
    if not isinstance(action, dict):
        return False
    if norm_text(action.get("action_type")) != action_type:
        return False
    if norm_text(action.get("owner")) != owner:
        return False
    if not has_refs(action, target_refs, key="target_refs"):
        return False
    if category_impacts is not None and not has_categories(action, category_impacts):
        return False
    return True


def action_type_matches(action, action_types, target_refs, category_impacts=None, owners=None):
    if not isinstance(action, dict):
        return False
    if norm_text(action.get("action_type")) not in set(action_types):
        return False
    if owners is not None and norm_text(action.get("owner")) not in set(owners):
        return False
    if not has_refs(action, target_refs, key="target_refs"):
        return False
    if category_impacts is not None and not has_categories(action, category_impacts):
        return False
    return True


def has_action(answer, action_type, owner, target_refs, category_impacts=None):
    return any(
        action_matches(action, action_type, owner, target_refs, category_impacts)
        for action in as_list(answer.get("priority_actions"))
    )


def has_any_action(answer, action_types, target_refs, category_impacts=None, owners=None):
    return any(
        action_type_matches(action, action_types, target_refs, category_impacts, owners)
        for action in as_list(answer.get("priority_actions"))
    )


def check_phone_preservation(answer):
    finding = find_record(answer.get("critical_findings"), "SRC-MER-CARROW-PHONE")
    checks = {
        "finding_ref": bool(finding),
        "issue_type": enum_is(finding, "issue_type", "preservation_failure"),
        "source_status": enum_is(finding, "source_status", "lost"),
        "production_impact": enum_is(finding, "production_impact", "source_lost"),
        "categories": has_categories(finding, ["MD-09", "MD-15"], exact=True),
        "recommended_action": norm_text(finding.get("recommended_action"))
        in {
            "disclose_to_government",
            "forensic_recovery",
        },
        "action_present": has_any_action(
            answer,
            {"disclose_to_government", "forensic_recovery"},
            ["SRC-MER-CARROW-PHONE"],
            ["MD-09", "MD-15"],
            owners={"outside_counsel", "client_legal", "ediscovery_vendor", "forensics", "investigation_team"},
        ),
    }
    return all(checks.values()), checks


def check_md09_miscoded_safety_document(answer):
    finding = find_record(answer.get("critical_findings"), "DOC-MER-DEALER-SAFETY")
    checks = {
        "finding_ref": bool(finding),
        "qc_ref": has_refs(finding, ["QC-MER-MD09-NR"]),
        "issue_type": enum_is(finding, "issue_type", "responsiveness_miscode"),
        "production_impact": enum_in(finding, "production_impact", {"not_produced", "underproduced", "recode_needed"}),
        "categories": has_categories(finding, ["MD-09"], exact=True),
        "document_count": int_value(finding.get("document_count")) == 1,
        "recommended_action": enum_is(finding, "recommended_action", "recode_and_produce"),
        "action_present": (
            has_any_action(
                answer,
                {"recode_and_produce", "quality_control_review"},
                ["DOC-MER-DEALER-SAFETY"],
                ["MD-09"],
                owners={"review_vendor", "review_qc", "client_legal", "ediscovery_vendor"},
            )
            or has_any_action(
                answer,
                {"recode_and_produce", "quality_control_review"},
                ["QC-MER-MD09-NR"],
                ["MD-09"],
                owners={"review_vendor", "review_qc", "client_legal", "ediscovery_vendor"},
            )
        ),
    }
    return all(checks.values()), checks


def check_privilege_log_gap(answer):
    finding = find_record(answer.get("critical_findings"), "PRIV-MER-LOG-GAP")
    unlogged = int_value(finding.get("unlogged_count"))
    if unlogged is None:
        unlogged = int_value(metric(answer, "unlogged_privilege_docs"))
    checks = {
        "finding_ref": bool(finding),
        "issue_type": enum_is(finding, "issue_type", "privilege_log_gap"),
        "status": enum_is(finding, "finding_status", "protocol_noncompliant"),
        "production_impact": enum_is(finding, "production_impact", "withheld_unlogged"),
        "categories": has_categories(finding, ["MD-11"], exact=True),
        "document_count": int_value(finding.get("document_count")) == 2260,
        "withheld_count": int_value(finding.get("withheld_count")) == 2260,
        "logged_count": int_value(finding.get("logged_count")) == 910,
        "unlogged_count": unlogged == 1350,
        "recommended_action": enum_is(finding, "recommended_action", "supplement_privilege_log"),
    }
    return all(checks.values()), checks


def check_board_portal_gap(answer):
    finding = find_record(answer.get("critical_findings"), "SRC-MER-BOARD-ROOM")
    checks = {
        "finding_ref": bool(finding),
        "issue_type": enum_is(finding, "issue_type", "collection_gap"),
        "source_status": enum_is(finding, "source_status", "not_collected"),
        "production_impact": enum_is(finding, "production_impact", "source_missing"),
        "categories": has_categories(finding, ["MD-07", "MD-08", "MD-09"], exact=True),
        "recommended_action": enum_is(finding, "recommended_action", "collect_source"),
        "action_present": has_action(
            answer,
            "collect_source",
            "client_it",
            ["SRC-MER-BOARD-ROOM"],
            ["MD-07", "MD-08", "MD-09"],
        ),
    }
    return all(checks.values()), checks


def check_category_status_matrix(answer):
    expected = {
        "MD-07": ("collection_gap", "source_missing", ["SRC-MER-BOARD-ROOM"], "collect_source"),
        "MD-08": ("collection_gap", "source_missing", ["SRC-MER-BOARD-ROOM"], "collect_source"),
        "MD-09": (
            "incomplete",
            "underproduced",
            [
                "DOC-MER-DEALER-SAFETY",
                "QC-MER-MD09-NR",
                "SRC-MER-BOARD-ROOM",
                "SRC-MER-CARROW-PHONE",
            ],
            "recode_and_produce",
        ),
        "MD-11": ("privilege_log_gap", "withheld_unlogged", ["PRIV-MER-LOG-GAP"], "supplement_privilege_log"),
        "MD-15": ("preservation_risk", "source_lost", ["SRC-MER-CARROW-PHONE"], "disclose_to_government"),
    }
    checks = {}
    for code, (status, impact, refs, action) in expected.items():
        record = category_record(answer, code)
        checks[f"{code}_present"] = bool(record)
        status_aliases = {
            "MD-09": {"incomplete", "responsiveness_gap"},
        }
        impact_aliases = {
            "MD-09": {"underproduced", "not_produced", "recode_needed"},
        }
        action_aliases = {
            "MD-15": {"disclose_to_government", "forensic_recovery"},
        }
        checks[f"{code}_status"] = enum_in(record, "status", status_aliases.get(code, {status}))
        checks[f"{code}_impact"] = enum_in(record, "production_impact", impact_aliases.get(code, {impact}))
        checks[f"{code}_refs"] = has_refs(record, refs, key="source_refs")
        checks[f"{code}_action"] = enum_in(record, "recommended_action", action_aliases.get(code, {action}))
    return all(checks.values()), checks


def check_metrics_and_readiness(answer):
    checks = {
        "unlogged_privilege_docs": int_value(metric(answer, "unlogged_privilege_docs")) == 1350,
        "miscoded_responsive_doc_count": int_value(metric(answer, "miscoded_responsive_doc_count")) == 1,
        "lost_personal_device_count": int_value(metric(answer, "lost_personal_device_count")) == 1,
        "uncollected_board_source_count": int_value(metric(answer, "uncollected_board_source_count")) == 1,
        "categories_with_open_gaps": int_value(metric(answer, "categories_with_open_gaps")) == 5,
        "rolling_production_ready": bool_value(metric(answer, "rolling_production_ready")) is False,
    }
    return all(checks.values()), checks


def check_priority_action_set(answer):
    required = {
        "phone_disclosure": (
            "disclose_to_government",
            "outside_counsel",
            ["SRC-MER-CARROW-PHONE"],
            ["MD-09", "MD-15"],
        ),
        "phone_forensics": (
            "forensic_recovery",
            "ediscovery_vendor",
            ["SRC-MER-CARROW-PHONE"],
            ["MD-09", "MD-15"],
        ),
        "board_collection": (
            "collect_source",
            "client_it",
            ["SRC-MER-BOARD-ROOM"],
            ["MD-07", "MD-08", "MD-09"],
        ),
        "md09_recode": (
            "recode_and_produce",
            "review_vendor",
            ["DOC-MER-DEALER-SAFETY", "QC-MER-MD09-NR"],
            ["MD-09"],
        ),
        "privilege_log": (
            "supplement_privilege_log",
            "privilege_team",
            ["PRIV-MER-LOG-GAP"],
            ["MD-11"],
        ),
    }
    checks = {}
    for name, (action, owner, refs, categories) in required.items():
        owners = {owner}
        actions = {action}
        if name == "phone_disclosure":
            actions = {"disclose_to_government", "forensic_recovery"}
            owners = {"outside_counsel", "client_legal", "ediscovery_vendor", "forensics", "investigation_team"}
        elif name == "phone_forensics":
            actions = {"forensic_recovery", "disclose_to_government"}
            owners = {"ediscovery_vendor", "forensics", "outside_counsel", "client_legal", "investigation_team"}
        elif name == "md09_recode":
            actions = {"recode_and_produce", "quality_control_review"}
            owners = {"review_vendor", "review_qc", "client_legal", "ediscovery_vendor"}
        elif name == "board_collection":
            owners = {"client_it", "ediscovery_vendor", "forensics", "investigation_team"}
        if name == "md09_recode":
            checks[name] = has_any_action(answer, actions, refs, categories, owners=owners) or has_any_action(
                answer, actions, ["QC-MER-MD09-NR"], categories, owners=owners
            )
        else:
            checks[name] = has_any_action(answer, actions, refs, categories, owners=owners)
    ranks = []
    for action in as_list(answer.get("priority_actions")):
        rank = int_value(action.get("priority_rank")) if isinstance(action, dict) else None
        if rank is not None:
            ranks.append(rank)
    checks["priority_ranks_unique"] = len(ranks) >= 4 and len(ranks) == len(set(ranks))
    return all(checks.values()), checks


CHECKS = {
    "P1_phone_preservation": check_phone_preservation,
    "P2_md09_miscoded_safety_document": check_md09_miscoded_safety_document,
    "P3_privilege_log_gap": check_privilege_log_gap,
    "P4_board_portal_gap": check_board_portal_gap,
    "P5_category_status_matrix": check_category_status_matrix,
    "P6_metrics_and_readiness": check_metrics_and_readiness,
    "P7_priority_action_set": check_priority_action_set,
}


def zero_result(rubric, error):
    total_weight = sum(point["weight"] for point in rubric["points"])
    points = []
    for point in rubric["points"]:
        assigned = point["weight"] / total_weight
        points.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "assigned_score": round(assigned, 6),
                "passed": False,
                "earned_score": 0,
                "details": {"error": error},
            }
        )
    return {"score": 0, "correct": False, "points": points}


def evaluate(candidate_path):
    rubric = load_json(RUBRIC_PATH)
    try:
        answer = load_json(candidate_path)
    except Exception as exc:
        return zero_result(rubric, f"Could not read candidate JSON: {exc}")

    if not isinstance(answer, dict):
        return zero_result(rubric, "Candidate answer must be a JSON object.")

    total_weight = sum(point["weight"] for point in rubric["points"])
    results = []
    earned_total = 0.0

    for point in rubric["points"]:
        check = CHECKS[point["id"]]
        passed, details = check(answer)
        assigned = point["weight"] / total_weight
        earned = assigned if passed else 0.0
        earned_total += earned
        results.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "assigned_score": round(assigned, 6),
                "passed": bool(passed),
                "earned_score": round(earned, 6),
                "details": details,
            }
        )

    score = round(earned_total, 6)
    return {
        "score": score,
        "correct": math.isclose(score, 1.0, rel_tol=0.0, abs_tol=1e-9),
        "matter_id_ok": norm_id(answer.get("matter_id")) == "MTR-MERIDIAN-GJ",
        "points": results,
    }


def main():
    candidate_path = resolve_candidate_path(sys.argv[1] if len(sys.argv) > 1 else None)
    result = evaluate(candidate_path)
    result["candidate_path"] = str(candidate_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
