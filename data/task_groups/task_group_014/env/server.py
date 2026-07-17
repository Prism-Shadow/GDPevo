#!/usr/bin/env python3
import argparse
import base64
import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from judge_api import judge_answer_request


DEFAULT_USERNAME = "payer_ops_solver"
DEFAULT_PASSWORD = "revcycle_sql_014"

READ_PREFIXES = (
    "select",
    "with",
    "pragma table_info(",
    "explain query plan",
)

BLOCKED_WORDS = {
    "alter",
    "attach",
    "begin",
    "commit",
    "create",
    "delete",
    "detach",
    "drop",
    "insert",
    "pragma writable_schema",
    "reindex",
    "replace",
    "rollback",
    "update",
    "vacuum",
}


def compact_sql(sql):
    return " ".join(sql.strip().split())


def strip_one_trailing_semicolon(sql):
    value = sql.strip()
    if value.endswith(";"):
        value = value[:-1].strip()
    return value


def statement_is_read_only(sql):
    if not isinstance(sql, str):
        return False, "sql must be a string"
    compact = compact_sql(sql)
    if not compact:
        return False, "sql is required"

    normalized = strip_one_trailing_semicolon(compact)
    if ";" in normalized:
        return False, "multiple statements are not allowed"

    lowered = normalized.lower()
    if not lowered.startswith(READ_PREFIXES):
        return False, "only SELECT, WITH, PRAGMA table_info(...), and EXPLAIN QUERY PLAN are allowed"

    padded = f" {lowered} "
    for word in BLOCKED_WORDS:
        if f" {word} " in padded:
            return False, f"statement contains blocked keyword: {word}"

    if lowered.startswith("pragma") and not lowered.startswith("pragma table_info("):
        return False, "only PRAGMA table_info(...) is allowed"

    return True, normalized


class QueryServer(BaseHTTPRequestHandler):
    server_version = "PayerOpsQueryService/1.0"

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - - [{self.log_date_time_string()}] {fmt % args}")

    def send_json(self, status, payload):
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, status, text):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authenticated(self):
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(header.split(" ", 1)[1], validate=True).decode("utf-8")
        except Exception:
            return False
        username, sep, password = decoded.partition(":")
        return bool(sep) and username == self.server.username and password == self.server.password

    def require_auth(self):
        if self.authenticated():
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="payer-ops-sql"')
        self.send_header("Content-Type", "application/json; charset=utf-8")
        body = json.dumps({"error": "authentication required"}).encode("utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return False

    def do_GET(self):
        if not self.require_auth():
            return
        path = urlparse(self.path).path
        if path == "/health":
            self.send_json(200, {"status": "ok", "database": os.path.basename(self.server.db_path)})
        elif path == "/":
            self.send_text(
                200,
                "Payer Operations SQL Query Service\n\n"
                "Submit read-only SQLite queries to POST /query as JSON:\n"
                '{"sql": "SELECT name FROM sqlite_master WHERE type = ? ORDER BY name", "params": ["table"]}\n',
            )
        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/judge":
            if os.environ.get("TASK_ENV_ENABLE_JUDGE") != "1":
                self.send_json(404, {"error": "not found"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            status, payload = judge_answer_request(self.rfile.read(length))
            self.send_json(status, payload)
            return
        if not self.require_auth():
            return
        if path != "/query":
            self.send_json(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(400, {"error": "invalid Content-Length"})
            return
        if length > 1_000_000:
            self.send_json(413, {"error": "request body too large"})
            return

        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self.send_json(400, {"error": "invalid JSON body"})
            return

        sql = payload.get("sql")
        params = payload.get("params", [])
        if params is None:
            params = []
        if not isinstance(params, list):
            self.send_json(400, {"error": "params must be a JSON array"})
            return

        ok, result = statement_is_read_only(sql)
        if not ok:
            self.send_json(400, {"error": result})
            return

        try:
            with sqlite3.connect(self.server.db_uri, uri=True, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA query_only = ON")
                cursor = conn.execute(result, params)
                rows = [dict(row) for row in cursor.fetchall()]
                columns = [item[0] for item in cursor.description] if cursor.description else []
        except sqlite3.Error as exc:
            self.send_json(400, {"error": str(exc)})
            return

        self.send_json(200, {"columns": columns, "rows": rows, "row_count": len(rows)})


def main():
    parser = argparse.ArgumentParser(description="SQLite-backed payer operations SQL query service")
    parser.add_argument("--db", default="payer_ops.db")
    parser.add_argument("--host", default=os.environ.get("TASK_ENV_BIND", os.environ.get("TASK_ENV_HOST", "0.0.0.0")))
    parser.add_argument("--port", type=int, default=int(os.environ.get("TASK_ENV_PORT", "9014")))
    args = parser.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        raise SystemExit(f"database not found: {db_path}")

    server = ThreadingHTTPServer((args.host, args.port), QueryServer)
    server.db_path = db_path
    server.db_uri = f"file:{db_path}?mode=ro"
    server.username = DEFAULT_USERNAME
    server.password = DEFAULT_PASSWORD
    print(f"Serving payer operations SQL on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down payer operations SQL service", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
