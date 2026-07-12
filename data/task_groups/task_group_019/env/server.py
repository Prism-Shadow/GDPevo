#!/usr/bin/env python3
"""HTTP JSON API for the Cascadia Licensing Review Portal."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from judge_api import judge_answer_request


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "clrp.db"
PUBLIC_MANIFEST_PATH = DATA_DIR / "public_manifest.json"


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def row_dicts(cursor: sqlite3.Cursor) -> list[dict]:
    return [dict(row) for row in cursor.fetchall()]


def csv_text(rows: list[dict], fieldnames: list[str]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


class CLRPHandler(BaseHTTPRequestHandler):
    server_version = "CLRP/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.client_address[0]} - - [{self.log_date_time_string()}] {fmt % args}")

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_POST(self) -> None:
        if urlparse(self.path).path.rstrip("/") != "/api/judge":
            self.write_json(HTTPStatus.NOT_FOUND, {"error": "not_found", "path": self.path})
            return
        length = int(self.headers.get("Content-Length", "0"))
        status, payload = judge_answer_request(self.rfile.read(length))
        self.write_json(HTTPStatus(status), payload)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = {key: values[-1] for key, values in parse_qs(parsed.query).items()}

        if path == "/health":
            self.handle_health()
            return

        if path.startswith("/exports/"):
            self.handle_export(path)
            return

        routes = {
            "/api/contractors/applications": self.handle_contractor_applications,
            "/api/contractors/bonds": self.handle_contractor_bonds,
            "/api/contractors/insurance": self.handle_contractor_insurance,
            "/api/contractors/violations": self.handle_contractor_violations,
            "/api/contractors/complaints": self.handle_contractor_complaints,
            "/api/contractors/field-notes": self.handle_contractor_field_notes,
            "/api/contractors/correspondence": self.handle_contractor_correspondence,
            "/api/contractors/bulletins": self.handle_contractor_bulletins,
            "/api/alcohol/applications": self.handle_alcohol_applications,
            "/api/alcohol/premises": self.handle_alcohol_premises,
            "/api/alcohol/incidents": self.handle_alcohol_incidents,
            "/api/alcohol/settlements": self.handle_alcohol_settlements,
            "/api/alcohol/restrictions": self.handle_alcohol_restrictions,
            "/api/alcohol/standard-obligations": self.handle_alcohol_standard_obligations,
            "/api/renewals/licensees": self.handle_renewal_licensees,
            "/api/renewals/violations": self.handle_renewal_violations,
            "/api/search/address": self.handle_search_address,
        }
        handler = routes.get(path)
        if handler is None:
            self.write_json(HTTPStatus.NOT_FOUND, {"error": "not_found", "path": path})
            return
        try:
            handler(params)
        except sqlite3.Error as exc:
            self.write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "database_error", "message": str(exc)})

    @property
    def db_path(self) -> Path:
        return self.server.db_path  # type: ignore[attr-defined]

    def write_json(self, status: HTTPStatus, payload: dict | list) -> None:
        data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def write_csv(self, filename: str, text: str) -> None:
        data = text.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def query(self, sql: str, args: tuple = ()) -> list[dict]:
        with connect(self.db_path) as conn:
            return row_dicts(conn.execute(sql, args))

    def table_response(
        self,
        table: str,
        where_sql: str = "",
        args: tuple = (),
        order_sql: str = "",
        limit: int = 200,
        meta: dict | None = None,
    ) -> None:
        sql = f"SELECT * FROM {table}"
        if where_sql:
            sql += f" WHERE {where_sql}"
        if order_sql:
            sql += f" ORDER BY {order_sql}"
        sql += " LIMIT ?"
        rows = self.query(sql, args + (limit,))
        payload = {
            "data": rows,
            "count": len(rows),
            "limit": limit,
            "table": table,
        }
        if meta:
            payload["meta"] = meta
        self.write_json(HTTPStatus.OK, payload)

    def handle_health(self) -> None:
        if not self.db_path.exists():
            self.write_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {
                    "status": "error",
                    "message": "database not found; run generate_data.py",
                    "database_path": str(self.db_path),
                },
            )
            return
        with connect(self.db_path) as conn:
            app_count = conn.execute("SELECT COUNT(*) FROM contractor_applications").fetchone()[0]
            licensee_count = conn.execute("SELECT COUNT(*) FROM renewal_licensees").fetchone()[0]
        self.write_json(
            HTTPStatus.OK,
            {
                "status": "ok",
                "service": "Cascadia Licensing Review Portal",
                "database_path": str(self.db_path),
                "public_manifest_path": str(PUBLIC_MANIFEST_PATH),
                "contractor_application_count": app_count,
                "renewal_licensee_count": licensee_count,
            },
        )

    def handle_contractor_applications(self, params: dict[str, str]) -> None:
        batch_id = params.get("batch_id", "").strip()
        if batch_id:
            self.table_response(
                "contractor_applications",
                "batch_id = ?",
                (batch_id,),
                "application_id",
                meta={"batch_id": batch_id},
            )
            return
        self.table_response("contractor_applications", order_sql="batch_id, application_id")

    def handle_contractor_bonds(self, params: dict[str, str]) -> None:
        self.name_search_response("contractor_bonds", params, "last_update DESC, bond_id")

    def handle_contractor_insurance(self, params: dict[str, str]) -> None:
        self.name_search_response("contractor_insurance", params, "last_update DESC, policy_id")

    def handle_contractor_violations(self, params: dict[str, str]) -> None:
        self.name_search_response("contractor_violations", params, "violation_date DESC, violation_id")

    def handle_contractor_complaints(self, params: dict[str, str]) -> None:
        self.name_search_response("contractor_complaints", params, "received_date DESC, complaint_id")

    def handle_contractor_field_notes(self, params: dict[str, str]) -> None:
        self.name_search_response("contractor_field_notes", params, "inspection_date DESC, note_id")

    def name_search_response(self, table: str, params: dict[str, str], order_sql: str) -> None:
        name = params.get("name", "").strip()
        if not name:
            self.table_response(table, order_sql=order_sql)
            return
        like = f"%{name}%"
        if table in {"contractor_bonds", "contractor_violations"}:
            where_sql = "legal_name LIKE ? OR principal_name LIKE ?"
            args = (like, like)
        elif table == "contractor_insurance":
            where_sql = "legal_name LIKE ? OR carrier LIKE ? OR policy_number LIKE ?"
            args = (like, like, like)
        else:
            where_sql = "legal_name LIKE ?"
            args = (like,)
        self.table_response(table, where_sql, args, order_sql, meta={"name_query": name})

    def handle_contractor_correspondence(self, params: dict[str, str]) -> None:
        batch_id = params.get("batch_id", "").strip()
        if batch_id:
            rows = self.query(
                """
                SELECT c.*
                FROM contractor_correspondence c
                JOIN contractor_applications a
                  ON a.application_id = c.affects_application_id
                WHERE a.batch_id = ?
                ORDER BY c.received_date DESC, c.item_id
                LIMIT 200
                """,
                (batch_id,),
            )
            self.write_json(
                HTTPStatus.OK,
                {
                    "table": "contractor_correspondence",
                    "count": len(rows),
                    "limit": 200,
                    "meta": {"batch_id": batch_id},
                    "data": rows,
                },
            )
            return
        self.table_response("contractor_correspondence", order_sql="received_date DESC, item_id")

    def handle_contractor_bulletins(self, params: dict[str, str]) -> None:
        effective_on = params.get("effective_on", "").strip()
        if effective_on:
            self.table_response(
                "contractor_bulletins",
                "effective_date <= ?",
                (effective_on,),
                "effective_date, bulletin_id",
                meta={"effective_on": effective_on},
            )
            return
        self.table_response("contractor_bulletins", order_sql="effective_date, bulletin_id")

    def handle_alcohol_applications(self, params: dict[str, str]) -> None:
        review_month = params.get("review_month", "").strip()
        if review_month:
            self.table_response(
                "alcohol_applications",
                "review_month = ?",
                (review_month,),
                "application_id",
                meta={"review_month": review_month},
            )
            return
        self.table_response("alcohol_applications", order_sql="review_month, application_id")

    def handle_alcohol_premises(self, params: dict[str, str]) -> None:
        premises_id = params.get("premises_id", "").strip()
        if premises_id:
            self.table_response(
                "alcohol_premises", "premises_id = ?", (premises_id,), "premises_id", meta={"premises_id": premises_id}
            )
            return
        self.table_response("alcohol_premises", order_sql="city, address")

    def handle_alcohol_incidents(self, params: dict[str, str]) -> None:
        premises_id_response = self.premises_child_response(
            "alcohol_incidents", params, "incident_date DESC, incident_id"
        )
        if premises_id_response:
            return

    def handle_alcohol_settlements(self, params: dict[str, str]) -> None:
        premises_id_response = self.premises_child_response(
            "alcohol_settlements", params, "settlement_date DESC, settlement_id"
        )
        if premises_id_response:
            return

    def handle_alcohol_restrictions(self, params: dict[str, str]) -> None:
        premises_id_response = self.premises_child_response(
            "alcohol_restrictions", params, "restriction_code, restriction_id"
        )
        if premises_id_response:
            return

    def premises_child_response(self, table: str, params: dict[str, str], order_sql: str) -> bool:
        premises_id = params.get("premises_id", "").strip()
        if premises_id:
            self.table_response(table, "premises_id = ?", (premises_id,), order_sql, meta={"premises_id": premises_id})
        else:
            self.table_response(table, order_sql=order_sql)
        return True

    def handle_alcohol_standard_obligations(self, params: dict[str, str]) -> None:
        license_type = params.get("license_type", "").strip()
        if license_type:
            self.table_response(
                "alcohol_standard_obligations",
                "license_type = ? OR license_type = 'ALL'",
                (license_type,),
                "license_type, obligation_code",
                meta={"license_type": license_type},
            )
            return
        self.table_response("alcohol_standard_obligations", order_sql="license_type, obligation_code")

    def handle_renewal_licensees(self, params: dict[str, str]) -> None:
        release_batch = params.get("release_batch", "").strip()
        if release_batch:
            self.table_response(
                "renewal_licensees",
                "release_batch = ?",
                (release_batch,),
                "license_id",
                meta={"release_batch": release_batch},
            )
            return
        self.table_response("renewal_licensees", order_sql="release_batch, license_id")

    def handle_renewal_violations(self, params: dict[str, str]) -> None:
        city = params.get("city", "").strip()
        if city:
            self.table_response(
                "renewal_violations",
                "city = ?",
                (city,),
                "violation_date DESC, violation_id",
                meta={"city": city},
            )
            return
        self.table_response("renewal_violations", order_sql="violation_date DESC, violation_id")

    def handle_search_address(self, params: dict[str, str]) -> None:
        address = params.get("address", "").strip()
        if not address:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": "missing_address", "message": "Provide address=..."})
            return
        like = f"%{address}%"
        alcohol_premises = self.query(
            "SELECT * FROM alcohol_premises WHERE address LIKE ? ORDER BY city, address LIMIT 100", (like,)
        )
        alcohol_applications = self.query(
            "SELECT * FROM alcohol_applications WHERE address LIKE ? ORDER BY review_month, application_id LIMIT 100",
            (like,),
        )
        renewal_licensees = self.query(
            "SELECT * FROM renewal_licensees WHERE address LIKE ? ORDER BY release_batch, license_id LIMIT 100",
            (like,),
        )
        renewal_violations = self.query(
            "SELECT * FROM renewal_violations WHERE address LIKE ? ORDER BY violation_date DESC, violation_id LIMIT 100",
            (like,),
        )
        self.write_json(
            HTTPStatus.OK,
            {
                "query": address,
                "data": {
                    "alcohol_premises": alcohol_premises,
                    "alcohol_applications": alcohol_applications,
                    "renewal_licensees": renewal_licensees,
                    "renewal_violations": renewal_violations,
                },
                "count": len(alcohol_premises)
                + len(alcohol_applications)
                + len(renewal_licensees)
                + len(renewal_violations),
            },
        )

    def handle_export(self, path: str) -> None:
        contractor_match = re.fullmatch(r"/exports/contractor_batch_([A-Za-z0-9_-]+)\.csv", path)
        if contractor_match:
            batch_id = contractor_match.group(1)
            rows = self.query(
                """
                SELECT application_id, batch_id, legal_name, dba, principal_name, trade,
                       application_date, exam_score, experience_years,
                       financial_statement_filed, background_status,
                       declared_bond_amount, declared_insurance_carrier,
                       declared_insurance_policy, prior_registration_id
                FROM contractor_applications
                WHERE batch_id = ?
                ORDER BY application_id
                """,
                (batch_id,),
            )
            fieldnames = [
                "application_id",
                "batch_id",
                "legal_name",
                "dba",
                "principal_name",
                "trade",
                "application_date",
                "exam_score",
                "experience_years",
                "financial_statement_filed",
                "background_status",
                "declared_bond_amount",
                "declared_insurance_carrier",
                "declared_insurance_policy",
                "prior_registration_id",
            ]
            self.write_csv(f"contractor_batch_{batch_id}.csv", csv_text(rows, fieldnames))
            return

        roster_match = re.fullmatch(r"/exports/renewal_roster_([A-Za-z0-9_-]+)\.csv", path)
        if roster_match:
            release_batch = roster_match.group(1)
            rows = self.query(
                """
                SELECT license_id, facility_name, legal_name, address, city,
                       channel_type, license_type, status, release_batch, successor_hint
                FROM renewal_licensees
                WHERE release_batch = ?
                ORDER BY license_id
                """,
                (release_batch,),
            )
            fieldnames = [
                "license_id",
                "facility_name",
                "legal_name",
                "address",
                "city",
                "channel_type",
                "license_type",
                "status",
                "release_batch",
                "successor_hint",
            ]
            self.write_csv(f"renewal_roster_{release_batch}.csv", csv_text(rows, fieldnames))
            return

        self.write_json(HTTPStatus.NOT_FOUND, {"error": "export_not_found", "path": path})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the CLRP HTTP API server.")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8057, help="Port to listen on.")
    parser.add_argument("--db", default=str(DB_PATH), help="Path to the SQLite database.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db).resolve()
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}. Run generate_data.py first.")
    server = ThreadingHTTPServer((args.host, args.port), CLRPHandler)
    server.db_path = db_path  # type: ignore[attr-defined]
    print(f"Cascadia Licensing Review Portal running at http://{args.host}:{args.port}")
    print(f"Database: {db_path}")
    print(f"Public manifest: {PUBLIC_MANIFEST_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping CLRP server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
