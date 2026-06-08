#!/usr/bin/env python3
"""Small JSON API server for the task_group_005 ERP finance environment."""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

DATASETS = {
    "/claims": "claims.json",
    "/api/claims": "claims.json",
    "/bills": "bills.json",
    "/api/ap/bills": "bills.json",
    "/payments": "payments.json",
    "/api/ap/payments": "payments.json",
    "/vendors": "vendors.json",
    "/api/vendors": "vendors.json",
    "/compliance/objects": "compliance_objects.json",
    "/api/compliance/objects": "compliance_objects.json",
    "/prepaids/invoices": "prepaid_invoices.json",
    "/api/prepaids/invoices": "prepaid_invoices.json",
    "/gl/balances": "gl_balances.json",
    "/api/prepaids/gl-balances": "gl_balances.json",
    "/close/logs": "close_logs.json",
    "/api/close/logs": "close_logs.json",
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class DataStore:
    def __init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        self.data = {route: load_json(DATA_DIR / filename) for route, filename in DATASETS.items()}
        self.manifest = load_json(ROOT / "manifest.json")


STORE = DataStore()


def matches(row, filters):
    for key, expected_values in filters.items():
        if key in ("limit", "offset"):
            continue
        if key not in row:
            return False
        actual = row.get(key)
        expected = {value.lower() for value in expected_values}
        if actual is None:
            actual_values = {""}
        elif isinstance(actual, list):
            actual_values = {str(item).lower() for item in actual}
        else:
            actual_values = {str(actual).lower()}
        if actual_values.isdisjoint(expected):
            return False
    return True


def as_int(values, default, minimum=0, maximum=500):
    if not values:
        return default
    try:
        value = int(values[0])
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


class Handler(BaseHTTPRequestHandler):
    server_version = "TaskGroup005Env/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query, keep_blank_values=True)

        if route == "/health":
            self.send_json({"status": "ok", "task_group": "task_group_005"})
            return
        if route == "/api/health":
            self.send_json({"status": "ok", "task_group": "task_group_005"})
            return
        if route == "/endpoints":
            self.send_json(
                {
                    "endpoints": ["/health", "/api/health", "/endpoints", "/api/ap/aging"] + sorted(DATASETS.keys()),
                    "filtering": "Use exact-match query parameters by field name. Use limit and offset for pagination.",
                }
            )
            return
        if route == "/api/ap/aging":
            self.send_json(self.ap_aging(query))
            return
        compliance_prefixes = (
            "/api/compliance/profile/",
            "/api/compliance/ownership/",
            "/api/compliance/registry/",
            "/api/compliance/screening/",
            "/api/compliance/bank/",
            "/api/compliance/risk/",
        )
        for prefix in compliance_prefixes:
            if route.startswith(prefix):
                business_id = route[len(prefix) :]
                self.send_json(self.compliance_detail(prefix, business_id))
                return
        if route.startswith("/api/claims/"):
            claim_id = route[len("/api/claims/") :]
            self.send_json(self.first_match("/api/claims", "claim_id", claim_id))
            return
        if route not in DATASETS:
            self.send_json({"error": "not_found", "path": route}, status=404)
            return

        rows = [row for row in STORE.data[route] if matches(row, query)]
        total = len(rows)
        offset = as_int(query.get("offset"), 0, minimum=0, maximum=max(total, 0))
        limit = as_int(query.get("limit"), 100, minimum=1, maximum=500)
        page = rows[offset : offset + limit]
        self.send_json(
            {
                "endpoint": route,
                "count": len(page),
                "total": total,
                "offset": offset,
                "limit": limit,
                "data": page,
            }
        )

    def first_match(self, dataset_route, key, value):
        rows = [row for row in STORE.data[dataset_route] if str(row.get(key, "")).lower() == value.lower()]
        if not rows:
            return {"error": "not_found", key: value}
        return rows[0]

    def compliance_detail(self, prefix, business_id):
        row = self.first_match("/api/compliance/objects", "business_id", business_id)
        if "error" in row:
            return row
        if prefix.endswith("/profile/"):
            keys = [
                "business_id",
                "business_name",
                "vendor_id",
                "jurisdiction",
                "registration_number",
                "tax_id",
                "missing_fields",
            ]
        elif prefix.endswith("/ownership/"):
            keys = ["business_id", "ubo_list", "ownership_layer_count", "shell_company_suspected"]
        elif prefix.endswith("/registry/"):
            keys = ["business_id", "registration_number", "tax_id", "license_expiry", "jurisdiction"]
        elif prefix.endswith("/screening/"):
            keys = ["business_id", "sanctions_check_status", "pep_status"]
        elif prefix.endswith("/bank/"):
            keys = ["business_id", "bank_account_status"]
        else:
            keys = ["business_id", "risk_score", "review_status"]
        return {key: row.get(key) for key in keys}

    def ap_aging(self, query):
        payments_by_bill = {}
        for payment in STORE.data["/api/ap/payments"]:
            bill_id = payment.get("bill_id")
            payments_by_bill[bill_id] = payments_by_bill.get(bill_id, 0.0) + float(payment.get("amount", 0.0))
        rows = []
        for bill in STORE.data["/api/ap/bills"]:
            amount = float(bill.get("amount", 0.0))
            paid = payments_by_bill.get(bill.get("bill_id"), 0.0)
            balance = round(max(amount - paid, 0.0), 2)
            row = {
                "bill_id": bill.get("bill_id"),
                "claim_id": bill.get("claim_id"),
                "vendor_id": bill.get("vendor_id"),
                "bill_date": bill.get("bill_date"),
                "due_date": bill.get("due_date"),
                "status": bill.get("status"),
                "amount": amount,
                "paid_amount": round(min(paid, amount), 2),
                "balance": balance,
                "as_of": (query.get("as_of") or [""])[0],
            }
            rows.append(row)
        filtered = [row for row in rows if matches(row, query)]
        return {
            "endpoint": "/api/ap/aging",
            "count": len(filtered),
            "total": len(filtered),
            "data": filtered,
        }

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.address_string()} - - [{self.log_date_time_string()}] {fmt % args}\n")

    def send_json(self, payload, status=200) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8005
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Serving task_group_005 environment at http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
