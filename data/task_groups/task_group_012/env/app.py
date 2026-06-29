#!/usr/bin/env python3
"""Local HR lifecycle portal service."""

from __future__ import annotations

import json
import mimetypes
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from judge_api import judge_answer_request


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
STATIC_DIR = ROOT / "static"


def ensure_data() -> None:
    if not (DATA_DIR / "manifest.json").exists():
        subprocess.run([sys.executable, str(ROOT / "generate_data.py")], check=True)


def read_json(name: str):
    with (DATA_DIR / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(name: str, payload) -> None:
    with (DATA_DIR / name).open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


def load_store() -> dict:
    return {
        "manifest": read_json("manifest.json"),
        "employees": read_json("employees.json"),
        "departments": read_json("departments.json"),
        "policies": read_json("policies.json"),
        "cases": read_json("cases.json"),
        "payroll_ledgers": read_json("payroll_ledgers.json"),
        "recruitment": read_json("recruitment.json"),
        "documents": read_json("documents.json"),
        "messages": read_json("messages.json"),
        "notifications": read_json("notifications.json"),
        "audit_events": read_json("audit_events.json"),
    }


def contains(value, needle: str) -> bool:
    return needle.lower() in str(value).lower()


def matches_query(item: dict, query: str) -> bool:
    if not query:
        return True
    return any(contains(value, query) for value in item.values() if not isinstance(value, (list, dict)))


def case_summary(case: dict) -> dict:
    return {
        key: case[key]
        for key in [
            "case_id",
            "title",
            "case_type",
            "status",
            "priority",
            "opened_at",
            "due_at",
            "employee_id",
            "employee_name",
            "department",
            "owner",
            "policy_refs",
            "summary",
        ]
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "NorthwindPeopleEnv/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def send_json(self, payload, status: int = 200) -> None:
        encoded = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_text(self, text: str, content_type: str = "text/plain; charset=utf-8", status: int = 200) -> None:
        encoded = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def serve_file(self, target: Path) -> None:
        if not target.exists() or not target.is_file():
            self.send_json({"error": "not_found"}, 404)
            return
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        payload = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def parse_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {key: values[-1] for key, values in parse_qs(raw).items()}

    def do_GET(self) -> None:
        store = load_store()
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/":
            self.serve_file(STATIC_DIR / "index.html")
            return
        if path.startswith("/static/"):
            rel = unquote(path.removeprefix("/static/"))
            target = (STATIC_DIR / rel).resolve()
            if not str(target).startswith(str(STATIC_DIR.resolve())):
                self.send_json({"error": "invalid_path"}, 400)
                return
            self.serve_file(target)
            return
        if path == "/health":
            self.send_json({"ok": True, "service": "northwind-people-env"})
            return
        if path == "/api/manifest":
            self.send_json(store["manifest"])
            return
        if path == "/api/summary":
            counts = {
                "employees": len(store["employees"]),
                "cases": len(store["cases"]),
                "policies": len(store["policies"]),
                "payroll_ledgers": len(store["payroll_ledgers"]),
                "recruitment": len(store["recruitment"]),
                "documents": len(store["documents"]),
                "messages": len(store["messages"]),
                "notifications": len(store["notifications"]),
                "audit_events": len(store["audit_events"]),
            }
            cases_by_status = {}
            for case in store["cases"]:
                cases_by_status[case["status"]] = cases_by_status.get(case["status"], 0) + 1
            self.send_json({"counts": counts, "cases_by_status": cases_by_status, "departments": store["departments"]})
            return
        if path == "/api/employees":
            search = query.get("q", [""])[0]
            status = query.get("status", [""])[0]
            rows = [emp for emp in store["employees"] if matches_query(emp, search)]
            if status:
                rows = [emp for emp in rows if emp["status"] == status]
            self.send_json(rows)
            return
        if path == "/api/cases":
            search = query.get("q", [""])[0]
            status = query.get("status", [""])[0]
            case_type = query.get("type", [""])[0]
            rows = [case_summary(case) for case in store["cases"] if matches_query(case, search)]
            if status:
                rows = [case for case in rows if case["status"] == status]
            if case_type:
                rows = [case for case in rows if case["case_type"] == case_type]
            self.send_json(rows)
            return
        if path.startswith("/api/cases/"):
            case_id = unquote(path.split("/")[-1])
            case = next((item for item in store["cases"] if item["case_id"] == case_id), None)
            self.send_json(case if case else {"error": "case_not_found"}, 200 if case else 404)
            return
        if path == "/api/policies":
            search = query.get("q", [""])[0]
            self.send_json([policy for policy in store["policies"] if matches_query(policy, search)])
            return
        if path.startswith("/api/policies/"):
            policy_id = unquote(path.split("/")[-1])
            policy = next((item for item in store["policies"] if item["policy_id"] == policy_id), None)
            self.send_json(policy if policy else {"error": "policy_not_found"}, 200 if policy else 404)
            return
        if path == "/api/payroll-ledgers":
            search = query.get("q", [""])[0]
            status = query.get("status", [""])[0]
            record_type = query.get("type", [""])[0]
            rows = [row for row in store["payroll_ledgers"] if matches_query(row, search)]
            if status:
                rows = [row for row in rows if row["status"] == status]
            if record_type:
                rows = [row for row in rows if row["record_type"] == record_type]
            self.send_json(rows)
            return
        if path == "/api/recruitment":
            search = query.get("q", [""])[0]
            self.send_json([row for row in store["recruitment"] if matches_query(row, search)])
            return
        if path == "/api/documents":
            search = query.get("q", [""])[0]
            self.send_json([row for row in store["documents"] if matches_query(row, search)])
            return
        if path == "/api/messages":
            search = query.get("q", [""])[0]
            self.send_json([row for row in store["messages"] if matches_query(row, search)])
            return
        if path == "/api/notifications":
            search = query.get("q", [""])[0]
            self.send_json([row for row in store["notifications"] if matches_query(row, search)])
            return
        if path == "/api/audit":
            search = query.get("q", [""])[0]
            case_id = query.get("case_id", [""])[0]
            rows = [row for row in store["audit_events"] if matches_query(row, search)]
            if case_id:
                rows = [row for row in rows if row["case_id"] == case_id]
            self.send_json(rows)
            return
        if path.startswith("/api/audit/"):
            audit_id = unquote(path.split("/")[-1])
            event = next((item for item in store["audit_events"] if item["audit_id"] == audit_id), None)
            self.send_json(event if event else {"error": "audit_event_not_found"}, 200 if event else 404)
            return
        if path.startswith("/api/attachments/"):
            attachment_id = unquote(path.split("/")[-1])
            for case in store["cases"]:
                for attachment in case["attachments"]:
                    if attachment["attachment_id"] == attachment_id:
                        self.send_text(attachment["content"])
                        return
            self.send_json({"error": "attachment_not_found"}, 404)
            return
        self.send_json({"error": "not_found"}, 404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/judge":
            length = int(self.headers.get("Content-Length", "0") or "0")
            status, payload = judge_answer_request(self.rfile.read(length))
            self.send_json(payload, status)
            return
        body = self.parse_body()
        if path.startswith("/api/cases/") and path.endswith("/comments"):
            case_id = unquote(path.split("/")[-2])
            cases = read_json("cases.json")
            for case in cases:
                if case["case_id"] == case_id:
                    next_id = len(case["comments"]) + 1
                    comment = {
                        "comment_id": f"CMT-{case_id[-3:]}-{next_id}",
                        "author": body.get("author", "Portal User"),
                        "created_at": body.get("created_at", "2026-06-05T09:00"),
                        "visibility": body.get("visibility", "Internal"),
                        "body": body.get("body", "").strip() or "No comment body provided.",
                    }
                    case["comments"].append(comment)
                    write_json("cases.json", cases)
                    self.send_json(comment, 201)
                    return
            self.send_json({"error": "case_not_found"}, 404)
            return
        self.send_json({"error": "not_found"}, 404)


def main() -> None:
    ensure_data()
    port = int(os.environ.get("PORT") or (sys.argv[1] if len(sys.argv) > 1 else "8120"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Northwind People Lifecycle Portal running at http://127.0.0.1:{port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
