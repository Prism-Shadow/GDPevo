#!/usr/bin/env python3
"""Small standard-library client for Atlas Commerce Operations task APIs."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ENDPOINTS = {
    "health": "/health",
    "schema": "/api/schema",
    "dictionary": "/api/data-dictionary",
    "data-dictionary": "/api/data-dictionary",
    "audit": "/api/correction-audit",
    "correction-audit": "/api/correction-audit",
}


def read_env_file(path: str | None) -> tuple[str | None, str | None]:
    if not path:
        return None, None
    env_path = Path(path)
    if not env_path.exists():
        return None, None
    text = env_path.read_text(encoding="utf-8")
    base_match = re.search(r"^Base URL:\s*(\S+)\s*$", text, re.MULTILINE)
    token_match = re.search(r"^Business API token:\s*(.+?)\s*$", text, re.MULTILINE)
    base_url = base_match.group(1) if base_match else None
    token = token_match.group(1) if token_match else None
    return base_url, token


def resolve_config(args: argparse.Namespace) -> tuple[str, str]:
    file_base, file_token = read_env_file(args.env_file)
    base_url = args.base_url or os.environ.get("TASK_ENV_BASE_URL") or file_base
    token = args.token or os.environ.get("ATLAS_API_TOKEN") or file_token
    if not base_url:
        raise SystemExit("Missing base URL. Pass --base-url, set TASK_ENV_BASE_URL, or use --env-file.")
    if not token:
        raise SystemExit("Missing API token. Pass --token, set ATLAS_API_TOKEN, or use --env-file.")
    return base_url.rstrip("/"), token


def auth_value(token: str) -> str:
    return token if token.lower().startswith("bearer ") else f"Bearer {token}"


def request_json(base_url: str, token: str, method: str, path: str, body: Any | None = None) -> Any:
    data = None
    headers = {"Authorization": auth_value(token)}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {raw}") from exc
    return json.loads(raw)


def read_text_arg(value: str | None, file_value: str | None) -> str:
    if file_value:
        return Path(file_value).read_text(encoding="utf-8")
    if value and value != "-":
        candidate = Path(value)
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
        return value
    return sys.stdin.read()


def main() -> int:
    parser = argparse.ArgumentParser(description="Call Atlas Commerce Operations task APIs.")
    parser.add_argument("--base-url")
    parser.add_argument("--token")
    parser.add_argument("--env-file", default="environment_access.md")
    subparsers = parser.add_subparsers(dest="command", required=True)

    get_parser = subparsers.add_parser("get", help="GET health, schema, dictionary, audit, or a raw path.")
    get_parser.add_argument("endpoint")

    sql_parser = subparsers.add_parser("sql", help="POST a read-only SQL query.")
    sql_parser.add_argument("sql", nargs="?", help="SQL text, a SQL file path, or '-' for stdin.")
    sql_parser.add_argument("--file", help="SQL file path.")

    tx_parser = subparsers.add_parser("transaction", help="POST a transaction JSON document.")
    tx_parser.add_argument("json_doc", nargs="?", help="JSON text, a JSON file path, or '-' for stdin.")
    tx_parser.add_argument("--file", help="JSON file path.")

    args = parser.parse_args()
    base_url, token = resolve_config(args)

    if args.command == "get":
        path = ENDPOINTS.get(args.endpoint, args.endpoint)
        if not path.startswith("/"):
            path = "/" + path
        result = request_json(base_url, token, "GET", path)
    elif args.command == "sql":
        sql = read_text_arg(args.sql, args.file).strip()
        if not sql:
            raise SystemExit("SQL text is empty.")
        result = request_json(base_url, token, "POST", "/api/sql", {"sql": sql})
    else:
        text = read_text_arg(args.json_doc, args.file).strip()
        if not text:
            raise SystemExit("Transaction JSON is empty.")
        result = request_json(base_url, token, "POST", "/api/sql/transaction", json.loads(text))

    json.dump(result, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
