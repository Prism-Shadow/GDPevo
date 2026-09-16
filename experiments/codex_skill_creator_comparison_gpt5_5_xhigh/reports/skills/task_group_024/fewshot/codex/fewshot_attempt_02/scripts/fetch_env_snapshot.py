#!/usr/bin/env python3
"""Fetch documented task-environment GET endpoints into one JSON file."""

import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ENDPOINTS = {
    "work-items": "/api/work-items",
    "mix-targets": "/api/mix-targets",
    "sla-policy": "/api/sla-policy",
    "releases": "/api/releases",
    "milestones": "/api/milestones",
    "dependencies": "/api/dependencies",
    "blockers": "/api/blockers",
}


def fetch_json(base_url, path, token=None, timeout=20):
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    headers = {"Accept": "application/json"}
    if token:
        headers["X-Env-Token"] = token
    request = Request(url, headers=headers, method="GET")
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=False, help="Task environment base URL")
    parser.add_argument("--out", default="-", help="Output JSON path, or '-' for stdout")
    parser.add_argument("--token", help="Optional X-Env-Token value")
    parser.add_argument(
        "--endpoint",
        action="append",
        choices=sorted(ENDPOINTS),
        help="Endpoint key to fetch; repeatable. Defaults to all documented GET endpoints.",
    )
    parser.add_argument("--list-endpoints", action="store_true", help="Print endpoint keys and exit")
    args = parser.parse_args()

    if args.list_endpoints:
        for key, path in ENDPOINTS.items():
            print(f"{key}\t{path}")
        return 0

    if not args.base_url:
        parser.error("--base-url is required unless --list-endpoints is used")

    selected = args.endpoint or list(ENDPOINTS)
    snapshot = {"base_url": args.base_url, "endpoints": {}}

    try:
        for key in selected:
            snapshot["endpoints"][key] = fetch_json(args.base_url, ENDPOINTS[key], args.token)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"fetch_env_snapshot.py: failed to fetch {key}: {exc}", file=sys.stderr)
        return 1

    rendered = json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    if args.out == "-":
        sys.stdout.write(rendered)
    else:
        Path(args.out).write_text(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
