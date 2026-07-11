#!/usr/bin/env python3
"""Small http.server app for the Northstar Care Intake Portal."""

from __future__ import annotations

import html
import json
import os
import secrets
import sys
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse


BASE = Path(__file__).resolve().parent
DATA_FILE = BASE / "data" / "generated_data.json"
EMAIL = "intake.admin@northstar.example"
PASSWORD = "Northstar-Intake-2026!"
ROLE = "Intake Operations Lead"
SESSIONS: set[str] = set()


def load_data() -> dict:
    if not DATA_FILE.exists():
        raise SystemExit("Missing data/generated_data.json. Run generate_data.py first.")
    return json.loads(DATA_FILE.read_text())


DATA = load_data()


def esc(value) -> str:
    if value is True:
        value = "yes"
    elif value is False:
        value = "no"
    elif value is None:
        value = ""
    return html.escape(str(value), quote=True)


def flatten(value, prefix: str = "") -> list[tuple[str, object]]:
    rows: list[tuple[str, object]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            label = f"{prefix}.{key}" if prefix else key
            rows.extend(flatten(item, label))
    elif isinstance(value, list):
        rows.append((prefix, ", ".join(str(x) for x in value)))
    else:
        rows.append((prefix, value))
    return rows


def badge(value) -> str:
    text = esc(value)
    lower = str(value).lower()
    cls = "neutral"
    if any(
        word in lower
        for word in (
            "active",
            "in network",
            "approved",
            "complete",
            "final",
            "ready",
            "sent",
            "signed",
            "current",
            "held",
        )
    ):
        cls = "good"
    if any(
        word in lower
        for word in (
            "missing",
            "inactive",
            "terminated",
            "out of network",
            "expired",
            "draft",
            "pending",
            "declined",
            "not ",
            "waitlist",
        )
    ):
        cls = "warn"
    if any(word in lower for word in ("urgent", "stat", "current")):
        cls = "hot" if "urgent" in lower or "stat" in lower else cls
    return f'<span class="badge {cls}">{text}</span>'


def find_by(items: list[dict], key: str, value: str) -> dict | None:
    for item in items:
        if str(item.get(key)) == value:
            return item
    return None


def patient_name(pid: str) -> str:
    patient = find_by(DATA["patients"], "patient_id", pid)
    return patient["name"] if patient else ""


def page(title: str, body: str, authed: bool) -> bytes:
    nav = ""
    if authed:
        links = [
            ("/dashboard", "Dashboard"),
            ("/patients", "Patients"),
            ("/benefits", "Benefits"),
            ("/pharmacies", "Pharmacies"),
            ("/transfers", "Transfers"),
            ("/referrals", "Referrals"),
            ("/charts", "Charts"),
            ("/programs", "Programs"),
            ("/queue", "Queue"),
            ("/documents", "Documents"),
            ("/policies", "Policies"),
        ]
        nav = "<nav>" + "".join(f'<a href="{href}">{label}</a>' for href, label in links) + "</nav>"
        nav += f'<div class="user">Signed in as {esc(EMAIL)} · {esc(ROLE)} · <a href="/logout">Logout</a></div>'
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)} - Northstar Care Intake</title>
  <style>
    :root {{ color-scheme: light; --ink:#1f2933; --muted:#617083; --line:#d8dee7; --bg:#f5f7fa; --panel:#fff; --blue:#245b8f; --green:#2f7d55; --amber:#95630f; --red:#b54708; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font:14px/1.45 system-ui, -apple-system, Segoe UI, sans-serif; color:var(--ink); background:var(--bg); }}
    header {{ background:#ffffff; border-bottom:1px solid var(--line); padding:14px 24px 10px; position:sticky; top:0; z-index:2; }}
    .brand {{ display:flex; align-items:baseline; gap:12px; margin-bottom:10px; }}
    .brand strong {{ font-size:19px; color:#18364f; }}
    .brand span, .user, .muted {{ color:var(--muted); }}
    nav {{ display:flex; gap:4px; flex-wrap:wrap; }}
    nav a {{ color:var(--blue); text-decoration:none; padding:6px 9px; border-radius:4px; }}
    nav a:hover {{ background:#edf4fa; }}
    main {{ max-width:1180px; margin:0 auto; padding:24px; }}
    h1 {{ margin:0 0 14px; font-size:24px; }}
    h2 {{ font-size:18px; margin:22px 0 8px; }}
    .panel {{ background:var(--panel); border:1px solid var(--line); border-radius:6px; padding:16px; margin-bottom:16px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; }}
    .metric {{ background:#fff; border:1px solid var(--line); border-radius:6px; padding:14px; }}
    .metric b {{ display:block; font-size:26px; }}
    table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid var(--line); }}
    th, td {{ text-align:left; border-bottom:1px solid var(--line); padding:8px 10px; vertical-align:top; }}
    th {{ background:#edf1f5; font-size:12px; text-transform:uppercase; letter-spacing:.02em; }}
    tr:hover td {{ background:#fafcff; }}
    a {{ color:var(--blue); }}
    .search {{ margin:0 0 12px; }}
    input[type=search], input[type=email], input[type=password] {{ width:100%; max-width:430px; padding:9px 10px; border:1px solid #b9c3cf; border-radius:4px; }}
    button {{ background:var(--blue); color:white; border:0; border-radius:4px; padding:9px 14px; cursor:pointer; }}
    .badge {{ display:inline-block; border-radius:999px; padding:2px 8px; font-size:12px; background:#eef1f5; color:#3d4b5c; }}
    .badge.good {{ background:#e8f5ee; color:var(--green); }}
    .badge.warn {{ background:#fff3df; color:var(--amber); }}
    .badge.hot {{ background:#fff0e8; color:var(--red); }}
    dl {{ display:grid; grid-template-columns:minmax(180px, 260px) 1fr; gap:0; background:#fff; border:1px solid var(--line); }}
    dt, dd {{ margin:0; padding:8px 10px; border-bottom:1px solid var(--line); }}
    dt {{ background:#f0f3f7; font-weight:600; color:#394b5f; }}
    .error {{ color:#a32020; font-weight:600; }}
    @media (max-width:700px) {{ main {{ padding:14px; }} dl {{ grid-template-columns:1fr; }} dt {{ border-bottom:0; }} table {{ font-size:13px; }} }}
  </style>
</head>
<body>
  <header><div class="brand"><strong>Northstar Care Intake</strong><span>operations portal</span></div>{nav}</header>
  <main>{body}</main>
</body>
</html>"""
    return html_doc.encode()


def detail_table(record: dict) -> str:
    rows = "".join(
        f"<dt>{esc(k.replace('_', ' ').title())}</dt><dd>{badge(v) if isinstance(v, str) else esc(v)}</dd>"
        for k, v in flatten(record)
    )
    return f"<dl>{rows}</dl>"


def search_box(section: str) -> str:
    return f'<form class="search" method="get"><input type="search" name="q" value="" placeholder="Search {esc(section)}"></form>'


def filter_items(items: list[dict], q: str) -> list[dict]:
    if not q:
        return items
    needle = q.lower()
    return [item for item in items if needle in json.dumps(item, sort_keys=True).lower()]


def table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


class Handler(BaseHTTPRequestHandler):
    server_version = "NorthstarIntake/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"{self.address_string()} - - [{self.log_date_time_string()}] {fmt % args}\n")

    def send_html(self, title: str, body: str, authed: bool = True, status: int = 200) -> None:
        content = page(title, body, authed)
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.end_headers()

    def authed(self) -> bool:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        sid = cookie.get("northstar_session")
        return bool(sid and sid.value in SESSIONS)

    def require_auth(self) -> bool:
        if self.authed():
            return True
        self.redirect("/login")
        return False

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        q = parse_qs(parsed.query).get("q", [""])[0].strip()
        if path == "/healthz":
            body = b"ok\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/":
            if self.authed():
                self.redirect("/dashboard")
            else:
                self.send_html(
                    "Welcome",
                    '<section class="panel"><h1>Northstar Care Intake</h1><p class="muted">Sign in to review intake records, transfer packets, referrals, charts, and program queues.</p><p><a href="/login">Go to login</a></p></section>',
                    False,
                )
            return
        if path == "/login":
            self.show_login()
            return
        if path == "/logout":
            self.logout()
            return
        if not self.require_auth():
            return
        self.route_business(path, q)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/login":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        fields = parse_qs(self.rfile.read(length).decode())
        if fields.get("email", [""])[0] == EMAIL and fields.get("password", [""])[0] == PASSWORD:
            sid = secrets.token_urlsafe(24)
            SESSIONS.add(sid)
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", "/dashboard")
            self.send_header("Set-Cookie", f"northstar_session={sid}; HttpOnly; SameSite=Lax; Path=/")
            self.end_headers()
        else:
            self.show_login("Invalid email or password.")

    def show_login(self, error: str = "") -> None:
        err = f'<p class="error">{esc(error)}</p>' if error else ""
        body = f"""<section class="panel"><h1>Sign in</h1>{err}
<form method="post" action="/login">
  <p><label>Email<br><input type="email" name="email" autocomplete="username" required></label></p>
  <p><label>Password<br><input type="password" name="password" autocomplete="current-password" required></label></p>
  <p><button type="submit">Sign in</button></p>
</form></section>"""
        self.send_html("Login", body, False, 401 if error else 200)

    def logout(self) -> None:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        sid = cookie.get("northstar_session")
        if sid:
            SESSIONS.discard(sid.value)
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", "/login")
        self.send_header("Set-Cookie", "northstar_session=; Max-Age=0; Path=/")
        self.end_headers()

    def route_business(self, path: str, q: str) -> None:
        if path == "/dashboard":
            self.dashboard()
        elif path == "/patients":
            self.patients(q)
        elif path.startswith("/patients/"):
            self.patient(path.rsplit("/", 1)[-1])
        elif path == "/benefits":
            self.benefits(q)
        elif path.startswith("/benefits/"):
            self.benefit(path.rsplit("/", 1)[-1])
        elif path == "/pharmacies":
            self.pharmacies(q)
        elif path == "/transfers":
            self.transfers(q)
        elif path.startswith("/transfers/"):
            self.transfer(path.rsplit("/", 1)[-1])
        elif path == "/referrals":
            self.referrals(q)
        elif path.startswith("/referrals/"):
            self.referral(path.rsplit("/", 1)[-1])
        elif path == "/charts":
            self.charts(q)
        elif path.startswith("/charts/"):
            self.chart(path.rsplit("/", 1)[-1])
        elif path == "/programs":
            self.programs(q)
        elif path.startswith("/programs/"):
            self.program(path.rsplit("/", 1)[-1])
        elif path == "/queue":
            self.queue(q)
        elif path.startswith("/queue/"):
            self.queue_detail(path.rsplit("/", 1)[-1])
        elif path == "/documents":
            self.documents()
        elif path == "/policies":
            self.policies()
        else:
            self.send_html("Not found", "<h1>Not found</h1>", True, 404)

    def dashboard(self) -> None:
        metrics = "".join(
            f'<div class="metric"><span>{esc(k.title())}</span><b>{len(DATA[k])}</b></div>'
            for k in ["patients", "benefits", "transfers", "referrals", "charts", "programs", "queue"]
        )
        urgent = [x for x in DATA["queue"] if x["urgency"] in ("urgent", "same day")]
        rows = [
            [
                f'<a href="/queue/{quote(x["queue_id"])}">{esc(x["queue_id"])}</a>',
                esc(x["service_family"]),
                badge(x["urgency"]),
                esc(x["visible_summary"]),
            ]
            for x in urgent[:8]
        ]
        self.send_html(
            "Dashboard",
            f'<h1>Dashboard</h1><section class="grid">{metrics}</section><h2>Priority queue</h2>{table(["Queue ID", "Family", "Urgency", "Summary"], rows)}',
        )

    def patients(self, q: str) -> None:
        items = filter_items(DATA["patients"], q)
        rows = [
            [
                f'<a href="/patients/{quote(p["patient_id"])}">{esc(p["patient_id"])}</a>',
                esc(p["name"]),
                esc(p["dob"]),
                esc(p["service_line"]),
                esc(p["requested_service"]),
            ]
            for p in items
        ]
        self.send_html(
            "Patients",
            f"<h1>Patients</h1>{search_box('patients')}{table(['Patient ID', 'Name', 'DOB', 'Service line', 'Requested service'], rows)}",
        )

    def patient(self, pid: str) -> None:
        rec = find_by(DATA["patients"], "patient_id", pid)
        if not rec:
            self.send_html("Patient not found", "<h1>Patient not found</h1>", True, 404)
            return
        links = f'<p><a href="/benefits/{quote(pid)}">Benefits</a> · <a href="/charts/{quote(pid)}">Chart</a> · <a href="/programs/{quote(pid)}">Program</a></p>'
        self.send_html(f"Patient {pid}", f"<h1>{esc(rec['name'])}</h1>{links}{detail_table(rec)}")

    def benefits(self, q: str) -> None:
        rows = []
        for b in filter_items(DATA["benefits"], q):
            rows.append(
                [
                    f'<a href="/benefits/{quote(b["patient_id"])}">{esc(b["patient_id"])}</a>',
                    esc(patient_name(b["patient_id"])),
                    badge(b["coverage_status"]),
                    badge(b["network_status"]),
                    badge(b["pbm_status"]),
                    badge(b["pharmacy_network_status"]),
                ]
            )
        self.send_html(
            "Benefits",
            f"<h1>Benefits</h1>{search_box('benefits')}{table(['Patient ID', 'Name', 'Coverage', 'Medical network', 'PBM', 'Pharmacy network'], rows)}",
        )

    def benefit(self, pid: str) -> None:
        rec = find_by(DATA["benefits"], "patient_id", pid)
        self.record_page("Benefits", rec, "Benefit not found")

    def pharmacies(self, q: str) -> None:
        rows = [
            [
                esc(p["pharmacy_id"]),
                esc(p["name"]),
                badge(p["network"]),
                badge("specialty" if p["specialty"] else "retail"),
                esc(p["phone"]),
            ]
            for p in filter_items(DATA["pharmacies"], q)
        ]
        self.send_html(
            "Pharmacies",
            f"<h1>Pharmacies</h1>{search_box('pharmacies')}{table(['ID', 'Name', 'Network', 'Type', 'Phone'], rows)}",
        )

    def transfers(self, q: str) -> None:
        rows = [
            [
                f'<a href="/transfers/{quote(t["transfer_id"])}">{esc(t["transfer_id"])}</a>',
                esc(t["patient_id"]),
                esc(patient_name(t["patient_id"])),
                esc(t["requested_start_date"]),
                badge(t["requested_chair_availability"]),
                badge(t["chart_prep_status"]),
            ]
            for t in filter_items(DATA["transfers"], q)
        ]
        self.send_html(
            "Transfers",
            f"<h1>Transfers</h1>{search_box('transfers')}{table(['Transfer ID', 'Patient ID', 'Name', 'Requested start', 'Chair', 'Chart prep'], rows)}",
        )

    def transfer(self, tid: str) -> None:
        rec = find_by(DATA["transfers"], "transfer_id", tid)
        self.record_page("Transfer", rec, "Transfer not found")

    def referrals(self, q: str) -> None:
        rows = [
            [
                f'<a href="/referrals/{quote(r["referral_id"])}">{esc(r["referral_id"])}</a>',
                esc(r["patient_name"]),
                esc(r["dob"]),
                esc(r["icd10_code"]),
                esc(r["laterality"]),
                badge(r["urgency"]),
                badge(r["authorization_status"]),
            ]
            for r in filter_items(DATA["referrals"], q)
        ]
        self.send_html(
            "Referrals",
            f"<h1>Referrals</h1>{search_box('referrals')}{table(['Referral ID', 'Patient', 'DOB', 'ICD-10', 'Laterality', 'Urgency', 'Auth'], rows)}",
        )

    def referral(self, rid: str) -> None:
        rec = find_by(DATA["referrals"], "referral_id", rid)
        self.record_page("Referral", rec, "Referral not found")

    def charts(self, q: str) -> None:
        rows = [
            [
                f'<a href="/charts/{quote(c["patient_id"])}">{esc(c["patient_id"])}</a>',
                esc(patient_name(c["patient_id"])),
                badge(c["chart_created"]),
                badge(c["demographics_complete"]),
                badge(c["history_complete"]),
                badge(c["problems_complete"]),
                badge(c["orientation_message"]),
            ]
            for c in filter_items(DATA["charts"], q)
        ]
        self.send_html(
            "Charts",
            f"<h1>Charts</h1>{search_box('charts')}{table(['Patient ID', 'Name', 'Created', 'Demographics', 'History', 'Problems', 'Orientation'], rows)}",
        )

    def chart(self, pid: str) -> None:
        rec = find_by(DATA["charts"], "patient_id", pid)
        self.record_page("Chart", rec, "Chart not found")

    def programs(self, q: str) -> None:
        rows = [
            [
                f'<a href="/programs/{quote(p["patient_id"])}">{esc(p["patient_id"])}</a>',
                esc(patient_name(p["patient_id"])),
                esc(", ".join(p["active_diagnoses"])),
                esc(p["recent_hba1c"]),
                esc(p["bp"]),
                badge(p["renal_flag"]),
                badge(p["consent_status"]),
                badge(p["program_form_status"]),
            ]
            for p in filter_items(DATA["programs"], q)
        ]
        self.send_html(
            "Programs",
            f"<h1>Programs</h1>{search_box('programs')}{table(['Patient ID', 'Name', 'Diagnoses', 'HbA1c', 'BP', 'Renal', 'Consent', 'Form'], rows)}",
        )

    def program(self, pid: str) -> None:
        rec = find_by(DATA["programs"], "patient_id", pid)
        self.record_page("Program", rec, "Program not found")

    def queue(self, q: str) -> None:
        rows = [
            [
                f'<a href="/queue/{quote(x["queue_id"])}">{esc(x["queue_id"])}</a>',
                esc(x["linked_record_type"]),
                esc(x["linked_id"]),
                esc(x["service_family"]),
                badge(x["urgency"]),
                badge(x["status"]),
                esc(x["visible_summary"]),
            ]
            for x in filter_items(DATA["queue"], q)
        ]
        self.send_html(
            "Queue",
            f"<h1>Queue</h1>{search_box('queue')}{table(['Queue ID', 'Type', 'Linked ID', 'Family', 'Urgency', 'Status', 'Summary'], rows)}",
        )

    def queue_detail(self, qid: str) -> None:
        rec = find_by(DATA["queue"], "queue_id", qid)
        if not rec:
            self.record_page("Queue", None, "Queue item not found")
            return
        target = {
            "transfer": f"/transfers/{quote(rec['linked_id'])}",
            "referral": f"/referrals/{quote(rec['linked_id'])}",
            "program": f"/programs/{quote(rec['linked_id'])}",
            "benefits": f"/benefits/{quote(rec['linked_id'])}",
            "chart": f"/charts/{quote(rec['linked_id'])}",
        }.get(rec["linked_record_type"], "#")
        self.send_html(
            "Queue item",
            f'<h1>{esc(qid)}</h1><p><a href="{target}">Open linked business record</a></p>{detail_table(rec)}',
        )

    def documents(self) -> None:
        rows = [
            [esc(d["document_id"]), esc(d["title"]), esc(d["owner"]), esc(d["updated"]), esc(d["summary"])]
            for d in DATA["documents"]
        ]
        self.send_html("Documents", f"<h1>Documents</h1>{table(['ID', 'Title', 'Owner', 'Updated', 'Summary'], rows)}")

    def policies(self) -> None:
        blocks = "".join(
            f'<section class="panel"><h2>{esc(p["policy_id"])} · {esc(p["title"])}</h2><p>{esc(p["body"])}</p></section>'
            for p in DATA["policies"]
        )
        self.send_html("Policies", f"<h1>Policies</h1>{blocks}")

    def record_page(self, title: str, rec: dict | None, missing: str) -> None:
        if not rec:
            self.send_html(title, f"<h1>{esc(missing)}</h1>", True, 404)
            return
        self.send_html(title, f"<h1>{esc(title)}</h1>{detail_table(rec)}")


def main() -> None:
    port = int(os.environ.get("TASK_ENV_PORT", "8073"))
    host = os.environ.get("TASK_ENV_HOST", "0.0.0.0")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Northstar Care Intake Portal listening at http://{host}:{port}", flush=True)
    print(f"Login: {EMAIL} / {PASSWORD}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
