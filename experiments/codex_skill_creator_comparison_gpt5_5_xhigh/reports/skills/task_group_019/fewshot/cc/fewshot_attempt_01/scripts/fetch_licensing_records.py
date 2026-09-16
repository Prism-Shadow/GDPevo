#!/usr/bin/env python3
"""Fetch and filter licensing task-environment records.

This helper is intentionally conservative: it gathers likely relevant source
records, but leaves final policy judgment to the solver and the answer template.
It uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from typing import Any


def fetch_json(base_url: str, path: str, limit: int = 1000) -> Any:
    base = base_url.rstrip("/") + "/"
    url = urllib.parse.urljoin(base, path.lstrip("/"))
    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}limit={limit}"
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def by_any_id(row: dict[str, Any], ids: set[str]) -> bool:
    for key in ("application_id", "related_application_id", "license_no"):
        if row.get(key) in ids:
            return True
    return False


def contractor(base_url: str, ids: list[str]) -> dict[str, Any]:
    id_set = set(ids)
    policies = fetch_json(base_url, "/api/policies")
    applications = [
        row
        for row in fetch_json(base_url, "/api/contractor/applications")
        if row.get("application_id") in id_set
    ]
    prior_ids = {row.get("prior_license_id") for row in applications if row.get("prior_license_id")}
    names = {row.get("applicant_name") for row in applications if row.get("applicant_name")}

    bonds = [
        row
        for row in fetch_json(base_url, "/api/contractor/bonds")
        if row.get("application_id") in id_set
    ]
    insurance = [
        row
        for row in fetch_json(base_url, "/api/contractor/insurance")
        if row.get("application_id") in id_set
    ]
    history = [
        row
        for row in fetch_json(base_url, "/api/contractor/license-history")
        if row.get("license_id") in prior_ids or row.get("applicant_name") in names
    ]
    violations = [
        row
        for row in fetch_json(base_url, "/api/contractor/violations")
        if by_any_id(row, id_set) or row.get("license_id") in prior_ids
    ]
    correspondence = [
        row
        for row in fetch_json(base_url, "/api/contractor/correspondence")
        if by_any_id(row, id_set) or row.get("license_id") in prior_ids
    ]
    inspections = [
        row
        for row in fetch_json(base_url, "/api/contractor/inspections")
        if by_any_id(row, id_set) or row.get("license_id") in prior_ids
    ]

    return {
        "policies": [p for p in policies if p.get("family") == "contractor"],
        "applications": applications,
        "bonds": bonds,
        "insurance": insurance,
        "license_history": history,
        "violations": violations,
        "correspondence": correspondence,
        "inspections": inspections,
    }


def liquor(base_url: str, application_id: str, location_id: str | None) -> dict[str, Any]:
    policies = fetch_json(base_url, "/api/policies")
    applications_all = fetch_json(base_url, "/api/liquor/applications")
    applications = [
        row
        for row in applications_all
        if row.get("application_id") == application_id
        or (location_id and row.get("location_id") == location_id)
    ]
    if not location_id and applications:
        location_id = applications[0].get("location_id")
    license_classes = {row.get("license_class") for row in applications if row.get("license_class")}

    settlements = [
        row
        for row in fetch_json(base_url, "/api/liquor/settlements")
        if row.get("application_id") == application_id
        or (location_id and row.get("location_id") == location_id)
    ]
    privileges = [
        row
        for row in fetch_json(base_url, "/api/liquor/privileges")
        if row.get("license_class") in license_classes
    ]
    incidents = [
        row
        for row in fetch_json(base_url, "/api/liquor/incidents")
        if row.get("application_id") == application_id
        or (location_id and row.get("location_id") == location_id)
    ]
    evidence = [
        row
        for row in fetch_json(base_url, "/api/liquor/site-evidence")
        if row.get("application_id") == application_id
        or (location_id and row.get("location_id") == location_id)
    ]

    return {
        "policies": [p for p in policies if p.get("family") == "liquor"],
        "applications": applications,
        "settlements": settlements,
        "privileges": privileges,
        "incidents": incidents,
        "site_evidence": evidence,
    }


def renewal(base_url: str, licenses: list[str], boundary: str | None) -> dict[str, Any]:
    license_set = set(licenses)
    policies = fetch_json(base_url, "/api/policies")
    rules = fetch_json(base_url, "/api/renewal/rules")
    licensees_all = fetch_json(base_url, "/api/alcohol/licensees")
    licensees = [row for row in licensees_all if row.get("license_no") in license_set]
    predecessors = {row.get("successor_to") for row in licensees if row.get("successor_to")}
    predecessor_rows = [row for row in licensees_all if row.get("license_no") in predecessors]
    match_licenses = license_set | predecessors

    violations = [
        row
        for row in fetch_json(base_url, "/api/alcohol/violations")
        if row.get("license_no") in match_licenses
    ]
    pre_boundary = []
    post_boundary = []
    for row in violations:
        if boundary and row.get("violation_date") and row["violation_date"] > boundary:
            post_boundary.append(row)
        else:
            pre_boundary.append(row)

    return {
        "policies": [p for p in policies if p.get("family") == "renewal"],
        "rules": rules,
        "licensees": licensees,
        "predecessor_licensees": predecessor_rows,
        "pre_boundary_violations": pre_boundary,
        "post_boundary_violations": post_boundary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    subparsers = parser.add_subparsers(dest="kind", required=True)

    contractor_parser = subparsers.add_parser("contractor")
    contractor_parser.add_argument("--ids", required=True, help="Comma-separated application IDs")

    liquor_parser = subparsers.add_parser("liquor")
    liquor_parser.add_argument("--application-id", required=True)
    liquor_parser.add_argument("--location-id")

    renewal_parser = subparsers.add_parser("renewal")
    renewal_parser.add_argument("--licenses", required=True, help="Comma-separated license numbers")
    renewal_parser.add_argument("--boundary")

    args = parser.parse_args()
    if args.kind == "contractor":
        result = contractor(args.base_url, parse_csv(args.ids))
    elif args.kind == "liquor":
        result = liquor(args.base_url, args.application_id, args.location_id)
    elif args.kind == "renewal":
        result = renewal(args.base_url, parse_csv(args.licenses), args.boundary)
    else:
        parser.error("unknown kind")
        return 2

    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
