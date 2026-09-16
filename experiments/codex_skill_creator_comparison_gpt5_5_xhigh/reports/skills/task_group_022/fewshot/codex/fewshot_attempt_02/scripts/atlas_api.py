#!/usr/bin/env python3
"""Small stdlib client for Atlas Commerce task APIs."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def base_url(value):
    raw = value or os.environ.get("TASK_ENV_BASE_URL") or "http://task-env:9022/"
    return raw.rstrip("/")


def read_text(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def request(args, method, path, body=None):
    url = base_url(args.base_url) + "/" + path.lstrip("/")
    headers = {"Accept": "application/json"}
    token = os.environ.get(args.token_env, "")
    if token:
        headers["Authorization"] = "Bearer " + token
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            payload = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        sys.stderr.write(exc.read().decode("utf-8") + "\n")
        return 1
    if not payload:
        return 0
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        print(payload)
    else:
        print(json.dumps(parsed, indent=2, sort_keys=False))
    return 0


def main():
    parser = argparse.ArgumentParser(description="Call Atlas Commerce task APIs.")
    parser.add_argument("--base-url", help="Task API base URL")
    parser.add_argument("--token-env", default="TASK_ENV_API_TOKEN")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("schema")
    sub.add_parser("dictionary")
    sub.add_parser("audit")

    sql = sub.add_parser("sql")
    sql.add_argument("sql", nargs="?", help="SQL string; reads stdin when omitted")
    sql.add_argument("--file", default="-", help="Read SQL from file path or stdin")

    post = sub.add_parser("post")
    post.add_argument("path", help="Endpoint path, such as /api/sql/transaction")
    post.add_argument("--file", default="-", help="Read JSON body from file path or stdin")

    args = parser.parse_args()

    if args.command == "schema":
        return request(args, "GET", "/api/schema")
    if args.command == "dictionary":
        return request(args, "GET", "/api/data-dictionary")
    if args.command == "audit":
        return request(args, "GET", "/api/correction-audit")
    if args.command == "sql":
        sql_text = args.sql if args.sql is not None else read_text(args.file)
        return request(args, "POST", "/api/sql", {"sql": sql_text})
    if args.command == "post":
        try:
            body = json.loads(read_text(args.file))
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"Invalid JSON body: {exc}\n")
            return 2
        return request(args, "POST", args.path, body)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
