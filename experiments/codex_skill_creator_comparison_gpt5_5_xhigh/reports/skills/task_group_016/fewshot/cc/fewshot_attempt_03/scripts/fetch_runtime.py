#!/usr/bin/env python3
"""Fetch a read-only case bundle from a synthetic clinic runtime API."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


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


def normalize_base_url(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("base URL is empty")
    return value.rstrip("/") + "/"


def get_json(base_url: str, path: str, timeout: float) -> tuple[Any | None, dict[str, Any]]:
    url = urllib.parse.urljoin(base_url, path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            meta = {
                "url": url,
                "status": response.status,
                "elapsed_ms": round((time.time() - started) * 1000),
            }
            if not body:
                return None, meta
            return json.loads(body.decode("utf-8")), meta
    except urllib.error.HTTPError as exc:
        return None, {"url": url, "status": exc.code, "error": exc.reason}
    except Exception as exc:  # Keep going so partial bundles are still useful.
        return None, {"url": url, "error": f"{type(exc).__name__}: {exc}"}


def unwrap_records(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "results", "data", "resources", "records", "entry"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        return [payload]
    return []


def iter_strings(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, list):
        for item in value:
            found.extend(iter_strings(item))
    elif isinstance(value, dict):
        for item in value.values():
            found.extend(iter_strings(item))
    return found


def contains_identifier(value: Any, identifiers: set[str]) -> bool:
    if not identifiers:
        return False
    for text in iter_strings(value):
        for identifier in identifiers:
            if identifier and identifier in text:
                return True
    return False


def collect_patient_ids(value: Any) -> set[str]:
    patient_ids: set[str] = set()

    def walk(node: Any, key_hint: str = "") -> None:
        if isinstance(node, dict):
            for key, item in node.items():
                lowered = key.lower().replace("-", "_")
                if isinstance(item, str):
                    if lowered in {"patient_id", "patientid"} or lowered.endswith("_patient_id"):
                        patient_ids.add(item)
                    if lowered in {"patient", "subject", "patient_ref", "patient_reference"}:
                        match = re.search(r"(PAT[-A-Za-z0-9_]+)", item)
                        if match:
                            patient_ids.add(match.group(1))
                    if "patient" in lowered:
                        match = re.search(r"(PAT[-A-Za-z0-9_]+)", item)
                        if match:
                            patient_ids.add(match.group(1))
                walk(item, lowered)
        elif isinstance(node, list):
            for item in node:
                walk(item, key_hint)
        elif isinstance(node, str) and "patient" in key_hint:
            match = re.search(r"(PAT[-A-Za-z0-9_]+)", node)
            if match:
                patient_ids.add(match.group(1))

    walk(value)
    return patient_ids


def collect_protocol_ids(value: Any) -> set[str]:
    protocol_ids: set[str] = set()

    def walk(node: Any, key_hint: str = "") -> None:
        if isinstance(node, dict):
            for key, item in node.items():
                lowered = key.lower().replace("-", "_")
                if isinstance(item, str) and "protocol" in lowered:
                    protocol_ids.add(item)
                walk(item, lowered)
        elif isinstance(node, list):
            for item in node:
                walk(item, key_hint)
        elif isinstance(node, str) and "protocol" in key_hint:
            protocol_ids.add(node)

    walk(value)
    return {pid for pid in protocol_ids if pid and "/" not in pid}


def filter_records(records: list[Any], identifiers: set[str], include_all: bool) -> list[Any]:
    if include_all or not identifiers:
        return records
    return [record for record in records if contains_identifier(record, identifiers)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("TASK_ENV_BASE_URL", ""))
    parser.add_argument("--case-id", default="")
    parser.add_argument("--patient-id", default="")
    parser.add_argument("--out", default="-", help="Output path, or '-' for stdout.")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument(
        "--include-unfiltered",
        action="store_true",
        help="Store full collection records instead of only records linked to the case or patient.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        base_url = normalize_base_url(args.base_url)
    except ValueError as exc:
        print(f"fetch_runtime.py: {exc}", file=sys.stderr)
        return 2

    identifiers = {value for value in (args.case_id, args.patient_id) if value}
    bundle: dict[str, Any] = {
        "base_url": base_url,
        "target": {"case_id": args.case_id or None, "patient_id": args.patient_id or None},
        "details": {},
        "collections": {},
        "protocol_details": {},
        "diagnostics": [],
    }

    if args.case_id:
        payload, meta = get_json(base_url, f"/api/cases/{urllib.parse.quote(args.case_id)}", args.timeout)
        bundle["diagnostics"].append(meta)
        if payload is not None:
            bundle["details"]["case"] = payload
            identifiers.add(args.case_id)
            discovered = collect_patient_ids(payload)
            if discovered and not args.patient_id:
                args.patient_id = sorted(discovered)[0]
                bundle["target"]["patient_id"] = args.patient_id
            identifiers.update(discovered)

    if args.patient_id:
        payload, meta = get_json(base_url, f"/api/patients/{urllib.parse.quote(args.patient_id)}", args.timeout)
        bundle["diagnostics"].append(meta)
        if payload is not None:
            bundle["details"]["patient"] = payload
            identifiers.add(args.patient_id)

    protocol_ids: set[str] = set()
    for endpoint in COLLECTION_ENDPOINTS:
        payload, meta = get_json(base_url, f"/api/{endpoint}", args.timeout)
        bundle["diagnostics"].append(meta)
        if payload is None:
            bundle["collections"][endpoint] = {"records": [], "source": meta}
            continue
        records = unwrap_records(payload)
        include_all = args.include_unfiltered or endpoint == "protocols"
        selected = filter_records(records, identifiers, include_all)
        bundle["collections"][endpoint] = {
            "total_records_seen": len(records),
            "records": selected,
            "source": meta,
        }
        for record in selected:
            protocol_ids.update(collect_protocol_ids(record))

    if "case" in bundle["details"]:
        protocol_ids.update(collect_protocol_ids(bundle["details"]["case"]))

    for protocol_id in sorted(protocol_ids):
        payload, meta = get_json(base_url, f"/api/protocols/{urllib.parse.quote(protocol_id)}", args.timeout)
        bundle["diagnostics"].append(meta)
        if payload is not None:
            bundle["protocol_details"][protocol_id] = payload

    text = json.dumps(bundle, indent=2, sort_keys=True)
    if args.out == "-":
        print(text)
    else:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
