#!/usr/bin/env python3
"""AsterOps local HTTP data-quality workbench."""

from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
DOWNLOADS_DIR = DATA_DIR / "downloads"

ENDPOINTS = {
    "/api/crm/contact_rows": {"key": "crm_contact_rows", "filters": {"batch_id", "person_key", "source_system"}},
    "/api/crm/campaign_members": {"key": "crm_campaign_members", "filters": {"campaign_id", "person_key"}},
    "/api/fleet/vehicles": {"key": "fleet_vehicles", "filters": {"region", "vehicle_id", "active"}},
    "/api/fleet/purchases": {"key": "fleet_purchases", "filters": {"region", "period", "vehicle_id"}},
    "/api/reference/fuel_aliases": {"key": "reference_fuel_aliases", "filters": {"canonical_fuel", "alias"}},
    "/api/facilities/charges": {"key": "facilities_charges", "filters": {"scope", "period"}},
    "/api/reference/category_aliases": {
        "key": "reference_category_aliases",
        "filters": {"canonical_category", "alias"},
    },
    "/api/logistics/cost_events": {"key": "logistics_cost_events", "filters": {"wave_id", "event_type"}},
    "/api/reference/quality_rules": {"key": "reference_quality_rules", "filters": {"domain", "rule_id"}},
}


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class AsterOpsHandler(BaseHTTPRequestHandler):
    server_version = "AsterOpsHTTP/1.0"

    def _send_json(self, status, payload):
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status, message):
        self._send_json(status, {"error": message, "status": status})

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = {key: values[-1] for key, values in parse_qs(parsed.query, keep_blank_values=True).items()}

        if path == "/api/health":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "version": self.server.manifest.get("version"),
                    "generated_at": self.server.manifest.get("generated_at"),
                    "record_counts": self.server.manifest.get("record_counts", {}),
                },
            )
            return

        if path == "/api/catalog":
            catalog = {}
            for endpoint, spec in ENDPOINTS.items():
                rows = self.server.data[spec["key"]]
                fields = sorted(rows[0].keys()) if rows else []
                catalog[endpoint] = {
                    "fields": fields,
                    "record_count": len(rows),
                    "filters": sorted(spec["filters"]),
                }
            self._send_json(
                200, {"endpoints": catalog, "downloads": sorted(p.name for p in DOWNLOADS_DIR.glob("*.csv"))}
            )
            return

        if path.startswith("/downloads/"):
            self._serve_download(path)
            return

        if path in ENDPOINTS:
            spec = ENDPOINTS[path]
            unknown = sorted(set(query) - spec["filters"])
            if unknown:
                self._send_error(400, f"Unsupported filter(s): {', '.join(unknown)}")
                return
            rows = self._filter_rows(self.server.data[spec["key"]], query)
            self._send_json(200, rows)
            return

        self._send_error(404, "Unknown endpoint")

    def _filter_rows(self, rows, query):
        filtered = rows
        for key, value in query.items():
            if key == "period":
                filtered = [row for row in filtered if self._row_period_match(row, value)]
            else:
                filtered = [row for row in filtered if str(row.get(key, "")) == value]
        return filtered

    @staticmethod
    def _row_period_match(row, value):
        for date_field in ("purchase_date", "charge_date", "event_date", "source_updated_at"):
            if str(row.get(date_field, "")).startswith(value):
                return True
        return False

    def _serve_download(self, path):
        filename = Path(unquote(path[len("/downloads/") :])).name
        file_path = (DOWNLOADS_DIR / filename).resolve()
        try:
            file_path.relative_to(DOWNLOADS_DIR.resolve())
        except ValueError:
            self._send_error(403, "Invalid download path")
            return
        if not file_path.is_file():
            self._send_error(404, "Download not found")
            return
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{file_path.name}"')
        self.end_headers()
        self.wfile.write(data)


def build_server(host, port):
    data_file = DATA_DIR / "asterops_data.json"
    manifest_file = DATA_DIR / "manifest.json"
    if not data_file.exists() or not manifest_file.exists():
        raise SystemExit("Generated data missing. Run generate_data.py first.")
    httpd = ThreadingHTTPServer((host, port), AsterOpsHandler)
    httpd.data = load_json(data_file)
    httpd.manifest = load_json(manifest_file)
    return httpd


def main():
    parser = argparse.ArgumentParser(description="Serve AsterOps environment data.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8007)
    args = parser.parse_args()
    httpd = build_server(args.host, args.port)
    print(f"AsterOps environment serving at http://{args.host}:{args.port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
