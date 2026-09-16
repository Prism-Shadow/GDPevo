#!/usr/bin/env python3
"""Collect case-scoped evidence from a Harborview Synthetic Clinic runtime."""

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
    "observations": "/api/observations",
    "medications": "/api/medications",
    "allergies": "/api/allergies",
    "problems": "/api/problems",
    "imaging": "/api/imaging",
    "care_registry": "/api/care-registry",
    "sdoh": "/api/sdoh",
}


def parse_env_access(path: Path) -> tuple[str, str | None, str | None]:
    text = path.read_text(encoding="utf-8")
    base_match = re.search(r"Base URL:\s*(\S+)", text)
    header_match = re.search(r"Header:\s*([A-Za-z0-9_-]+)", text)
    value_match = re.search(r"Value:\s*(\S+)", text)
    if not base_match:
        raise ValueError(f"Could not find Base URL in {path}")
    return (
        base_match.group(1).rstrip("/"),
        header_match.group(1) if header_match else None,
        value_match.group(1) if value_match else None,
    )


def get_json(base_url: str, path: str, header_name: str | None, token: str | None) -> Any:
    url = urllib.parse.urljoin(base_url + "/", path.lstrip("/"))
    headers = {"Accept": "application/json"}
    if header_name and token:
        headers[header_name] = token
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {url} failed: {exc.code} {detail}") from exc


def collection_items(payload: Any) -> list[Any]:
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]
    if isinstance(payload, list):
        return payload
    return []


def mentions_identifier(item: Any, identifiers: set[str]) -> bool:
    text = json.dumps(item, sort_keys=True, separators=(",", ":"))
    return any(identifier and identifier in text for identifier in identifiers)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", required=True, type=Path, help="Path to environment_access.md")
    parser.add_argument("--case-id", required=True, help="Target case identifier")
    parser.add_argument("--out", required=True, type=Path, help="Output JSON path")
    parser.add_argument(
        "--include-full-collections",
        action="store_true",
        help="Also include unfiltered collection payloads for manual review",
    )
    args = parser.parse_args()

    base_url, header_name, token = parse_env_access(args.env)

    result: dict[str, Any] = {
        "case_id": args.case_id,
        "base_url": base_url,
        "health": get_json(base_url, "/health", header_name, token),
    }

    case = get_json(base_url, f"/api/cases/{urllib.parse.quote(args.case_id)}", header_name, token)
    result["case"] = case
    patient_id = case.get("patient_id") if isinstance(case, dict) else None
    result["patient_id"] = patient_id
    identifiers = {args.case_id}
    if patient_id:
        identifiers.add(str(patient_id))
        result["patient"] = get_json(
            base_url,
            f"/api/patients/{urllib.parse.quote(str(patient_id))}",
            header_name,
            token,
        )

    related: dict[str, list[Any]] = {}
    full: dict[str, Any] = {}
    for name, endpoint in COLLECTION_ENDPOINTS.items():
        payload = get_json(base_url, endpoint, header_name, token)
        items = collection_items(payload)
        related[name] = [item for item in items if mentions_identifier(item, identifiers)]
        if args.include_full_collections:
            full[name] = payload
    result["related"] = related
    if full:
        result["full_collections"] = full

    protocols_index = get_json(base_url, "/api/protocols", header_name, token)
    protocol_details = []
    for protocol in collection_items(protocols_index):
        protocol_id = protocol.get("protocol_id") if isinstance(protocol, dict) else None
        if protocol_id:
            protocol_details.append(
                get_json(
                    base_url,
                    f"/api/protocols/{urllib.parse.quote(str(protocol_id))}",
                    header_name,
                    token,
                )
            )
    result["protocols"] = {
        "index": protocols_index,
        "details": protocol_details,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
