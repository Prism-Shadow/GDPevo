#!/usr/bin/env python3
"""Fetch whitelisted Northwind ERP API paths.

This helper intentionally supports only the public paths used by the task
environment. It writes raw JSON responses for later calculation checks.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


COLLECTION_ROOTS = {
    "/products",
    "/inventory",
    "/warehouses",
    "/orders",
    "/customers",
    "/suppliers",
    "/purchase_orders",
    "/boms",
    "/incidents",
}
EXACT_PATHS = {"/manifest", "/shipping/quote"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="ERP API base URL")
    parser.add_argument(
        "--path",
        action="append",
        required=True,
        help="API path to fetch, such as /orders or /orders/ORDER_ID. Query strings are allowed.",
    )
    parser.add_argument("--out-dir", help="Directory for one JSON file per path")
    parser.add_argument("--timeout", type=float, default=20.0)
    return parser.parse_args()


def validate_path(path: str) -> str:
    if not path.startswith("/"):
        raise ValueError(f"path must start with '/': {path}")

    split = urllib.parse.urlsplit(path)
    clean_path = split.path.rstrip("/") or "/"

    if clean_path in EXACT_PATHS:
        return path

    if any(clean_path == root or clean_path.startswith(root + "/") for root in COLLECTION_ROOTS):
        return path

    allowed = sorted(EXACT_PATHS | COLLECTION_ROOTS)
    raise ValueError(f"path is not in allowed ERP endpoints: {path}; allowed roots: {allowed}")


def fetch_json(base_url: str, path: str, timeout: float) -> Any:
    base = base_url.rstrip("/")
    url = base + validate_path(path)
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc.reason}") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Response from {url} was not JSON: {body[:300]}") from exc


def safe_filename(path: str) -> str:
    split = urllib.parse.urlsplit(path)
    raw = split.path.strip("/") or "root"
    if split.query:
        raw += "_" + split.query
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("_") + ".json"


def main() -> int:
    args = parse_args()
    results: dict[str, Any] = {}

    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    for path in args.path:
        data = fetch_json(args.base_url, path, args.timeout)
        results[path] = data
        if out_dir:
            destination = out_dir / safe_filename(path)
            destination.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            print(f"wrote {destination}", file=sys.stderr)

    if not out_dir:
        print(json.dumps(results, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
