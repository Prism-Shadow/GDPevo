#!/usr/bin/env python3
"""Read-only Public Health Observatory HTML and CSV service."""

from __future__ import annotations

import csv
import html
import io
import json
import os
import re
import signal
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from judge_api import JudgeRejected, evaluate_answer, known_train_task, rejection

BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("TASK_ENV_DB_PATH", BASE / "generated/observatory.sqlite"))
JUDGE_ENABLED = os.environ.get("TASK_ENV_ENABLE_JUDGE") == "1"
PAGE_SIZES = {25, 50, 100, 200}
MAX_EXPORT = 100_000


def cols(*items):
    return list(items)


DATASETS = {
    "states": {
        "title": "State geography reference", "path": "/geographies/states", "from": "geo_state s",
        "columns": cols(("s.state_fips", "state_fips", "TEXT"), ("s.state_abbr", "state_abbr", "TEXT"), ("s.state_name", "state_name", "TEXT"), ("s.region", "region", "TEXT"), ("s.division", "division", "TEXT"), ("s.is_state", "is_state", "INTEGER")),
        "filters": {"state_abbr": "s.state_abbr", "state_fips": "s.state_fips", "region": "s.region", "division": "s.division"}, "order": "s.state_fips"},
    "counties": {
        "title": "County geography reference", "path": "/geographies/counties", "from": "geo_county c JOIN geo_state s ON s.state_fips=c.state_fips",
        "columns": cols(("c.county_fips", "county_fips", "TEXT"), ("c.state_abbr", "state_abbr", "TEXT"), ("c.county_name", "county_name", "TEXT"), ("s.region", "region", "TEXT"), ("c.rucc", "rucc", "INTEGER"), ("c.metro_class", "metro_class", "TEXT"), ("c.population_base", "population_base", "INTEGER"), ("c.latitude", "latitude", "REAL"), ("c.longitude", "longitude", "REAL")),
        "filters": {"county_fips": "c.county_fips", "state_abbr": "c.state_abbr", "region": "s.region", "rucc": "c.rucc", "metro_class": "c.metro_class"}, "order": "c.county_fips"},
    "countries": {
        "title": "Country geography reference", "path": "/geographies/countries", "from": "geo_country g",
        "columns": cols(("g.iso3", "iso3", "TEXT"), ("g.canonical_name", "canonical_name", "TEXT"), ("g.portal_label", "portal_label", "TEXT"), ("g.alternate_labels", "alternate_labels", "TEXT"), ("g.region", "region", "TEXT"), ("g.income_group", "income_group", "TEXT")),
        "filters": {"iso3": "g.iso3", "label": "g.portal_label", "region": "g.region", "income_group": "g.income_group"}, "order": "g.iso3"},
    "state_health": {
        "title": "State health observations", "path": "/data/state-health", "from": "state_health_observation o",
        "columns": cols(("o.observation_id", "observation_id", "TEXT"), ("o.state_fips", "state_fips", "TEXT"), ("o.state_abbr", "state_abbr", "TEXT"), ("o.year", "year", "INTEGER"), ("o.measure_id", "measure_id", "TEXT"), ("o.value_type", "value_type", "TEXT"), ("o.source_type", "source_type", "TEXT"), ("o.release_status", "release_status", "TEXT"), ("o.revision", "revision", "INTEGER"), ("o.value", "value", "REAL"), ("o.standard_error", "standard_error", "REAL"), ("o.sample_size", "sample_size", "INTEGER"), ("o.suppression_flag", "suppression_flag", "INTEGER"), ("o.quality_flag", "quality_flag", "TEXT"), ("o.released_at", "released_at", "TEXT")),
        "filters": {k: "o." + k for k in ("state_abbr", "measure_id", "year", "value_type", "source_type", "release_status", "revision")}, "order": "o.state_abbr,o.measure_id,o.year,o.value_type,o.source_type,o.release_status,o.revision,o.observation_id"},
    "state_socioeconomic": {
        "title": "State socioeconomic releases", "path": "/data/state-socioeconomic", "from": "state_socioeconomic o",
        "columns": cols(("o.record_id", "record_id", "TEXT"), ("o.state_fips", "state_fips", "TEXT"), ("o.state_abbr", "state_abbr", "TEXT"), ("o.year", "year", "INTEGER"), ("o.release_status", "release_status", "TEXT"), ("o.revision", "revision", "INTEGER"), ("o.released_at", "released_at", "TEXT"), ("o.poverty", "poverty", "REAL"), ("o.bachelors", "bachelors", "REAL"), ("o.median_income", "median_income", "REAL"), ("o.unemployment", "unemployment", "REAL"), ("o.uninsured", "uninsured", "REAL"), ("o.food_insecurity", "food_insecurity", "REAL"), ("o.population", "population", "INTEGER"), ("o.quality_flag", "quality_flag", "TEXT")),
        "filters": {k: "o." + k for k in ("state_abbr", "year", "release_status", "revision")}, "order": "o.state_abbr,o.year,o.release_status,o.revision,o.record_id"},
    "county_health": {
        "title": "County health observations", "path": "/data/county-health", "from": "county_health_observation o JOIN geo_county c ON c.county_fips=o.county_fips JOIN geo_state s ON s.state_fips=c.state_fips",
        "columns": cols(("o.observation_id", "observation_id", "TEXT"), ("o.county_fips", "county_fips", "TEXT"), ("o.state_abbr", "state_abbr", "TEXT"), ("s.region", "region", "TEXT"), ("o.year", "year", "INTEGER"), ("o.measure_id", "measure_id", "TEXT"), ("o.value_type", "value_type", "TEXT"), ("o.release_status", "release_status", "TEXT"), ("o.revision", "revision", "INTEGER"), ("o.released_at", "released_at", "TEXT"), ("o.value", "value", "REAL"), ("o.low_ci", "low_ci", "REAL"), ("o.high_ci", "high_ci", "REAL"), ("o.population", "population", "INTEGER"), ("o.suppression_flag", "suppression_flag", "INTEGER"), ("o.quality_flag", "quality_flag", "TEXT")),
        "filters": {"county_fips": "o.county_fips", "state_abbr": "o.state_abbr", "region": "s.region", **{k: "o." + k for k in ("measure_id", "year", "value_type", "release_status", "revision", "suppression_flag")}}, "order": "o.county_fips,o.measure_id,o.year,o.value_type,o.release_status,o.revision,o.observation_id"},
    "county_socioeconomic": {
        "title": "County socioeconomic releases", "path": "/data/county-socioeconomic", "from": "county_socioeconomic o JOIN geo_county c ON c.county_fips=o.county_fips JOIN geo_state s ON s.state_fips=c.state_fips",
        "columns": cols(("o.record_id", "record_id", "TEXT"), ("o.county_fips", "county_fips", "TEXT"), ("o.state_abbr", "state_abbr", "TEXT"), ("s.region", "region", "TEXT"), ("o.year", "year", "INTEGER"), ("o.release_status", "release_status", "TEXT"), ("o.revision", "revision", "INTEGER"), ("o.released_at", "released_at", "TEXT"), ("o.poverty", "poverty", "REAL"), ("o.median_income", "median_income", "REAL"), ("o.bachelors", "bachelors", "REAL"), ("o.unemployment", "unemployment", "REAL"), ("o.net_migration", "net_migration", "REAL"), ("o.uninsured", "uninsured", "REAL"), ("o.population", "population", "INTEGER"), ("o.quality_flag", "quality_flag", "TEXT")),
        "filters": {"county_fips": "o.county_fips", "state_abbr": "o.state_abbr", "region": "s.region", **{k: "o." + k for k in ("year", "release_status", "revision")}}, "order": "o.county_fips,o.year,o.release_status,o.revision,o.record_id"},
    "country_indicators": {
        "title": "Country indicator observations", "path": "/data/country-indicators", "from": "country_indicator_observation o",
        "columns": cols(("o.observation_id", "observation_id", "TEXT"), ("o.country_label", "country_label", "TEXT"), ("o.iso3", "iso3", "TEXT"), ("o.year", "year", "INTEGER"), ("o.indicator_id", "indicator_id", "TEXT"), ("o.release_status", "release_status", "TEXT"), ("o.revision", "revision", "INTEGER"), ("o.released_at", "released_at", "TEXT"), ("o.value", "value", "REAL"), ("o.unit", "unit", "TEXT"), ("o.quality_flag", "quality_flag", "TEXT")),
        "filters": {k: "o." + k for k in ("iso3", "country_label", "indicator_id", "year", "release_status", "revision", "quality_flag")}, "order": "o.country_label,o.indicator_id,o.year,o.release_status,o.revision,o.observation_id"},
    "revisions": {
        "title": "Revision notices", "path": "/data/revisions", "from": "revision_event r",
        "columns": cols(("r.revision_event_id", "revision_event_id", "TEXT"), ("r.domain", "domain", "TEXT"), ("r.entity_id", "entity_id", "TEXT"), ("r.field_id", "field_id", "TEXT"), ("r.effective_year", "effective_year", "INTEGER"), ("r.old_value", "old_value", "REAL"), ("r.new_value", "new_value", "REAL"), ("r.status", "status", "TEXT"), ("r.issued_at", "issued_at", "TEXT"), ("r.reason_code", "reason_code", "TEXT"), ("r.note", "note", "TEXT")),
        "filters": {k: "r." + k for k in ("domain", "entity_id", "field_id", "effective_year", "status")}, "order": "r.issued_at,r.revision_event_id"},
}

PATH_DATASET = {cfg["path"]: name for name, cfg in DATASETS.items()}


def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def connection():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def page_shell(title, body):
    nav = " ".join(f'<a href="{p}">{esc(t)}</a>' for p, t in (("/", "Home"), ("/catalog", "Catalog"), ("/geographies/states", "States"), ("/geographies/counties", "Counties"), ("/geographies/countries", "Countries"), ("/methodology", "Methodology")))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{esc(title)} — Public Health Observatory</title><style>body{{font:15px system-ui,sans-serif;line-height:1.45;margin:auto;max-width:1500px;padding:1.2rem;color:#172331}}nav{{padding:.7rem;background:#e8f1f5}}nav a{{margin-right:1rem}}a{{color:#075b82}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{border:1px solid #ccd6dc;padding:.35rem;text-align:left;vertical-align:top}}th{{background:#edf3f6;position:sticky;top:0}}.scroll{{overflow:auto}}label{{display:inline-block;margin:.25rem .5rem .25rem 0}}input,select{{padding:.25rem}}.card{{border:1px solid #ccd6dc;padding:.8rem;margin:.6rem 0}}.muted{{color:#536773}}.error{{color:#8b1e1e}}code{{background:#edf3f6;padding:.1rem .2rem}}</style></head><body><header><h1>Public Health Observatory Data Portal</h1><nav>{nav}</nav></header><main><h2>{esc(title)}</h2>{body}</main></body></html>'''


class RequestError(Exception):
    pass


def parse_request(cfg, query, paginate=True):
    allowed = set(cfg["filters"]) | ({"page", "page_size"} if paginate else {"format", "dataset"})
    unknown = set(query) - allowed
    if unknown:
        raise RequestError("Unsupported parameter: " + sorted(unknown)[0])
    where, params = [], []
    with connection() as conn:
        for name, expression in cfg["filters"].items():
            if name not in query:
                continue
            raw = query[name][0].strip()
            if not raw:
                raise RequestError(f"Filter {name} cannot be empty")
            values = [v.strip() for v in raw.split(",")]
            if any(not v or len(v) > 100 or not re.fullmatch(r"[A-Za-z0-9 _.'-]+", v) for v in values):
                raise RequestError(f"Invalid value for {name}")
            valid = {str(row[0]) for row in conn.execute(f"SELECT DISTINCT {expression} FROM {cfg['from']} WHERE {expression} IS NOT NULL")}
            if any(v not in valid for v in values):
                raise RequestError(f"Unknown value for {name}")
            where.append(f"{expression} IN ({','.join('?' for _ in values)})")
            params.extend(values)
    page, size = 1, 50
    if paginate:
        try:
            page = int(query.get("page", ["1"])[0])
            size = int(query.get("page_size", ["50"])[0])
        except ValueError as exc:
            raise RequestError("page and page_size must be integers") from exc
        if page < 1 or size not in PAGE_SIZES:
            raise RequestError("page must be positive and page_size must be 25, 50, 100, or 200")
    return where, params, page, size


def query_rows(name, query, export=False):
    cfg = DATASETS[name]
    where, params, page, size = parse_request(cfg, query, not export)
    clause = " WHERE " + " AND ".join(where) if where else ""
    selected = ",".join(f"{expr} AS {alias}" for expr, alias, _ in cfg["columns"])
    with connection() as conn:
        total = conn.execute(f"SELECT count(*) FROM {cfg['from']}{clause}", params).fetchone()[0]
        if export and total > MAX_EXPORT:
            raise RequestError("Export exceeds 100,000 rows; narrow the filters and try again")
        tail = "" if export else " LIMIT ? OFFSET ?"
        values = list(params) + ([] if export else [size, (page - 1) * size])
        rows = conn.execute(f"SELECT {selected} FROM {cfg['from']}{clause} ORDER BY {cfg['order']}{tail}", values).fetchall()
    return cfg, rows, total, page, size


def dataset_page(name, query):
    cfg, rows, total, page, size = query_rows(name, query)
    controls = []
    for key in cfg["filters"]:
        controls.append(f'<label>{esc(key)} <input name="{esc(key)}" value="{esc(query.get(key, [""])[0])}"></label>')
    controls.append(f'<label>page size <select name="page_size">' + "".join(f'<option{(" selected" if size == n else "")} value="{n}">{n}</option>' for n in sorted(PAGE_SIZES)) + "</select></label>")
    clean = {k: v[0] for k, v in query.items() if k in cfg["filters"] and v[0]}
    csv_q = urlencode({"dataset": name, "format": "csv", **clean})
    headers = [alias for _, alias, _ in cfg["columns"]]
    table = '<div class="scroll"><table><thead><tr>' + "".join(f"<th>{esc(h)}</th>" for h in headers) + "</tr></thead><tbody>"
    table += "".join("<tr>" + "".join(f'<td>{esc("—" if row[h] is None else row[h])}</td>' for h in headers) + "</tr>" for row in rows) + "</tbody></table></div>"
    links = []
    if page > 1:
        links.append(f'<a href="?{esc(urlencode({**clean, "page_size": size, "page": page - 1}))}">Previous</a>')
    if page * size < total:
        links.append(f'<a href="?{esc(urlencode({**clean, "page_size": size, "page": page + 1}))}">Next</a>')
    body = f'<p>{esc(cfg["title"])}. Filters accept comma-separated exact values. Missing values are shown as an em dash.</p><form method="get">{" ".join(controls)} <button>Apply filters</button></form><p><strong>{total:,}</strong> matching rows; page {page}. <a href="/download?{esc(csv_q)}">Download matching CSV</a></p>{table}<p>{" | ".join(links)}</p>'
    return page_shell(cfg["title"], body)


class Handler(BaseHTTPRequestHandler):
    server_version = "Observatory/1.0"

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}", flush=True)

    def send_bytes(self, status, payload, content_type, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(payload)

    def send_html(self, status, title, body):
        self.send_bytes(status, page_shell(title, body).encode(), "text/html; charset=utf-8")

    def do_GET(self):
        parsed = urlsplit(self.path)
        query = parse_qs(parsed.query, keep_blank_values=True)
        try:
            if parsed.path == "/health":
                expected = set(DATASETS)
                with connection() as conn:
                    ok = conn.execute("PRAGMA quick_check").fetchone()[0] == "ok"
                    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not ok or not {"geo_state", "geo_county", "geo_country", "state_health_observation", "country_indicator_observation"} <= tables:
                    raise RuntimeError("database validation failed")
                self.send_bytes(200, b'{"status":"ok"}\n', "application/json; charset=utf-8")
            elif parsed.path == "/":
                if query:
                    raise RequestError("The landing page does not accept parameters")
                cards = "".join(f'<div class="card"><h3><a href="{cfg["path"]}">{esc(cfg["title"])}</a></h3><p>Browse auditable releases or export the same filtered rows as CSV.</p></div>' for cfg in DATASETS.values())
                body = '<p>Browse surveillance, socioeconomic, geography, revision, and methodology records. Publication status, revision, value type, and source fields are retained for audit.</p><div class="card"><h3>Release notices</h3><p>Final releases may supersede provisional records. Applied revisions are reflected in later final revisions; pending and withdrawn notices do not replace published values.</p></div><form method="get" action="/data/state-health"><label>State abbreviation <input name="state_abbr" placeholder="CA"></label><label>Year <input name="year" placeholder="2024"></label><button>Browse state health</button></form>' + cards
                self.send_bytes(200, page_shell("Portal home", body).encode(), "text/html; charset=utf-8")
            elif parsed.path in PATH_DATASET:
                self.send_bytes(200, dataset_page(PATH_DATASET[parsed.path], query).encode(), "text/html; charset=utf-8")
            elif parsed.path == "/catalog":
                if query:
                    raise RequestError("The catalog does not accept parameters")
                blocks = []
                with connection() as conn:
                    for name, cfg in DATASETS.items():
                        count = conn.execute(f"SELECT count(*) FROM {cfg['from']}").fetchone()[0]
                        years = [alias for _, alias, _ in cfg["columns"] if alias in ("year", "effective_year")]
                        coverage = "not applicable"
                        if years:
                            expr = next(expr for expr, alias, _ in cfg["columns"] if alias == years[0])
                            lo, hi = conn.execute(f"SELECT min({expr}),max({expr}) FROM {cfg['from']}").fetchone()
                            coverage = f"{lo}–{hi}"
                        schema = ", ".join(f"{alias} ({typ})" for _, alias, typ in cfg["columns"])
                        blocks.append(f'<div class="card"><h3>{esc(name)}</h3><p>{count:,} rows; coverage {esc(coverage)}.</p><p><strong>Columns:</strong> {esc(schema)}</p><p><strong>Filters:</strong> {esc(", ".join(cfg["filters"]))}</p><p><a href="{cfg["path"]}">Browse</a> · <a href="/download?{urlencode({"dataset": name, "format": "csv"})}">CSV</a></p></div>')
                    measures = conn.execute("SELECT domain,measure_id,display_name,unit,direction FROM measure_dictionary ORDER BY domain,measure_id").fetchall()
                mt = '<table><tr><th>domain</th><th>measure_id</th><th>display_name</th><th>unit</th><th>direction</th></tr>' + "".join("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in row) + "</tr>" for row in measures) + "</table>"
                self.send_bytes(200, page_shell("Dataset catalog", "".join(blocks) + "<h3>Measure dictionary</h3>" + mt).encode(), "text/html; charset=utf-8")
            elif parsed.path == "/methodology":
                unknown = set(query) - {"doc"}
                if unknown:
                    raise RequestError("Unsupported methodology parameter")
                with connection() as conn:
                    docs = conn.execute("SELECT * FROM methodology_document ORDER BY effective_date DESC,doc_id").fetchall()
                wanted = query.get("doc", [None])[0]
                if wanted and wanted not in {d["doc_id"] for d in docs}:
                    raise RequestError("Unknown methodology document")
                index = "<ul>" + "".join(f'<li><a href="/methodology?doc={esc(d["doc_id"])}">{esc(d["title"])}</a> ({esc(d["status"])}, {esc(d["effective_date"])})</li>' for d in docs) + "</ul>"
                shown = [d for d in docs if not wanted or d["doc_id"] == wanted]
                articles = "".join(f'<article class="card"><h3>{esc(d["title"])}</h3><p class="muted">Version {esc(d["version"])} · {esc(d["effective_date"])} · {esc(d["status"])} · {esc(d["topic"])}</p><p>{esc(d["body"])}</p></article>' for d in shown)
                self.send_bytes(200, page_shell("Methodology library", "<h3>Document index</h3>" + index + articles).encode(), "text/html; charset=utf-8")
            elif parsed.path == "/download":
                name = query.get("dataset", [""])[0]
                if name not in DATASETS:
                    raise RequestError("Unknown dataset")
                if query.get("format", [""])[0] != "csv":
                    raise RequestError("format must be csv")
                cfg, rows, _, _, _ = query_rows(name, query, export=True)
                output = io.StringIO(newline="")
                writer = csv.writer(output, lineterminator="\n")
                headers = [a for _, a, _ in cfg["columns"]]
                writer.writerow(headers)
                writer.writerows([[row[h] for h in headers] for row in rows])
                self.send_bytes(200, output.getvalue().encode(), "text/csv; charset=utf-8", {"Content-Disposition": f'attachment; filename="{name}.csv"'})
            else:
                self.send_html(404, "Not found", "<p>The requested page was not found.</p>")
        except RequestError as exc:
            self.send_html(400, "Invalid request", f'<p class="error">{esc(exc)}</p>')
        except (sqlite3.Error, OSError):
            self.send_html(503, "Unavailable", '<p class="error">The data service is temporarily unavailable.</p>')

    def do_POST(self):
        if urlsplit(self.path).path != "/api/judge" or not JUDGE_ENABLED:
            self.send_html(404, "Not found", "<p>The requested page was not found.</p>")
            return
        rejected = rejection()
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 65536:
                status = 413 if length > 65536 else 400
                raise JudgeRejected
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                status = 415
                raise JudgeRejected
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                status = 400
                raise JudgeRejected
            task_id = payload.get("task_id")
            if not known_train_task(task_id):
                status = 404
                raise JudgeRejected
            status = 422
            response = evaluate_answer(task_id, payload.get("answer"))
            status = 200
        except (ValueError, json.JSONDecodeError):
            status, response = 400, rejected
        except JudgeRejected:
            response = rejected
        self.send_bytes(status, json.dumps(response, separators=(",", ":")).encode(), "application/json; charset=utf-8")


def main():
    bind = os.environ.get("TASK_ENV_BIND", "0.0.0.0")
    try:
        port = int(os.environ.get("TASK_ENV_PORT", "9023"))
    except ValueError as exc:
        raise SystemExit("TASK_ENV_PORT must be an integer") from exc
    server = ThreadingHTTPServer((bind, port), Handler)
    server.daemon_threads = True
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    print(f"Public Health Observatory listening on {bind}:{port}; judge={'enabled' if JUDGE_ENABLED else 'disabled'}", flush=True)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
