#!/usr/bin/env python3
"""Cedar Ridge Intake Coordination Portal."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from judge_api import JudgeError, score_train_answer


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "clinic.db"
TASK_GROUP_ID = "task_group_013"
MAX_LIMIT = 500


def open_db(read_only: bool = True) -> sqlite3.Connection:
    if read_only:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def one(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> dict | None:
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    names = [
        "patients",
        "intake_rosters",
        "coverage",
        "pbm",
        "pharmacies",
        "patient_pharmacy",
        "lifestyle",
        "clinical_history",
        "referrals",
        "icd_codes",
        "documents",
        "transfer_requests",
        "facility_capacity",
        "chart_artifacts",
        "program_candidates",
    ]
    return {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in names}


def query_limit(params: dict[str, list[str]], default: int = 100) -> int:
    raw = params.get("limit", [str(default)])[0]
    try:
        value = int(raw)
    except ValueError:
        value = default
    return max(1, min(value, MAX_LIMIT))


def like(value: str) -> str:
    return f"%{value.strip()}%"


def readonly_sql(sql: str) -> str:
    stripped = sql.strip()
    if not stripped:
        raise ValueError("sql is required")
    if "\x00" in stripped:
        raise ValueError("invalid sql")
    without_trailing = stripped[:-1].strip() if stripped.endswith(";") else stripped
    if ";" in without_trailing:
        raise ValueError("multiple statements are not allowed")
    first = without_trailing.split(None, 1)[0].lower() if without_trailing.split(None, 1) else ""
    if first == "select":
        return without_trailing
    if first == "pragma":
        lower = without_trailing.lower()
        if "=" in lower or re.search(r"\b(journal_mode|writable_schema|user_version|application_id)\b", lower):
            raise ValueError("mutating PRAGMA statements are not allowed")
        return without_trailing
    raise ValueError("only SELECT and read-only PRAGMA statements are allowed")


def dashboard_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Cedar Ridge Intake Coordination Portal</title>
  <style>
    :root { color-scheme: light; font-family: Arial, sans-serif; background: #f6f7f9; color: #17202a; }
    body { margin: 0; }
    header { background: #24415c; color: white; padding: 18px 28px; }
    h1 { font-size: 24px; margin: 0 0 4px; }
    main { padding: 22px 28px 36px; max-width: 1180px; margin: 0 auto; }
    section { margin: 0 0 22px; }
    h2 { font-size: 17px; margin: 0 0 10px; }
    form { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 10px; }
    input, select, textarea { border: 1px solid #aab4be; border-radius: 4px; padding: 7px 8px; font: inherit; background: white; }
    textarea { width: min(920px, 100%); min-height: 82px; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }
    button { background: #2f6f8f; color: white; border: 0; border-radius: 4px; padding: 8px 12px; cursor: pointer; }
    button:focus, input:focus, textarea:focus { outline: 2px solid #8ac0d6; outline-offset: 1px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; }
    .panel { background: white; border: 1px solid #d8dee6; border-radius: 6px; padding: 14px; }
    pre { background: #111827; color: #eef2f7; border-radius: 5px; padding: 12px; overflow: auto; max-height: 360px; }
    table { border-collapse: collapse; width: 100%; background: white; }
    th, td { border-bottom: 1px solid #e5e9ef; text-align: left; padding: 6px 7px; font-size: 13px; vertical-align: top; }
    th { background: #eef3f6; }
    .muted { color: #52616f; font-size: 13px; }
  </style>
</head>
<body>
  <header>
    <h1>Cedar Ridge Intake Coordination Portal</h1>
    <div class="muted">Shared read-only intake, referral, transfer, chart, and program data</div>
  </header>
  <main>
    <section class="grid">
      <div class="panel">
        <h2>Patients</h2>
        <form data-target="/patients">
          <input name="q" placeholder="name or patient id">
          <input name="limit" value="10" size="4">
          <button>Search</button>
        </form>
        <pre id="patients"></pre>
      </div>
      <div class="panel">
        <h2>Referrals</h2>
        <form data-target="/referrals">
          <input name="batch_id" placeholder="batch id">
          <select name="service_line">
            <option value="">any service</option>
            <option>orthopedics</option><option>pulmonary</option><option>cardiology</option>
          </select>
          <input name="limit" value="10" size="4">
          <button>Search</button>
        </form>
        <pre id="referrals"></pre>
      </div>
      <div class="panel">
        <h2>Transfers</h2>
        <form data-target="/transfers">
          <input name="batch_id" placeholder="batch id">
          <input name="limit" value="10" size="4">
          <button>Search</button>
        </form>
        <pre id="transfers"></pre>
      </div>
      <div class="panel">
        <h2>Program Candidates</h2>
        <form data-target="/programs/DMHTN-2026A/candidates">
          <select name="_path">
            <option value="/programs/DMHTN-2026A/candidates">DMHTN-2026A</option>
            <option value="/programs/RENAL-DM-2026B/candidates">RENAL-DM-2026B</option>
          </select>
          <button>Load</button>
        </form>
        <pre id="programs"></pre>
      </div>
    </section>
    <section class="panel">
      <h2>Read-only SQL</h2>
      <form id="sql-form">
        <textarea name="sql">SELECT roster_id, patient_id, requested_service_date FROM intake_rosters ORDER BY roster_id, patient_id LIMIT 20</textarea>
        <button>Run SELECT</button>
      </form>
      <pre id="sql"></pre>
    </section>
  </main>
  <script>
    async function getJSON(path) {
      const response = await fetch(path);
      return response.json();
    }
    function fill(id, data) {
      document.getElementById(id).textContent = JSON.stringify(data, null, 2);
    }
    for (const form of document.querySelectorAll('form[data-target]')) {
      form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const data = new FormData(form);
        const override = data.get('_path');
        data.delete('_path');
        const params = new URLSearchParams();
        for (const [key, value] of data.entries()) if (value) params.set(key, value);
        const path = (override || form.dataset.target) + (params.toString() ? '?' + params.toString() : '');
        const panel = form.closest('.panel').querySelector('pre').id;
        fill(panel, await getJSON(path));
      });
    }
    document.getElementById('sql-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      const sql = new FormData(event.target).get('sql');
      const response = await fetch('/query', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({sql})});
      fill('sql', await response.json());
    });
    getJSON('/health').then(data => fill('patients', data));
  </script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "CedarRidgePortal/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.client_address[0]} - - [{self.log_date_time_string()}] {fmt % args}", flush=True)

    def send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html: str, status: int = 200) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> object:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("request body too large")
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") if parsed.path != "/" else "/"
        params = parse_qs(parsed.query)
        try:
            if path == "/":
                self.send_html(dashboard_html())
                return
            if path == "/health":
                self.handle_health()
                return
            if path == "/patients":
                self.handle_patients(params)
                return
            if path.startswith("/patients/"):
                self.handle_patient_detail(unquote(path.split("/", 2)[2]))
                return
            if path == "/referrals":
                self.handle_referrals(params)
                return
            if path.startswith("/referrals/"):
                self.handle_referral_detail(unquote(path.split("/", 2)[2]))
                return
            if path == "/transfers":
                self.handle_transfers(params)
                return
            if path.startswith("/transfers/"):
                self.handle_transfer_detail(unquote(path.split("/", 2)[2]))
                return
            if path == "/documents":
                self.handle_documents(params)
                return
            if path.startswith("/chart/"):
                self.handle_chart(unquote(path.split("/", 2)[2]))
                return
            match = re.fullmatch(r"/programs/([^/]+)/candidates", path)
            if match:
                self.handle_program_candidates(unquote(match.group(1)))
                return
            if path.startswith("/icd/"):
                self.handle_icd(unquote(path.split("/", 2)[2]))
                return
            if path == "/pharmacies":
                self.handle_pharmacies(params)
                return
            self.send_json({"error": "not found"}, 404)
        except sqlite3.Error as exc:
            self.send_json({"error": "database error", "detail": str(exc)}, 500)
        except Exception as exc:  # noqa: BLE001 - keep service error responses JSON.
            self.send_json({"error": "request failed", "detail": str(exc)}, 400)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") if parsed.path != "/" else "/"
        try:
            if path == "/query":
                self.handle_query()
                return
            if path == "/api/judge":
                if os.environ.get("TASK_ENV_ENABLE_JUDGE") != "1":
                    self.send_json({"error": "not found"}, 404)
                    return
                self.handle_judge()
                return
            self.send_json({"error": "not found"}, 404)
        except json.JSONDecodeError:
            self.send_json({"error": "invalid json"}, 400)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)
        except sqlite3.Error as exc:
            self.send_json({"error": "database error", "detail": str(exc)}, 400)

    def handle_health(self) -> None:
        ready = DB_PATH.exists()
        payload = {"status": "ok" if ready else "error", "task_group_id": TASK_GROUP_ID, "database_ready": ready}
        if ready:
            with open_db() as conn:
                payload["record_counts"] = table_counts(conn)
        self.send_json(payload, 200 if ready else 503)

    def handle_patients(self, params: dict[str, list[str]]) -> None:
        limit = query_limit(params)
        clauses = []
        values: list[object] = []
        if params.get("patient_id"):
            clauses.append("patient_id = ?")
            values.append(params["patient_id"][0])
        if params.get("q"):
            clauses.append("(patient_id LIKE ? OR first_name LIKE ? OR last_name LIKE ?)")
            q = like(params["q"][0])
            values.extend([q, q, q])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with open_db() as conn:
            data = rows(conn, f"SELECT * FROM patients {where} ORDER BY patient_id LIMIT ?", tuple(values + [limit]))
        self.send_json({"patients": data, "count": len(data)})

    def handle_patient_detail(self, patient_id: str) -> None:
        with open_db() as conn:
            patient = one(conn, "SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
            if not patient:
                self.send_json({"error": "patient not found"}, 404)
                return
            payload = {
                "patient": patient,
                "rosters": rows(
                    conn, "SELECT * FROM intake_rosters WHERE patient_id = ? ORDER BY roster_id", (patient_id,)
                ),
                "coverage": rows(
                    conn, "SELECT * FROM coverage WHERE patient_id = ? ORDER BY coverage_id", (patient_id,)
                ),
                "pbm": rows(conn, "SELECT * FROM pbm WHERE patient_id = ? ORDER BY pbm_id", (patient_id,)),
                "pharmacies": rows(
                    conn,
                    """SELECT pp.preference_rank, ph.* FROM patient_pharmacy pp
                       JOIN pharmacies ph ON ph.pharmacy_id = pp.pharmacy_id
                       WHERE pp.patient_id = ? ORDER BY pp.preference_rank""",
                    (patient_id,),
                ),
                "lifestyle": one(conn, "SELECT * FROM lifestyle WHERE patient_id = ?", (patient_id,)),
                "clinical_history": one(conn, "SELECT * FROM clinical_history WHERE patient_id = ?", (patient_id,)),
                "referrals": rows(
                    conn,
                    "SELECT * FROM referrals WHERE patient_id = ? ORDER BY date_received, referral_id",
                    (patient_id,),
                ),
                "transfers": rows(
                    conn,
                    "SELECT * FROM transfer_requests WHERE patient_id = ? ORDER BY requested_start_date",
                    (patient_id,),
                ),
                "documents": rows(
                    conn,
                    "SELECT * FROM documents WHERE patient_id = ? ORDER BY received_date DESC, document_id",
                    (patient_id,),
                ),
                "chart_artifacts": rows(
                    conn, "SELECT * FROM chart_artifacts WHERE patient_id = ? ORDER BY artifact_type", (patient_id,)
                ),
                "program_candidates": rows(
                    conn, "SELECT * FROM program_candidates WHERE patient_id = ? ORDER BY program_code", (patient_id,)
                ),
            }
        self.send_json(payload)

    def handle_referrals(self, params: dict[str, list[str]]) -> None:
        limit = query_limit(params)
        clauses = []
        values: list[object] = []
        for field in ["batch_id", "service_line", "patient_id"]:
            if params.get(field):
                clauses.append(f"{field} = ?")
                values.append(params[field][0])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with open_db() as conn:
            data = rows(
                conn,
                f"SELECT * FROM referrals {where} ORDER BY batch_id, referral_id LIMIT ?",
                tuple(values + [limit]),
            )
        self.send_json({"referrals": data, "count": len(data)})

    def handle_referral_detail(self, referral_id: str) -> None:
        with open_db() as conn:
            referral = one(conn, "SELECT * FROM referrals WHERE referral_id = ?", (referral_id,))
            if not referral:
                self.send_json({"error": "referral not found"}, 404)
                return
            payload = {
                "referral": referral,
                "patient": one(conn, "SELECT * FROM patients WHERE patient_id = ?", (referral["patient_id"],)),
                "icd": one(conn, "SELECT * FROM icd_codes WHERE code = ?", (referral["icd10_code"],)),
                "documents": rows(
                    conn, "SELECT * FROM documents WHERE referral_id = ? ORDER BY received_date DESC", (referral_id,)
                ),
            }
        self.send_json(payload)

    def handle_transfers(self, params: dict[str, list[str]]) -> None:
        limit = query_limit(params)
        clauses = []
        values: list[object] = []
        for field in ["batch_id", "patient_id"]:
            if params.get(field):
                clauses.append(f"{field} = ?")
                values.append(params[field][0])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with open_db() as conn:
            data = rows(
                conn,
                f"SELECT * FROM transfer_requests {where} ORDER BY batch_id, requested_start_date, transfer_id LIMIT ?",
                tuple(values + [limit]),
            )
        self.send_json({"transfers": data, "count": len(data)})

    def handle_transfer_detail(self, transfer_id: str) -> None:
        with open_db() as conn:
            transfer = one(conn, "SELECT * FROM transfer_requests WHERE transfer_id = ?", (transfer_id,))
            if not transfer:
                self.send_json({"error": "transfer not found"}, 404)
                return
            payload = {
                "transfer": transfer,
                "patient": one(conn, "SELECT * FROM patients WHERE patient_id = ?", (transfer["patient_id"],)),
                "documents": rows(
                    conn, "SELECT * FROM documents WHERE transfer_id = ? ORDER BY doc_type", (transfer_id,)
                ),
                "capacity": rows(
                    conn,
                    """SELECT * FROM facility_capacity
                       WHERE modality = ? AND date BETWEEN ? AND COALESCE(?, ?)
                       ORDER BY date, location_id""",
                    (
                        transfer["modality"],
                        transfer["requested_start_date"],
                        transfer["requested_end_date"],
                        transfer["requested_start_date"],
                    ),
                ),
            }
        self.send_json(payload)

    def handle_documents(self, params: dict[str, list[str]]) -> None:
        limit = query_limit(params)
        clauses = []
        values: list[object] = []
        for field in ["patient_id", "referral_id", "transfer_id", "doc_type"]:
            if params.get(field):
                clauses.append(f"{field} = ?")
                values.append(params[field][0])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with open_db() as conn:
            data = rows(
                conn,
                f"SELECT * FROM documents {where} ORDER BY received_date DESC, document_id LIMIT ?",
                tuple(values + [limit]),
            )
        self.send_json({"documents": data, "count": len(data)})

    def handle_chart(self, patient_id: str) -> None:
        with open_db() as conn:
            patient = one(conn, "SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
            if not patient:
                self.send_json({"error": "patient not found"}, 404)
                return
            artifacts = rows(
                conn, "SELECT * FROM chart_artifacts WHERE patient_id = ? ORDER BY artifact_type", (patient_id,)
            )
            payload = {
                "patient": patient,
                "chart_artifacts": artifacts,
                "active_problems": [row for row in artifacts if row["artifact_type"] == "active_problems"],
                "recent_vitals_labs": [row for row in artifacts if row["artifact_type"] in {"vitals", "labs"}],
                "meds_allergies": [row for row in artifacts if row["artifact_type"] in {"medications", "allergies"}],
                "clinical_history": one(conn, "SELECT * FROM clinical_history WHERE patient_id = ?", (patient_id,)),
            }
        self.send_json(payload)

    def handle_program_candidates(self, program_code: str) -> None:
        with open_db() as conn:
            data = rows(
                conn,
                """SELECT pc.*, p.first_name, p.last_name, p.dob, p.phone, p.email, p.existing_chart
                   FROM program_candidates pc
                   JOIN patients p ON p.patient_id = pc.patient_id
                   WHERE pc.program_code = ?
                   ORDER BY pc.patient_id""",
                (program_code,),
            )
        self.send_json({"program_code": program_code, "candidates": data, "count": len(data)})

    def handle_icd(self, code: str) -> None:
        with open_db() as conn:
            data = one(conn, "SELECT * FROM icd_codes WHERE code = ?", (code,))
        if data:
            self.send_json({"icd": data})
        else:
            self.send_json({"error": "icd code not found"}, 404)

    def handle_pharmacies(self, params: dict[str, list[str]]) -> None:
        limit = query_limit(params, default=100)
        with open_db() as conn:
            if params.get("patient_id"):
                data = rows(
                    conn,
                    """SELECT pp.patient_id, pp.preference_rank, ph.*
                       FROM patient_pharmacy pp
                       JOIN pharmacies ph ON ph.pharmacy_id = pp.pharmacy_id
                       WHERE pp.patient_id = ?
                       ORDER BY pp.preference_rank""",
                    (params["patient_id"][0],),
                )
            else:
                clauses = []
                values: list[object] = []
                if params.get("network_status"):
                    clauses.append("network_status = ?")
                    values.append(params["network_status"][0])
                where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
                data = rows(
                    conn, f"SELECT * FROM pharmacies {where} ORDER BY pharmacy_id LIMIT ?", tuple(values + [limit])
                )
        self.send_json({"pharmacies": data, "count": len(data)})

    def handle_query(self) -> None:
        body = self.read_json()
        if not isinstance(body, dict):
            raise ValueError("request body must be a JSON object")
        sql = readonly_sql(str(body.get("sql", "")))
        params = body.get("params", [])
        if params is None:
            params = []
        if not isinstance(params, list):
            raise ValueError("params must be a list")
        with open_db() as conn:
            cur = conn.execute(sql, params)
            data = [dict(row) for row in cur.fetchmany(MAX_LIMIT + 1)]
            truncated = len(data) > MAX_LIMIT
            if truncated:
                data = data[:MAX_LIMIT]
            columns = [item[0] for item in cur.description] if cur.description else []
        self.send_json({"columns": columns, "rows": data, "row_count": len(data), "truncated": truncated})

    def handle_judge(self) -> None:
        body = self.read_json()
        if not isinstance(body, dict):
            self.send_json({"error": "request body must be a JSON object"}, 400)
            return
        try:
            result = score_train_answer(str(body.get("task_id", "")), body.get("answer"))
        except JudgeError as exc:
            self.send_json({"error": exc.message}, exc.status)
            return
        self.send_json(result)


def main() -> None:
    bind = os.environ.get("TASK_ENV_BIND", "0.0.0.0")
    port = int(os.environ.get("TASK_ENV_PORT", "9013"))
    server = ThreadingHTTPServer((bind, port), Handler)
    print(f"Cedar Ridge portal serving on {bind}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
