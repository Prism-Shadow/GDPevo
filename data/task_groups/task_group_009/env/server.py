#!/usr/bin/env python3
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from judge_api import judge_answer_request


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def load_json(name):
    with (DATA / name).open("r", encoding="utf-8") as f:
        return json.load(f)


class FinanceOpsHandler(BaseHTTPRequestHandler):
    cache = {}

    def log_message(self, fmt, *args):
        return

    @classmethod
    def get_data(cls, name):
        if name not in cls.cache:
            cls.cache[name] = load_json(name)
        return cls.cache[name]

    def send_json(self, obj, status=200):
        payload = json.dumps(obj, ensure_ascii=True, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = {k: v[0] for k, v in parse_qs(parsed.query).items() if v}

        if path == "/":
            self.send_json(
                {
                    "service": "Crescent Finance Ops",
                    "message": "Use /api/manifest for available business endpoints.",
                }
            )
            return

        if path == "/health":
            self.send_json({"status": "ok"})
            return

        if path == "/api/manifest":
            self.send_json(self.get_data("manifest.json"))
            return

        if path == "/api/finance/branches":
            self.send_json(self.get_data("finance_branches.json"))
            return

        if path == "/api/finance/period-map":
            self.send_json(self.get_data("finance_period_map.json"))
            return

        if path == "/api/finance/accounts":
            self.send_json(self.get_data("finance_accounts.json"))
            return

        if path == "/api/finance/records":
            records = self.get_data("finance_records.json")
            branches = {b["branch_id"]: b for b in self.get_data("finance_branches.json")}
            if "branch_id" in query:
                records = [r for r in records if r["branch_id"] == query["branch_id"]]
            if "region" in query:
                records = [r for r in records if branches[r["branch_id"]]["region_id"] == query["region"]]
            if "account" in query:
                records = [r for r in records if r["account"] == query["account"]]
            self.send_json(records)
            return

        if path == "/api/compensation/rate-book":
            self.send_json(self.get_data("compensation_rate_book.json"))
            return

        if path == "/api/compensation/rosters":
            rosters = self.get_data("compensation_rosters.json")
            if "ensemble_id" in query:
                rosters = [r for r in rosters if r["ensemble_id"] == query["ensemble_id"]]
            self.send_json(rosters)
            return

        if path == "/api/compensation/scenarios":
            self.send_json(self.get_data("compensation_scenarios.json"))
            return

        if path == "/api/payroll/rate-book":
            self.send_json(self.get_data("payroll_rate_book.json"))
            return

        if path == "/api/payroll/productions":
            productions = self.get_data("payroll_productions.json")
            if "production_id" in query:
                productions = [p for p in productions if p["production_id"] == query["production_id"]]
            self.send_json(productions)
            return

        self.send_json({"error": "not found", "path": path}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/api/judge":
            length = int(self.headers.get("Content-Length", "0") or "0")
            status, payload = judge_answer_request(self.rfile.read(length))
            self.send_json(payload, status=status)
            return
        self.send_json({"error": "not found", "path": path}, status=404)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8047)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), FinanceOpsHandler)
    print(f"Crescent Finance Ops API listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
