#!/usr/bin/env python3
"""HTTP API facade for the operations analytics SQLite database."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from judge_api import judge_answer_request


READ_LIMIT_DEFAULT = 100
READ_LIMIT_MAX = 1000


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "content-type")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.end_headers()
    handler.wfile.write(body)


def parse_json_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON body: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("JSON body must be an object")
    return data


def connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con


def install_readonly_authorizer(con: sqlite3.Connection) -> None:
    allowed = {
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_FUNCTION,
        sqlite3.SQLITE_TRANSACTION,
    }
    for name in ("SQLITE_RECURSIVE", "SQLITE_PRAGMA"):
        if hasattr(sqlite3, name):
            allowed.add(getattr(sqlite3, name))

    def authorize(action, arg1, arg2, dbname, source):
        if action in allowed:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    con.set_authorizer(authorize)


def install_simulation_authorizer(con: sqlite3.Connection) -> None:
    allowed = {
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_FUNCTION,
        sqlite3.SQLITE_TRANSACTION,
        sqlite3.SQLITE_UPDATE,
    }
    for name in ("SQLITE_RECURSIVE", "SQLITE_PRAGMA", "SQLITE_SAVEPOINT"):
        if hasattr(sqlite3, name):
            allowed.add(getattr(sqlite3, name))

    def authorize(action, arg1, arg2, dbname, source):
        if action in allowed:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    con.set_authorizer(authorize)


def rows_for_query(con: sqlite3.Connection, sql: str, params: list | tuple | None = None) -> dict:
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("sql must be a non-empty string")
    if params is None:
        params = []
    if not isinstance(params, (list, tuple)):
        raise ValueError("params must be a list")
    cur = con.execute(sql, params)
    rows = [dict(row) for row in cur.fetchall()]
    return {
        "columns": [item[0] for item in cur.description] if cur.description else [],
        "row_count": len(rows),
        "rows": rows,
    }


def quote_identifier(name: str) -> str:
    if not isinstance(name, str) or not name:
        raise ValueError("table name must be a non-empty string")
    return '"' + name.replace('"', '""') + '"'


def schema_payload(db_path: Path) -> dict:
    con = connect(db_path)
    try:
        objects = []
        for row in con.execute(
            """
            SELECT name, type, sql
            FROM sqlite_master
            WHERE type IN ('table', 'view')
              AND name NOT LIKE 'sqlite_%'
            ORDER BY type, name
            """
        ):
            columns = [
                {
                    "name": col["name"],
                    "type": col["type"],
                    "notnull": bool(col["notnull"]),
                    "primary_key": bool(col["pk"]),
                }
                for col in con.execute(f"PRAGMA table_info({row['name']})")
            ]
            objects.append(
                {
                    "name": row["name"],
                    "type": row["type"],
                    "columns": columns,
                    "sql": row["sql"],
                }
            )
        return {"objects": objects}
    finally:
        con.close()


class OpsAnalyticsHandler(BaseHTTPRequestHandler):
    server_version = "OpsAnalyticsAPI/1.0"

    @property
    def db_path(self) -> Path:
        return self.server.db_path  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args) -> None:
        if getattr(self.server, "quiet", False):
            return
        super().log_message(fmt, *args)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)
        try:
            if path == "/":
                json_response(
                    self,
                    HTTPStatus.OK,
                    {
                        "service": "ops_analytics_api",
                        "description": "HTTP access to the shared operations analytics database.",
                        "endpoints": {
                            "GET /health": "service status",
                            "GET /schema": "tables, views, and columns",
                            "GET /tables": "table and view names",
                            "GET /tables/<name>?limit=100&offset=0": "sample rows from one table or view",
                            "POST /query": "read-only SQL query with JSON body {'sql': str, 'params': []}",
                            "POST /simulate": "run an UPDATE script on a temporary database copy, then run read-only queries",
                        },
                    },
                )
                return
            if path == "/health":
                json_response(self, HTTPStatus.OK, {"status": "ok", "database_exists": self.db_path.exists()})
                return
            if path == "/schema":
                json_response(self, HTTPStatus.OK, schema_payload(self.db_path))
                return
            if path == "/tables":
                con = connect(self.db_path)
                try:
                    rows = [
                        dict(row)
                        for row in con.execute(
                            """
                            SELECT name, type
                            FROM sqlite_master
                            WHERE type IN ('table', 'view')
                              AND name NOT LIKE 'sqlite_%'
                            ORDER BY type, name
                            """
                        )
                    ]
                finally:
                    con.close()
                json_response(self, HTTPStatus.OK, {"objects": rows})
                return
            if path.startswith("/tables/"):
                name = unquote(path.split("/", 2)[2])
                limit = min(int(query.get("limit", [READ_LIMIT_DEFAULT])[0]), READ_LIMIT_MAX)
                offset = int(query.get("offset", [0])[0])
                con = connect(self.db_path)
                try:
                    install_readonly_authorizer(con)
                    result = rows_for_query(
                        con,
                        f"SELECT * FROM {quote_identifier(name)} LIMIT ? OFFSET ?",
                        [limit, offset],
                    )
                finally:
                    con.close()
                json_response(self, HTTPStatus.OK, result)
                return
            json_response(self, HTTPStatus.NOT_FOUND, {"error": "not found"})
        except Exception as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        try:
            if path == "/api/judge":
                length = int(self.headers.get("Content-Length", "0"))
                status, payload = judge_answer_request(self.rfile.read(length))
                json_response(self, status, payload)
                return
            body = parse_json_body(self)
            if path == "/query":
                con = connect(self.db_path)
                try:
                    install_readonly_authorizer(con)
                    result = rows_for_query(con, body.get("sql"), body.get("params", []))
                finally:
                    con.close()
                json_response(self, HTTPStatus.OK, result)
                return
            if path == "/simulate":
                script = body.get("script")
                queries = body.get("queries", [])
                if not isinstance(script, str) or not script.strip():
                    raise ValueError("script must be a non-empty SQL string")
                if not isinstance(queries, list):
                    raise ValueError("queries must be a list")
                fd, tmp_path = tempfile.mkstemp(prefix="ops_api_sim_", suffix=".sqlite")
                os.close(fd)
                try:
                    shutil.copyfile(self.db_path, tmp_path)
                    con = connect(Path(tmp_path))
                    try:
                        install_simulation_authorizer(con)
                        before_changes = con.total_changes
                        con.executescript(script)
                        changed_rows = con.total_changes - before_changes
                        con.commit()
                        install_readonly_authorizer(con)
                        query_results = {}
                        for index, item in enumerate(queries):
                            if not isinstance(item, dict):
                                raise ValueError("each query must be an object")
                            name = item.get("name") or f"query_{index + 1}"
                            query_results[str(name)] = rows_for_query(
                                con,
                                item.get("sql"),
                                item.get("params", []),
                            )
                    finally:
                        con.close()
                finally:
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
                json_response(
                    self,
                    HTTPStatus.OK,
                    {"changed_rows": changed_rows, "results": query_results},
                )
                return
            json_response(self, HTTPStatus.NOT_FOUND, {"error": "not found"})
        except Exception as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the operations analytics database over HTTP.")
    parser.add_argument("--db", type=Path, required=True, help="Path to ops_analytics.sqlite")
    parser.add_argument("--host", default=os.environ.get("TASK_ENV_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("TASK_ENV_PORT", "8050")))
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if not args.db.exists():
        raise SystemExit(f"database does not exist: {args.db}")

    server = ThreadingHTTPServer((args.host, args.port), OpsAnalyticsHandler)
    server.db_path = args.db.resolve()  # type: ignore[attr-defined]
    server.quiet = args.quiet  # type: ignore[attr-defined]
    print(f"Serving operations analytics API at http://{args.host}:{args.port}", flush=True)
    print(f"Database: {server.db_path}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
