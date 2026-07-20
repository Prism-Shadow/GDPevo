#!/usr/bin/env python3
import json
import sys
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parents[1]
RUBRIC_PATH = Path(__file__).resolve().with_name("rubric.json")
EXPECTED_MATTER_ID = "MTR-BRIARGATE-SEC"


def norm_str(value):
    if value is None:
        return None
    return str(value).strip()


def norm_id(value):
    if value is None:
        return None
    return str(value).strip().upper()


def norm_enum(value):
    if value is None:
        return None
    return str(value).strip().lower()


def norm_set(values):
    if values is None:
        return set()
    if isinstance(values, str):
        values = list(values.replace(";", ",").split(","))
    if not isinstance(values, list):
        return set()
    return {norm_id(v) for v in values if norm_id(v)}


def as_int(value):
    if isinstance(value, bool):
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


def list_of_dicts(answer, key):
    value = answer.get(key)
    return value if isinstance(value, list) else []


def find_by_id(items, key, expected):
    expected_norm = norm_id(expected)
    for item in items:
        if isinstance(item, dict) and norm_id(item.get(key)) == expected_norm:
            return item
    return None


def load_candidate(path):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(data, dict):
        return None, "Top-level JSON value must be an object."
    return data, None


def check_laptop(answer):
    item = find_by_id(list_of_dicts(answer, "custodian_issues"), "source_id", "SRC-BRIAR-LIN-LAPTOP")
    checks = {
        "source_present": item is not None,
        "custodian": item is not None and norm_str(item.get("custodian")) == "Evelyn Lin",
        "source_type": item is not None and norm_enum(item.get("source_type")) == "laptop",
        "status": item is not None and norm_enum(item.get("status")) == "lost",
        "risk_class": item is not None and norm_enum(item.get("risk_class")) == "post_hold_preservation_failure",
        "event_date": item is not None and norm_str(item.get("event_date")) == "2024-04-12",
        "category_impacts": item is not None and norm_set(item.get("category_impacts")) == {"SEC-A", "SEC-D"},
        "priority": item is not None and norm_enum(item.get("priority")) == "critical",
        "action": item is not None
        and norm_enum(item.get("recommended_action")) == "disclose_preservation_issue_and_pursue_forensics",
    }
    return all(checks.values()), checks


def check_sync_folder_metrics(answer):
    metrics = answer.get("metrics") if isinstance(answer.get("metrics"), dict) else {}
    checks = {
        "event_id": norm_id(metrics.get("sync_folder_event_id")) == "RET-BRIAR-CLOUD-DEL",
        "deleted_count": as_int(metrics.get("sync_folder_deleted_count")) == 24,
        "recovered_count": as_int(metrics.get("sync_folder_recovered_count")) == 17,
        "unrecovered_count": as_int(metrics.get("sync_folder_unrecovered_count")) == 7,
        "affected_categories": norm_set(metrics.get("sync_folder_affected_categories")) == {"SEC-B", "SEC-C"},
    }
    return all(checks.values()), checks


def check_unrecovered_files(answer):
    files = list_of_dicts(answer, "unrecovered_files")
    by_doc = {
        norm_id(item.get("doc_id")): item for item in files if isinstance(item, dict) and norm_id(item.get("doc_id"))
    }
    expected_classes = {
        "DOC-BRIAR-SOLARIS-MODEL": "valuation_workpaper",
        "DOC-BRIAR-NOVA-WATERFALL": "investor_communication",
    }
    exact_ids = set(by_doc) == set(expected_classes)
    per_file = {}
    for doc_id, file_class in expected_classes.items():
        item = by_doc.get(doc_id)
        per_file[doc_id] = {
            "event_id": item is not None and norm_id(item.get("event_id")) == "RET-BRIAR-CLOUD-DEL",
            "file_class": item is not None and norm_enum(item.get("file_class")) == file_class,
            "recovery_status": item is not None and norm_enum(item.get("recovery_status")) == "unrecovered",
            "category_impacts": item is not None and norm_set(item.get("category_impacts")) == {"SEC-B", "SEC-C"},
            "priority": item is not None and norm_enum(item.get("priority")) == "critical",
        }
    metrics = answer.get("metrics") if isinstance(answer.get("metrics"), dict) else {}
    checks = {
        "exact_doc_ids": exact_ids,
        "metric_count": as_int(metrics.get("unrecovered_investigation_relevant_file_count")) == 2,
        "per_file": per_file,
    }
    return exact_ids and checks["metric_count"] and all(all(v.values()) for v in per_file.values()), checks


def check_protonmail(answer):
    item = find_by_id(list_of_dicts(answer, "custodian_issues"), "source_id", "SRC-BRIAR-LIN-PMAIL")
    metrics = answer.get("metrics") if isinstance(answer.get("metrics"), dict) else {}
    status = norm_enum(item.get("status")) if item is not None else None
    checks = {
        "source_present": item is not None,
        "custodian": item is not None and norm_str(item.get("custodian")) == "Evelyn Lin",
        "source_type": item is not None and norm_enum(item.get("source_type")) == "personal_email",
        "status": status in {"uncollected", "not_collected"},
        "risk_class": item is not None and norm_enum(item.get("risk_class")) == "collection_gap",
        "category_impacts": item is not None and norm_set(item.get("category_impacts")) == {"SEC-A", "SEC-C"},
        "priority": item is not None and norm_enum(item.get("priority")) == "high",
        "action": item is not None and norm_enum(item.get("recommended_action")) == "collect_or_certify_unavailable",
        "metric_count": as_int(metrics.get("personal_account_gap_count")) == 1,
    }
    return all(checks.values()), checks


def check_privilege_defect(answer, defect_id, defect_type, count, third_party, priority, action):
    item = find_by_id(list_of_dicts(answer, "privilege_defects"), "defect_id", defect_id)
    if third_party is None:
        third_party_ok = item is not None and item.get("third_party") in (None, "", "N/A", "n/a")
    else:
        third_party_ok = item is not None and norm_str(item.get("third_party")) == third_party
    checks = {
        "defect_present": item is not None,
        "defect_type": item is not None and norm_enum(item.get("defect_type")) == defect_type,
        "doc_count": item is not None and as_int(item.get("doc_count")) == count,
        "third_party": third_party_ok,
        "priority": item is not None and norm_enum(item.get("priority")) == priority,
        "action": item is not None and norm_enum(item.get("recommended_action")) == action,
    }
    return all(checks.values()), checks


def check_waiver(answer):
    passed, checks = check_privilege_defect(
        answer,
        "PRIV-BRIAR-ADVISER-WAIVER",
        "third_party_waiver",
        4,
        "outside placement adviser",
        "critical",
        "waiver_analysis_and_disclosure_position",
    )
    metrics = answer.get("metrics") if isinstance(answer.get("metrics"), dict) else {}
    checks["metric_count"] = as_int(metrics.get("privileged_forwarded_count")) == 4
    return passed and checks["metric_count"], checks


def check_overdesignation(answer):
    passed, checks = check_privilege_defect(
        answer,
        "PRIV-BRIAR-OVERDESIG",
        "over_designation",
        15,
        None,
        "medium",
        "downgrade_overdesignated_business_docs",
    )
    metrics = answer.get("metrics") if isinstance(answer.get("metrics"), dict) else {}
    checks["metric_count"] = as_int(metrics.get("over_designated_count")) == 15
    return passed and checks["metric_count"], checks


def check_miscoded_priv(answer):
    passed, checks = check_privilege_defect(
        answer,
        "QC-BRIAR-MISCODED-PRIV",
        "privileged_coded_nonprivileged",
        38,
        None,
        "high",
        "privilege_recode_and_clawback_assessment",
    )
    metrics = answer.get("metrics") if isinstance(answer.get("metrics"), dict) else {}
    checks["metric_count"] = as_int(metrics.get("miscoded_privileged_count")) == 38
    return passed and checks["metric_count"], checks


def check_red_flags(answer):
    flags = list_of_dicts(answer, "substantive_red_flags")
    by_doc = {
        norm_id(item.get("doc_id")): item for item in flags if isinstance(item, dict) and norm_id(item.get("doc_id"))
    }
    expected_types = {
        "DOC-BRIAR-NOVA-BACKSOLVE": "valuation_back_into",
        "DOC-BRIAR-SOLARIS-OVERRIDE": "unsupported_valuation_mark",
    }
    exact_ids = set(by_doc) == set(expected_types)
    per_doc = {}
    for doc_id, red_type in expected_types.items():
        item = by_doc.get(doc_id)
        per_doc[doc_id] = {
            "red_flag_type": item is not None and norm_enum(item.get("red_flag_type")) == red_type,
            "category_impacts": item is not None and norm_set(item.get("category_impacts")) == {"SEC-A"},
            "priority": item is not None and norm_enum(item.get("priority")) == "high",
            "action": item is not None and norm_enum(item.get("recommended_action")) == "escalate_valuation_red_flags",
        }
    return exact_ids and all(all(v.values()) for v in per_doc.values()), {
        "exact_doc_ids": exact_ids,
        "per_doc": per_doc,
    }


def check_actions(answer):
    actions = list_of_dicts(answer, "recommended_actions")
    by_target = {
        norm_id(item.get("target_id")): item
        for item in actions
        if isinstance(item, dict) and norm_id(item.get("target_id"))
    }
    expected = {
        "RET-BRIAR-CLOUD-DEL": ("forensic_recovery_and_sec_disclosure_review", "ediscovery_counsel", "critical", 2),
        "SRC-BRIAR-LIN-LAPTOP": ("forensic_recovery_and_sec_disclosure_review", "ediscovery_counsel", "critical", 2),
        "SRC-BRIAR-LIN-PMAIL": ("personal_account_collection", "forensics_team", "high", 5),
        "PRIV-BRIAR-ADVISER-WAIVER": ("privilege_waiver_review", "privilege_counsel", "critical", 3),
        "QC-BRIAR-MISCODED-PRIV": ("privilege_recode", "review_qc_lead", "high", 5),
        "PRIV-BRIAR-OVERDESIG": ("overdesignation_cleanup", "privilege_counsel", "medium", 7),
    }
    per_target = {}
    for target_id, (action_type, owner, priority, due_days) in expected.items():
        item = by_target.get(target_id)
        per_target[target_id] = {
            "present": item is not None,
            "action_type": item is not None and norm_enum(item.get("action_type")) == action_type,
            "owner": item is not None and norm_enum(item.get("owner")) == owner,
            "priority": item is not None and norm_enum(item.get("priority")) == priority,
            "due_days": item is not None and as_int(item.get("due_days")) == due_days,
        }
    valuation_targets = {"DOC-BRIAR-NOVA-BACKSOLVE", "DOC-BRIAR-SOLARIS-OVERRIDE"}
    valuation_action = None
    for target_id in valuation_targets:
        item = by_target.get(target_id)
        if item is not None:
            valuation_action = item
            break
    valuation_action_ok = {
        "present": valuation_action is not None,
        "action_type": valuation_action is not None
        and norm_enum(valuation_action.get("action_type")) == "valuation_red_flag_escalation",
        "owner": valuation_action is not None and norm_enum(valuation_action.get("owner")) == "investigation_team",
        "priority": valuation_action is not None and norm_enum(valuation_action.get("priority")) == "high",
        "due_days": valuation_action is not None and as_int(valuation_action.get("due_days")) == 4,
    }
    top_two = {
        norm_id(item.get("target_id"))
        for item in actions
        if isinstance(item, dict) and as_int(item.get("rank")) in {1, 2}
    }
    ranks = [as_int(item.get("rank")) for item in actions if isinstance(item, dict)]
    checks = {
        "targets": per_target,
        "valuation_action": valuation_action_ok,
        "top_two_preservation_targets": top_two == {"RET-BRIAR-CLOUD-DEL", "SRC-BRIAR-LIN-LAPTOP"},
        "ranks_are_unique_integers": len([rank for rank in ranks if rank is not None]) == len(actions)
        and len(set(ranks)) == len(actions),
    }
    return (
        all(all(v.values()) for v in per_target.values())
        and all(valuation_action_ok.values())
        and checks["top_two_preservation_targets"]
        and checks["ranks_are_unique_integers"]
    ), checks


CHECKS = {
    "SP001": check_laptop,
    "SP002": check_sync_folder_metrics,
    "SP003": check_unrecovered_files,
    "SP004": check_protonmail,
    "SP005": check_waiver,
    "SP006": check_overdesignation,
    "SP007": check_miscoded_priv,
    "SP008": check_red_flags,
    "SP009": check_actions,
}


def main():
    candidate_path = Path(sys.argv[1]) if len(sys.argv) > 1 else TASK_DIR / "output" / "answer.json"
    rubric = json.loads(RUBRIC_PATH.read_text(encoding="utf-8"))["rubric"]
    total_weight = sum(point["weight"] for point in rubric)

    answer, error = load_candidate(candidate_path)
    parse_ok = error is None
    matter_ok = parse_ok and norm_id(answer.get("matter_id")) == EXPECTED_MATTER_ID
    results = []

    for point in rubric:
        assigned = point["weight"] / total_weight
        if not parse_ok:
            passed = False
            details = {"error": error}
        elif not matter_ok:
            passed = False
            details = {
                "matter_id": answer.get("matter_id"),
                "expected_matter_id": EXPECTED_MATTER_ID,
            }
        else:
            passed, details = CHECKS[point["id"]](answer)
        results.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "assigned_score": round(assigned, 10),
                "passed": bool(passed),
                "earned_score": round(assigned if passed else 0.0, 10),
                "details": details,
            }
        )

    earned_weight = sum(item["weight"] for item in results if item["passed"])
    score = earned_weight / total_weight
    output = {
        "task_id": "test_003",
        "candidate_path": str(candidate_path),
        "score": round(score, 10),
        "max_score": 1.0,
        "parse_ok": parse_ok,
        "matter_id_ok": bool(matter_ok),
        "points": results,
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
