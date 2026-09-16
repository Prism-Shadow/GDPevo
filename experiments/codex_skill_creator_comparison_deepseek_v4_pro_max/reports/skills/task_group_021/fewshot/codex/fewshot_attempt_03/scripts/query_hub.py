#!/usr/bin/env python3
"""Deterministic paginated query helper for the Asteria Fleet Data Quality Hub.

Usage:
    python3 query_hub.py <base_url> <sql> [--credential <cred>] [--page-size <n>]

Reads environment_access.md-style configuration: the base URL is the
hub root; if the task supplies a query credential, pass it as --credential.

The hub POST /api/query returns {"items": [...], "total": N, "limit": L, "offset": O}.
This script pages through all results and writes the full JSON array to stdout.
"""

import json
import sys
import urllib.request
import urllib.error


def query_all(base_url, sql, credential=None, page_size=500):
    all_items = []
    offset = 0

    while True:
        body = json.dumps({"sql": sql, "limit": page_size, "offset": offset})
        data = body.encode("utf-8")

        req = urllib.request.Request(
            f"{base_url}/api/query",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        if credential:
            req.add_header("Authorization", f"Bearer {credential}")

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"HTTP {e.code}: {body}", file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as e:
            print(f"Connection error: {e.reason}", file=sys.stderr)
            sys.exit(1)

        items = result.get("items", [])
        total = result.get("total", 0)

        all_items.extend(items)

        offset += len(items)
        if offset >= total or not items:
            break

    return all_items


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Paginated query helper for Fleet DQ Hub")
    parser.add_argument("base_url", help="Hub base URL (e.g., http://task-env:9021)")
    parser.add_argument("sql", help="SQL query to execute")
    parser.add_argument("--credential", default=None, help="Bearer token for /api/query")
    parser.add_argument("--page-size", type=int, default=500, help="Rows per page")
    args = parser.parse_args()

    items = query_all(args.base_url, args.sql, args.credential, args.page_size)
    json.dump(items, sys.stdout, indent=2, ensure_ascii=False)
