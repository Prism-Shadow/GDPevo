#!/usr/bin/env python3
"""Fetch licensing task-environment GET endpoints with an optional limit."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def endpoint_to_filename(endpoint: str) -> str:
    cleaned = endpoint.split("?", 1)[0].strip("/")
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", cleaned)
    return f"{cleaned or 'root'}.json"


def build_url(base_url: str, endpoint: str, limit: int | None) -> str:
    if not endpoint.startswith("/api/"):
        raise ValueError(f"endpoint must start with /api/: {endpoint}")

    base = base_url.rstrip("/") + "/"
    parsed = urllib.parse.urlsplit(endpoint)
    query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    if limit is not None and "limit" not in query:
        query["limit"] = str(limit)
    path = parsed.path.lstrip("/")
    rebuilt = urllib.parse.urlunsplit(("", "", path, urllib.parse.urlencode(query), ""))
    return urllib.parse.urljoin(base, rebuilt)


def fetch_json(url: str) -> object:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Task environment base URL")
    parser.add_argument("endpoints", nargs="+", help="Endpoint paths such as /api/policies")
    parser.add_argument("--limit", type=int, default=1000, help="limit query value to add when absent")
    parser.add_argument("--output-dir", help="Directory for endpoint JSON files")
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    combined: dict[str, object] = {}
    for endpoint in args.endpoints:
        try:
            url = build_url(args.base_url, endpoint, args.limit)
            data = fetch_json(url)
        except Exception as exc:
            print(f"fetch failed for {endpoint}: {exc}", file=sys.stderr)
            return 1

        if output_dir:
            (output_dir / endpoint_to_filename(endpoint)).write_text(
                json.dumps(data, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        else:
            combined[endpoint] = data

    if not output_dir:
        print(json.dumps(combined, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
