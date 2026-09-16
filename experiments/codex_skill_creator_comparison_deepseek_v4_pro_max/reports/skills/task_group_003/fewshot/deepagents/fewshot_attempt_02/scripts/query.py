#!/usr/bin/env python3
"""
Support console API query helper.

Fetches records from the support console and prints them as formatted JSON.
Use this for bulk lookups when the agent needs several related records at once.

Usage:
  python3 scripts/query.py <base_url> <endpoint> [<id>]

Examples:
  python3 scripts/query.py http://task-env:9003 /api/tickets/TCK-5107
  python3 scripts/query.py http://task-env:9003 /api/outages
  python3 scripts/query.py http://task-env:9003 /api/catalog
"""

import json
import sys
import urllib.request
import urllib.error


def fetch_json(url: str):
    """GET a JSON endpoint and return the parsed result."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return {"_error": f"HTTP {e.code}", "_body": body[:500]}
    except urllib.error.URLError as e:
        return {"_error": f"URL error: {e.reason}"}


def main():
    if len(sys.argv) < 3:
        print("Usage: query.py <base_url> <endpoint> [<resource_id>]")
        print("Example: query.py http://task-env:9003 /api/tickets/TCK-5107")
        sys.exit(1)

    base = sys.argv[1].rstrip("/")
    endpoint = sys.argv[2]
    resource_id = sys.argv[3] if len(sys.argv) > 3 else ""

    url = f"{base}{endpoint}"
    if resource_id:
        url = f"{url}/{resource_id}"

    result = fetch_json(url)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
