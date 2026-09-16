#!/usr/bin/env python3
"""Collect filtered licensing-environment records for review tasks."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date


ENDPOINTS = {
    "policies": "/api/policies",
    "contractor_applications": "/api/contractor/applications",
    "contractor_bonds": "/api/contractor/bonds",
    "contractor_insurance": "/api/contractor/insurance",
    "contractor_license_history": "/api/contractor/license-history",
    "contractor_violations": "/api/contractor/violations",
    "contractor_correspondence": "/api/contractor/correspondence",
    "contractor_inspections": "/api/contractor/inspections",
    "liquor_applications": "/api/liquor/applications",
    "liquor_settlements": "/api/liquor/settlements",
    "liquor_privileges": "/api/liquor/privileges",
    "liquor_incidents": "/api/liquor/incidents",
    "liquor_site_evidence": "/api/liquor/site-evidence",
    "alcohol_licensees": "/api/alcohol/licensees",
    "alcohol_violations": "/api/alcohol/violations",
    "renewal_rules": "/api/renewal/rules",
}


def get_json(base_url: str, path: str):
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"GET {path} failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"GET {path} failed: {exc.reason}") from exc


def by_key(rows, key, values):
    wanted = set(values)
    return [row for row in rows if row.get(key) in wanted]


def parse_date(value: str | None):
    if not value:
        return None
    return date.fromisoformat(value)


def collect_contractor(base_url: str, ids: list[str]):
    data = {name: get_json(base_url, path) for name, path in ENDPOINTS.items() if name.startswith("contractor_")}
    policies = get_json(base_url, ENDPOINTS["policies"])
    apps = by_key(data["contractor_applications"], "application_id", ids)
    prior_license_ids = {row.get("prior_license_id") for row in apps if row.get("prior_license_id")}

    return {
        "policies": [row for row in policies if row.get("family") == "contractor"],
        "applications": apps,
        "bonds": by_key(data["contractor_bonds"], "application_id", ids),
        "insurance": by_key(data["contractor_insurance"], "application_id", ids),
        "license_history": [
            row for row in data["contractor_license_history"] if row.get("license_id") in prior_license_ids
        ],
        "violations": [
            row
            for row in data["contractor_violations"]
            if row.get("related_application_id") in ids or row.get("license_id") in prior_license_ids
        ],
        "correspondence": by_key(data["contractor_correspondence"], "related_application_id", ids),
        "inspections": by_key(data["contractor_inspections"], "related_application_id", ids),
    }


def collect_liquor(base_url: str, ids: list[str], locations: list[str]):
    apps = get_json(base_url, ENDPOINTS["liquor_applications"])
    selected_apps = [
        row
        for row in apps
        if row.get("application_id") in set(ids) or row.get("location_id") in set(locations)
    ]
    selected_locations = set(locations) | {row.get("location_id") for row in selected_apps if row.get("location_id")}
    license_classes = {row.get("license_class") for row in selected_apps if row.get("license_class")}
    policies = get_json(base_url, ENDPOINTS["policies"])

    return {
        "policies": [row for row in policies if row.get("family") == "liquor"],
        "applications": selected_apps,
        "settlements": [
            row for row in get_json(base_url, ENDPOINTS["liquor_settlements"]) if row.get("location_id") in selected_locations
        ],
        "privileges": [
            row for row in get_json(base_url, ENDPOINTS["liquor_privileges"]) if row.get("license_class") in license_classes
        ],
        "incidents": [
            row for row in get_json(base_url, ENDPOINTS["liquor_incidents"]) if row.get("location_id") in selected_locations
        ],
        "site_evidence": [
            row for row in get_json(base_url, ENDPOINTS["liquor_site_evidence"]) if row.get("location_id") in selected_locations
        ],
    }


def collect_renewal(base_url: str, ids: list[str], boundary: str | None):
    licensees = by_key(get_json(base_url, ENDPOINTS["alcohol_licensees"]), "license_no", ids)
    exact_ids = {row["license_no"] for row in licensees}
    predecessor_ids = {row.get("successor_to") for row in licensees if row.get("successor_to")}
    match_ids = exact_ids | predecessor_ids
    boundary_date = parse_date(boundary)

    matched = []
    post_boundary = []
    for row in get_json(base_url, ENDPOINTS["alcohol_violations"]):
        is_match = row.get("license_no") in match_ids
        if not is_match:
            continue
        row_date = parse_date(row.get("violation_date"))
        if boundary_date and row_date and row_date > boundary_date:
            post_boundary.append(row)
        else:
            matched.append(row)

    return {
        "rules": get_json(base_url, ENDPOINTS["renewal_rules"]),
        "licensees": licensees,
        "matched_violations": matched,
        "post_boundary_violations": post_boundary,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--family", required=True, choices=["contractor", "liquor", "renewal"])
    parser.add_argument("--ids", nargs="+", default=[])
    parser.add_argument("--locations", nargs="*", default=[])
    parser.add_argument("--boundary")
    args = parser.parse_args()

    if args.family in {"contractor", "renewal"} and not args.ids:
        parser.error("--ids is required for contractor and renewal tasks")
    if args.family == "liquor" and not args.ids and not args.locations:
        parser.error("--ids or --locations is required for liquor tasks")

    if args.family == "contractor":
        result = collect_contractor(args.base_url, args.ids)
    elif args.family == "liquor":
        result = collect_liquor(args.base_url, args.ids, args.locations)
    else:
        result = collect_renewal(args.base_url, args.ids, args.boundary)

    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
