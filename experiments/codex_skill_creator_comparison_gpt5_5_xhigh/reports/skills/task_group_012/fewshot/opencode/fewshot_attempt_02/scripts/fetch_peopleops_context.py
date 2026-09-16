#!/usr/bin/env python3
"""Fetch and search allowed PeopleOps task-environment API endpoints."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


LIST_ENDPOINTS = {
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


def get_json(base_url: str, path: str) -> Any:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def contains_query(value: Any, query: str) -> bool:
    needle = query.casefold()
    if isinstance(value, dict):
        return any(contains_query(v, query) for v in value.values())
    if isinstance(value, list):
        return any(contains_query(v, query) for v in value)
    return needle in str(value).casefold()


def index_matches(data: dict[str, Any], queries: list[str]) -> dict[str, list[Any]]:
    if not queries:
        return {}
    matches: dict[str, list[Any]] = {}
    for name, records in data.items():
        if isinstance(records, list):
            found = [record for record in records if any(contains_query(record, q) for q in queries)]
            if found:
                matches[name] = found
        elif any(contains_query(records, q) for q in queries):
            matches[name] = [records]
    return matches


def fetch_details(base_url: str, args: argparse.Namespace) -> dict[str, Any]:
    details: dict[str, Any] = {}
    for case_id in args.case_id:
        details[f"case:{case_id}"] = get_json(base_url, f"/api/cases/{case_id}")
    for policy_id in args.policy_id:
        details[f"policy:{policy_id}"] = get_json(base_url, f"/api/policies/{policy_id}")
    for audit_id in args.audit_id:
        details[f"audit:{audit_id}"] = get_json(base_url, f"/api/audit/{audit_id}")
    for attachment_id in args.attachment_id:
        details[f"attachment:{attachment_id}"] = get_json(base_url, f"/api/attachments/{attachment_id}")
    return details


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL, e.g. http://task-env:9012/")
    parser.add_argument("--query", action="append", default=[], help="Case, employee, candidate, opening, audit, or record id/name to search for")
    parser.add_argument("--case-id", action="append", default=[], help="Fetch /api/cases/{case_id}")
    parser.add_argument("--policy-id", action="append", default=[], help="Fetch /api/policies/{policy_id}")
    parser.add_argument("--audit-id", action="append", default=[], help="Fetch /api/audit/{audit_id}")
    parser.add_argument("--attachment-id", action="append", default=[], help="Fetch /api/attachments/{attachment_id}")
    parser.add_argument("--out", help="Write JSON snapshot to this path instead of stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        endpoints = {name: get_json(args.base_url, path) for name, path in LIST_ENDPOINTS.items()}
        details = fetch_details(args.base_url, args)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"fetch_peopleops_context: {exc}", file=sys.stderr)
        return 2

    snapshot = {
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "base_url": args.base_url,
        "queries": args.query,
        "endpoints": endpoints,
        "details": details,
        "matches": index_matches({**endpoints, **details}, args.query),
    }
    text = json.dumps(snapshot, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
