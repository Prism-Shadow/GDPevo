#!/usr/bin/env python3
"""Fetch a portable snapshot of the engineering portfolio task API."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


DEFAULT_ENDPOINTS = [
    "/api/work-items",
    "/api/mix-targets",
    "/api/sla-policy",
    "/api/releases",
    "/api/milestones",
    "/api/dependencies",
    "/api/blockers",
]


def fetch_json(base_url, path, token=None):
    url = base_url.rstrip("/") + path
    headers = {}
    if token:
        headers["X-Env-Token"] = token
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch allowed GET endpoints from the portfolio task environment."
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("TASK_ENV_BASE_URL"),
        help="Task environment base URL, for example http://task-env:9024",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("TASK_ENV_TOKEN"),
        help="Optional X-Env-Token, only if runtime access notes provide one.",
    )
    parser.add_argument(
        "--release",
        action="append",
        default=[],
        help="Optional release ID to also fetch via /api/releases/{release_id}.",
    )
    parser.add_argument("--out", help="Output JSON path. Defaults to stdout.")
    args = parser.parse_args()

    if not args.base_url:
        parser.error("--base-url is required unless TASK_ENV_BASE_URL is set")

    snapshot = {"base_url": args.base_url.rstrip("/"), "endpoints": {}, "errors": {}}
    endpoints = list(DEFAULT_ENDPOINTS)
    endpoints.extend(f"/api/releases/{release_id}" for release_id in args.release)

    for path in endpoints:
        try:
            snapshot["endpoints"][path] = fetch_json(args.base_url, path, args.token)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            snapshot["errors"][path] = str(exc)

    output = json.dumps(snapshot, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(output)
            handle.write("\n")
    else:
        sys.stdout.write(output)
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
