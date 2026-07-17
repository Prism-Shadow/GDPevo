from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from advisory_rules import load_data
from judge_api import judge_answer_request


DATA_DIR = Path(__file__).resolve().parent / "data"
DATA = None


def json_response(handler, payload, status=200):
    body = json.dumps(payload, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def html_response(handler, html, status=200):
    body = html.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        global DATA
        if DATA is None:
            DATA = load_data(DATA_DIR)
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = parse_qs(parsed.query)

        if path in ("", "/"):
            return html_response(
                self,
                "<h1>Private Wealth Advisory Portal</h1><p>Use /api endpoints for client, document, account, policy, and trust records.</p>",
            )
        if path == "/api/health":
            return json_response(self, {"ok": True, "service": "private-wealth-advisory"})
        if path == "/api/clients":
            search = qs.get("search", [""])[0].lower()
            clients = DATA["clients"]
            if search:
                clients = [
                    c for c in clients if search in c["client_id"].lower() or search in c["household_name"].lower()
                ]
            return json_response(self, clients)
        if path.startswith("/api/clients/"):
            cid = unquote(path.split("/")[-1])
            matches = [c for c in DATA["clients"] if c["client_id"] == cid]
            if not matches:
                return json_response(self, {"error": "client not found"}, 404)
            return json_response(self, matches[0])
        if path == "/api/source-documents":
            cid = qs.get("client_id", [None])[0]
            rows = DATA["source_documents"]
            if cid:
                rows = [r for r in rows if r["client_id"] == cid]
            return json_response(self, rows)
        if path == "/api/retirement-accounts":
            cid = qs.get("client_id", [None])[0]
            rows = DATA["retirement_accounts"]
            if cid:
                rows = [r for r in rows if r["client_id"] == cid]
            return json_response(self, rows)
        if path == "/api/life-insurance":
            cid = qs.get("client_id", [None])[0]
            rows = DATA["life_insurance"]
            if cid:
                rows = [r for r in rows if r["client_id"] == cid]
            return json_response(self, rows)
        if path == "/api/trust-candidates":
            cid = qs.get("client_id", [None])[0]
            rows = DATA["trust_candidates"]
            if cid:
                rows = [r for r in rows if r["client_id"] == cid]
            return json_response(self, rows)
        if path == "/api/policies/tax":
            return json_response(self, DATA["tax_policy"])
        if path == "/api/rmd-factors":
            return json_response(self, DATA["rmd_factors"])
        if path.startswith("/portal/client/"):
            cid = unquote(path.split("/")[-1])
            matches = [c for c in DATA["clients"] if c["client_id"] == cid]
            if not matches:
                return html_response(self, "<h1>Not found</h1>", 404)
            c = matches[0]
            html = f"""
            <h1>{c["household_name"]}</h1>
            <p>Client ID: {c["client_id"]}</p>
            <p>Advisor team: {c["advisor_team"]}</p>
            <p>Use API links for planning documents, retirement accounts, life insurance, and trust candidates.</p>
            """
            return html_response(self, html)
        return json_response(self, {"error": "unknown endpoint", "path": path}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.rstrip("/") != "/api/judge":
            return json_response(self, {"error": "unknown endpoint", "path": parsed.path}, 404)
        if os.environ.get("TASK_ENV_ENABLE_JUDGE") != "1":
            return json_response(self, {"error": "unknown endpoint", "path": parsed.path}, 404)
        length = int(self.headers.get("Content-Length", "0"))
        status, payload = judge_answer_request(self.rfile.read(length))
        return json_response(self, payload, status)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("TASK_ENV_BIND", os.environ.get("TASK_ENV_HOST", "0.0.0.0")))
    parser.add_argument(
        "--port", default=int(os.environ.get("TASK_ENV_PORT", os.environ.get("PORT", "9008"))), type=int
    )
    args = parser.parse_args()
    global DATA
    DATA = load_data(DATA_DIR)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Private Wealth Advisory API listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
