#!/usr/bin/env python3
"""Fetch linked MedBridge Sales Ops records with stdlib-only HTTP."""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen


COLLECTIONS = {
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


def normalize_base(base_url):
    return base_url.rstrip("/") + "/"


def fetch_json(base_url, path):
    url = urljoin(normalize_base(base_url), path.lstrip("/"))
    req = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=20) as response:
            return json.load(response)
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"error": exc.reason}
        return {"_http_error": exc.code, "_url": url, "payload": payload}
    except URLError as exc:
        raise SystemExit(f"request failed for {url}: {exc}") from exc


def records(payload):
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return payload["records"]
    if isinstance(payload, list):
        return payload
    return []


def list_collection(base_url, collection):
    if collection not in COLLECTIONS:
        raise SystemExit(f"unknown collection: {collection}")
    return fetch_json(base_url, f"/api/{collection}")


def get_record(base_url, collection, record_id, id_key="id"):
    direct = fetch_json(base_url, f"/api/{collection}/{quote(record_id)}")
    if not (isinstance(direct, dict) and direct.get("_http_error")) and not direct.get("error"):
        return direct
    for record in records(list_collection(base_url, collection)):
        if str(record.get(id_key) or record.get("code") or record.get("id")) == record_id:
            return record
    return direct


def related_quote_bundle(base_url, quote_id):
    quote_record = get_record(base_url, "quotes", quote_id)
    product_codes = set()
    if isinstance(quote_record, dict):
        if quote_record.get("primary_product_code"):
            product_codes.add(quote_record["primary_product_code"])
        for line in quote_record.get("line_items", []):
            if line.get("product_code"):
                product_codes.add(line["product_code"])
    return {
        "quote": quote_record,
        "customer": get_record(base_url, "customers", quote_record.get("customer_id", ""))
        if isinstance(quote_record, dict) and quote_record.get("customer_id")
        else None,
        "products": [get_record(base_url, "products", code, id_key="code") for code in sorted(product_codes)],
        "freight_quotes": [
            row
            for row in records(list_collection(base_url, "freight-quotes"))
            if row.get("quote_id") == quote_id
        ],
        "policies": records(list_collection(base_url, "policies")),
    }


def related_rfq_bundle(base_url, rfq_id):
    rfq_record = get_record(base_url, "rfqs", rfq_id)
    product_codes = []
    if isinstance(rfq_record, dict):
        product_codes = sorted({row.get("product_code") for row in rfq_record.get("requested_modules", []) if row.get("product_code")})
    return {
        "rfq": rfq_record,
        "customer": get_record(base_url, "customers", rfq_record.get("customer_id", ""))
        if isinstance(rfq_record, dict) and rfq_record.get("customer_id")
        else None,
        "products": [get_record(base_url, "products", code, id_key="code") for code in product_codes],
        "policies": records(list_collection(base_url, "policies")),
    }


def related_opportunity_bundle(base_url, opportunity_id):
    opportunity = get_record(base_url, "opportunities", opportunity_id)
    invoices = [row for row in records(list_collection(base_url, "invoices")) if row.get("opportunity_id") == opportunity_id]
    payments = [row for row in records(list_collection(base_url, "payments")) if row.get("opportunity_id") == opportunity_id]
    journals = [row for row in records(list_collection(base_url, "revenue-journals")) if row.get("opportunity_id") == opportunity_id]
    events = [row for row in records(list_collection(base_url, "events")) if row.get("opportunity_id") == opportunity_id]
    vouchers = [row for row in records(list_collection(base_url, "vouchers")) if row.get("opportunity_id") == opportunity_id]
    return {
        "opportunity": opportunity,
        "customer": get_record(base_url, "customers", opportunity.get("customer_id", ""))
        if isinstance(opportunity, dict) and opportunity.get("customer_id")
        else None,
        "invoices": invoices,
        "payments": payments,
        "revenue_journals": journals,
        "events": events,
        "vouchers": vouchers,
        "policies": records(list_collection(base_url, "policies")),
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch MedBridge Sales Ops API records.")
    parser.add_argument("base_url", help="Task environment base URL")
    parser.add_argument("--path", help="Raw API path to fetch, such as /api/products")
    parser.add_argument("--search", help="Search text for /api/search")
    parser.add_argument("--collection", choices=sorted(COLLECTIONS), help="Collection to list")
    parser.add_argument("--quote-id", help="Fetch quote, customer, products, freight, and policies")
    parser.add_argument("--rfq-id", help="Fetch RFQ, customer, products, and policies")
    parser.add_argument("--opportunity-id", help="Fetch opportunity reconciliation records")
    args = parser.parse_args()

    selected = [
        bool(args.path),
        bool(args.search),
        bool(args.collection),
        bool(args.quote_id),
        bool(args.rfq_id),
        bool(args.opportunity_id),
    ]
    if sum(selected) != 1:
        parser.error("choose exactly one of --path, --search, --collection, --quote-id, --rfq-id, or --opportunity-id")

    if args.path:
        payload = fetch_json(args.base_url, args.path)
    elif args.search:
        payload = fetch_json(args.base_url, f"/api/search?q={quote(args.search)}")
    elif args.collection:
        payload = list_collection(args.base_url, args.collection)
    elif args.quote_id:
        payload = related_quote_bundle(args.base_url, args.quote_id)
    elif args.rfq_id:
        payload = related_rfq_bundle(args.base_url, args.rfq_id)
    else:
        payload = related_opportunity_bundle(args.base_url, args.opportunity_id)

    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
