#!/usr/bin/env python3
"""Flask service for the Investigation Review Hub environment."""

from __future__ import annotations

import os
import sqlite3
import threading
from typing import Any

from flask import Flask, jsonify, request
from generate_data import (
    DB_PATH,
    ENDPOINTS,
    JUDGE_DATA_PATH,
    MANIFEST_PATH,
    SEED,
    SERVICE_NAME,
    STATE_MODE,
    generate_all,
)


API_KEY = "review-key-017"
ADMIN_API_KEY = os.getenv("TASK_ENV_ADMIN_KEY", "admin-reset-key-017")
MAX_ROWS = 500
PUBLIC_TABLES = [
    "matters",
    "subpoena_categories",
    "production_stats",
    "custodian_sources",
    "review_documents",
    "privilege_entries",
    "qc_findings",
    "retention_events",
    "remediation_actions",
]
CSV_FIELDS = {"topic_tags", "category_impacts", "issue_tags", "affected_categories"}
RESET_LOCK = threading.Lock()


def get_bind() -> str:
    return os.getenv("TASK_ENV_BIND", "0.0.0.0")


def get_port() -> int:
    raw = os.getenv("TASK_ENV_PORT", "9017")
    try:
        return int(raw)
    except ValueError:
        return 9017


def judge_enabled() -> bool:
    return os.getenv("TASK_ENV_ENABLE_JUDGE", "0") == "1"


def ensure_data() -> None:
    if not DB_PATH.exists() or not MANIFEST_PATH.exists():
        generate_all()


def db_connect() -> sqlite3.Connection:
    ensure_data()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def require_api_key() -> tuple[bool, Any]:
    if request.headers.get("X-API-Key") != API_KEY:
        return False, (jsonify({"error": "unauthorized"}), 401)
    return True, None


def require_admin_key() -> tuple[bool, Any]:
    if request.headers.get("X-Admin-Key") != ADMIN_API_KEY:
        return False, (jsonify({"error": "unauthorized"}), 401)
    return True, None


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    for field in CSV_FIELDS:
        if field in result:
            value = result[field] or ""
            result[field] = [part for part in value.split(",") if part]
    return result


def parse_limit(default: int = 100) -> int:
    raw = request.args.get("limit", str(default))
    try:
        value = int(raw)
    except ValueError:
        value = default
    return max(1, min(MAX_ROWS, value))


def add_exact_filters(where: list[str], params: list[Any], filters: dict[str, str]) -> None:
    for arg_name, column in filters.items():
        value = request.args.get(arg_name)
        if value not in (None, ""):
            where.append(f"{column} = ?")
            params.append(value)


def add_like_filter(where: list[str], params: list[Any], arg_name: str, columns: list[str]) -> None:
    value = request.args.get(arg_name)
    if value in (None, ""):
        return
    clauses = [f"LOWER({column}) LIKE ?" for column in columns]
    where.append("(" + " OR ".join(clauses) + ")")
    params.extend([f"%{value.lower()}%" for _ in columns])


def select_rows(
    table: str,
    *,
    exact_filters: dict[str, str] | None = None,
    like_filters: dict[str, list[str]] | None = None,
    order_by: str,
    default_limit: int = 100,
) -> Any:
    where: list[str] = []
    params: list[Any] = []
    add_exact_filters(where, params, exact_filters or {})
    for arg_name, columns in (like_filters or {}).items():
        add_like_filter(where, params, arg_name, columns)

    sql = f"SELECT * FROM {table}"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY {order_by} LIMIT ?"
    params.append(parse_limit(default_limit))

    with db_connect() as conn:
        rows = [row_to_dict(row) for row in conn.execute(sql, params).fetchall()]
    return jsonify({"count": len(rows), "rows": rows})


def count_rows() -> dict[str, int]:
    with db_connect() as conn:
        return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in PUBLIC_TABLES}


def reject_if_not_single_select(sql: str) -> tuple[bool, str, str]:
    if not isinstance(sql, str) or not sql.strip():
        return False, "", "sql must be a non-empty string"
    if "--" in sql or "/*" in sql or "*/" in sql:
        return False, "", "comments are not permitted"

    cleaned = sql.strip()
    semicolon_index = _single_trailing_semicolon_index(cleaned)
    if semicolon_index is None:
        return False, "", "only one SELECT statement is permitted"
    if semicolon_index >= 0:
        cleaned = cleaned[:semicolon_index].strip()

    lowered = " ".join(cleaned.lower().split())
    if not lowered.startswith("select "):
        return False, "", "only SELECT statements are permitted"

    blocked = [
        " sqlite_",
        "sqlite_master",
        "sqlite_schema",
        "pragma",
        "attach",
        "detach",
        "insert",
        "update",
        "delete",
        "replace",
        "drop",
        "alter",
        "create",
        "vacuum",
        "reindex",
        "load_extension",
        "readfile",
        "writefile",
    ]
    padded = f" {lowered} "
    for token in blocked:
        if token in padded:
            return False, "", "query references a blocked operation or internal object"
    return True, cleaned, ""


def _single_trailing_semicolon_index(sql: str) -> int | None:
    in_single = False
    in_double = False
    semicolon_positions: list[int] = []
    i = 0
    while i < len(sql):
        char = sql[i]
        if char == "'" and not in_double:
            if in_single and i + 1 < len(sql) and sql[i + 1] == "'":
                i += 2
                continue
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == ";" and not in_single and not in_double:
            semicolon_positions.append(i)
        i += 1
    if not semicolon_positions:
        return -1
    if len(semicolon_positions) > 1:
        return None
    semicolon_index = semicolon_positions[0]
    if sql[semicolon_index + 1 :].strip():
        return None
    return semicolon_index


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    ensure_data()

    @app.get("/health")
    def health():
        return jsonify(
            {
                "service": SERVICE_NAME,
                "status": "ok",
                "seed": SEED,
                "state_mode": STATE_MODE,
                "port": get_port(),
                "judge_enabled": judge_enabled(),
                "row_counts": count_rows(),
            }
        )

    @app.get("/")
    def index():
        orchestration_only = {"GET /health", "POST /admin/reset", "POST /api/judge"}
        enabled_endpoints = [endpoint for endpoint in ENDPOINTS if endpoint not in orchestration_only]
        return jsonify(
            {
                "service": SERVICE_NAME,
                "status": "ok",
                "state_mode": STATE_MODE,
                "business_endpoints": enabled_endpoints,
            }
        )

    @app.get("/api/schema")
    def schema():
        with db_connect() as conn:
            tables = []
            for table in PUBLIC_TABLES:
                columns = [
                    {"name": row["name"], "type": row["type"]}
                    for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
                ]
                tables.append({"table": table, "columns": columns})
        return jsonify({"tables": tables})

    @app.get("/api/matters")
    def matters():
        return select_rows(
            "matters",
            exact_filters={
                "matter_id": "matter_id",
                "agency": "agency",
                "investigation_type": "investigation_type",
                "status": "status",
            },
            like_filters={"q": ["matter_id", "name", "agency", "description", "lead_partner"]},
            order_by="matter_id",
            default_limit=100,
        )

    @app.get("/api/subpoena-categories")
    def subpoena_categories():
        return select_rows(
            "subpoena_categories",
            exact_filters={"matter_id": "matter_id", "category_code": "category_code"},
            like_filters={"q": ["category_code", "title", "request_text", "topic_tags"], "topic_tag": ["topic_tags"]},
            order_by="matter_id, category_code",
            default_limit=150,
        )

    @app.get("/api/productions")
    def productions():
        return select_rows(
            "production_stats",
            exact_filters={
                "matter_id": "matter_id",
                "category_code": "category_code",
                "batch_id": "batch_id",
                "status": "status",
            },
            like_filters={"q": ["notes", "zero_claim_reason"]},
            order_by="matter_id, batch_date, batch_id, category_code",
            default_limit=150,
        )

    @app.get("/api/custodian-sources")
    def custodian_sources():
        return select_rows(
            "custodian_sources",
            exact_filters={
                "matter_id": "matter_id",
                "custodian_name": "custodian_name",
                "status": "status",
                "source_type": "source_type",
            },
            like_filters={
                "q": ["source_id", "custodian_name", "source_label", "issue_tags", "notes"],
                "issue_type": ["issue_tags"],
                "category_code": ["category_impacts"],
            },
            order_by="matter_id, custodian_name, source_id",
            default_limit=150,
        )

    @app.get("/api/documents/search")
    def documents_search():
        if request.args.get("matter_id") in (None, "") and request.args.get("q") in (None, ""):
            return jsonify({"error": "matter_id or q is required"}), 400
        return select_rows(
            "review_documents",
            exact_filters={
                "matter_id": "matter_id",
                "category_code": "category_code",
                "custodian_name": "custodian_name",
                "responsiveness": "responsiveness",
                "privilege_status": "privilege_status",
                "produced_status": "produced_status",
            },
            like_filters={
                "q": ["doc_id", "title", "summary", "issue_tags", "category_code", "custodian_name"],
                "issue_type": ["issue_tags"],
            },
            order_by="matter_id, doc_date DESC, doc_id",
            default_limit=100,
        )

    @app.get("/api/privilege-log")
    def privilege_log():
        return select_rows(
            "privilege_entries",
            exact_filters={
                "matter_id": "matter_id",
                "category_code": "category_code",
                "custodian_name": "custodian_name",
                "issue_type": "issue_type",
                "third_party": "third_party",
            },
            like_filters={"q": ["entry_id", "notes", "custodian_name"]},
            order_by="matter_id, issue_type, entry_id",
            default_limit=150,
        )

    @app.get("/api/qc-findings")
    def qc_findings():
        return select_rows(
            "qc_findings",
            exact_filters={
                "matter_id": "matter_id",
                "batch_id": "batch_id",
                "issue_type": "issue_type",
                "severity": "severity",
                "affected_category": "affected_category",
            },
            like_filters={"q": ["finding_id", "source_ref", "notes"]},
            order_by="matter_id, severity DESC, finding_id",
            default_limit=150,
        )

    @app.get("/api/retention-events")
    def retention_events():
        return select_rows(
            "retention_events",
            exact_filters={
                "matter_id": "matter_id",
                "record_type": "record_type",
                "status": "status",
            },
            like_filters={
                "q": ["event_id", "record_type", "affected_categories", "source_ref", "notes"],
                "category_code": ["affected_categories"],
            },
            order_by="matter_id, event_date, event_id",
            default_limit=150,
        )

    @app.get("/api/remediation-actions")
    def remediation_actions():
        return select_rows(
            "remediation_actions",
            exact_filters={
                "matter_id": "matter_id",
                "action_type": "action_type",
                "priority": "priority",
                "severity": "severity",
                "owner": "owner",
                "target_ref": "target_ref",
            },
            like_filters={"q": ["action_id", "description", "target_ref", "owner"]},
            order_by="matter_id, priority, due_days, action_id",
            default_limit=150,
        )

    @app.post("/api/query")
    def query():
        ok, response = require_api_key()
        if not ok:
            return response
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "invalid JSON body"}), 400
        sql = payload.get("sql")
        valid, cleaned_sql, error = reject_if_not_single_select(sql)
        if not valid:
            return jsonify({"error": error}), 400
        params = payload.get("params", [])
        if not isinstance(params, (list, dict)):
            return jsonify({"error": "params must be a list or object"}), 400
        try:
            with db_connect() as conn:
                cursor = conn.execute(cleaned_sql, params)
                rows = cursor.fetchmany(MAX_ROWS + 1)
                columns = [description[0] for description in cursor.description or []]
        except sqlite3.Error as exc:
            return jsonify({"error": "query failed", "detail": str(exc)}), 400

        capped = rows[:MAX_ROWS]
        result_rows = [dict(row) for row in capped]
        return jsonify(
            {
                "columns": columns,
                "rows": result_rows,
                "row_count": len(result_rows),
                "truncated": len(rows) > MAX_ROWS,
            }
        )

    @app.post("/admin/reset")
    def admin_reset():
        ok, response = require_admin_key()
        if not ok:
            return response
        with RESET_LOCK:
            manifest = generate_all()
        return jsonify(
            {
                "status": "reset",
                "seed": SEED,
                "state_mode": STATE_MODE,
                "row_counts": manifest["table_counts"],
            }
        )

    if judge_enabled():
        from judge_api import register_judge

        register_judge(app, JUDGE_DATA_PATH)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=get_bind(), port=get_port())
