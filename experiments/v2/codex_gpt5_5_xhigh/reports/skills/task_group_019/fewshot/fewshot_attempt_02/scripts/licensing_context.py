#!/usr/bin/env python3
"""Fetch grouped licensing records from a task environment.

This helper intentionally performs no eligibility decisions. It prints targeted
records and parsed JSON fields so Codex can apply the skill instructions and the
task's answer template without hard-coding examples.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from typing import Any


ENDPOINTS = {
    "contractor": [
        "policies",
        "contractor/applications",
        "contractor/bonds",
        "contractor/insurance",
        "contractor/license-history",
        "contractor/violations",
        "contractor/correspondence",
        "contractor/inspections",
    ],
    "liquor": [
        "policies",
        "liquor/applications",
        "liquor/settlements",
        "liquor/privileges",
        "liquor/incidents",
        "liquor/site-evidence",
    ],
    "renewal": [
        "policies",
        "alcohol/licensees",
        "alcohol/violations",
        "renewal/rules",
    ],
}

SQL_TABLES = {
    "contractor": [
        "policies",
        "contractor_applications",
        "contractor_bonds",
        "contractor_insurance",
        "contractor_license_history",
        "contractor_violations",
        "contractor_correspondence",
        "contractor_inspections",
    ],
    "liquor": [
        "policies",
        "liquor_applications",
        "liquor_settlements",
        "liquor_privileges",
        "liquor_incidents",
        "liquor_site_evidence",
    ],
    "renewal": [
        "policies",
        "alcohol_licensees",
        "alcohol_violations",
        "renewal_rules",
    ],
}


def parse_env_file(path: str) -> tuple[str, str | None]:
    text = open(path, encoding="utf-8").read()
    base_match = re.search(r"^GDPEVO_ENV_BASE_URL=(\S+)", text, re.MULTILINE)
    token_match = re.search(r"^X-Task-Token:\s*(\S+)", text, re.MULTILINE)
    if not base_match:
        raise SystemExit(f"Could not find GDPEVO_ENV_BASE_URL in {path}")
    return base_match.group(1).rstrip("/") + "/", token_match.group(1) if token_match else None


def request_json(url: str, *, token: str | None = None, payload: dict[str, Any] | None = None) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-Task-Token"] = token
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def get_endpoint(base_url: str, endpoint: str) -> list[dict[str, Any]]:
    return request_json(base_url + endpoint)


def sql(base_url: str, token: str | None, query: str) -> list[dict[str, Any]]:
    if not token:
        return []
    try:
        result = request_json(base_url + "api/sql", token=token, payload={"query": query})
    except urllib.error.HTTPError as exc:
        print(f"SQL skipped for query: {query} ({exc})", file=sys.stderr)
        return []
    return result.get("rows", [])


def parse_json_fields(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for key in list(out):
        if key.endswith("_json") and isinstance(out[key], str):
            try:
                out[key + "_parsed"] = json.loads(out[key])
            except json.JSONDecodeError:
                pass
    return out


def print_section(title: str, value: Any) -> None:
    print(f"\n## {title}")
    print(json.dumps(value, indent=2, sort_keys=True))


def in_targets(row: dict[str, Any], targets: set[str]) -> bool:
    return any(str(value) in targets for value in row.values())


def contains_any(row: dict[str, Any], needles: set[str]) -> bool:
    return any(needle and needle in str(value) for needle in needles for value in row.values())


def contractor_context(args: argparse.Namespace, base_url: str, token: str | None) -> None:
    targets = set(args.target_id)
    if not targets:
        raise SystemExit("contractor domain requires at least one --target-id")

    rows_by_table = {table: sql(base_url, token, f"select * from {table}") for table in SQL_TABLES["contractor"]}
    if not any(rows_by_table.values()):
        rows_by_table = {
            endpoint.replace("/", "_").replace("-", "_"): get_endpoint(base_url, "api/" + endpoint)
            for endpoint in ENDPOINTS["contractor"]
        }

    applications = [r for r in rows_by_table["contractor_applications"] if r.get("application_id") in targets]
    prior_ids = {r.get("prior_license_id") for r in applications if r.get("prior_license_id")}

    print_section("contractor_policies", [parse_json_fields(r) for r in rows_by_table["policies"] if r.get("family") == "contractor"])
    print_section("applications", applications)
    print_section("bonds", [r for r in rows_by_table["contractor_bonds"] if r.get("application_id") in targets])
    print_section("insurance", [r for r in rows_by_table["contractor_insurance"] if r.get("application_id") in targets])
    print_section("license_history", [r for r in rows_by_table["contractor_license_history"] if r.get("license_id") in prior_ids])
    print_section(
        "violations",
        [
            r
            for r in rows_by_table["contractor_violations"]
            if r.get("related_application_id") in targets or r.get("license_id") in prior_ids
        ],
    )
    print_section(
        "correspondence",
        [r for r in rows_by_table["contractor_correspondence"] if r.get("related_application_id") in targets],
    )
    print_section(
        "inspections",
        [r for r in rows_by_table["contractor_inspections"] if r.get("related_application_id") in targets],
    )


def liquor_context(args: argparse.Namespace, base_url: str, token: str | None) -> None:
    if not args.application_id and not args.location_id:
        raise SystemExit("liquor domain requires --application-id or --location-id")

    app_ids = set(args.application_id)
    loc_ids = set(args.location_id)
    apps = sql(base_url, token, "select * from liquor_applications")
    if not apps:
        apps = get_endpoint(base_url, "api/liquor/applications")
    matched_apps = [r for r in apps if r.get("application_id") in app_ids or r.get("location_id") in loc_ids]
    loc_ids.update(r.get("location_id") for r in matched_apps if r.get("location_id"))
    classes = {r.get("license_class") for r in matched_apps if r.get("license_class")}

    tables = {table: sql(base_url, token, f"select * from {table}") for table in SQL_TABLES["liquor"]}
    if not any(tables.values()):
        tables = {
            endpoint.replace("/", "_").replace("-", "_"): get_endpoint(base_url, "api/" + endpoint)
            for endpoint in ENDPOINTS["liquor"]
        }

    print_section("liquor_policies", [parse_json_fields(r) for r in tables["policies"] if r.get("family") == "liquor"])
    print_section("applications", matched_apps)
    print_section("privileges", [r for r in tables["liquor_privileges"] if r.get("license_class") in classes])
    print_section("settlements", [parse_json_fields(r) for r in tables["liquor_settlements"] if r.get("location_id") in loc_ids])
    print_section("incidents", [r for r in tables["liquor_incidents"] if r.get("location_id") in loc_ids])
    print_section("site_evidence", [r for r in tables["liquor_site_evidence"] if r.get("location_id") in loc_ids])


def renewal_context(args: argparse.Namespace, base_url: str, token: str | None) -> None:
    targets = set(args.target_id)
    if not targets:
        raise SystemExit("renewal domain requires at least one --target-id")
    boundary = args.boundary_date
    if boundary:
        try:
            date.fromisoformat(boundary)
        except ValueError as exc:
            raise SystemExit("--boundary-date must be YYYY-MM-DD") from exc

    tables = {table: sql(base_url, token, f"select * from {table}") for table in SQL_TABLES["renewal"]}
    if not any(tables.values()):
        tables = {
            endpoint.replace("/", "_").replace("-", "_"): get_endpoint(base_url, "api/" + endpoint)
            for endpoint in ENDPOINTS["renewal"]
        }

    licensees = [r for r in tables["alcohol_licensees"] if r.get("license_no") in targets]
    predecessor_ids = {r.get("successor_to") for r in licensees if r.get("successor_to")}
    match_ids = targets | {x for x in predecessor_ids if x}

    violations = [
        r
        for r in tables["alcohol_violations"]
        if r.get("license_no") in match_ids or contains_any(r, predecessor_ids)
    ]
    if args.include_address_candidates:
        addresses = {r.get("address") for r in licensees if r.get("address")}
        known_license_numbers = {r.get("license_no") for r in violations}
        address_candidates = [
            r
            for r in tables["alcohol_violations"]
            if r.get("address") in addresses and r.get("license_no") not in known_license_numbers
        ]
    else:
        address_candidates = []
    included = [r for r in violations if not boundary or str(r.get("violation_date", "")) <= boundary]
    excluded = [r for r in violations if boundary and str(r.get("violation_date", "")) > boundary]

    print_section("renewal_policies", [parse_json_fields(r) for r in tables["policies"] if r.get("family") == "renewal"])
    print_section("renewal_rules", [parse_json_fields(r) for r in tables["renewal_rules"]])
    print_section("licensees", licensees)
    print_section("included_violations", included)
    print_section("post_boundary_violations", excluded)
    if address_candidates:
        print_section("address_match_candidates", address_candidates)


def main() -> None:
    parser = argparse.ArgumentParser(description="Print grouped licensing context records.")
    parser.add_argument("--env-file", default="environment_access.md")
    parser.add_argument("--domain", choices=sorted(ENDPOINTS), required=True)
    parser.add_argument("--target-id", action="append", default=[], help="Application or license ID; repeat as needed.")
    parser.add_argument("--application-id", action="append", default=[])
    parser.add_argument("--location-id", action="append", default=[])
    parser.add_argument("--boundary-date")
    parser.add_argument("--include-address-candidates", action="store_true")
    args = parser.parse_args()

    base_url, token = parse_env_file(args.env_file)
    if args.domain == "contractor":
        contractor_context(args, base_url, token)
    elif args.domain == "liquor":
        liquor_context(args, base_url, token)
    else:
        renewal_context(args, base_url, token)


if __name__ == "__main__":
    main()
