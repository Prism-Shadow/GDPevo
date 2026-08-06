#!/usr/bin/env python3
"""Fetch a matter-scoped Investigation Review Hub snapshot."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


ENDPOINTS = {
    "matters": "/api/matters",
    "subpoena_categories": "/api/subpoena-categories",
    "productions": "/api/productions",
    "custodian_sources": "/api/custodian-sources",
    "documents": "/api/documents/search",
    "privilege_log": "/api/privilege-log",
    "qc_findings": "/api/qc-findings",
    "retention_events": "/api/retention-events",
    "remediation_actions": "/api/remediation-actions",
}


def get_json(base_url: str, path: str, matter_id: str, api_key: str | None) -> object:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    url = f"{url}?{urllib.parse.urlencode({'matter_id': matter_id})}"
    request = urllib.request.Request(url)
    if api_key:
        request.add_header("X-API-Key", api_key)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"GET {url} failed: HTTP {exc.code}: {body}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Review Hub base URL")
    parser.add_argument("--matter-id", required=True, help="Matter ID to fetch")
    parser.add_argument("--api-key", default=None, help="Optional X-API-Key value")
    args = parser.parse_args()

    snapshot = {
        "matter_id": args.matter_id,
        "endpoints": {},
    }
    for name, path in ENDPOINTS.items():
        snapshot["endpoints"][name] = get_json(args.base_url, path, args.matter_id, args.api_key)

    json.dump(snapshot, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
