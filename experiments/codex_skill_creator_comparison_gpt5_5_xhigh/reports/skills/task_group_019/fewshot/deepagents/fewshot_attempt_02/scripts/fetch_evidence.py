#!/usr/bin/env python3
"""Fetch and group licensing task-environment evidence.

This helper intentionally does not decide outcomes. It retrieves the allowed
family endpoints with an explicit limit, filters to prompt targets, parses JSON
string fields, and writes a compact evidence bundle for manual reasoning.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from typing import Any
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


ENDPOINTS = {
    "contractor": [
        "api/policies",
        "api/contractor/applications",
        "api/contractor/bonds",
        "api/contractor/insurance",
        "api/contractor/license-history",
        "api/contractor/violations",
        "api/contractor/correspondence",
        "api/contractor/inspections",
    ],
    "liquor": [
        "api/policies",
        "api/liquor/applications",
        "api/liquor/settlements",
        "api/liquor/privileges",
        "api/liquor/incidents",
        "api/liquor/site-evidence",
    ],
    "renewal": [
        "api/policies",
        "api/renewal/rules",
        "api/alcohol/licensees",
        "api/alcohol/violations",
    ],
}

ALWAYS_KEEP = {
    "api/policies",
    "api/renewal/rules",
    "api/liquor/privileges",
}


def split_csv(value: str | None) -> set[str]:
    if not value:
        return set()
    return {part.strip() for part in value.split(",") if part.strip()}


def fetch_json(base_url: str, endpoint: str, limit: int) -> Any:
    params = urlencode({"limit": limit})
    url = urljoin(base_url.rstrip("/") + "/", endpoint) + "?" + params
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_embedded_json(row: dict[str, Any]) -> dict[str, Any]:
    parsed = dict(row)
    for key, value in row.items():
        if key.endswith("_json") and isinstance(value, str):
            try:
                parsed[key[:-5] + "_parsed"] = json.loads(value)
            except json.JSONDecodeError:
                parsed[key[:-5] + "_parsed"] = None
    return parsed


def value_matches(value: Any, exact: set[str], prefixes: set[str]) -> bool:
    if value is None:
        return False
    text = str(value)
    return text in exact or any(text.startswith(prefix) for prefix in prefixes)


def endpoint_name(endpoint: str) -> str:
    return endpoint.replace("api/", "").replace("/", "_").replace("-", "_")


def is_primary_endpoint(family: str, endpoint: str) -> bool:
    if family == "contractor":
        return endpoint == "api/contractor/applications"
    if family == "liquor":
        return endpoint == "api/liquor/applications"
    if family == "renewal":
        return endpoint == "api/alcohol/licensees"
    return False


def primary_relevant(
    family: str,
    row: dict[str, Any],
    exact: set[str],
    prefixes: set[str],
    locations: set[str],
) -> bool:
    if not row_relevant(row, exact, prefixes, locations, {
        "applications": set(),
        "locations": locations,
        "license_ids": set(),
        "license_nos": exact,
        "applicant_names": set(),
        "addresses": set(),
    }):
        return False
    if family == "renewal" and row.get("active") in (0, False) and row.get("license_no") not in exact:
        return False
    return True


def collect_relationships(family: str, grouped: dict[str, list[dict[str, Any]]]) -> dict[str, set[str]]:
    related = {
        "applications": set(),
        "locations": set(),
        "license_ids": set(),
        "license_nos": set(),
        "applicant_names": set(),
        "addresses": set(),
    }
    if family == "contractor":
        for row in grouped.get("contractor_applications", []):
            if row.get("application_id"):
                related["applications"].add(str(row["application_id"]))
            if row.get("prior_license_id"):
                related["license_ids"].add(str(row["prior_license_id"]))
            if row.get("applicant_name"):
                related["applicant_names"].add(str(row["applicant_name"]))
    elif family == "liquor":
        for row in grouped.get("liquor_applications", []):
            if row.get("application_id"):
                related["applications"].add(str(row["application_id"]))
            if row.get("location_id"):
                related["locations"].add(str(row["location_id"]))
    elif family == "renewal":
        for row in grouped.get("alcohol_licensees", []):
            if row.get("license_no"):
                related["license_nos"].add(str(row["license_no"]))
            if row.get("successor_to"):
                related["license_nos"].add(str(row["successor_to"]))
            if row.get("address"):
                related["addresses"].add(str(row["address"]))
    return related


def row_relevant(
    row: dict[str, Any],
    exact: set[str],
    prefixes: set[str],
    locations: set[str],
    related: dict[str, set[str]],
) -> bool:
    target_fields = (
        "application_id",
        "related_application_id",
        "license_no",
        "license_id",
        "prior_license_id",
        "correspondence_id",
    )
    for field in target_fields:
        if value_matches(row.get(field), exact, prefixes):
            return True

    if row.get("location_id") in locations or row.get("location_id") in related["locations"]:
        return True
    if row.get("related_application_id") in related["applications"]:
        return True
    if row.get("application_id") in related["applications"]:
        return True
    if row.get("license_id") in related["license_ids"]:
        return True
    if row.get("license_no") in related["license_nos"]:
        return True
    if row.get("address") in related["addresses"] and row.get("license_no") in related["license_nos"]:
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--family", required=True, choices=sorted(ENDPOINTS))
    parser.add_argument("--targets", help="Comma-separated application IDs or license numbers.")
    parser.add_argument("--prefixes", help="Comma-separated target ID prefixes for ranges.")
    parser.add_argument("--locations", help="Comma-separated location IDs.")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--output", help="Write JSON evidence to this path instead of stdout.")
    parser.add_argument("--all", action="store_true", help="Keep all fetched rows. Use only for small, trusted task datasets.")
    args = parser.parse_args()

    exact = split_csv(args.targets)
    prefixes = split_csv(args.prefixes)
    locations = split_csv(args.locations)
    if not (exact or prefixes or locations or args.all):
        parser.error("provide --targets, --prefixes, --locations, or --all")

    raw_grouped: dict[str, list[dict[str, Any]]] = OrderedDict()
    for endpoint in ENDPOINTS[args.family]:
        data = fetch_json(args.base_url, endpoint, args.limit)
        if not isinstance(data, list):
            data = [data]
        rows = [parse_embedded_json(row) for row in data if isinstance(row, dict)]
        name = endpoint_name(endpoint)
        if endpoint in ALWAYS_KEEP or args.all:
            raw_grouped[name] = rows
        elif is_primary_endpoint(args.family, endpoint):
            raw_grouped[name] = [
                row
                for row in rows
                if primary_relevant(args.family, row, exact, prefixes, locations)
            ]
        else:
            raw_grouped[name] = rows

    related = collect_relationships(args.family, raw_grouped)
    grouped: dict[str, list[dict[str, Any]]] = OrderedDict()
    for endpoint in ENDPOINTS[args.family]:
        name = endpoint_name(endpoint)
        rows = raw_grouped[name]
        if endpoint in ALWAYS_KEEP or args.all or is_primary_endpoint(args.family, endpoint):
            grouped[name] = rows
        else:
            grouped[name] = [
                row for row in rows if row_relevant(row, exact, prefixes, locations, related)
            ]

    result = OrderedDict()
    result["_meta"] = {
        "family": args.family,
        "limit": args.limit,
        "targets": sorted(exact),
        "prefixes": sorted(prefixes),
        "locations": sorted(locations),
        "record_counts": {key: len(value) for key, value in grouped.items()},
    }
    result.update(grouped)

    output = json.dumps(result, indent=2, sort_keys=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(output + "\n")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
