#!/usr/bin/env python3
"""Fetch paged Asteria Fleet Data Quality Hub data into JSON files."""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


FAMILY_ENDPOINTS = {
    "contacts": "/api/contacts",
    "fuel": "/api/transactions/fuel",
    "freight": "/api/transactions/freight",
    "maintenance": "/api/maintenance/events",
}


def load_access(path):
    access = {}
    for raw_line in Path(path).read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("-") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        access[key.strip()] = value.strip()
    base_url = access.get("base_url")
    if not base_url:
        raise SystemExit(f"base_url not found in {path}")
    credentials = access.get("credentials")
    if credentials and credentials.lower() == "none":
        credentials = None
    return base_url.rstrip("/"), credentials


def request_json(base_url, path, params=None, credentials=None):
    query = ""
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        query = "?" + urllib.parse.urlencode(clean)
    url = base_url + path + query
    headers = {"Accept": "application/json"}
    if credentials:
        headers["Authorization"] = f"Bearer {credentials}"
        headers["X-API-Key"] = credentials
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} for {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Request failed for {url}: {exc}") from exc


def get_paged(base_url, path, params=None, credentials=None):
    params = dict(params or {})
    offset = int(params.pop("offset", 0) or 0)
    items = []
    metadata = {}
    while True:
        page_params = dict(params)
        page_params["offset"] = offset
        data = request_json(base_url, path, page_params, credentials)
        if "items" not in data:
            return data
        page_items = data.get("items") or []
        items.extend(page_items)
        metadata = {k: v for k, v in data.items() if k != "items"}
        total = data.get("total")
        if total is not None and len(items) >= int(total):
            break
        if not page_items:
            break
        offset += len(page_items)
    metadata["items"] = items
    metadata["fetched_count"] = len(items)
    return metadata


def write_json(out_dir, name, data):
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print(path)


def collection_families(collections):
    result = {}
    for item in collections.get("items", []):
        collection_id = item.get("collection_id")
        family = item.get("family")
        if collection_id and family:
            result[collection_id] = family
    return result


def add_reference_plan(collection_id, family, alias_domains, conversion_kinds, needs_fx):
    if family == "fuel":
        alias_domains.add("fuel")
        conversion_kinds.add("volume")
        needs_fx[0] = True
    elif family == "freight":
        alias_domains.add("freight")
        conversion_kinds.update(["weight", "distance"])
        needs_fx[0] = True
    elif family == "maintenance":
        conversion_kinds.add("distance")
        needs_fx[0] = True
    elif family == "contacts":
        return
    else:
        print(f"warning: unknown family for {collection_id}: {family}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default="environment_access.md", help="Path to environment_access.md")
    parser.add_argument("--out", default="asteria_dump", help="Output directory for JSON files")
    parser.add_argument("--collection", action="append", default=[], help="Collection ID to fetch")
    parser.add_argument("--domain", action="append", default=[], help="Alias domain to fetch, e.g. fuel or freight")
    parser.add_argument("--kind", action="append", default=[], help="Conversion kind to fetch")
    args = parser.parse_args()

    base_url, credentials = load_access(args.env)
    out_dir = Path(args.out)

    collections = get_paged(base_url, "/api/catalog/collections", credentials=credentials)
    schema = request_json(base_url, "/api/catalog/schema", credentials=credentials)
    write_json(out_dir, "catalog_collections.json", collections)
    write_json(out_dir, "catalog_schema.json", schema)

    families = collection_families(collections)
    alias_domains = set(args.domain)
    conversion_kinds = set(args.kind)
    needs_fx = [False]

    for collection_id in args.collection:
        family = families.get(collection_id)
        add_reference_plan(collection_id, family, alias_domains, conversion_kinds, needs_fx)

        snapshots = get_paged(
            base_url,
            "/api/source-snapshots",
            {"collection": collection_id},
            credentials,
        )
        write_json(out_dir, f"{collection_id}__source_snapshots.json", snapshots)

        endpoint = FAMILY_ENDPOINTS.get(family)
        if endpoint:
            records = get_paged(base_url, endpoint, {"collection": collection_id}, credentials)
            write_json(out_dir, f"{collection_id}__records.json", records)
        else:
            print(f"warning: no endpoint mapped for collection {collection_id}", file=sys.stderr)

    for domain in sorted(alias_domains):
        aliases = get_paged(base_url, "/api/reference/aliases", {"domain": domain}, credentials)
        write_json(out_dir, f"reference_aliases__{domain}.json", aliases)

    for kind in sorted(conversion_kinds):
        conversions = get_paged(base_url, "/api/reference/conversions", {"kind": kind}, credentials)
        write_json(out_dir, f"reference_conversions__{kind}.json", conversions)

    if needs_fx[0]:
        fx = get_paged(base_url, "/api/reference/fx", credentials=credentials)
        write_json(out_dir, "reference_fx.json", fx)


if __name__ == "__main__":
    main()
