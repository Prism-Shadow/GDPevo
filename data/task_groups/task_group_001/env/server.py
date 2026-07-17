#!/usr/bin/env python3
"""HarborCRM stdlib JSON API server."""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from judge_api import judge_answer_request


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "harborcrm_data.json"
MANIFEST_FILE = BASE_DIR / "data" / "manifest.json"


def ensure_data() -> None:
    if DATA_FILE.exists() and MANIFEST_FILE.exists():
        return
    import generate_data

    generate_data.main()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def first_param(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key)
    return values[0] if values else None


def filter_rows(rows: list[dict], **criteria: str | None) -> list[dict]:
    clean = {key: value for key, value in criteria.items() if value is not None}
    if not clean:
        return rows
    return [row for row in rows if all(str(row.get(key)) == str(value) for key, value in clean.items())]


def public_exhibitor(row: dict) -> dict:
    """Hide construction labels while preserving normal exhibitor-directory facts."""
    allowed = {
        "show_id",
        "company_id",
        "company_name",
        "website",
        "booth",
        "country",
        "description",
        "crm_account_id",
    }
    return {key: row.get(key) for key in allowed if key in row}


def public_policies(policies: dict) -> dict:
    return {
        "prospecting": {
            "platform_enums": policies.get("prospecting", {}).get("platform_enums", []),
            "qualification_note": (
                "Use exhibitor descriptions and company context to decide whether an "
                "account builds target underwater platforms or is only adjacent to them."
            ),
        },
        "contact_hygiene": {
            "note": "Prepare contacts for CRM import using normalized, contactable records.",
        },
        "sponsor_handoff": {
            "status_enums": ["paid_deferred", "open_invoice", "proposal_only", "not_sponsor"],
            "note": "Reconcile event, finance, and CRM records before final handoff.",
        },
    }


class HarborHandler(BaseHTTPRequestHandler):
    server_version = "HarborCRM/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write(f"{self.address_string()} - - [{self.log_date_time_string()}] {fmt % args}\n")

    @property
    def data(self) -> dict:
        return self.server.data  # type: ignore[attr-defined]

    @property
    def manifest(self) -> dict:
        return self.server.manifest  # type: ignore[attr-defined]

    def send_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def not_found(self, message: str = "Not found") -> None:
        self.send_json(404, {"error": message})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        parts = [part for part in path.split("/") if part]
        params = parse_qs(parsed.query)

        try:
            payload = self.route(parts, params)
        except KeyError as exc:
            self.not_found(str(exc))
            return
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
            return

        if payload is None:
            self.not_found()
            return
        self.send_json(200, payload)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/judge":
            self.not_found()
            return
        if os.environ.get("TASK_ENV_ENABLE_JUDGE") != "1":
            self.not_found()
            return
        length = int(self.headers.get("Content-Length", "0"))
        status, payload = judge_answer_request(self.rfile.read(length))
        self.send_json(status, payload)

    def route(self, parts: list[str], params: dict[str, list[str]]) -> object | None:
        if parts == ["health"]:
            return {
                "status": "ok",
                "service": "HarborCRM",
                "seed": self.manifest["seed"],
                "generated_at": self.manifest["generated_at"],
                "counts": self.manifest["counts"],
            }

        if parts == ["api", "policies"]:
            return public_policies(self.data["policies"])

        if len(parts) >= 2 and parts[:2] == ["api", "events"]:
            return self.route_events(parts, params)

        if len(parts) >= 3 and parts[:3] == ["api", "finance", "invoices"]:
            event_id = first_param(params, "event_id")
            account_id = first_param(params, "account_id")
            return filter_rows(self.data["finance_invoices"], event_id=event_id, account_id=account_id)

        if len(parts) >= 2 and parts[:2] == ["api", "crm"]:
            return self.route_crm(parts, params)

        if len(parts) >= 2 and parts[:2] == ["api", "tradeshows"]:
            return self.route_tradeshows(parts, params)

        if len(parts) >= 2 and parts[:2] == ["api", "import_batches"]:
            return self.route_import_batches(parts, params)

        return None

    def route_events(self, parts: list[str], params: dict[str, list[str]]) -> object | None:
        if parts == ["api", "events"]:
            status = first_param(params, "status")
            return filter_rows(self.data["events"], status=status)

        if len(parts) == 3:
            event_id = parts[2]
            matches = filter_rows(self.data["events"], event_id=event_id)
            return matches[0] if matches else None

        if len(parts) == 4:
            event_id = parts[2]
            child = parts[3]
            if not filter_rows(self.data["events"], event_id=event_id):
                return None
            if child in {"orders", "sponsor_packages"}:
                return filter_rows(self.data["sponsor_packages"], event_id=event_id)
            if child == "badges":
                return filter_rows(self.data["badges"], event_id=event_id)
        return None

    def route_crm(self, parts: list[str], params: dict[str, list[str]]) -> object | None:
        if len(parts) != 3:
            return None
        resource = parts[2]
        if resource == "accounts":
            status = first_param(params, "status")
            owner_region = first_param(params, "owner_region")
            return filter_rows(self.data["crm_accounts"], status=status, owner_region=owner_region)
        if resource == "contacts":
            account_id = first_param(params, "account_id")
            return filter_rows(self.data["crm_contacts"], account_id=account_id)
        if resource == "opportunities":
            event_id = first_param(params, "event_id")
            account_id = first_param(params, "account_id")
            return filter_rows(self.data["crm_opportunities"], event_id=event_id, account_id=account_id)
        if resource == "campaign_members":
            event_id = first_param(params, "event_id")
            account_id = first_param(params, "account_id")
            return filter_rows(self.data["campaign_members"], event_id=event_id, account_id=account_id)
        return None

    def route_tradeshows(self, parts: list[str], params: dict[str, list[str]]) -> object | None:
        if parts == ["api", "tradeshows"]:
            return self.data["tradeshows"]
        if len(parts) == 3:
            show_id = parts[2]
            matches = filter_rows(self.data["tradeshows"], show_id=show_id)
            return matches[0] if matches else None
        if len(parts) == 4:
            show_id = parts[2]
            child = parts[3]
            if not filter_rows(self.data["tradeshows"], show_id=show_id):
                return None
            if child == "exhibitors":
                rows = filter_rows(self.data["exhibitors"], show_id=show_id)
                return [public_exhibitor(row) for row in rows]
            if child == "meeting_interest":
                return filter_rows(self.data["meeting_interest"], show_id=show_id)
        return None

    def route_import_batches(self, parts: list[str], params: dict[str, list[str]]) -> object | None:
        if parts == ["api", "import_batches"]:
            return self.data["import_batches"]
        if len(parts) == 3:
            batch_id = parts[2]
            matches = filter_rows(self.data["import_batches"], batch_id=batch_id)
            return matches[0] if matches else None
        if len(parts) == 4:
            batch_id = parts[2]
            child = parts[3]
            if not filter_rows(self.data["import_batches"], batch_id=batch_id):
                return None
            if child == "raw_contacts":
                return filter_rows(self.data["raw_contacts"], batch_id=batch_id)
            if child == "suppression":
                return self.data["suppression"]
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the HarborCRM local JSON API.")
    parser.add_argument("--host", default=os.environ.get("TASK_ENV_BIND", os.environ.get("TASK_ENV_HOST", "0.0.0.0")))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("TASK_ENV_PORT", os.environ.get("PORT", "9001")))
    )
    args = parser.parse_args()

    ensure_data()
    data = load_json(DATA_FILE)
    manifest = load_json(MANIFEST_FILE)
    server = ThreadingHTTPServer((args.host, args.port), HarborHandler)
    server.data = data  # type: ignore[attr-defined]
    server.manifest = manifest  # type: ignore[attr-defined]
    print(f"HarborCRM API listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
