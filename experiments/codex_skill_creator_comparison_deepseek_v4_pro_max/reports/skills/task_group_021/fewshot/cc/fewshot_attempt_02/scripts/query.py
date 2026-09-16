#!/usr/bin/env python3
"""Paginated query helper for the Asteria Fleet Data Quality Hub.

Usage:
    python query.py <base_url> <collection_kind> <collection_id> [snapshot_ids...]

Prints all rows as a JSON array to stdout.

Or import and use programmatically:
    from query import load_all
    rows = load_all("http://task-env:9021", "transactions", "fuel_purchases_2026_01")
"""

import json
import sys
import urllib.request
import urllib.error


def _api_url(base_url: str, path: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}{path}"


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_json(url: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_all(
    base_url: str,
    collection_kind: str,
    collection_id: str,
    snapshot_ids: list[str] | None = None,
    filters: dict | None = None,
    limit: int = 500,
) -> list[dict]:
    """Load all rows from a collection via paginated /api/query.

    Args:
        base_url: The hub base URL (e.g., http://task-env:9021).
        collection_kind: One of 'contacts', 'transactions', 'maintenance'.
        collection_id: Stable collection identifier.
        snapshot_ids: Optional list of snapshot IDs to restrict to.
        filters: Optional server-side filters dict.
        limit: Page size (default 500).

    Returns:
        A list of all row dicts.
    """
    all_rows = []
    offset = 0
    url = _api_url(base_url, "/api/query")

    while True:
        body: dict = {
            "collection_kind": collection_kind,
            "collection_id": collection_id,
            "limit": limit,
            "offset": offset,
        }
        if snapshot_ids:
            body["snapshot_ids"] = snapshot_ids
        if filters:
            body["filters"] = filters

        resp = _post_json(url, body)
        rows = resp.get("rows", [])
        all_rows.extend(rows)

        if len(rows) < limit:
            break
        offset += limit

    return all_rows


def main() -> None:
    if len(sys.argv) < 4:
        print(
            "Usage: python query.py <base_url> <collection_kind> <collection_id> "
            "[snapshot_ids...]",
            file=sys.stderr,
        )
        sys.exit(2)

    base_url = sys.argv[1]
    collection_kind = sys.argv[2]
    collection_id = sys.argv[3]
    snapshot_ids = sys.argv[4:] if len(sys.argv) > 4 else None

    rows = load_all(base_url, collection_kind, collection_id, snapshot_ids)
    json.dump(rows, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
