#!/usr/bin/env python3
"""Fetch a portable evidence snapshot from the M&A deal workbench."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEAL_ENDPOINTS = {
    "deal": "/api/deals/{deal_id}",
    "terms": "/api/deals/{deal_id}/terms",
    "documents": "/api/deals/{deal_id}/documents",
    "benchmarks": "/api/deals/{deal_id}/benchmarks",
    "risk_estimates": "/api/deals/{deal_id}/risk-estimates",
    "cap_table": "/api/deals/{deal_id}/cap-table",
    "consents": "/api/deals/{deal_id}/consents",
    "employees": "/api/deals/{deal_id}/employees",
    "material_contracts": "/api/deals/{deal_id}/material-contracts",
    "regulatory": "/api/deals/{deal_id}/regulatory",
    "diligence_findings": "/api/deals/{deal_id}/diligence-findings",
    "notes": "/api/deals/{deal_id}/notes",
}

INDEX_ENDPOINTS = {
    "workspace": "/workspace",
    "deals_index": "/api/deals",
    "playbooks_index": "/api/playbooks",
    "policies_index": "/api/policies",
}


def url_for(base_url: str, path: str) -> str:
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = raw
            return {"ok": True, "status": resp.status, "url": url, "data": data}
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "status": exc.code, "url": url, "error": error_body}
    except urllib.error.URLError as exc:
        return {"ok": False, "status": None, "url": url, "error": str(exc.reason)}


def find_ids(obj: Any, suffixes: tuple[str, ...]) -> list[str]:
    found: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                lowered = key.lower()
                if isinstance(child, str) and any(lowered.endswith(suffix) for suffix in suffixes):
                    found.append(child)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(obj)
    deduped: list[str] = []
    for item in found:
        if item not in deduped:
            deduped.append(item)
    return deduped


def post_sql(base_url: str, token: str, sql: str) -> dict[str, Any]:
    url = url_for(base_url, "/api/query")
    attempts = [
        {"token": token, "sql": sql},
        {"token": token, "query": sql},
    ]
    results = []
    for payload in attempts:
        result = request_json("POST", url, payload)
        results.append({"payload_keys": sorted(payload.keys()), "result": result})
        if result["ok"]:
            return results[-1]
    return {"ok": False, "attempts": results}


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch M&A deal-workbench evidence as JSON.")
    parser.add_argument("--base-url", required=True, help="Workbench base URL, such as http://task-env:9020/")
    parser.add_argument("--deal-id", required=True, help="Stable deal ID from the task prompt.")
    parser.add_argument("--out", required=True, help="Path for the JSON evidence snapshot.")
    parser.add_argument("--playbook-id", action="append", default=[], help="Playbook ID to fetch rules for. May repeat.")
    parser.add_argument("--policy-id", action="append", default=[], help="Policy ID to fetch thresholds for. May repeat.")
    parser.add_argument("--sql", action="append", default=[], help="Optional read-only SQL query. May repeat.")
    parser.add_argument("--query-token", default="deal-workbench-readonly", help="Token for POST /api/query when SQL is allowed.")
    parser.add_argument("--skip-index", action="store_true", help="Skip workspace/deals/playbooks/policies index endpoints.")
    args = parser.parse_args()

    snapshot: dict[str, Any] = {
        "fetched_at": _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "base_url": args.base_url,
        "deal_id": args.deal_id,
        "endpoints": {},
        "playbooks": {},
        "policies": {},
        "queries": [],
    }

    if not args.skip_index:
        for name, path in INDEX_ENDPOINTS.items():
            snapshot["endpoints"][name] = request_json("GET", url_for(args.base_url, path))

    for name, path in DEAL_ENDPOINTS.items():
        snapshot["endpoints"][name] = request_json("GET", url_for(args.base_url, path.format(deal_id=args.deal_id)))

    deal_data = snapshot["endpoints"].get("deal", {}).get("data")
    inferred_playbooks = find_ids(deal_data, ("playbook_id",)) if deal_data is not None else []
    inferred_policies = find_ids(deal_data, ("policy_id",)) if deal_data is not None else []

    playbook_ids = list(dict.fromkeys(args.playbook_id + inferred_playbooks))
    policy_ids = list(dict.fromkeys(args.policy_id + inferred_policies))

    for playbook_id in playbook_ids:
        path = f"/api/playbooks/{urllib.parse.quote(playbook_id)}/rules"
        snapshot["playbooks"][playbook_id] = request_json("GET", url_for(args.base_url, path))

    for policy_id in policy_ids:
        path = f"/api/policies/{urllib.parse.quote(policy_id)}/thresholds"
        snapshot["policies"][policy_id] = request_json("GET", url_for(args.base_url, path))

    for sql in args.sql:
        snapshot["queries"].append({"sql": sql, "response": post_sql(args.base_url, args.query_token, sql)})

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, sort_keys=True)
        f.write("\n")

    failed = [
        name
        for name, result in snapshot["endpoints"].items()
        if isinstance(result, dict) and not result.get("ok")
    ]
    if failed:
        print("Fetched with failed endpoints: " + ", ".join(failed), file=sys.stderr)
    else:
        print(f"Wrote evidence snapshot to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
