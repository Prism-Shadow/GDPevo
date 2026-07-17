#!/usr/bin/env python3
"""Read-only HTTP API for the task_group_015 EHR/referral environment."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from judge_api import JudgeAPI


BASE_DIR = Path(__file__).resolve().parent
RECORDS_PATH = BASE_DIR / "data" / "records.json"
MANIFEST_PATH = BASE_DIR / "data" / "manifest.json"
STATE_MODE = "read_only"


def ensure_data() -> None:
    if RECORDS_PATH.exists() and MANIFEST_PATH.exists():
        return
    subprocess.run([sys.executable, str(BASE_DIR / "generate_data.py")], check=True)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def as_list(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key)
    if not values:
        return None
    return values[0]


def normalize_code(code: str) -> str:
    return unquote(code).upper()


class EHRHandler(BaseHTTPRequestHandler):
    data: dict = {}
    manifest: dict = {}
    judge_enabled: bool = False
    judge_api: JudgeAPI | None = None

    server_version = "TaskGroup015EHR/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - - [{self.log_date_time_string()}] {fmt % args}", file=sys.stderr)

    def send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: int, message: str) -> None:
        self.send_json({"error": message, "status": status}, status)

    def read_body_json(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "invalid Content-Length")
            return None
        raw = self.rfile.read(length) if length else b"{}"
        try:
            value = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "request body must be JSON")
            return None
        if not isinstance(value, dict):
            self.send_error_json(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
            return None
        return value

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = parse_qs(parsed.query)
        try:
            payload = self.route_get(path, params)
        except KeyError as exc:
            self.send_error_json(HTTPStatus.NOT_FOUND, str(exc).strip("'"))
            return
        if payload is None:
            self.send_error_json(HTTPStatus.NOT_FOUND, "endpoint not found")
            return
        self.send_json(payload)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path != "/api/judge" or not self.judge_enabled or self.judge_api is None:
            self.send_error_json(HTTPStatus.NOT_FOUND, "endpoint not found")
            return
        body = self.read_body_json()
        if body is None:
            return
        result, status = self.judge_api.handle(body)
        self.send_json(result, status)

    def route_get(self, path: str, params: dict[str, list[str]]) -> object | None:
        parts = [p for p in path.split("/") if p]
        if path == "/health":
            return {
                "status": "ok",
                "version": self.manifest.get("version"),
                "record_counts": self.manifest.get("record_counts", {}),
                "state_mode": STATE_MODE,
                "judge_enabled": self.judge_enabled,
            }
        if path == "/api/patients":
            return {"patients": self.patient_search(params)}
        if len(parts) == 3 and parts[:2] == ["api", "patients"]:
            return self.patient_detail(parts[2])
        if len(parts) == 4 and parts[:2] == ["api", "patients"]:
            return self.patient_collection(parts[2], parts[3], params)
        if path == "/api/audit-logs":
            return {"audit_logs": self.audit_logs(params)}
        if path == "/api/duplicates/candidates":
            return {"duplicate_candidates": self.data["duplicate_candidates"]}
        if len(parts) == 3 and parts[:2] == ["api", "duplicates"]:
            return self.get_one("duplicate_candidates", "candidate_id", parts[2])
        if path == "/api/referrals":
            return {"referrals": self.referrals(params)}
        if len(parts) == 3 and parts[:2] == ["api", "referrals"]:
            return self.get_one("referrals", "referral_id", parts[2])
        if path == "/api/icd10":
            return {"icd10": self.data["icd10"]}
        if len(parts) == 3 and parts[:2] == ["api", "icd10"]:
            return self.get_one("icd10", "code", normalize_code(parts[2]))
        if path == "/api/providers":
            return {"providers": self.data["providers"]}
        if len(parts) == 3 and parts[:2] == ["api", "providers"]:
            return self.get_one("providers", "provider_id", parts[2])
        if path == "/api/service-codes":
            return {"service_codes": self.data["service_codes"]}
        if len(parts) == 3 and parts[:2] == ["api", "service-codes"]:
            return self.get_one("service_codes", "code", normalize_code(parts[2]))
        return None

    def get_one(self, collection: str, key: str, value: str) -> dict:
        for row in self.data[collection]:
            if str(row.get(key)) == value:
                return row
        raise KeyError(f"{collection} record not found")

    def patient_search(self, params: dict[str, list[str]]) -> list[dict]:
        q = (as_list(params, "q") or "").lower()
        family = (as_list(params, "family") or "").lower()
        given = (as_list(params, "given") or "").lower()
        dob = as_list(params, "dob")
        insurance_id = as_list(params, "insurance_id")
        rows = []
        for patient in self.data["patients"]:
            haystack = " ".join(
                [
                    patient["patient_id"],
                    patient["display_name"],
                    patient["enterprise_mrn"],
                    patient["insurance_id"],
                    patient["phone"],
                ]
            ).lower()
            if q and q not in haystack:
                continue
            if family and family not in patient["family_name"].lower():
                continue
            if given and given not in patient["given_name"].lower():
                continue
            if dob and patient["dob"] != dob:
                continue
            if insurance_id and patient["insurance_id"] != insurance_id:
                continue
            rows.append(
                {
                    "patient_id": patient["patient_id"],
                    "display_name": patient["display_name"],
                    "dob": patient["dob"],
                    "enterprise_mrn": patient["enterprise_mrn"],
                    "phone": patient["phone"],
                    "insurance_id": patient["insurance_id"],
                    "canonical_status": patient["canonical_status"],
                }
            )
        return sorted(rows, key=lambda r: (r["display_name"], r["patient_id"]))

    def patient_detail(self, patient_id: str) -> dict:
        patient = self.get_one("patients", "patient_id", patient_id)
        provider = next(
            (p for p in self.data["providers"] if p["provider_id"] == patient["primary_care_provider_id"]), None
        )
        result = dict(patient)
        result["primary_care_provider"] = provider
        return result

    def patient_collection(self, patient_id: str, collection: str, params: dict[str, list[str]]) -> dict:
        allowed = {
            "conditions": "conditions",
            "medications": "medications",
            "allergies": "allergies",
            "encounters": "encounters",
            "immunizations": "immunizations",
            "documents": "documents",
            "service-requests": "service_requests",
            "disclosures": "disclosures",
        }
        if collection not in allowed:
            raise KeyError("patient collection not found")
        rows = [r for r in self.data[allowed[collection]] if r.get("patient_id") == patient_id]
        status = as_list(params, "status")
        if status and status != "all":
            rows = [r for r in rows if r.get("status") == status]
        if collection == "encounters":
            rows = sorted(rows, key=lambda r: r["date"], reverse=True)
            limit = as_list(params, "limit")
            if limit:
                try:
                    rows = rows[: max(0, int(limit))]
                except ValueError:
                    raise KeyError("limit must be an integer")
        elif collection in {"immunizations", "documents", "disclosures"}:
            rows = sorted(rows, key=lambda r: r.get("date", ""), reverse=True)
        return {allowed[collection]: rows}

    def audit_logs(self, params: dict[str, list[str]]) -> list[dict]:
        patient_id = as_list(params, "patient_id")
        event = as_list(params, "event")
        date_from = as_list(params, "date_from")
        date_to = as_list(params, "date_to")
        rows = self.data["audit_logs"]
        if patient_id:
            rows = [r for r in rows if r["patient_id"] == patient_id]
        if event:
            rows = [r for r in rows if r["event"] == event]
        if date_from:
            rows = [r for r in rows if r["date"] >= date_from]
        if date_to:
            rows = [r for r in rows if r["date"] <= date_to]
        return sorted(rows, key=lambda r: (r["date"], r["audit_id"]), reverse=True)

    def referrals(self, params: dict[str, list[str]]) -> list[dict]:
        rows = self.data["referrals"]
        filters = {
            "batch": "batch_id",
            "urgency": "urgency",
            "patient": "patient_id",
            "status": "status",
        }
        for param, key in filters.items():
            value = as_list(params, param)
            if value:
                rows = [r for r in rows if r.get(key) == value]
        return sorted(rows, key=lambda r: (r["batch_id"], r["referral_id"]))


def main() -> None:
    ensure_data()
    data = load_json(RECORDS_PATH)
    manifest = load_json(MANIFEST_PATH)
    bind = os.environ.get("TASK_ENV_BIND", "0.0.0.0")
    port = int(os.environ.get("TASK_ENV_PORT", "9015"))
    judge_enabled = os.environ.get("TASK_ENV_ENABLE_JUDGE") == "1"

    EHRHandler.data = data
    EHRHandler.manifest = manifest
    EHRHandler.judge_enabled = judge_enabled
    EHRHandler.judge_api = JudgeAPI(data) if judge_enabled else None

    httpd = ThreadingHTTPServer((bind, port), EHRHandler)
    print(f"task_group_015 env serving on {bind}:{port}; judge_enabled={judge_enabled}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
