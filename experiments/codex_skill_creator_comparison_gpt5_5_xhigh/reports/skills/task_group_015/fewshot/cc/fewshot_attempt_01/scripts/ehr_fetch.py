#!/usr/bin/env python3
"""Fetch allowed EHR task-environment records into one JSON file."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


PATIENT_SUBRESOURCES = [
    "conditions",
    "medications",
    "allergies",
    "encounters",
    "immunizations",
    "documents",
    "service-requests",
    "disclosures",
]


def get_json(base_url: str, path: str) -> Any:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return {"_error": f"HTTP {exc.code}", "_path": path}
    except urllib.error.URLError as exc:
        return {"_error": str(exc.reason), "_path": path}
    if not body.strip():
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"_error": "non_json_response", "_path": path, "_body": body}


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--patient", action="append", default=[])
    parser.add_argument("--duplicate", action="append", default=[])
    parser.add_argument("--referral", action="append", default=[])
    parser.add_argument("--provider", action="append", default=[])
    parser.add_argument("--icd10", action="append", default=[])
    parser.add_argument("--service-code", action="append", default=[])
    parser.add_argument("--include-patients-list", action="store_true")
    parser.add_argument("--include-referrals-list", action="store_true")
    parser.add_argument("--include-duplicates-list", action="store_true")
    parser.add_argument("--include-audit-logs", action="store_true")
    parser.add_argument("--out", help="Write JSON here instead of stdout")
    args = parser.parse_args()

    result: dict[str, Any] = {
        "patients": {},
        "duplicates": {},
        "referrals": {},
        "providers": {},
        "icd10": {},
        "service_codes": {},
        "lists": {},
    }

    if args.include_patients_list:
        result["lists"]["patients"] = get_json(args.base_url, "/api/patients")
    if args.include_referrals_list:
        result["lists"]["referrals"] = get_json(args.base_url, "/api/referrals")
    if args.include_duplicates_list:
        result["lists"]["duplicates_candidates"] = get_json(args.base_url, "/api/duplicates/candidates")
    if args.include_audit_logs:
        result["lists"]["audit_logs"] = get_json(args.base_url, "/api/audit-logs")

    for patient_id in unique(args.patient):
        patient_record: dict[str, Any] = {
            "detail": get_json(args.base_url, f"/api/patients/{patient_id}")
        }
        for subresource in PATIENT_SUBRESOURCES:
            patient_record[subresource] = get_json(
                args.base_url, f"/api/patients/{patient_id}/{subresource}"
            )
        result["patients"][patient_id] = patient_record

    for duplicate_id in unique(args.duplicate):
        result["duplicates"][duplicate_id] = get_json(
            args.base_url, f"/api/duplicates/{duplicate_id}"
        )

    for referral_id in unique(args.referral):
        result["referrals"][referral_id] = get_json(
            args.base_url, f"/api/referrals/{referral_id}"
        )

    for provider_id in unique(args.provider):
        result["providers"][provider_id] = get_json(
            args.base_url, f"/api/providers/{provider_id}"
        )

    for code in unique(args.icd10):
        result["icd10"][code] = get_json(args.base_url, f"/api/icd10/{code}")

    for code in unique(args.service_code):
        result["service_codes"][code] = get_json(
            args.base_url, f"/api/service-codes/{code}"
        )

    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.write("\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
