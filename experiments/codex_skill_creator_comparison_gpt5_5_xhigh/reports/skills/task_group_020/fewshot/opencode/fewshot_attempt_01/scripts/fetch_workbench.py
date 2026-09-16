#!/usr/bin/env python3
"""Collect a deal-workbench snapshot using only Python stdlib."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ENDPOINTS = [
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


def get_json(base_url: str, path: str):
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = response.read().decode("utf-8")
            return {"ok": True, "url": url, "data": json.loads(data)}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "url": url, "status": exc.code, "error": body}
    except Exception as exc:  # noqa: BLE001 - diagnostic helper
        return {"ok": False, "url": url, "error": str(exc)}


def post_query(base_url: str, sql: str):
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", "api/query")
    payload = json.dumps({"token": "deal-workbench-readonly", "sql": sql}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = response.read().decode("utf-8")
            return {"ok": True, "url": url, "data": json.loads(data)}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "url": url, "status": exc.code, "error": body}
    except Exception as exc:  # noqa: BLE001 - diagnostic helper
        return {"ok": False, "url": url, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch a deal-workbench snapshot.")
    parser.add_argument("base_url", help="Task environment base URL")
    parser.add_argument("deal_id", help="Deal ID, such as PRJ_EXAMPLE")
    parser.add_argument("--playbook-id", help="Optional playbook ID to fetch")
    parser.add_argument("--policy-id", help="Optional policy ID to fetch")
    parser.add_argument("--sql", action="append", default=[], help="Optional read-only SQL query")
    parser.add_argument("--out", default="workbench_snapshot.json", help="Output JSON path")
    args = parser.parse_args()

    snapshot = {
        "deal_id": args.deal_id,
        "base_url": args.base_url,
        "deal": get_json(args.base_url, f"/api/deals/{args.deal_id}"),
        "endpoints": {},
        "playbooks": get_json(args.base_url, "/api/playbooks"),
        "policies": get_json(args.base_url, "/api/policies"),
        "queries": [],
    }

    for endpoint in ENDPOINTS:
        snapshot["endpoints"][endpoint] = get_json(args.base_url, f"/api/deals/{args.deal_id}/{endpoint}")

    if args.playbook_id:
        snapshot["playbook_rules"] = get_json(args.base_url, f"/api/playbooks/{args.playbook_id}/rules")

    if args.policy_id:
        snapshot["policy_thresholds"] = get_json(args.base_url, f"/api/policies/{args.policy_id}/thresholds")

    for sql in args.sql:
        snapshot["queries"].append({"sql": sql, "result": post_query(args.base_url, sql)})

    out_path = Path(args.out)
    out_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
