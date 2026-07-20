#!/usr/bin/env python3
"""Northstar payer-operations HTTP environment."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from generate_data import DB_PATH, generate_database
from judge_api import JudgeError, score_train_answer


SERVICE = "northstar-payer-operations"
DEFAULT_PORT = 9014
TOKEN = "pa-review-token-014"
ROOT = Path(__file__).resolve().parent
DB_FILE = Path(os.environ.get("TASK_DB_PATH", str(DB_PATH))).resolve()
MAX_SQL_ROWS = 500
READONLY_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|replace|vacuum|reindex|analyze)\b",
    re.IGNORECASE,
)


def judge_enabled() -> bool:
    return os.environ.get("TASK_ENV_ENABLE_JUDGE") == "1"


def db_present() -> bool:
    return DB_FILE.exists()


def ensure_database() -> None:
    if not db_present():
        generate_database(DB_FILE, overwrite=True)


def connect(readonly: bool = True) -> sqlite3.Connection:
    ensure_database()
    if readonly:
        uri = f"file:{DB_FILE.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        conn.execute("PRAGMA query_only=ON")
    else:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [{key: row[key] for key in row.keys()} for row in rows]


def one_row(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(sql, params).fetchone()
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def many_rows(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return rows_to_dicts(rows)


def parse_int(value: str | None, default: int, maximum: int) -> int:
    try:
        parsed = int(value or default)
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, maximum))


def strip_sql_strings(sql: str) -> str:
    result: list[str] = []
    quote: str | None = None
    idx = 0
    while idx < len(sql):
        char = sql[idx]
        if quote:
            if char == quote:
                if idx + 1 < len(sql) and sql[idx + 1] == quote:
                    idx += 2
                    continue
                quote = None
            result.append(" ")
            idx += 1
            continue
        if char in ("'", '"'):
            quote = char
            result.append(" ")
        else:
            result.append(char)
        idx += 1
    return "".join(result)


def trim_single_statement(sql: str) -> str:
    no_literals = strip_sql_strings(sql)
    semicolon_at = no_literals.find(";")
    if semicolon_at == -1:
        return sql.strip()
    if no_literals[semicolon_at + 1 :].strip():
        raise ValueError("only one SQL statement is allowed")
    return sql[:semicolon_at].strip()


def validate_readonly_sql(sql: Any) -> str:
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("sql must be a non-empty string")
    statement = trim_single_statement(sql)
    no_literals = strip_sql_strings(statement)
    lowered = no_literals.lstrip().lower()
    if "pragma writable_schema" in lowered:
        raise ValueError("writable pragmas are not allowed")
    if lowered.startswith("pragma"):
        if not re.match(r"^pragma\s+table_info\s*\(\s*[A-Za-z_][A-Za-z0-9_]*\s*\)\s*$", lowered, re.IGNORECASE):
            raise ValueError("only PRAGMA table_info(table_name) is allowed")
        return statement
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise ValueError("only SELECT, WITH, and PRAGMA table_info statements are allowed")
    if READONLY_KEYWORDS.search(no_literals):
        raise ValueError("mutating SQL is not allowed")
    return statement


def html_page() -> bytes:
    content = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Northstar Payer Operations</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 32px; line-height: 1.45; color: #202124; }
    main { max-width: 920px; }
    code { background: #f1f3f4; padding: 2px 5px; border-radius: 4px; }
    li { margin: 5px 0; }
  </style>
</head>
<body>
<main>
  <h1>Northstar Payer Operations</h1>
  <p>Shared read-only payer operations portal for utilization management, appeals, payment review, and queue analysis.</p>
  <h2>Business Entry Points</h2>
  <ul>
    <li><code>GET /api/tables</code></li>
    <li><code>GET /api/cases</code></li>
    <li><code>GET /api/policies</code></li>
    <li><code>GET /api/rate-schedules</code></li>
    <li><code>GET /api/appeals</code></li>
    <li><code>POST /sql/query</code></li>
  </ul>
</main>
</body>
</html>
"""
    return content.encode("utf-8")


def table_catalog() -> dict[str, Any]:
    with connect() as conn:
        tables = [
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]
        result = []
        for table in tables:
            columns = [
                {
                    "name": col["name"],
                    "type": col["type"],
                    "not_null": bool(col["notnull"]),
                    "primary_key": bool(col["pk"]),
                }
                for col in conn.execute(f"PRAGMA table_info({table})").fetchall()
            ]
            result.append({"table": table, "columns": columns})
    return {"tables": result}


def list_cases(query: dict[str, list[str]]) -> dict[str, Any]:
    clauses: list[str] = []
    params: list[Any] = []
    filters = {
        "stage": "c.current_stage",
        "status": "c.current_status",
        "member_id": "c.member_id",
        "service_domain": "c.service_domain",
        "request_type": "c.request_type",
    }
    for key, column in filters.items():
        if query.get(key):
            clauses.append(f"{column} = ?")
            params.append(query[key][0])
    if query.get("q"):
        clauses.append("(c.case_id LIKE ? OR c.summary LIKE ? OR m.patient_name LIKE ?)")
        needle = f"%{query['q'][0]}%"
        params.extend([needle, needle, needle])
    limit = parse_int(query.get("limit", [None])[0], 100, 500)
    sql = """
        SELECT c.case_id, c.request_type, c.service_domain, c.request_date, c.due_date,
               c.current_stage, c.current_status, c.urgency, c.summary,
               m.member_id, m.patient_name, m.plan_type, p.provider_name, p.specialty
        FROM cases c
        JOIN members m ON m.member_id = c.member_id
        JOIN providers p ON p.provider_id = c.provider_id
    """
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY c.request_date DESC, c.case_id LIMIT ?"
    params.append(limit)
    rows = many_rows(sql, tuple(params))
    return {"count": len(rows), "cases": rows}


def case_detail(case_id: str) -> dict[str, Any] | None:
    case = one_row(
        """
        SELECT c.*, m.patient_name, m.dob, m.plan_id, m.plan_type, m.product, m.employer_group,
               m.member_status, p.provider_name, p.specialty, p.npi, p.phone, p.fax, p.organization
        FROM cases c
        JOIN members m ON m.member_id = c.member_id
        JOIN providers p ON p.provider_id = c.provider_id
        WHERE c.case_id = ?
        """,
        (case_id,),
    )
    if case is None:
        return None
    detail = dict(case)
    detail["request_lines"] = many_rows("SELECT * FROM request_lines WHERE case_id = ? ORDER BY line_id", (case_id,))
    detail["documents"] = many_rows(
        "SELECT * FROM documents WHERE case_id = ? ORDER BY received_date DESC, document_id", (case_id,)
    )
    detail["document_facts"] = many_rows(
        "SELECT * FROM document_facts WHERE case_id = ? ORDER BY document_id, fact_id", (case_id,)
    )
    detail["criteria"] = many_rows(
        """
        SELECT cc.*, pc.criterion_key, pc.criterion_text, pc.approval_required, pc.result_if_missing
        FROM case_criteria cc
        JOIN policy_criteria pc ON pc.criterion_id = cc.criterion_id
        WHERE cc.case_id = ?
        ORDER BY pc.criterion_id
        """,
        (case_id,),
    )
    detail["authorizations"] = many_rows("SELECT * FROM authorizations WHERE case_id = ? ORDER BY auth_id", (case_id,))
    detail["p2p_events"] = many_rows("SELECT * FROM p2p_events WHERE case_id = ? ORDER BY scheduled_at", (case_id,))
    detail["appeals"] = many_rows("SELECT * FROM appeals WHERE case_id = ? ORDER BY received_date", (case_id,))
    detail["drug_trials"] = many_rows("SELECT * FROM drug_trials WHERE case_id = ? ORDER BY trial_id", (case_id,))
    detail["assistance_screen"] = many_rows("SELECT * FROM assistance_screen WHERE case_id = ?", (case_id,))
    claims = many_rows("SELECT * FROM claims WHERE case_id = ? ORDER BY claim_id", (case_id,))
    for claim in claims:
        claim["lines"] = many_rows(
            "SELECT * FROM claim_lines WHERE claim_id = ? ORDER BY line_number", (claim["claim_id"],)
        )
    detail["claims"] = claims
    return detail


def list_policies(query: dict[str, list[str]]) -> dict[str, Any]:
    clauses: list[str] = []
    params: list[Any] = []
    if query.get("active_on"):
        clauses.append("effective_start <= ? AND effective_end >= ?")
        params.extend([query["active_on"][0], query["active_on"][0]])
    if query.get("q"):
        clauses.append("(policy_id LIKE ? OR policy_name LIKE ? OR summary LIKE ?)")
        needle = f"%{query['q'][0]}%"
        params.extend([needle, needle, needle])
    sql = "SELECT * FROM policies"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY precedence, policy_id"
    policies = many_rows(sql, tuple(params))
    return {"count": len(policies), "policies": policies}


def policy_detail(policy_id: str) -> dict[str, Any] | None:
    policy = one_row("SELECT * FROM policies WHERE policy_id = ?", (policy_id,))
    if policy is None:
        return None
    policy["criteria"] = many_rows(
        "SELECT * FROM policy_criteria WHERE policy_id = ? ORDER BY criterion_id", (policy_id,)
    )
    return policy


def document_detail(document_id: str) -> dict[str, Any] | None:
    document = one_row("SELECT * FROM documents WHERE document_id = ?", (document_id,))
    if document is None:
        return None
    document["facts"] = many_rows(
        "SELECT * FROM document_facts WHERE document_id = ? ORDER BY fact_id", (document_id,)
    )
    return document


def rate_schedules(query: dict[str, list[str]]) -> dict[str, Any]:
    filters = {
        "payer": "payer",
        "plan_type": "plan_type",
        "service_domain": "service_domain",
        "cpt_code": "cpt_code",
        "modifier": "modifier",
    }
    clauses: list[str] = []
    params: list[Any] = []
    for key, column in filters.items():
        if query.get(key):
            clauses.append(f"{column} = ?")
            params.append(query[key][0])
    if query.get("effective_on"):
        clauses.append("effective_start <= ? AND effective_end >= ?")
        params.extend([query["effective_on"][0], query["effective_on"][0]])
    sql = "SELECT * FROM payment_benchmarks"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += (
        " ORDER BY payer, plan_type, service_domain, cpt_code, COALESCE(modifier, ''), effective_start DESC LIMIT 500"
    )
    rows = many_rows(sql, tuple(params))
    return {"count": len(rows), "rate_schedules": rows}


def appeals(query: dict[str, list[str]]) -> dict[str, Any]:
    filters = {
        "case_id": "a.case_id",
        "appeal_path": "a.appeal_path",
        "outcome": "a.outcome",
        "owner": "a.owner",
    }
    clauses: list[str] = []
    params: list[Any] = []
    for key, column in filters.items():
        if query.get(key):
            clauses.append(f"{column} = ?")
            params.append(query[key][0])
    sql = """
        SELECT a.*, c.current_stage, c.current_status, c.urgency, c.summary,
               m.patient_name, m.plan_type
        FROM appeals a
        JOIN cases c ON c.case_id = a.case_id
        JOIN members m ON m.member_id = c.member_id
    """
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY a.appeal_deadline, a.appeal_id LIMIT 500"
    rows = many_rows(sql, tuple(params))
    return {"count": len(rows), "appeals": rows}


def execute_sql_query(payload: dict[str, Any], headers: Any) -> tuple[int, dict[str, Any]]:
    auth = headers.get("Authorization", "")
    if auth != f"Bearer {TOKEN}":
        return HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"}
    try:
        sql = validate_readonly_sql(payload.get("sql"))
        params = payload.get("params", [])
        if not isinstance(params, (list, tuple, dict)):
            raise ValueError("params must be a JSON array or object")
        with connect() as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchmany(MAX_SQL_ROWS + 1)
            columns = [description[0] for description in (cursor.description or [])]
            limited = len(rows) > MAX_SQL_ROWS
            rows = rows[:MAX_SQL_ROWS]
        return HTTPStatus.OK, {
            "columns": columns,
            "rows": rows_to_dicts(rows),
            "row_count": len(rows),
            "limited": limited,
            "max_rows": MAX_SQL_ROWS,
        }
    except sqlite3.Error as exc:
        return HTTPStatus.BAD_REQUEST, {"error": "sql_error", "message": str(exc)}
    except ValueError as exc:
        return HTTPStatus.BAD_REQUEST, {"error": "invalid_sql", "message": str(exc)}


class Handler(BaseHTTPRequestHandler):
    server_version = "NorthstarPA/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def send_bytes(self, status: int, content: bytes, content_type: str = "application/octet-stream") -> None:
        self.send_response(int(status))
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_bytes(status, body, "application/json; charset=utf-8")

    def read_json(self) -> dict[str, Any] | None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") if parsed.path != "/" else "/"
        query = parse_qs(parsed.query)
        try:
            if path == "/":
                self.send_bytes(HTTPStatus.OK, html_page(), "text/html; charset=utf-8")
            elif path == "/portal":
                self.send_bytes(HTTPStatus.OK, html_page(), "text/html; charset=utf-8")
            elif path == "/health":
                port = int(os.environ.get("TASK_ENV_PORT", str(DEFAULT_PORT)))
                self.send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "service": SERVICE,
                        "port": port,
                        "database_present": db_present(),
                        "judge_enabled": judge_enabled(),
                    },
                )
            elif path == "/api/tables":
                self.send_json(HTTPStatus.OK, table_catalog())
            elif path == "/api/cases":
                self.send_json(HTTPStatus.OK, list_cases(query))
            elif path.startswith("/api/cases/"):
                case_id = unquote(path.removeprefix("/api/cases/"))
                detail = case_detail(case_id)
                if detail is None:
                    self.send_json(HTTPStatus.NOT_FOUND, {"error": "case_not_found"})
                else:
                    self.send_json(HTTPStatus.OK, {"case": detail})
            elif path == "/api/policies":
                self.send_json(HTTPStatus.OK, list_policies(query))
            elif path.startswith("/api/policies/"):
                policy_id = unquote(path.removeprefix("/api/policies/"))
                detail = policy_detail(policy_id)
                if detail is None:
                    self.send_json(HTTPStatus.NOT_FOUND, {"error": "policy_not_found"})
                else:
                    self.send_json(HTTPStatus.OK, {"policy": detail})
            elif path.startswith("/api/documents/"):
                document_id = unquote(path.removeprefix("/api/documents/"))
                detail = document_detail(document_id)
                if detail is None:
                    self.send_json(HTTPStatus.NOT_FOUND, {"error": "document_not_found"})
                else:
                    self.send_json(HTTPStatus.OK, {"document": detail})
            elif path == "/api/rate-schedules":
                self.send_json(HTTPStatus.OK, rate_schedules(query))
            elif path == "/api/appeals":
                self.send_json(HTTPStatus.OK, appeals(query))
            else:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        except Exception as exc:
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "server_error", "message": str(exc)})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") if parsed.path != "/" else "/"
        payload = self.read_json()
        if payload is None:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return
        if path == "/sql/query":
            status, response = execute_sql_query(payload, self.headers)
            self.send_json(status, response)
            return
        if path == "/api/judge":
            if not judge_enabled():
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            try:
                response = score_train_answer(str(payload.get("task_id", "")), payload.get("answer"))
                self.send_json(HTTPStatus.OK, response)
            except JudgeError as exc:
                self.send_json(HTTPStatus.BAD_REQUEST, {"error": "rejected", "notice": str(exc)})
            return
        self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})


def main() -> None:
    ensure_database()
    bind = os.environ.get("TASK_ENV_BIND", "0.0.0.0")
    port = int(os.environ.get("TASK_ENV_PORT", str(DEFAULT_PORT)))
    server = ThreadingHTTPServer((bind, port), Handler)
    print(f"{SERVICE} listening on {bind}:{port}; judge_enabled={judge_enabled()}")
    server.serve_forever()


if __name__ == "__main__":
    main()
