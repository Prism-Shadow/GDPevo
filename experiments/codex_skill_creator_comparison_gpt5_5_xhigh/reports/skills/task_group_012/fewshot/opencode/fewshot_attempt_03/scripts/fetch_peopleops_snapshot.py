#!/usr/bin/env python3
"""Fetch a portable PeopleOps API snapshot for evidence reconciliation."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


LIST_ENDPOINTS = {
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


def normalize_base_url(base_url: str) -> str:
    if not base_url:
        raise ValueError("base_url is required")
    return base_url.rstrip("/") + "/"


def fetch_json(base_url: str, path: str) -> Any:
    url = urllib.parse.urljoin(base_url, path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {url} failed with HTTP {exc.code}: {body[:300]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GET {url} failed: {exc.reason}") from exc


def collect_snapshot(base_url: str, include_attachments: bool) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for name, path in {"manifest": "/api/manifest", "summary": "/api/summary"}.items():
        data[name] = fetch_json(base_url, path)

    for name, path in LIST_ENDPOINTS.items():
        data[name] = fetch_json(base_url, path)

    case_details: dict[str, Any] = {}
    for case in data.get("cases", []):
        case_id = case.get("case_id")
        if case_id:
            case_details[case_id] = fetch_json(base_url, f"/api/cases/{case_id}")
    data["case_details"] = case_details

    policy_details: dict[str, Any] = {}
    for policy in data.get("policies", []):
        policy_id = policy.get("policy_id")
        if policy_id:
            policy_details[policy_id] = fetch_json(base_url, f"/api/policies/{policy_id}")
    data["policy_details"] = policy_details

    audit_details: dict[str, Any] = {}
    for event in data.get("audit", []):
        audit_id = event.get("audit_id")
        if audit_id:
            audit_details[audit_id] = fetch_json(base_url, f"/api/audit/{audit_id}")
    data["audit_details"] = audit_details

    if include_attachments:
        attachment_ids = sorted(find_attachment_ids(data))
        attachments: dict[str, Any] = {}
        for attachment_id in attachment_ids:
            try:
                attachments[attachment_id] = fetch_json(base_url, f"/api/attachments/{attachment_id}")
            except RuntimeError as exc:
                attachments[attachment_id] = {"error": str(exc)}
        data["attachment_details"] = attachments

    return {
        "base_url": base_url,
        "fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data": data,
    }


def find_attachment_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "attachment_id" and isinstance(child, str):
                found.add(child)
            else:
                found.update(find_attachment_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(find_attachment_ids(child))
    return found


def contains_term(value: Any, terms: list[str]) -> bool:
    if not terms:
        return False
    if isinstance(value, (str, int, float, bool)) or value is None:
        text = str(value).lower()
        return any(term.lower() in text for term in terms)
    if isinstance(value, list):
        return any(contains_term(item, terms) for item in value)
    if isinstance(value, dict):
        return any(contains_term(k, terms) or contains_term(v, terms) for k, v in value.items())
    return False


def focused_matches(value: Any, terms: list[str]) -> Any:
    if not terms:
        return {}
    if isinstance(value, list):
        matches = [item for item in value if contains_term(item, terms)]
        return matches
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            if contains_term(key, terms):
                result[key] = child
                continue
            child_matches = focused_matches(child, terms)
            if child_matches not in ({}, []):
                result[key] = child_matches
        return result
    return value if contains_term(value, terms) else {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="PeopleOps task base URL, for example http://task-env:9012/")
    parser.add_argument("--out", default="-", help="Output JSON path, or '-' for stdout")
    parser.add_argument("--filter", action="append", default=[], help="Target ID/name term; repeatable")
    parser.add_argument(
        "--include-attachments",
        action="store_true",
        help="Fetch /api/attachments/{attachment_id} for attachment IDs found in the snapshot",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        base_url = normalize_base_url(args.base_url)
        snapshot = collect_snapshot(base_url, include_attachments=args.include_attachments)
        if args.filter:
            snapshot["matches"] = focused_matches(snapshot["data"], args.filter)
    except Exception as exc:  # noqa: BLE001 - CLI should report concise failure.
        print(f"error: {exc}", file=sys.stderr)
        return 1

    text = json.dumps(snapshot, indent=2, sort_keys=True)
    if args.out == "-":
        print(text)
    else:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
