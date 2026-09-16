#!/usr/bin/env python3
"""Collect read-only EHR task-environment evidence as JSON."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


PATIENT_SCOPES = [
    "conditions",
    "medications",
    "allergies",
    "encounters",
    "immunizations",
    "documents",
    "disclosures",
    "service-requests",
]


def get_json(base_url: str, path: str) -> object:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"error": f"http_{exc.code}", "url": url, "body": body}
    except urllib.error.URLError as exc:
        return {"error": "url_error", "url": url, "reason": str(exc.reason)}


def by_key(items: list[object], key: str, value: str) -> list[object]:
    return [
        item
        for item in items
        if isinstance(item, dict) and str(item.get(key, "")) == value
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default=os.environ.get("TASK_ENV_BASE_URL", "http://task-env:9015/"),
    )
    parser.add_argument("--patient", action="append", default=[])
    parser.add_argument("--duplicate", action="append", default=[])
    parser.add_argument("--referral", action="append", default=[])
    parser.add_argument("--batch", action="append", default=[])
    parser.add_argument("--provider", action="append", default=[])
    parser.add_argument("--icd", action="append", default=[])
    parser.add_argument("--service-code", action="append", default=[])
    parser.add_argument(
        "--service-request",
        action="append",
        default=[],
        metavar="PATIENT_ID:SERVICE_REQUEST_ID",
    )
    parser.add_argument("--audit-logs", action="store_true")
    args = parser.parse_args()

    out: dict[str, object] = {
        "base_url": args.base_url,
        "patients": {},
        "duplicates": {},
        "referrals": {},
        "batches": {},
        "providers": {},
        "icd10": {},
        "service_codes": {},
        "service_requests": {},
    }

    for patient_id in sorted(set(args.patient)):
        patient_bundle: dict[str, object] = {
            "detail": get_json(args.base_url, f"/api/patients/{patient_id}")
        }
        for scope in PATIENT_SCOPES:
            patient_bundle[scope] = get_json(
                args.base_url, f"/api/patients/{patient_id}/{scope}"
            )
        out["patients"][patient_id] = patient_bundle

    for candidate_id in sorted(set(args.duplicate)):
        out["duplicates"][candidate_id] = get_json(
            args.base_url, f"/api/duplicates/{candidate_id}"
        )

    for referral_id in sorted(set(args.referral)):
        out["referrals"][referral_id] = get_json(
            args.base_url, f"/api/referrals/{referral_id}"
        )

    all_referrals = None
    for batch_id in sorted(set(args.batch)):
        if all_referrals is None:
            all_referrals = get_json(args.base_url, "/api/referrals")
        rows = []
        if isinstance(all_referrals, dict):
            referrals = all_referrals.get("referrals", [])
            if isinstance(referrals, list):
                rows = by_key(referrals, "batch_id", batch_id)
        out["batches"][batch_id] = {"referrals": rows}

    for provider_id in sorted(set(args.provider)):
        out["providers"][provider_id] = get_json(
            args.base_url, f"/api/providers/{provider_id}"
        )

    for code in sorted(set(args.icd)):
        out["icd10"][code] = get_json(args.base_url, f"/api/icd10/{code}")

    for code in sorted(set(args.service_code)):
        out["service_codes"][code] = get_json(
            args.base_url, f"/api/service-codes/{code}"
        )

    for spec in args.service_request:
        if ":" not in spec:
            out["service_requests"][spec] = {
                "error": "expected PATIENT_ID:SERVICE_REQUEST_ID"
            }
            continue
        patient_id, request_id = spec.split(":", 1)
        payload = get_json(args.base_url, f"/api/patients/{patient_id}/service-requests")
        matches = []
        if isinstance(payload, dict):
            requests = payload.get("service_requests", [])
            if isinstance(requests, list):
                matches = by_key(requests, "service_request_id", request_id)
        out["service_requests"][request_id] = {
            "patient_id": patient_id,
            "matches": matches,
        }

    if args.audit_logs:
        out["audit_logs"] = get_json(args.base_url, "/api/audit-logs")

    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
