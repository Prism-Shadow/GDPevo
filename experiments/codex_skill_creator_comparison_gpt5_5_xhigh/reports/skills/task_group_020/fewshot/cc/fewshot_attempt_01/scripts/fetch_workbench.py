#!/usr/bin/env python3
"""Fetch common M&A deal workbench API records into JSON files."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


COMMON_DEAL_ENDPOINTS = [
    "deal",
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


def build_url(base_url: str, path: str) -> str:
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def fetch_json(base_url: str, path: str, post_body: dict | None = None) -> tuple[int, object]:
    url = build_url(base_url, path)
    data = None
    headers = {"accept": "application/json"}
    method = "GET"
    if post_body is not None:
        data = json.dumps(post_body).encode("utf-8")
        headers["content-type"] = "application/json"
        method = "POST"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
            status = response.getcode()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, {"error": body}
    except urllib.error.URLError as exc:
        return 0, {"error": str(exc)}
    try:
        return status, json.loads(body)
    except json.JSONDecodeError:
        return status, {"raw": body}


def write_json(out_dir: Path, name: str, payload: object) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument("--deal-id", required=True, help="Deal ID to fetch")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--playbook-id", help="Optional playbook ID for /api/playbooks/<id>/rules")
    parser.add_argument("--policy-id", help="Optional policy ID for /api/policies/<id>/thresholds")
    parser.add_argument(
        "--endpoint",
        action="append",
        default=[],
        help="Additional API path to fetch, such as /api/search?q=term. May be repeated.",
    )
    parser.add_argument("--sql", help="Optional read-only SQL query for POST /api/query")
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Exit non-zero if any endpoint returns an error or non-2xx status.",
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    failures: list[str] = []

    for endpoint in COMMON_DEAL_ENDPOINTS:
        if endpoint == "deal":
            path = f"/api/deals/{args.deal_id}"
            name = "deal"
        else:
            path = f"/api/deals/{args.deal_id}/{endpoint}"
            name = endpoint.replace("-", "_")
        status, payload = fetch_json(args.base_url, path)
        write_json(out_dir, name, {"status": status, "path": path, "data": payload})
        if status < 200 or status >= 300:
            failures.append(path)

    if args.playbook_id:
        path = f"/api/playbooks/{args.playbook_id}/rules"
        status, payload = fetch_json(args.base_url, path)
        write_json(out_dir, "playbook_rules", {"status": status, "path": path, "data": payload})
        if status < 200 or status >= 300:
            failures.append(path)

    if args.policy_id:
        path = f"/api/policies/{args.policy_id}/thresholds"
        status, payload = fetch_json(args.base_url, path)
        write_json(out_dir, "policy_thresholds", {"status": status, "path": path, "data": payload})
        if status < 200 or status >= 300:
            failures.append(path)

    for index, path in enumerate(args.endpoint, start=1):
        status, payload = fetch_json(args.base_url, path)
        write_json(out_dir, f"extra_{index}", {"status": status, "path": path, "data": payload})
        if status < 200 or status >= 300:
            failures.append(path)

    if args.sql:
        post_body = {"token": "deal-workbench-readonly", "query": args.sql}
        status, payload = fetch_json(args.base_url, "/api/query", post_body=post_body)
        write_json(out_dir, "sql_query", {"status": status, "path": "/api/query", "data": payload})
        if status < 200 or status >= 300:
            failures.append("/api/query")

    if failures:
        print("Fetch completed with missing or failed endpoints:", file=sys.stderr)
        for path in failures:
            print(f"- {path}", file=sys.stderr)
        return 1 if args.fail_on_missing else 0

    print(f"Wrote workbench records to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
