#!/usr/bin/env python3
"""Snapshot allowed Investigation Review Hub endpoints using only stdlib."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


GET_ENDPOINTS = [
    "/api/schema",
    "/api/matters",
    "/api/subpoena-categories",
    "/api/productions",
    "/api/custodian-sources",
    "/api/documents/search",
    "/api/privilege-log",
    "/api/qc-findings",
    "/api/retention-events",
    "/api/remediation-actions",
]


def fetch_json(url: str, api_key: str | None) -> dict:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {"_raw": body}
            return {"ok": True, "status": response.status, "url": url, "data": data}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "status": exc.code, "url": url, "error": body}
    except urllib.error.URLError as exc:
        return {"ok": False, "status": None, "url": url, "error": str(exc)}


def endpoint_url(base_url: str, endpoint: str, matter_id: str | None, filtered: bool) -> str:
    base = base_url.rstrip("/") + "/"
    url = urllib.parse.urljoin(base, endpoint.lstrip("/"))
    if filtered and matter_id:
        query = {"matter_id": matter_id, "limit": "10000"}
        return url + "?" + urllib.parse.urlencode(query)
    return url


def has_data(result: dict) -> bool:
    if not result.get("ok"):
        return False
    data = result.get("data")
    if isinstance(data, list):
        return bool(data)
    if isinstance(data, dict):
        for key in ("data", "results", "items", "records", "rows"):
            value = data.get(key)
            if isinstance(value, list) and value:
                return True
        return bool(data)
    return data is not None


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch allowed Investigation Review Hub endpoints.")
    parser.add_argument("base_url", help="Hub base URL, for example http://task-env:9017/")
    parser.add_argument("--matter-id", help="Matter ID used for matter_id filtering when supported.")
    parser.add_argument("--api-key", help="Value for X-API-Key when the task provides one.")
    parser.add_argument("--out", help="Write JSON snapshot to this path instead of stdout.")
    args = parser.parse_args()

    snapshot = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "matter_id": args.matter_id,
        "endpoints": {},
    }

    for endpoint in GET_ENDPOINTS:
        result = fetch_json(endpoint_url(args.base_url, endpoint, args.matter_id, True), args.api_key)
        if args.matter_id and not has_data(result):
            fallback = fetch_json(endpoint_url(args.base_url, endpoint, args.matter_id, False), args.api_key)
            if fallback.get("ok"):
                fallback["note"] = "unfiltered fallback after filtered request returned no data or failed"
                result = fallback
        snapshot["endpoints"][endpoint] = result

    output = json.dumps(snapshot, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(output + "\n")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
