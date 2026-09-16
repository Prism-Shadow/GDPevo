#!/usr/bin/env python3
"""Fetch read-only EHR quality-governance evidence into one JSON bundle."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from pathlib import Path
from typing import Any


PATIENT_SUBRESOURCES = (
    "conditions",
    "medications",
    "allergies",
    "encounters",
    "immunizations",
    "documents",
    "service-requests",
    "disclosures",
)


def api_get(base_url: str, path: str, params: dict[str, str] | None = None) -> Any:
    base = base_url.rstrip("/") + "/"
    url = urllib.parse.urljoin(base, path.lstrip("/"))
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return {"_error": f"HTTP {exc.code}", "_path": path}
    except urllib.error.URLError as exc:
        return {"_error": str(exc.reason), "_path": path}
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_error": "non-json response", "_path": path, "_text": text}


def values(obj: Any) -> Iterable[Any]:
    if isinstance(obj, dict):
        yield obj
        for item in obj.values():
            yield from values(item)
    elif isinstance(obj, list):
        for item in obj:
            yield from values(item)


def list_from_response(data: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get(key), list):
        return [x for x in data[key] if isinstance(x, dict)]
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


def add_if_string(items: set[str], value: Any) -> None:
    if isinstance(value, str) and value:
        items.add(value)


def collect_codes(bundle: dict[str, Any]) -> set[str]:
    codes: set[str] = set()
    code_keys = {"code", "diagnosis_code", "primary_code"}
    list_code_keys = {"diagnoses", "diagnosis_codes", "reason_codes", "supporting_codes"}
    for obj in values(bundle):
        if not isinstance(obj, dict):
            continue
        for key in code_keys:
            add_if_string(codes, obj.get(key))
        for key in list_code_keys:
            val = obj.get(key)
            if isinstance(val, list):
                for item in val:
                    add_if_string(codes, item)
    return codes


def collect_provider_ids(bundle: dict[str, Any]) -> set[str]:
    provider_ids: set[str] = set()
    keys = {
        "provider_id",
        "primary_care_provider_id",
        "receiving_provider_id",
        "requester_id",
        "requester_provider_id",
        "performer_id",
        "performer_provider_id",
        "recipient_provider_id",
    }
    for obj in values(bundle):
        if isinstance(obj, dict):
            for key in keys:
                add_if_string(provider_ids, obj.get(key))
    return provider_ids


def collect_patient_ids(bundle: dict[str, Any]) -> set[str]:
    patient_ids: set[str] = set()
    for obj in values(bundle):
        if not isinstance(obj, dict):
            continue
        add_if_string(patient_ids, obj.get("patient_id"))
        ids = obj.get("patient_ids")
        if isinstance(ids, list):
            for item in ids:
                add_if_string(patient_ids, item)
    return patient_ids


def collect_service_codes(bundle: dict[str, Any]) -> set[str]:
    service_codes: set[str] = set()
    for obj in values(bundle):
        if isinstance(obj, dict):
            add_if_string(service_codes, obj.get("service_code"))
    return service_codes


def fetch_patient_bundle(base_url: str, patient_id: str) -> dict[str, Any]:
    patient: dict[str, Any] = {"detail": api_get(base_url, f"/api/patients/{patient_id}")}
    for resource in PATIENT_SUBRESOURCES:
        patient[resource] = api_get(base_url, f"/api/patients/{patient_id}/{resource}")
    return patient


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("TASK_ENV_BASE_URL"))
    parser.add_argument("--patient", action="append", default=[])
    parser.add_argument("--candidate", action="append", default=[])
    parser.add_argument("--referral", action="append", default=[])
    parser.add_argument("--provider", action="append", default=[])
    parser.add_argument("--icd10", action="append", default=[])
    parser.add_argument("--service-code", action="append", default=[])
    parser.add_argument("--service-request", action="append", default=[])
    parser.add_argument("--batch")
    parser.add_argument("--audit-logs", action="store_true")
    parser.add_argument("--out", help="Write bundle to this file instead of stdout")
    args = parser.parse_args()

    if not args.base_url:
        print("Provide --base-url or set TASK_ENV_BASE_URL", file=sys.stderr)
        return 2

    bundle: dict[str, Any] = {
        "duplicates": {},
        "referrals": {},
        "batches": {},
        "patients": {},
        "providers": {},
        "icd10": {},
        "service_codes": {},
        "service_requests": {},
    }

    for candidate_id in sorted(set(args.candidate)):
        bundle["duplicates"][candidate_id] = api_get(
            args.base_url, f"/api/duplicates/{candidate_id}"
        )

    for referral_id in sorted(set(args.referral)):
        bundle["referrals"][referral_id] = api_get(
            args.base_url, f"/api/referrals/{referral_id}"
        )

    if args.batch:
        data = api_get(args.base_url, "/api/referrals", {"batch_id": args.batch})
        rows = list_from_response(data, "referrals")
        if rows and any("batch_id" in r for r in rows):
            rows = [r for r in rows if r.get("batch_id") == args.batch]
        bundle["batches"][args.batch] = {
            "referrals": rows,
            "referral_count": len(rows),
        }

    for patient_id in sorted(set(args.patient) | collect_patient_ids(bundle)):
        bundle["patients"][patient_id] = fetch_patient_bundle(args.base_url, patient_id)

    for sr_id in sorted(set(args.service_request)):
        found = []
        for patient_id, patient_bundle in bundle["patients"].items():
            rows = list_from_response(patient_bundle.get("service-requests"), "service_requests")
            found.extend(
                dict(row, _patient_bundle_id=patient_id)
                for row in rows
                if row.get("service_request_id") == sr_id
            )
        bundle["service_requests"][sr_id] = found

    provider_ids = set(args.provider) | collect_provider_ids(bundle)
    for provider_id in sorted(provider_ids):
        bundle["providers"][provider_id] = api_get(
            args.base_url, f"/api/providers/{provider_id}"
        )

    codes = set(args.icd10) | collect_codes(bundle)
    for code in sorted(codes):
        bundle["icd10"][code] = api_get(args.base_url, f"/api/icd10/{code}")

    service_codes = set(args.service_code) | collect_service_codes(bundle)
    for code in sorted(service_codes):
        bundle["service_codes"][code] = api_get(
            args.base_url, f"/api/service-codes/{urllib.parse.quote(code, safe='')}"
        )

    if args.audit_logs:
        bundle["audit_logs"] = api_get(args.base_url, "/api/audit-logs")

    text = json.dumps(bundle, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
