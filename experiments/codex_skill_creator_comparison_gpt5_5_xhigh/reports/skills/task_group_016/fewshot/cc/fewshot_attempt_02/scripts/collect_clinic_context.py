#!/usr/bin/env python3
"""Collect filtered synthetic clinic context for a target case.

The script uses only Python's standard library and read-only GET endpoints.
It does not make protocol decisions; it gathers the facts a solver should
review before filling the task's answer template.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
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


def read_base_url(env_file: str | None) -> str | None:
    if not env_file:
        return None
    text = Path(env_file).read_text(encoding="utf-8")
    match = re.search(r"^base_url:\s*(\S+)\s*$", text, re.MULTILINE)
    return match.group(1) if match else None


def api_get(base_url: str, path: str, params: dict[str, Any] | None = None) -> Any:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    if params:
        url = f"{url}?{urlencode(params)}"
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def try_get(base_url: str, path: str, params: dict[str, Any] | None = None) -> Any:
    try:
        return api_get(base_url, path, params)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def paged_collection(base_url: str, endpoint: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    offset = 0
    limit = 100

    while True:
        data = try_get(base_url, f"/api/{endpoint}", {"limit": limit, "offset": offset})
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            data = try_get(base_url, f"/api/{endpoint}")
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            return items

        page_items = [item for item in data["items"] if isinstance(item, dict)]
        items.extend(page_items)

        total = data.get("count")
        if not page_items or not isinstance(total, int) or len(items) >= total:
            break
        offset += len(page_items)

    return items


def find_case(base_url: str, case_id: str) -> dict[str, Any]:
    direct = try_get(base_url, f"/api/cases/{case_id}")
    if isinstance(direct, dict) and direct:
        return direct

    for item in paged_collection(base_url, "cases"):
        if item.get("case_id") == case_id:
            return item
    raise SystemExit(f"Could not find case_id {case_id!r}")


def find_patient(base_url: str, patient_id: str | None) -> dict[str, Any] | None:
    if not patient_id:
        return None
    direct = try_get(base_url, f"/api/patients/{patient_id}")
    if isinstance(direct, dict) and direct:
        return direct
    for item in paged_collection(base_url, "patients"):
        if item.get("patient_id") == patient_id:
            return item
    return None


def patient_id_from_case(case: dict[str, Any]) -> str | None:
    candidates = [
        case,
        case.get("case") if isinstance(case.get("case"), dict) else None,
        case.get("patient") if isinstance(case.get("patient"), dict) else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, dict) and isinstance(candidate.get("patient_id"), str):
            return candidate["patient_id"]
    return None


def relevant_items(
    items: list[dict[str, Any]], case_id: str, patient_id: str | None
) -> list[dict[str, Any]]:
    filtered = []
    for item in items:
        if item.get("case_id") == case_id:
            filtered.append(item)
        elif patient_id and item.get("patient_id") == patient_id:
            filtered.append(item)
    return filtered


def protocol_details(base_url: str) -> dict[str, Any]:
    protocols = try_get(base_url, "/api/protocols")
    details: dict[str, Any] = {"list": protocols, "by_id": {}}
    if not isinstance(protocols, dict):
        return details

    for item in protocols.get("items", []):
        if not isinstance(item, dict):
            continue
        protocol_id = item.get("protocol_id")
        if not protocol_id:
            continue
        detail = try_get(base_url, f"/api/protocols/{protocol_id}")
        if detail is not None:
            details["by_id"][protocol_id] = detail
    return details


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True, help="Target clinic case id")
    parser.add_argument("--base-url", help="Runtime base URL")
    parser.add_argument("--env-file", help="Path to environment_access.md")
    args = parser.parse_args()

    base_url = args.base_url or read_base_url(args.env_file)
    if not base_url:
        raise SystemExit("Provide --base-url or --env-file containing base_url")

    case = find_case(base_url, args.case_id)
    patient_id = patient_id_from_case(case)
    patient = case.get("patient") if isinstance(case.get("patient"), dict) else None
    if patient is None:
        patient = find_patient(base_url, patient_id)

    collections: dict[str, list[dict[str, Any]]] = {}
    for endpoint in COLLECTION_ENDPOINTS:
        collections[endpoint] = relevant_items(
            paged_collection(base_url, endpoint), args.case_id, patient_id
        )

    output = {
        "case_id": args.case_id,
        "patient_id": patient_id,
        "case": case,
        "patient": patient,
        "collections": collections,
        "protocols": protocol_details(base_url),
    }
    json.dump(output, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
