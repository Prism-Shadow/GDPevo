#!/usr/bin/env python3
"""Small Atlas Commerce Operations API client."""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


def find_environment_access(start):
    for directory in [start, *start.parents]:
        candidate = directory / "environment_access.md"
        if candidate.exists():
            return candidate
    return None


def parse_environment_access(path):
    data = {}
    if not path:
        return data
    text = path.read_text()
    base_match = re.search(r"^base_url:\s*(\S+)\s*$", text, re.MULTILINE)
    token_match = re.search(r"^\s*token_env:\s*(\S+)\s*$", text, re.MULTILINE)
    if base_match:
        data["base_url"] = base_match.group(1)
    if token_match:
        data["token_env"] = token_match.group(1)
    return data


def resolve_config(args):
    env_file = find_environment_access(Path.cwd())
    env_access = parse_environment_access(env_file)
    base_url = (
        args.base_url
        or os.environ.get("TASK_ENV_BASE_URL")
        or env_access.get("base_url")
        or "http://task-env:9022/"
    )
    token_env = env_access.get("token_env") or "TASK_ENV_API_TOKEN"
    token = args.token or os.environ.get(token_env) or os.environ.get("TASK_ENV_API_TOKEN")
    return base_url.rstrip("/"), token


def request_json(base_url, token, method, path, body=None):
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        print(payload or f"HTTP {exc.code}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        print(payload)
        return None


def read_text_argument(value, file_path):
    if value and file_path:
        print("Use either inline text or --file, not both.", file=sys.stderr)
        sys.exit(2)
    if file_path:
        return Path(file_path).read_text()
    if value:
        return value
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Provide inline text, --file, or stdin.", file=sys.stderr)
    sys.exit(2)


def emit(payload, compact):
    if payload is None:
        return
    if compact:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print(json.dumps(payload, indent=2, sort_keys=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Atlas task environment base URL")
    parser.add_argument("--token", help="Bearer token; defaults to TASK_ENV_API_TOKEN")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("schema", help="GET /api/schema")
    subparsers.add_parser("dictionary", aliases=["dict"], help="GET /api/data-dictionary")
    subparsers.add_parser("audit", help="GET /api/correction-audit")

    sql_parser = subparsers.add_parser("sql", help="POST /api/sql")
    sql_parser.add_argument("--sql", help="SQL text")
    sql_parser.add_argument("--file", help="File containing SQL")

    txn_parser = subparsers.add_parser("transaction", help="POST /api/sql/transaction")
    txn_parser.add_argument("--json", help="Inline JSON transaction body")
    txn_parser.add_argument("--file", help="File containing JSON transaction body")

    args = parser.parse_args()
    base_url, token = resolve_config(args)

    if args.command == "schema":
        payload = request_json(base_url, token, "GET", "/api/schema")
    elif args.command in {"dictionary", "dict"}:
        payload = request_json(base_url, token, "GET", "/api/data-dictionary")
    elif args.command == "audit":
        payload = request_json(base_url, token, "GET", "/api/correction-audit")
    elif args.command == "sql":
        sql = read_text_argument(args.sql, args.file)
        payload = request_json(base_url, token, "POST", "/api/sql", {"sql": sql})
    elif args.command == "transaction":
        body_text = read_text_argument(args.json, args.file)
        try:
            body = json.loads(body_text)
        except json.JSONDecodeError as exc:
            print(f"Invalid transaction JSON: {exc}", file=sys.stderr)
            sys.exit(2)
        payload = request_json(base_url, token, "POST", "/api/sql/transaction", body)
    else:
        parser.error("unknown command")

    emit(payload, args.compact)


if __name__ == "__main__":
    main()
