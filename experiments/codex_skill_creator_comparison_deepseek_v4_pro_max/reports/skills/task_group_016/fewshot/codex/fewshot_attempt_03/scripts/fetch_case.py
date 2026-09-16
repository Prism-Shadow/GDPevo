#!/usr/bin/env python3
"""
Fetch a case and its linked patient from the clinic API.

Usage:
    python fetch_case.py <base_url> <case_id>

Outputs JSON with case and patient data on stdout.
"""
import json
import sys
import urllib.request
import urllib.error


def fetch_json(url):
    """GET a JSON resource and return the parsed object."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def main():
    if len(sys.argv) != 3:
        print("Usage: fetch_case.py <base_url> <case_id>", file=sys.stderr)
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    case_id = sys.argv[2]

    case = fetch_json(f"{base_url}/api/cases/{case_id}")
    if case is None:
        print(json.dumps({"error": f"case {case_id} not found"}))
        return

    patient_id = (
        case.get("patient_id")
        or case.get("subject", {}).get("reference", "").replace("Patient/", "")
    )
    patient = (
        fetch_json(f"{base_url}/api/patients/{patient_id}")
        if patient_id else None
    )

    result = {"case": case, "patient_id": patient_id, "patient": patient}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
