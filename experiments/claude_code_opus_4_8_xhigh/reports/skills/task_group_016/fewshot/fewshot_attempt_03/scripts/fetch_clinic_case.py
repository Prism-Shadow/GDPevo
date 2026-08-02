#!/usr/bin/env python3
"""Read-only helper for clinic-protocol-cds tasks.

Pulls everything you need to answer one synthetic-clinic case into a single JSON
blob printed to stdout: the case bundle, the patient bundle, every observation
for the patient (so distractors are visible), and all protocol bodies.

It performs GETs only and never mutates the environment. `POST /api/query` is
intentionally not used (it needs a clinic token that these runs do not provide).

Usage:
    python3 fetch_clinic_case.py CASE-ID [--base URL]

The base URL defaults to the GDPEVO_ENV_BASE_URL environment variable (as given
in the run's environment-access file). Example:
    GDPEVO_ENV_BASE_URL=http://task-env:9016/ python3 fetch_clinic_case.py CASE-K-303
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

# case.case_type -> protocol_id (orientation; verify against GET /api/protocols)
CASE_TYPE_TO_PROTOCOL = {
    "acute_respiratory": "RESP-CAP-2026",
    "pediatric_head_injury": "PEDS-HEAD-2026",
    "potassium_repletion": "K-REPLETION-2026",
    "care_management": "CM-HIGH-RISK-2026",
    "observation_window": "OBS-WINDOW-2026",
}


def get(base, path, timeout=15):
    url = base.rstrip("/") + path
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        return {"_http_error": e.code, "_url": url, "_body": body}
    except Exception as e:  # noqa: BLE001 - surface any transport error
        return {"_error": str(e), "_url": url}


def main():
    ap = argparse.ArgumentParser(description="Fetch a clinic case bundle (read-only).")
    ap.add_argument("case_id", help="Target case id, e.g. CASE-RESP-102")
    ap.add_argument(
        "--base",
        default=os.environ.get("GDPEVO_ENV_BASE_URL", ""),
        help="Base URL (default: $GDPEVO_ENV_BASE_URL)",
    )
    args = ap.parse_args()

    if not args.base:
        sys.exit("No base URL. Set GDPEVO_ENV_BASE_URL or pass --base.")

    base = args.base
    bundle = get(base, "/api/cases/%s" % args.case_id)

    patient_id = None
    case_type = None
    if isinstance(bundle, dict):
        case = bundle.get("case") or {}
        patient_id = (bundle.get("patient") or {}).get("patient_id") or case.get("patient_id")
        case_type = case.get("case_type")

    out = {
        "base_url": base,
        "case_id": args.case_id,
        "case_type": case_type,
        "suggested_protocol_id": CASE_TYPE_TO_PROTOCOL.get(case_type),
        "case_bundle": bundle,
    }

    if patient_id:
        out["patient_bundle"] = get(base, "/api/patients/%s" % patient_id)
        out["patient_observations"] = get(
            base, "/api/observations?patient_id=%s" % patient_id
        )

    protocols_index = get(base, "/api/protocols")
    out["protocols_index"] = protocols_index
    protocol_bodies = {}
    items = protocols_index.get("items") if isinstance(protocols_index, dict) else None
    for item in items or []:
        pid = item.get("protocol_id")
        if pid:
            protocol_bodies[pid] = get(base, "/api/protocols/%s" % pid)
    out["protocol_bodies"] = protocol_bodies

    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
