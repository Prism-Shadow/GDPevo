#!/usr/bin/env python3
"""Collect common read-only EHR task evidence into one JSON object."""

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


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


def endpoint(base_url, path, query=None):
    url = base_url.rstrip("/") + path
    if query:
        url += "?" + urlencode(query)
    return url


def get_json(base_url, path, query=None, timeout=20):
    url = endpoint(base_url, path, query)
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return {"ok": True, "url": url, "data": json.loads(raw)}
    except HTTPError as exc:
        return {"ok": False, "url": url, "status": exc.code, "error": exc.reason}
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "url": url, "error": str(exc)}


def add_many(result, key, base_url, ids, path_template, timeout):
    if not ids:
        return
    result[key] = {}
    for item_id in ids:
        result[key][item_id] = get_json(base_url, path_template.format(id=item_id), timeout=timeout)


def add_patient_bundle(result, base_url, patient_ids, timeout):
    if not patient_ids:
        return
    result["patients"] = {}
    for patient_id in patient_ids:
        bundle = {"detail": get_json(base_url, f"/api/patients/{patient_id}", timeout=timeout)}
        for subresource in PATIENT_SUBRESOURCES:
            bundle[subresource] = get_json(
                base_url,
                f"/api/patients/{patient_id}/{subresource}",
                timeout=timeout,
            )
        result["patients"][patient_id] = bundle


def add_referral_batch(result, base_url, batch_ids, timeout):
    if not batch_ids:
        return
    result["referral_batches"] = {}
    for batch_id in batch_ids:
        queried = get_json(base_url, "/api/referrals", {"batch_id": batch_id}, timeout=timeout)
        result["referral_batches"][batch_id] = queried


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("TASK_ENV_BASE_URL"))
    parser.add_argument("--patient-id", action="append", default=[])
    parser.add_argument("--duplicate-id", action="append", default=[])
    parser.add_argument("--referral-id", action="append", default=[])
    parser.add_argument("--batch-id", action="append", default=[])
    parser.add_argument("--provider-id", action="append", default=[])
    parser.add_argument("--icd-code", action="append", default=[])
    parser.add_argument("--service-code", action="append", default=[])
    parser.add_argument("--include-audit-logs", action="store_true")
    parser.add_argument("--include-duplicate-list", action="store_true")
    parser.add_argument("--include-provider-list", action="store_true")
    parser.add_argument("--include-referral-list", action="store_true")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--out", help="Write JSON to this path instead of stdout")
    args = parser.parse_args()

    if not args.base_url:
        parser.error("--base-url or TASK_ENV_BASE_URL is required")

    result = {"base_url": args.base_url.rstrip("/")}
    add_patient_bundle(result, args.base_url, args.patient_id, args.timeout)
    add_many(result, "duplicates", args.base_url, args.duplicate_id, "/api/duplicates/{id}", args.timeout)
    add_many(result, "referrals", args.base_url, args.referral_id, "/api/referrals/{id}", args.timeout)
    add_referral_batch(result, args.base_url, args.batch_id, args.timeout)
    add_many(result, "providers", args.base_url, args.provider_id, "/api/providers/{id}", args.timeout)
    add_many(result, "icd10", args.base_url, args.icd_code, "/api/icd10/{id}", args.timeout)
    add_many(result, "service_codes", args.base_url, args.service_code, "/api/service-codes/{id}", args.timeout)

    if args.include_audit_logs:
        result["audit_logs"] = get_json(args.base_url, "/api/audit-logs", timeout=args.timeout)
    if args.include_duplicate_list:
        result["duplicate_candidates"] = get_json(args.base_url, "/api/duplicates/candidates", timeout=args.timeout)
    if args.include_provider_list:
        result["provider_list"] = get_json(args.base_url, "/api/providers", timeout=args.timeout)
    if args.include_referral_list:
        result["referral_list"] = get_json(args.base_url, "/api/referrals", timeout=args.timeout)

    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(output)
    else:
        sys.stdout.write(output)


if __name__ == "__main__":
    main()
