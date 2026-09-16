#!/usr/bin/env python3
"""Fetch Northstar task-environment records without external dependencies."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_TOKEN = "pa-review-token-014"


def normalize_base_url(base_url: str) -> str:
    base_url = base_url.strip()
    if not base_url:
        raise ValueError("base URL is required")
    return base_url.rstrip("/")


def request_json(method: str, url: str, token: str | None = None, payload: dict | None = None) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} {exc.reason}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"request failed: {exc}") from exc


def print_json(value: dict) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def endpoint_url(base_url: str, *parts: str) -> str:
    quoted = [urllib.parse.quote(part.strip("/"), safe="") for part in parts]
    return "/".join([normalize_base_url(base_url), *quoted])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument(
        "--token",
        default=os.environ.get("NORTHSTAR_SQL_TOKEN", DEFAULT_TOKEN),
        help="Bearer token for SQL requests; defaults to NORTHSTAR_SQL_TOKEN or the staged token",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("tables", help="GET /api/tables")
    subparsers.add_parser("rate-schedules", help="GET /api/rate-schedules")
    subparsers.add_parser("appeals", help="GET /api/appeals")

    case_parser = subparsers.add_parser("case", help="GET /api/cases/{case_id}")
    case_parser.add_argument("case_id")

    policy_parser = subparsers.add_parser("policy", help="GET /api/policies/{policy_id}")
    policy_parser.add_argument("policy_id")

    document_parser = subparsers.add_parser("document", help="GET /api/documents/{document_id}")
    document_parser.add_argument("document_id")

    sql_parser = subparsers.add_parser("sql", help="POST /sql/query")
    sql_parser.add_argument("sql", nargs="?", help="SQL string. Reads stdin when omitted.")

    args = parser.parse_args()
    base_url = normalize_base_url(args.base_url)

    if args.command == "tables":
        result = request_json("GET", f"{base_url}/api/tables")
    elif args.command == "rate-schedules":
        result = request_json("GET", f"{base_url}/api/rate-schedules")
    elif args.command == "appeals":
        result = request_json("GET", f"{base_url}/api/appeals")
    elif args.command == "case":
        result = request_json("GET", endpoint_url(base_url, "api", "cases", args.case_id))
    elif args.command == "policy":
        result = request_json("GET", endpoint_url(base_url, "api", "policies", args.policy_id))
    elif args.command == "document":
        result = request_json("GET", endpoint_url(base_url, "api", "documents", args.document_id))
    elif args.command == "sql":
        sql = args.sql if args.sql is not None else sys.stdin.read()
        sql = sql.strip()
        if not sql:
            raise SystemExit("SQL is required")
        result = request_json("POST", f"{base_url}/sql/query", token=args.token, payload={"sql": sql})
    else:
        parser.error(f"unknown command: {args.command}")

    print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
