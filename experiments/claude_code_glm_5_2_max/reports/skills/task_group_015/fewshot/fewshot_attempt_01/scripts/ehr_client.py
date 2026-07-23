#!/usr/bin/env python3
"""Generic read-only client and normalization helpers for the EHR
quality-governance / referral-coordination environment.

This module is deliberately task-agnostic: it knows the endpoint catalog and
the normalization conventions shared by every packet type, but it contains no
case-specific IDs, codes, names, or clinical values. Use it to fetch evidence
from the network API described in ``environment_access.md`` and to shape that
evidence toward any ``answer_template.json`` contract.

The network API is the ONLY source of truth for environment data.
``environment_access.md`` is read solely to obtain the base URL needed to reach
that API over the network (it is an access doc, not environment data).
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any, Iterable

# Map of list endpoint path -> wrapper key that holds the array in the response.
_WRAPPER_KEYS = {
    "api/patients": "patients",
    "api/audit-logs": "audit_logs",
    "api/duplicates/candidates": "duplicate_candidates",
    "api/referrals": "referrals",
    "api/icd10": "icd10",
    "api/providers": "providers",
    "api/service-codes": "service_codes",
}

# Per-patient sub-resource path suffix -> wrapper key.
_SUB_KEYS = {
    "conditions": "conditions",
    "medications": "medications",
    "allergies": "allergies",
    "encounters": "encounters",
    "documents": "documents",
    "immunizations": "immunizations",
    "disclosures": "disclosures",
    "service-requests": "service_requests",
}

# ICD-10 chapter expected for a given orthopedic / musculoskeletal service line.
# Used by the batch-audit "out of range chapter" check. Extend as needed.
SERVICE_LINE_EXPECTED_CHAPTER = {
    "orthopedics": "Musculoskeletal",
}


class EhrClient:
    """Thin HTTP client over the read-only EHR quality-governance API."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @classmethod
    def from_env_access(cls, path: str = "environment_access.md",
                        timeout: float = 30.0) -> "EhrClient":
        """Build a client from the base URL declared in environment_access.md."""
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        m = re.search(r"Base URL:\s*(\S+)", text)
        if not m:
            raise ValueError(f"Could not find 'Base URL:' in {path}")
        return cls(m.group(1), timeout=timeout)

    def _get(self, path: str) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code} for {url}") from e

    def _list(self, path: str, wrapper: str) -> list[dict]:
        data = self._get(path)
        if isinstance(data, dict) and wrapper in data:
            return list(data[wrapper])
        if isinstance(data, list):
            return data
        return []

    # -- global list / detail endpoints --
    def patients(self) -> list[dict]:
        return self._list("api/patients", "patients")

    def patient(self, patient_id: str) -> dict:
        return self._get(f"api/patients/{patient_id}")

    def audit_logs(self) -> list[dict]:
        return self._list("api/audit-logs", "audit_logs")

    def duplicate_candidates(self) -> list[dict]:
        return self._list("api/duplicates/candidates", "duplicate_candidates")

    def duplicate(self, candidate_id: str) -> dict:
        return self._get(f"api/duplicates/{candidate_id}")

    def referrals(self) -> list[dict]:
        return self._list("api/referrals", "referrals")

    def referral(self, referral_id: str) -> dict:
        return self._get(f"api/referrals/{referral_id}")

    def icd10(self) -> list[dict]:
        return self._list("api/icd10", "icd10")

    def icd10_code(self, code: str) -> dict:
        return self._get(f"api/icd10/{code}")

    def providers(self) -> list[dict]:
        return self._list("api/providers", "providers")

    def provider(self, provider_id: str) -> dict:
        return self._get(f"api/providers/{provider_id}")

    def service_codes(self) -> list[dict]:
        return self._list("api/service-codes", "service_codes")

    def service_code(self, code: str) -> dict:
        return self._get(f"api/service-codes/{code}")

    # -- per-patient sub-resources --
    def _sub(self, patient_id: str, suffix: str, wrapper: str) -> list[dict]:
        return self._list(f"api/patients/{patient_id}/{suffix}", wrapper)

    def conditions(self, patient_id: str) -> list[dict]:
        return self._sub(patient_id, "conditions", "conditions")

    def medications(self, patient_id: str) -> list[dict]:
        return self._sub(patient_id, "medications", "medications")

    def allergies(self, patient_id: str) -> list[dict]:
        return self._sub(patient_id, "allergies", "allergies")

    def encounters(self, patient_id: str) -> list[dict]:
        return self._sub(patient_id, "encounters", "encounters")

    def documents(self, patient_id: str) -> list[dict]:
        return self._sub(patient_id, "documents", "documents")

    def immunizations(self, patient_id: str) -> list[dict]:
        return self._sub(patient_id, "immunizations", "immunizations")

    def disclosures(self, patient_id: str) -> list[dict]:
        return self._sub(patient_id, "disclosures", "disclosures")

    def service_requests(self, patient_id: str) -> list[dict]:
        return self._sub(patient_id, "service-requests", "service_requests")

    # -- convenience: client-side filtering (the API does NOT filter) --
    def clinical_bundle(self, patient_id: str) -> dict:
        return {
            "patient": self.patient(patient_id),
            "conditions": self.conditions(patient_id),
            "medications": self.medications(patient_id),
            "allergies": self.allergies(patient_id),
            "encounters": self.encounters(patient_id),
            "documents": self.documents(patient_id),
            "immunizations": self.immunizations(patient_id),
            "disclosures": self.disclosures(patient_id),
            "service_requests": self.service_requests(patient_id),
        }

    def referrals_for_batch(self, batch_id: str) -> list[dict]:
        return [r for r in self.referrals() if r.get("batch_id") == batch_id]

    def referrals_for_patient(self, patient_id: str) -> list[dict]:
        return [r for r in self.referrals() if r.get("patient_id") == patient_id]

    def audit_logs_for_patient(self, patient_id: str) -> list[dict]:
        return [a for a in self.audit_logs() if a.get("patient_id") == patient_id]

    def audit_logs_for_candidate(self, candidate: dict) -> list[dict]:
        ids = set(candidate.get("patient_ids") or [])
        return [a for a in self.audit_logs() if a.get("patient_id") in ids]


# ---------------------------------------------------------------------------
# Normalization helpers (pure functions, task-agnostic)
# ---------------------------------------------------------------------------

_ACTIVE_VALUES = {"active"}


def is_active(record: dict) -> bool:
    return str(record.get("status", "")).strip().lower() in _ACTIVE_VALUES


def active_records(records: Iterable[dict]) -> list[dict]:
    return [r for r in records if is_active(r)]


def sorted_set(values: Iterable[Any]) -> list:
    """Unique non-empty values sorted ascending (string ordering)."""
    cleaned = [v for v in values if v not in (None, "")]
    return sorted(set(cleaned))


def active_keys(records: Iterable[dict]) -> list[str]:
    """Sorted set of normalized_key values from active records."""
    return sorted_set(r.get("normalized_key") for r in active_records(records))


def union_keys(*lists: Iterable[str]) -> list[str]:
    out: list = []
    for lst in lists:
        out.extend(lst)
    return sorted_set(out)


def set_difference(a: Iterable[str], b: Iterable[str]) -> list[str]:
    """Items in ``a`` but not in ``b``, sorted ascending."""
    bset = set(b)
    return sorted_set(x for x in a if x not in bset)


def icd_chapter(client: EhrClient, code: str) -> str | None:
    if not code:
        return None
    try:
        return client.icd10_code(code).get("chapter")
    except RuntimeError:
        return None


def icd_expected_terms(client: EhrClient, code: str) -> list[str]:
    if not code:
        return []
    try:
        return client.icd10_code(code).get("expected_terms", [])
    except RuntimeError:
        return []


def icd_requires_laterality(client: EhrClient, code: str) -> bool:
    if not code:
        return False
    try:
        return bool(client.icd10_code(code).get("requires_laterality"))
    except RuntimeError:
        return False


def service_code_valid(client: EhrClient, code: str) -> bool:
    if not code:
        return False
    try:
        rec = client.service_code(code)
    except RuntimeError:
        return False
    return bool(rec.get("active"))


def provider_service_line(client: EhrClient, provider_id: str) -> str | None:
    if not provider_id:
        return None
    try:
        return client.provider(provider_id).get("service_line")
    except RuntimeError:
        return None


def sbar_coverage(service_request: dict) -> dict:
    """Derive sbar_coverage from a service_request's `sbar` object."""
    sections = ["situation", "background", "assessment", "recommendation"]
    sbar = service_request.get("sbar") or {}
    present, missing = [], []
    for s in sections:
        val = sbar.get(s)
        if val not in (None, "", []):
            present.append(s)
        else:
            missing.append(s)
    return {
        "complete": not missing,
        "sections_present": present,
        "missing_sections": missing,
    }


def laterality_mismatch(diagnosis_code: str, diagnosis_narrative: str,
                        expected_terms: list[str]) -> list[str]:
    """Return mismatch_types for a referral's code/narrative vs ICD expected_terms.

    Returns any of: laterality_mismatch, narrative_mismatch, missing_laterality.
    Narrative matching is case-insensitive substring against expected_terms.
    """
    mismatches: list[str] = []
    narrative = (diagnosis_narrative or "").lower()
    terms = [t.lower() for t in expected_terms]
    narrative_ok = any(t and t in narrative for t in terms)
    if not narrative_ok:
        mismatches.append("narrative_mismatch")

    # Laterality: only meaningful when the code requires laterality.
    code = (diagnosis_code or "").upper()
    requires_lat = code.endswith(("1", "2", "4", "5"))  # 1=right,2=left,4=right,5=left
    # Heuristic; prefer icd_requires_laterality for the authoritative flag.
    has_lat_term = any(tok in narrative for tok in ("right", "left"))
    if requires_lat and not has_lat_term:
        mismatches.append("missing_laterality")
    elif requires_lat and has_lat_term:
        code_lat = "right" if code.endswith(("1", "4")) else "left"
        if code_lat not in narrative:
            mismatches.append("laterality_mismatch")
    return mismatches


if __name__ == "__main__":
    # Smoke test: confirm the API is reachable and a few endpoints respond.
    c = EhrClient.from_env_access("environment_access.md")
    print("base_url:", c.base_url)
    print("patients:", len(c.patients()))
    print("referrals:", len(c.referrals()))
    print("duplicate_candidates:", len(c.duplicate_candidates()))
    print("providers:", len(c.providers()))
    print("icd10:", len(c.icd10()))
