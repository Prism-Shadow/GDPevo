#!/usr/bin/env python3
"""Fetch MedBridge Sales Ops API records for template-driven JSON tasks.

This helper is intentionally generic. It does not know any task-specific answer
values; it only retrieves allowed API resources and prints JSON for inspection.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


COLLECTIONS = [
    "customers",
    "products",
    "rfqs",
    "quotes",
    "freight-quotes",
    "policies",
    "opportunities",
    "invoices",
    "payments",
    "revenue-journals",
    "events",
    "vouchers",
]


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def fetch_json(base_url: str, path: str) -> Any:
    if not path.startswith("/"):
        path = "/" + path
    url = normalize_base_url(base_url) + path
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return {"error": "http_error", "status": exc.code, "path": path}
    except urllib.error.URLError as exc:
        return {"error": "url_error", "reason": str(exc.reason), "path": path}

    if not data.strip():
        return None
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return {"error": "non_json_response", "path": path, "body": data}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch allowed MedBridge Sales Ops API records."
    )
    parser.add_argument("base_url", help="Task environment base URL.")
    parser.add_argument(
        "--search",
        action="append",
        default=[],
        help="Search term to send to /api/search. Repeatable.",
    )
    parser.add_argument(
        "--resource",
        action="append",
        default=[],
        help=(
            "Resource path under /api, such as quotes/<id>, vouchers/<code>, "
            "or customers. Repeatable."
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch all standard collection endpoints.",
    )
    args = parser.parse_args()

    result: dict[str, Any] = {}

    if args.search:
        result["search"] = {}
        for term in args.search:
            query = urllib.parse.urlencode({"q": term})
            result["search"][term] = fetch_json(args.base_url, f"/api/search?{query}")

    if args.resource:
        result["resources"] = {}
        for resource in args.resource:
            clean = resource.strip("/")
            result["resources"][clean] = fetch_json(args.base_url, f"/api/{clean}")

    if args.all:
        result["collections"] = {
            collection: fetch_json(args.base_url, f"/api/{collection}")
            for collection in COLLECTIONS
        }

    if not result:
        result["api"] = fetch_json(args.base_url, "/api")

    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
