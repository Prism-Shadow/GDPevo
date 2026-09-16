#!/usr/bin/env python3
"""Collect Investigation Review Hub endpoint data for one matter.

This helper intentionally uses only stdlib modules. It does not know any
matter-specific IDs or answers. Pass the task-provided base URL and, when the
task provides one, the query API header/key.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


ENDPOINTS = [
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


def request_json(url: str, headers: dict[str, str], method: str = "GET", body: Any = None) -> Any:
    data = None
    req_headers = dict(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=req_headers, method=method)
    with urlopen(req, timeout=20) as response:
        raw = response.read().decode("utf-8")
    if not raw.strip():
        return None
    return json.loads(raw)


def fetch_get(base_url: str, path: str, matter_id: str, headers: dict[str, str]) -> dict[str, Any]:
    endpoint_url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    attempts = [
        endpoint_url + "?" + urlencode({"matter_id": matter_id}),
        endpoint_url,
    ]
    errors: list[str] = []
    for url in attempts:
        try:
            return {"ok": True, "url": url, "data": request_json(url, headers)}
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append(f"{url}: {exc}")
    return {"ok": False, "url": endpoint_url, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True, help="Task-provided TASK_ENV_BASE_URL")
    parser.add_argument("--matter-id", required=True, help="Matter ID to review")
    parser.add_argument("--api-key-header", help="Optional API key header name")
    parser.add_argument("--api-key", help="Optional API key value")
    parser.add_argument("--out", default="-", help="Output JSON path, or '-' for stdout")
    args = parser.parse_args()

    headers: dict[str, str] = {"Accept": "application/json"}
    if args.api_key_header and args.api_key:
        headers[args.api_key_header] = args.api_key

    snapshot: dict[str, Any] = {
        "matter_id": args.matter_id,
        "endpoints": {},
        "query_probe": None,
    }

    for path in ENDPOINTS:
        snapshot["endpoints"][path] = fetch_get(args.base_url, path, args.matter_id, headers)

    query_url = urljoin(args.base_url.rstrip("/") + "/", "api/query")
    if args.api_key_header and args.api_key:
        try:
            snapshot["query_probe"] = {
                "ok": True,
                "url": query_url,
                "data": request_json(query_url, headers, method="POST", body={"query": "SELECT 1 AS ok"}),
            }
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            snapshot["query_probe"] = {"ok": False, "url": query_url, "error": str(exc)}

    output = json.dumps(snapshot, indent=2, sort_keys=True)
    if args.out == "-":
        print(output)
    else:
        Path(args.out).write_text(output + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
