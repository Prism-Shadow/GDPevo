#!/usr/bin/env python3
"""Collect case-scoped context from the synthetic clinic task API.

This helper uses only the Python standard library. It prints a JSON bundle to
stdout and never mutates the runtime environment.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


COLLECTION_ENDPOINTS = [
    "observations",
    "medications",
    "allergies",
    "problems",
    "imaging",
    "care-registry",
    "sdoh",
]


def fetch_json(base_url: str, path: str) -> Any:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise SystemExit(f"GET {path} failed: HTTP {exc.code}") from exc
    except URLError as exc:
        raise SystemExit(f"GET {path} failed: {exc.reason}") from exc


def items_from(payload: Any) -> list[Any]:
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]
    if isinstance(payload, list):
        return payload
    if payload is None:
        return []
    return [payload]


def contains_identifier(value: Any, identifier: str | None) -> bool:
    if not identifier:
        return False
    if isinstance(value, dict):
        return any(contains_identifier(v, identifier) for v in value.values())
    if isinstance(value, list):
        return any(contains_identifier(v, identifier) for v in value)
    return str(value) == identifier


def relevant_items(payload: Any, case_id: str, patient_id: str | None) -> list[Any]:
    relevant = []
    for item in items_from(payload):
        if contains_identifier(item, case_id) or contains_identifier(item, patient_id):
            relevant.append(item)
    return relevant


def find_case(cases_payload: Any, case_id: str) -> dict[str, Any]:
    for item in items_from(cases_payload):
        if isinstance(item, dict) and item.get("case_id") == case_id:
            return item
    raise SystemExit(f"Case not found in /api/cases: {case_id}")


def protocol_details(base_url: str) -> dict[str, Any]:
    listing = fetch_json(base_url, "/api/protocols")
    details: dict[str, Any] = {"listing": listing, "items": {}}
    for item in items_from(listing):
        if not isinstance(item, dict):
            continue
        protocol_id = item.get("protocol_id")
        if protocol_id:
            details["items"][protocol_id] = fetch_json(
                base_url, f"/api/protocols/{protocol_id}"
            )
    return details


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument("--case-id", required=True, help="Target clinic case id")
    parser.add_argument(
        "--include-full-collections",
        action="store_true",
        help="Also include unfiltered collection payloads for manual review",
    )
    args = parser.parse_args()

    cases_payload = fetch_json(args.base_url, "/api/cases")
    case_summary = find_case(cases_payload, args.case_id)
    case_detail = fetch_json(args.base_url, f"/api/cases/{args.case_id}")

    patient_id = None
    for source in (case_detail, case_summary):
        if isinstance(source, dict) and source.get("patient_id"):
            patient_id = str(source["patient_id"])
            break

    patient_detail = None
    if patient_id:
        patient_detail = fetch_json(args.base_url, f"/api/patients/{patient_id}")

    resources: dict[str, Any] = {}
    for endpoint in COLLECTION_ENDPOINTS:
        payload = fetch_json(args.base_url, f"/api/{endpoint}")
        entry: dict[str, Any] = {
            "relevant_items": relevant_items(payload, args.case_id, patient_id),
            "total_items": len(items_from(payload)),
        }
        if args.include_full_collections:
            entry["full_payload"] = payload
        resources[endpoint] = entry

    bundle = {
        "target_case_id": args.case_id,
        "patient_id": patient_id,
        "case_summary": case_summary,
        "case_detail": case_detail,
        "patient_detail": patient_detail,
        "resources": resources,
        "protocols": protocol_details(args.base_url),
    }
    try:
        json.dump(bundle, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    except BrokenPipeError:
        sys.stdout = open(os.devnull, "w")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
