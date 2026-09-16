#!/usr/bin/env python3
"""Collect task-local EHR API context for normalized quality packets."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


PATIENT_CHILD_ENDPOINTS = (
    "conditions",
    "medications",
    "allergies",
    "encounters",
    "immunizations",
    "documents",
    "service-requests",
    "disclosures",
)

ID_PATTERNS = {
    "patients": re.compile(r"\bP-\d+\b"),
    "providers": re.compile(r"\bPRV-[A-Z]+-\d+\b"),
    "referrals": re.compile(r"\bREF-[A-Z0-9-]+\b"),
    "duplicates": re.compile(r"\bDUP-[A-Z0-9-]+\b"),
    "service_requests": re.compile(r"\bSR-[A-Z0-9-]+\b"),
}

ICD_RE = re.compile(r"\b[A-TV-Z][0-9][0-9A-Z](?:\.[0-9A-Z]{1,4})?\b")
BATCH_HINT_RE = re.compile(r"(?:batch|batch_id)\s*[:`'\"]+\s*([A-Z]{3}\d{2}-[A-Z0-9-]+)", re.I)

def fetch_json(base_url: str, path: str) -> tuple[Any | None, str | None]:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        return None, f"{path}: HTTP {exc.code}"
    except URLError as exc:
        return None, f"{path}: {exc.reason}"
    except TimeoutError:
        return None, f"{path}: timed out"

    try:
        return json.loads(raw), None
    except json.JSONDecodeError as exc:
        return None, f"{path}: invalid JSON: {exc}"


def first_list(payload: Any, preferred_keys: tuple[str, ...] = ()) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in preferred_keys:
            value = payload.get(key)
            if isinstance(value, list):
                return value
        for value in payload.values():
            if isinstance(value, list):
                return value
    return []


def add_unique(values: set[str], item: Any) -> None:
    if isinstance(item, str) and item:
        values.add(item)


def walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def collect_ids(value: Any, collected: dict[str, set[str]]) -> None:
    text = json.dumps(value, sort_keys=True)
    for bucket, pattern in ID_PATTERNS.items():
        collected[bucket].update(pattern.findall(text))

    for obj in walk(value):
        for key, item in obj.items():
            if key in {
                "patient_id",
                "primary_patient_id",
                "possible_duplicate_patient_id",
                "merge_target_patient_id",
                "merge_source_patient_id",
                "source_patient_id",
                "target_patient_id",
            }:
                add_unique(collected["patients"], item)
            elif key == "patient_ids" and isinstance(item, list):
                for patient_id in item:
                    add_unique(collected["patients"], patient_id)
            elif key.endswith("_provider_id") or key == "provider_id":
                add_unique(collected["providers"], item)
            elif key in {"referral_id", "referral_ids"}:
                if isinstance(item, list):
                    for referral_id in item:
                        add_unique(collected["referrals"], referral_id)
                else:
                    add_unique(collected["referrals"], item)
            elif key in {"service_request_id", "service_request_ids"}:
                if isinstance(item, list):
                    for service_request_id in item:
                        add_unique(collected["service_requests"], service_request_id)
                else:
                    add_unique(collected["service_requests"], item)
            elif key in {"diagnosis_code", "primary_code", "code"} and isinstance(item, str):
                if ICD_RE.fullmatch(item):
                    collected["icd_codes"].add(item)
            elif key in {"diagnosis_codes", "reason_codes", "supporting_codes"} and isinstance(item, list):
                for code in item:
                    if isinstance(code, str) and ICD_RE.fullmatch(code):
                        collected["icd_codes"].add(code)
            elif key == "service_code" and isinstance(item, str):
                collected["service_codes"].add(item)


def read_text(path: str | None, errors: list[str]) -> str:
    if not path:
        return ""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        errors.append(f"{path}: {exc}")
        return ""


def parse_prompt(prompt_text: str, collected: dict[str, set[str]]) -> None:
    for bucket, pattern in ID_PATTERNS.items():
        collected[bucket].update(pattern.findall(prompt_text))
    for match in BATCH_HINT_RE.findall(prompt_text):
        collected["batches"].add(match)


def sorted_records(records: list[Any], key: str) -> list[Any]:
    return sorted(records, key=lambda item: str(item.get(key, "")) if isinstance(item, dict) else "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task API base URL")
    parser.add_argument("--prompt", help="Prompt file to parse for IDs")
    parser.add_argument("--template", help="Answer template to include for reference")
    parser.add_argument("--patient", action="append", default=[], help="Patient ID; repeatable")
    parser.add_argument("--provider", action="append", default=[], help="Provider ID; repeatable")
    parser.add_argument("--referral", action="append", default=[], help="Referral ID; repeatable")
    parser.add_argument("--duplicate", action="append", default=[], help="Duplicate candidate ID; repeatable")
    parser.add_argument("--service-request", action="append", default=[], help="ServiceRequest ID; repeatable")
    parser.add_argument("--batch", action="append", default=[], help="Referral batch ID; repeatable")
    parser.add_argument("--icd-code", action="append", default=[], help="ICD-10 code; repeatable")
    parser.add_argument("--service-code", action="append", default=[], help="Service code; repeatable")
    parser.add_argument("--include-audit-logs", action="store_true", help="Fetch and filter audit logs")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    collected: dict[str, set[str]] = defaultdict(set)

    prompt_text = read_text(args.prompt, errors)
    parse_prompt(prompt_text, collected)
    template_text = read_text(args.template, errors)
    template_json: Any | None = None
    if template_text:
        try:
            template_json = json.loads(template_text)
        except json.JSONDecodeError as exc:
            errors.append(f"{args.template}: invalid JSON: {exc}")

    for value, bucket in (
        (args.patient, "patients"),
        (args.provider, "providers"),
        (args.referral, "referrals"),
        (args.duplicate, "duplicates"),
        (args.service_request, "service_requests"),
        (args.batch, "batches"),
        (args.icd_code, "icd_codes"),
        (args.service_code, "service_codes"),
    ):
        collected[bucket].update(value)

    context: dict[str, Any] = {
        "source": {
            "base_url": args.base_url.rstrip("/") + "/",
            "prompt_file": args.prompt,
            "template_file": args.template,
        },
        "answer_template": template_json,
        "duplicates": {},
        "referrals": {},
        "batch_referrals": {},
        "patients": {},
        "patient_resources": {},
        "providers": {},
        "service_requests": {},
        "icd10": {},
        "service_codes": {},
        "audit_logs": [],
        "warnings": warnings,
        "errors": errors,
    }

    def remember(value: Any) -> None:
        collect_ids(value, collected)

    def get(path: str, remember_payload: bool = True) -> Any | None:
        payload, error = fetch_json(args.base_url, path)
        if error:
            errors.append(error)
            return None
        if remember_payload:
            remember(payload)
        return payload

    def fetch_duplicate(candidate_id: str) -> None:
        if candidate_id in context["duplicates"]:
            return
        payload = get(f"/api/duplicates/{candidate_id}")
        if payload is None:
            list_payload = get("/api/duplicates/candidates", remember_payload=False)
            for item in first_list(list_payload, ("duplicate_candidates", "candidates")):
                if isinstance(item, dict) and item.get("candidate_id") == candidate_id:
                    payload = item
                    remember(payload)
                    break
        if payload is not None:
            context["duplicates"][candidate_id] = payload

    def fetch_referral(referral_id: str) -> None:
        if referral_id in context["referrals"]:
            return
        payload = get(f"/api/referrals/{referral_id}")
        if payload is None:
            list_payload = get("/api/referrals", remember_payload=False)
            for item in first_list(list_payload, ("referrals",)):
                if isinstance(item, dict) and item.get("referral_id") == referral_id:
                    payload = item
                    remember(payload)
                    break
        if payload is not None:
            context["referrals"][referral_id] = payload

    def fetch_batch(batch_id: str) -> None:
        if batch_id in context["batch_referrals"]:
            return
        payload = get("/api/referrals", remember_payload=False)
        rows = [
            item
            for item in first_list(payload, ("referrals",))
            if isinstance(item, dict) and item.get("batch_id") == batch_id
        ]
        rows = sorted_records(rows, "referral_id")
        context["batch_referrals"][batch_id] = rows
        remember(rows)
        if not rows:
            warnings.append(f"No referrals found for batch {batch_id}")

    def fetch_patient(patient_id: str) -> None:
        if patient_id not in context["patients"]:
            payload = get(f"/api/patients/{patient_id}")
            if payload is not None:
                context["patients"][patient_id] = payload
        resources = context["patient_resources"].setdefault(patient_id, {})
        for child in PATIENT_CHILD_ENDPOINTS:
            if child in resources:
                continue
            payload = get(f"/api/patients/{patient_id}/{child}")
            if payload is not None:
                resources[child] = payload

    def fetch_provider(provider_id: str) -> None:
        if provider_id in context["providers"]:
            return
        payload = get(f"/api/providers/{provider_id}")
        if payload is not None:
            context["providers"][provider_id] = payload

    def fetch_icd10(code: str) -> None:
        if code in context["icd10"]:
            return
        payload = get(f"/api/icd10/{code}")
        if payload is not None:
            context["icd10"][code] = payload

    def fetch_service_code(code: str) -> None:
        if code in context["service_codes"]:
            return
        payload = get(f"/api/service-codes/{code}")
        if payload is not None:
            context["service_codes"][code] = payload

    for candidate_id in sorted(collected["duplicates"]):
        fetch_duplicate(candidate_id)
    for referral_id in sorted(collected["referrals"]):
        fetch_referral(referral_id)
    for batch_id in sorted(collected["batches"]):
        fetch_batch(batch_id)

    # Fetch patients after duplicate/referral/batch records have contributed dependent IDs.
    for patient_id in sorted(collected["patients"]):
        fetch_patient(patient_id)

    # Find requested service requests in fetched patient service-request lists.
    for service_request_id in sorted(collected["service_requests"]):
        found = False
        for patient_id, resources in context["patient_resources"].items():
            for item in first_list(resources.get("service-requests"), ("service_requests", "serviceRequests")):
                if isinstance(item, dict) and item.get("service_request_id") == service_request_id:
                    context["service_requests"][service_request_id] = item
                    remember(item)
                    found = True
        if not found:
            warnings.append(
                f"ServiceRequest {service_request_id} was not found in fetched patient service-request lists; pass the patient ID if missing."
            )

    # Fetch dependent provider/code lookups after all clinical records are loaded.
    for provider_id in sorted(collected["providers"]):
        fetch_provider(provider_id)
    for code in sorted(collected["icd_codes"]):
        fetch_icd10(code)
    for code in sorted(collected["service_codes"]):
        fetch_service_code(code)

    if args.include_audit_logs:
        payload = get("/api/audit-logs", remember_payload=False)
        tokens = set().union(
            collected["patients"],
            collected["providers"],
            collected["referrals"],
            collected["duplicates"],
            collected["service_requests"],
            collected["batches"],
        )
        for item in first_list(payload, ("audit_logs", "auditLogs")):
            text = json.dumps(item, sort_keys=True)
            if any(token in text for token in tokens):
                context["audit_logs"].append(item)
                remember(item)
        context["audit_logs"] = sorted_records(context["audit_logs"], "audit_id")

    context["discovered_ids"] = {key: sorted(value) for key, value in sorted(collected.items())}
    json.dump(context, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
