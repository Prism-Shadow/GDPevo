#!/usr/bin/env python3
"""Collect filtered Court Operations Portal records for closeout tasks."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from typing import Any


ENDPOINTS = {
    "jurisdictions": "/api/jurisdictions",
    "cases": "/api/cases",
    "charges": "/api/charges",
    "docket_entries": "/api/docket-entries",
    "citations": "/api/citations",
    "fee_schedules": "/api/fee-schedules",
    "payment_policies": "/api/payment-policies",
    "forms": "/api/forms",
    "financial_petitions": "/api/financial-petitions",
}

SORT_KEYS = {
    "jurisdictions": ("jurisdiction_code",),
    "cases": ("case_number",),
    "charges": ("case_number", "count_no", "charge_id"),
    "docket_entries": ("case_number", "entry_date", "entry_id"),
    "citations": ("citation_number",),
    "fee_schedules": ("jurisdiction_code", "priority", "fee_id"),
    "payment_policies": ("jurisdiction_code", "policy_id"),
    "forms": ("jurisdiction_code", "form_id"),
    "financial_petitions": ("petition_id", "case_number"),
}


def get_json(base_url: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=20) as response:
        data = response.read().decode("utf-8")
    parsed = json.loads(data)
    if not isinstance(parsed, dict):
        raise ValueError(f"Unexpected response from {path}: expected object")
    return parsed


def dedupe(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for record in records:
        key = json.dumps(record, sort_keys=True, separators=(",", ":"))
        if key not in seen:
            seen.add(key)
            unique.append(record)
    return unique


def sort_records(name: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = SORT_KEYS.get(name, ())

    def key_func(record: dict[str, Any]) -> tuple[str, ...]:
        return tuple("" if record.get(key) is None else str(record.get(key)) for key in keys)

    return sorted(records, key=key_func)


def collect_by_field(
    base_url: str,
    name: str,
    field: str,
    values: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    if not values:
        return []

    records: list[dict[str, Any]] = []
    for value in values:
        try:
            payload = get_json(base_url, ENDPOINTS[name], {field: value, "limit": limit})
            endpoint_records = payload.get("results", [])
            if isinstance(endpoint_records, list):
                records.extend(
                    r for r in endpoint_records
                    if isinstance(r, dict) and str(r.get(field)) == value
                )
        except Exception as exc:
            print(f"warning: filtered fetch failed for {name} {field}={value}: {exc}", file=sys.stderr)

    if records:
        return sort_records(name, dedupe(records))

    payload = get_json(base_url, ENDPOINTS[name], {"limit": limit})
    endpoint_records = payload.get("results", [])
    if not isinstance(endpoint_records, list):
        return []
    filtered = [r for r in endpoint_records if isinstance(r, dict) and str(r.get(field)) in values]
    return sort_records(name, dedupe(filtered))


def collect_for_jurisdictions(
    base_url: str,
    name: str,
    jurisdictions: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    if not jurisdictions:
        return []
    records: list[dict[str, Any]] = []
    for jurisdiction in jurisdictions:
        try:
            payload = get_json(base_url, ENDPOINTS[name], {"jurisdiction_code": jurisdiction, "limit": limit})
            endpoint_records = payload.get("results", [])
            if isinstance(endpoint_records, list):
                records.extend(
                    r for r in endpoint_records
                    if isinstance(r, dict) and str(r.get("jurisdiction_code")) == jurisdiction
                )
        except Exception as exc:
            print(f"warning: jurisdiction fetch failed for {name} {jurisdiction}: {exc}", file=sys.stderr)

    if records:
        return sort_records(name, dedupe(records))

    payload = get_json(base_url, ENDPOINTS[name], {"limit": limit})
    endpoint_records = payload.get("results", [])
    if not isinstance(endpoint_records, list):
        return []
    filtered = [
        r for r in endpoint_records
        if isinstance(r, dict) and str(r.get("jurisdiction_code")) in jurisdictions
    ]
    return sort_records(name, dedupe(filtered))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Portal base URL, for example http://task-env:9018/")
    parser.add_argument("--case", dest="cases", action="append", default=[], help="Target case number")
    parser.add_argument("--citation", dest="citations", action="append", default=[], help="Target citation number")
    parser.add_argument("--petition", dest="petitions", action="append", default=[], help="Target financial petition ID")
    parser.add_argument("--jurisdiction", dest="jurisdictions", action="append", default=[], help="Target jurisdiction code")
    parser.add_argument("--limit", type=int, default=500, help="Result limit for list endpoints")
    args = parser.parse_args()

    target_cases = set(args.cases)
    petition_records = collect_by_field(
        args.base_url, "financial_petitions", "petition_id", args.petitions, args.limit
    )
    for record in petition_records:
        case_number = record.get("case_number")
        if case_number:
            target_cases.add(str(case_number))

    if target_cases:
        petition_records.extend(
            collect_by_field(
                args.base_url,
                "financial_petitions",
                "case_number",
                sorted(target_cases),
                args.limit,
            )
        )

    snapshot: dict[str, list[dict[str, Any]]] = {
        "cases": collect_by_field(args.base_url, "cases", "case_number", sorted(target_cases), args.limit),
        "charges": collect_by_field(args.base_url, "charges", "case_number", sorted(target_cases), args.limit),
        "docket_entries": collect_by_field(
            args.base_url, "docket_entries", "case_number", sorted(target_cases), args.limit
        ),
        "citations": collect_by_field(args.base_url, "citations", "citation_number", args.citations, args.limit),
    }

    snapshot["financial_petitions"] = sort_records("financial_petitions", dedupe(petition_records))

    jurisdictions = set(args.jurisdictions)
    for group in ("cases", "citations", "financial_petitions"):
        for record in snapshot[group]:
            value = record.get("jurisdiction_code")
            if value:
                jurisdictions.add(str(value))

    jurisdiction_list = sorted(jurisdictions)
    snapshot["jurisdictions"] = collect_for_jurisdictions(
        args.base_url, "jurisdictions", jurisdiction_list, args.limit
    )
    snapshot["fee_schedules"] = collect_for_jurisdictions(
        args.base_url, "fee_schedules", jurisdiction_list, args.limit
    )
    snapshot["payment_policies"] = collect_for_jurisdictions(
        args.base_url, "payment_policies", jurisdiction_list, args.limit
    )
    snapshot["forms"] = collect_for_jurisdictions(args.base_url, "forms", jurisdiction_list, args.limit)

    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
