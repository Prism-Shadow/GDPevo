#!/usr/bin/env python3
"""Authenticated network-only HTTP interface for the Atlas SQLite workplace."""

from __future__ import annotations

import hmac
import ipaddress
import json
import os
import re
import shutil
import sqlite3
import tempfile
import threading
import time
from contextlib import closing
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlsplit

from judge_api import TRAIN_TASK_IDS, evaluate_train_answer


SCHEMA_VERSION = "atlas-commerce-1.0"
MAX_BODY_BYTES = 1_048_576
MAX_QUERY_ROWS = 5000
MAX_AUDIT_ROWS = 1000
QUERY_SECONDS = 3.0
QUERY_PROGRESS_STEPS = 2_000_000

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.environ.get("TASK_ENV_DATABASE", "/var/lib/atlas/atlas_runtime.sqlite3"))
BASELINE_PATH = Path(os.environ.get("TASK_ENV_BASELINE", str(BASE_DIR / "atlas_baseline.sqlite3")))
BUSINESS_TOKEN = os.environ.get("TASK_ENV_API_TOKEN", "atlas-ops-token-022")
OPERATOR_TOKEN = os.environ.get("TASK_ENV_OPERATOR_TOKEN", "atlas-operator-022")
JUDGE_ENABLED = os.environ.get("TASK_ENV_ENABLE_JUDGE", "0") == "1"
JUDGE_SPEC_PATH = Path(os.environ.get("TASK_ENV_JUDGE_SPECS", str(BASE_DIR / "train_judge_specs.json")))

MUTATION_LOCK = threading.RLock()

TABLE_DESCRIPTIONS = {
    "accounts": "Customer and company account master data, including production-exclusion flags.",
    "campaigns": "Marketing campaign names, active windows, and acquisition channels.",
    "warehouses": "Fulfillment facilities with regional business-clock attributes.",
    "employees": "Warehouse employees, team assignments, roles, and active periods.",
    "products": "Sellable SKU master data and physical unit packaging.",
    "fx_rates": "Daily currency conversion rates expressed as USD per currency unit.",
    "orders": "Order headers and denormalized current status snapshots.",
    "order_lines": "SKU quantities requested on each order.",
    "order_events": "Imported append-only order lifecycle events.",
    "shipments": "Physical shipment headers associated with orders.",
    "carrier_scans": "Imported carrier observations with raw and normalized event values.",
    "payment_events": "Imported payment authorization, settlement, void, and reversal events.",
    "refund_attempts": "Provider refund attempts, retries, outcomes, and linked reversals.",
    "support_cases": "Support case headers and denormalized current ownership/state.",
    "case_events": "Imported append-only support case lifecycle events.",
    "warehouse_tasks": "Operational warehouse work assignments and planning attributes.",
    "warehouse_task_events": "Imported append-only execution events for warehouse work.",
    "inventory_movements": "Imported stock movements with source quantities and normalized each-unit values.",
    "inventory_snapshots": "Periodic point-in-time stock and reservation observations.",
    "source_import_batches": "Operational source-ingestion batches and their completion metadata.",
    "correction_audit": "Public audit records appended for controlled canonical corrections.",
}

COLUMN_DESCRIPTIONS = {
    "raw_quantity": "Signed quantity exactly as supplied by the source.",
    "raw_uom": "Source unit of measure, such as EA or CASE.",
    "raw_uom_multiplier": "Source-declared number of each units per raw unit.",
    "canonical_quantity_each": "Normalized signed quantity measured in individual each units.",
    "canonical_uom_multiplier": "Normalized number of each units per raw unit.",
    "raw_status": "Status text exactly as supplied by the carrier.",
    "raw_event_at": "Event timestamp exactly as supplied by the carrier, encoded in UTC.",
    "canonical_status": "Normalized carrier status used by operational analytics.",
    "canonical_event_at": "Normalized carrier event timestamp encoded in UTC.",
    "gross_amount_minor": "Order gross value in the smallest unit of the order currency.",
    "amount_minor": "Monetary value in the smallest unit of the named currency.",
    "usd_per_unit": "USD value of one unit of the named currency for the rate date.",
    "metadata_json": "Source event attributes encoded as a JSON object string.",
    "source_system": "Stable identifier for the upstream system that supplied the row.",
    "external_event_id": "Upstream event identifier that can recur on import retries.",
    "ingested_at": "UTC timestamp when this copy reached the workplace database.",
    "current_status": "Convenience snapshot that may lag append-only event history.",
    "corrected_at": "UTC timestamp of an approved canonical correction, or null.",
    "correction_reason": "Short reason recorded for an approved canonical correction, or null.",
    "correction_key": "Caller-provided unique idempotency key for one correction audit record.",
    "old_value": "Text representation of the value before correction.",
    "new_value": "Text representation of the value after correction.",
}

ALLOWED_UPDATE_FIELDS = {
    "carrier_scans": {"canonical_status", "canonical_event_at", "corrected_at", "correction_reason"},
    "inventory_movements": {"canonical_quantity_each", "canonical_uom_multiplier", "corrected_at", "correction_reason"},
}
BUSINESS_UPDATE_FIELDS = {
    "carrier_scans": {"canonical_status", "canonical_event_at"},
    "inventory_movements": {"canonical_quantity_each", "canonical_uom_multiplier"},
}
PRIMARY_GUARDS = {"carrier_scans": "scan_row_id", "inventory_movements": "movement_row_id"}
AUDIT_COLUMNS = {
    "audit_id", "correction_key", "entity_type", "entity_id", "source_row_id",
    "field_name", "old_value", "new_value", "reason_code", "corrected_at", "actor",
}


class RequestProblem(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def connect(read_only: bool = False) -> sqlite3.Connection:
    if read_only:
        connection = sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True, timeout=5.0)
    else:
        connection = sqlite3.connect(DATABASE_PATH, timeout=5.0)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def _scan_sql(sql: str) -> tuple[str, bool, bool]:
    """Mask quoted text and report comments/statement delimiters outside it."""
    result: list[str] = []
    index = 0
    comment = False
    semicolon = False
    length = len(sql)
    while index < length:
        char = sql[index]
        if char in ("'", '"', "`", "["):
            end_char = "]" if char == "[" else char
            result.append(" ")
            index += 1
            while index < length:
                result.append(" ")
                if sql[index] == end_char:
                    if end_char in ("'", '"', "`") and index + 1 < length and sql[index + 1] == end_char:
                        result.append(" ")
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            else:
                raise RequestProblem(400, "query rejected")
            continue
        if char == "-" and index + 1 < length and sql[index + 1] == "-":
            comment = True
            result.extend("  ")
            index += 2
            while index < length and sql[index] not in "\r\n":
                result.append(" ")
                index += 1
            continue
        if char == "/" and index + 1 < length and sql[index + 1] == "*":
            comment = True
            result.extend("  ")
            index += 2
            while index + 1 < length and sql[index:index + 2] != "*/":
                result.append(" ")
                index += 1
            if index + 1 >= length:
                raise RequestProblem(400, "query rejected")
            result.extend("  ")
            index += 2
            continue
        if char == ";":
            semicolon = True
        result.append(char)
        index += 1
    return "".join(result), comment, semicolon


def _validate_sql_envelope(sql: Any) -> tuple[str, str]:
    if not isinstance(sql, str) or not sql.strip() or len(sql) > 100_000 or "\x00" in sql:
        raise RequestProblem(400, "query rejected")
    masked, has_comment, has_semicolon = _scan_sql(sql)
    if has_comment or has_semicolon:
        raise RequestProblem(400, "query rejected")
    return sql.strip(), masked.strip()


def validate_select(sql: Any) -> str:
    clean, masked = _validate_sql_envelope(sql)
    first = re.match(r"(?is)^(SELECT|WITH)\b", masked)
    if not first:
        raise RequestProblem(400, "query rejected")
    forbidden = r"\b(PRAGMA|ATTACH|DETACH|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|REPLACE|VACUUM|REINDEX|ANALYZE)\b"
    if re.search(forbidden, masked, re.IGNORECASE):
        raise RequestProblem(400, "query rejected")
    if re.search(r"\b(load_extension|readfile|writefile|fts3_tokenizer)\s*\(", masked, re.IGNORECASE):
        raise RequestProblem(400, "query rejected")
    return clean


def validate_params(params: Any) -> list[Any]:
    if params is None:
        return []
    if not isinstance(params, list) or len(params) > 200:
        raise RequestProblem(400, "invalid request")
    for value in params:
        if value is not None and not isinstance(value, (str, int, float, bool)):
            raise RequestProblem(400, "invalid request")
    return params


def _query_rows(connection: sqlite3.Connection, sql: str, params: list[Any], limit: int = MAX_QUERY_ROWS) -> dict[str, Any]:
    deadline = time.monotonic() + QUERY_SECONDS
    progress_calls = 0

    def progress() -> int:
        nonlocal progress_calls
        progress_calls += 1000
        return 1 if progress_calls > QUERY_PROGRESS_STEPS or time.monotonic() > deadline else 0

    connection.set_progress_handler(progress, 1000)
    try:
        cursor = connection.execute(sql, params)
        if cursor.description is None:
            raise RequestProblem(400, "query rejected")
        columns = [description[0] for description in cursor.description]
        fetched = cursor.fetchmany(limit + 1)
        truncated = len(fetched) > limit
        rows = [list(row) for row in fetched[:limit]]
        return {"columns": columns, "rows": rows, "row_count": len(rows), "truncated": truncated}
    except RequestProblem:
        raise
    except sqlite3.Error:
        raise RequestProblem(400, "query rejected") from None
    finally:
        connection.set_progress_handler(None, 0)


def _split_csv(value: str) -> list[str]:
    fields: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    index = 0
    while index < len(value):
        char = value[index]
        if quote:
            if char == quote:
                if index + 1 < len(value) and value[index + 1] == quote:
                    index += 2
                    continue
                quote = None
        elif char in ("'", '"'):
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            fields.append(value[start:index].strip())
            start = index + 1
        index += 1
    fields.append(value[start:].strip())
    if quote or depth != 0 or any(not field for field in fields):
        raise RequestProblem(400, "transaction rejected")
    return fields


SIMPLE_VALUE = re.compile(r"(?is)^(?:\?|NULL|[-+]?\d+(?:\.\d+)?|'(?:''|[^'])*')$")


def validate_update(sql: Any) -> str:
    clean, masked = _validate_sql_envelope(sql)
    match = re.match(r"(?is)^UPDATE\s+(carrier_scans|inventory_movements)\s+SET\s+(.+?)\s+WHERE\s+(.+)$", clean)
    masked_match = re.match(r"(?is)^UPDATE\s+(carrier_scans|inventory_movements)\s+SET\s+(.+?)\s+WHERE\s+(.+)$", masked)
    if not match or not masked_match or match.group(1).lower() != masked_match.group(1).lower():
        raise RequestProblem(400, "transaction rejected")
    table = match.group(1).lower()
    assignments = _split_csv(match.group(2))
    updated_fields: set[str] = set()
    for assignment in assignments:
        assignment_match = re.match(r"(?is)^([a-z_][a-z0-9_]*)\s*=\s*(.+)$", assignment)
        if not assignment_match:
            raise RequestProblem(400, "transaction rejected")
        field = assignment_match.group(1).lower()
        if field in updated_fields or field not in ALLOWED_UPDATE_FIELDS[table] or not SIMPLE_VALUE.match(assignment_match.group(2).strip()):
            raise RequestProblem(400, "transaction rejected")
        updated_fields.add(field)
    business_fields = updated_fields & BUSINESS_UPDATE_FIELDS[table]
    if not business_fields:
        raise RequestProblem(400, "transaction rejected")
    where_masked = masked_match.group(3)
    if re.search(r"\b(OR|SELECT|UNION|EXISTS|IN|LIKE|GLOB|BETWEEN|CASE|JOIN)\b", where_masked, re.IGNORECASE):
        raise RequestProblem(400, "transaction rejected")
    primary = PRIMARY_GUARDS[table]
    if not re.search(rf"\b{primary}\s*=\s*\?", where_masked, re.IGNORECASE):
        raise RequestProblem(400, "transaction rejected")
    for field in business_fields:
        if not re.search(rf"\b{field}\s*(?:=|IS)\s*\?", where_masked, re.IGNORECASE):
            raise RequestProblem(400, "transaction rejected")
    if re.search(r"\b(DELETE|INSERT|CREATE|ALTER|DROP|REPLACE|PRAGMA|ATTACH|DETACH)\b", masked, re.IGNORECASE):
        raise RequestProblem(400, "transaction rejected")
    return clean


def validate_audit_insert(sql: Any) -> str:
    clean, _masked = _validate_sql_envelope(sql)
    match = re.match(r"(?is)^INSERT\s+INTO\s+correction_audit\s*\(([^)]+)\)\s*VALUES\s*\((.*)\)\s*$", clean)
    if not match:
        raise RequestProblem(400, "transaction rejected")
    columns = [column.strip().lower() for column in match.group(1).split(",")]
    values = _split_csv(match.group(2))
    if len(columns) != len(values) or set(columns) != AUDIT_COLUMNS or len(columns) != len(AUDIT_COLUMNS):
        raise RequestProblem(400, "transaction rejected")
    if any(not re.match(r"^[a-z_][a-z0-9_]*$", column) for column in columns):
        raise RequestProblem(400, "transaction rejected")
    if any(not SIMPLE_VALUE.match(value) for value in values):
        raise RequestProblem(400, "transaction rejected")
    return clean


def classify_transaction_sql(sql: Any) -> tuple[str, str]:
    if not isinstance(sql, str):
        raise RequestProblem(400, "transaction rejected")
    masked, _comment, _semi = _scan_sql(sql)
    first_match = re.match(r"(?is)^\s*([a-z]+)\b", masked)
    if not first_match:
        raise RequestProblem(400, "transaction rejected")
    first = first_match.group(1).upper()
    if first in ("SELECT", "WITH"):
        return "select", validate_select(sql)
    if first == "UPDATE":
        return "update", validate_update(sql)
    if first == "INSERT":
        return "insert", validate_audit_insert(sql)
    raise RequestProblem(400, "transaction rejected")


def run_transaction(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise RequestProblem(400, "invalid request")
    statements = payload.get("statements")
    expected = payload.get("expected_total_changes")
    if not isinstance(statements, list) or not 1 <= len(statements) <= 6:
        raise RequestProblem(400, "invalid request")
    if isinstance(expected, bool) or not isinstance(expected, int) or expected < 0 or expected > 12:
        raise RequestProblem(400, "invalid request")
    prepared: list[tuple[str, str, list[Any]]] = []
    for statement in statements:
        if not isinstance(statement, dict) or set(statement) - {"sql", "params"}:
            raise RequestProblem(400, "invalid request")
        kind, sql = classify_transaction_sql(statement.get("sql"))
        prepared.append((kind, sql, validate_params(statement.get("params", []))))

    with MUTATION_LOCK:
        connection = connect(read_only=False)
        results: list[dict[str, Any]] = []
        total_changes = 0
        try:
            connection.execute("BEGIN IMMEDIATE")
            for kind, sql, params in prepared:
                if kind == "select":
                    query_result = _query_rows(connection, sql, params)
                    results.append({"type": "select", **query_result})
                    continue
                before = connection.total_changes
                cursor = connection.execute(sql, params)
                changed = connection.total_changes - before
                if kind == "update" and changed > 1:
                    raise RequestProblem(409, "transaction rejected")
                if kind == "insert" and changed != 1:
                    raise RequestProblem(409, "transaction rejected")
                total_changes += changed
                results.append({"type": kind, "changes": changed})
            if total_changes != expected:
                raise RequestProblem(409, "expected change count mismatch")
            connection.commit()
            return {"total_changes": total_changes, "statements": results}
        except RequestProblem:
            connection.rollback()
            raise
        except sqlite3.Error:
            connection.rollback()
            raise RequestProblem(409, "transaction rejected") from None
        finally:
            connection.close()


def schema_payload() -> dict[str, Any]:
    with closing(connect(read_only=True)) as connection:
        tables = [
            {"name": row[0], "ddl": row[1]}
            for row in connection.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        ]
        indexes = [
            {"name": row[0], "table": row[1], "ddl": row[2]}
            for row in connection.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL ORDER BY name")
        ]
    return {"schema_version": SCHEMA_VERSION, "tables": tables, "indexes": indexes}


def _column_description(name: str) -> str:
    if name in COLUMN_DESCRIPTIONS:
        return COLUMN_DESCRIPTIONS[name]
    if name.endswith("_at") or name in {"created_at", "starts_at", "ends_at", "active_from", "active_to", "occurred_at", "snapshot_at", "due_at", "promised_at", "shipped_at", "opened_at"}:
        return "ISO-8601 UTC timestamp; nullable only where the schema permits."
    if name.endswith("_date") or name == "rate_date":
        return "ISO calendar date in YYYY-MM-DD form."
    if name.startswith("is_"):
        return "Integer boolean: 1 means true and 0 means false."
    if name.endswith("_id") or name == "sku":
        return "Stable textual business or row identifier; relationships are shown in the schema."
    if "quantity" in name or name in {"units", "planned_units", "on_hand_each", "reserved_each"}:
        return "Integer unit quantity; fields ending in each are individual units."
    if name == "productive_minutes":
        return "Productive work duration in whole minutes."
    return name.replace("_", " ").capitalize() + "."


def dictionary_payload() -> dict[str, Any]:
    tables = []
    with closing(connect(read_only=True)) as connection:
        table_names = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        for table in table_names:
            columns = []
            for row in connection.execute(f'PRAGMA table_info("{table}")'):
                columns.append({"name": row[1], "type": row[2], "nullable": not bool(row[3] or row[5]), "description": _column_description(row[1])})
            tables.append({"name": table, "description": TABLE_DESCRIPTIONS[table], "columns": columns})
    return {
        "schema_version": SCHEMA_VERSION,
        "conventions": {
            "timestamps": "All stored timestamps use ISO-8601 UTC text ending in Z.",
            "dates": "Calendar dates use YYYY-MM-DD text.",
            "money": "Monetary minor fields use the smallest unit of the row currency; FX is USD per currency unit.",
            "source_rows": "Raw fields preserve source values; canonical fields hold normalized operational values.",
        },
        "tables": tables,
    }


def audit_payload(query: str) -> dict[str, Any]:
    parameters = parse_qs(query, keep_blank_values=True)
    allowed = {"entity_type", "entity_id", "source_row_id", "limit"}
    if set(parameters) - allowed or any(len(values) != 1 for values in parameters.values()):
        raise RequestProblem(400, "invalid request")
    clauses: list[str] = []
    values: list[Any] = []
    for field in ("entity_type", "entity_id", "source_row_id"):
        if field in parameters:
            value = parameters[field][0]
            if not value or len(value) > 200:
                raise RequestProblem(400, "invalid request")
            clauses.append(f"{field} = ?")
            values.append(value)
    try:
        limit = int(parameters.get("limit", ["100"])[0])
    except ValueError:
        raise RequestProblem(400, "invalid request") from None
    if limit < 1 or limit > MAX_AUDIT_ROWS:
        raise RequestProblem(400, "invalid request")
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    sql = "SELECT audit_id, correction_key, entity_type, entity_id, source_row_id, field_name, old_value, new_value, reason_code, corrected_at, actor FROM correction_audit" + where + " ORDER BY corrected_at DESC, audit_id LIMIT ?"
    values.append(limit)
    with closing(connect(read_only=True)) as connection:
        result = _query_rows(connection, sql, values, limit)
    return result


def reset_database() -> None:
    if not BASELINE_PATH.is_file():
        raise RequestProblem(503, "reset unavailable")
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MUTATION_LOCK:
        descriptor, temporary_name = tempfile.mkstemp(prefix="atlas-reset-", suffix=".sqlite3", dir=DATABASE_PATH.parent)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            shutil.copyfile(BASELINE_PATH, temporary)
            with closing(sqlite3.connect(temporary)) as check:
                if check.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise RequestProblem(503, "reset unavailable")
            os.replace(temporary, DATABASE_PATH)
        finally:
            temporary.unlink(missing_ok=True)


class AtlasHandler(BaseHTTPRequestHandler):
    server_version = "AtlasOps"
    sys_version = ""

    def log_message(self, _format: str, *args: object) -> None:
        return

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self, token: str) -> bool:
        expected = f"Bearer {token}"
        supplied = self.headers.get("Authorization", "")
        return hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8"))

    def _require_business(self) -> None:
        if not self._authorized(BUSINESS_TOKEN):
            raise RequestProblem(401, "unauthorized")

    def _body(self) -> Any:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise RequestProblem(415, "application/json required")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise RequestProblem(400, "invalid request") from None
        if length <= 0 or length > MAX_BODY_BYTES:
            raise RequestProblem(400, "invalid request")
        try:
            return json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise RequestProblem(400, "invalid request") from None

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlsplit(self.path)
        try:
            if parsed.path == "/health" and not parsed.query:
                self._json(200, {"status": "ok", "schema_version": SCHEMA_VERSION})
                return
            if parsed.path == "/api/schema" and not parsed.query:
                self._require_business()
                self._json(200, schema_payload())
                return
            if parsed.path == "/api/data-dictionary" and not parsed.query:
                self._require_business()
                self._json(200, dictionary_payload())
                return
            if parsed.path == "/api/correction-audit":
                self._require_business()
                self._json(200, audit_payload(parsed.query))
                return
            raise RequestProblem(404, "not found")
        except RequestProblem as problem:
            self._json(problem.status, {"error": problem.message})
        except Exception:
            self._json(500, {"error": "service error"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlsplit(self.path)
        try:
            if parsed.query:
                raise RequestProblem(404, "not found")
            if parsed.path == "/api/sql":
                self._require_business()
                payload = self._body()
                if not isinstance(payload, dict) or set(payload) - {"sql", "params"}:
                    raise RequestProblem(400, "invalid request")
                sql = validate_select(payload.get("sql"))
                params = validate_params(payload.get("params", []))
                with closing(connect(read_only=True)) as connection:
                    self._json(200, _query_rows(connection, sql, params))
                return
            if parsed.path == "/api/sql/transaction":
                self._require_business()
                self._json(200, run_transaction(self._body()))
                return
            if parsed.path == "/api/operator/reset":
                if not self._authorized(OPERATOR_TOKEN):
                    raise RequestProblem(401, "unauthorized")
                self._body()
                reset_database()
                self._json(200, {"status": "reset", "schema_version": SCHEMA_VERSION})
                return
            if parsed.path == "/api/judge" and JUDGE_ENABLED:
                self._require_business()
                payload = self._body()
                if not isinstance(payload, dict) or set(payload) != {"task_id", "answer"}:
                    raise RequestProblem(400, "invalid request")
                task_id = payload.get("task_id")
                answer = payload.get("answer")
                if not isinstance(task_id, str) or task_id not in TRAIN_TASK_IDS or not isinstance(answer, dict):
                    raise RequestProblem(400, "judge request rejected")
                self._json(200, evaluate_train_answer(task_id, answer, JUDGE_SPEC_PATH))
                return
            raise RequestProblem(404, "not found")
        except RequestProblem as problem:
            self._json(problem.status, {"error": problem.message})
        except Exception:
            self._json(500, {"error": "service error"})


def main() -> None:
    bind = os.environ.get("TASK_ENV_BIND", "0.0.0.0")
    port_text = os.environ.get("TASK_ENV_PORT", "9022")
    try:
        ipaddress.IPv4Address(bind)
        port = int(port_text)
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise SystemExit("invalid bind or port") from None
    if not DATABASE_PATH.is_file():
        raise SystemExit("runtime database is not initialized")
    server = ThreadingHTTPServer((bind, port), AtlasHandler)
    server.daemon_threads = True
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
