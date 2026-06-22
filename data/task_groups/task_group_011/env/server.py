#!/usr/bin/env python3
"""HTTP API for the shared credit office environment."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from judge_api import judge_answer_request


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "credit_office.db"
MANIFEST_PATH = DATA_DIR / "public_manifest.json"
POLICIES_PATH = DATA_DIR / "policies.json"


def ensure_data():
    if not DB_PATH.exists() or not MANIFEST_PATH.exists():
        raise RuntimeError("Generated data is missing. Run python3 generate_data.py first.")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_dicts(rows):
    return [dict(row) for row in rows]


def one_row(conn, sql, params=()):
    row = conn.execute(sql, params).fetchone()
    return None if row is None else dict(row)


class CreditOfficeHandler(BaseHTTPRequestHandler):
    server_version = "CreditOfficeHTTP/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))

    def send_json(self, status, value):
        payload = json.dumps(value, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def send_error_json(self, status, message):
        self.send_json(status, {"error": message, "status": status})

    def do_GET(self):
        try:
            self.route_get()
        except sqlite3.Error as exc:
            self.send_error_json(500, f"database error: {exc}")
        except Exception as exc:
            self.send_error_json(500, str(exc))

    def do_POST(self):
        parsed = urlparse(self.path)
        path_parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
        if path_parts == ["api", "judge"]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            status, payload = judge_answer_request(self.rfile.read(length))
            self.send_json(status, payload)
            return
        self.send_error_json(404, "endpoint not found")

    def route_get(self):
        parsed = urlparse(self.path)
        path_parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
        query = parse_qs(parsed.query)

        if path_parts == ["api", "health"]:
            with connect() as conn:
                counts = {}
                for table in [
                    "branches",
                    "branch_metrics",
                    "loans",
                    "sector_exposures",
                    "applications",
                    "ncua_benchmarks",
                    "credit_union_segments",
                ]:
                    counts[table] = conn.execute(f"select count(*) from {table}").fetchone()[0]
            self.send_json(200, {"status": "ok", "service": "credit_office", "record_counts": counts})
            return

        if path_parts == ["api", "manifest"]:
            self.send_json(200, json.loads(MANIFEST_PATH.read_text(encoding="ascii")))
            return

        if path_parts == ["api", "policies"]:
            self.send_json(200, json.loads(POLICIES_PATH.read_text(encoding="ascii")))
            return

        if path_parts == ["api", "benchmarks", "fdic", "q4-2024"]:
            with connect() as conn:
                row = one_row(conn, "select * from fdic_benchmarks where benchmark_version = ?", ("fdic_q4_2024",))
            if row is None:
                self.send_error_json(404, "FDIC benchmark not found")
            else:
                self.send_json(200, row)
            return

        if path_parts == ["api", "benchmarks", "ncua", "q1-2025"]:
            state_code = query.get("state_code", [None])[0]
            with connect() as conn:
                if state_code:
                    rows = conn.execute(
                        "select * from ncua_benchmarks where state_code = ? order by state_code",
                        (state_code.upper(),),
                    ).fetchall()
                else:
                    rows = conn.execute("select * from ncua_benchmarks order by state_code").fetchall()
            self.send_json(200, {"benchmark_version": "ncua_q1_2025", "rows": rows_to_dicts(rows)})
            return

        if path_parts == ["api", "branches"]:
            institution_type = query.get("institution_type", [None])[0]
            sql = "select * from branches"
            params = []
            if institution_type:
                sql += " where institution_type = ?"
                params.append(institution_type)
            sql += " order by branch_id"
            with connect() as conn:
                rows = conn.execute(sql, params).fetchall()
            self.send_json(200, rows_to_dicts(rows))
            return

        if len(path_parts) >= 3 and path_parts[0:2] == ["api", "branches"]:
            branch_id = path_parts[2].upper()
            with connect() as conn:
                branch = one_row(conn, "select * from branches where branch_id = ?", (branch_id,))
                if branch is None:
                    self.send_error_json(404, f"branch not found: {branch_id}")
                    return

                if len(path_parts) == 3:
                    self.send_json(200, branch)
                    return

                if len(path_parts) == 4 and path_parts[3] == "metrics":
                    quarter = query.get("quarter", [None])[0]
                    if quarter:
                        rows = conn.execute(
                            "select * from branch_metrics where branch_id = ? and quarter = ? order by quarter desc",
                            (branch_id, quarter),
                        ).fetchall()
                    else:
                        rows = conn.execute(
                            "select * from branch_metrics where branch_id = ? order by quarter desc",
                            (branch_id,),
                        ).fetchall()
                    self.send_json(200, rows_to_dicts(rows))
                    return

                if len(path_parts) == 4 and path_parts[3] == "loans":
                    clauses = ["branch_id = ?"]
                    params = [branch_id]
                    if "loan_type" in query:
                        clauses.append("loan_type = ?")
                        params.append(query["loan_type"][0])
                    if "payment_status" in query:
                        clauses.append("payment_status = ?")
                        params.append(query["payment_status"][0])
                    if "min_current_rating" in query:
                        clauses.append("current_rating >= ?")
                        params.append(int(query["min_current_rating"][0]))
                    sql = "select * from loans where " + " and ".join(clauses) + " order by loan_id"
                    rows = conn.execute(sql, params).fetchall()
                    self.send_json(200, rows_to_dicts(rows))
                    return

                if len(path_parts) == 4 and path_parts[3] == "sector-exposures":
                    rows = conn.execute(
                        "select * from sector_exposures where branch_id = ? order by sector",
                        (branch_id,),
                    ).fetchall()
                    self.send_json(200, rows_to_dicts(rows))
                    return

                if len(path_parts) == 4 and path_parts[3] == "applications":
                    loan_type = query.get("loan_type", [None])[0]
                    if loan_type:
                        rows = conn.execute(
                            "select * from applications where branch_id = ? and loan_type = ? order by application_id",
                            (branch_id, loan_type),
                        ).fetchall()
                    else:
                        rows = conn.execute(
                            "select * from applications where branch_id = ? order by application_id",
                            (branch_id,),
                        ).fetchall()
                    self.send_json(200, rows_to_dicts(rows))
                    return

        if len(path_parts) == 3 and path_parts[0:2] == ["api", "credit-union-segments"]:
            segment_id = path_parts[2].upper()
            with connect() as conn:
                row = conn.execute(
                    "select segment_json from credit_union_segments where segment_id = ?",
                    (segment_id,),
                ).fetchone()
            if row is None:
                self.send_error_json(404, f"credit union segment not found: {segment_id}")
            else:
                self.send_json(200, json.loads(row["segment_json"]))
            return

        self.send_error_json(404, "endpoint not found")


def main():
    parser = argparse.ArgumentParser(description="Run the credit office API server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8057, type=int)
    args = parser.parse_args()

    ensure_data()
    server = ThreadingHTTPServer((args.host, args.port), CreditOfficeHandler)
    print(f"Credit office API listening at http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping credit office API.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
