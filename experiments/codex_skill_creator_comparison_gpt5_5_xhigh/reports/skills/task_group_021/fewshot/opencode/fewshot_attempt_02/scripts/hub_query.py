#!/usr/bin/env python3
"""Small Asteria Hub client for catalog/schema/query access."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def read_env(path: str | None) -> dict[str, object]:
    if not path:
        return {}
    data: dict[str, object] = {}
    current_list: str | None = None
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_list:
            data.setdefault(current_list, []).append(line[4:].strip())
            continue
        current_list = None
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value:
                data[key] = value
            else:
                data[key] = []
                current_list = key
    return data


def auth_candidates(config: dict[str, object]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = [{}]
    explicit = os.environ.get("ASTERIA_AUTH_HEADER")
    if explicit and ":" in explicit:
        key, value = explicit.split(":", 1)
        candidates.append({key.strip(): value.strip()})

    cred = str(config.get("credentials", "")).strip()
    tokens = [
        os.environ.get("ASTERIA_QUERY_TOKEN"),
        os.environ.get("TASK_ENV_QUERY_TOKEN"),
        os.environ.get("QUERY_TOKEN"),
    ]
    if cred and cred.lower() not in {"none", "null", "no", "n/a"}:
        tokens.append(cred)

    for token in [t for t in tokens if t]:
        candidates.extend(
            [
                {"Authorization": f"Bearer {token}"},
                {"X-API-Key": token},
                {"X-Query-Token": token},
            ]
        )
    return candidates


def request_json(
    base_url: str,
    method: str,
    path: str,
    *,
    params: dict[str, str] | None = None,
    body: object | None = None,
    auths: list[dict[str, str]] | None = None,
) -> object:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    if params:
        url = url + "?" + urllib.parse.urlencode(params)

    payload = None
    headers = {"Accept": "application/json"}
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    errors: list[str] = []
    for auth in auths or [{}]:
        merged_headers = dict(headers)
        merged_headers.update(auth)
        req = urllib.request.Request(url, data=payload, headers=merged_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            errors.append(f"{exc.code} {text}")
            if exc.code != 401:
                break
        except urllib.error.URLError as exc:
            raise SystemExit(f"request failed: {exc}") from exc

    raise SystemExit("request failed: " + " | ".join(errors))


def query_sql(base_url: str, sql: str, auths: list[dict[str, str]]) -> object:
    errors: list[str] = []
    for key in ("query", "sql"):
        try:
            return request_json(base_url, "POST", "/api/query", body={key: sql}, auths=auths)
        except SystemExit as exc:
            errors.append(str(exc))
    raise SystemExit("query failed with both payload keys: " + " | ".join(errors))


def rows_from_result(result: object) -> list[object]:
    if isinstance(result, dict):
        for key in ("rows", "items", "results", "data"):
            value = result.get(key)
            if isinstance(value, list):
                return value
    if isinstance(result, list):
        return result
    return []


def shell_quote_sql(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default="environment_access.md")
    parser.add_argument("--base-url")
    sub = parser.add_subparsers(dest="cmd", required=True)

    get_p = sub.add_parser("get")
    get_p.add_argument("path")
    get_p.add_argument("--param", action="append", default=[], help="name=value query parameter")

    query_p = sub.add_parser("query")
    query_p.add_argument("sql", nargs="?", help="SQL string; reads stdin when omitted")

    dump_p = sub.add_parser("dump-view")
    dump_p.add_argument("view")
    dump_p.add_argument("--collection")
    dump_p.add_argument("--where")
    dump_p.add_argument("--batch-size", type=int, default=1000)
    dump_p.add_argument("--out", required=True)

    args = parser.parse_args()
    config = read_env(args.env)
    base_url = args.base_url or str(config.get("base_url", "")).strip()
    if not base_url:
        raise SystemExit("missing base_url; pass --base-url or provide environment_access.md")
    auths = auth_candidates(config)

    if args.cmd == "get":
        params = {}
        for item in args.param:
            if "=" not in item:
                raise SystemExit(f"invalid --param {item!r}; expected name=value")
            key, value = item.split("=", 1)
            params[key] = value
        result = request_json(base_url, "GET", args.path, params=params, auths=auths)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if args.cmd == "query":
        sql = args.sql if args.sql is not None else sys.stdin.read()
        result = query_sql(base_url, sql, auths)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if args.cmd == "dump-view":
        clauses = []
        if args.collection:
            clauses.append(f"collection_id = {shell_quote_sql(args.collection)}")
        if args.where:
            clauses.append(f"({args.where})")
        where = " where " + " and ".join(clauses) if clauses else ""
        offset = 0
        total = 0
        with Path(args.out).open("w", encoding="utf-8") as handle:
            while True:
                sql = f"select * from {args.view}{where} limit {args.batch_size} offset {offset}"
                result = query_sql(base_url, sql, auths)
                rows = rows_from_result(result)
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                total += len(rows)
                if len(rows) < args.batch_size:
                    break
                offset += args.batch_size
        print(json.dumps({"rows_written": total, "out": args.out}, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
