#!/usr/bin/env python3
"""Fetch a synthetic clinic case bundle and protocol records.

This helper is intentionally generic. It does not embed any training case,
patient, observation, or answer values.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


LIST_ENDPOINTS = (
    "patients",
    "observations",
    "medications",
    "allergies",
    "problems",
    "imaging",
    "care-registry",
    "sdoh",
)


def read_base_url(env_path: str | None) -> str | None:
    if not env_path:
        return None
    with open(env_path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped.startswith("base_url:"):
                return stripped.split(":", 1)[1].strip()
    return None


def urljoin(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def get_json(base_url: str, path: str) -> Any:
    url = urljoin(base_url, path)
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {url} failed with HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GET {url} failed: {exc}") from exc


def items_from_payload(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if isinstance(payload.get("items"), list):
            return payload["items"]
        for value in payload.values():
            if isinstance(value, list):
                return value
    return []


def find_case_in_list(payload: Any, case_id: str) -> dict[str, Any]:
    for item in items_from_payload(payload):
        if isinstance(item, dict) and item.get("case_id") == case_id:
            return item
    raise RuntimeError(f"case_id {case_id!r} was not found in /api/cases")


def get_case_bundle(base_url: str, case_id: str) -> dict[str, Any]:
    quoted = urllib.parse.quote(case_id, safe="")
    try:
        payload = get_json(base_url, f"/api/cases/{quoted}")
        if isinstance(payload, dict):
            return payload
        raise RuntimeError(f"/api/cases/{case_id} did not return a JSON object")
    except RuntimeError:
        cases = get_json(base_url, "/api/cases")
        return {"case": find_case_in_list(cases, case_id)}


def patient_id_from_bundle(bundle: dict[str, Any]) -> str | None:
    case = bundle.get("case")
    if isinstance(case, dict) and isinstance(case.get("patient_id"), str):
        return case["patient_id"]
    if isinstance(bundle.get("patient_id"), str):
        return bundle["patient_id"]
    return None


def related_record(record: Any, case_id: str, patient_id: str | None) -> bool:
    if not isinstance(record, dict):
        return False
    if record.get("case_id") == case_id:
        return True
    if patient_id and record.get("patient_id") == patient_id:
        return True
    return False


def enrich_from_list_endpoints(base_url: str, bundle: dict[str, Any], case_id: str) -> None:
    patient_id = patient_id_from_bundle(bundle)
    for endpoint in LIST_ENDPOINTS:
        key = endpoint.replace("-", "_")
        if key in bundle and bundle[key] not in (None, [], {}):
            continue
        try:
            payload = get_json(base_url, f"/api/{endpoint}")
        except RuntimeError as exc:
            bundle.setdefault("_fetch_warnings", []).append(str(exc))
            continue
        related = [item for item in items_from_payload(payload) if related_record(item, case_id, patient_id)]
        if endpoint == "patients":
            if related and "patient" not in bundle:
                bundle["patient"] = related[0]
        elif endpoint == "care-registry":
            bundle[key] = related[0] if related else None
        else:
            bundle[key] = related


def fetch_protocols(base_url: str) -> list[dict[str, Any]]:
    try:
        listing = get_json(base_url, "/api/protocols")
    except RuntimeError as exc:
        return [{"_fetch_error": str(exc)}]

    protocols: list[dict[str, Any]] = []
    for item in items_from_payload(listing):
        if not isinstance(item, dict):
            continue
        protocol_id = item.get("protocol_id")
        if not isinstance(protocol_id, str):
            protocols.append(item)
            continue
        try:
            detail = get_json(base_url, f"/api/protocols/{urllib.parse.quote(protocol_id, safe='')}")
            protocols.append(detail if isinstance(detail, dict) else item)
        except RuntimeError as exc:
            fallback = dict(item)
            fallback["_fetch_error"] = str(exc)
            protocols.append(fallback)
    return protocols


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Runtime base URL. Overrides --env.")
    parser.add_argument("--env", help="Path to environment_access.md")
    parser.add_argument("--case-id", required=True, help="Target case id")
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument(
        "--no-fallback-lists",
        action="store_true",
        help="Do not call broad list endpoints if the case endpoint is sparse.",
    )
    args = parser.parse_args()

    base_url = args.base_url or read_base_url(args.env)
    if not base_url:
        parser.error("provide --base-url or an --env file containing base_url")

    bundle = get_case_bundle(base_url, args.case_id)
    if not args.no_fallback_lists:
        enrich_from_list_endpoints(base_url, bundle, args.case_id)

    output = {
        "source": {
            "base_url": base_url,
            "case_id": args.case_id,
        },
        "case_bundle": bundle,
        "protocols": fetch_protocols(base_url),
    }

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
