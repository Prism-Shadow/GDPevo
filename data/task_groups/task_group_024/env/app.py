#!/usr/bin/env python3
import json
import os
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from judge_api import handle_judge_request, judge_enabled


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "portfolio.db"
MANIFEST_PATH = BASE_DIR / "data_manifest.json"
QUERY_TOKEN = "portfolio-readonly"
MAX_QUERY_ROWS = 1000


def ensure_database():
    if not DB_PATH.exists():
        import generate_data

        generate_data.main()


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def json_response(handler, status, payload):
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def parse_json_body(handler):
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        raise ValueError("request body must be valid JSON")


def row_to_dict(row):
    data = dict(row)
    if "labels" in data and isinstance(data["labels"], str):
        try:
            data["labels"] = json.loads(data["labels"])
        except json.JSONDecodeError:
            data["labels"] = []
    return data


def fetch_all(table, filters=None, order_by=None, limit_default=500):
    filters = filters or {}
    clauses = []
    params = []
    for column, value in filters.items():
        if value is not None:
            clauses.append(f"{column} = ?")
            params.append(value)
    sql = f"SELECT * FROM {table}"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    if order_by:
        sql += f" ORDER BY {order_by}"
    if limit_default:
        sql += " LIMIT ?"
        params.append(limit_default)
    with connect() as conn:
        return [row_to_dict(row) for row in conn.execute(sql, params).fetchall()]


def health_payload():
    counts = {}
    db_exists = DB_PATH.exists()
    if db_exists:
        with connect() as conn:
            for table in [
                "work_items",
                "mix_targets",
                "sla_policy",
                "releases",
                "milestones",
                "dependencies",
                "blockers",
            ]:
                counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return {
        "ok": True,
        "database_exists": db_exists,
        "record_counts": counts,
        "judge_enabled": judge_enabled(os.environ),
    }


def single_statement(sql):
    stripped = sql.strip()
    if not stripped:
        return None
    if stripped.endswith(";"):
        stripped = stripped[:-1].strip()
    if ";" in stripped:
        return None
    return stripped


def leading_keyword(sql):
    text = re.sub(r"^\s*(?:--[^\n]*\n\s*|/\*.*?\*/\s*)*", "", sql, flags=re.DOTALL)
    match = re.match(r"([A-Za-z_]+)", text)
    return match.group(1).lower() if match else ""


def run_readonly_query(sql, params):
    statement = single_statement(sql)
    if statement is None:
        raise ValueError("sql must contain exactly one statement")
    if leading_keyword(statement) not in {"select", "with"}:
        raise PermissionError("only SELECT statements are allowed")
    if not isinstance(params, list):
        raise ValueError("params must be a JSON array")

    with connect() as conn:

        def authorizer(action, arg1, arg2, dbname, source):
            allowed = {
                sqlite3.SQLITE_SELECT,
                sqlite3.SQLITE_READ,
                sqlite3.SQLITE_FUNCTION,
            }
            return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY

        conn.set_authorizer(authorizer)
        cursor = conn.execute(statement, params)
        columns = [desc[0] for desc in cursor.description or []]
        rows = cursor.fetchmany(MAX_QUERY_ROWS + 1)
        truncated = len(rows) > MAX_QUERY_ROWS
        rows = rows[:MAX_QUERY_ROWS]
        return {
            "columns": columns,
            "rows": [list(row) for row in rows],
            "row_count": len(rows),
            "truncated": truncated,
        }


class Handler(BaseHTTPRequestHandler):
    server_version = "PortfolioEnv/1.0"

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        ensure_database()
        parsed = urlparse(self.path)
        path = parsed.path
        query = {key: values[-1] for key, values in parse_qs(parsed.query).items() if values}

        try:
            if path == "/health":
                json_response(self, 200, health_payload())
            elif path == "/api/work-items":
                self.handle_work_items(query)
            elif path.startswith("/api/work-items/"):
                item_id = unquote(path.rsplit("/", 1)[-1])
                self.handle_work_item(item_id)
            elif path == "/api/mix-targets":
                rows = fetch_all(
                    "mix_targets",
                    {key: query.get(key) for key in ["scope_id", "quarter", "team_group", "product_area"]},
                    "quarter, team_group, product_area",
                    500,
                )
                json_response(self, 200, {"mix_targets": rows})
            elif path == "/api/sla-policy":
                json_response(
                    self, 200, {"sla_policy": fetch_all("sla_policy", order_by="severity", limit_default=None)}
                )
            elif path == "/api/releases":
                json_response(
                    self, 200, {"releases": fetch_all("releases", order_by="target_date", limit_default=None)}
                )
            elif path.startswith("/api/releases/"):
                release_id = unquote(path.rsplit("/", 1)[-1])
                self.handle_release(release_id)
            elif path == "/api/milestones":
                rows = fetch_all(
                    "milestones",
                    {key: query.get(key) for key in ["release_id", "owner_team"]},
                    "release_id, id",
                    500,
                )
                json_response(self, 200, {"milestones": rows})
            elif path == "/api/dependencies":
                rows = fetch_all(
                    "dependencies",
                    {key: query.get(key) for key in ["blocked_id", "depends_on_id", "relation"]},
                    "blocked_id, depends_on_id",
                    500,
                )
                json_response(self, 200, {"dependencies": rows})
            elif path == "/api/blockers":
                rows = fetch_all(
                    "blockers",
                    {key: query.get(key) for key in ["work_item_id", "release_id", "severity", "status"]},
                    "release_id, status, id",
                    500,
                )
                json_response(self, 200, {"blockers": rows})
            else:
                json_response(self, 404, {"error": "not found"})
        except Exception as exc:
            json_response(self, 500, {"error": str(exc)})

    def do_POST(self):
        ensure_database()
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/query":
                self.handle_query()
            elif path == "/api/judge" and judge_enabled(os.environ):
                payload = parse_json_body(self)
                status, response = handle_judge_request(payload)
                json_response(self, status, response)
            else:
                json_response(self, 404, {"error": "not found"})
        except ValueError as exc:
            json_response(self, 400, {"error": str(exc)})
        except PermissionError as exc:
            json_response(self, 403, {"error": str(exc)})
        except sqlite3.Error as exc:
            json_response(self, 400, {"error": str(exc)})
        except Exception as exc:
            json_response(self, 500, {"error": str(exc)})

    def handle_work_items(self, query):
        clauses = []
        params = []
        for column in ["team", "product_area", "release_id", "status", "work_type", "severity", "milestone_id"]:
            if query.get(column):
                clauses.append(f"{column} = ?")
                params.append(query[column])
        if query.get("closed_after"):
            clauses.append("closed_at >= ?")
            params.append(query["closed_after"])
        if query.get("closed_before"):
            clauses.append("closed_at <= ?")
            params.append(query["closed_before"])
        limit = min(int(query.get("limit", "500")), 1000)
        sql = "SELECT * FROM work_items"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at, id LIMIT ?"
        params.append(limit)
        with connect() as conn:
            rows = [row_to_dict(row) for row in conn.execute(sql, params).fetchall()]
        json_response(self, 200, {"work_items": rows, "count": len(rows)})

    def handle_work_item(self, item_id):
        with connect() as conn:
            row = conn.execute("SELECT * FROM work_items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            json_response(self, 404, {"error": "work item not found"})
            return
        json_response(self, 200, {"work_item": row_to_dict(row)})

    def handle_release(self, release_id):
        with connect() as conn:
            release = conn.execute("SELECT * FROM releases WHERE id = ?", (release_id,)).fetchone()
            if not release:
                json_response(self, 404, {"error": "release not found"})
                return
            milestones = [
                row_to_dict(row)
                for row in conn.execute("SELECT * FROM milestones WHERE release_id = ? ORDER BY id", (release_id,))
            ]
            blockers = [
                row_to_dict(row)
                for row in conn.execute(
                    "SELECT * FROM blockers WHERE release_id = ? ORDER BY status, severity, id", (release_id,)
                )
            ]
        json_response(self, 200, {"release": row_to_dict(release), "milestones": milestones, "blockers": blockers})

    def handle_query(self):
        if self.headers.get("X-Env-Token") != QUERY_TOKEN:
            raise PermissionError("missing or invalid X-Env-Token")
        payload = parse_json_body(self)
        sql = payload.get("sql")
        if not isinstance(sql, str):
            raise ValueError("sql must be a string")
        params = payload.get("params", [])
        json_response(self, 200, run_readonly_query(sql, params))


def main():
    ensure_database()
    bind = os.environ.get("TASK_ENV_BIND", "0.0.0.0")
    port = int(os.environ.get("TASK_ENV_PORT", "9024"))
    server = ThreadingHTTPServer((bind, port), Handler)
    print(json.dumps({"ok": True, "bind": bind, "port": port, "database": str(DB_PATH)}, sort_keys=True), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
