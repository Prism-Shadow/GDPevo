#!/usr/bin/env python3
"""Fetch a tolerant JSON snapshot from an M&A deal workbench.

The script uses only the Python standard library. Missing routes are recorded
with status/error metadata instead of failing the whole snapshot.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


COMMON_DEAL_ENDPOINTS = [
    "terms",
    "risk-estimates",
    "employees",
    "consents",
    "regulatory",
    "benchmarks",
    "notes",
    "cap-table",
    "material-contracts",
    "diligence-findings",
    "documents",
]


def request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            try:
                parsed: Any = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                parsed = raw
            return {"ok": True, "status": resp.status, "data": parsed}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "status": exc.code, "error": body[:1000]}
    except Exception as exc:  # noqa: BLE001 - preserve diagnostics in snapshot.
        return {"ok": False, "status": None, "error": str(exc)}


def build_url(base_url: str, path: str) -> str:
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument("--deal-id", required=True, help="Workbench deal ID")
    parser.add_argument("--playbook-id", help="Optional playbook or policy ID")
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument(
        "--sql",
        action="append",
        default=[],
        help="Optional read-only SQL query. May be supplied multiple times.",
    )
    parser.add_argument(
        "--sql-token",
        default="deal-workbench-readonly",
        help="Read-only SQL token used by the task workbench.",
    )
    args = parser.parse_args()

    snapshot: dict[str, Any] = {
        "deal_id": args.deal_id,
        "base_url": args.base_url,
        "records": {},
        "sql": [],
    }

    paths = [f"/api/deals/{args.deal_id}"]
    paths.extend(f"/api/deals/{args.deal_id}/{name}" for name in COMMON_DEAL_ENDPOINTS)
    if args.playbook_id:
        paths.append(f"/api/playbooks/{args.playbook_id}/rules")
        paths.append(f"/api/policies/{args.playbook_id}/rules")

    for path in paths:
        snapshot["records"][path] = request_json("GET", build_url(args.base_url, path))

    for query in args.sql:
        payload = {"token": args.sql_token, "sql": query}
        result = request_json("POST", build_url(args.base_url, "/api/query"), payload)
        snapshot["sql"].append({"query": query, "result": result})

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
