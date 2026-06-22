#!/usr/bin/env python3
"""Standard-library JSON API for the MedBridge Sales Ops environment."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from judge_api import judge_answer_request


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "business_data.json"
MANIFEST_PATH = BASE_DIR / "data" / "manifest.json"

COLLECTIONS = {
    "customers": ("customers", "id"),
    "products": ("products", "code"),
    "rfqs": ("rfqs", "id"),
    "quotes": ("quotes", "id"),
    "freight-quotes": ("freight_quotes", "id"),
    "policies": ("policies", "id"),
    "opportunities": ("opportunities", "id"),
    "invoices": ("invoices", "id"),
    "payments": ("payments", "id"),
    "revenue-journals": ("revenue_journals", "id"),
    "events": ("events", "id"),
    "vouchers": ("vouchers", "code"),
}

DETAIL_ENDPOINTS = {
    "customers",
    "products",
    "rfqs",
    "quotes",
    "freight-quotes",
    "opportunities",
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


DATA = load_json(DATA_PATH)
MANIFEST = load_json(MANIFEST_PATH) if MANIFEST_PATH.exists() else {"endpoints": []}


def public_metadata() -> dict:
    metadata = DATA.get("metadata", {})
    return {
        "service": metadata.get("service", "MedBridge Sales Ops"),
        "description": metadata.get("description", ""),
        "seed": metadata.get("seed"),
        "generated_at": metadata.get("generated_at"),
        "endpoints": MANIFEST.get("endpoints", []),
        "collections": sorted(COLLECTIONS),
    }


def flatten_key_values(value, target_key: str) -> list:
    matches = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == target_key:
                matches.append(item)
            matches.extend(flatten_key_values(item, target_key))
    elif isinstance(value, list):
        for item in value:
            matches.extend(flatten_key_values(item, target_key))
    return matches


def scalar_matches(value, expected: str) -> bool:
    if isinstance(value, bool):
        return expected.lower() == str(value).lower()
    if value is None:
        return expected.lower() in {"none", "null", ""}
    if isinstance(value, (int, float)):
        return str(value) == expected or f"{float(value):.2f}" == expected
    return str(value).lower() == expected.lower()


def record_matches(record: dict, filters: dict[str, list[str]]) -> bool:
    for key, expected_values in filters.items():
        values = flatten_key_values(record, key)
        if not values:
            return False
        matched = False
        for expected in expected_values:
            for value in values:
                if isinstance(value, list):
                    if any(scalar_matches(item, expected) for item in value):
                        matched = True
                elif scalar_matches(value, expected):
                    matched = True
        if not matched:
            return False
    return True


def text_blob(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True).lower()


def record_identity(collection: str, record: dict) -> str | None:
    _, id_key = COLLECTIONS[collection]
    return record.get(id_key)


class Handler(BaseHTTPRequestHandler):
    server_version = "MedBridgeSalesOps/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path_parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
        query = parse_qs(parsed.query, keep_blank_values=True)

        if path_parts == ["health"]:
            self.send_json(
                200,
                {
                    "ok": True,
                    "status": "ok",
                    "service": "MedBridge Sales Ops",
                    "seed": DATA.get("metadata", {}).get("seed"),
                },
            )
            return

        if path_parts == ["api"]:
            self.send_json(200, public_metadata())
            return

        if path_parts == ["api", "search"]:
            self.handle_search(query)
            return

        if len(path_parts) >= 2 and path_parts[0] == "api":
            self.handle_collection(path_parts[1:], query)
            return

        self.send_json(404, {"error": "not_found", "message": "Endpoint not found."})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path_parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
        if path_parts == ["api", "judge"]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            status, payload = judge_answer_request(self.rfile.read(length))
            self.send_json(status, payload)
            return
        self.send_json(404, {"error": "not_found", "message": "Endpoint not found."})

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def handle_collection(self, parts: list[str], query: dict[str, list[str]]) -> None:
        collection_slug = parts[0]
        if collection_slug not in COLLECTIONS:
            self.send_json(404, {"error": "not_found", "message": "Unknown collection."})
            return

        data_key, id_key = COLLECTIONS[collection_slug]
        records = DATA.get(data_key, [])

        if len(parts) == 1:
            filters = {key: values for key, values in query.items() if key}
            filtered = [record for record in records if record_matches(record, filters)] if filters else records
            self.send_json(
                200,
                {
                    "collection": collection_slug,
                    "count": len(filtered),
                    "records": filtered,
                },
            )
            return

        if len(parts) == 2 and collection_slug in DETAIL_ENDPOINTS:
            record_id = parts[1]
            for record in records:
                if str(record.get(id_key)) == record_id:
                    self.send_json(200, record)
                    return
            self.send_json(404, {"error": "not_found", "message": f"{collection_slug} record not found."})
            return

        self.send_json(404, {"error": "not_found", "message": "Endpoint not found."})

    def handle_search(self, query: dict[str, list[str]]) -> None:
        search_text = query.get("q", [""])[0].strip().lower()
        if not search_text:
            self.send_json(200, {"q": "", "count": 0, "results": []})
            return

        results = []
        for collection_slug, (data_key, _) in COLLECTIONS.items():
            for record in DATA.get(data_key, []):
                if search_text in text_blob(record):
                    results.append(
                        {
                            "collection": collection_slug,
                            "id": record_identity(collection_slug, record),
                            "record": record,
                        }
                    )
        self.send_json(200, {"q": search_text, "count": len(results), "results": results[:100]})

    def send_json(self, status_code: int, payload) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status_code)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format: str, *args) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    port = int(os.environ.get("PORT", "8002"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"MedBridge Sales Ops API listening on http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
