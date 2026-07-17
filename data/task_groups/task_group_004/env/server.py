#!/usr/bin/env python3
"""ApexCloud Retention Operations JSON/CSV API."""

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


def load_json(filename: str) -> list[dict]:
    with (DATA_DIR / filename).open(encoding="utf-8") as handle:
        return json.load(handle)


class DataStore:
    def __init__(self) -> None:
        self.accounts = load_json("accounts.json")
        self.account_by_id = {row["account_id"]: row for row in self.accounts}
        self.metrics = load_json("account_metrics.json")
        self.tickets = load_json("support_tickets.json")
        self.nps = load_json("nps_responses.json")
        self.billing = load_json("billing_snapshots.json")
        self.ar_aging = load_json("ar_aging.json")
        self.opportunities = load_json("opportunities.json")
        self.hr_summary = load_json("hr_summary.json")
        self.event_performance = load_json("event_performance.json")
        with (BASE_DIR / "manifest.json").open(encoding="utf-8") as handle:
            self.manifest = json.load(handle)


STORE: DataStore | None = None


def between(value: str, start: str | None, end: str | None) -> bool:
    if start and value < start:
        return False
    if end and value > end:
        return False
    return True


def first_query(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    return values[0] if values else None


class Handler(BaseHTTPRequestHandler):
    server_version = "ApexCloudRetention/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        return

    @property
    def store(self) -> DataStore:
        assert STORE is not None
        return STORE

    def send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_csv_file(self, filename: str) -> None:
        path = DATA_DIR / filename
        if not path.exists():
            self.send_json({"error": "not_found", "message": f"Export {filename} is not available"}, 404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def not_found(self) -> None:
        self.send_json({"error": "not_found", "message": "No matching public endpoint"}, 404)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)
        parts = [unquote(part) for part in path.split("/") if part]

        if path == "/api/health":
            self.send_json(
                {
                    "status": "ok",
                    "service": "ApexCloud Retention Operations",
                    "seed": self.store.manifest.get("seed"),
                    "row_counts": self.store.manifest.get("row_counts", {}),
                }
            )
            return

        if path == "/api/accounts":
            self.send_json({"accounts": self.store.accounts, "count": len(self.store.accounts)})
            return

        if len(parts) == 3 and parts[:2] == ["api", "accounts"]:
            account_id = parts[2]
            account = self.store.account_by_id.get(account_id)
            if not account:
                self.send_json({"error": "not_found", "message": f"Unknown account_id {account_id}"}, 404)
                return
            self.send_json(account)
            return

        if len(parts) == 4 and parts[:2] == ["api", "accounts"] and parts[3] == "metrics":
            account_id = parts[2]
            rows = [
                row
                for row in self.store.metrics
                if row["account_id"] == account_id
                and between(row["month"], first_query(query, "start"), first_query(query, "end"))
            ]
            self.send_json({"account_id": account_id, "metrics": rows, "count": len(rows)})
            return

        if len(parts) == 4 and parts[:2] == ["api", "accounts"] and parts[3] == "tickets":
            account_id = parts[2]
            rows = [
                row
                for row in self.store.tickets
                if row["account_id"] == account_id
                and between(row["created_date"], first_query(query, "start"), first_query(query, "end"))
            ]
            self.send_json({"account_id": account_id, "tickets": rows, "count": len(rows)})
            return

        if len(parts) == 4 and parts[:2] == ["api", "accounts"] and parts[3] == "nps":
            account_id = parts[2]
            rows = [
                row
                for row in self.store.nps
                if row["account_id"] == account_id
                and between(row["response_date"], first_query(query, "start"), first_query(query, "end"))
            ]
            self.send_json({"account_id": account_id, "nps_responses": rows, "count": len(rows)})
            return

        if path == "/api/billing/snapshots":
            as_of = first_query(query, "as_of")
            account_id = first_query(query, "account_id")
            rows = self.store.billing
            if as_of:
                rows = [row for row in rows if row["as_of"] == as_of]
            if account_id:
                rows = [row for row in rows if row["account_id"] == account_id]
            self.send_json({"snapshots": rows, "count": len(rows)})
            return

        if path == "/api/finance/ar-aging":
            as_of = first_query(query, "as_of")
            region = first_query(query, "region")
            rows = self.store.ar_aging
            if as_of:
                rows = [row for row in rows if row["as_of"] == as_of]
            if region:
                rows = [row for row in rows if row["region"] == region]
            self.send_json({"ar_aging": rows, "count": len(rows)})
            return

        if path == "/api/opportunities":
            start = first_query(query, "start")
            end = first_query(query, "end")
            region = first_query(query, "region")
            rows = [row for row in self.store.opportunities if between(row["close_date"], start, end)]
            if region:
                rows = [row for row in rows if row["region"] == region]
            self.send_json({"opportunities": rows, "count": len(rows)})
            return

        if path == "/api/hr/summary":
            quarter = first_query(query, "quarter")
            region = first_query(query, "region")
            rows = self.store.hr_summary
            if quarter:
                rows = [row for row in rows if row["quarter"] == quarter]
            if region:
                rows = [row for row in rows if row["region"] == region]
            self.send_json({"hr_summary": rows, "count": len(rows)})
            return

        if path == "/api/events/performance":
            event_id = first_query(query, "event")
            quarter = first_query(query, "quarter")
            rows = self.store.event_performance
            if event_id:
                rows = [row for row in rows if row["event_id"] == event_id]
            if quarter:
                rows = [row for row in rows if row["quarter"] == quarter]
            self.send_json({"event_performance": rows, "count": len(rows)})
            return

        exports = {
            "/exports/churn/train.csv": "churn_train.csv",
            "/exports/churn/validation.csv": "churn_validation.csv",
            "/exports/churn/candidates.csv": "churn_candidates.csv",
            "/exports/account_metric_extract.csv": "account_metric_extract.csv",
        }
        if path in exports:
            self.send_csv_file(exports[path])
            return

        self.not_found()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/judge":
            self.not_found()
            return
        if os.environ.get("TASK_ENV_ENABLE_JUDGE") != "1":
            self.not_found()
            return
        length = int(self.headers.get("Content-Length", "0"))
        status, payload = judge_answer_request(self.rfile.read(length))
        self.send_json(payload, status)


def main() -> None:
    global STORE
    parser = argparse.ArgumentParser(description="Serve the ApexCloud Retention Operations dataset.")
    parser.add_argument("--host", default=os.environ.get("TASK_ENV_BIND", os.environ.get("TASK_ENV_HOST", "0.0.0.0")))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("TASK_ENV_PORT", os.environ.get("PORT", "9004")))
    )
    args = parser.parse_args()
    STORE = DataStore()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Serving ApexCloud Retention Operations on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
