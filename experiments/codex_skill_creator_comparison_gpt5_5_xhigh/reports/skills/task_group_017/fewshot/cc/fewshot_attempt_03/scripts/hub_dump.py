#!/usr/bin/env python3
"""Dump matter-scoped Investigation Review Hub records.

This helper is intentionally generic. It only talks to a task-provided hub URL
and writes the JSON responses it can retrieve.
"""

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


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def build_url(base_url: str, endpoint: str, params: dict[str, str] | None = None) -> str:
    endpoint = "/" + endpoint.lstrip("/")
    url = normalize_base_url(base_url) + endpoint
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return url


def request_json(
    method: str,
    url: str,
    headers: dict[str, str],
    payload: Any | None = None,
) -> tuple[Any, str]:
    data = None
    req_headers = dict(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as response:
        text = response.read().decode("utf-8")
    if not text.strip():
        return None, text
    return json.loads(text), text


def error_message(exc: BaseException) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return f"HTTP {exc.code}: {body[:500]}"
    return str(exc)


def record_matter_id(record: Any) -> str | None:
    if not isinstance(record, dict):
        return None
    for key in ("matter_id", "matterId", "matter", "matterID"):
        value = record.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            nested = record_matter_id(value)
            if nested:
                return nested
    return None


def filter_for_matter(data: Any, matter_id: str | None) -> Any:
    if not matter_id:
        return data
    if isinstance(data, list):
        matching = [item for item in data if record_matter_id(item) == matter_id]
        return matching if matching else data
    if isinstance(data, dict):
        data_matter = record_matter_id(data)
        if data_matter == matter_id:
            return data
        filtered: dict[str, Any] = {}
        changed = False
        for key, value in data.items():
            if isinstance(value, list):
                filtered_value = [item for item in value if record_matter_id(item) == matter_id]
                filtered[key] = filtered_value if filtered_value else value
                changed = changed or bool(filtered_value)
            else:
                filtered[key] = value
        return filtered if changed else data
    return data


def fetch_endpoint(
    base_url: str,
    endpoint: str,
    headers: dict[str, str],
    matter_id: str | None,
) -> dict[str, Any]:
    attempts = []
    if matter_id:
        attempts.append(build_url(base_url, endpoint, {"matter_id": matter_id}))
    attempts.append(build_url(base_url, endpoint))

    errors: list[str] = []
    for url in attempts:
        try:
            data, _text = request_json("GET", url, headers)
            return {
                "status": "ok",
                "url": url,
                "data": filter_for_matter(data, matter_id),
            }
        except Exception as exc:  # noqa: BLE001 - report and try fallback URL.
            errors.append(f"{url}: {error_message(exc)}")
    return {"status": "error", "endpoint": endpoint, "errors": errors}


def post_sql_query(base_url: str, headers: dict[str, str], sql: str) -> dict[str, Any]:
    url = build_url(base_url, "/api/query")
    errors: list[str] = []
    for payload in ({"query": sql}, {"sql": sql}):
        try:
            data, _text = request_json("POST", url, headers, payload)
            return {"status": "ok", "url": url, "payload_keys": list(payload), "data": data}
        except Exception as exc:  # noqa: BLE001 - try common payload variants.
            errors.append(f"{list(payload)}: {error_message(exc)}")
    return {"status": "error", "url": url, "errors": errors}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task hub base URL.")
    parser.add_argument("--matter-id", help="Matter ID to filter for.")
    parser.add_argument("--api-key", help="API key for SQL/query endpoint, if provided.")
    parser.add_argument(
        "--api-key-header",
        default="X-API-Key",
        help="Header name for the API key. Default: X-API-Key.",
    )
    parser.add_argument(
        "--endpoints",
        help="Comma-separated endpoint list. Defaults to common hub endpoints.",
    )
    parser.add_argument("--sql", help="Optional SQL query to post to /api/query.")
    parser.add_argument("--out", required=True, help="Output JSON path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    headers = {"Accept": "application/json"}
    if args.api_key:
        headers[args.api_key_header] = args.api_key

    endpoints = DEFAULT_ENDPOINTS
    if args.endpoints:
        endpoints = [item.strip() for item in args.endpoints.split(",") if item.strip()]

    output: dict[str, Any] = {
        "base_url": normalize_base_url(args.base_url),
        "matter_id": args.matter_id,
        "endpoints": {},
    }

    for endpoint in endpoints:
        output["endpoints"][endpoint] = fetch_endpoint(
            args.base_url,
            endpoint,
            headers,
            args.matter_id,
        )

    if args.sql:
        output["sql_query"] = post_sql_query(args.base_url, headers, args.sql)

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, sort_keys=True)
        handle.write("\n")

    failed = [
        endpoint
        for endpoint, result in output["endpoints"].items()
        if isinstance(result, dict) and result.get("status") != "ok"
    ]
    if failed:
        print(f"Wrote {args.out}; failed endpoints: {', '.join(failed)}", file=sys.stderr)
    else:
        print(f"Wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
