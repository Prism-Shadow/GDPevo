#!/usr/bin/env python3
"""Fetch MedBridge Sales Ops API records for quote and reconciliation tasks."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen


DEFAULT_COLLECTIONS = {
    "customers",
    "events",
    "freight-quotes",
    "invoices",
    "opportunities",
    "payments",
    "policies",
    "products",
    "quotes",
    "revenue-journals",
    "rfqs",
    "vouchers",
}


def normalize_base_url(raw: str) -> str:
    base = raw.strip().rstrip("/")
    if not base:
        raise ValueError("base URL is empty")
    if base.endswith("/api"):
        base = base[:-4]
    return base + "/"


def fetch_json(base_url: str, path: str) -> Any:
    url = urljoin(base_url, path.lstrip("/"))
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {url} failed with HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"GET {url} failed: {exc.reason}") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"GET {url} did not return JSON: {body[:500]}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch records from the MedBridge Sales Ops task API.",
    )
    parser.add_argument("base_url", help="Task API base URL, for example http://host:port/")
    parser.add_argument("--api", action="store_true", help="Fetch GET /api metadata")
    parser.add_argument(
        "--search",
        action="append",
        default=[],
        metavar="TEXT",
        help="Search text; may be repeated",
    )
    parser.add_argument(
        "--get",
        nargs=2,
        action="append",
        default=[],
        metavar=("COLLECTION", "ID"),
        help="Fetch /api/COLLECTION/ID; may be repeated",
    )
    parser.add_argument(
        "--list",
        action="append",
        default=[],
        metavar="COLLECTION",
        help="Fetch /api/COLLECTION; may be repeated",
    )
    return parser.parse_args()


def validate_collection(collection: str) -> str:
    if collection not in DEFAULT_COLLECTIONS:
        allowed = ", ".join(sorted(DEFAULT_COLLECTIONS))
        raise ValueError(f"unknown collection '{collection}'. Allowed: {allowed}")
    return collection


def main() -> int:
    args = parse_args()
    try:
        base_url = normalize_base_url(args.base_url)
        output: dict[str, Any] = {}

        if args.api:
            output["api"] = fetch_json(base_url, "api")

        if args.search:
            output["search"] = []
            for text in args.search:
                output["search"].append(
                    {
                        "query": text,
                        "result": fetch_json(base_url, f"api/search?q={quote(text)}"),
                    }
                )

        if args.get:
            output["get"] = []
            for collection, record_id in args.get:
                collection = validate_collection(collection)
                output["get"].append(
                    {
                        "collection": collection,
                        "id": record_id,
                        "result": fetch_json(
                            base_url,
                            f"api/{collection}/{quote(record_id, safe='')}",
                        ),
                    }
                )

        if args.list:
            output["list"] = []
            for collection in args.list:
                collection = validate_collection(collection)
                output["list"].append(
                    {
                        "collection": collection,
                        "result": fetch_json(base_url, f"api/{collection}"),
                    }
                )

        if not output:
            output["api"] = fetch_json(base_url, "api")

        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"medbridge_api.py: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
