#!/usr/bin/env python3
"""Fetch a paged Asteria Fleet Data Quality Hub bundle for one collection."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


FAMILY_ENDPOINT = {
    "contacts": "/api/contacts",
    "fuel": "/api/transactions/fuel",
    "freight": "/api/transactions/freight",
    "maintenance": "/api/maintenance/events",
}

ALIAS_DOMAIN = {
    "fuel": "fuel",
    "freight": "freight",
}

CONVERSION_KINDS = {
    "fuel": ["volume"],
    "freight": ["weight", "distance"],
    "maintenance": ["distance"],
}


def get_json(base_url: str, path: str, params: dict[str, Any] | None = None) -> Any:
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params)
    url = base_url.rstrip("/") + path + query
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GET {url} failed with HTTP {exc.code}: {body}") from exc


def fetch_paged(
    base_url: str,
    path: str,
    params: dict[str, Any] | None = None,
    page_size: int = 500,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    offset = 0
    total = None
    while True:
        page_params = dict(params or {})
        page_params["limit"] = page_size
        page_params["offset"] = offset
        data = get_json(base_url, path, page_params)
        if "items" not in data:
            raise SystemExit(f"Expected paged response with items from {path}: {data}")
        page_items = data["items"]
        items.extend(page_items)
        total = data.get("total", len(items))
        limit = data.get("limit", page_size)
        if not page_items or offset + limit >= total:
            break
        offset += limit
    return items


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--family", required=True, choices=sorted(FAMILY_ENDPOINT))
    parser.add_argument("--collection", required=True)
    parser.add_argument("--out", default="-")
    parser.add_argument("--page-size", type=int, default=500)
    args = parser.parse_args()

    rows = fetch_paged(
        args.base_url,
        FAMILY_ENDPOINT[args.family],
        {"collection": args.collection},
        args.page_size,
    )

    references: dict[str, Any] = {}
    domain = ALIAS_DOMAIN.get(args.family)
    if domain:
        references["aliases"] = fetch_paged(
            args.base_url,
            "/api/reference/aliases",
            {"domain": domain},
            args.page_size,
        )

    for kind in CONVERSION_KINDS.get(args.family, []):
        references.setdefault("conversions", {})[kind] = fetch_paged(
            args.base_url,
            "/api/reference/conversions",
            {"kind": kind},
            args.page_size,
        )

    if args.family in {"fuel", "freight"}:
        currencies = sorted(
            {
                row.get("currency")
                for row in rows
                if row.get("currency") and row.get("currency") != "USD"
            }
        )
        references["fx"] = {
            currency: fetch_paged(
                args.base_url,
                "/api/reference/fx",
                {"currency": currency},
                args.page_size,
            )
            for currency in currencies
        }

    bundle = {
        "collection_id": args.collection,
        "family": args.family,
        "catalog": get_json(args.base_url, "/api/catalog/collections"),
        "schema": get_json(args.base_url, "/api/catalog/schema"),
        "source_snapshots": fetch_paged(
            args.base_url,
            "/api/source-snapshots",
            {"collection": args.collection},
            args.page_size,
        ),
        "rows": rows,
        "references": references,
    }

    if args.out == "-":
        json.dump(bundle, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(bundle, f, ensure_ascii=False, indent=2)
            f.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
