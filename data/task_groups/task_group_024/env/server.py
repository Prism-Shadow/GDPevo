#!/usr/bin/env python3
"""HTTP service for the engineering operations workspace."""

from __future__ import annotations

import argparse
import html
import json
import os
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from judge_api import judge_answer_request


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
JUDGE_ENABLED = os.environ.get("TASK_ENV_ENABLE_JUDGE", "0") == "1"

TABLE_FILES = {
    "teams": "teams.json",
    "owners": "owners.json",
    "work_items": "work_items.json",
    "status_history": "status_history.json",
    "dependencies": "dependencies.json",
    "blockers": "blockers.json",
    "releases": "releases.json",
    "milestones": "milestones.json",
    "milestone_items": "milestone_items.json",
    "portfolio_targets": "portfolio_targets.json",
    "sla_policies": "sla_policies.json",
    "documents": "documents.json",
}

CATEGORY_TERMS = {
    "security": {"security", "vulnerability", "compliance", "audit", "access", "credential", "encryption", "token"},
    "reliability": {"reliability", "slo", "incident", "capacity", "failover", "resiliency", "retry", "storm"},
    "techdebt": {"tech-debt", "tech debt", "refactor", "cleanup", "migration", "modernize", "internal", "platform"},
    "tech_debt": {"tech-debt", "tech debt", "refactor", "cleanup", "migration", "modernize", "internal", "platform"},
    "newfeature": {"feature", "enhancement", "customer", "workflow", "onboarding", "launch", "setting"},
    "new_feature": {"feature", "enhancement", "customer", "workflow", "onboarding", "launch", "setting"},
}


def load_data() -> dict[str, list[dict[str, object]]]:
    data = {}
    missing = []
    for key, filename in TABLE_FILES.items():
        path = DATA_DIR / filename
        if not path.exists():
            missing.append(str(path))
            continue
        with path.open("r", encoding="utf-8") as handle:
            data[key] = json.load(handle)
    if missing:
        raise RuntimeError("Generated data is missing. Run python3 generate_data.py. Missing: " + ", ".join(missing))
    return data


DATA = load_data()
ITEM_BY_ID = {item["id"]: item for item in DATA["work_items"]}
RELEASE_BY_ID = {release["release_id"]: release for release in DATA["releases"]}
MILESTONE_BY_ID = {milestone["milestone_id"]: milestone for milestone in DATA["milestones"]}
TEAM_BY_ID = {team["team_id"]: team for team in DATA["teams"]}
OWNER_BY_ID = {owner["owner_id"]: owner for owner in DATA["owners"]}


def first(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key)
    if not values:
        return None
    return values[0]


def text_blob(item: dict[str, object]) -> str:
    labels = item.get("labels") or []
    return " ".join(
        [
            str(item.get("title", "")),
            str(item.get("description", "")),
            str(item.get("work_type", "")),
            str(item.get("target_area", "")),
            " ".join(str(label) for label in labels),
        ]
    ).lower()


def matches_category_hint(item: dict[str, object], hint: str) -> bool:
    normalized = hint.strip().lower().replace("-", "_").replace(" ", "_")
    blob = text_blob(item)
    terms = CATEGORY_TERMS.get(normalized)
    if terms:
        return any(term in blob for term in terms)
    return hint.strip().lower() in blob


def release_item_ids(release_id: str) -> set[str]:
    return {item["id"] for item in DATA["work_items"] if release_id in (item.get("release_ids") or [])}


def collection(records: list[dict[str, object]]) -> dict[str, object]:
    return {"count": len(records), "results": records}


class Handler(BaseHTTPRequestHandler):
    server_version = "EngineeringOpsEnv/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - - [{self.log_date_time_string()}] {fmt % args}")

    def send_json(self, value: object, status: int = 200) -> None:
        payload = json.dumps(value, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_html(self, value: str, status: int = 200) -> None:
        payload = value.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:
        if urlparse(self.path).path.rstrip("/") != "/api/judge" or not JUDGE_ENABLED:
            self.send_json({"error": "not found", "path": self.path}, 404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        status, payload = judge_answer_request(self.rfile.read(length))
        self.send_json(payload, status)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = parse_qs(parsed.query, keep_blank_values=False)
        try:
            if path == "/health":
                self.send_json({"status": "ok", "service": "engineering-ops", "read_only": True})
            elif path == "/":
                self.send_html(self.index_page())
            elif path == "/web/dashboard":
                self.send_html(self.dashboard_page())
            elif path == "/web/policies":
                self.send_html(self.policies_page())
            elif path.startswith("/api/"):
                self.handle_api(path, params)
            else:
                self.send_json({"error": "not found", "path": path}, 404)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)

    def handle_api(self, path: str, params: dict[str, list[str]]) -> None:
        if path == "/api/teams":
            self.send_json(collection(DATA["teams"]))
            return
        if path == "/api/owners":
            records = DATA["owners"]
            team_id = first(params, "team_id")
            if team_id:
                records = [owner for owner in records if owner["team_id"] == team_id]
            self.send_json(collection(records))
            return
        if path == "/api/work-items":
            self.send_json(collection(self.filter_work_items(params)))
            return
        if path.startswith("/api/work-items/"):
            work_item_id = unquote(path.split("/", 3)[3])
            item = ITEM_BY_ID.get(work_item_id)
            if item is None:
                self.send_json({"error": "work item not found", "id": work_item_id}, 404)
            else:
                self.send_json(item)
            return
        if path == "/api/status-history":
            self.send_json(collection(self.filter_status_history(params)))
            return
        if path == "/api/dependencies":
            self.send_json(collection(self.filter_dependencies(params)))
            return
        if path == "/api/blockers":
            self.send_json(collection(self.filter_blockers(params)))
            return
        if path == "/api/releases":
            self.send_json(collection(DATA["releases"]))
            return
        if path.startswith("/api/releases/"):
            release_id = unquote(path.split("/", 3)[3])
            release = RELEASE_BY_ID.get(release_id)
            if release is None:
                self.send_json({"error": "release not found", "release_id": release_id}, 404)
            else:
                self.send_json(release)
            return
        if path == "/api/milestones":
            release_id = first(params, "release_id")
            records = DATA["milestones"]
            if release_id:
                records = [milestone for milestone in records if milestone["release_id"] == release_id]
            self.send_json(collection(records))
            return
        if path == "/api/milestone-items":
            self.send_json(collection(self.filter_milestone_items(params)))
            return
        if path == "/api/portfolio-targets":
            self.send_json(collection(self.filter_portfolio_targets(params)))
            return
        if path == "/api/sla-policies":
            self.send_json(collection(DATA["sla_policies"]))
            return
        if path == "/api/search":
            self.send_json(self.search(params))
            return
        self.send_json({"error": "unknown api endpoint", "path": path}, 404)

    def filter_work_items(self, params: dict[str, list[str]]) -> list[dict[str, object]]:
        product = first(params, "product")
        quarter = first(params, "quarter")
        status = first(params, "status")
        category_hint = first(params, "category_hint")
        release_id = first(params, "release_id")
        records = DATA["work_items"]
        if product:
            records = [item for item in records if str(item["product"]).lower() == product.lower()]
        if quarter:
            records = [item for item in records if item["quarter"] == quarter]
        if status:
            records = [item for item in records if str(item["status_export"]).lower() == status.lower()]
        if category_hint:
            records = [item for item in records if matches_category_hint(item, category_hint)]
        if release_id:
            records = [item for item in records if release_id in (item.get("release_ids") or [])]
        return sorted(records, key=lambda item: item["id"])

    def filter_status_history(self, params: dict[str, list[str]]) -> list[dict[str, object]]:
        work_item_id = first(params, "work_item_id")
        product = first(params, "product")
        records = DATA["status_history"]
        if work_item_id:
            records = [row for row in records if row["work_item_id"] == work_item_id]
        if product:
            product_ids = {
                item["id"] for item in DATA["work_items"] if str(item["product"]).lower() == product.lower()
            }
            records = [row for row in records if row["work_item_id"] in product_ids]
        return sorted(records, key=lambda row: (row["work_item_id"], row["timestamp"]))

    def filter_dependencies(self, params: dict[str, list[str]]) -> list[dict[str, object]]:
        release_id = first(params, "release_id")
        records = DATA["dependencies"]
        if release_id:
            ids = release_item_ids(release_id)
            records = [
                dependency
                for dependency in records
                if dependency["upstream_id"] in ids or dependency["downstream_id"] in ids
            ]
        return sorted(records, key=lambda row: (row["upstream_id"], row["downstream_id"], row["dependency_type"]))

    def filter_blockers(self, params: dict[str, list[str]]) -> list[dict[str, object]]:
        release_id = first(params, "release_id")
        active = first(params, "active")
        records = DATA["blockers"]
        if release_id:
            ids = release_item_ids(release_id)
            records = [blocker for blocker in records if blocker["work_item_id"] in ids]
        if active is not None:
            requested = active.lower() in {"1", "true", "yes"}
            records = [blocker for blocker in records if bool(blocker["active"]) is requested]
        return sorted(records, key=lambda row: row["blocker_id"])

    def filter_milestone_items(self, params: dict[str, list[str]]) -> list[dict[str, object]]:
        release_id = first(params, "release_id")
        records = DATA["milestone_items"]
        if release_id:
            milestone_ids = {
                milestone["milestone_id"] for milestone in DATA["milestones"] if milestone["release_id"] == release_id
            }
            records = [row for row in records if row["milestone_id"] in milestone_ids]
        return sorted(records, key=lambda row: (row["milestone_id"], row["work_item_id"]))

    def filter_portfolio_targets(self, params: dict[str, list[str]]) -> list[dict[str, object]]:
        product = first(params, "product")
        quarter = first(params, "quarter")
        records = DATA["portfolio_targets"]
        if product:
            records = [target for target in records if str(target["product"]).lower() == product.lower()]
        if quarter:
            records = [target for target in records if target["quarter"] == quarter]
        return sorted(records, key=lambda row: (row["product"], row["quarter"], row["category"]))

    def search(self, params: dict[str, list[str]]) -> dict[str, object]:
        query = (first(params, "q") or "").strip().lower()
        if not query:
            return {"count": 0, "results": []}
        results = []
        for item in DATA["work_items"]:
            blob = text_blob(item)
            if query in blob or query == str(item["id"]).lower():
                results.append(
                    {
                        "type": "work_item",
                        "id": item["id"],
                        "title": item["title"],
                        "product": item["product"],
                        "url": f"/api/work-items/{item['id']}",
                    }
                )
        for release in DATA["releases"]:
            blob = " ".join(
                str(release.get(key, "")) for key in ["release_id", "name", "product", "release_train"]
            ).lower()
            if query in blob:
                results.append(
                    {
                        "type": "release",
                        "id": release["release_id"],
                        "title": release["name"],
                        "product": release["product"],
                        "url": f"/api/releases/{release['release_id']}",
                    }
                )
        for blocker in DATA["blockers"]:
            blob = " ".join(
                str(blocker.get(key, "")) for key in ["blocker_id", "work_item_id", "blocker_type", "cause_text"]
            ).lower()
            if query in blob:
                results.append(
                    {
                        "type": "blocker",
                        "id": blocker["blocker_id"],
                        "title": blocker["blocker_type"],
                        "work_item_id": blocker["work_item_id"],
                    }
                )
        for document in DATA["documents"]:
            blob = " ".join(
                [
                    str(document.get("document_id", "")),
                    str(document.get("title", "")),
                    str(document.get("body", "")),
                    " ".join(document.get("tags", [])),
                ]
            ).lower()
            if query in blob:
                results.append(
                    {
                        "type": "document",
                        "id": document["document_id"],
                        "title": document["title"],
                        "url": "/web/policies",
                    }
                )
        return {"count": len(results), "results": results[:200]}

    def index_page(self) -> str:
        return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Engineering Operations Workspace</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.45; color: #1f2937; }
    a { color: #1d4ed8; }
    code { background: #f3f4f6; padding: 0.1rem 0.25rem; border-radius: 4px; }
  </style>
</head>
<body>
  <h1>Engineering Operations Workspace</h1>
  <p>This service exposes shared engineering operations records for portfolio, SLA, and release-readiness analysis.</p>
  <ul>
    <li><a href="/web/dashboard">Dashboard</a></li>
    <li><a href="/web/policies">Policies</a></li>
    <li><a href="/api/work-items">Work items API</a></li>
    <li><a href="/api/releases">Releases API</a></li>
    <li><a href="/api/search?q=release">Search API example</a></li>
  </ul>
</body>
</html>"""

    def dashboard_page(self) -> str:
        product_counts = defaultdict(int)
        release_counts = defaultdict(int)
        for item in DATA["work_items"]:
            product_counts[item["product"]] += 1
            for release_id in item.get("release_ids") or []:
                release_counts[release_id] += 1
        product_rows = "\n".join(
            f'<tr><td><a href="/api/work-items?product={quote(product)}">{html.escape(product)}</a></td><td>{count}</td></tr>'
            for product, count in sorted(product_counts.items())
        )
        release_rows = "\n".join(
            f'<tr><td><a href="/api/releases/{html.escape(release["release_id"])}">{html.escape(release["name"])}</a></td>'
            f"<td>{html.escape(release['product'])}</td><td>{html.escape(release['release_date'])}</td><td>{release_counts[release['release_id']]}</td></tr>"
            for release in DATA["releases"]
        )
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Engineering Operations Dashboard</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #111827; }}
    table {{ border-collapse: collapse; margin: 1rem 0 2rem; min-width: 42rem; }}
    th, td {{ border: 1px solid #d1d5db; padding: 0.45rem 0.6rem; text-align: left; }}
    th {{ background: #f3f4f6; }}
    a {{ color: #1d4ed8; }}
  </style>
</head>
<body>
  <h1>Engineering Operations Dashboard</h1>
  <p><a href="/web/policies">Policy notes</a> describe category precedence, SLA aging, and release readiness conventions.</p>
  <h2>Products</h2>
  <table><thead><tr><th>Product</th><th>Work items</th></tr></thead><tbody>{product_rows}</tbody></table>
  <h2>Releases</h2>
  <table><thead><tr><th>Release</th><th>Product</th><th>Date</th><th>Linked work items</th></tr></thead><tbody>{release_rows}</tbody></table>
</body>
</html>"""

    def policies_page(self) -> str:
        docs = "\n".join(
            f"<section><h2>{html.escape(doc['title'])}</h2><p>{html.escape(doc['body'])}</p></section>"
            for doc in DATA["documents"]
        )
        sla_rows = "\n".join(
            f"<tr><td>{html.escape(row['category'])}</td><td>{html.escape(row['severity'])}</td><td>{row['target_days']}</td></tr>"
            for row in DATA["sla_policies"]
        )
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Engineering Operations Policies</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 58rem; color: #111827; line-height: 1.5; }}
    table {{ border-collapse: collapse; margin: 1rem 0 2rem; }}
    th, td {{ border: 1px solid #d1d5db; padding: 0.4rem 0.55rem; text-align: left; }}
    th {{ background: #f3f4f6; }}
  </style>
</head>
<body>
  <h1>Engineering Operations Policies</h1>
  {docs}
  <h2>SLA Targets</h2>
  <table><thead><tr><th>Category</th><th>Severity</th><th>Target days</th></tr></thead><tbody>{sla_rows}</tbody></table>
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the engineering operations environment service.")
    parser.add_argument("--host", default=os.environ.get("TASK_ENV_BIND", "0.0.0.0"))
    parser.add_argument("--port", default=int(os.environ.get("TASK_ENV_PORT", "9024")), type=int)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Engineering operations environment listening at http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
