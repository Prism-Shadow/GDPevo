#!/usr/bin/env python3
"""Collect relevant PeopleOps evidence from the task environment."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = os.environ.get("TASK_ENV_BASE_URL", "http://task-env:9012/")
TIMEOUT_SECONDS = 20


def fetch_json(base_url: str, path: str):
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"GET {path} failed with HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"GET {path} failed: {exc.reason}") from exc
    except ValueError as exc:
        raise RuntimeError(f"GET {path} returned invalid JSON") from exc


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_needles(values: Iterable[str]) -> list[str]:
    needles: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        value = str(value).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        needles.append(value)
    return needles


def word_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    for char in text:
        if char.isalnum():
            current.append(char)
            continue
        if current:
            token = "".join(current)
            if len(token) >= 3:
                tokens.append(token)
            current = []
    if current:
        token = "".join(current)
        if len(token) >= 3:
            tokens.append(token)
    return tokens


def record_text(record) -> str:
    return json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def matches(record, needles: list[str]) -> bool:
    if not needles:
        return True
    haystack = record_text(record)
    return any(needle in haystack for needle in needles)


def filter_collection(items, needles: list[str]):
    if not isinstance(items, list):
        return []
    return [item for item in items if matches(item, needles)]


def exact_match(value, options: Iterable[str]) -> bool:
    option_set = set(options)
    if not option_set:
        return False
    if value is None:
        return False
    return str(value) in option_set


def match_employee_record(record: dict, employee_ids: list[str], employee_names: list[str]) -> bool:
    if not employee_ids and not employee_names:
        return True
    return exact_match(record.get("employee_id"), employee_ids) or exact_match(record.get("name"), employee_names)


def match_case_record(
    record: dict,
    case_ids: list[str],
    employee_ids: list[str],
    employee_names: list[str],
) -> bool:
    if not case_ids and not employee_ids and not employee_names:
        return True
    if exact_match(record.get("case_id"), case_ids):
        return True
    if exact_match(record.get("employee_id"), employee_ids):
        return True
    if exact_match(record.get("employee_name"), employee_names):
        return True
    return False


def match_payroll_record(record: dict, employee_ids: list[str], employee_names: list[str]) -> bool:
    if not employee_ids and not employee_names:
        return True
    return exact_match(record.get("employee_id"), employee_ids) or exact_match(record.get("employee_name"), employee_names)


def match_policy_record(record: dict, policy_ids: list[str]) -> bool:
    if not policy_ids:
        return True
    return exact_match(record.get("policy_id"), policy_ids)


def match_audit_record(
    record: dict,
    case_ids: list[str],
    employee_ids: list[str],
    audit_ids: list[str],
) -> bool:
    if not case_ids and not employee_ids and not audit_ids:
        return True
    if exact_match(record.get("audit_id"), audit_ids):
        return True
    if exact_match(record.get("case_id"), case_ids):
        return True
    return exact_match(record.get("employee_id"), employee_ids)


def match_message_record(
    record: dict,
    case_ids: list[str],
    recipients: list[str],
    message_ids: list[str],
) -> bool:
    if not case_ids and not recipients and not message_ids:
        return True
    if exact_match(record.get("message_id"), message_ids):
        return True
    if exact_match(record.get("case_id"), case_ids):
        return True
    return exact_match(record.get("recipient"), recipients)


def match_recruitment_record(
    record: dict,
    opening_ids: list[str],
    candidate_ids: list[str],
) -> bool:
    if not opening_ids and not candidate_ids:
        return True
    if exact_match(record.get("opening_id"), opening_ids):
        return True
    for candidate in as_list(record.get("candidates")):
        if exact_match(candidate.get("candidate_id"), candidate_ids):
            return True
    for offer in as_list(record.get("offer_register")):
        if exact_match(offer.get("candidate_id"), candidate_ids):
            return True
    for packet in as_list(record.get("notice_packets")):
        if exact_match(packet.get("candidate_id"), candidate_ids):
            return True
    for candidate in as_list(record.get("candidates")):
        if exact_match(candidate.get("candidate_id"), opening_ids):
            return True
    return False


def collect_case_details(base_url: str, case_ids: list[str]):
    details = []
    for case_id in case_ids:
        if not case_id:
            continue
        try:
            details.append(fetch_json(base_url, f"/api/cases/{case_id}"))
        except RuntimeError:
            continue
    return details


def collect_attachments(base_url: str, case_details: list[dict]):
    attachment_ids: list[str] = []
    for case in case_details:
        for attachment in as_list(case.get("attachments")):
            attachment_id = attachment.get("attachment_id")
            if attachment_id:
                attachment_ids.append(str(attachment_id))
    attachment_ids = normalize_needles(attachment_ids)

    attachments = []
    for attachment_id in attachment_ids:
        try:
            attachments.append(fetch_json(base_url, f"/api/attachments/{attachment_id}"))
        except RuntimeError:
            continue
    return attachments


def collect_requested_ids(args) -> list[str]:
    raw_values: list[str] = []
    raw_values.extend(as_list(args.employee_id))
    raw_values.extend(as_list(args.case_id))
    raw_values.extend(as_list(args.opening_id))
    raw_values.extend(as_list(args.policy_id))
    raw_values.extend(as_list(args.audit_id))
    raw_values.extend(as_list(args.candidate_id))
    raw_values.extend(as_list(args.attachment_id))
    return normalize_needles(raw_values)


def gather_case_relations(case_details: list[dict]) -> dict[str, list[str]]:
    relation_map: dict[str, list[str]] = {
        "case_ids": [],
        "employee_ids": [],
        "employee_names": [],
        "employee_name_tokens": [],
        "policy_ids": [],
        "approval_ids": [],
        "attachment_ids": [],
        "attachment_names": [],
        "audit_ids": [],
    }
    for case in case_details:
        if case.get("case_id"):
            relation_map["case_ids"].append(str(case["case_id"]))
        if case.get("employee_id"):
            relation_map["employee_ids"].append(str(case["employee_id"]))
        if case.get("employee_name"):
            relation_map["employee_names"].append(str(case["employee_name"]))
            relation_map["employee_name_tokens"].extend(word_tokens(str(case["employee_name"])))
        relation_map["policy_ids"].extend(as_list(case.get("policy_refs")))
        for approval in as_list(case.get("approvals")):
            if approval.get("approval_id"):
                relation_map["approval_ids"].append(str(approval["approval_id"]))
        for attachment in as_list(case.get("attachments")):
            if attachment.get("attachment_id"):
                relation_map["attachment_ids"].append(str(attachment["attachment_id"]))
            if attachment.get("name"):
                relation_map["attachment_names"].append(str(attachment["name"]))
        for audit_event in as_list(case.get("audit_events")):
            if audit_event.get("audit_id"):
                relation_map["audit_ids"].append(str(audit_event["audit_id"]))
    return {key: normalize_needles(values) for key, values in relation_map.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--employee-id", action="append", default=[])
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--opening-id", action="append", default=[])
    parser.add_argument("--policy-id", action="append", default=[])
    parser.add_argument("--audit-id", action="append", default=[])
    parser.add_argument("--candidate-id", action="append", default=[])
    parser.add_argument("--attachment-id", action="append", default=[])
    args = parser.parse_args()

    base_url = args.base_url
    requested_needles = collect_requested_ids(args)

    manifest = fetch_json(base_url, "/api/manifest")
    summary = fetch_json(base_url, "/api/summary")

    employees = fetch_json(base_url, "/api/employees")
    cases = fetch_json(base_url, "/api/cases")
    payroll_ledgers = fetch_json(base_url, "/api/payroll-ledgers")
    recruitment = fetch_json(base_url, "/api/recruitment")
    documents = fetch_json(base_url, "/api/documents")
    messages = fetch_json(base_url, "/api/messages")
    audit = fetch_json(base_url, "/api/audit")
    policies = fetch_json(base_url, "/api/policies")

    if requested_needles:
        filtered_cases = [
            record
            for record in cases
            if exact_match(record.get("case_id"), requested_needles)
            or exact_match(record.get("employee_id"), requested_needles)
        ]
    else:
        filtered_cases = cases
    case_ids = normalize_needles(
        [*args.case_id, *args.opening_id, *(case.get("case_id") for case in filtered_cases)]
    )
    case_details = collect_case_details(base_url, case_ids)
    relations = gather_case_relations(case_details)

    employee_ids = normalize_needles([*requested_needles, *relations["employee_ids"]])
    employee_names = relations["employee_names"]
    case_ids_for_filter = normalize_needles([*requested_needles, *relations["case_ids"]])
    policy_ids = normalize_needles([*requested_needles, *relations["policy_ids"]])
    audit_ids = normalize_needles([*requested_needles, *relations["audit_ids"]])
    candidate_ids = normalize_needles([*args.candidate_id])
    opening_ids = normalize_needles([*args.opening_id, *relations["case_ids"]])

    employees = [record for record in employees if match_employee_record(record, employee_ids, employee_names)]
    cases = [
        record
        for record in cases
        if match_case_record(record, case_ids_for_filter, relations["employee_ids"], employee_names)
    ]
    payroll_ledgers = [
        record for record in payroll_ledgers if match_payroll_record(record, employee_ids, employee_names)
    ]
    recruitment = [
        record for record in recruitment if match_recruitment_record(record, opening_ids, candidate_ids)
    ]
    documents = filter_collection(
        documents,
        normalize_needles(
            [
                *requested_needles,
                *relations["case_ids"],
                *relations["employee_ids"],
                *relations["employee_name_tokens"],
                *relations["policy_ids"],
                *relations["attachment_names"],
                *relations["attachment_ids"],
            ]
        ),
    )
    messages = filter_collection(
        messages,
        [],
    )
    messages = [
        record
        for record in messages
        if match_message_record(record, case_ids_for_filter, relations["employee_names"], requested_needles)
    ]
    audit = [record for record in audit if match_audit_record(record, case_ids_for_filter, relations["employee_ids"], audit_ids)]
    policies = [record for record in policies if match_policy_record(record, policy_ids)]

    attachments = collect_attachments(base_url, case_details)

    bundle = {
        "manifest": manifest,
        "summary": summary,
        "employees": employees,
        "cases": cases,
        "case_details": case_details,
        "payroll_ledgers": payroll_ledgers,
        "recruitment": recruitment,
        "documents": documents,
        "messages": messages,
        "audit": audit,
        "policies": policies,
        "attachments": attachments,
    }

    json.dump(bundle, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
