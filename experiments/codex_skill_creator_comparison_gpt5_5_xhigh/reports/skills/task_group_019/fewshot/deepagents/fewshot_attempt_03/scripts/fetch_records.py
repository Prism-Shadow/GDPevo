#!/usr/bin/env python3
"""Fetch target licensing-environment records for licensing review tasks.

This helper intentionally fetches by target identifiers from the prompt. It is
not a solver; apply SKILL.md rules and the task answer template after fetching.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from typing import Any


def get_json(base_url: str, path: str, params: dict[str, str] | None = None) -> Any:
    base = base_url.rstrip("/") + "/"
    url = urllib.parse.urljoin(base, path.lstrip("/"))
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=20) as response:
        data = response.read().decode("utf-8")
    parsed = json.loads(data)
    if isinstance(parsed, dict) and "error" in parsed:
        raise RuntimeError(f"{path} rejected params {params}: {parsed['error']}")
    return parsed


def extend(result: dict[str, Any], key: str, rows: Any) -> None:
    if rows is None:
        return
    if isinstance(rows, list):
        result.setdefault(key, []).extend(rows)
    else:
        result.setdefault(key, []).append(rows)


def unique_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        marker = json.dumps(row, sort_keys=True)
        if marker not in seen:
            seen.add(marker)
            out.append(row)
    return out


def fetch_contractor(base_url: str, ids: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {"policies": get_json(base_url, "/api/policies")}
    prior_license_ids: list[str] = []
    for app_id in ids:
        apps = get_json(base_url, "/api/contractor/applications", {"application_id": app_id})
        extend(result, "applications", apps)
        for app in apps:
            prior = app.get("prior_license_id")
            if prior:
                prior_license_ids.append(prior)
        extend(result, "bonds", get_json(base_url, "/api/contractor/bonds", {"application_id": app_id}))
        extend(result, "insurance", get_json(base_url, "/api/contractor/insurance", {"application_id": app_id}))
        extend(result, "violations", get_json(base_url, "/api/contractor/violations", {"related_application_id": app_id}))
        extend(result, "correspondence", get_json(base_url, "/api/contractor/correspondence", {"related_application_id": app_id}))
        extend(result, "inspections", get_json(base_url, "/api/contractor/inspections", {"related_application_id": app_id}))
    for license_id in sorted(set(prior_license_ids)):
        try:
            extend(result, "license_history", get_json(base_url, "/api/contractor/license-history", {"license_id": license_id}))
        except RuntimeError:
            rows = get_json(base_url, "/api/contractor/license-history")
            extend(result, "license_history", [r for r in rows if r.get("license_id") == license_id])
    for key, rows in list(result.items()):
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            result[key] = unique_rows(rows)
    return result


def fetch_liquor(base_url: str, applications: list[str], locations: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {"policies": get_json(base_url, "/api/policies")}
    license_classes: set[str] = set()
    for app_id in applications:
        apps = get_json(base_url, "/api/liquor/applications", {"application_id": app_id})
        extend(result, "applications", apps)
        for app in apps:
            if app.get("location_id"):
                locations.append(app["location_id"])
            if app.get("license_class"):
                license_classes.add(app["license_class"])
    for location_id in sorted(set(locations)):
        extend(result, "settlements", get_json(base_url, "/api/liquor/settlements", {"location_id": location_id}))
        extend(result, "incidents", get_json(base_url, "/api/liquor/incidents", {"location_id": location_id}))
        extend(result, "site_evidence", get_json(base_url, "/api/liquor/site-evidence", {"location_id": location_id}))
    privileges = get_json(base_url, "/api/liquor/privileges")
    result["privileges"] = [row for row in privileges if row.get("license_class") in license_classes]
    for key, rows in list(result.items()):
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            result[key] = unique_rows(rows)
    return result


def fetch_renewal(base_url: str, licenses: list[str], boundary: str | None) -> dict[str, Any]:
    result: dict[str, Any] = {"rules": get_json(base_url, "/api/renewal/rules")}
    violation_license_numbers = set(licenses)
    for license_no in licenses:
        rows = get_json(base_url, "/api/alcohol/licensees", {"license_no": license_no})
        extend(result, "licensees", rows)
        for row in rows:
            successor = row.get("successor_to")
            if successor:
                violation_license_numbers.add(successor)
    for license_no in sorted(violation_license_numbers):
        extend(result, "violations", get_json(base_url, "/api/alcohol/violations", {"license_no": license_no}))
    if boundary:
        result["selected_rules"] = [r for r in result["rules"] if r.get("release_boundary") == boundary]
    for key, rows in list(result.items()):
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            result[key] = unique_rows(rows)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    sub = parser.add_subparsers(dest="family", required=True)

    contractor = sub.add_parser("contractor")
    contractor.add_argument("--ids", nargs="+", required=True)

    liquor = sub.add_parser("liquor")
    liquor.add_argument("--applications", nargs="*", default=[])
    liquor.add_argument("--locations", nargs="*", default=[])

    renewal = sub.add_parser("renewal")
    renewal.add_argument("--licenses", nargs="+", required=True)
    renewal.add_argument("--boundary")

    args = parser.parse_args()
    if args.family == "contractor":
        payload = fetch_contractor(args.base_url, args.ids)
    elif args.family == "liquor":
        payload = fetch_liquor(args.base_url, args.applications, args.locations)
    else:
        payload = fetch_renewal(args.base_url, args.licenses, args.boundary)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
