#!/usr/bin/env python3
"""Collect MedBridge API context for prompt-linked records.

This helper is intentionally generic: it extracts likely MedBridge record IDs
from a prompt and runs exact API searches/fetches without embedding any task
data. It prints JSON for the solver to inspect before filling the answer
template.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path


ID_PATTERN = re.compile(
    r"\b(?:Q|RFQ|OPP|CUST|FR|INV|PAY|RJ|EVT|POL)-[A-Z0-9][A-Z0-9-]*\b"
    r"|\b[A-Z]{2,12}(?:-[A-Z0-9]{1,16})+\b"
    r"|\b(?=[A-Z0-9]*[A-Z])(?=[A-Z0-9]*\d)[A-Z0-9]{6,}\b"
)

COLLECTION_BY_PREFIX = {
    "Q-": "quotes",
    "RFQ-": "rfqs",
    "OPP-": "opportunities",
    "CUST-": "customers",
    "FR-": "freight-quotes",
    "INV-": "invoices",
    "PAY-": "payments",
    "RJ-": "revenue-journals",
    "EVT-": "events",
    "POL-": "policies",
}


def get_json(base_url: str, path: str) -> object:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def candidate_collections(record_id: str) -> list[str]:
    for prefix, collection in COLLECTION_BY_PREFIX.items():
        if record_id.startswith(prefix):
            return [collection]
    if "-" in record_id:
        return ["products", "vouchers"]
    return ["vouchers", "products"]


def extract_ids(text: str) -> list[str]:
    seen: set[str] = set()
    ids: list[str] = []
    for match in ID_PATTERN.finditer(text.upper()):
        value = match.group(0)
        if value not in seen:
            seen.add(value)
            ids.append(value)
    return ids


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--prompt", type=Path)
    parser.add_argument("--id", action="append", default=[])
    args = parser.parse_args()

    text = args.prompt.read_text(encoding="utf-8") if args.prompt else ""
    ids = extract_ids(text)
    for record_id in args.id:
        upper_id = record_id.upper()
        if upper_id not in ids:
            ids.append(upper_id)

    output: dict[str, object] = {"api": None, "direct_records": {}, "searches": {}}
    output["api"] = get_json(args.base_url, "/api")

    for record_id in ids:
        output["direct_records"][record_id] = {}
        for collection in candidate_collections(record_id):
            try:
                output["direct_records"][record_id][collection] = get_json(
                    args.base_url, f"/api/{collection}/{record_id}"
                )
            except Exception as exc:  # noqa: BLE001
                output["direct_records"][record_id][collection] = {"error": str(exc)}
        try:
            query = urllib.parse.quote(record_id)
            output["searches"][record_id] = get_json(args.base_url, f"/api/search?q={query}")
        except Exception as exc:  # noqa: BLE001
            output["searches"][record_id] = {"error": str(exc)}

    json.dump(output, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
