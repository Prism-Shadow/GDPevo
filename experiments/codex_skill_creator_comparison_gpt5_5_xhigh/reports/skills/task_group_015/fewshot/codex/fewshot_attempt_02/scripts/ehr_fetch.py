#!/usr/bin/env python3
"""Collect read-only EHR task evidence into one JSON document.

This helper intentionally performs no answer inference. It fetches allowed
endpoint families and groups related records so an agent can inspect evidence
against the task's answer template.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


PATIENT_COLLECTIONS = (
    "conditions",
    "medications",
    "allergies",
    "encounters",
    "immunizations",
    "documents",
    "service-requests",
    "disclosures",
)


def normalize_base_url(raw: str) -> str:
    base = raw.strip()
    if not base:
        raise ValueError("base URL is empty")
    return base.rstrip("/") + "/"


def fetch_json(base_url: str, path: str) -> Any:
    url = urllib.parse.urljoin(base_url, path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {path} failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GET {path} failed: {exc.reason}") from exc
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"GET {path} returned non-JSON response") from exc


def add_unique(values: list[str], value: str | None) -> None:
    if value and value not in values:
        values.append(value)


def collect_patient(base_url: str, patient_id: str) -> dict[str, Any]:
    record: dict[str, Any] = {"detail": fetch_json(base_url, f"/api/patients/{patient_id}")}
    for collection in PATIENT_COLLECTIONS:
        record[collection] = fetch_json(base_url, f"/api/patients/{patient_id}/{collection}")
    return record


def find_service_request(base_url: str, service_request_id: str) -> tuple[str | None, dict[str, Any] | None]:
    patients = fetch_json(base_url, "/api/patients").get("patients", [])
    for patient in patients:
        patient_id = patient.get("patient_id")
        if not patient_id:
            continue
        service_requests = fetch_json(base_url, f"/api/patients/{patient_id}/service-requests")
        for service_request in service_requests.get("service_requests", []):
            if service_request.get("service_request_id") == service_request_id:
                return patient_id, service_request
    return None, None


def collect(args: argparse.Namespace) -> dict[str, Any]:
    base_url = normalize_base_url(args.base_url)
    result: dict[str, Any] = {
        "base_url": base_url,
        "patients": {},
        "duplicates": {},
        "referrals": {},
        "providers": {},
        "icd10": {},
        "service_codes": {},
        "service_requests": {},
        "batches": {},
    }

    patient_ids: list[str] = []
    provider_ids: list[str] = []
    icd_codes: list[str] = []
    service_codes: list[str] = []

    for patient_id in args.patient:
        add_unique(patient_ids, patient_id)

    for candidate_id in args.candidate:
        candidate = fetch_json(base_url, f"/api/duplicates/{candidate_id}")
        result["duplicates"][candidate_id] = candidate
        for patient_id in candidate.get("patient_ids", []):
            add_unique(patient_ids, patient_id)

    for referral_id in args.referral:
        referral = fetch_json(base_url, f"/api/referrals/{referral_id}")
        result["referrals"][referral_id] = referral
        add_unique(patient_ids, referral.get("patient_id"))
        add_unique(provider_ids, referral.get("receiving_provider_id"))
        add_unique(icd_codes, referral.get("diagnosis_code"))

    for batch_id in args.batch:
        all_referrals = fetch_json(base_url, "/api/referrals").get("referrals", [])
        rows = [row for row in all_referrals if row.get("batch_id") == batch_id]
        result["batches"][batch_id] = {"referrals": rows}
        for row in rows:
            add_unique(provider_ids, row.get("receiving_provider_id"))
            add_unique(icd_codes, row.get("diagnosis_code"))

    for provider_id in args.provider:
        add_unique(provider_ids, provider_id)
    for code in args.icd10:
        add_unique(icd_codes, code)
    for code in args.service_code:
        add_unique(service_codes, code)

    for service_request_id in args.service_request:
        patient_id, service_request = find_service_request(base_url, service_request_id)
        result["service_requests"][service_request_id] = {
            "patient_id": patient_id,
            "service_request": service_request,
        }
        add_unique(patient_ids, patient_id)
        if service_request:
            add_unique(provider_ids, service_request.get("requester_id"))
            add_unique(provider_ids, service_request.get("performer_id"))
            add_unique(service_codes, service_request.get("service_code"))
            for code in service_request.get("reason_codes", []):
                add_unique(icd_codes, code)

    for patient_id in patient_ids:
        result["patients"][patient_id] = collect_patient(base_url, patient_id)

    for provider_id in provider_ids:
        result["providers"][provider_id] = fetch_json(base_url, f"/api/providers/{provider_id}")

    for code in icd_codes:
        result["icd10"][code] = fetch_json(base_url, f"/api/icd10/{urllib.parse.quote(code, safe='')}")

    for code in service_codes:
        result["service_codes"][code] = fetch_json(
            base_url,
            f"/api/service-codes/{urllib.parse.quote(code, safe='')}",
        )

    if args.include_directories:
        result["directories"] = {
            "patients": fetch_json(base_url, "/api/patients"),
            "providers": fetch_json(base_url, "/api/providers"),
            "icd10": fetch_json(base_url, "/api/icd10"),
            "service_codes": fetch_json(base_url, "/api/service-codes"),
            "duplicate_candidates": fetch_json(base_url, "/api/duplicates/candidates"),
            "referrals": fetch_json(base_url, "/api/referrals"),
        }

    if args.audit_logs:
        result["audit_logs"] = fetch_json(base_url, "/api/audit-logs")

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument("--patient", action="append", default=[], help="Patient ID to collect")
    parser.add_argument("--candidate", action="append", default=[], help="Duplicate candidate ID")
    parser.add_argument("--referral", action="append", default=[], help="Referral ID")
    parser.add_argument("--service-request", action="append", default=[], help="ServiceRequest ID")
    parser.add_argument("--batch", action="append", default=[], help="Referral batch ID")
    parser.add_argument("--provider", action="append", default=[], help="Provider ID")
    parser.add_argument("--icd10", action="append", default=[], help="ICD-10 code")
    parser.add_argument("--service-code", action="append", default=[], help="Service code")
    parser.add_argument("--include-directories", action="store_true", help="Fetch directory/list endpoints")
    parser.add_argument("--audit-logs", action="store_true", help="Fetch audit logs")
    parser.add_argument("--out", help="Optional output path; defaults to stdout")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = collect(args)
    except Exception as exc:  # noqa: BLE001 - CLI should print concise failures.
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(output + "\n")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
