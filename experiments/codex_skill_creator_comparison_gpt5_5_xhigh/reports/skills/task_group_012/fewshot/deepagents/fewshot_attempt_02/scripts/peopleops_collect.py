#!/usr/bin/env python3
"""Collect filtered PeopleOps Console evidence from permitted API endpoints."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


def fetch_text(base_url: str, path: str) -> str:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=15) as response:
        return response.read().decode("utf-8")


def fetch_json(base_url: str, path: str) -> Any:
    return json.loads(fetch_text(base_url, path))


def maybe_fetch_json(base_url: str, path: str) -> Any:
    try:
        return fetch_json(base_url, path)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}


def maybe_fetch_attachment(base_url: str, attachment_id: str) -> Any:
    try:
        text = fetch_text(base_url, f"/api/attachments/{attachment_id}")
    except (HTTPError, URLError, TimeoutError) as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"attachment_id": attachment_id, "content": text}


def text_contains(record: Any, needles: set[str]) -> bool:
    if not needles:
        return False
    haystack = json.dumps(record, sort_keys=True, ensure_ascii=False).lower()
    return any(needle.lower() in haystack for needle in needles if needle)


def add_unique(items: list[str], value: str | None) -> None:
    if value and value not in items:
        items.append(value)


def filter_records(records: Any, needles: set[str]) -> list[Any]:
    if not isinstance(records, list):
        return []
    return [record for record in records if text_contains(record, needles)]


def collect(base_url: str, employee_id: str | None, case_id: str | None, opening_id: str | None) -> dict[str, Any]:
    target_ids = {value for value in (employee_id, case_id, opening_id) if value}

    evidence: dict[str, Any] = {
        "targets": {
            "employee_id": employee_id,
            "case_id": case_id,
            "opening_id": opening_id,
        },
        "manifest": maybe_fetch_json(base_url, "/api/manifest"),
        "summary": maybe_fetch_json(base_url, "/api/summary"),
    }

    employees = maybe_fetch_json(base_url, "/api/employees")
    cases = maybe_fetch_json(base_url, "/api/cases")
    recruitment = maybe_fetch_json(base_url, "/api/recruitment")
    ledgers = maybe_fetch_json(base_url, "/api/payroll-ledgers")
    documents = maybe_fetch_json(base_url, "/api/documents")
    messages = maybe_fetch_json(base_url, "/api/messages")
    notifications = maybe_fetch_json(base_url, "/api/notifications")
    audit = maybe_fetch_json(base_url, "/api/audit")

    evidence["employees"] = filter_records(employees, {employee_id} if employee_id else set())
    evidence["cases"] = filter_records(cases, target_ids)
    evidence["recruitment"] = filter_records(recruitment, {opening_id} if opening_id else set())
    evidence["payroll_ledgers"] = filter_records(ledgers, {employee_id} if employee_id else set())
    evidence["documents"] = filter_records(documents, target_ids)
    evidence["messages"] = filter_records(messages, target_ids)
    evidence["notifications"] = filter_records(notifications, target_ids)
    evidence["audit"] = filter_records(audit, target_ids)

    case_ids: list[str] = []
    add_unique(case_ids, case_id)
    for case in evidence["cases"]:
        add_unique(case_ids, case.get("case_id") if isinstance(case, dict) else None)

    case_details: dict[str, Any] = {}
    policy_ids: list[str] = []
    attachment_ids: list[str] = []
    for cid in case_ids:
        detail = maybe_fetch_json(base_url, f"/api/cases/{cid}")
        case_details[cid] = detail
        if isinstance(detail, dict):
            for policy_id in detail.get("policy_refs", []):
                add_unique(policy_ids, policy_id)
            for attachment in detail.get("attachments", []):
                if isinstance(attachment, dict):
                    add_unique(attachment_ids, attachment.get("attachment_id"))
    evidence["case_details"] = case_details

    policies_index = maybe_fetch_json(base_url, "/api/policies")
    if isinstance(policies_index, list):
        for policy in policies_index:
            if isinstance(policy, dict) and text_contains(policy, target_ids):
                add_unique(policy_ids, policy.get("policy_id"))
    evidence["policies_index"] = policies_index
    evidence["policy_details"] = {
        policy_id: maybe_fetch_json(base_url, f"/api/policies/{policy_id}")
        for policy_id in policy_ids
    }

    audit_ids: list[str] = []
    for record in evidence["audit"]:
        if isinstance(record, dict):
            add_unique(audit_ids, record.get("audit_id"))
    for detail in case_details.values():
        if isinstance(detail, dict):
            for record in detail.get("audit_events", []):
                if isinstance(record, dict):
                    add_unique(audit_ids, record.get("audit_id"))
    evidence["audit_details"] = {
        audit_id: maybe_fetch_json(base_url, f"/api/audit/{audit_id}")
        for audit_id in audit_ids
    }

    evidence["attachment_details"] = {
        attachment_id: maybe_fetch_attachment(base_url, attachment_id)
        for attachment_id in attachment_ids
    }

    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument("--employee-id", help="Target employee ID")
    parser.add_argument("--case-id", help="Target case ID")
    parser.add_argument("--opening-id", help="Target recruitment opening ID")
    args = parser.parse_args()

    evidence = collect(args.base_url, args.employee_id, args.case_id, args.opening_id)
    json.dump(evidence, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
