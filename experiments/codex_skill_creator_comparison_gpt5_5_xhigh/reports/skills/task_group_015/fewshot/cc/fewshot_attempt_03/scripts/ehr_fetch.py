#!/usr/bin/env python3
"""Collect read-only EHR task-environment evidence into one JSON bundle."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
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


def get_json(base_url: str, path: str) -> Any:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"error": exc.reason, "status": exc.code, "path": path}
    except urllib.error.URLError as exc:
        return {"error": str(exc.reason), "path": path}


def split_values(values: list[str] | None) -> list[str]:
    if not values:
        return []
    out: list[str] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                out.append(part)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--patients", nargs="*", help="Patient IDs, comma-separated or space-separated")
    parser.add_argument("--duplicates", nargs="*", help="Duplicate candidate IDs")
    parser.add_argument("--referrals", nargs="*", help="Referral IDs")
    parser.add_argument("--batch", nargs="*", help="Referral batch IDs to collect from /api/referrals")
    parser.add_argument("--providers", nargs="*", help="Provider IDs")
    parser.add_argument("--icd10", nargs="*", help="ICD-10 codes")
    parser.add_argument("--service-codes", nargs="*", help="Service code IDs")
    parser.add_argument("--audit-logs", action="store_true")
    parser.add_argument("--directories", action="store_true", help="Fetch provider, ICD-10, and service-code directories")
    parser.add_argument(
        "--patient-subresources",
        nargs="*",
        default=[],
        help="Patient subresources to fetch, or 'all'",
    )
    args = parser.parse_args()

    patient_ids = split_values(args.patients)
    duplicate_ids = split_values(args.duplicates)
    referral_ids = split_values(args.referrals)
    batch_ids = set(split_values(args.batch))
    provider_ids = split_values(args.providers)
    icd_codes = split_values(args.icd10)
    service_codes = split_values(args.service_codes)

    requested_subresources = split_values(args.patient_subresources)
    if "all" in requested_subresources:
        requested_subresources = list(PATIENT_SUBRESOURCES)
    requested_subresources = [s for s in requested_subresources if s in PATIENT_SUBRESOURCES]

    bundle: dict[str, Any] = {
        "base_url": args.base_url,
        "patients": {},
        "duplicates": {},
        "referrals": {},
        "referral_batches": {},
        "providers": {},
        "icd10": {},
        "service_codes": {},
    }

    for patient_id in patient_ids:
        patient_bundle: dict[str, Any] = {"detail": get_json(args.base_url, f"/api/patients/{patient_id}")}
        for subresource in requested_subresources:
            patient_bundle[subresource] = get_json(
                args.base_url,
                f"/api/patients/{patient_id}/{subresource}",
            )
        bundle["patients"][patient_id] = patient_bundle

    for candidate_id in duplicate_ids:
        bundle["duplicates"][candidate_id] = get_json(args.base_url, f"/api/duplicates/{candidate_id}")

    for referral_id in referral_ids:
        bundle["referrals"][referral_id] = get_json(args.base_url, f"/api/referrals/{referral_id}")

    if batch_ids:
        referrals_payload = get_json(args.base_url, "/api/referrals")
        referrals = referrals_payload.get("referrals", []) if isinstance(referrals_payload, dict) else []
        for batch_id in sorted(batch_ids):
            bundle["referral_batches"][batch_id] = [
                row for row in referrals if row.get("batch_id") == batch_id
            ]

    for provider_id in provider_ids:
        bundle["providers"][provider_id] = get_json(args.base_url, f"/api/providers/{provider_id}")

    for code in icd_codes:
        bundle["icd10"][code] = get_json(args.base_url, f"/api/icd10/{urllib.parse.quote(code)}")

    for code in service_codes:
        bundle["service_codes"][code] = get_json(
            args.base_url,
            f"/api/service-codes/{urllib.parse.quote(code)}",
        )

    if args.directories:
        bundle["provider_directory"] = get_json(args.base_url, "/api/providers")
        bundle["icd10_directory"] = get_json(args.base_url, "/api/icd10")
        bundle["service_code_directory"] = get_json(args.base_url, "/api/service-codes")

    if args.audit_logs:
        bundle["audit_logs"] = get_json(args.base_url, "/api/audit-logs")

    json.dump(bundle, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
