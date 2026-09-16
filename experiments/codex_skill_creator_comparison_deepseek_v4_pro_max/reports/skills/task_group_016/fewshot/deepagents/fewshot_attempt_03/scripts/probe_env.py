#!/usr/bin/env python3
"""Probe the clinic runtime API for a case and its associated clinical data.

Usage:
  python3 scripts/probe_env.py <base_url> <case_id>

Dumps to stdout: case, patient, observations, medications, allergies, problems,
imaging, care-registry, sdoh, and protocol references. Use this for a fast
overview before making structured clinical decisions.
"""

import json
import sys
import urllib.request
import urllib.error


def get(url: str) -> dict | list:
    """GET a JSON endpoint and return the parsed body."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def post(url: str, body: dict) -> dict | list:
    """POST a JSON body and return the parsed response."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 scripts/probe_env.py <base_url> <case_id>", file=sys.stderr)
        sys.exit(1)

    base = sys.argv[1].rstrip("/")
    case_id = sys.argv[2]

    # 1. Case
    print("=== CASE ===")
    case = get(f"{base}/api/cases/{case_id}")
    print(json.dumps(case, indent=2))
    patient_id = case.get("patientId") or case.get("patient_id")

    if not patient_id:
        print("ERROR: could not determine patientId from case", file=sys.stderr)
        sys.exit(1)

    print(f"\nPatient ID: {patient_id}")

    # 2. Patient
    print("=== PATIENT ===")
    patient = None
    try:
        patient = get(f"{base}/api/patients/{patient_id}")
    except urllib.error.HTTPError:
        # Fall back to listing all patients and filtering
        patients = get(f"{base}/api/patients")
        patient = next((p for p in patients if p.get("id") == patient_id), None)
    if patient:
        print(json.dumps(patient, indent=2))
    else:
        print("(not found)")

    # 3. Observations
    print("=== OBSERVATIONS ===")
    try:
        # Try POST query first for patient-scoped results
        obs = post(f"{base}/api/query", {"patientId": patient_id, "resourceType": "Observation"})
    except urllib.error.HTTPError:
        obs = get(f"{base}/api/observations")
        obs = [o for o in obs if o.get("patientId") == patient_id]
    for o in obs:
        print(json.dumps(o, indent=2))
    if not obs:
        print("(none)")

    # 4. Medications
    print("=== MEDICATIONS ===")
    try:
        meds = post(f"{base}/api/query", {"patientId": patient_id, "resourceType": "Medication"})
    except urllib.error.HTTPError:
        meds = get(f"{base}/api/medications")
        meds = [m for m in meds if m.get("patientId") == patient_id]
    for m in meds:
        print(json.dumps(m, indent=2))
    if not meds:
        print("(none)")

    # 5. Allergies
    print("=== ALLERGIES ===")
    try:
        algs = post(f"{base}/api/query", {"patientId": patient_id, "resourceType": "Allergy"})
    except urllib.error.HTTPError:
        algs = get(f"{base}/api/allergies")
        algs = [a for a in algs if a.get("patientId") == patient_id]
    for a in algs:
        print(json.dumps(a, indent=2))
    if not algs:
        print("(none)")

    # 6. Problems
    print("=== PROBLEMS ===")
    try:
        probs = post(f"{base}/api/query", {"patientId": patient_id, "resourceType": "Problem"})
    except urllib.error.HTTPError:
        probs = get(f"{base}/api/problems")
        probs = [p for p in probs if p.get("patientId") == patient_id]
    for p in probs:
        print(json.dumps(p, indent=2))
    if not probs:
        print("(none)")

    # 7. Imaging
    print("=== IMAGING ===")
    try:
        imgs = post(f"{base}/api/query", {"patientId": patient_id, "resourceType": "Imaging"})
    except urllib.error.HTTPError:
        imgs = get(f"{base}/api/imaging")
        imgs = [i for i in imgs if i.get("patientId") == patient_id]
    for i in imgs:
        print(json.dumps(i, indent=2))
    if not imgs:
        print("(none)")

    # 8. Care Registry
    print("=== CARE REGISTRY ===")
    try:
        reg = post(f"{base}/api/query", {"patientId": patient_id, "resourceType": "CareRegistry"})
    except urllib.error.HTTPError:
        reg = get(f"{base}/api/care-registry")
        reg = [r for r in reg if r.get("patientId") == patient_id]
    for r in reg:
        print(json.dumps(r, indent=2))
    if not reg:
        print("(none)")

    # 9. SDOH
    print("=== SDOH ===")
    try:
        sdoh = post(f"{base}/api/query", {"patientId": patient_id, "resourceType": "SDOH"})
    except urllib.error.HTTPError:
        sdoh = get(f"{base}/api/sdoh")
        sdoh = [s for s in sdoh if s.get("patientId") == patient_id]
    for s in sdoh:
        print(json.dumps(s, indent=2))
    if not sdoh:
        print("(none)")

    # 10. Protocol references from the case
    print("=== PROTOCOLS ===")
    protocol_refs = case.get("protocolRefs", [])
    if not protocol_refs:
        # Try listing all
        try:
            all_protocols = get(f"{base}/api/protocols")
            for p in all_protocols:
                print(json.dumps(p, indent=2))
        except urllib.error.HTTPError:
            print("(none)")
    else:
        for pid in protocol_refs:
            try:
                proto = get(f"{base}/api/protocols/{pid}")
                print(json.dumps(proto, indent=2))
            except urllib.error.HTTPError:
                print(f"(protocol {pid} not found)")


if __name__ == "__main__":
    main()
