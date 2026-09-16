#!/usr/bin/env python3
"""Collect a compact PeopleOps evidence bundle from the task environment."""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = os.environ.get("TASK_ENV_BASE_URL", "http://task-env:9012")


def fetch_json(base_url: str, path: str) -> Any:
    url = base_url.rstrip("/") + path
    with urllib.request.urlopen(url) as response:
        return json.load(response)


def text_match(value: Any, needles: list[str]) -> bool:
    if not needles:
        return False
    haystack = json.dumps(value, sort_keys=True, ensure_ascii=False).lower()
    return any(needle.lower() in haystack for needle in needles)


def collect_terms(*values: Any) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()

    def add(term: str) -> None:
        term = term.strip()
        if len(term) < 3:
            return
        key = term.lower()
        if key not in seen:
            seen.add(key)
            terms.append(term)

    def walk(value: Any) -> None:
        if not value:
            return
        if isinstance(value, str):
            add(value)
            return
        if isinstance(value, list):
            for item in value:
                walk(item)
            return
        if isinstance(value, dict):
            for item in value.values():
                walk(item)

    for value in values:
        walk(value)

    return terms


def collect_name_terms(*names: Any) -> list[str]:
    terms: list[str] = []
    for name in names:
        if not isinstance(name, str) or not name.strip():
            continue
        terms.append(name)
        for part in re.split(r"[\s/]+", name.strip()):
            if len(part) >= 3 and part not in terms:
                terms.append(part)
    return terms


def find_case(cases: list[dict[str, Any]], case_id: str | None, employee_id: str | None) -> dict[str, Any] | None:
    for case in cases:
        if case_id and case.get("case_id") == case_id:
            return case
        if employee_id and case.get("employee_id") == employee_id:
            return case
    return None


def find_recruitment(recruitment: list[dict[str, Any]], opening_id: str | None) -> dict[str, Any] | None:
    if not opening_id:
        return None
    for item in recruitment:
        if item.get("opening_id") == opening_id:
            return item
    return None


def relevant_documents(documents: list[dict[str, Any]], needles: list[str]) -> list[dict[str, Any]]:
    if not needles:
        return documents
    return [doc for doc in documents if text_match(doc, needles)]


def relevant_messages(messages: list[dict[str, Any]], needles: list[str]) -> list[dict[str, Any]]:
    if not needles:
        return messages
    return [msg for msg in messages if text_match(msg, needles)]


def relevant_audit(audit: list[dict[str, Any]], needles: list[str]) -> list[dict[str, Any]]:
    if not needles:
        return audit
    return [event for event in audit if text_match(event, needles)]


def relevant_payroll_ledgers(rows: list[dict[str, Any]], employee_id: str | None, needles: list[str]) -> list[dict[str, Any]]:
    if not employee_id:
        return []
    rows = [row for row in rows if row.get("employee_id") == employee_id]
    if needles:
        rows = [row for row in rows if text_match(row, needles)] or rows
    return rows


def relevant_employees(rows: list[dict[str, Any]], employee_id: str | None) -> list[dict[str, Any]]:
    if not employee_id:
        return []
    return [row for row in rows if row.get("employee_id") == employee_id]


def relevant_policies(rows: list[dict[str, Any]], policy_refs: list[str]) -> list[dict[str, Any]]:
    if not policy_refs:
        return rows
    wanted = {ref for ref in policy_refs}
    return [row for row in rows if row.get("policy_id") in wanted]


def build_bundle(args: argparse.Namespace) -> dict[str, Any]:
    manifest = fetch_json(args.base_url, "/api/manifest")
    summary = fetch_json(args.base_url, "/api/summary")
    cases = fetch_json(args.base_url, "/api/cases")
    employees = fetch_json(args.base_url, "/api/employees")
    policies = fetch_json(args.base_url, "/api/policies")
    payroll_ledgers = fetch_json(args.base_url, "/api/payroll-ledgers")
    recruitment = fetch_json(args.base_url, "/api/recruitment")
    documents = fetch_json(args.base_url, "/api/documents")
    messages = fetch_json(args.base_url, "/api/messages")
    audit = fetch_json(args.base_url, "/api/audit")

    focus_strings: list[str] = [v for v in [args.case_id, args.employee_id, args.opening_id, args.candidate_id] if v]

    case = find_case(cases, args.case_id, args.employee_id)
    recruitment_item = find_recruitment(recruitment, args.opening_id)
    linked_employee_id = args.employee_id or (case or {}).get("employee_id")

    employee_record = None
    if linked_employee_id:
        for row in employees:
            if row.get("employee_id") == linked_employee_id:
                employee_record = row
                break

    policy_refs = list((case or {}).get("policy_refs", []))

    search_terms = collect_terms(
        focus_strings,
        (case or {}).get("case_id"),
        (case or {}).get("employee_id"),
        (case or {}).get("title"),
        (case or {}).get("summary"),
        (employee_record or {}).get("email"),
        (employee_record or {}).get("department"),
    )
    search_terms = collect_terms(
        search_terms,
        collect_name_terms(
            (case or {}).get("employee_name"),
            (employee_record or {}).get("name"),
        ),
    )

    if recruitment_item:
        recruitment_candidate_terms: list[str] = []
        for candidate in recruitment_item.get("candidates", []):
            if isinstance(candidate, dict):
                recruitment_candidate_terms.extend(
                    [
                        candidate.get("candidate_id"),
                        candidate.get("name"),
                        *collect_name_terms(candidate.get("name")),
                    ]
                )
        for offer in recruitment_item.get("offer_register", []):
            if isinstance(offer, dict):
                recruitment_candidate_terms.extend(
                    [
                        offer.get("offer_id"),
                        offer.get("candidate_id"),
                    ]
                )
        for packet in recruitment_item.get("notice_packets", []):
            if isinstance(packet, dict):
                recruitment_candidate_terms.extend(
                    [
                        packet.get("message_id"),
                        packet.get("candidate_id"),
                    ]
                )
        for record in recruitment_item.get("payroll_precheck_records", []):
            if isinstance(record, dict):
                recruitment_candidate_terms.extend(
                    [
                        record.get("record_id"),
                        record.get("candidate_id"),
                    ]
                )
        for cost in recruitment_item.get("cost_ledger", []):
            if isinstance(cost, dict):
                recruitment_candidate_terms.append(cost.get("line_id"))

        recruitment_terms: list[str] = collect_terms(
            recruitment_item.get("opening_id"),
            recruitment_candidate_terms,
        )
        search_terms = collect_terms(search_terms, recruitment_terms)

    bundle = {
        "request": {
            "case_id": args.case_id,
            "employee_id": args.employee_id,
            "opening_id": args.opening_id,
            "candidate_id": args.candidate_id,
        },
        "manifest": manifest,
        "summary": summary,
        "cases": [case] if case else [],
        "employees": relevant_employees(employees, linked_employee_id),
        "policies": relevant_policies(policies, policy_refs),
        "payroll_ledgers": relevant_payroll_ledgers(payroll_ledgers, linked_employee_id, search_terms),
        "recruitment": [recruitment_item] if recruitment_item else [],
        "documents": relevant_documents(documents, search_terms),
        "messages": relevant_messages(messages, search_terms),
        "audit": relevant_audit(audit, search_terms),
    }

    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--case-id")
    parser.add_argument("--employee-id")
    parser.add_argument("--opening-id")
    parser.add_argument("--candidate-id")
    args = parser.parse_args()

    try:
        bundle = build_bundle(args)
    except urllib.error.URLError as exc:
        print(f"Failed to fetch task environment data: {exc}", file=sys.stderr)
        return 1

    json.dump(bundle, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
