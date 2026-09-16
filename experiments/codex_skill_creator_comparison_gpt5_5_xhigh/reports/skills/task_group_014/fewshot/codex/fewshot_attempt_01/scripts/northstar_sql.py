#!/usr/bin/env python3
"""Run a SQL query against the Northstar task environment."""

import argparse
import json
import sys
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description="POST SQL to /sql/query.")
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument("--token", required=True, help="Bearer token from the task prompt")
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds")
    parser.add_argument("sql", nargs="*", help="SQL text; stdin is used when omitted")
    args = parser.parse_args()

    sql = " ".join(args.sql).strip() if args.sql else sys.stdin.read().strip()
    if not sql:
        print("SQL text is required", file=sys.stderr)
        return 2

    base_url = args.base_url.rstrip("/")
    request = urllib.request.Request(
        f"{base_url}/sql/query",
        data=json.dumps({"sql": sql}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {args.token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(body or str(exc), file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        print(json.dumps(json.loads(body), indent=2, sort_keys=False))
    except json.JSONDecodeError:
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
