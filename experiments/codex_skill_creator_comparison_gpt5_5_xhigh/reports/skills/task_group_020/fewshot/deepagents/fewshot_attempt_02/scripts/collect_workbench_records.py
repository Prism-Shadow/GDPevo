#!/usr/bin/env python3
"""Collect M&A workbench records for one deal into a JSON evidence bundle."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


COMMON_DEAL_ENDPOINTS = [
    "terms",
    "documents",
    "benchmarks",
    "risk-estimates",
    "cap-table",
    "consents",
    "employees",
    "material-contracts",
    "regulatory",
    "diligence-findings",
    "notes",
]


def fetch_json(base_url: str, path: str, method: str = "GET", payload: Any = None) -> dict[str, Any]:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return {"ok": True, "status": response.status, "json": json.loads(raw)}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "status": exc.code, "error": body[:1000]}
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "status": None, "error": str(exc)}


def find_first_id(value: Any, keys: tuple[str, ...]) -> str | None:
    if isinstance(value, dict):
        for key in keys:
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        for child in value.values():
            found = find_first_id(child, keys)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_first_id(child, keys)
            if found:
                return found
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument("--deal-id", required=True, help="Exact deal ID from the prompt")
    parser.add_argument("--out", required=True, help="Path to write JSON evidence bundle")
    parser.add_argument("--playbook-id", help="Optional playbook ID from prompt or deal record")
    parser.add_argument("--policy-id", help="Optional policy ID from prompt or deal record")
    parser.add_argument("--sql", help="Optional read-only SQL query for /api/query")
    parser.add_argument("--token", default="deal-workbench-readonly", help="SQL token")
    args = parser.parse_args()

    bundle: dict[str, Any] = {
        "deal_id": args.deal_id,
        "base_url": args.base_url,
        "records": {},
    }

    deal_path = f"/api/deals/{args.deal_id}"
    bundle["records"]["deal"] = fetch_json(args.base_url, deal_path)

    deal_json = bundle["records"]["deal"].get("json")
    playbook_id = args.playbook_id or find_first_id(
        deal_json,
        ("playbook_id", "seller_playbook_id", "buyer_playbook_id", "applicable_playbook_id"),
    )
    policy_id = args.policy_id or find_first_id(
        deal_json,
        ("policy_id", "committee_policy_id", "applicable_policy_id"),
    )

    for endpoint in COMMON_DEAL_ENDPOINTS:
        key = endpoint.replace("-", "_")
        bundle["records"][key] = fetch_json(args.base_url, f"/api/deals/{args.deal_id}/{endpoint}")

    if playbook_id:
        bundle["playbook_id"] = playbook_id
        bundle["records"]["playbook_rules"] = fetch_json(args.base_url, f"/api/playbooks/{playbook_id}/rules")

    if policy_id:
        bundle["policy_id"] = policy_id
        bundle["records"]["policy_thresholds"] = fetch_json(args.base_url, f"/api/policies/{policy_id}/thresholds")

    if args.sql:
        bundle["records"]["sql_query"] = fetch_json(
            args.base_url,
            "/api/query",
            method="POST",
            payload={"token": args.token, "query": args.sql},
        )

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(bundle, handle, indent=2, sort_keys=True)
        handle.write("\n")

    failed = [key for key, record in bundle["records"].items() if not record.get("ok")]
    if failed:
        print("Collected with failed endpoints: " + ", ".join(failed), file=sys.stderr)
    else:
        print("Collected all requested endpoints", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
