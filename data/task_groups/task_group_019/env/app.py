import os
import re
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, request
from generate_data import generate
from judge_api import register_judge


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "licensing.db"
SQL_TOKEN = "licensing-review-019"
OPERATOR_RESET_TOKEN = "licensing-review-019-operator-reset"
DEFAULT_LIMIT = 200
MAX_LIMIT = 1000
HIDDEN_COLUMNS = {"target_group"}

ENDPOINT_TABLES = {
    "/api/policies": "policies",
    "/api/contractor/applications": "contractor_applications",
    "/api/contractor/bonds": "contractor_bonds",
    "/api/contractor/insurance": "contractor_insurance",
    "/api/contractor/license-history": "contractor_license_history",
    "/api/contractor/violations": "contractor_violations",
    "/api/contractor/correspondence": "contractor_correspondence",
    "/api/contractor/inspections": "contractor_inspections",
    "/api/liquor/applications": "liquor_applications",
    "/api/liquor/settlements": "liquor_settlements",
    "/api/liquor/privileges": "liquor_privileges",
    "/api/liquor/incidents": "liquor_incidents",
    "/api/liquor/site-evidence": "liquor_site_evidence",
    "/api/alcohol/licensees": "alcohol_licensees",
    "/api/alcohol/violations": "alcohol_violations",
    "/api/renewal/rules": "renewal_rules",
}

BLOCKED_SQL_PATTERNS = [
    r";",
    r"--",
    r"/\*",
    r"\bpragma\b",
    r"\battach\b",
    r"\bdetach\b",
    r"\binsert\b",
    r"\bupdate\b",
    r"\bdelete\b",
    r"\bdrop\b",
    r"\balter\b",
    r"\bcreate\b",
    r"\breplace\b",
    r"\btruncate\b",
    r"\bvacuum\b",
    r"\breindex\b",
    r"\banalyze\b",
    r"\bload_extension\b",
    r"\breadfile\b",
    r"\bwritefile\b",
    r"\bsqlite_",
    r"\btarget_group\b",
]


def ensure_database():
    if not DB_PATH.exists():
        generate(DATA_DIR)


def connect_readonly():
    uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def connect_operator():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def table_columns(table, include_hidden=False):
    with connect_readonly() as conn:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    columns = [row["name"] for row in rows]
    if include_hidden:
        return columns
    return [column for column in columns if column not in HIDDEN_COLUMNS]


def parse_limit(args):
    raw_limit = args.get("limit", DEFAULT_LIMIT)
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        raise ValueError("limit must be an integer")
    if limit < 1:
        raise ValueError("limit must be at least 1")
    return min(limit, MAX_LIMIT)


def rows_to_dicts(rows):
    return [dict(row) for row in rows]


def is_hidden_result_column(column_name):
    normalized = str(column_name or "").strip().strip('"`[]').lower()
    unqualified = normalized.rsplit(".", 1)[-1]
    return unqualified in HIDDEN_COLUMNS


def sql_rows_to_response(columns, rows):
    visible_indexes = [idx for idx, column in enumerate(columns) if not is_hidden_result_column(column)]
    visible_columns = [columns[idx] for idx in visible_indexes]
    visible_rows = []
    for row in rows:
        visible_rows.append({columns[idx]: row[idx] for idx in visible_indexes})
    return visible_columns, visible_rows


def validate_sql(query):
    if not isinstance(query, str) or not query.strip():
        return "query must be a non-empty string"
    stripped = query.strip()
    if not re.match(r"(?is)^select\b", stripped):
        return "only SELECT statements are allowed"
    lowered = stripped.lower()
    for pattern in BLOCKED_SQL_PATTERNS:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            return "query uses a blocked SQL construct"
    return None


def create_app():
    ensure_database()
    app = Flask(__name__)

    @app.get("/health")
    def health():
        counts = {}
        ok = True
        try:
            with connect_readonly() as conn:
                for table in ENDPOINT_TABLES.values():
                    counts[table] = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
        except sqlite3.Error:
            ok = False
        status = 200 if ok else 503
        return jsonify({"status": "ok" if ok else "error", "database": ok, "counts": counts}), status

    def business_endpoint(table):
        try:
            limit = parse_limit(request.args)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        columns = table_columns(table)
        column_set = set(columns)
        filters = []
        values = []
        for key, value in request.args.items():
            if key == "limit":
                continue
            if key not in column_set:
                return jsonify({"error": f"unknown filter field: {key}"}), 400
            filters.append(f"{key} = ?")
            values.append(value)
        where = f" WHERE {' AND '.join(filters)}" if filters else ""
        select_columns = ", ".join(columns)
        query = f"SELECT {select_columns} FROM {table}{where} ORDER BY 1 LIMIT ?"
        values.append(limit)
        with connect_readonly() as conn:
            rows = conn.execute(query, values).fetchall()
        return jsonify(rows_to_dicts(rows))

    for route, table in ENDPOINT_TABLES.items():
        app.add_url_rule(route, route, lambda table=table: business_endpoint(table), methods=["GET"])

    @app.post("/api/sql")
    def sql_query():
        if request.headers.get("X-Task-Token") != SQL_TOKEN:
            return jsonify({"error": "missing or invalid X-Task-Token"}), 401
        body = request.get_json(silent=True) or {}
        query = body.get("query")
        params = body.get("params", [])
        if not isinstance(params, list):
            return jsonify({"error": "params must be a JSON list"}), 400
        validation_error = validate_sql(query)
        if validation_error:
            return jsonify({"error": validation_error}), 400
        try:
            row_limit = min(int(body.get("limit", DEFAULT_LIMIT) or DEFAULT_LIMIT), MAX_LIMIT)
        except (TypeError, ValueError):
            return jsonify({"error": "limit must be an integer"}), 400
        if row_limit < 1:
            return jsonify({"error": "limit must be at least 1"}), 400
        try:
            with connect_readonly() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchmany(row_limit + 1)
                columns = [description[0] for description in cursor.description or []]
        except (sqlite3.Error, ValueError, TypeError) as exc:
            return jsonify({"error": f"query failed: {exc}"}), 400
        truncated = len(rows) > row_limit
        rows = rows[:row_limit]
        columns, response_rows = sql_rows_to_response(columns, rows)
        return jsonify(
            {
                "columns": columns,
                "rows": response_rows,
                "row_count": len(rows),
                "truncated": truncated,
                "limit": row_limit,
            }
        )

    @app.post("/operator/reset")
    def operator_reset():
        if request.headers.get("X-Operator-Token") != OPERATOR_RESET_TOKEN:
            return jsonify({"error": "missing or invalid X-Operator-Token"}), 401
        manifest = generate(DATA_DIR)
        return jsonify({"status": "reset", "seed": manifest["seed"], "counts": manifest["counts"]})

    if os.environ.get("TASK_ENV_ENABLE_JUDGE") == "1":
        register_judge(app, DATA_DIR)

    return app


if __name__ == "__main__":
    bind = os.environ.get("TASK_ENV_BIND", "0.0.0.0")
    port = int(os.environ.get("TASK_ENV_PORT", "9019"))
    create_app().run(host=bind, port=port)
