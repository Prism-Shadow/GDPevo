#!/usr/bin/env python3
"""Collect common Investigation Review Hub endpoint responses as JSON."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_ENDPOINTS = [
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch common read-only Investigation Review Hub endpoints."
    )
    parser.add_argument("--base-url", required=True, help="Hub base URL")
    parser.add_argument("--matter-id", help="Matter ID to pass as a query parameter")
    parser.add_argument("--api-key", help="API key value for X-API-Key")
    parser.add_argument(
        "--api-key-header",
        default="X-API-Key",
        help="API key header name, default: X-API-Key",
    )
    parser.add_argument(
        "--endpoint",
        action="append",
        dest="endpoints",
        help="Endpoint path to fetch. Repeat to override the default endpoint list.",
    )
    parser.add_argument(
        "--sql",
        action="append",
        help="SQL query to send to /api/query. Repeat for multiple queries.",
    )
    return parser.parse_args()


def make_url(base_url: str, path: str, matter_id: str | None = None) -> str:
    base = base_url.rstrip("/") + "/"
    path = path.lstrip("/")
    url = urllib.parse.urljoin(base, path)
    if matter_id:
        joiner = "&" if "?" in url else "?"
        url = f"{url}{joiner}{urllib.parse.urlencode({'matter_id': matter_id})}"
    return url


def request_json(
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
) -> Any:
    data = None
    req_headers = dict(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8")
    if not raw.strip():
        return None
    return json.loads(raw)


def fetch_endpoint(
    base_url: str,
    endpoint: str,
    headers: dict[str, str],
    matter_id: str | None,
) -> dict[str, Any]:
    attempts = []
    if matter_id and endpoint != "/api/schema":
        attempts.append(make_url(base_url, endpoint, matter_id))
    attempts.append(make_url(base_url, endpoint, None))

    errors = []
    for url in attempts:
        try:
            return {"ok": True, "url": url, "data": request_json("GET", url, headers)}
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
            errors.append({"url": url, "error": str(exc)})
    return {"ok": False, "endpoint": endpoint, "errors": errors}


def post_sql(base_url: str, headers: dict[str, str], sql: str) -> dict[str, Any]:
    url = make_url(base_url, "/api/query", None)
    errors = []
    for key in ("sql", "query"):
        try:
            return {
                "ok": True,
                "url": url,
                "payload_key": key,
                "data": request_json("POST", url, headers, {key: sql}),
            }
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
            errors.append({"payload_key": key, "error": str(exc)})
    return {"ok": False, "url": url, "sql": sql, "errors": errors}


def main() -> int:
    args = parse_args()
    headers = {"Accept": "application/json"}
    if args.api_key:
        headers[args.api_key_header] = args.api_key

    endpoints = args.endpoints or DEFAULT_ENDPOINTS
    result: dict[str, Any] = {
        "base_url": args.base_url,
        "matter_id": args.matter_id,
        "endpoints": {},
        "queries": [],
    }

    for endpoint in endpoints:
        result["endpoints"][endpoint] = fetch_endpoint(
            args.base_url, endpoint, headers, args.matter_id
        )

    for sql in args.sql or []:
        result["queries"].append(post_sql(args.base_url, headers, sql))

    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
