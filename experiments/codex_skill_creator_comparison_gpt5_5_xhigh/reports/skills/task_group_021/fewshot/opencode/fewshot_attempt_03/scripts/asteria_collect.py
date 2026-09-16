#!/usr/bin/env python3
"""Fetch paginated Asteria Fleet Data Quality Hub records for one task.

This script is a collection/bootstrap helper. It does not solve the audit; it
writes complete raw inputs that a solver can reconcile deterministically.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ENDPOINT_BY_FAMILY = {
    "contacts": "/api/contacts",
    "fuel": "/api/transactions/fuel",
    "freight": "/api/transactions/freight",
    "maintenance": "/api/maintenance/events",
}

CONVERSION_KINDS_BY_FAMILY = {
    "fuel": ["volume"],
    "freight": ["weight", "distance"],
    "maintenance": ["distance"],
}


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/"


def parse_env_file(path: Path | None) -> str | None:
    if not path or not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("base_url:"):
            return line.split(":", 1)[1].strip()
    return None


def find_case_scope(case_dir: Path | None):
    if not case_dir:
        return None
    candidates = [
        case_dir / "payloads" / "case_scope.json",
        case_dir / "case_scope.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return read_json(candidate)
    return None


def request_json(base_url: str, path: str, params: dict | None = None):
    url = urllib.parse.urljoin(base_url, path.lstrip("/"))
    if params:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{url}?{query}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {body}") from exc
    return json.loads(body)


def fetch_pages(base_url: str, path: str, params: dict | None = None, limit: int = 100):
    params = dict(params or {})
    items = []
    offset = 0
    total = None
    while True:
        page_params = dict(params)
        page_params.update({"limit": limit, "offset": offset})
        page = request_json(base_url, path, page_params)
        if "error" in page:
            raise RuntimeError(f"{path} returned error: {page['error']}")
        if "items" not in page:
            return page
        batch = page["items"]
        items.extend(batch)
        total = page.get("total", len(items))
        if not batch or len(items) >= total:
            break
        offset += len(batch)
    return {"items": items, "limit": limit, "offset": 0, "total": total if total is not None else len(items)}


def infer_family(collection_id: str | None, catalog: dict) -> str | None:
    if not collection_id:
        return None
    for item in catalog.get("items", []):
        if item.get("collection_id") == collection_id:
            return item.get("family")
    lowered = collection_id.lower()
    if "fuel" in lowered:
        return "fuel"
    if "freight" in lowered:
        return "freight"
    if "maintenance" in lowered:
        return "maintenance"
    if "contact" in lowered or "roster" in lowered or "onboarding" in lowered:
        return "contacts"
    return None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Hub base URL, for example http://host:port/")
    parser.add_argument("--env-file", type=Path, help="environment_access.md path")
    parser.add_argument("--case-dir", type=Path, help="Task input directory containing payloads/case_scope.json")
    parser.add_argument("--collection", help="Collection id; defaults to case_scope collection_id")
    parser.add_argument("--family", choices=sorted(ENDPOINT_BY_FAMILY), help="Collection family")
    parser.add_argument("--out", type=Path, required=True, help="Output directory for fetched JSON")
    parser.add_argument("--limit", type=int, default=100, help="Page size for GET endpoints")
    args = parser.parse_args(argv)

    base_url = args.base_url or parse_env_file(args.env_file)
    if not base_url:
        parser.error("Provide --base-url or --env-file with a base_url line")
    base_url = normalize_base_url(base_url)

    case_scope = find_case_scope(args.case_dir)
    collection_id = args.collection or (case_scope or {}).get("collection_id")
    if not collection_id:
        parser.error("Provide --collection or --case-dir with payloads/case_scope.json")

    args.out.mkdir(parents=True, exist_ok=True)
    if case_scope is not None:
        write_json(args.out / "case_scope.json", case_scope)

    catalog = fetch_pages(base_url, "/api/catalog/collections", limit=args.limit)
    write_json(args.out / "catalog_collections.json", catalog)
    schema = request_json(base_url, "/api/catalog/schema")
    write_json(args.out / "schema.json", schema)

    family = args.family or infer_family(collection_id, catalog)
    if family not in ENDPOINT_BY_FAMILY:
        parser.error(f"Could not infer supported family for collection {collection_id!r}; pass --family")

    snapshots = fetch_pages(
        base_url,
        "/api/source-snapshots",
        params={"collection": collection_id},
        limit=args.limit,
    )
    write_json(args.out / "source_snapshots.json", snapshots)

    rows = fetch_pages(
        base_url,
        ENDPOINT_BY_FAMILY[family],
        params={"collection": collection_id},
        limit=args.limit,
    )
    write_json(args.out / "rows.json", rows)

    fetched = {
        "base_url": base_url,
        "collection_id": collection_id,
        "family": family,
        "row_total": rows.get("total"),
        "snapshot_total": snapshots.get("total"),
        "files": [
            "catalog_collections.json",
            "schema.json",
            "source_snapshots.json",
            "rows.json",
        ],
    }

    if family in ("fuel", "freight"):
        aliases = fetch_pages(
            base_url,
            "/api/reference/aliases",
            params={"domain": family},
            limit=args.limit,
        )
        alias_file = f"aliases_{family}.json"
        write_json(args.out / alias_file, aliases)
        fetched["files"].append(alias_file)
        fetched["alias_total"] = aliases.get("total")

    for kind in CONVERSION_KINDS_BY_FAMILY.get(family, []):
        conversions = fetch_pages(
            base_url,
            "/api/reference/conversions",
            params={"kind": kind},
            limit=args.limit,
        )
        conversion_file = f"conversions_{kind}.json"
        write_json(args.out / conversion_file, conversions)
        fetched["files"].append(conversion_file)

    if family in ("fuel", "freight", "maintenance"):
        fx = fetch_pages(base_url, "/api/reference/fx", limit=args.limit)
        write_json(args.out / "fx_rates.json", fx)
        fetched["files"].append("fx_rates.json")
        fetched["fx_total"] = fx.get("total")

    write_json(args.out / "manifest.json", fetched)
    print(json.dumps(fetched, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
