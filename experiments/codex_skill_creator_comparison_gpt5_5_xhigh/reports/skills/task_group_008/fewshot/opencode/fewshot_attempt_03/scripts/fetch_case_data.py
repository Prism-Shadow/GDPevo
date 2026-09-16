#!/usr/bin/env python3
"""Fetch a filtered advisory case data bundle from the task API.

The script uses only the advisory endpoints exposed by the task harness. It does
not calculate an answer; it collects the facts needed for the skill workflow.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import urlopen


def fetch_json(base_url: str, path: str) -> Any:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    try:
        with urlopen(url, timeout=20) as response:
            return json.load(response)
    except HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code} while fetching {url}") from exc
    except URLError as exc:
        raise SystemExit(f"Network error while fetching {url}: {exc.reason}") from exc


def by_client(rows: Any, client_id: str) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    return [
        row
        for row in rows
        if isinstance(row, dict) and row.get("client_id") == client_id
    ]


def build_bundle(base_url: str, client_id: str) -> dict[str, Any]:
    return {
        "client_id": client_id,
        "client": fetch_json(base_url, f"/api/clients/{client_id}"),
        "source_documents": by_client(
            fetch_json(base_url, "/api/source-documents"), client_id
        ),
        "retirement_accounts": by_client(
            fetch_json(base_url, "/api/retirement-accounts"), client_id
        ),
        "life_insurance": by_client(
            fetch_json(base_url, "/api/life-insurance"), client_id
        ),
        "trust_candidates": by_client(
            fetch_json(base_url, "/api/trust-candidates"), client_id
        ),
        "tax_policy": fetch_json(base_url, "/api/policies/tax"),
        "rmd_factors": fetch_json(base_url, "/api/rmd-factors"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch filtered advisory API data for one client."
    )
    parser.add_argument("client_id", help="Stable client identifier, such as CLT-####")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("API_BASE"),
        help="Advisory API base URL. Defaults to API_BASE.",
    )
    parser.add_argument("--out", help="Optional output JSON path.")
    args = parser.parse_args()

    if not args.base_url:
        raise SystemExit("Set API_BASE or pass --base-url.")

    bundle = build_bundle(args.base_url, args.client_id)
    text = json.dumps(bundle, indent=2, sort_keys=True) + "\n"

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
