#!/usr/bin/env python3
"""Fetch complete Asteria Data Quality Hub data for one collection."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path


FAMILY_ENDPOINTS = {
    "contacts": "/api/contacts",
    "fuel": "/api/transactions/fuel",
    "freight": "/api/transactions/freight",
    "maintenance": "/api/maintenance/events",
}


REFERENCE_KINDS = {
    "contacts": {"domains": [], "conversions": []},
    "fuel": {"domains": ["fuel"], "conversions": ["volume"]},
    "freight": {"domains": ["freight"], "conversions": ["weight", "distance"]},
    "maintenance": {"domains": [], "conversions": ["distance"]},
}


def parse_env(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("base_url:"):
            return line.split(":", 1)[1].strip()
    raise SystemExit(f"base_url not found in {path}")


def parse_header(value: str) -> tuple[str, str]:
    if ":" not in value:
        raise argparse.ArgumentTypeError("headers must be in 'Name: value' form")
    name, header_value = value.split(":", 1)
    return name.strip(), header_value.strip()


def request_json(base_url: str, path: str, params: dict[str, object], headers: dict[str, str]):
    query = urllib.parse.urlencode(params)
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    if query:
        url = f"{url}?{query}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GET {url} failed: HTTP {exc.code}: {detail}") from exc
    return json.loads(body)


def fetch_all(
    base_url: str,
    path: str,
    params: dict[str, object],
    headers: dict[str, str],
    page_size: int,
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    offset = 0
    total = None
    while total is None or offset < total:
        payload = dict(params)
        payload.update({"limit": page_size, "offset": offset})
        data = request_json(base_url, path, payload, headers)
        if "items" not in data:
            raise SystemExit(f"{path} did not return an items array: {data}")
        page = data["items"]
        items.extend(page)
        total = int(data.get("total", len(items)))
        limit = int(data.get("limit", page_size))
        if not page:
            break
        offset += limit
    return items


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True, type=Path, help="Path to environment_access.md")
    parser.add_argument("--collection", required=True, help="Collection ID from case_scope.json")
    parser.add_argument("--out", required=True, type=Path, help="Output directory for fetched JSON")
    parser.add_argument("--base-url", help="Override base URL from environment_access.md")
    parser.add_argument("--family", choices=sorted(FAMILY_ENDPOINTS), help="Override catalog family")
    parser.add_argument("--page-size", type=int, default=500)
    parser.add_argument("--header", action="append", type=parse_header, default=[])
    args = parser.parse_args()

    base_url = args.base_url or parse_env(args.env)
    headers = {name: value for name, value in args.header}
    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    collections = fetch_all(base_url, "/api/catalog/collections", {}, headers, args.page_size)
    schema = request_json(base_url, "/api/catalog/schema", {}, headers)
    write_json(out_dir / "catalog_collections.json", collections)
    write_json(out_dir / "catalog_schema.json", schema)

    matches = [row for row in collections if row.get("collection_id") == args.collection]
    if not matches and not args.family:
        raise SystemExit(f"collection not found in catalog: {args.collection}")
    family = args.family or str(matches[0].get("family"))
    if family not in FAMILY_ENDPOINTS:
        raise SystemExit(f"unsupported collection family: {family}")

    records = fetch_all(
        base_url,
        FAMILY_ENDPOINTS[family],
        {"collection": args.collection},
        headers,
        args.page_size,
    )
    snapshots = fetch_all(
        base_url,
        "/api/source-snapshots",
        {"collection": args.collection},
        headers,
        args.page_size,
    )
    write_json(out_dir / "records.json", records)
    write_json(out_dir / "source_snapshots.json", snapshots)

    refs = REFERENCE_KINDS[family]
    for domain in refs["domains"]:
        aliases = fetch_all(
            base_url,
            "/api/reference/aliases",
            {"domain": domain},
            headers,
            args.page_size,
        )
        write_json(out_dir / f"reference_aliases_{domain}.json", aliases)

    for kind in refs["conversions"]:
        conversions = fetch_all(
            base_url,
            "/api/reference/conversions",
            {"kind": kind},
            headers,
            args.page_size,
        )
        write_json(out_dir / f"conversions_{kind}.json", conversions)

    currencies = sorted(
        {
            str(row.get("currency"))
            for row in records
            if row.get("currency") and str(row.get("currency")).upper() != "USD"
        }
    )
    for currency in currencies:
        rates = fetch_all(
            base_url,
            "/api/reference/fx",
            {"currency": currency},
            headers,
            args.page_size,
        )
        write_json(out_dir / f"fx_{currency}.json", rates)

    print(json.dumps({
        "collection": args.collection,
        "family": family,
        "record_count": len(records),
        "snapshot_count": len(snapshots),
        "out": str(out_dir),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
