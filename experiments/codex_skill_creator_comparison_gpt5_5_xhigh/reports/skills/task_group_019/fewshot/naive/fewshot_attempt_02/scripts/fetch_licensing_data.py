#!/usr/bin/env python3
"""Fetch read-only licensing task data from allowed endpoints."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


BLOCKED = {"/api/judge"}


def endpoint_name(endpoint: str) -> str:
    name = endpoint.strip("/").replace("/", "__") or "root"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name) + ".json"


def request_json(url: str, *, method: str = "GET", token: str | None = None, body: object | None = None) -> object:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-Task-Token"] = token
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL from environment_access.md")
    parser.add_argument("--out", required=True, help="Output directory for fetched JSON files")
    parser.add_argument("--endpoint", action="append", default=[], help="GET endpoint path, repeatable")
    parser.add_argument("--sql-token", help="SQL token from environment_access.md, if provided")
    parser.add_argument("--sql", action="append", default=[], help="Read-only SQL SELECT query, repeatable")
    parser.add_argument("--sql-limit", type=int, default=500, help="Limit sent with each SQL query")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    base = args.base_url.rstrip("/") + "/"

    manifest: dict[str, object] = {"base_url": args.base_url, "files": []}

    for endpoint in args.endpoint:
        path = "/" + endpoint.lstrip("/")
        if path in BLOCKED:
            raise SystemExit(f"Refusing blocked endpoint: {path}")
        url = urllib.parse.urljoin(base, path.lstrip("/"))
        data = request_json(url)
        file_path = out / endpoint_name(path)
        file_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest["files"].append(str(file_path))

    for index, query in enumerate(args.sql, start=1):
        if not query.lstrip().lower().startswith("select"):
            raise SystemExit("Only read-only SELECT SQL queries are allowed")
        if not args.sql_token:
            raise SystemExit("--sql-token is required when --sql is used")
        url = urllib.parse.urljoin(base, "api/sql")
        data = request_json(
            url,
            method="POST",
            token=args.sql_token,
            body={"query": query, "params": [], "limit": args.sql_limit},
        )
        file_path = out / f"sql_{index:02d}.json"
        file_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest["files"].append(str(file_path))

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}", file=sys.stderr)
        raise SystemExit(1)
