#!/usr/bin/env python3
"""Small stdlib client for Atlas Commerce Operations task APIs."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def parse_env_file(path: str | None) -> dict[str, str]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    values: dict[str, str] = {}
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip('"').strip("'")
        if key.strip() in {"base_url", "token_env"}:
            values[key.strip()] = value
    return values


def base_url(args: argparse.Namespace, env_file: dict[str, str]) -> str:
    value = (
        args.base_url
        or os.environ.get("TASK_ENV_BASE_URL")
        or os.environ.get("ATLAS_BASE_URL")
        or env_file.get("base_url")
    )
    if not value or value == "<TASK_ENV_BASE_URL>":
        raise SystemExit("No Atlas base URL found. Pass --base-url or set TASK_ENV_BASE_URL.")
    return value.rstrip("/")


def token(args: argparse.Namespace, env_file: dict[str, str]) -> str:
    token_env = args.token_env or env_file.get("token_env") or "TASK_ENV_API_TOKEN"
    value = args.token or os.environ.get(token_env)
    if not value:
        raise SystemExit(f"No bearer token found. Set {token_env} or pass --token.")
    return value


def request_json(method: str, url: str, bearer: str, payload: object | None = None) -> object:
    data = None
    headers = {
        "Authorization": f"Bearer {bearer}",
        "Accept": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {body}") from exc
    return json.loads(raw)


def emit(value: object, out: str | None) -> None:
    text = json.dumps(value, indent=2, sort_keys=False)
    if out:
        Path(out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def read_sql(args: argparse.Namespace) -> str:
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if args.sql:
        return " ".join(args.sql)
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("Provide SQL as arguments, --file, or stdin.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url")
    parser.add_argument("--token")
    parser.add_argument("--token-env")
    parser.add_argument("--env-file", default="environment_access.md")
    parser.add_argument("--out")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("schema")
    sub.add_parser("dictionary")
    sub.add_parser("audit")

    sql_parser = sub.add_parser("sql")
    sql_parser.add_argument("--file")
    sql_parser.add_argument("sql", nargs=argparse.REMAINDER)

    tx_parser = sub.add_parser("transaction")
    tx_parser.add_argument("--body-file", required=True, help="JSON request body for /api/sql/transaction.")

    args = parser.parse_args()
    env_file = parse_env_file(args.env_file)
    root = base_url(args, env_file)
    bearer = token(args, env_file)

    if args.cmd == "schema":
        result = request_json("GET", f"{root}/api/schema", bearer)
    elif args.cmd == "dictionary":
        result = request_json("GET", f"{root}/api/data-dictionary", bearer)
    elif args.cmd == "audit":
        result = request_json("GET", f"{root}/api/correction-audit", bearer)
    elif args.cmd == "sql":
        result = request_json("POST", f"{root}/api/sql", bearer, {"sql": read_sql(args)})
    elif args.cmd == "transaction":
        body = json.loads(Path(args.body_file).read_text(encoding="utf-8"))
        result = request_json("POST", f"{root}/api/sql/transaction", bearer, body)
    else:
        raise AssertionError(args.cmd)

    emit(result, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
