#!/usr/bin/env python3
"""Collect MedBridge Sales Ops API records related to task identifiers."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


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

PRIMARY_ID = {
    "customers": "id",
    "products": "code",
    "rfqs": "id",
    "quotes": "id",
    "freight-quotes": "id",
    "policies": "id",
    "opportunities": "id",
    "invoices": "id",
    "payments": "id",
    "revenue-journals": "id",
    "events": "id",
    "vouchers": "code",
}

ID_PATTERNS = {
    "customers": re.compile(r"\bCUST-[A-Z0-9-]+\b"),
    "rfqs": re.compile(r"\bRFQ-[A-Z0-9-]+\b"),
    "quotes": re.compile(r"\bQ-[A-Z0-9-]+\b"),
    "freight-quotes": re.compile(r"\bFR-[A-Z0-9-]+\b"),
    "opportunities": re.compile(r"\bOPP-[A-Z0-9-]+\b"),
    "invoices": re.compile(r"\bINV-[A-Z0-9-]+\b"),
    "payments": re.compile(r"\bPAY-[A-Z0-9-]+\b"),
    "revenue-journals": re.compile(r"\bRJ-[A-Z0-9-]+\b"),
    "events": re.compile(r"\bEVT-[A-Z0-9-]+\b"),
}


def fetch_json(base_url: str, path: str) -> Any:
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        with urlopen(url, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code} for {url}") from exc
    except URLError as exc:
        raise SystemExit(f"Could not reach {url}: {exc.reason}") from exc


def load_collections(base_url: str) -> dict[str, list[dict[str, Any]]]:
    data: dict[str, list[dict[str, Any]]] = {}
    for collection in COLLECTIONS:
        payload = fetch_json(base_url, f"/api/{collection}")
        data[collection] = payload.get("records", [])
    return data


def add_matches_from_text(ids: dict[str, set[str]], text: str) -> None:
    for collection, pattern in ID_PATTERNS.items():
        ids[collection].update(pattern.findall(text))


def add_cli_ids(args: argparse.Namespace, ids: dict[str, set[str]]) -> None:
    mapping = {
        "customer": "customers",
        "product": "products",
        "rfq": "rfqs",
        "quote": "quotes",
        "freight": "freight-quotes",
        "opportunity": "opportunities",
        "invoice": "invoices",
        "payment": "payments",
        "journal": "revenue-journals",
        "event": "events",
        "voucher": "vouchers",
    }
    for attr, collection in mapping.items():
        for value in getattr(args, attr) or []:
            ids[collection].add(value)


def find_exact(
    data: dict[str, list[dict[str, Any]]], ids: dict[str, set[str]]
) -> dict[str, list[dict[str, Any]]]:
    selected: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for collection, wanted in ids.items():
        key = PRIMARY_ID[collection]
        for record in data.get(collection, []):
            record_id = str(record.get(key, ""))
            if record_id in wanted and (collection, record_id) not in seen:
                selected[collection].append(record)
                seen.add((collection, record_id))
    return selected


def add_record(
    selected: dict[str, list[dict[str, Any]]],
    seen: set[tuple[str, str]],
    collection: str,
    record: dict[str, Any],
) -> None:
    key = PRIMARY_ID[collection]
    record_id = str(record.get(key, ""))
    if record_id and (collection, record_id) not in seen:
        selected[collection].append(record)
        seen.add((collection, record_id))


def expand_related(
    data: dict[str, list[dict[str, Any]]],
    selected: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    seen = {
        (collection, str(record.get(PRIMARY_ID[collection], "")))
        for collection, records in selected.items()
        for record in records
    }

    customer_ids = {
        record.get("customer_id")
        for collection in ("quotes", "rfqs", "opportunities", "events", "vouchers")
        for record in selected.get(collection, [])
        if record.get("customer_id")
    }
    quote_ids = {record.get("id") for record in selected.get("quotes", [])}
    opportunity_ids = {record.get("id") for record in selected.get("opportunities", [])}
    event_ids = {record.get("id") for record in selected.get("events", [])}
    voucher_codes = {record.get("code") for record in selected.get("vouchers", [])}
    product_codes = {
        item.get("product_code")
        for quote in selected.get("quotes", [])
        for item in quote.get("line_items", [])
        if item.get("product_code")
    }
    product_codes.update(
        item.get("product_code")
        for rfq in selected.get("rfqs", [])
        for item in rfq.get("requested_modules", [])
        if item.get("product_code")
    )

    for record in data["customers"]:
        if record.get("id") in customer_ids:
            add_record(selected, seen, "customers", record)

    for record in data["products"]:
        if record.get("code") in product_codes:
            add_record(selected, seen, "products", record)

    for record in data["freight-quotes"]:
        if record.get("quote_id") in quote_ids:
            add_record(selected, seen, "freight-quotes", record)

    linked_collections = ["invoices", "payments", "revenue-journals", "events", "vouchers"]
    for collection in linked_collections:
        for record in data[collection]:
            if record.get("opportunity_id") in opportunity_ids:
                add_record(selected, seen, collection, record)
            elif record.get("customer_id") in customer_ids and opportunity_ids:
                add_record(selected, seen, collection, record)

    for record in data["events"]:
        if record.get("id") in event_ids or record.get("voucher_code") in voucher_codes:
            add_record(selected, seen, "events", record)

    for record in data["vouchers"]:
        if record.get("event_id") in event_ids or record.get("code") in voucher_codes:
            add_record(selected, seen, "vouchers", record)

    for record in data["policies"]:
        add_record(selected, seen, "policies", record)

    return {collection: selected.get(collection, []) for collection in COLLECTIONS}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect MedBridge records related to prompt IDs."
    )
    parser.add_argument("base_url")
    parser.add_argument("--text", action="append", help="Prompt text to scan for IDs")
    parser.add_argument("--text-file", action="append", help="File to scan for IDs")
    for option in [
        "customer",
        "product",
        "rfq",
        "quote",
        "freight",
        "opportunity",
        "invoice",
        "payment",
        "journal",
        "event",
        "voucher",
    ]:
        parser.add_argument(f"--{option}", action="append")
    args = parser.parse_args()

    ids: dict[str, set[str]] = defaultdict(set)
    for text in args.text or []:
        add_matches_from_text(ids, text)
    for path in args.text_file or []:
        with open(path, "r", encoding="utf-8") as handle:
            add_matches_from_text(ids, handle.read())
    add_cli_ids(args, ids)

    data = load_collections(args.base_url)
    selected = find_exact(data, ids)
    expanded = expand_related(data, selected)
    print(json.dumps(expanded, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
