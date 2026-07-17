#!/usr/bin/env python3
"""Read-only Harborview Synthetic Clinic HTTP service."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import generate_data
import judge_api


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("TASK_ENV_DB", str(BASE_DIR / "generated" / "clinic.sqlite3")))
MANIFEST_PATH = DB_PATH.parent / "manifest.json"
READONLY_TOKEN = "synclinic-readonly"
MAX_QUERY_ROWS = 500

PUBLIC_TABLES = {
    "patients",
    "cases",
    "case_findings",
    "allergies",
    "problems",
    "medications",
    "observations",
    "imaging",
    "care_registry",
    "sdoh",
    "protocols",
}

FORBIDDEN_SQL_FRAGMENTS = [
    ";",
    "pragma",
    "attach",
    "detach",
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "replace",
    "vacuum",
    "reindex",
    "analyze",
    "truncate",
    "sqlite_master",
    "sqlite_schema",
    "sqlite_temp_master",
    "load_extension",
    "generated/",
    "manifest",
    "seed",
    "answer",
    "evaluator",
    "notes",
    "scratch",
    "task_group",
]


def ensure_database() -> None:
    if not DB_PATH.exists():
        generate_data.generate(DB_PATH)


def open_db(readonly: bool = True) -> sqlite3.Connection:
    if readonly:
        uri = f"file:{DB_PATH}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row) -> dict:
    return {key: row[key] for key in row.keys()}


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [row_to_dict(row) for row in rows]


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: Any) -> None:
    body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def not_found(handler: BaseHTTPRequestHandler) -> None:
    json_response(handler, HTTPStatus.NOT_FOUND, {"error": "not found"})


def bad_request(handler: BaseHTTPRequestHandler, message: str) -> None:
    json_response(handler, HTTPStatus.BAD_REQUEST, {"error": message})


def parse_query(path: str) -> tuple[str, dict[str, list[str]]]:
    parsed = urlparse(path)
    return parsed.path.rstrip("/") or "/", parse_qs(parsed.query, keep_blank_values=False)


def first(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    return values[0] if values else None


def limit_clause(query: dict[str, list[str]], default: int = 100, maximum: int = 500) -> tuple[int, int]:
    try:
        limit = int(first(query, "limit") or default)
    except ValueError:
        limit = default
    try:
        offset = int(first(query, "offset") or 0)
    except ValueError:
        offset = 0
    return max(1, min(limit, maximum)), max(0, offset)


def add_filter(
    clauses: list[str], params: list[Any], query: dict[str, list[str]], column: str, key: str | None = None
) -> None:
    param_key = key or column
    value = first(query, param_key)
    if value:
        clauses.append(f"{column} = ?")
        params.append(value)


def list_table(
    table: str,
    query: dict[str, list[str]],
    filters: list[tuple[str, str | None]],
    order_by: str,
) -> dict:
    clauses: list[str] = []
    params: list[Any] = []
    for column, key in filters:
        add_filter(clauses, params, query, column, key)
    start = first(query, "start")
    end = first(query, "end")
    if start and "effective_time" in order_by:
        clauses.append("effective_time >= ?")
        params.append(start)
    if end and "effective_time" in order_by:
        clauses.append("effective_time <= ?")
        params.append(end)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    limit, offset = limit_clause(query)
    sql = f"SELECT * FROM {table} {where} ORDER BY {order_by} LIMIT ? OFFSET ?"
    with open_db() as conn:
        rows = conn.execute(sql, (*params, limit, offset)).fetchall()
    return {"items": rows_to_dicts(rows), "count": len(rows), "limit": limit, "offset": offset}


def get_patient(patient_id: str) -> dict | None:
    with open_db() as conn:
        patient = conn.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,)).fetchone()
        if patient is None:
            return None
        return {
            "patient": row_to_dict(patient),
            "allergies": rows_to_dicts(
                conn.execute(
                    "SELECT * FROM allergies WHERE patient_id = ? ORDER BY status, allergen", (patient_id,)
                ).fetchall()
            ),
            "problems": rows_to_dicts(
                conn.execute(
                    "SELECT * FROM problems WHERE patient_id = ? ORDER BY status, name", (patient_id,)
                ).fetchall()
            ),
            "medications": rows_to_dicts(
                conn.execute(
                    "SELECT * FROM medications WHERE patient_id = ? ORDER BY status, name", (patient_id,)
                ).fetchall()
            ),
            "sdoh": rows_to_dicts(
                conn.execute(
                    "SELECT * FROM sdoh WHERE patient_id = ? ORDER BY severity DESC, domain", (patient_id,)
                ).fetchall()
            ),
        }


def get_case(case_id: str) -> dict | None:
    with open_db() as conn:
        case = conn.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        if case is None:
            return None
        patient_id = case["patient_id"]
        registry = conn.execute("SELECT * FROM care_registry WHERE case_id = ?", (case_id,)).fetchone()
        return {
            "case": row_to_dict(case),
            "patient": row_to_dict(
                conn.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,)).fetchone()
            ),
            "findings": rows_to_dicts(
                conn.execute(
                    "SELECT finding_key, finding_value, source_id FROM case_findings WHERE case_id = ? ORDER BY id",
                    (case_id,),
                ).fetchall()
            ),
            "allergies": rows_to_dicts(
                conn.execute(
                    "SELECT * FROM allergies WHERE patient_id = ? ORDER BY status, allergen", (patient_id,)
                ).fetchall()
            ),
            "problems": rows_to_dicts(
                conn.execute(
                    "SELECT * FROM problems WHERE patient_id = ? ORDER BY status, name", (patient_id,)
                ).fetchall()
            ),
            "medications": rows_to_dicts(
                conn.execute(
                    "SELECT * FROM medications WHERE patient_id = ? ORDER BY status, name", (patient_id,)
                ).fetchall()
            ),
            "observations": rows_to_dicts(
                conn.execute(
                    "SELECT * FROM observations WHERE case_id = ? ORDER BY effective_time, observation_id", (case_id,)
                ).fetchall()
            ),
            "imaging": rows_to_dicts(
                conn.execute(
                    "SELECT * FROM imaging WHERE case_id = ? ORDER BY performed_at, imaging_id", (case_id,)
                ).fetchall()
            ),
            "care_registry": row_to_dict(registry) if registry else None,
            "sdoh": rows_to_dicts(
                conn.execute(
                    "SELECT * FROM sdoh WHERE patient_id = ? ORDER BY severity DESC, domain", (patient_id,)
                ).fetchall()
            ),
        }


def list_protocols() -> dict:
    with open_db() as conn:
        rows = conn.execute("SELECT protocol_id, title, version FROM protocols ORDER BY protocol_id").fetchall()
    return {"items": rows_to_dicts(rows), "count": len(rows)}


def get_protocol(protocol_id: str) -> dict | None:
    with open_db() as conn:
        row = conn.execute("SELECT * FROM protocols WHERE protocol_id = ?", (protocol_id,)).fetchone()
    if row is None:
        return None
    item = row_to_dict(row)
    item["body"] = json.loads(item.pop("body_json"))
    return item


def validate_sql(sql: Any, params: Any) -> tuple[bool, str]:
    if not isinstance(sql, str) or not sql.strip():
        return False, "sql must be a non-empty string"
    stripped = sql.strip()
    lowered = stripped.lower()
    if not lowered.startswith("select"):
        return False, "only SELECT statements are allowed"
    for fragment in FORBIDDEN_SQL_FRAGMENTS:
        if fragment in lowered:
            return False, "query contains a forbidden operation or metadata reference"
    if not isinstance(params, (list, tuple, dict)):
        return False, "params must be a list, tuple, or object"
    return True, ""


def install_authorizer(conn: sqlite3.Connection) -> None:
    def authorize(action_code, arg1, arg2, db_name, trigger_name):
        del arg2, db_name, trigger_name
        if action_code == sqlite3.SQLITE_READ:
            if arg1 not in PUBLIC_TABLES:
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        if action_code in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_FUNCTION):
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    conn.set_authorizer(authorize)


def handle_query(payload: Any) -> tuple[int, dict]:
    if not isinstance(payload, dict):
        return HTTPStatus.BAD_REQUEST, {"error": "request body must be a JSON object"}
    sql = payload.get("sql")
    params = payload.get("params", [])
    ok, error = validate_sql(sql, params)
    if not ok:
        return HTTPStatus.BAD_REQUEST, {"error": error}
    try:
        with open_db(readonly=True) as conn:
            install_authorizer(conn)
            cursor = conn.execute(sql, params)
            rows = cursor.fetchmany(MAX_QUERY_ROWS + 1)
            columns = [description[0] for description in cursor.description or []]
    except sqlite3.Error as exc:
        return HTTPStatus.BAD_REQUEST, {"error": "query rejected", "detail": str(exc)}
    truncated = len(rows) > MAX_QUERY_ROWS
    rows = rows[:MAX_QUERY_ROWS]
    return HTTPStatus.OK, {
        "columns": columns,
        "rows": [dict(row) for row in rows],
        "count": len(rows),
        "truncated": truncated,
    }


def read_json_body(handler: BaseHTTPRequestHandler) -> Any:
    length_text = handler.headers.get("Content-Length", "0")
    try:
        length = int(length_text)
    except ValueError:
        raise ValueError("invalid content length")
    if length <= 0:
        raise ValueError("empty request body")
    if length > 200_000:
        raise ValueError("request body too large")
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid json: {exc.msg}") from exc


class ClinicHandler(BaseHTTPRequestHandler):
    server_version = "HarborviewSyntheticClinic/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"{self.address_string()} - - [{self.log_date_time_string()}] {fmt % args}\n")

    def do_GET(self) -> None:
        path, query = parse_query(self.path)
        if path == "/health":
            ready = DB_PATH.exists()
            manifest = {}
            if MANIFEST_PATH.exists():
                try:
                    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    manifest = {}
            json_response(
                self,
                HTTPStatus.OK,
                {
                    "status": "ok" if ready else "degraded",
                    "schema_version": manifest.get("schema_version", generate_data.SCHEMA_VERSION),
                    "database_ready": ready,
                    "service": "harborview-synthetic-clinic",
                },
            )
            return

        if path == "/api/patients":
            payload = list_table("patients", query, [("patient_id", None), ("sex", None)], "patient_id")
            json_response(self, HTTPStatus.OK, payload)
            return
        if path.startswith("/api/patients/"):
            patient_id = unquote(path.rsplit("/", 1)[-1])
            payload = get_patient(patient_id)
            if payload is None:
                not_found(self)
            else:
                json_response(self, HTTPStatus.OK, payload)
            return

        if path == "/api/cases":
            payload = list_table(
                "cases",
                query,
                [("case_id", None), ("patient_id", None), ("case_type", None), ("status", None)],
                "service_date, case_id",
            )
            json_response(self, HTTPStatus.OK, payload)
            return
        if path.startswith("/api/cases/"):
            case_id = unquote(path.rsplit("/", 1)[-1])
            payload = get_case(case_id)
            if payload is None:
                not_found(self)
            else:
                json_response(self, HTTPStatus.OK, payload)
            return

        if path == "/api/observations":
            payload = list_table(
                "observations",
                query,
                [
                    ("observation_id", None),
                    ("patient_id", None),
                    ("case_id", None),
                    ("code", None),
                    ("category", None),
                    ("status", None),
                ],
                "effective_time, observation_id",
            )
            json_response(self, HTTPStatus.OK, payload)
            return
        if path == "/api/medications":
            payload = list_table(
                "medications",
                query,
                [("patient_id", None), ("status", None), ("code", None)],
                "patient_id, status, name",
            )
            json_response(self, HTTPStatus.OK, payload)
            return
        if path == "/api/allergies":
            payload = list_table(
                "allergies",
                query,
                [("patient_id", None), ("status", None), ("allergen", None)],
                "patient_id, status, allergen",
            )
            json_response(self, HTTPStatus.OK, payload)
            return
        if path == "/api/problems":
            payload = list_table(
                "problems", query, [("patient_id", None), ("status", None), ("code", None)], "patient_id, status, name"
            )
            json_response(self, HTTPStatus.OK, payload)
            return
        if path == "/api/imaging":
            payload = list_table(
                "imaging",
                query,
                [("patient_id", None), ("case_id", None), ("status", None)],
                "performed_at, imaging_id",
            )
            json_response(self, HTTPStatus.OK, payload)
            return
        if path == "/api/care-registry":
            payload = list_table(
                "care_registry",
                query,
                [("patient_id", None), ("case_id", None), ("program_hint", None)],
                "risk_score DESC, case_id",
            )
            json_response(self, HTTPStatus.OK, payload)
            return
        if path == "/api/sdoh":
            payload = list_table(
                "sdoh", query, [("patient_id", None), ("domain", None), ("severity", None)], "patient_id, domain"
            )
            json_response(self, HTTPStatus.OK, payload)
            return
        if path == "/api/protocols":
            json_response(self, HTTPStatus.OK, list_protocols())
            return
        if path.startswith("/api/protocols/"):
            protocol_id = unquote(path.rsplit("/", 1)[-1])
            payload = get_protocol(protocol_id)
            if payload is None:
                not_found(self)
            else:
                json_response(self, HTTPStatus.OK, payload)
            return
        not_found(self)

    def do_POST(self) -> None:
        path, _query = parse_query(self.path)
        if path == "/api/query":
            if self.headers.get("X-Clinic-Token") != READONLY_TOKEN:
                json_response(self, HTTPStatus.UNAUTHORIZED, {"error": "invalid or missing clinic token"})
                return
            try:
                payload = read_json_body(self)
            except ValueError as exc:
                bad_request(self, str(exc))
                return
            status, response = handle_query(payload)
            json_response(self, status, response)
            return

        if path == "/api/judge" and os.environ.get("TASK_ENV_ENABLE_JUDGE") == "1":
            try:
                payload = read_json_body(self)
            except ValueError as exc:
                bad_request(self, str(exc))
                return
            status, response = judge_api.handle_judge_request(payload)
            json_response(self, status, response)
            return

        not_found(self)


def main() -> None:
    ensure_database()
    bind = os.environ.get("TASK_ENV_BIND", "0.0.0.0")
    try:
        port = int(os.environ.get("TASK_ENV_PORT", "9016"))
    except ValueError:
        port = 9016
    server = ThreadingHTTPServer((bind, port), ClinicHandler)
    print(f"Harborview Synthetic Clinic listening on {bind}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
