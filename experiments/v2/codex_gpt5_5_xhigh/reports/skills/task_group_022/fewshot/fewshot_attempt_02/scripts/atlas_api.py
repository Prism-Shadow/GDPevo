#!/usr/bin/env python3
"""Small CLI for the Atlas Commerce Operations task API."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def load_env(path: Path) -> tuple[str, str]:
    base_url = None
    auth = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("GDPEVO_ENV_BASE_URL="):
            base_url = line.split("=", 1)[1].strip()
        elif line.startswith("Authorization:"):
            auth = line.split(":", 1)[1].strip()
    if not base_url or not auth:
        raise SystemExit(f"could not find base URL and Authorization in {path}")
    return base_url.rstrip("/"), auth


def request_json(base_url: str, auth: str, method: str, path: str, payload: object | None = None) -> object:
    data = None
    headers = {"Authorization": auth}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {body}") from exc
    return json.loads(body)


def main() -> int:
    parser = argparse.ArgumentParser(description="Call the Atlas Commerce Operations API")
    parser.add_argument("--env", default="environment_access.md", help="path to environment_access.md")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("schema")
    sub.add_parser("dictionary")
    sub.add_parser("audit")
    sql = sub.add_parser("sql")
    sql.add_argument("query")
    sql_file = sub.add_parser("sql-file")
    sql_file.add_argument("path")
    tx_file = sub.add_parser("transaction-file")
    tx_file.add_argument("path")
    args = parser.parse_args()

    base_url, auth = load_env(Path(args.env))

    if args.command == "schema":
        result = request_json(base_url, auth, "GET", "/api/schema")
    elif args.command == "dictionary":
        result = request_json(base_url, auth, "GET", "/api/data-dictionary")
    elif args.command == "audit":
        result = request_json(base_url, auth, "GET", "/api/correction-audit")
    elif args.command == "sql":
        result = request_json(base_url, auth, "POST", "/api/sql", {"sql": args.query})
    elif args.command == "sql-file":
        query = Path(args.path).read_text(encoding="utf-8")
        result = request_json(base_url, auth, "POST", "/api/sql", {"sql": query})
    elif args.command == "transaction-file":
        payload = json.loads(Path(args.path).read_text(encoding="utf-8"))
        result = request_json(base_url, auth, "POST", "/api/sql/transaction", payload)
    else:
        parser.error("unknown command")

    json.dump(result, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
