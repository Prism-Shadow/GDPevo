#!/usr/bin/env python3
"""Gather all evidence for one clinic case from the synthetic clinic runtime.

This is a *data-gathering convenience only*. It performs no clinical decision
logic and produces no answer — it just fetches the case bundle, the matching
protocol, and the patient-scoped observation list so you can inspect every
relevant record at once, then apply the protocol and fill answer_template.json
yourself.

Usage:
    python3 gather_case.py <BASE_URL> <CASE_ID>
    # BASE_URL comes from environment_access.md (GDPEVO_ENV_BASE_URL)

Example:
    python3 gather_case.py http://task-env:9016 CASE-RESP-102

Only GET endpoints are used; nothing is mutated.
"""
import json
import sys
import urllib.request
import urllib.error

# case_type -> protocol_id (see references/environment_api.md)
CASE_TYPE_TO_PROTOCOL = {
    "acute_respiratory": "RESP-CAP-2026",
    "pediatric_head_injury": "PEDS-HEAD-2026",
    "potassium_repletion": "K-REPLETION-2026",
    "observation_window": "OBS-WINDOW-2026",
    "care_management": "CM-HIGH-RISK-2026",
}


def get(base, path):
    url = base.rstrip("/") + path
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "url": url}
    except Exception as e:  # noqa: BLE001 - surface any transport error
        return {"_error": str(e), "url": url}


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    base, case_id = sys.argv[1], sys.argv[2]

    bundle = get(base, f"/api/cases/{case_id}")
    out = {"case_id": case_id, "bundle": bundle}

    case = bundle.get("case") if isinstance(bundle, dict) else None
    if case:
        patient_id = case.get("patient_id")
        case_type = case.get("case_type")
        out["patient_id"] = patient_id
        out["case_type"] = case_type

        protocol_id = CASE_TYPE_TO_PROTOCOL.get(case_type)
        if protocol_id:
            out["protocol_id"] = protocol_id
            out["protocol"] = get(base, f"/api/protocols/{protocol_id}")
        else:
            out["protocol_note"] = (
                f"Unknown case_type {case_type!r}; check GET /api/protocols."
            )

        if patient_id:
            # Patient-scoped observation universe, to catch cross-patient
            # distractors present in the bundle.
            out["patient_observations"] = get(
                base, f"/api/observations?patient_id={patient_id}"
            )

    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
