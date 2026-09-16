#!/usr/bin/env python3
"""Fetch the composite case record from the clinic runtime.

Usage:
    python fetch_case.py <case_id> [--base-url URL]

Outputs the full composite JSON to stdout.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request


def fetch_case(case_id: str, base_url: str) -> dict:
    url = f"{base_url.rstrip('/')}/api/cases/{case_id}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP error {e.code} fetching {url}: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection error fetching {url}: {e.reason}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch a composite case record from the clinic runtime."
    )
    parser.add_argument("case_id", help="Target case identifier (e.g. CASE-RESP-102)")
    parser.add_argument(
        "--base-url",
        default="http://task-env:9016",
        help="Clinic runtime base URL (default: http://task-env:9016)",
    )
    args = parser.parse_args()

    data = fetch_case(args.case_id, args.base_url)
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
