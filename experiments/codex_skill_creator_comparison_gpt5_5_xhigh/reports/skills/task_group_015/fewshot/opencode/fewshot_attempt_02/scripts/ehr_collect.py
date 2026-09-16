#!/usr/bin/env python3
"""Collect reusable evidence from the read-only EHR task API.

This script does not produce final answers. It gathers endpoint evidence for the
current prompt IDs so the solver can apply the task's answer_template.json.
"""

from __future__ import annotations

import argparse
import json
import os
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


def fetch_json(base_url: str, path: str) -> Any:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        return {"_error": "http_error", "status": exc.code, "path": path}
    except urllib.error.URLError as exc:
        return {"_error": "url_error", "reason": str(exc.reason), "path": path}


def append_unique(items: list[str], value: str | None) -> None:
    if value and value not in items:
        items.append(value)


def add_patient_bundle(out: dict[str, Any], base_url: str, patient_id: str) -> None:
    if patient_id in out["patients"]:
        return
    bundle: dict[str, Any] = {"detail": fetch_json(base_url, f"/api/patients/{patient_id}")}
    for collection in PATIENT_COLLECTIONS:
        bundle[collection] = fetch_json(base_url, f"/api/patients/{patient_id}/{collection}")
    out["patients"][patient_id] = bundle


def add_provider(out: dict[str, Any], base_url: str, provider_id: str | None) -> None:
    if provider_id and provider_id not in out["providers"]:
        out["providers"][provider_id] = fetch_json(base_url, f"/api/providers/{provider_id}")


def add_icd(out: dict[str, Any], base_url: str, code: str | None) -> None:
    if code and code not in out["icd10"]:
        out["icd10"][code] = fetch_json(base_url, f"/api/icd10/{urllib.parse.quote(code)}")


def add_service_code(out: dict[str, Any], base_url: str, code: str | None) -> None:
    if code and code not in out["service_codes"]:
        out["service_codes"][code] = fetch_json(
            base_url, f"/api/service-codes/{urllib.parse.quote(code)}"
        )


def referral_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("referrals"), list):
        return [row for row in payload["referrals"] if isinstance(row, dict)]
    return []


def service_request_rows(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    payload = bundle.get("service-requests")
    if isinstance(payload, dict) and isinstance(payload.get("service_requests"), list):
        return [row for row in payload["service_requests"] if isinstance(row, dict)]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("TASK_ENV_BASE_URL"))
    parser.add_argument("--patient", action="append", default=[])
    parser.add_argument("--duplicate", action="append", default=[])
    parser.add_argument("--referral", action="append", default=[])
    parser.add_argument("--batch", action="append", default=[])
    parser.add_argument("--service-request", action="append", default=[])
    parser.add_argument("--provider", action="append", default=[])
    parser.add_argument("--icd", action="append", default=[])
    parser.add_argument("--service-code", action="append", default=[])
    parser.add_argument("--include-directory", action="store_true")
    parser.add_argument("--output", "-o")
    args = parser.parse_args()

    if not args.base_url:
        parser.error("--base-url or TASK_ENV_BASE_URL is required")

    out: dict[str, Any] = {
        "base_url": args.base_url,
        "duplicates": {},
        "referrals": {},
        "batches": {},
        "patients": {},
        "providers": {},
        "icd10": {},
        "service_codes": {},
        "audit_logs": None,
        "unresolved_service_requests": [],
    }

    patient_ids: list[str] = []
    provider_ids: list[str] = []
    icd_codes: list[str] = []
    service_codes: list[str] = []

    for patient_id in args.patient:
        append_unique(patient_ids, patient_id)

    for candidate_id in args.duplicate:
        candidate = fetch_json(args.base_url, f"/api/duplicates/{candidate_id}")
        out["duplicates"][candidate_id] = candidate
        if isinstance(candidate, dict):
            for patient_id in candidate.get("patient_ids", []) or []:
                append_unique(patient_ids, patient_id)
        out["audit_logs"] = fetch_json(args.base_url, "/api/audit-logs")

    for referral_id in args.referral:
        referral = fetch_json(args.base_url, f"/api/referrals/{referral_id}")
        out["referrals"][referral_id] = referral
        if isinstance(referral, dict):
            append_unique(patient_ids, referral.get("patient_id"))
            append_unique(provider_ids, referral.get("receiving_provider_id"))
            append_unique(icd_codes, referral.get("diagnosis_code"))

    if args.batch:
        all_referrals = fetch_json(args.base_url, "/api/referrals")
        rows = referral_rows(all_referrals)
        for batch_id in args.batch:
            batch_rows = [row for row in rows if row.get("batch_id") == batch_id]
            out["batches"][batch_id] = {"referrals": batch_rows}
            for row in batch_rows:
                append_unique(patient_ids, row.get("patient_id"))
                append_unique(provider_ids, row.get("receiving_provider_id"))
                append_unique(icd_codes, row.get("diagnosis_code"))

    for patient_id in sorted(patient_ids):
        add_patient_bundle(out, args.base_url, patient_id)
        detail = out["patients"][patient_id].get("detail")
        if isinstance(detail, dict):
            append_unique(provider_ids, detail.get("primary_care_provider_id"))
        for request in service_request_rows(out["patients"][patient_id]):
            append_unique(provider_ids, request.get("requester_id"))
            append_unique(provider_ids, request.get("performer_id"))
            add_service_code(out, args.base_url, request.get("service_code"))
            for code in request.get("reason_codes", []) or []:
                append_unique(icd_codes, code)

    for request_id in args.service_request:
        found = False
        for patient_id, bundle in out["patients"].items():
            for request in service_request_rows(bundle):
                if request.get("service_request_id") == request_id:
                    out.setdefault("service_requests", {})[request_id] = {
                        "patient_id": patient_id,
                        "record": request,
                    }
                    found = True
        if not found:
            out["unresolved_service_requests"].append(
                {
                    "service_request_id": request_id,
                    "note": "service requests are patient-scoped; pass the owning --patient ID",
                }
            )

    for provider_id in args.provider:
        append_unique(provider_ids, provider_id)
    for code in args.icd:
        append_unique(icd_codes, code)
    for code in args.service_code:
        append_unique(service_codes, code)

    for provider_id in sorted(provider_ids):
        add_provider(out, args.base_url, provider_id)
    for code in sorted(icd_codes):
        add_icd(out, args.base_url, code)
    for code in sorted(service_codes):
        add_service_code(out, args.base_url, code)

    if args.include_directory:
        out["provider_directory"] = fetch_json(args.base_url, "/api/providers")
        out["icd10_directory"] = fetch_json(args.base_url, "/api/icd10")
        out["service_code_directory"] = fetch_json(args.base_url, "/api/service-codes")

    text = json.dumps(out, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
