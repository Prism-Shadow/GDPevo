#!/usr/bin/env python3
"""Collect read-only context from the synthetic clinic runtime."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


COLLECTION_ENDPOINTS = {
    "patients": "/api/patients",
    "cases": "/api/cases",
    "observations": "/api/observations",
    "medications": "/api/medications",
    "allergies": "/api/allergies",
    "problems": "/api/problems",
    "imaging": "/api/imaging",
    "care_registry": "/api/care-registry",
    "sdoh": "/api/sdoh",
}


def read_access_base_url(path: str | None) -> str | None:
    if not path:
        return None
    access_path = Path(path)
    if not access_path.exists():
        return None
    for line in access_path.read_text().splitlines():
        match = re.match(r"\s*base_url:\s*(\S+)\s*$", line)
        if match:
            return match.group(1)
    return None


def fetch_json(base_url: str, path: str) -> Any:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def iter_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [payload]
    return []


def extract_patient_id(case_payload: Any) -> str | None:
    if not isinstance(case_payload, dict):
        return None
    candidates = [case_payload]
    for key in ("case", "patient"):
        value = case_payload.get(key)
        if isinstance(value, dict):
            candidates.append(value)
    for candidate in candidates:
        patient_id = candidate.get("patient_id")
        if isinstance(patient_id, str) and patient_id:
            return patient_id
    return None


def related_records(payload: Any, case_id: str, patient_id: str | None) -> list[dict[str, Any]]:
    records = []
    for record in iter_records(payload):
        if record.get("case_id") == case_id:
            records.append(record)
            continue
        if patient_id and record.get("patient_id") == patient_id:
            records.append(record)
    return records


def token_set(*values: Any) -> set[str]:
    text = " ".join(json.dumps(value, sort_keys=True) for value in values if value is not None)
    tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
    return {token for token in tokens if len(token) > 2}


def score_protocol(protocol: dict[str, Any], context_tokens: set[str]) -> int:
    protocol_tokens = token_set(protocol)
    return len(context_tokens & protocol_tokens)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Clinic runtime base URL")
    parser.add_argument("--access-file", default="environment_access.md", help="File containing base_url")
    parser.add_argument("--case-id", required=True, help="Target case identifier")
    parser.add_argument("--prompt", help="Optional prompt file to improve protocol scoring")
    parser.add_argument("--out", help="Write JSON context to this path instead of stdout")
    args = parser.parse_args()

    base_url = args.base_url or read_access_base_url(args.access_file)
    if not base_url:
        print("Missing --base-url and no base_url found in access file.", file=sys.stderr)
        return 2

    prompt_text = Path(args.prompt).read_text() if args.prompt else ""
    errors: dict[str, str] = {}

    try:
        case_bundle = fetch_json(base_url, f"/api/cases/{urllib.parse.quote(args.case_id)}")
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"Could not fetch case {args.case_id}: {exc}", file=sys.stderr)
        return 1

    patient_id = extract_patient_id(case_bundle)
    collections: dict[str, Any] = {}
    for name, path in COLLECTION_ENDPOINTS.items():
        try:
            payload = fetch_json(base_url, path)
            collections[name] = related_records(payload, args.case_id, patient_id)
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            errors[name] = str(exc)

    protocols_index: Any = None
    protocols: list[dict[str, Any]] = []
    try:
        protocols_index = fetch_json(base_url, "/api/protocols")
        for item in iter_records(protocols_index):
            protocol_id = item.get("protocol_id")
            if not isinstance(protocol_id, str) or not protocol_id:
                continue
            try:
                protocol = fetch_json(base_url, f"/api/protocols/{urllib.parse.quote(protocol_id)}")
                protocols.append(protocol)
            except (urllib.error.URLError, json.JSONDecodeError) as exc:
                errors[f"protocol:{protocol_id}"] = str(exc)
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        errors["protocols"] = str(exc)

    context_tokens = token_set(prompt_text, case_bundle)
    protocols.sort(key=lambda item: score_protocol(item, context_tokens), reverse=True)

    output = {
        "case_id": args.case_id,
        "patient_id": patient_id,
        "case_bundle": case_bundle,
        "related_collections": collections,
        "protocols_index": protocols_index,
        "protocols_scored_best_first": protocols,
        "fetch_errors": errors,
    }

    rendered = json.dumps(output, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(rendered + "\n")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
