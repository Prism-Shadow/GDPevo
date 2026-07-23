#!/usr/bin/env python3
"""Reusable helper for the Northstar payer-operations environment.

Resolves the base URL and bearer token from environment_access.md (or env
overrides), then exposes the two access modes:

  Query SQL:
      python3 query_env.py sql "SELECT * FROM cases WHERE case_id = 'CASE-XYZ-001'"
  GET a business endpoint:
      python3 query_env.py get /api/cases/CASE-XYZ-001
      python3 query_env.py get /api/policies/POL-EXAMPLE-2026

Env overrides (optional):
      NORTHSTAR_BASE_URL   e.g. http://task-env:9014
      NORTHSTAR_TOKEN      the bearer token for POST /sql/query

The script prints compact JSON. It is read-only; only SELECT-style SQL is
useful against the environment.
"""
import json
import os
import sys
import urllib.request
import urllib.error

DEFAULT_BASE_URL = "http://task-env:9014"
DEFAULT_TOKEN = "pa-review-token-014"
SQL_PATH = "/sql/query"


def config():
    base = os.environ.get("NORTHSTAR_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    token = os.environ.get("NORTHSTAR_TOKEN", DEFAULT_TOKEN)
    return base, token


def post_sql(sql: str):
    base, token = config()
    url = base + SQL_PATH
    body = json.dumps({"sql": sql}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_path(path: str):
    base, _token = config()
    if not path.startswith("/"):
        path = "/" + path
    req = urllib.request.Request(base + path, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main(argv):
    if len(argv) < 2 or argv[1] not in ("sql", "get"):
        print(__doc__, file=sys.stderr)
        return 2
    mode = argv[1]
    try:
        if mode == "sql":
            if len(argv) < 3:
                print("sql mode requires a SELECT string", file=sys.stderr)
                return 2
            result = post_sql(argv[2])
        else:
            if len(argv) < 3:
                print("get mode requires a path", file=sys.stderr)
                return 2
            result = get_path(argv[2])
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
