#!/usr/bin/env python3
"""Fetch paged Asteria Fleet Data Quality Hub records for a task collection."""

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
    "fuel": {"alias_domain": "fuel", "conversion_kinds": ["volume"], "fx": True},
    "freight": {"alias_domain": "freight", "conversion_kinds": ["weight", "distance"], "fx": True},
    "maintenance": {"alias_domain": None, "conversion_kinds": ["distance"], "fx": False},
    "contacts": {"alias_domain": None, "conversion_kinds": [], "fx": False},
}


def parse_access(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("base_url:"):
            return line.split(":", 1)[1].strip().rstrip("/")
    raise SystemExit(f"base_url not found in {path}")


def get_json(base_url: str, path: str, params: dict[str, object] | None = None) -> dict:
    query = ""
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        query = "?" + urllib.parse.urlencode(clean)
    url = base_url + path + query
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def get_all_pages(base_url: str, path: str, params: dict[str, object] | None = None) -> dict:
    params = dict(params or {})
    offset = int(params.get("offset", 0))
    items = []
    total = None
    limit = None

    while True:
        params["offset"] = offset
        page = get_json(base_url, path, params)
        if "items" not in page:
            return page
        page_items = page.get("items", [])
        items.extend(page_items)
        total = int(page.get("total", len(items)))
        limit = int(page.get("limit", len(page_items) or 100))
        if offset + len(page_items) >= total or not page_items:
            break
        offset += limit

    return {"items": items, "limit": limit, "offset": 0, "total": total}


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def find_collection_family(catalog: dict, collection_id: str) -> str | None:
    for item in catalog.get("items", []):
        if item.get("collection_id") == collection_id:
            return item.get("family")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--access", default="environment_access.md", help="Path to environment_access.md")
    parser.add_argument("--collection", required=True, help="Collection ID from case_scope.json")
    parser.add_argument("--family", choices=sorted(FAMILY_ENDPOINTS), help="Override collection family")
    parser.add_argument("--alias-domain", help="Override alias domain to fetch")
    parser.add_argument("--out", default="asteria_dump", help="Output directory")
    args = parser.parse_args()

    base_url = parse_access(Path(args.access))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, object] = {"base_url": base_url, "collection": args.collection, "files": {}}

    catalog = get_all_pages(base_url, "/api/catalog/collections")
    schema = get_json(base_url, "/api/catalog/schema")
    write_json(out_dir / "catalog.json", catalog)
    write_json(out_dir / "schema.json", schema)
    manifest["files"]["catalog"] = "catalog.json"
    manifest["files"]["schema"] = "schema.json"

    family = args.family or find_collection_family(catalog, args.collection)
    if family not in FAMILY_ENDPOINTS:
        raise SystemExit(f"Unsupported or unknown collection family for {args.collection!r}: {family!r}")
    manifest["family"] = family

    snapshots = get_all_pages(base_url, "/api/source-snapshots", {"collection": args.collection})
    write_json(out_dir / "source_snapshots.json", snapshots)
    manifest["files"]["source_snapshots"] = "source_snapshots.json"

    records = get_all_pages(base_url, FAMILY_ENDPOINTS[family], {"collection": args.collection})
    records_name = f"{family}_records.json"
    write_json(out_dir / records_name, records)
    manifest["files"]["records"] = records_name

    ref_plan = REFERENCE_KINDS.get(family, {})
    alias_domain = args.alias_domain or ref_plan.get("alias_domain")
    if alias_domain:
        aliases = get_all_pages(base_url, "/api/reference/aliases", {"domain": alias_domain})
        alias_name = f"aliases_{alias_domain}.json"
        write_json(out_dir / alias_name, aliases)
        manifest["files"]["aliases"] = alias_name

    conversion_files = []
    for kind in ref_plan.get("conversion_kinds", []):
        conversions = get_all_pages(base_url, "/api/reference/conversions", {"kind": kind})
        conversion_name = f"conversions_{kind}.json"
        write_json(out_dir / conversion_name, conversions)
        conversion_files.append(conversion_name)
    if conversion_files:
        manifest["files"]["conversions"] = conversion_files

    if ref_plan.get("fx"):
        fx = get_all_pages(base_url, "/api/reference/fx")
        write_json(out_dir / "fx_rates.json", fx)
        manifest["files"]["fx"] = "fx_rates.json"

    write_json(out_dir / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
