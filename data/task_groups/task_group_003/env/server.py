#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from judge_api import judge_answer_request


BASE = Path(__file__).resolve().parent
DATA = json.loads((BASE / "data" / "support_data.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((BASE / "data" / "manifest.json").read_text(encoding="utf-8"))


def by_key(collection, key, value):
    for item in DATA[collection]:
        if str(item.get(key)) == value:
            return item
    return None


def contains_text(value, query):
    return query.lower() in json.dumps(value, sort_keys=True).lower()


class Handler(BaseHTTPRequestHandler):
    server_version = "SupportConsole/1.0"

    def log_message(self, format, *args):
        return

    def send_json(self, payload, status=200):
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def not_found(self):
        self.send_json({"error": "not_found"}, status=404)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path).rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        if path == "/health":
            return self.send_json({"ok": True, "service": "task_group_003_support_console"})
        if path == "/api/catalog":
            return self.send_json(MANIFEST)

        if path == "/api/search":
            query = qs.get("q", [""])[0]
            if not query:
                return self.send_json({"query": query, "results": []})
            results = []
            for collection, rows in DATA.items():
                for row in rows:
                    if contains_text(row, query):
                        results.append({"collection": collection, "record": row})
            return self.send_json({"query": query, "results": results[:100]})

        simple_collections = {
            "/api/accounts": ("accounts", "account_id"),
            "/api/tickets": ("tickets", "ticket_id"),
            "/api/customers": ("customers", "customer_id"),
            "/api/lines": ("lines", "line_id"),
            "/api/devices": ("devices", "device_id"),
            "/api/plans": ("plans", "plan_id"),
            "/api/bills": ("bills", "bill_id"),
            "/api/cases": ("cases", "case_id"),
        }

        for prefix, (collection, key) in simple_collections.items():
            if path == prefix:
                rows = DATA[collection]
                if "service_area" in qs:
                    area = qs["service_area"][0]
                    rows = [r for r in rows if r.get("service_area") == area]
                if "customer_id" in qs:
                    cid = qs["customer_id"][0]
                    rows = [r for r in rows if r.get("customer_id") == cid]
                return self.send_json(rows)
            if path.startswith(prefix + "/"):
                record_id = path[len(prefix) + 1 :]
                item = by_key(collection, key, record_id)
                return self.send_json(item) if item else self.not_found()

        if path == "/api/outages":
            rows = DATA["outages"]
            if "service_area" in qs:
                area = qs["service_area"][0]
                rows = [r for r in rows if r.get("service_area") == area]
            return self.send_json(rows)

        if path.startswith("/api/diagnostics/"):
            ticket_id = path.split("/")[-1]
            rows = [r for r in DATA["diagnostics"] if r["ticket_id"] == ticket_id]
            return self.send_json(rows[0] if rows else {})

        if path.startswith("/api/troubleshooting/"):
            ticket_id = path.split("/")[-1]
            rows = [r for r in DATA["troubleshooting"] if r["ticket_id"] == ticket_id]
            return self.send_json(rows[0] if rows else {})

        if path == "/api/enterprise/accounts":
            return self.send_json(DATA["enterprise_accounts"])
        if path.startswith("/api/enterprise/accounts/"):
            ent_id = path.split("/")[-1]
            item = by_key("enterprise_accounts", "enterprise_account_id", ent_id)
            return self.send_json(item) if item else self.not_found()

        if path == "/api/enterprise/incidents":
            rows = DATA["enterprise_incidents"]
            if "account_id" in qs:
                ent_id = qs["account_id"][0]
                rows = [r for r in rows if r["enterprise_account_id"] == ent_id]
            return self.send_json(rows)
        if path.startswith("/api/enterprise/incidents/"):
            inc_id = path.split("/")[-1]
            item = by_key("enterprise_incidents", "incident_id", inc_id)
            return self.send_json(item) if item else self.not_found()

        if path == "/api/enterprise/export-runs":
            rows = DATA["export_runs"]
            if "account_id" in qs:
                ent_id = qs["account_id"][0]
                rows = [r for r in rows if r["enterprise_account_id"] == ent_id]
            if "incident_id" in qs:
                inc_id = qs["incident_id"][0]
                rows = [r for r in rows if r["incident_id"] == inc_id]
            return self.send_json(rows)

        if path == "/api/enterprise/messages":
            rows = DATA["messages"]
            if "query" in qs:
                query = qs["query"][0]
                rows = [r for r in rows if contains_text(r, query)]
            return self.send_json(rows)

        if path.startswith("/api/enterprise/sla/"):
            ent_id = path.split("/")[-1]
            rows = [r for r in DATA["sla_contracts"] if r["enterprise_account_id"] == ent_id]
            return self.send_json(rows[0] if rows else {})

        self.not_found()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/judge":
            return self.not_found()
        if os.environ.get("TASK_ENV_ENABLE_JUDGE") != "1":
            return self.not_found()
        length = int(self.headers.get("Content-Length", "0"))
        status, payload = judge_answer_request(self.rfile.read(length))
        return self.send_json(payload, status=status)


def main():
    host = os.environ.get("TASK_ENV_BIND", os.environ.get("TASK_ENV_HOST", "0.0.0.0"))
    port = int(os.environ.get("TASK_ENV_PORT", os.environ.get("PORT", "9003")))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Support console API listening on http://{host}:{port}")
    print(f"Health: http://{host}:{port}/health")
    server.serve_forever()


if __name__ == "__main__":
    main()
