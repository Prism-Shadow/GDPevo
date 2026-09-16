#!/usr/bin/env python3
"""Collect EHR task evidence from the documented read-only API endpoints."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


PATIENT_SUFFIXES = [
    "",
    "/conditions",
    "/medications",
    "/allergies",
    "/encounters",
    "/immunizations",
    "/documents",
    "/service-requests",
    "/disclosures",
]


def fetch_json(base_url: str, path: str) -> Any:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {exc.code}", "url": url, "body": body}
    except Exception as exc:  # Keep evidence collection non-fatal.
        return {"error": type(exc).__name__, "url": url, "message": str(exc)}


def unique(items: list[str]) -> list[str]:
    return sorted({item for item in items if item})


def add_patient_bundle(out: dict[str, Any], base_url: str, patient_id: str) -> None:
    patient_out: dict[str, Any] = {}
    for suffix in PATIENT_SUFFIXES:
        key = "detail" if not suffix else suffix.strip("/").replace("-", "_")
        patient_out[key] = fetch_json(base_url, f"/api/patients/{patient_id}{suffix}")
    out.setdefault("patients", {})[patient_id] = patient_out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("TASK_ENV_BASE_URL", "http://task-env:9015/"),
        help="Task environment base URL.",
    )
    parser.add_argument("--patient", action="append", default=[], help="Patient ID to expand.")
    parser.add_argument("--duplicate", action="append", default=[], help="Duplicate candidate ID.")
    parser.add_argument("--referral", action="append", default=[], help="Referral ID.")
    parser.add_argument("--referral-batch", action="append", default=[], help="Referral batch ID to filter locally.")
    parser.add_argument("--provider", action="append", default=[], help="Provider ID.")
    parser.add_argument("--icd", action="append", default=[], help="ICD-10 code.")
    parser.add_argument("--service-code", action="append", default=[], help="Service code.")
    parser.add_argument("--audit-logs", action="store_true", help="Fetch audit logs for local filtering.")
    parser.add_argument("--all-referrals", action="store_true", help="Fetch referral collection without filtering.")
    parser.add_argument("--out", help="Optional path to write the collected JSON bundle.")
    args = parser.parse_args()

    out: dict[str, Any] = {"base_url": args.base_url.rstrip("/") + "/"}

    for patient_id in unique(args.patient):
        add_patient_bundle(out, args.base_url, patient_id)

    for candidate_id in unique(args.duplicate):
        out.setdefault("duplicates", {})[candidate_id] = fetch_json(args.base_url, f"/api/duplicates/{candidate_id}")

    for referral_id in unique(args.referral):
        out.setdefault("referrals", {})[referral_id] = fetch_json(args.base_url, f"/api/referrals/{referral_id}")

    if args.referral_batch or args.all_referrals:
        collection = fetch_json(args.base_url, "/api/referrals")
        out["referral_collection_raw_count"] = len(collection.get("referrals", [])) if isinstance(collection, dict) else None
        if args.referral_batch and isinstance(collection, dict):
            wanted = set(args.referral_batch)
            out["referral_batches"] = {
                batch: [row for row in collection.get("referrals", []) if row.get("batch_id") == batch]
                for batch in sorted(wanted)
            }
        else:
            out["referral_collection"] = collection

    for provider_id in unique(args.provider):
        out.setdefault("providers", {})[provider_id] = fetch_json(args.base_url, f"/api/providers/{provider_id}")

    for code in unique(args.icd):
        out.setdefault("icd10", {})[code] = fetch_json(args.base_url, f"/api/icd10/{urllib.parse.quote(code)}")

    for code in unique(args.service_code):
        out.setdefault("service_codes", {})[code] = fetch_json(
            args.base_url, f"/api/service-codes/{urllib.parse.quote(code)}"
        )

    if args.audit_logs:
        out["audit_logs"] = fetch_json(args.base_url, "/api/audit-logs")

    text = json.dumps(out, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
