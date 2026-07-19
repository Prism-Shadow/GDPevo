#!/usr/bin/env python3
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Optional


TASK_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE = TASK_DIR / "output" / "answer.json"
RUBRIC_PATH = Path(__file__).resolve().with_name("rubric.json")


EXPECTED_METRICS = {
    "withheld_privilege_docs": 1290,
    "logged_privilege_docs": 480,
    "unlogged_privilege_docs": 810,
    "waived_privilege_doc_count": 6,
    "miscoded_responsive_doc_count": 1,
    "personal_email_gap_source_count": 1,
    "personal_phone_partial_source_count": 1,
    "nonready_category_count": 3,
    "production_ready": False,
}

EXPECTED_ACTIONS = [
    (
        "recode_and_produce",
        "review_qc",
        "P0",
        {"DOC-COBALT-BANKER-SIDE", "QC-COBALT-ZERO-CR06"},
        {"CR-06"},
    ),
    (
        "collect_personal_email",
        "forensics",
        "P1",
        {"SRC-COBALT-PARK-GMAIL"},
        {"CR-06", "CR-15"},
    ),
    (
        "collect_signal_messages",
        "forensics",
        "P1",
        {"SRC-COBALT-PARK-PHONE"},
        {"CR-15"},
    ),
    (
        "supplement_privilege_log",
        "privilege_team",
        "P1",
        {"PRIV-COBALT-LOG-GAP"},
        {"CR-11"},
    ),
    (
        "waiver_assessment_and_disclosure",
        "privilege_counsel",
        "P1",
        {"PRIV-COBALT-SELLER-WAIVER"},
        {"CR-06"},
    ),
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_candidate_path(raw_path: Optional[str]) -> Path:
    if not raw_path:
        return DEFAULT_CANDIDATE
    path = Path(raw_path).resolve()
    if path.is_dir():
        return path / "answer.json"
    return path


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def norm_token(value: Any) -> str:
    return norm(value).replace("-", "_").replace(" ", "_")


def norm_id(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().upper()


def id_set(values: Iterable[Any]) -> set:
    return {norm_id(value) for value in values if norm_id(value)}


def str_set(values: Iterable[Any]) -> set:
    return {str(value).strip() for value in values if str(value).strip()}


def int_value(value: Any) -> Optional[int]:
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


def bool_value(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = norm(value)
        if text == "true":
            return True
        if text == "false":
            return False
    return None


def record_refs(record: dict[str, Any]) -> set:
    refs = set()
    for key in [
        "issue_id",
        "correction_id",
        "action_id",
        "finding_id",
        "defect_id",
        "source_id",
        "doc_id",
        "document_id",
        "linked_qc_id",
    ]:
        if key in record:
            refs.add(norm_id(record.get(key)))
    for key in [
        "record_refs",
        "blocking_refs",
        "target_refs",
        "source_refs",
        "document_ids",
        "defect_refs",
    ]:
        refs.update(id_set(as_list(record.get(key))))
    return refs


def get_items(answer: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return [item for item in as_list(answer.get(key)) if isinstance(item, dict)]


def find_by_ref(answer: dict[str, Any], section: str, ref_id: str) -> dict[str, Any]:
    target = norm_id(ref_id)
    for item in get_items(answer, section):
        if target in record_refs(item):
            return item
    return {}


def find_category(answer: dict[str, Any], category_code: str) -> dict[str, Any]:
    target = norm_id(category_code)
    for item in get_items(answer, "readiness_statuses"):
        if norm_id(item.get("category_code")) == target:
            return item
    return {}


def categories(record: dict[str, Any], key: str = "category_impacts") -> set:
    if key in record:
        return id_set(as_list(record.get(key)))
    if "affected_categories" in record:
        return id_set(as_list(record.get("affected_categories")))
    category_code = record.get("category_code")
    return {norm_id(category_code)} if category_code else set()


def has_categories(record: dict[str, Any], expected: Iterable[str], exact: bool = True) -> bool:
    actual = categories(record)
    expected_set = id_set(expected)
    return actual == expected_set if exact else expected_set.issubset(actual)


def refs_include(record: dict[str, Any], expected: Iterable[str]) -> bool:
    return id_set(expected).issubset(record_refs(record))


def enum_is(record: dict[str, Any], key: str, expected: str) -> bool:
    return norm(record.get(key)) == norm(expected)


def enum_in(record: dict[str, Any], key: str, expected: Iterable[str]) -> bool:
    return norm_token(record.get(key)) in {norm_token(item) for item in expected}


def metric(answer: dict[str, Any], key: str) -> Any:
    metrics = as_dict(answer.get("metrics"))
    return metrics.get(key)


def action_by_rank(answer: dict[str, Any], rank: int) -> dict[str, Any]:
    for item in get_items(answer, "priority_actions"):
        if int_value(item.get("priority_rank") or item.get("rank")) == rank:
            return item
    return {}


def has_action(
    answer: dict[str, Any],
    action_type: str,
    owner: str,
    target_refs: Iterable[str],
    category_impacts: Iterable[str],
    source_obj: Optional[dict[str, Any]] = None,
    priority: Optional[str] = None,
) -> bool:
    candidates = get_items(answer, "priority_actions")
    if source_obj:
        candidates.append(source_obj)
    for item in candidates:
        if norm(item.get("action_type") or item.get("recommended_action") or item.get("action")) != norm(action_type):
            continue
        if norm(item.get("owner")) != norm(owner):
            continue
        if priority is not None and norm_id(item.get("priority")) != norm_id(priority):
            continue
        if not refs_include(item, target_refs):
            continue
        if not has_categories(item, category_impacts, exact=False):
            continue
        return True
    return False


def has_equivalent_action(
    answer: dict[str, Any],
    action_types: Iterable[str],
    owners: Iterable[str],
    target_refs: Iterable[str],
    category_impacts: Iterable[str],
    source_obj: Optional[dict[str, Any]] = None,
    priorities: Optional[Iterable[str]] = None,
) -> bool:
    candidates = get_items(answer, "priority_actions")
    if source_obj:
        candidates.append(source_obj)
    owner_set = {norm_token(owner) for owner in owners}
    action_set = {norm_token(action_type) for action_type in action_types}
    priority_set = {norm_id(priority) for priority in priorities} if priorities is not None else None
    for item in candidates:
        if (
            norm_token(item.get("action_type") or item.get("recommended_action") or item.get("action"))
            not in action_set
        ):
            continue
        if norm_token(item.get("owner")) not in owner_set:
            continue
        if priority_set is not None and norm_id(item.get("priority")) not in priority_set:
            continue
        if not refs_include(item, target_refs):
            continue
        if not has_categories(item, category_impacts, exact=False):
            continue
        return True
    return False


def check_sp001(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    cr06 = find_category(answer, "CR-06")
    cr11 = find_category(answer, "CR-11")
    cr15 = find_category(answer, "CR-15")
    ready = bool_value(metric(answer, "production_ready"))
    details = {
        "matter_id": norm_id(answer.get("matter_id")) == "MTR-COBALTRIDGE-GJ",
        "cr06_present": bool(cr06),
        "cr06_status": enum_in(
            cr06, "readiness_status", {"not_ready_zero_claim_contradicted", "not_ready_multiple_blockers"}
        ),
        "cr06_impact": enum_is(cr06, "production_impact", "multiple_impacts"),
        "cr06_refs": refs_include(
            cr06,
            [
                "DOC-COBALT-BANKER-SIDE",
                "QC-COBALT-ZERO-CR06",
                "SRC-COBALT-PARK-GMAIL",
                "PRIV-COBALT-SELLER-WAIVER",
            ],
        ),
        "cr11_status_and_ref": enum_is(cr11, "readiness_status", "not_ready_privilege_log_incomplete")
        and enum_is(cr11, "production_impact", "withheld_unlogged")
        and refs_include(cr11, ["PRIV-COBALT-LOG-GAP"]),
        "cr15_status_and_refs": enum_is(cr15, "readiness_status", "not_ready_personal_source_gap")
        and enum_in(cr15, "production_impact", {"partial_source_missing", "multiple_impacts"})
        and refs_include(cr15, ["SRC-COBALT-PARK-GMAIL", "SRC-COBALT-PARK-PHONE"]),
        "production_ready_false": ready is False,
    }
    return all(details.values()), details


def check_sp002(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    issue = find_by_ref(answer, "issue_ledger", "DOC-COBALT-BANKER-SIDE")
    details = {
        "issue_found": bool(issue),
        "qc_ref": refs_include(issue, ["QC-COBALT-ZERO-CR06"]),
        "issue_type": norm(issue.get("issue_type")) in {"zero_claim_contradiction", "responsive_miscoding"},
        "category_cr06": has_categories(issue, ["CR-06"]),
        "document_count_1": int_value(issue.get("document_count")) == 1
        or int_value(metric(answer, "miscoded_responsive_doc_count")) == 1,
        "current_coding_nonresponsive": enum_is(issue, "current_coding", "nonresponsive"),
        "not_produced": enum_is(issue, "produced_status", "not_produced"),
        "corrected_disposition": enum_is(issue, "corrected_disposition", "responsive_produce"),
    }
    return all(details.values()), details


def check_sp003(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    issue = find_by_ref(answer, "issue_ledger", "SRC-COBALT-PARK-GMAIL")
    details = {
        "issue_found": bool(issue),
        "issue_type": enum_is(issue, "issue_type", "personal_email_gap"),
        "issue_status": enum_is(issue, "issue_status", "not_collected"),
        "source_status": enum_is(issue, "source_status", "not_collected"),
        "categories": has_categories(issue, ["CR-06", "CR-15"]),
    }
    return all(details.values()), details


def check_sp004(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    issue = find_by_ref(answer, "issue_ledger", "SRC-COBALT-PARK-PHONE")
    details = {
        "issue_found": bool(issue),
        "issue_type": enum_is(issue, "issue_type", "personal_phone_gap"),
        "issue_status": enum_is(issue, "issue_status", "partial_collection"),
        "source_status": enum_is(issue, "source_status", "partial_collection"),
        "missing_signal": norm_token(issue.get("missing_component")) == "signal_messages",
        "categories": has_categories(issue, ["CR-15"]),
    }
    return all(details.values()), details


def check_sp005(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    correction = find_by_ref(answer, "privilege_corrections", "PRIV-COBALT-LOG-GAP")
    issue = find_by_ref(answer, "issue_ledger", "PRIV-COBALT-LOG-GAP")
    obj = correction or issue
    details = {
        "record_found": bool(obj),
        "status": norm(obj.get("privilege_status") or obj.get("issue_status")) == "incomplete_log",
        "correction_type": norm(obj.get("correction_type") or obj.get("issue_type"))
        in {
            "supplement_log",
            "privilege_log_gap",
        },
        "category_cr11": has_categories(obj, ["CR-11"]),
        "document_count_1290": int_value(obj.get("document_count")) == 1290,
        "withheld_1290": int_value(obj.get("withheld_count")) == 1290
        or int_value(metric(answer, "withheld_privilege_docs")) == 1290,
        "logged_480": int_value(obj.get("logged_count")) == 480
        or int_value(metric(answer, "logged_privilege_docs")) == 480,
        "unlogged_810": int_value(obj.get("unlogged_count")) == 810
        or int_value(metric(answer, "unlogged_privilege_docs")) == 810,
    }
    return all(details.values()), details


def check_sp006(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    correction = find_by_ref(answer, "privilege_corrections", "PRIV-COBALT-SELLER-WAIVER")
    issue = find_by_ref(answer, "issue_ledger", "PRIV-COBALT-SELLER-WAIVER")
    obj = correction or issue
    details = {
        "record_found": bool(obj),
        "status": norm(obj.get("privilege_status") or obj.get("issue_status")) == "waived",
        "correction_type": norm(obj.get("correction_type") or obj.get("issue_type"))
        in {
            "waiver_assessment",
            "third_party_waiver",
        },
        "category_cr06": has_categories(obj, ["CR-06"]),
        "document_count_6": int_value(obj.get("document_count")) == 6
        or int_value(metric(answer, "waived_privilege_doc_count")) == 6,
        "withheld_6": int_value(obj.get("withheld_count")) == 6,
        "logged_6": int_value(obj.get("logged_count")) == 6,
        "third_party": norm_token(obj.get("third_party")) == "seller_side_banker",
    }
    return all(details.values()), details


def check_sp007(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    metrics = as_dict(answer.get("metrics"))
    details = {}
    passed = True
    for key, expected in EXPECTED_METRICS.items():
        actual = bool_value(metrics.get(key)) if isinstance(expected, bool) else int_value(metrics.get(key))
        key_pass = actual == expected
        details[key] = {"expected": expected, "actual": metrics.get(key), "passed": key_pass}
        passed = passed and key_pass
    return passed, details


def check_sp008(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    ranks_seen = set()
    duplicate_rank = False
    for item in get_items(answer, "priority_actions"):
        rank = int_value(item.get("priority_rank") or item.get("rank"))
        if rank is None:
            continue
        if rank in ranks_seen:
            duplicate_rank = True
        ranks_seen.add(rank)

    details: dict[str, Any] = {"duplicate_rank": duplicate_rank, "rank_checks": []}
    passed = not duplicate_rank
    action_aliases = {
        "recode_and_produce": {"recode_and_produce", "qc_remediation"},
        "collect_personal_email": {"collect_personal_email"},
        "collect_signal_messages": {"collect_signal_messages"},
        "supplement_privilege_log": {"supplement_privilege_log"},
        "waiver_assessment_and_disclosure": {"waiver_assessment_and_disclosure"},
    }
    owner_aliases = {
        "review_qc": {"review_qc", "review_vendor"},
        "forensics": {"forensics", "ediscovery_vendor"},
        "privilege_team": {"privilege_team", "privilege_counsel"},
        "privilege_counsel": {"privilege_counsel", "outside_counsel"},
    }
    for rank, expected in enumerate(EXPECTED_ACTIONS, start=1):
        action_type, owner, priority, refs, cats = expected
        actual = action_by_rank(answer, rank)
        rank_pass = (
            norm_token(actual.get("action_type") or actual.get("recommended_action") or actual.get("action"))
            in action_aliases.get(action_type, {action_type})
            and norm_token(actual.get("owner")) in owner_aliases.get(owner, {owner})
            and norm_id(actual.get("priority")) in {"P0", "P1", "P2"}
            and refs_include(actual, refs)
            and has_categories(actual, cats, exact=False)
        )
        passed = passed and rank_pass
        details["rank_checks"].append(
            {
                "rank": rank,
                "expected_action": action_type,
                "actual_action_at_rank": actual.get("action_type") or actual.get("action"),
                "target_refs_at_rank": sorted(record_refs(actual)),
                "category_impacts_at_rank": sorted(categories(actual)),
                "passed": rank_pass,
            }
        )
    return passed, details


CHECKS = {
    "SP001": check_sp001,
    "SP002": check_sp002,
    "SP003": check_sp003,
    "SP004": check_sp004,
    "SP005": check_sp005,
    "SP006": check_sp006,
    "SP007": check_sp007,
    "SP008": check_sp008,
}


def score_answer(answer: dict[str, Any], parse_error: Optional[str] = None) -> dict[str, Any]:
    rubric = load_json(RUBRIC_PATH)["rubric"]
    total_weight = sum(point["weight"] for point in rubric)
    score = 0.0
    points = []
    for point in rubric:
        assigned = point["weight"] / total_weight
        if parse_error:
            passed = False
            details: dict[str, Any] = {"parse_error": parse_error}
        else:
            passed, details = CHECKS[point["id"]](answer)
        earned = assigned if passed else 0.0
        score += earned
        points.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "assigned_score": round(assigned, 10),
                "passed": bool(passed),
                "earned_score": round(earned, 10),
                "details": details,
            }
        )
    return {
        "task_id": "test_004",
        "score": round(score, 10),
        "max_score": 1.0,
        "scoring_policy": "Each rubric point earns all assigned weight or zero; no within-point partial credit.",
        "points": points,
    }


def main() -> int:
    candidate_path = resolve_candidate_path(sys.argv[1] if len(sys.argv) > 1 else None)
    try:
        answer = load_json(candidate_path)
        if not isinstance(answer, dict):
            raise ValueError("candidate answer must be a JSON object")
        result = score_answer(answer)
    except Exception as exc:
        result = score_answer({}, parse_error=str(exc))
    result["candidate_path"] = str(candidate_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
