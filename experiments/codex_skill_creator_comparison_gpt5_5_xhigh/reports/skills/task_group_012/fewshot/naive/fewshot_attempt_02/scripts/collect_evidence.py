#!/usr/bin/env python3
"""Collect read-only PeopleOps evidence from a task environment."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


COLLECTIONS = {
    "manifest": "/api/manifest",
    "summary": "/api/summary",
    "employees": "/api/employees",
    "cases": "/api/cases",
    "policies": "/api/policies",
    "payroll_ledgers": "/api/payroll-ledgers",
    "recruitment": "/api/recruitment",
    "documents": "/api/documents",
    "messages": "/api/messages",
    "notifications": "/api/notifications",
    "audit": "/api/audit",
}


def fetch_text(base_url: str, path: str) -> str:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    with urllib.request.urlopen(url, timeout=15) as response:
        return response.read().decode("utf-8")


def fetch_json(base_url: str, path: str) -> Any:
    return json.loads(fetch_text(base_url, path))


def fetch_attachment(base_url: str, path: str) -> Any:
    data = fetch_text(base_url, path)
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return {"content": data}


def as_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False).lower()


def record_matches(record: Any, terms: list[str]) -> bool:
    if not terms:
        return True
    haystack = as_text(record)
    return any(term.lower() in haystack for term in terms if term)


def add_terms(values: list[str | None]) -> list[str]:
    terms: list[str] = []
    for value in values:
        if value and value not in terms:
            terms.append(value)
    return terms


def collect(args: argparse.Namespace) -> dict[str, Any]:
    terms = add_terms(
        args.term
        + args.employee_id
        + args.case_id
        + args.opening_id
        + args.candidate_id
        + args.policy_id
        + args.audit_id
    )
    result: dict[str, Any] = {
        "base_url": args.base_url.rstrip("/"),
        "query_terms": terms,
        "collections": {},
        "details": {"cases": {}, "policies": {}, "audit": {}, "attachments": {}},
        "errors": [],
    }

    collections: dict[str, Any] = {}
    for name, path in COLLECTIONS.items():
        try:
            data = fetch_json(args.base_url, path)
            collections[name] = data
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            result["errors"].append({"endpoint": path, "error": str(exc)})

    for name, data in collections.items():
        if args.full or name in {"manifest", "summary"}:
            result["collections"][name] = data
        elif isinstance(data, list):
            result["collections"][name] = [record for record in data if record_matches(record, terms)]
        else:
            result["collections"][name] = data if record_matches(data, terms) else {}

    case_ids = add_terms(args.case_id + args.opening_id)
    policy_ids = add_terms(args.policy_id)
    audit_ids = add_terms(args.audit_id)
    attachment_ids = add_terms(args.attachment_id)

    for case_id in case_ids:
        try:
            detail = fetch_json(args.base_url, f"/api/cases/{urllib.parse.quote(case_id, safe='')}")
            result["details"]["cases"][case_id] = detail
            policy_ids.extend(
                policy_id
                for policy_id in detail.get("policy_refs", [])
                if isinstance(policy_id, str) and policy_id not in policy_ids
            )
            audit_ids.extend(
                event.get("audit_id")
                for event in detail.get("audit_events", [])
                if isinstance(event, dict)
                and isinstance(event.get("audit_id"), str)
                and event.get("audit_id") not in audit_ids
            )
            attachment_ids.extend(
                item.get("attachment_id")
                for item in detail.get("attachments", [])
                if isinstance(item, dict)
                and isinstance(item.get("attachment_id"), str)
                and item.get("attachment_id") not in attachment_ids
            )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            result["errors"].append({"endpoint": f"/api/cases/{case_id}", "error": str(exc)})

    for policy_id in policy_ids:
        try:
            result["details"]["policies"][policy_id] = fetch_json(
                args.base_url, f"/api/policies/{urllib.parse.quote(policy_id, safe='')}"
            )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            result["errors"].append({"endpoint": f"/api/policies/{policy_id}", "error": str(exc)})

    for audit_id in audit_ids:
        try:
            result["details"]["audit"][audit_id] = fetch_json(
                args.base_url, f"/api/audit/{urllib.parse.quote(audit_id, safe='')}"
            )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            result["errors"].append({"endpoint": f"/api/audit/{audit_id}", "error": str(exc)})

    for attachment_id in attachment_ids:
        try:
            result["details"]["attachments"][attachment_id] = fetch_attachment(
                args.base_url, f"/api/attachments/{urllib.parse.quote(attachment_id, safe='')}"
            )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            result["errors"].append({"endpoint": f"/api/attachments/{attachment_id}", "error": str(exc)})

    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Task environment base URL, for example http://task-env:9012/")
    parser.add_argument("--employee-id", action="append", default=[], help="Employee id to filter for")
    parser.add_argument("--case-id", action="append", default=[], help="Case id to fetch and filter for")
    parser.add_argument("--opening-id", action="append", default=[], help="Recruitment opening id to filter for")
    parser.add_argument("--candidate-id", action="append", default=[], help="Candidate id to filter for")
    parser.add_argument("--policy-id", action="append", default=[], help="Policy id to fetch")
    parser.add_argument("--audit-id", action="append", default=[], help="Audit id to fetch")
    parser.add_argument("--attachment-id", action="append", default=[], help="Attachment id to fetch")
    parser.add_argument("--term", action="append", default=[], help="Additional case-insensitive search term")
    parser.add_argument("--full", action="store_true", help="Include full collections instead of filtering by terms")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    evidence = collect(args)
    json.dump(evidence, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if not evidence["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
