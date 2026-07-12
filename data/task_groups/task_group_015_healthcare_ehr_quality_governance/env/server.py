#!/usr/bin/env python3
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from judge_api import judge_answer_request


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "ehr_quality_data.json"


def load_data():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


DATA = load_data()


def filter_rows(rows, query):
    result = list(rows)
    for key, values in query.items():
        value = values[0]
        if not value:
            continue
        result = [row for row in result if str(row.get(key, "")) == value]
    return result


def by_id(rows, key, value):
    for row in rows:
        if row.get(key) == value:
            return row
    return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def send_json(self, obj, status=200):
        body = json.dumps(obj, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def not_found(self):
        self.send_json({"error": "not_found"}, 404)

    def do_POST(self):
        if urlparse(self.path).path.rstrip("/") != "/api/judge":
            self.not_found()
            return
        length = int(self.headers.get("Content-Length", "0"))
        status, payload = judge_answer_request(self.rfile.read(length))
        self.send_json(payload, status)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        if path == "/health":
            self.send_json({"status": "ok", "seed": DATA["seed"]})
            return
        if path == "/api":
            self.send_json(
                {
                    "endpoints": [
                        "/api/patients",
                        "/api/duplicate-candidates",
                        "/api/referrals",
                        "/api/referral-batches",
                        "/api/handoff-packets",
                        "/api/service-requests",
                        "/api/providers",
                        "/api/codebook/icd10",
                        "/api/documents",
                        "/api/audit-log",
                    ]
                }
            )
            return
        if path == "/api/patients":
            self.send_json(filter_rows(DATA["patients"], query))
            return
        if path.startswith("/api/patients/"):
            parts = path.split("/")
            patient_id = parts[3] if len(parts) > 3 else ""
            patient = by_id(DATA["patients"], "patient_id", patient_id)
            if patient is None:
                self.not_found()
                return
            if len(parts) == 4:
                self.send_json(patient)
                return
            if len(parts) == 5:
                section = parts[4]
                if section in {
                    "problems",
                    "medications",
                    "allergies",
                    "encounters",
                    "immunizations",
                    "disclosures",
                    "documents",
                }:
                    rows = patient.get(section, [])
                    self.send_json(filter_rows(rows, query))
                    return
        if path == "/api/providers":
            self.send_json(filter_rows(DATA["providers"], query))
            return
        if path == "/api/duplicate-candidates":
            self.send_json(filter_rows(DATA["duplicate_candidates"], query))
            return
        if path.startswith("/api/duplicate-candidates/"):
            row = by_id(DATA["duplicate_candidates"], "candidate_id", path.split("/")[-1])
            self.send_json(row) if row else self.not_found()
            return
        if path == "/api/referrals":
            self.send_json(filter_rows(DATA["referrals"], query))
            return
        if path == "/api/referral-batches":
            self.send_json(filter_rows(DATA["referral_batches"], query))
            return
        if path.startswith("/api/referral-batches/"):
            batch_id = path.split("/")[-1]
            batch = by_id(DATA["referral_batches"], "batch_id", batch_id)
            if not batch:
                self.not_found()
                return
            refs = [r for r in DATA["referrals"] if r["batch_id"] == batch_id]
            self.send_json({"batch": batch, "referrals": refs})
            return
        if path == "/api/handoff-packets":
            self.send_json(filter_rows(DATA["handoff_packets"], query))
            return
        if path.startswith("/api/handoff-packets/"):
            row = by_id(DATA["handoff_packets"], "packet_id", path.split("/")[-1])
            self.send_json(row) if row else self.not_found()
            return
        if path == "/api/service-requests":
            self.send_json(filter_rows(DATA["service_requests"], query))
            return
        if path.startswith("/api/service-requests/"):
            row = by_id(DATA["service_requests"], "request_id", path.split("/")[-1])
            self.send_json(row) if row else self.not_found()
            return
        if path == "/api/codebook/icd10":
            self.send_json(filter_rows(DATA["codebook_icd10"], query))
            return
        if path == "/api/documents":
            self.send_json(filter_rows(DATA["documents"], query))
            return
        if path == "/api/audit-log":
            self.send_json(filter_rows(DATA["audit_log"], query))
            return
        self.not_found()


def main():
    port = int(os.environ.get("TASK_ENV_PORT", "8007"))
    host = os.environ.get("TASK_ENV_HOST", "0.0.0.0")
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"EHR quality environment running at http://{host}:{port}", flush=True)
    print("Endpoint index: /api ; health: /health", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
