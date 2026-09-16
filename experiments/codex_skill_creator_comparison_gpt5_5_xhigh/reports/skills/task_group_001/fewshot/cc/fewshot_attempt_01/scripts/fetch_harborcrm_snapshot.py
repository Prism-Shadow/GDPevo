#!/usr/bin/env python3
"""Fetch HarborCRM GET endpoints into one JSON snapshot."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


COMMON_ENDPOINTS = [
    "/api/events",
    "/api/tradeshows",
    "/api/import_batches",
    "/api/crm/accounts",
    "/api/crm/contacts",
    "/api/crm/opportunities",
    "/api/crm/campaign_members",
]

EVENT_ENDPOINTS = [
    "/api/events/{event_id}",
    "/api/events/{event_id}/sponsors",
]

SHOW_ENDPOINTS = [
    "/api/tradeshows/{show_id}",
    "/api/tradeshows/{show_id}/exhibitors",
    "/api/tradeshows/{show_id}/meeting_interest",
]

BATCH_ENDPOINTS = [
    "/api/import_batches/{batch_id}",
    "/api/import_batches/{batch_id}/raw_contacts",
    "/api/import_batches/{batch_id}/suppression",
]


def build_url(base_url: str, endpoint: str) -> str:
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", endpoint.lstrip("/"))


def fetch_json(base_url: str, endpoint: str, timeout: float) -> tuple[object | None, dict | None]:
    url = build_url(base_url, endpoint)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            if not raw.strip():
                return None, None
            return json.loads(raw), None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return None, {"status": exc.code, "reason": exc.reason, "body": body[:500]}
    except Exception as exc:  # Keep snapshot collection best-effort.
        return None, {"error": type(exc).__name__, "message": str(exc)}


def unique_endpoints(endpoints: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for endpoint in endpoints:
        if endpoint not in seen:
            seen.add(endpoint)
            result.append(endpoint)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="HarborCRM API base URL")
    parser.add_argument("--common", action="store_true", help="Fetch shared CRM and entity list endpoints")
    parser.add_argument("--event-id", action="append", default=[], help="Event ID to fetch")
    parser.add_argument("--show-id", action="append", default=[], help="Trade-show ID to fetch")
    parser.add_argument("--batch-id", action="append", default=[], help="Import batch ID to fetch")
    parser.add_argument(
        "--endpoint",
        action="append",
        default=[],
        help="Additional allowed endpoint path, for example /api/policies",
    )
    parser.add_argument("--out", help="Output JSON file. Defaults to stdout")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    endpoints: list[str] = []
    if args.common:
        endpoints.extend(COMMON_ENDPOINTS)
    for event_id in args.event_id:
        endpoints.extend(path.format(event_id=event_id) for path in EVENT_ENDPOINTS)
    for show_id in args.show_id:
        endpoints.extend(path.format(show_id=show_id) for path in SHOW_ENDPOINTS)
    for batch_id in args.batch_id:
        endpoints.extend(path.format(batch_id=batch_id) for path in BATCH_ENDPOINTS)
    endpoints.extend(args.endpoint)

    snapshot = {"base_url": args.base_url, "data": {}, "errors": {}}
    for endpoint in unique_endpoints(endpoints):
        data, error = fetch_json(args.base_url, endpoint, args.timeout)
        if error:
            snapshot["errors"][endpoint] = error
        else:
            snapshot["data"][endpoint] = data

    text = json.dumps(snapshot, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
