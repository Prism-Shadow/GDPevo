#!/usr/bin/env python3
"""Collect a reusable M&A deal-workbench evidence bundle."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


SUBRESOURCES = [
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


def fetch_json(base_url: str, path: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else None


def try_fetch(base_url: str, path: str) -> dict[str, Any]:
    try:
        return {"ok": True, "data": fetch_json(base_url, path)}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": exc.reason}
    except Exception as exc:  # Keep collection best-effort across optional endpoints.
        return {"ok": False, "error": str(exc)}


def extract_nested_id(response: Any, wrapper: str, field: str) -> str | None:
    if isinstance(response, dict):
        value = response.get(wrapper)
        if isinstance(value, dict):
            nested = value.get(field)
            return str(nested) if nested else None
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect deal workbench data for one deal ID.")
    parser.add_argument("--base-url", required=True, help="Workbench base URL, for example http://task-env:9020/")
    parser.add_argument("--deal-id", required=True, help="Deal ID to collect.")
    parser.add_argument("--playbook-id", help="Optional playbook ID when not present on the deal record.")
    parser.add_argument("--policy-id", help="Optional policy ID when not present on the deal record.")
    parser.add_argument("--query-token", help="Optional read-only SQL token.")
    parser.add_argument("--sql", action="append", default=[], help="Optional read-only SQL query; may be repeated.")
    parser.add_argument("--output", help="Write JSON bundle to this path instead of stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle: dict[str, Any] = {
        "deal_id": args.deal_id,
        "deal": try_fetch(args.base_url, f"/api/deals/{urllib.parse.quote(args.deal_id)}"),
        "subresources": {},
        "playbook": None,
        "policy": None,
        "sql_results": [],
    }

    for resource in SUBRESOURCES:
        path = f"/api/deals/{urllib.parse.quote(args.deal_id)}/{resource}"
        bundle["subresources"][resource] = try_fetch(args.base_url, path)

    deal_data = bundle["deal"].get("data") if isinstance(bundle["deal"], dict) else None
    playbook_id = args.playbook_id or extract_nested_id(deal_data, "deal", "playbook_id")
    policy_id = args.policy_id or extract_nested_id(deal_data, "deal", "policy_id")

    if playbook_id:
        bundle["playbook"] = try_fetch(args.base_url, f"/api/playbooks/{urllib.parse.quote(playbook_id)}/rules")
    if policy_id:
        bundle["policy"] = try_fetch(args.base_url, f"/api/policies/{urllib.parse.quote(policy_id)}/thresholds")

    for sql in args.sql:
        if not args.query_token:
            bundle["sql_results"].append({"ok": False, "error": "query token required", "sql": sql})
            continue
        try:
            result = fetch_json(
                args.base_url,
                "/api/query",
                method="POST",
                payload={"token": args.query_token, "sql": sql},
            )
            bundle["sql_results"].append({"ok": True, "sql": sql, "data": result})
        except urllib.error.HTTPError as exc:
            bundle["sql_results"].append({"ok": False, "status": exc.code, "error": exc.reason, "sql": sql})
        except Exception as exc:
            bundle["sql_results"].append({"ok": False, "error": str(exc), "sql": sql})

    output = json.dumps(bundle, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(output)
            handle.write("\n")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
