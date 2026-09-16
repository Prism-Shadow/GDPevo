#!/usr/bin/env python3
"""Small stdlib client for Atlas task-environment APIs."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def base_url_from_args(args):
    base_url = args.base_url or os.environ.get("TASK_ENV_BASE_URL") or os.environ.get("ATLAS_TASK_ENV_BASE_URL")
    if not base_url:
        raise SystemExit("Set TASK_ENV_BASE_URL or pass --base-url.")
    return base_url.rstrip("/")


def headers():
    result = {"Accept": "application/json"}
    token = os.environ.get("TASK_ENV_TOKEN") or os.environ.get("ATLAS_AUTH_TOKEN") or os.environ.get("AUTH_TOKEN")
    if token:
        result["Authorization"] = f"Bearer {token}"
    return result


def request_json(base_url, method, endpoint, body=None):
    endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    data = None
    req_headers = headers()
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{base_url}{endpoint}", data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(request) as response:
            raw = response.read()
            text = raw.decode("utf-8")
            ctype = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {endpoint}:\n{detail}") from exc
    if "json" in ctype:
        return json.loads(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def read_query(value):
    if value.startswith("@"):
        with open(value[1:], "r", encoding="utf-8") as handle:
            return handle.read()
    if os.path.exists(value):
        with open(value, "r", encoding="utf-8") as handle:
            return handle.read()
    return value


def print_result(value):
    if isinstance(value, (dict, list)):
        print(json.dumps(value, indent=2, sort_keys=True))
    else:
        print(value)


def main():
    parser = argparse.ArgumentParser(description="Call Atlas task-environment API endpoints.")
    parser.add_argument("--base-url", help="Base URL. Defaults to TASK_ENV_BASE_URL.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("schema", help="GET /api/schema")
    sub.add_parser("dictionary", help="GET /api/data-dictionary")

    sql_parser = sub.add_parser("sql", help="POST a SQL query to /api/sql")
    sql_parser.add_argument("query", help="SQL text, a file path, or @file")
    sql_parser.add_argument("--endpoint", default="/api/sql")
    sql_parser.add_argument("--payload-key", default="sql")

    post_parser = sub.add_parser("post", help="POST a JSON body to an arbitrary API endpoint")
    post_parser.add_argument("endpoint")
    post_parser.add_argument("json_body", help="JSON text, a file path, or @file")

    args = parser.parse_args()
    base_url = base_url_from_args(args)

    if args.command == "schema":
        print_result(request_json(base_url, "GET", "/api/schema"))
    elif args.command == "dictionary":
        print_result(request_json(base_url, "GET", "/api/data-dictionary"))
    elif args.command == "sql":
        query = read_query(args.query)
        print_result(request_json(base_url, "POST", args.endpoint, {args.payload_key: query}))
    elif args.command == "post":
        body = json.loads(read_query(args.json_body))
        print_result(request_json(base_url, "POST", args.endpoint, body))


if __name__ == "__main__":
    main()

