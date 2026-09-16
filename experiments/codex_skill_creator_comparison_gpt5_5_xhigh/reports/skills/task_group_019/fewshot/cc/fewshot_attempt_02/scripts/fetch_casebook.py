#!/usr/bin/env python3
"""Fetch a compact licensing casebook from the task environment."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable


def fetch_json(base_url: str, path: str, params: dict[str, str] | None = None):
    base = base_url.rstrip("/") + "/"
    url = urllib.parse.urljoin(base, path.lstrip("/"))
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as response:
        data = response.read().decode("utf-8")
    return json.loads(data)


def safe_fetch(base_url: str, path: str, errors: list[dict], params: dict[str, str] | None = None):
    try:
        data = fetch_json(base_url, path, params)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        errors.append({"endpoint": path, "params": params or {}, "error": str(exc)})
        return []
    if isinstance(data, dict) and "error" in data:
        errors.append({"endpoint": path, "params": params or {}, "error": data["error"]})
        return []
    return data if isinstance(data, list) else data


def any_value_in(record: dict, keys: Iterable[str], values: set[str]) -> bool:
    return any(str(record.get(key) or "") in values for key in keys)


def filter_records(records, keys: Iterable[str], values: set[str]):
    if not values:
        return records
    return [record for record in records if isinstance(record, dict) and any_value_in(record, keys, values)]


def fetch_with_application_filter(base_url: str, path: str, ids: list[str], errors: list[dict]):
    if not ids:
        return safe_fetch(base_url, path, errors)
    combined = []
    for app_id in ids:
        rows = safe_fetch(base_url, path, errors, {"application_id": app_id})
        if isinstance(rows, list):
            combined.extend(rows)
    return combined


def parse_json_field(record: dict, field: str):
    value = record.get(field)
    if isinstance(value, str):
        try:
            record[field + "_parsed"] = json.loads(value)
        except json.JSONDecodeError:
            record[field + "_parsed_error"] = True
    return record


def contractor_casebook(base_url: str, ids: list[str]):
    errors: list[dict] = []
    id_set = set(ids)
    policies = [
        parse_json_field(row, "details_json")
        for row in safe_fetch(base_url, "/api/policies", errors)
        if row.get("family") == "contractor"
    ]
    apps = filter_records(
        safe_fetch(base_url, "/api/contractor/applications", errors),
        ["application_id"],
        id_set,
    )
    prior_ids = {row.get("prior_license_id") for row in apps if row.get("prior_license_id")}
    bonds = fetch_with_application_filter(base_url, "/api/contractor/bonds", ids, errors)
    insurance = fetch_with_application_filter(base_url, "/api/contractor/insurance", ids, errors)
    history = filter_records(
        safe_fetch(base_url, "/api/contractor/license-history", errors),
        ["license_id"],
        prior_ids,
    )
    linked_keys = ["application_id", "related_application_id", "license_id", "related_license_id"]
    linked_values = id_set | prior_ids
    violations = filter_records(safe_fetch(base_url, "/api/contractor/violations", errors), linked_keys, linked_values)
    correspondence = filter_records(
        safe_fetch(base_url, "/api/contractor/correspondence", errors),
        linked_keys,
        linked_values,
    )
    inspections = filter_records(
        safe_fetch(base_url, "/api/contractor/inspections", errors),
        linked_keys,
        linked_values,
    )
    return {
        "family": "contractor",
        "targets": ids,
        "policies": policies,
        "applications": apps,
        "bonds": bonds,
        "insurance": insurance,
        "license_history": history,
        "violations": violations,
        "correspondence": correspondence,
        "inspections": inspections,
        "errors": errors,
    }


def liquor_casebook(base_url: str, ids: list[str], locations: list[str]):
    errors: list[dict] = []
    id_set = set(ids)
    location_set = set(locations)
    policies = [
        parse_json_field(row, "details_json")
        for row in safe_fetch(base_url, "/api/policies", errors)
        if row.get("family") == "liquor"
    ]
    all_apps = safe_fetch(base_url, "/api/liquor/applications", errors)
    apps = [
        row
        for row in all_apps
        if isinstance(row, dict)
        and ((not id_set and not location_set) or row.get("application_id") in id_set or row.get("location_id") in location_set)
    ]
    location_set |= {row.get("location_id") for row in apps if row.get("location_id")}
    license_classes = {row.get("license_class") for row in apps if row.get("license_class")}
    settlements = [
        parse_json_field(row, "controls_json")
        for row in filter_records(safe_fetch(base_url, "/api/liquor/settlements", errors), ["location_id"], location_set)
    ]
    privileges = filter_records(
        safe_fetch(base_url, "/api/liquor/privileges", errors),
        ["license_class"],
        set(license_classes),
    )
    incidents = filter_records(safe_fetch(base_url, "/api/liquor/incidents", errors), ["location_id"], location_set)
    evidence = filter_records(safe_fetch(base_url, "/api/liquor/site-evidence", errors), ["location_id"], location_set)
    return {
        "family": "liquor",
        "targets": ids,
        "locations": sorted(location_set),
        "policies": policies,
        "applications": apps,
        "settlements": settlements,
        "privileges": privileges,
        "incidents": incidents,
        "site_evidence": evidence,
        "errors": errors,
    }


def renewal_casebook(base_url: str, ids: list[str]):
    errors: list[dict] = []
    id_set = set(ids)
    policies = [
        parse_json_field(row, "details_json")
        for row in safe_fetch(base_url, "/api/policies", errors)
        if row.get("family") == "renewal"
    ]
    all_licensees = safe_fetch(base_url, "/api/alcohol/licensees", errors)
    targets = filter_records(all_licensees, ["license_no"], id_set)
    predecessor_ids = {row.get("successor_to") for row in targets if row.get("successor_to")}
    licensees = [
        row
        for row in all_licensees
        if isinstance(row, dict) and (row.get("license_no") in id_set or row.get("license_no") in predecessor_ids)
    ]
    violations = filter_records(
        safe_fetch(base_url, "/api/alcohol/violations", errors),
        ["license_no", "matched_license_no"],
        id_set | predecessor_ids,
    )
    rules = [parse_json_field(row, "details_json") for row in safe_fetch(base_url, "/api/renewal/rules", errors)]
    return {
        "family": "renewal",
        "targets": ids,
        "policies": policies,
        "licensees": licensees,
        "violations": violations,
        "rules": rules,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument("--family", required=True, choices=["contractor", "liquor", "renewal"])
    parser.add_argument("--ids", nargs="*", default=[], help="Target application IDs or license numbers")
    parser.add_argument("--locations", nargs="*", default=[], help="Target liquor location IDs")
    parser.add_argument("--out", help="Optional output file path")
    args = parser.parse_args()

    if args.family == "contractor":
        casebook = contractor_casebook(args.base_url, args.ids)
    elif args.family == "liquor":
        casebook = liquor_casebook(args.base_url, args.ids, args.locations)
    else:
        casebook = renewal_casebook(args.base_url, args.ids)

    output = json.dumps(casebook, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(output + "\n")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
