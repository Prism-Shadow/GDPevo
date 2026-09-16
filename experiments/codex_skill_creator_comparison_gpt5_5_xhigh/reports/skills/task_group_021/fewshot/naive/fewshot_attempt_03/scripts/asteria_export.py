#!/usr/bin/env python3
"""Export Asteria Fleet Data Quality Hub data for local reconciliation."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FAMILY_ENDPOINTS = {
    "contacts": "/api/contacts",
    "fuel": "/api/transactions/fuel",
    "freight": "/api/transactions/freight",
    "maintenance": "/api/maintenance/events",
}

REF_DOMAINS = {
    "fuel": ["fuel"],
    "freight": ["freight"],
    "contacts": [],
    "maintenance": [],
}

CONVERSION_KINDS = {
    "fuel": ["volume"],
    "freight": ["weight", "distance"],
    "maintenance": ["distance"],
    "contacts": [],
}


def get_json(base_url: str, path: str, params: dict[str, object] | None = None) -> dict:
    query = urlencode({k: v for k, v in (params or {}).items() if v is not None})
    url = base_url.rstrip("/") + path + (f"?{query}" if query else "")
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GET {url} failed with HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise SystemExit(f"GET {url} failed: {exc}") from exc


def get_pages(base_url: str, path: str, params: dict[str, object] | None = None) -> dict:
    all_items = []
    offset = 0
    total = None
    while True:
        page_params = dict(params or {})
        page_params["offset"] = offset
        payload = get_json(base_url, path, page_params)
        if "items" not in payload:
            return payload
        items = payload["items"]
        all_items.extend(items)
        total = payload.get("total", len(all_items))
        limit = payload.get("limit") or len(items)
        if not items or len(all_items) >= total:
            break
        offset += int(limit)
    return {"items": all_items, "total": total if total is not None else len(all_items)}


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("TASK_ENV_BASE_URL"))
    parser.add_argument("--collection", required=True)
    parser.add_argument("--family", required=True, choices=sorted(FAMILY_ENDPOINTS))
    parser.add_argument("--out", required=True, help="Output directory for exported JSON files.")
    parser.add_argument("--refs", action="store_true", help="Also export aliases, conversions, and FX data useful for this family.")
    args = parser.parse_args()

    if not args.base_url:
        parser.error("--base-url is required unless TASK_ENV_BASE_URL is set")

    out_dir = Path(args.out)
    write_json(out_dir / "collections.json", get_pages(args.base_url, "/api/catalog/collections"))
    write_json(out_dir / "schema.json", get_json(args.base_url, "/api/catalog/schema"))
    write_json(
        out_dir / "source_snapshots.json",
        get_pages(args.base_url, "/api/source-snapshots", {"collection": args.collection}),
    )
    write_json(
        out_dir / "rows.json",
        get_pages(args.base_url, FAMILY_ENDPOINTS[args.family], {"collection": args.collection}),
    )

    if args.refs:
        for domain in REF_DOMAINS[args.family]:
            write_json(
                out_dir / f"aliases_{domain}.json",
                get_pages(args.base_url, "/api/reference/aliases", {"domain": domain}),
            )
        for kind in CONVERSION_KINDS[args.family]:
            write_json(
                out_dir / f"conversions_{kind}.json",
                get_pages(args.base_url, "/api/reference/conversions", {"kind": kind}),
            )
        if args.family in {"fuel", "freight", "maintenance"}:
            write_json(out_dir / "fx.json", get_pages(args.base_url, "/api/reference/fx"))

    return 0


if __name__ == "__main__":
    sys.exit(main())
