#!/usr/bin/env python3
"""Fetch and filter licensing task-environment records.

This helper uses only Python's standard library. It does not make decisions; it
groups records so the solver can apply the skill's rules and the active answer
template.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


ENDPOINTS = {
    "contractor": [
        "/api/policies",
        "/api/contractor/applications",
        "/api/contractor/bonds",
        "/api/contractor/insurance",
        "/api/contractor/license-history",
        "/api/contractor/violations",
        "/api/contractor/correspondence",
        "/api/contractor/inspections",
    ],
    "liquor": [
        "/api/policies",
        "/api/liquor/applications",
        "/api/liquor/settlements",
        "/api/liquor/privileges",
        "/api/liquor/incidents",
        "/api/liquor/site-evidence",
    ],
    "renewal": [
        "/api/policies",
        "/api/alcohol/licensees",
        "/api/alcohol/violations",
        "/api/renewal/rules",
    ],
}


def fetch_json(base_url: str, endpoint: str) -> Any:
    url = base_url.rstrip("/") + endpoint
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GET {endpoint} failed: HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"GET {endpoint} failed: {exc}") from exc


def endpoint_key(endpoint: str) -> str:
    return endpoint.rstrip("/").split("/")[-1].replace("-", "_")


def as_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def parse_json_field(row: dict[str, Any], field: str) -> None:
    raw = row.get(field)
    if isinstance(raw, str):
        try:
            row[field + "_parsed"] = json.loads(raw)
        except json.JSONDecodeError:
            row[field + "_parsed"] = None


def filter_contractor(raw: dict[str, Any], ids: set[str]) -> dict[str, Any]:
    applications = [
        row
        for row in as_list(raw.get("applications"))
        if row.get("application_id") in ids
    ]
    prior_license_ids = {row.get("prior_license_id") for row in applications}
    prior_license_ids.discard(None)

    return {
        "policies": [
            row
            for row in as_list(raw.get("policies"))
            if row.get("family") == "contractor"
        ],
        "applications": applications,
        "bonds": [
            row for row in as_list(raw.get("bonds")) if row.get("application_id") in ids
        ],
        "insurance": [
            row
            for row in as_list(raw.get("insurance"))
            if row.get("application_id") in ids
        ],
        "license_history": [
            row
            for row in as_list(raw.get("license_history"))
            if row.get("license_id") in prior_license_ids
        ],
        "violations": [
            row
            for row in as_list(raw.get("violations"))
            if row.get("related_application_id") in ids
        ],
        "correspondence": [
            row
            for row in as_list(raw.get("correspondence"))
            if row.get("related_application_id") in ids
        ],
        "inspections": [
            row
            for row in as_list(raw.get("inspections"))
            if row.get("related_application_id") in ids
        ],
    }


def filter_liquor(
    raw: dict[str, Any], ids: set[str], explicit_location_ids: set[str]
) -> dict[str, Any]:
    applications = [
        row
        for row in as_list(raw.get("applications"))
        if row.get("application_id") in ids
        or row.get("location_id") in explicit_location_ids
    ]
    location_ids = {row.get("location_id") for row in applications}
    location_ids.update(explicit_location_ids)
    location_ids.discard(None)

    def by_location(key: str) -> list[dict[str, Any]]:
        return [
            row for row in as_list(raw.get(key)) if row.get("location_id") in location_ids
        ]

    return {
        "policies": [
            row for row in as_list(raw.get("policies")) if row.get("family") == "liquor"
        ],
        "applications": applications,
        "settlements": by_location("settlements"),
        "privileges": by_location("privileges"),
        "incidents": by_location("incidents"),
        "site_evidence": by_location("site_evidence"),
    }


def filter_renewal(raw: dict[str, Any], ids: set[str]) -> dict[str, Any]:
    licensees = [
        row for row in as_list(raw.get("licensees")) if row.get("license_no") in ids
    ]
    predecessor_ids = {row.get("successor_to") for row in licensees}
    predecessor_ids.discard(None)
    all_match_ids = ids | predecessor_ids

    return {
        "policies": [
            row for row in as_list(raw.get("policies")) if row.get("family") == "renewal"
        ],
        "rules": as_list(raw.get("rules")),
        "licensees": [
            row
            for row in as_list(raw.get("licensees"))
            if row.get("license_no") in all_match_ids
        ],
        "violations": [
            row
            for row in as_list(raw.get("violations"))
            if row.get("license_no") in all_match_ids
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--domain", choices=sorted(ENDPOINTS), required=True)
    parser.add_argument("--ids", nargs="*", default=[])
    parser.add_argument("--location-ids", nargs="*", default=[])
    args = parser.parse_args()

    ids = set(args.ids)
    raw: dict[str, Any] = {}
    for endpoint in ENDPOINTS[args.domain]:
        key = endpoint_key(endpoint)
        raw[key] = fetch_json(args.base_url, endpoint)

    for row in as_list(raw.get("policies")):
        parse_json_field(row, "details_json")
    for row in as_list(raw.get("settlements")):
        parse_json_field(row, "controls_json")

    if args.domain == "contractor":
        output = filter_contractor(raw, ids)
    elif args.domain == "liquor":
        output = filter_liquor(raw, ids, set(args.location_ids))
    else:
        output = filter_renewal(raw, ids)

    json.dump(output, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
