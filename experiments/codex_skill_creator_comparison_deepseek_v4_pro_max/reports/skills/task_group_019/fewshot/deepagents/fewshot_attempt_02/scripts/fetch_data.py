#!/usr/bin/env python3
"""
Fetch all licensing data from the task environment REST API.

Usage:
  python fetch_data.py --base-url URL [--domain all|contractor|liquor|alcohol|renewal] [--token TOKEN]

The script fetches /api/policies plus the selected domain endpoints and
writes one JSON object to stdout. The output keys match the endpoint paths
(e.g. "contractor_applications", "alcohol_licensees").

Credentials:
  --token is used as X-Task-Token header on every request.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Endpoint registry
# ---------------------------------------------------------------------------

POLICIES = "/api/policies"

DOMAIN_ENDPOINTS = {
    "contractor": [
        "/api/contractor/applications",
        "/api/contractor/bonds",
        "/api/contractor/insurance",
        "/api/contractor/license-history",
        "/api/contractor/violations",
        "/api/contractor/correspondence",
        "/api/contractor/inspections",
    ],
    "liquor": [
        "/api/liquor/applications",
        "/api/liquor/settlements",
        "/api/liquor/privileges",
        "/api/liquor/incidents",
        "/api/liquor/site-evidence",
    ],
    "alcohol": [
        "/api/alcohol/licensees",
        "/api/alcohol/violations",
    ],
    "renewal": [
        "/api/renewal/rules",
    ],
}


def _key(path: str) -> str:
    """Convert an API path like /api/contractor/applications to a stable key."""
    return path.strip("/").replace("/", "_")


def fetch_one(base_url: str, path: str, token: str | None) -> object:
    """GET *path* from *base_url* and return the parsed JSON body."""
    url = base_url.rstrip("/") + path
    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("X-Task-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        msg = f"HTTP {exc.code} for {url}"
        try:
            detail = exc.read().decode("utf-8", errors="replace")
            msg += f": {detail[:200]}"
        except Exception:
            pass
        raise SystemExit(msg) from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Connection error for {url}: {exc.reason}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch licensing data from the task environment.")
    parser.add_argument("--base-url", default=os.environ.get("TASK_ENV_BASE_URL", "http://task-env:9019"),
                        help="Base URL of the licensing environment (default: http://task-env:9019 or $TASK_ENV_BASE_URL)")
    parser.add_argument("--token", default=os.environ.get("TASK_TOKEN", "licensing-review-019"),
                        help="X-Task-Token header value (default: licensing-review-019 or $TASK_TOKEN)")
    parser.add_argument("--domain", choices=["all", "contractor", "liquor", "alcohol", "renewal"], default="all",
                        help="Which domain endpoints to fetch (default: all)")
    args = parser.parse_args()

    result: dict[str, object] = {}

    # Always fetch policies
    policies = fetch_one(args.base_url, POLICIES, args.token)
    if policies is not None:
        result[_key(POLICIES)] = policies

    # Determine which endpoints to fetch
    if args.domain == "all":
        paths: list[str] = []
        for ep_list in DOMAIN_ENDPOINTS.values():
            paths.extend(ep_list)
    else:
        paths = DOMAIN_ENDPOINTS.get(args.domain, [])

    for path in paths:
        data = fetch_one(args.base_url, path, args.token)
        if data is not None:
            result[_key(path)] = data

    json.dump(result, sys.stdout, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
