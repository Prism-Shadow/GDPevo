#!/usr/bin/env python3
"""Small standard-library HTTP API for the ClinicProtocol environment."""

from __future__ import annotations

import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from judge_api import judge_answer_request


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "clinic_data.json"


def load_data() -> dict:
    if not DATA_PATH.exists():
        raise SystemExit(f"Missing data file: {DATA_PATH}. Run env/generate_data.py first.")
    with DATA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


DATA = load_data()


def first_param(params: dict[str, list[str]], name: str) -> str | None:
    values = params.get(name)
    if not values:
        return None
    value = values[0].strip()
    return value if value else None


def matches_text(value: str, query: str) -> bool:
    return query.casefold() in value.casefold()


def parse_instant(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def date_filter(item: dict, params: dict[str, list[str]]) -> bool:
    value = item.get("effectiveDateTime")
    if not value:
        return False
    try:
        effective = parse_instant(value)
    except ValueError:
        return False
    date_from = first_param(params, "date_from")
    date_to = first_param(params, "date_to")
    if date_from:
        try:
            start = parse_instant(date_from if "T" in date_from else f"{date_from}T00:00:00-05:00")
        except ValueError:
            return False
        if effective < start:
            return False
    if date_to:
        try:
            end = parse_instant(date_to if "T" in date_to else f"{date_to}T23:59:59-05:00")
        except ValueError:
            return False
        if effective > end:
            return False
    return True


def public_patient_summary(patient: dict) -> dict:
    return {
        "patient_id": patient["patient_id"],
        "identifier": patient["identifier"],
        "name": patient["name"],
        "birth_date": patient["birth_date"],
        "sex": patient["sex"],
    }


def public_patient_detail(patient: dict) -> dict:
    return {
        "patient_id": patient["patient_id"],
        "identifier": patient["identifier"],
        "name": patient["name"],
        "birth_date": patient["birth_date"],
        "sex": patient["sex"],
        "phone": patient["phone"],
        "address": patient["address"],
        "allergies": patient["allergies"],
        "active_problems": patient["active_problems"],
        "medication_summary": patient["medication_summary"],
    }


class ClinicHandler(BaseHTTPRequestHandler):
    server_version = "ClinicProtocolHTTP/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} - - [{self.log_date_time_string()}] {fmt % args}")

    def write_json(self, payload, status: int = 200) -> None:
        encoded = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def not_found(self) -> None:
        self.write_json({"error": "not_found"}, 404)

    def bad_request(self, message: str) -> None:
        self.write_json({"error": "bad_request", "message": message}, 400)

    def do_POST(self) -> None:
        if urlparse(self.path).path.rstrip("/") != "/api/judge":
            self.not_found()
            return
        length = int(self.headers.get("Content-Length", "0"))
        status, payload = judge_answer_request(self.rfile.read(length))
        self.write_json(payload, status)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = parse_qs(parsed.query)

        if path == "/api/status":
            self.write_json(self.status_payload())
            return
        if path == "/api/protocols":
            self.write_json({"protocols": DATA["protocols"], "count": len(DATA["protocols"])})
            return
        if path.startswith("/api/protocols/"):
            protocol_id = unquote(path.split("/", 3)[3])
            protocol = next((item for item in DATA["protocols"] if item["protocol_id"] == protocol_id), None)
            if protocol is None:
                self.not_found()
            else:
                self.write_json({"protocol": protocol})
            return
        if path == "/api/patients":
            self.write_json(self.filter_patients(params))
            return
        if path.startswith("/api/patients/"):
            patient_id = unquote(path.split("/", 3)[3])
            patient = next((item for item in DATA["patients"] if item["patient_id"] == patient_id), None)
            if patient is None:
                self.not_found()
            else:
                self.write_json({"patient": public_patient_detail(patient)})
            return
        if path == "/api/encounters":
            self.write_json(self.filter_encounters(params))
            return
        if path == "/api/observations":
            self.write_json(self.filter_observations(params))
            return
        if path == "/api/medication_requests":
            self.write_json(self.filter_medication_requests(params))
            return
        if path == "/api/care_cases":
            self.write_json(self.filter_care_cases(params))
            return
        self.not_found()

    def status_payload(self) -> dict:
        counts = {
            "protocols": len(DATA["protocols"]),
            "patients": len(DATA["patients"]),
            "encounters": len(DATA["encounters"]),
            "observations": len(DATA["observations"]),
            "medication_requests": len(DATA["medication_requests"]),
            "care_cases": len(DATA["care_cases"]),
        }
        return {
            "status": "ok",
            "service": "clinic_protocol_decision_support",
            "seed": DATA["metadata"]["seed"],
            "synthetic_clock": DATA["metadata"]["synthetic_clock"],
            "timezone": DATA["metadata"]["timezone"],
            "counts": counts,
        }

    def filter_patients(self, params: dict[str, list[str]]) -> dict:
        identifier = first_param(params, "identifier")
        name = first_param(params, "name")
        items = DATA["patients"]
        if identifier:
            items = [item for item in items if item["identifier"] == identifier or item["patient_id"] == identifier]
        if name:
            items = [
                item
                for item in items
                if matches_text(item["name"]["text"], name)
                or matches_text(item["name"]["family"], name)
                or matches_text(item["name"]["given"], name)
            ]
        return {"patients": [public_patient_summary(item) for item in items], "count": len(items)}

    def filter_encounters(self, params: dict[str, list[str]]) -> dict:
        patient_id = first_param(params, "patient_id")
        encounter_id = first_param(params, "encounter_id")
        kind = first_param(params, "kind")
        items = DATA["encounters"]
        if patient_id:
            items = [item for item in items if item["patient_id"] == patient_id]
        if encounter_id:
            items = [item for item in items if item["encounter_id"] == encounter_id]
        if kind:
            items = [item for item in items if item["kind"] == kind]
        return {"encounters": items, "count": len(items)}

    def filter_observations(self, params: dict[str, list[str]]) -> dict:
        patient_id = first_param(params, "patient_id")
        code = first_param(params, "code")
        status = first_param(params, "status")
        category = first_param(params, "category")
        items = DATA["observations"]
        if patient_id:
            items = [item for item in items if item["patient_id"] == patient_id]
        if code:
            items = [item for item in items if item["code"] == code]
        if status:
            items = [item for item in items if item["status"] == status]
        if category:
            items = [item for item in items if item["category"] == category]
        if first_param(params, "date_from") or first_param(params, "date_to"):
            items = [item for item in items if date_filter(item, params)]
        return {"observations": items, "count": len(items)}

    def filter_medication_requests(self, params: dict[str, list[str]]) -> dict:
        patient_id = first_param(params, "patient_id")
        status = first_param(params, "status")
        category = first_param(params, "category")
        items = DATA["medication_requests"]
        if patient_id:
            items = [item for item in items if item["patient_id"] == patient_id]
        if status:
            items = [item for item in items if item["status"] == status]
        if category:
            items = [item for item in items if item["category"] == category]
        return {"medication_requests": items, "count": len(items)}

    def filter_care_cases(self, params: dict[str, list[str]]) -> dict:
        case_id = first_param(params, "case_id")
        patient_id = first_param(params, "patient_id")
        status = first_param(params, "status")
        items = DATA["care_cases"]
        if case_id:
            items = [item for item in items if item["case_id"] == case_id]
        if patient_id:
            items = [item for item in items if item["patient_id"] == patient_id]
        if status:
            items = [item for item in items if item["status"] == status]
        return {"care_cases": items, "count": len(items)}


def main() -> None:
    host = os.environ.get("TASK_ENV_HOST", "0.0.0.0")
    port_text = os.environ.get("TASK_ENV_PORT", os.environ.get("PORT", "8076"))
    try:
        port = int(port_text)
    except ValueError:
        raise SystemExit(f"Invalid PORT: {port_text!r}")
    server = ThreadingHTTPServer((host, port), ClinicHandler)
    print(f"ClinicProtocol API listening at http://{host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
