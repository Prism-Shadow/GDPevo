#!/usr/bin/env python3
"""Fetch MedBridge Sales Ops API records for JSON-answer tasks."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


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


def normalize_base_url(value: str) -> str:
    return value.rstrip("/") + "/"


def api_url(base_url: str, path: str) -> str:
    clean_path = path.strip("/")
    return normalize_base_url(base_url) + clean_path


def fetch_json(base_url: str, path: str) -> dict[str, Any]:
    url = api_url(base_url, path)
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
            try:
                data: Any = json.loads(body)
            except json.JSONDecodeError:
                data = body
            return {"path": "/" + path.strip("/"), "status": response.status, "data": data}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"path": "/" + path.strip("/"), "status": exc.code, "error": body}
    except URLError as exc:
        return {"path": "/" + path.strip("/"), "status": None, "error": str(exc.reason)}


def endpoint_for_id(record_id: str) -> str | None:
    if record_id.startswith("CUST-"):
        return f"api/customers/{quote(record_id)}"
    if record_id.startswith("RFQ-"):
        return f"api/rfqs/{quote(record_id)}"
    if record_id.startswith("Q-"):
        return f"api/quotes/{quote(record_id)}"
    if record_id.startswith("FR-"):
        return f"api/freight-quotes/{quote(record_id)}"
    if record_id.startswith("OPP-"):
        return f"api/opportunities/{quote(record_id)}"
    if record_id.startswith("INV-"):
        return f"api/invoices/{quote(record_id)}"
    if record_id.startswith("PAY-"):
        return f"api/payments/{quote(record_id)}"
    if record_id.startswith(("RJ-", "REV-", "JRN-")):
        return f"api/revenue-journals/{quote(record_id)}"
    if record_id.startswith("EVT-"):
        return f"api/events/{quote(record_id)}"
    return None


def add_endpoint(paths: list[str], endpoint: str) -> None:
    clean = endpoint.strip("/")
    if not clean:
        return
    if clean == "health":
        paths.append("health")
    elif clean == "api" or clean.startswith("api/"):
        paths.append(clean)
    else:
        paths.append(f"api/{clean}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch MedBridge Sales Ops API records and print JSON results."
    )
    parser.add_argument(
        "base_url",
        nargs="?",
        default=os.environ.get("TASK_ENV_BASE_URL") or os.environ.get("BASE_URL"),
        help="Task API base URL. Defaults to TASK_ENV_BASE_URL or BASE_URL.",
    )
    parser.add_argument("--id", action="append", default=[], help="Record ID to fetch by prefix.")
    parser.add_argument("--product", action="append", default=[], help="Product code to fetch.")
    parser.add_argument("--voucher", action="append", default=[], help="Voucher code to fetch.")
    parser.add_argument(
        "--endpoint",
        action="append",
        default=[],
        help="Endpoint or collection path to fetch, such as quotes or api/policies.",
    )
    parser.add_argument("--search", action="append", default=[], help="Search query.")
    parser.add_argument(
        "--all-collections",
        action="store_true",
        help="Fetch all standard API collections.",
    )
    parser.add_argument("--api", action="store_true", help="Fetch /api discovery.")
    parser.add_argument("--health", action="store_true", help="Fetch /health.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.base_url:
        print(
            json.dumps(
                {"error": "Provide base_url or set TASK_ENV_BASE_URL/BASE_URL."},
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    paths: list[str] = []
    if args.health:
        paths.append("health")
    if args.api:
        paths.append("api")
    for endpoint in args.endpoint:
        add_endpoint(paths, endpoint)
    if args.all_collections:
        paths.extend(f"api/{name}" for name in COLLECTIONS)
    for record_id in args.id:
        endpoint = endpoint_for_id(record_id)
        if endpoint is None:
            paths.append("api/search?" + urlencode({"q": record_id}))
        else:
            paths.append(endpoint)
    for product_code in args.product:
        paths.append(f"api/products/{quote(product_code)}")
    for voucher_code in args.voucher:
        paths.append(f"api/vouchers/{quote(voucher_code)}")
    for query in args.search:
        paths.append("api/search?" + urlencode({"q": query}))

    if not paths:
        paths = ["api"]

    seen: set[str] = set()
    results = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        results.append(fetch_json(args.base_url, path))

    print(json.dumps({"base_url": normalize_base_url(args.base_url), "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
