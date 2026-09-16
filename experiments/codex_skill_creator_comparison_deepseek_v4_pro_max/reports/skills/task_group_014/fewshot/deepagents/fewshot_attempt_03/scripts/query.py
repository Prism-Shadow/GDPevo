#!/usr/bin/env python3
"""Execute a SQL query against the Northstar payer-operations environment.

Usage:
    python3 query.py "<SQL>" --base-url <URL> --token <BEARER_TOKEN>

The script POSTs to {base_url}/sql/query with the Authorization header
and prints the JSON response to stdout.
"""

import argparse
import json
import sys
import urllib.request
import urllib.error


def main():
    parser = argparse.ArgumentParser(
        description="Run a SQL query against Northstar payer ops SQL endpoint."
    )
    parser.add_argument("sql", help="SQL query string")
    parser.add_argument(
        "--base-url",
        required=True,
        help="Task environment base URL, e.g. http://task-env:9014",
    )
    parser.add_argument(
        "--token",
        required=True,
        help="Bearer token for the SQL endpoint, e.g. pa-review-token-014",
    )
    args = parser.parse_args()

    url = args.base_url.rstrip("/") + "/sql/query"
    payload = json.dumps({"sql": args.sql}).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {args.token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            json.dump(result, sys.stdout, indent=2)
            sys.stdout.write("\n")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
