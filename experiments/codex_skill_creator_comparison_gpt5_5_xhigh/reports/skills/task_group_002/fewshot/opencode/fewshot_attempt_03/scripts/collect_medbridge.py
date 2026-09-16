#!/usr/bin/env python3
"""Collect MedBridge Sales Ops API records for a task.

The script intentionally gathers source records only. It does not write a final
answer because each task's answer_template.json controls the required schema.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import urlopen


DIRECT_COLLECTIONS = {
    "customers",
    "products",
    "rfqs",
    "quotes",
    "freight-quotes",
    "policies",
    "opportunities",
    "events",
    "vouchers",
}


def fetch_json(base_url: str, path: str) -> Any:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    with urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def add_record(records: dict[str, dict[str, Any]], collection: str, record_id: str, record: Any) -> None:
    if not collection or not record_id or not isinstance(record, dict):
        return
    records[collection][record_id] = record


def add_search_results(records: dict[str, dict[str, Any]], payload: Any) -> None:
    if not isinstance(payload, dict):
        return
    for item in payload.get("results", []):
        if not isinstance(item, dict):
            continue
        add_record(records, item.get("collection", ""), item.get("id", ""), item.get("record"))


def direct_fetch(base_url: str, collection: str, record_id: str) -> tuple[bool, Any]:
    if collection not in DIRECT_COLLECTIONS:
        return False, {"error": f"unsupported direct collection: {collection}"}
    try:
        payload = fetch_json(base_url, f"/api/{collection}/{quote(record_id)}")
    except (HTTPError, URLError, TimeoutError) as exc:
        return False, {"error": str(exc)}
    if isinstance(payload, dict) and "error" in payload:
        return False, payload
    return True, payload


def extract_related_terms(records: dict[str, dict[str, Any]]) -> set[str]:
    terms: set[str] = set()
    for collection_records in records.values():
        for record in collection_records.values():
            if not isinstance(record, dict):
                continue
            for key in ("customer_id", "quote_id", "opportunity_id", "event_id", "voucher_code"):
                value = record.get(key)
                if isinstance(value, str) and value:
                    terms.add(value)
            for item in record.get("line_items", []) or []:
                if isinstance(item, dict) and item.get("product_code"):
                    terms.add(str(item["product_code"]))
            for item in record.get("requested_modules", []) or []:
                if isinstance(item, dict) and item.get("product_code"):
                    terms.add(str(item["product_code"]))
            for phase in record.get("phases", []) or []:
                if not isinstance(phase, dict):
                    continue
                for key in ("invoice_id", "phase_id"):
                    value = phase.get(key)
                    if isinstance(value, str) and value:
                        terms.add(value)
            code = record.get("primary_product_code") or record.get("product_code") or record.get("code")
            if isinstance(code, str) and code:
                terms.add(code)
    return terms


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect MedBridge Sales Ops API records.")
    parser.add_argument("--base-url", required=True, help="Task API base URL, for example http://task-env:9002/")
    parser.add_argument("--term", action="append", default=[], help="Exact business identifier to search. Repeatable.")
    parser.add_argument(
        "--direct",
        action="append",
        default=[],
        help="Direct fetch in collection:id form, for example products:PRODUCT-CODE. Repeatable.",
    )
    parser.add_argument("--expand", action="store_true", help="Search related IDs discovered in the first pass.")
    parser.add_argument("--out", help="Write JSON output to this path instead of stdout.")
    args = parser.parse_args()

    records: dict[str, dict[str, Any]] = defaultdict(dict)
    errors: list[dict[str, str]] = []
    queried_terms: list[str] = []

    try:
        api_index = fetch_json(args.base_url, "/api")
    except (HTTPError, URLError, TimeoutError) as exc:
        api_index = {"error": str(exc)}

    for term in args.term:
        queried_terms.append(term)
        try:
            add_search_results(records, fetch_json(args.base_url, f"/api/search?q={quote(term)}"))
        except (HTTPError, URLError, TimeoutError) as exc:
            errors.append({"term": term, "error": str(exc)})

    for direct in args.direct:
        if ":" not in direct:
            errors.append({"direct": direct, "error": "expected collection:id"})
            continue
        collection, record_id = direct.split(":", 1)
        ok, payload = direct_fetch(args.base_url, collection, record_id)
        if ok:
            add_record(records, collection, record_id, payload)
        else:
            errors.append({"direct": direct, "error": json.dumps(payload, sort_keys=True)})

    if args.expand:
        for term in sorted(extract_related_terms(records) - set(queried_terms)):
            queried_terms.append(term)
            try:
                add_search_results(records, fetch_json(args.base_url, f"/api/search?q={quote(term)}"))
            except (HTTPError, URLError, TimeoutError) as exc:
                errors.append({"term": term, "error": str(exc)})

    output = {
        "api_index": api_index,
        "queried_terms": queried_terms,
        "records_by_collection": {key: dict(value) for key, value in sorted(records.items())},
        "errors": errors,
    }

    text = json.dumps(output, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    else:
        print(text)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
