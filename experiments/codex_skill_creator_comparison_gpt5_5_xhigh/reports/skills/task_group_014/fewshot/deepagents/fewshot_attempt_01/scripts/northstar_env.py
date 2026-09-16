#!/usr/bin/env python3
"""Query the Northstar payer-operations task environment."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def _bearer(token: str | None) -> str | None:
    if not token:
        return None
    return token if token.lower().startswith("bearer ") else f"Bearer {token}"


def request_json(base_url: str, method: str, path: str, token: str | None = None, body=None):
    url = base_url.rstrip("/") + path
    headers = {"Accept": "application/json"}
    auth = _bearer(token)
    if auth:
        headers["Authorization"] = auth
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} for {path}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach {url}: {exc.reason}") from exc
    return json.loads(raw)


def print_json(value) -> None:
    print(json.dumps(value, indent=2, sort_keys=False))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("TASK_ENV_BASE_URL", ""))
    parser.add_argument("--token", default=os.environ.get("NORTHSTAR_TOKEN") or os.environ.get("TASK_ENV_TOKEN"))
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("tables")
    sub.add_parser("policies")
    sub.add_parser("appeals")
    sub.add_parser("rate-schedules")

    case_p = sub.add_parser("case")
    case_p.add_argument("case_id")

    policy_p = sub.add_parser("policy")
    policy_p.add_argument("policy_id")

    document_p = sub.add_parser("document")
    document_p.add_argument("document_id")

    sql_p = sub.add_parser("sql")
    sql_p.add_argument("sql", nargs="+")

    args = parser.parse_args(argv)
    if not args.base_url:
        parser.error("--base-url or TASK_ENV_BASE_URL is required")

    if args.command == "tables":
        print_json(request_json(args.base_url, "GET", "/api/tables", args.token))
    elif args.command == "policies":
        print_json(request_json(args.base_url, "GET", "/api/policies", args.token))
    elif args.command == "appeals":
        print_json(request_json(args.base_url, "GET", "/api/appeals", args.token))
    elif args.command == "rate-schedules":
        print_json(request_json(args.base_url, "GET", "/api/rate-schedules", args.token))
    elif args.command == "case":
        print_json(request_json(args.base_url, "GET", f"/api/cases/{args.case_id}", args.token))
    elif args.command == "policy":
        print_json(request_json(args.base_url, "GET", f"/api/policies/{args.policy_id}", args.token))
    elif args.command == "document":
        print_json(request_json(args.base_url, "GET", f"/api/documents/{args.document_id}", args.token))
    elif args.command == "sql":
        sql = " ".join(args.sql)
        print_json(request_json(args.base_url, "POST", "/sql/query", args.token, {"sql": sql}))
    else:
        parser.error(f"unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
