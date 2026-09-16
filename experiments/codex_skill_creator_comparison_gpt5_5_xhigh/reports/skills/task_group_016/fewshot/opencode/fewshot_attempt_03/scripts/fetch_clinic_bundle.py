#!/usr/bin/env python3
"""Fetch read-only synthetic clinic API resources for a target case.

The script intentionally uses only Python's standard library. It writes raw JSON
responses so the solver can inspect source data without repeatedly retyping curl
commands. It does not mutate the runtime and does not call POST endpoints.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


COLLECTION_ENDPOINTS = [
    "patients",
    "cases",
    "observations",
    "medications",
    "allergies",
    "problems",
    "imaging",
    "care-registry",
    "sdoh",
    "protocols",
]


def get_json(base_url: str, path: str) -> tuple[int | None, Any]:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    req = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
            if not body.strip():
                return response.status, None
            return response.status, json.loads(body)
    except HTTPError as exc:
        try:
            payload = exc.read().decode("utf-8")
            parsed: Any = json.loads(payload) if payload.strip() else payload
        except Exception:
            parsed = str(exc)
        return exc.code, {"error": parsed}
    except (URLError, TimeoutError) as exc:
        return None, {"error": str(exc)}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def walk_strings(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            found.extend(walk_strings(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(walk_strings(item))
    elif isinstance(value, str):
        found.append(value)
    return found


def infer_patient_id(case_payload: Any) -> str | None:
    preferred_keys = {"patient_id", "patientId", "patient", "subject_id", "subjectId", "subject"}
    if isinstance(case_payload, dict):
        stack: list[Any] = [case_payload]
        while stack:
            current = stack.pop()
            if isinstance(current, dict):
                for key, value in current.items():
                    if key in preferred_keys and isinstance(value, str) and value:
                        match = re.search(r"PAT[-A-Za-z0-9]+", value)
                        return match.group(0) if match else value
                    stack.append(value)
            elif isinstance(current, list):
                stack.extend(current)
    for text in walk_strings(case_payload):
        match = re.search(r"PAT[-A-Za-z0-9]+", text)
        if match:
            return match.group(0)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch standard synthetic clinic GET endpoints.")
    parser.add_argument("--base-url", required=True, help="Runtime base URL, for example http://task-env:9016/")
    parser.add_argument("--case-id", help="Target case id from the prompt.")
    parser.add_argument("--patient-id", help="Known patient id. If omitted, inferred from case payload when possible.")
    parser.add_argument("--out-dir", default="clinic_bundle", help="Directory for fetched JSON files.")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    index: dict[str, Any] = {"base_url": args.base_url, "case_id": args.case_id, "patient_id": args.patient_id, "files": {}}

    if args.case_id:
        status, payload = get_json(args.base_url, f"api/cases/{args.case_id}")
        write_json(out_dir / "case.json", {"status": status, "payload": payload})
        index["files"]["case"] = "case.json"
        if not args.patient_id:
            args.patient_id = infer_patient_id(payload)
            index["patient_id"] = args.patient_id

    if args.patient_id:
        status, payload = get_json(args.base_url, f"api/patients/{args.patient_id}")
        write_json(out_dir / "patient.json", {"status": status, "payload": payload})
        index["files"]["patient"] = "patient.json"

    for endpoint in COLLECTION_ENDPOINTS:
        status, payload = get_json(args.base_url, f"api/{endpoint}")
        file_name = f"{endpoint.replace('-', '_')}.json"
        write_json(out_dir / file_name, {"status": status, "payload": payload})
        index["files"][endpoint] = file_name

    write_json(out_dir / "index.json", index)
    print(json.dumps(index, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
