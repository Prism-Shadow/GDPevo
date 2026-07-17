#!/usr/bin/env python3
"""Read-only HTTP service for the Asteria Fleet Data Quality Hub."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import signal
import sqlite3
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from generate_data import PUBLIC_VIEWS, verify
from judge_api import JudgeError, TrainJudge, error_response


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "asteria_quality.db"
MANIFEST_PATH = BASE_DIR / "manifest.json"
TRUTH_PATH = BASE_DIR / "construction_truth.json"
QUERY_TOKEN = "asteria-read-021"
MAX_PAGE = 500
MAX_QUERY_ROWS = 2000
MAX_BODY = 1_000_000
QUERY_TIMEOUT_SECONDS = 2.0
ALLOWED_VIEWS = frozenset(PUBLIC_VIEWS)
VIEW_BASE_TABLES = {
    "v_contacts": "private_contacts",
    "v_fuel_transactions": "private_fuel_transactions",
    "v_freight_charges": "private_freight_charges",
    "v_maintenance_events": "private_maintenance_events",
    "v_reference_aliases": "private_reference_aliases",
    "v_unit_conversions": "private_unit_conversions",
    "v_fx_rates": "private_fx_rates",
    "v_source_snapshots": "private_source_snapshots",
}
PRIVATE_BASE_TABLES = frozenset(VIEW_BASE_TABLES.values())
SAFE_FUNCTIONS = frozenset({
    "abs", "avg", "coalesce", "count", "date", "datetime", "group_concat", "hex",
    "ifnull", "instr", "julianday", "length", "likely", "likelihood", "lower",
    "ltrim", "max", "min", "nullif", "printf", "quote", "random", "randomblob",
    "replace", "round", "rtrim", "sign", "strftime", "substr", "substring", "sum",
    "total", "trim", "typeof", "unicode", "unlikely", "upper", "zeroblob",
})
# Random functions are removed below: declarations stay explicit and easy to audit.
SAFE_FUNCTIONS = SAFE_FUNCTIONS - {"random", "randomblob"}

COLLECTION_VIEWS = {
    "contacts": "v_contacts",
    "fuel": "v_fuel_transactions",
    "freight": "v_freight_charges",
    "maintenance": "v_maintenance_events",
}

FIELD_MEANINGS = {
    "collection_id": "Business collection identifier.",
    "snapshot_id": "Source snapshot identifier.",
    "source_system": "Originating business system.",
    "business_updated_at": "Time the business record was updated.",
    "ingested_at": "Time the row entered this data hub.",
    "valid_from": "First business date on which the reference row applies.",
    "valid_to": "Last business date on which the reference row applies, if bounded.",
    "published_at": "Time the reference row was published.",
    "record_status": "Status supplied by the source record.",
    "snapshot_status": "Publication status supplied with the snapshot.",
    "verified_flag": "Whether the source marked the row as verified.",
    "factor": "Multiplier from the source unit to the canonical unit.",
    "usd_per_unit": "USD value of one currency unit for the stated date and status.",
}


class ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class HubState:
    def __init__(self) -> None:
        verification = verify(DB_PATH, MANIFEST_PATH, TRUTH_PATH)
        self.data_version = verification["database_sha256"][:16]
        self.view_counts = verification["views"]
        self.db_uri = f"file:{DB_PATH.resolve()}?mode=ro&immutable=1"
        self.judge_enabled = os.environ.get("TASK_ENV_ENABLE_JUDGE", "0") == "1"
        self.judge = TrainJudge(BASE_DIR / "judge_specs.json") if self.judge_enabled else None

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_uri, uri=True, timeout=1.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        return conn


def parse_date(value: str, name: str) -> str:
    try:
        parsed = dt.date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ApiError(400, "invalid filter") from exc
    if parsed.isoformat() != value:
        raise ApiError(400, "invalid filter")
    return value


def single(params: dict[str, list[str]], name: str, required: bool = False) -> str | None:
    values = params.get(name)
    if values is None:
        if required:
            raise ApiError(400, "invalid filter")
        return None
    if len(values) != 1 or (required and values[0] == ""):
        raise ApiError(400, "invalid filter")
    return values[0]


def ensure_params(params: dict[str, list[str]], allowed: set[str]) -> None:
    if set(params) - allowed:
        raise ApiError(400, "invalid filter")


def page(params: dict[str, list[str]]) -> tuple[int, int]:
    try:
        limit = int(single(params, "limit") or "100")
        offset = int(single(params, "offset") or "0")
    except ValueError as exc:
        raise ApiError(400, "invalid pagination") from exc
    if not 1 <= limit <= MAX_PAGE or offset < 0:
        raise ApiError(400, "invalid pagination")
    return limit, offset


def collection_family(conn: sqlite3.Connection, collection: str) -> tuple[str, bool]:
    row = conn.execute(
        "SELECT family,queryable FROM private_collection_catalog WHERE collection_id=?",
        (collection,),
    ).fetchone()
    if row is None:
        raise ApiError(400, "invalid collection")
    return str(row["family"]), bool(row["queryable"])


def collection_response(
    conn: sqlite3.Connection,
    view: str,
    where: list[str],
    values: list[Any],
    order: str,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    clause = " AND ".join(where) if where else "1=1"
    total = int(conn.execute(f"SELECT count(*) FROM {view} WHERE {clause}", values).fetchone()[0])
    rows = conn.execute(
        f"SELECT * FROM {view} WHERE {clause} ORDER BY {order} LIMIT ? OFFSET ?",
        [*values, limit, offset],
    ).fetchall()
    return {"items": [dict(row) for row in rows], "offset": offset, "limit": limit, "total": total}


def make_authorizer() -> Any:
    denied = {
        getattr(sqlite3, name)
        for name in (
            "SQLITE_ALTER_TABLE", "SQLITE_ANALYZE", "SQLITE_ATTACH", "SQLITE_CREATE_INDEX",
            "SQLITE_CREATE_TABLE", "SQLITE_CREATE_TEMP_INDEX", "SQLITE_CREATE_TEMP_TABLE",
            "SQLITE_CREATE_TEMP_TRIGGER", "SQLITE_CREATE_TEMP_VIEW", "SQLITE_CREATE_TRIGGER",
            "SQLITE_CREATE_VIEW", "SQLITE_DELETE", "SQLITE_DETACH", "SQLITE_DROP_INDEX",
            "SQLITE_DROP_TABLE", "SQLITE_DROP_TEMP_INDEX", "SQLITE_DROP_TEMP_TABLE",
            "SQLITE_DROP_TEMP_TRIGGER", "SQLITE_DROP_TEMP_VIEW", "SQLITE_DROP_TRIGGER",
            "SQLITE_DROP_VIEW", "SQLITE_INSERT", "SQLITE_PRAGMA", "SQLITE_REINDEX",
            "SQLITE_SAVEPOINT", "SQLITE_TRANSACTION", "SQLITE_UPDATE",
        )
        if hasattr(sqlite3, name)
    }
    allowed_simple = {sqlite3.SQLITE_SELECT}
    if hasattr(sqlite3, "SQLITE_RECURSIVE"):
        allowed_simple.add(sqlite3.SQLITE_RECURSIVE)

    def authorize(action: int, arg1: str | None, arg2: str | None, _database: str | None, source: str | None) -> int:
        if action in denied:
            return sqlite3.SQLITE_DENY
        if action in allowed_simple:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ:
            table = (arg1 or "").lower()
            source_view = (source or "").lower()
            if table in ALLOWED_VIEWS:
                return sqlite3.SQLITE_OK
            if source_view in ALLOWED_VIEWS and VIEW_BASE_TABLES.get(source_view) == table:
                return sqlite3.SQLITE_OK
            # SQLite 3.40 emits a source-less empty-column READ for count(*)
            # after expanding a view. Explicit private table names are rejected
            # lexically before this authorizer is installed.
            if table in PRIVATE_BASE_TABLES and (arg2 or "") == "":
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_FUNCTION:
            function = (arg2 or arg1 or "").lower()
            return sqlite3.SQLITE_OK if function in SAFE_FUNCTIONS else sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_DENY

    return authorize


def execute_public_query(state: HubState, query: Any) -> dict[str, Any]:
    if not isinstance(query, str) or not query.strip() or len(query) > 50_000:
        raise ApiError(400, "invalid query")
    sql = query.strip()
    if "\x00" in sql or "--" in sql or "/*" in sql or not re.match(r"^(SELECT|WITH)\b", sql, re.IGNORECASE):
        raise ApiError(400, "invalid query")
    body = sql[:-1].rstrip() if sql.endswith(";") else sql
    if ";" in body:
        raise ApiError(400, "invalid query")
    if re.search(r"\b(PRAGMA|ATTACH|DETACH|VACUUM|REINDEX|ANALYZE|LOAD_EXTENSION|SQLITE_MASTER|SQLITE_SCHEMA)\b", body, re.IGNORECASE):
        raise ApiError(400, "invalid query")
    if re.search(r"\bPRIVATE_[A-Z0-9_]*\b", body, re.IGNORECASE):
        raise ApiError(400, "invalid query")
    conn = state.connect()
    deadline = time.monotonic() + QUERY_TIMEOUT_SECONDS
    conn.set_authorizer(make_authorizer())
    conn.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 1000)
    try:
        cursor = conn.execute(body)
        if cursor.description is None:
            raise ApiError(400, "invalid query")
        raw_rows = cursor.fetchmany(MAX_QUERY_ROWS + 1)
        columns = [item[0] for item in cursor.description]
        truncated = len(raw_rows) > MAX_QUERY_ROWS
        rows = [list(row) for row in raw_rows[:MAX_QUERY_ROWS]]
        return {"columns": columns, "rows": rows, "row_count": len(rows), "truncated": truncated}
    except ApiError:
        raise
    except (sqlite3.Error, ValueError, OverflowError) as exc:
        raise ApiError(400, "invalid query") from exc
    finally:
        conn.close()


class HubHandler(BaseHTTPRequestHandler):
    server_version = "AsteriaHub/1"
    sys_version = ""
    state: HubState

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> Any:
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length or "0")
        except ValueError as exc:
            raise ApiError(400, "invalid request") from exc
        if length <= 0 or length > MAX_BODY:
            raise ApiError(400, "invalid request")
        try:
            return json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(400, "invalid request") from exc

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlsplit(self.path)
        params = parse_qs(parsed.query, keep_blank_values=True)
        try:
            payload = self.handle_get(parsed.path, params)
            self.send_json(200, payload)
        except ApiError as exc:
            self.send_json(exc.status, {"error": exc.message})
        except Exception:
            self.send_json(500, {"error": "service error"})

    def handle_get(self, path: str, params: dict[str, list[str]]) -> Any:
        if path == "/health":
            ensure_params(params, set())
            return {"status": "ok", "state_mode": "read_only", "data_version": self.state.data_version, "record_counts": self.state.view_counts}
        conn = self.state.connect()
        try:
            if path == "/api/catalog/collections":
                ensure_params(params, {"limit", "offset"})
                limit, offset = page(params)
                total = int(conn.execute("SELECT count(*) FROM private_collection_catalog").fetchone()[0])
                rows = conn.execute(
                    "SELECT collection_id,description,family,source_systems,time_start,time_end,approximate_record_count "
                    "FROM private_collection_catalog ORDER BY collection_id LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()
                items = []
                for row in rows:
                    item = dict(row)
                    item["source_systems"] = json.loads(item["source_systems"])
                    items.append(item)
                return {"items": items, "offset": offset, "limit": limit, "total": total}
            if path == "/api/catalog/schema":
                ensure_params(params, set())
                views = []
                for view in sorted(ALLOWED_VIEWS):
                    fields = []
                    for row in conn.execute(f"PRAGMA table_info({view})"):
                        name = row[1]
                        meaning = FIELD_MEANINGS.get(name, f"Source field `{name}` exposed by this logical view.")
                        fields.append({"name": name, "type": row[2] or "ANY", "meaning": meaning})
                    views.append({"name": view, "fields": fields})
                return {"views": views}
            if path == "/api/contacts":
                ensure_params(params, {"collection", "source_system", "limit", "offset"})
                limit, offset = page(params)
                collection = single(params, "collection", True)
                family, queryable = collection_family(conn, collection)
                if family != "contacts" or not queryable:
                    raise ApiError(400, "invalid collection")
                where, values = ["collection_id=?"], [collection]
                source = single(params, "source_system")
                if source is not None:
                    valid = conn.execute("SELECT 1 FROM v_contacts WHERE collection_id=? AND source_system=? LIMIT 1", (collection, source)).fetchone()
                    if valid is None:
                        raise ApiError(400, "invalid filter")
                    where.append("source_system=?")
                    values.append(source)
                return collection_response(conn, "v_contacts", where, values, "row_id", limit, offset)
            if path == "/api/transactions/fuel":
                ensure_params(params, {"collection", "merchant", "limit", "offset"})
                limit, offset = page(params)
                collection = single(params, "collection", True)
                family, queryable = collection_family(conn, collection)
                if family != "fuel" or not queryable:
                    raise ApiError(400, "invalid collection")
                where, values = ["collection_id=?"], [collection]
                merchant = single(params, "merchant")
                if merchant is not None:
                    where.append("merchant_id=?")
                    values.append(merchant)
                return collection_response(conn, "v_fuel_transactions", where, values, "transaction_id,snapshot_id", limit, offset)
            if path == "/api/transactions/freight":
                ensure_params(params, {"collection", "carrier", "limit", "offset"})
                limit, offset = page(params)
                collection = single(params, "collection", True)
                family, queryable = collection_family(conn, collection)
                if family != "freight" or not queryable:
                    raise ApiError(400, "invalid collection")
                where, values = ["collection_id=?"], [collection]
                carrier = single(params, "carrier")
                if carrier is not None:
                    where.append("carrier_id=?")
                    values.append(carrier)
                return collection_response(conn, "v_freight_charges", where, values, "charge_id,snapshot_id", limit, offset)
            if path == "/api/maintenance/events":
                ensure_params(params, {"collection", "snapshot_id", "asset_id", "limit", "offset"})
                limit, offset = page(params)
                collection = single(params, "collection", True)
                family, queryable = collection_family(conn, collection)
                if family != "maintenance" or not queryable:
                    raise ApiError(400, "invalid collection")
                where, values = ["collection_id=?"], [collection]
                snapshot = single(params, "snapshot_id")
                if snapshot is not None:
                    valid = conn.execute("SELECT 1 FROM v_source_snapshots WHERE collection_id=? AND snapshot_id=?", (collection, snapshot)).fetchone()
                    if valid is None:
                        raise ApiError(400, "invalid filter")
                    where.append("snapshot_id=?")
                    values.append(snapshot)
                asset = single(params, "asset_id")
                if asset is not None:
                    where.append("asset_id=?")
                    values.append(asset)
                return collection_response(conn, "v_maintenance_events", where, values, "event_id,snapshot_id", limit, offset)
            if path == "/api/reference/aliases":
                ensure_params(params, {"domain", "as_of", "limit", "offset"})
                limit, offset = page(params)
                domain = single(params, "domain", True)
                if domain not in {"fuel", "freight"}:
                    raise ApiError(400, "invalid filter")
                where, values = ["domain=?"], [domain]
                as_of = single(params, "as_of")
                if as_of is not None:
                    parse_date(as_of, "as_of")
                    where.extend(["valid_from<=?", "(valid_to IS NULL OR valid_to>=?)"])
                    values.extend([as_of, as_of])
                return collection_response(conn, "v_reference_aliases", where, values, "alias_id", limit, offset)
            if path == "/api/reference/conversions":
                ensure_params(params, {"kind", "as_of", "limit", "offset"})
                limit, offset = page(params)
                kind = single(params, "kind", True)
                if kind not in {"volume", "weight", "distance", "odometer"}:
                    raise ApiError(400, "invalid filter")
                where, values = ["kind=?"], [kind]
                as_of = single(params, "as_of")
                if as_of is not None:
                    parse_date(as_of, "as_of")
                    where.extend(["valid_from<=?", "(valid_to IS NULL OR valid_to>=?)"])
                    values.extend([as_of, as_of])
                return collection_response(conn, "v_unit_conversions", where, values, "from_unit,valid_from", limit, offset)
            if path == "/api/reference/fx":
                ensure_params(params, {"date", "currency", "limit", "offset"})
                limit, offset = page(params)
                where, values = [], []
                date = single(params, "date")
                if date is not None:
                    parse_date(date, "date")
                    where.append("rate_date=?")
                    values.append(date)
                currency = single(params, "currency")
                if currency is not None:
                    if currency not in {"USD", "EUR", "GBP", "CAD"}:
                        raise ApiError(400, "invalid filter")
                    where.append("currency=?")
                    values.append(currency)
                return collection_response(conn, "v_fx_rates", where, values, "rate_date,currency,rate_status", limit, offset)
            if path == "/api/source-snapshots":
                ensure_params(params, {"collection", "limit", "offset"})
                limit, offset = page(params)
                collection = single(params, "collection", True)
                _family, queryable = collection_family(conn, collection)
                if not queryable:
                    raise ApiError(400, "invalid collection")
                return collection_response(conn, "v_source_snapshots", ["collection_id=?"], [collection], "snapshot_id", limit, offset)
            raise ApiError(404, "not found")
        finally:
            conn.close()

    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        try:
            if path == "/api/query":
                if self.headers.get("Authorization") != f"Bearer {QUERY_TOKEN}":
                    raise ApiError(401, "authentication required")
                payload = self.read_json()
                if not isinstance(payload, dict) or set(payload) != {"query"}:
                    raise ApiError(400, "invalid request")
                self.send_json(200, execute_public_query(self.state, payload["query"]))
                return
            if path == "/api/judge" and self.state.judge_enabled and self.state.judge is not None:
                payload = self.read_json()
                try:
                    status, response = self.state.judge.evaluate(payload)
                except JudgeError as exc:
                    status, response = error_response(exc)
                self.send_json(status, response)
                return
            raise ApiError(404, "not found")
        except ApiError as exc:
            self.send_json(exc.status, {"error": exc.message})
        except Exception:
            self.send_json(500, {"error": "service error"})


def main() -> None:
    state = HubState()
    HubHandler.state = state
    bind = os.environ.get("TASK_ENV_BIND", "0.0.0.0")
    try:
        port = int(os.environ.get("TASK_ENV_PORT", "9021"))
    except ValueError as exc:
        raise SystemExit("TASK_ENV_PORT must be an integer") from exc
    server = ThreadingHTTPServer((bind, port), HubHandler)
    server.daemon_threads = True

    def stop(_signum: int, _frame: Any) -> None:
        server._BaseServer__shutdown_request = True  # type: ignore[attr-defined]

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
