#!/usr/bin/env python3
"""Fetch a reusable EHR evidence bundle from the task API."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


PATIENT_CHILD_ENDPOINTS = (
    "conditions",
    "medications",
    "allergies",
    "encounters",
    "immunizations",
    "documents",
    "service-requests",
    "disclosures",
)


def unique(items):
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def get_json(base_url, path, notes):
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        notes.append({"path": path, "error": f"HTTP {exc.code}"})
    except Exception as exc:  # Keep evidence collection best-effort.
        notes.append({"path": path, "error": str(exc)})
    return None


def first_array(payload, names):
    if not isinstance(payload, dict):
        return []
    for name in names:
        value = payload.get(name)
        if isinstance(value, list):
            return value
    return []


def add_patient_from_record(record, patient_ids):
    if isinstance(record, dict) and record.get("patient_id"):
        patient_ids.append(record["patient_id"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("TASK_ENV_BASE_URL"))
    parser.add_argument("--out", default="-", help="Output JSON path, or '-' for stdout.")
    parser.add_argument("--patient", action="append", default=[], help="Patient ID to fetch.")
    parser.add_argument("--duplicate", action="append", default=[], help="Duplicate candidate ID.")
    parser.add_argument("--referral", action="append", default=[], help="Referral ID.")
    parser.add_argument("--batch", action="append", default=[], help="Referral batch ID.")
    parser.add_argument("--service-request", action="append", default=[], help="ServiceRequest ID.")
    parser.add_argument("--provider", action="append", default=[], help="Provider ID.")
    parser.add_argument("--icd", action="append", default=[], help="ICD-10 code.")
    parser.add_argument("--service-code", action="append", default=[], help="Service code.")
    args = parser.parse_args()

    if not args.base_url:
        parser.error("--base-url or TASK_ENV_BASE_URL is required")

    notes = []
    patient_ids = list(args.patient)
    provider_ids = list(args.provider)
    icd_codes = list(args.icd)
    service_codes = list(args.service_code)

    bundle = {
        "fetched_at": _dt.datetime.now(_dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "inputs": {
            "patients": unique(args.patient),
            "duplicates": unique(args.duplicate),
            "referrals": unique(args.referral),
            "batches": unique(args.batch),
            "service_requests": unique(args.service_request),
            "providers": unique(args.provider),
            "icd": unique(args.icd),
            "service_codes": unique(args.service_code),
        },
        "duplicates": {},
        "referrals": {"by_id": {}, "by_batch": {}},
        "patients": {},
        "providers": {},
        "icd10": {},
        "service_codes": {},
        "audit_logs": {"matched": []},
        "notes": notes,
    }

    for duplicate_id in unique(args.duplicate):
        payload = get_json(args.base_url, f"/api/duplicates/{duplicate_id}", notes)
        if payload:
            bundle["duplicates"][duplicate_id] = payload
            for pid in payload.get("patient_ids", []):
                patient_ids.append(pid)

    need_referral_index = bool(args.batch or args.referral)
    referral_index = []
    if need_referral_index:
        payload = get_json(args.base_url, "/api/referrals", notes)
        referral_index = first_array(payload, ("referrals",))

    for referral_id in unique(args.referral):
        payload = get_json(args.base_url, f"/api/referrals/{referral_id}", notes)
        if not payload:
            payload = next((r for r in referral_index if r.get("referral_id") == referral_id), None)
        if payload:
            bundle["referrals"]["by_id"][referral_id] = payload
            add_patient_from_record(payload, patient_ids)
            if payload.get("receiving_provider_id"):
                provider_ids.append(payload["receiving_provider_id"])
            if payload.get("diagnosis_code"):
                icd_codes.append(payload["diagnosis_code"])

    for batch_id in unique(args.batch):
        rows = [r for r in referral_index if r.get("batch_id") == batch_id]
        rows.sort(key=lambda r: r.get("referral_id", ""))
        bundle["referrals"]["by_batch"][batch_id] = rows
        for row in rows:
            add_patient_from_record(row, patient_ids)
            if row.get("receiving_provider_id"):
                provider_ids.append(row["receiving_provider_id"])
            if row.get("diagnosis_code"):
                icd_codes.append(row["diagnosis_code"])

    # If a ServiceRequest ID is supplied without patients, scan patient-scoped endpoints.
    if args.service_request and not patient_ids:
        payload = get_json(args.base_url, "/api/patients", notes)
        for patient in first_array(payload, ("patients",)):
            add_patient_from_record(patient, patient_ids)

    for patient_id in unique(patient_ids):
        patient_bundle = {}
        detail = get_json(args.base_url, f"/api/patients/{patient_id}", notes)
        if detail:
            patient_bundle["detail"] = detail
            if detail.get("primary_care_provider_id"):
                provider_ids.append(detail["primary_care_provider_id"])
        for child in PATIENT_CHILD_ENDPOINTS:
            payload = get_json(args.base_url, f"/api/patients/{patient_id}/{child}", notes)
            if payload is not None:
                patient_bundle[child] = payload
                for record in first_array(payload, (child.replace("-", "_"), child)):
                    if record.get("provider_id"):
                        provider_ids.append(record["provider_id"])
                    if record.get("recipient_provider_id"):
                        provider_ids.append(record["recipient_provider_id"])
                    if record.get("performer_id"):
                        provider_ids.append(record["performer_id"])
                    if record.get("requester_id"):
                        provider_ids.append(record["requester_id"])
                    if record.get("service_code"):
                        service_codes.append(record["service_code"])
                    for code in record.get("reason_codes", []) or []:
                        icd_codes.append(code)
                    if record.get("code"):
                        icd_codes.append(record["code"])
                    for code in record.get("diagnoses", []) or []:
                        icd_codes.append(code)
        bundle["patients"][patient_id] = patient_bundle

    requested_srs = set(args.service_request)
    if requested_srs:
        found = {}
        for patient_id, patient_bundle in bundle["patients"].items():
            rows = first_array(patient_bundle.get("service-requests"), ("service_requests",))
            for row in rows:
                sr_id = row.get("service_request_id")
                if sr_id in requested_srs:
                    found[sr_id] = row
                    add_patient_from_record(row, patient_ids)
        missing = sorted(requested_srs - set(found))
        if missing:
            notes.append({"service_requests_not_found": missing})
        bundle["service_requests"] = found

    for provider_id in unique(provider_ids):
        payload = get_json(args.base_url, f"/api/providers/{provider_id}", notes)
        if payload:
            bundle["providers"][provider_id] = payload

    for code in unique(service_codes):
        payload = get_json(args.base_url, f"/api/service-codes/{urllib.parse.quote(code)}", notes)
        if payload:
            bundle["service_codes"][code] = payload

    for code in unique(icd_codes):
        payload = get_json(args.base_url, f"/api/icd10/{urllib.parse.quote(code)}", notes)
        if payload:
            bundle["icd10"][code] = payload

    audit_payload = get_json(args.base_url, "/api/audit-logs", notes)
    audits = first_array(audit_payload, ("audit_logs",))
    patient_set = set(unique(patient_ids))
    duplicate_terms = set(args.duplicate)
    matched_audits = []
    for audit in audits:
        text = " ".join(str(audit.get(k, "")) for k in ("audit_id", "patient_id", "summary", "event"))
        if audit.get("patient_id") in patient_set or any(term in text for term in duplicate_terms):
            matched_audits.append(audit)
    bundle["audit_logs"]["matched"] = sorted(matched_audits, key=lambda a: a.get("audit_id", ""))

    data = json.dumps(bundle, indent=2, sort_keys=True)
    if args.out == "-":
        print(data)
    else:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(data + "\n")


if __name__ == "__main__":
    main()
