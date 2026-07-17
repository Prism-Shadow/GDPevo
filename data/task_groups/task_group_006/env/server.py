#!/usr/bin/env python3
"""Small stdlib HTTP API for the ProcureOps shared environment."""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from judge_api import judge_answer_request


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "procureops_data.json"
MANIFEST_FILE = DATA_DIR / "manifest.json"

COLLECTIONS = {
    "programs": ("program_id", "programs"),
    "suppliers": ("supplier_id", "suppliers"),
    "items": ("sku", "items"),
    "contracts": ("contract_id", "contracts"),
    "purchase_requisitions": ("requisition_id", "purchase_requisitions"),
    "purchase_orders": ("po_id", "purchase_orders"),
    "receipts": ("receipt_id", "receipts"),
    "ap_invoices": ("invoice_id", "ap_invoices"),
    "payments": ("payment_id", "payments"),
    "approval_events": ("event_id", "approval_events"),
    "budget_snapshots": ("snapshot_id", "budget_snapshots"),
    "vendor_risk_events": ("event_id", "vendor_risk_events"),
}

ALIASES = {
    "purchase-requests": "purchase_requisitions",
    "purchase_requests": "purchase_requisitions",
    "purchase-requisitions": "purchase_requisitions",
    "purchase-orders": "purchase_orders",
    "ap-invoices": "ap_invoices",
    "approvals": "approval_events",
    "budgets": "budget_snapshots",
    "vendor-risks": "vendor_risk_events",
}

DATE_FIELDS = {
    "contracts": "effective_date",
    "purchase_requisitions": "need_by",
    "purchase_orders": "order_date",
    "receipts": "receipt_date",
    "ap_invoices": "invoice_date",
    "payments": "scheduled_date",
    "approval_events": "event_date",
    "budget_snapshots": "snapshot_date",
    "vendor_risk_events": "event_date",
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


DATA = load_json(DATA_FILE) if DATA_FILE.exists() else {}
MANIFEST = load_json(MANIFEST_FILE) if MANIFEST_FILE.exists() else {}


def normalize_collection(path_parts: list[str]) -> tuple[str | None, str | None]:
    if not path_parts:
        return None, None
    if len(path_parts) >= 2 and path_parts[0] == "ap":
        if path_parts[1] == "invoices":
            return "ap_invoices", path_parts[2] if len(path_parts) > 2 else None
        if path_parts[1] == "payments":
            return "payments", path_parts[2] if len(path_parts) > 2 else None
    name = ALIASES.get(path_parts[0], path_parts[0])
    return name, path_parts[1] if len(path_parts) > 1 else None


def get_nested_values(record: dict, key: str) -> list[str]:
    values = []
    if key in record and record[key] is not None:
        values.append(str(record[key]))
    for value in record.values():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and key in item and item[key] is not None:
                    values.append(str(item[key]))
    return values


def record_matches(record: dict, collection_name: str, query: dict[str, list[str]]) -> bool:
    for key, values in query.items():
        expected = [v.lower() for v in values if v != ""]
        if not expected:
            continue
        if key in {"start", "end"}:
            date_field = DATE_FIELDS.get(collection_name)
            if not date_field:
                continue
            actual_date = str(record.get(date_field, ""))
            if key == "start" and actual_date < expected[0]:
                return False
            if key == "end" and actual_date > expected[0]:
                return False
            continue
        actual = [v.lower() for v in get_nested_values(record, key)]
        if not actual or not any(a in expected for a in actual):
            return False
    return True


class ProcureOpsHandler(BaseHTTPRequestHandler):
    server_version = "ProcureOpsHTTP/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def send_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path_parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
        query = parse_qs(parsed.query, keep_blank_values=False)

        if not path_parts:
            self.send_json(200, {"service": "ProcureOps", "endpoints": sorted(COLLECTIONS)})
            return
        if path_parts == ["health"]:
            self.send_json(200, {"ok": True, "service": "ProcureOps", "seed": MANIFEST.get("seed")})
            return
        if path_parts == ["manifest"]:
            self.send_json(200, MANIFEST)
            return

        collection_name, record_id = normalize_collection(path_parts)
        if collection_name not in COLLECTIONS:
            self.send_json(404, {"error": "unknown endpoint"})
            return
        id_field, data_key = COLLECTIONS[collection_name]
        records = DATA.get(data_key, [])

        if record_id:
            for record in records:
                if str(record.get(id_field)) == record_id:
                    self.send_json(200, record)
                    return
            self.send_json(404, {"error": "record not found", "id": record_id})
            return

        filtered = [record for record in records if record_matches(record, collection_name, query)]
        self.send_json(200, {"count": len(filtered), "results": filtered})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/judge":
            self.send_json(404, {"error": "unknown endpoint"})
            return
        if os.environ.get("TASK_ENV_ENABLE_JUDGE") != "1":
            self.send_json(404, {"error": "unknown endpoint"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        status, payload = judge_answer_request(self.rfile.read(length))
        self.send_json(status, payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve ProcureOps shared data.")
    parser.add_argument("--host", default=os.environ.get("TASK_ENV_BIND", os.environ.get("TASK_ENV_HOST", "0.0.0.0")))
    parser.add_argument(
        "--port", default=int(os.environ.get("TASK_ENV_PORT", os.environ.get("PORT", "9006"))), type=int
    )
    args = parser.parse_args()
    httpd = ThreadingHTTPServer((args.host, args.port), ProcureOpsHandler)
    print(f"ProcureOps API listening on http://{args.host}:{args.port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
