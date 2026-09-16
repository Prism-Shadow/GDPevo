#!/usr/bin/env python3
"""
Query helper for the Investigation Review Hub SQL endpoint.

Usage:
    python3 query_hub.py "<SQL>" [--base-url URL] [--api-key KEY]
    python3 query_hub.py --file query.sql [--base-url URL] [--api-key KEY]

Defaults: base-url=http://task-env:9017, api-key=review-key-017
Output: JSON object with rows and count, or error message.
"""

import json
import sys
import urllib.request
import urllib.error


def query_hub(sql, base_url="http://task-env:9017", api_key="review-key-017"):
    url = f"{base_url}/api/query"
    data = json.dumps({"sql": sql}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {e.code}", "detail": body}
    except urllib.error.URLError as e:
        return {"error": "Connection failed", "detail": str(e.reason)}


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Query the Investigation Review Hub SQL endpoint."
    )
    parser.add_argument(
        "sql",
        nargs="?",
        help="SQL query string (enclose in quotes)",
    )
    parser.add_argument(
        "--file", "-f",
        help="Read SQL from a file",
    )
    parser.add_argument(
        "--base-url",
        default="http://task-env:9017",
        help="Hub base URL (default: http://task-env:9017)",
    )
    parser.add_argument(
        "--api-key",
        default="review-key-017",
        help="API key (default: review-key-017)",
    )
    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            sql = f.read().strip()
    elif args.sql:
        sql = args.sql
    else:
        parser.print_help()
        sys.exit(1)

    if not sql:
        print("Error: empty SQL query", file=sys.stderr)
        sys.exit(1)

    result = query_hub(sql, base_url=args.base_url, api_key=args.api_key)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
