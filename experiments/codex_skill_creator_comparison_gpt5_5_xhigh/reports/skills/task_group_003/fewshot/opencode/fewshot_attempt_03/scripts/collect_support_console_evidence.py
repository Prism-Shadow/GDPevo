#!/usr/bin/env python3
"""Collect support-console evidence for ticket, mobile case, and enterprise tasks."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class ConsoleClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def get(self, path: str, default: Any = None) -> Any:
        url = f"{self.base_url}{path}"
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                return json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if default is not None:
                return default
            return {"_error": str(exc), "_path": path}

    def search(self, query: str) -> list[dict[str, Any]]:
        encoded = urllib.parse.urlencode({"q": query})
        data = self.get(f"/api/search?{encoded}", default={"results": []})
        if isinstance(data, dict) and isinstance(data.get("results"), list):
            return data["results"]
        return []

    def first_search_record(self, query: str, collection: str) -> dict[str, Any] | None:
        for result in self.search(query):
            if result.get("collection") == collection and isinstance(result.get("record"), dict):
                return result["record"]
        return None


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def matching_outages(outages: list[dict[str, Any]], ticket: dict[str, Any]) -> list[dict[str, Any]]:
    service_area = ticket.get("service_area")
    service_type = ticket.get("service_type")
    matches = []
    for outage in outages:
        service_types = outage.get("service_types") or []
        if (
            outage.get("active") is True
            and outage.get("service_area") == service_area
            and (not service_type or service_type in service_types)
        ):
            matches.append(outage)
    return matches


def collect_tickets(client: ConsoleClient, payload_dir: Path) -> list[dict[str, Any]]:
    ticket_files = [p for p in payload_dir.glob("*.csv") if "ticket" in p.name or "queue" in p.name]
    if not ticket_files:
        return []

    outages = as_list(client.get("/api/outages", default=[]))
    collected: list[dict[str, Any]] = []
    for ticket_file in sorted(ticket_files):
        for row in csv_rows(ticket_file):
            ticket_id = row.get("ticket_id", "")
            account_id = row.get("account_id", "")
            ticket = client.get(f"/api/tickets/{urllib.parse.quote(ticket_id)}", default=None)
            if not isinstance(ticket, dict) or "_error" in ticket:
                ticket = client.first_search_record(ticket_id, "tickets") or {}
            account = client.first_search_record(account_id, "accounts") if account_id else None
            diagnostics = client.get(f"/api/diagnostics/{urllib.parse.quote(ticket_id)}", default=None)
            troubleshooting = client.get(f"/api/troubleshooting/{urllib.parse.quote(ticket_id)}", default=None)
            collected.append(
                {
                    "source_file": ticket_file.name,
                    "payload_row": row,
                    "ticket": ticket,
                    "account": account,
                    "matching_outages": matching_outages(outages, ticket if isinstance(ticket, dict) else {}),
                    "diagnostics": diagnostics if isinstance(diagnostics, dict) else None,
                    "troubleshooting": troubleshooting if isinstance(troubleshooting, dict) else None,
                }
            )
    return collected


def case_ids_from_payload(payload_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    case_files = [p for p in payload_dir.glob("*.json") if p.name != "answer_template.json"]
    cases: list[dict[str, Any]] = []
    preferences: dict[str, Any] = {}
    for case_file in sorted(case_files):
        data = load_json(case_file)
        if isinstance(data, dict) and isinstance(data.get("cases"), list):
            for case in data["cases"]:
                if isinstance(case, dict) and case.get("case_id"):
                    merged = dict(case)
                    merged["_source_file"] = case_file.name
                    cases.append(merged)
            if isinstance(data.get("customer_preferences"), dict):
                preferences.update(data["customer_preferences"])
    return cases, preferences


def bills_for_customer(all_bills: list[dict[str, Any]], customer_id: str) -> list[dict[str, Any]]:
    return [bill for bill in all_bills if bill.get("customer_id") == customer_id]


def collect_cases(client: ConsoleClient, payload_dir: Path) -> list[dict[str, Any]]:
    payload_cases, preferences = case_ids_from_payload(payload_dir)
    if not payload_cases:
        return []

    all_bills = as_list(client.get("/api/bills", default=[]))
    collected: list[dict[str, Any]] = []
    for payload_case in payload_cases:
        case_id = payload_case["case_id"]
        case_record = client.first_search_record(case_id, "cases") or {}
        customer_id = case_record.get("customer_id")
        line_id = case_record.get("line_id")
        device_id = case_record.get("device_id")

        line = client.get(f"/api/lines/{urllib.parse.quote(str(line_id))}", default={}) if line_id else {}
        if isinstance(line, dict) and line.get("device_id"):
            device_id = line["device_id"]
        device = client.get(f"/api/devices/{urllib.parse.quote(str(device_id))}", default={}) if device_id else {}
        customer = client.get(f"/api/customers/{urllib.parse.quote(str(customer_id))}", default={}) if customer_id else {}
        plan_id = line.get("plan_id") if isinstance(line, dict) else None
        plan = client.get(f"/api/plans/{urllib.parse.quote(str(plan_id))}", default={}) if plan_id else {}

        collected.append(
            {
                "payload_case": payload_case,
                "case": case_record,
                "customer": customer if isinstance(customer, dict) else {},
                "line": line if isinstance(line, dict) else {},
                "device": device if isinstance(device, dict) else {},
                "plan": plan if isinstance(plan, dict) else {},
                "bills": bills_for_customer(all_bills, str(customer_id)),
                "payload_preferences": preferences.get(case_id, {}),
            }
        )
    return collected


def parse_enterprise_payloads(payload_dir: Path) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for path in payload_dir.glob("*.txt"):
        text = read_text(path)
        parsed["complaint_text"] = text
        incident_match = re.search(r"\bINC-\d+\b", text)
        client_match = re.search(r"^Client:\s*(.+)$", text, re.MULTILINE)
        product_match = re.search(r"^Product:\s*(.+)$", text, re.MULTILINE)
        if incident_match:
            parsed["incident_id"] = incident_match.group(0)
        if client_match:
            parsed["client_name"] = client_match.group(1).strip()
        if product_match:
            parsed["product"] = product_match.group(1).strip()
    for path in payload_dir.glob("*.json"):
        if path.name == "answer_template.json":
            continue
        data = load_json(path)
        if isinstance(data, dict) and "required_fields" in data:
            parsed["response_requirements"] = data
    return parsed


def meaningful_tokens(text: str) -> list[str]:
    skip = {"inc", "llc", "ltd", "corp", "group", "the", "and", "retail"}
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [token for token in tokens if len(token) > 3 and token not in skip]


def collect_enterprise(client: ConsoleClient, payload_dir: Path) -> dict[str, Any]:
    payload = parse_enterprise_payloads(payload_dir)
    if not payload:
        return {}

    incident_id = payload.get("incident_id")
    incident = client.get(f"/api/enterprise/incidents/{urllib.parse.quote(incident_id)}", default={}) if incident_id else {}
    if (not isinstance(incident, dict) or not incident) and incident_id:
        incident = client.first_search_record(incident_id, "enterprise_incidents") or {}

    client_name = payload.get("client_name", "")
    account = None
    enterprise_account_id = incident.get("enterprise_account_id") if isinstance(incident, dict) else None
    if enterprise_account_id:
        account = client.get(f"/api/enterprise/accounts/{urllib.parse.quote(str(enterprise_account_id))}", default=None)
    if not isinstance(account, dict) or not account:
        account = client.first_search_record(client_name, "enterprise_accounts") if client_name else None
    if account and not enterprise_account_id:
        enterprise_account_id = account.get("enterprise_account_id")

    export_runs = []
    for run in as_list(client.get("/api/enterprise/export-runs", default=[])):
        same_incident = incident_id and run.get("incident_id") == incident_id
        same_account = enterprise_account_id and run.get("enterprise_account_id") == enterprise_account_id
        if same_incident or same_account:
            export_runs.append(run)

    message_terms = set(meaningful_tokens(client_name))
    if incident_id:
        message_terms.add(incident_id.lower())

    messages = []
    for message in as_list(client.get("/api/enterprise/messages", default=[])):
        body = f"{message.get('body', '')} {message.get('channel', '')}".lower()
        if any(term in body for term in message_terms):
            messages.append(message)
    if not messages and payload.get("product"):
        product_terms = set(meaningful_tokens(str(payload["product"])))
        for message in as_list(client.get("/api/enterprise/messages", default=[])):
            body = f"{message.get('body', '')} {message.get('channel', '')}".lower()
            if any(term in body for term in product_terms):
                messages.append(message)

    sla = client.get(f"/api/enterprise/sla/{urllib.parse.quote(str(enterprise_account_id))}", default={}) if enterprise_account_id else {}
    return {
        "payload": payload,
        "incident": incident if isinstance(incident, dict) else {},
        "enterprise_account": account if isinstance(account, dict) else {},
        "export_runs": export_runs,
        "messages": messages,
        "sla": sla if isinstance(sla, dict) else {},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect support-console evidence for a task payload directory.")
    parser.add_argument("--base-url", required=True, help="Support console base URL, for example http://task-env:9003")
    parser.add_argument("--payload-dir", default="payloads", help="Directory containing task payload files")
    parser.add_argument("--output", help="Write evidence JSON to this path instead of stdout")
    args = parser.parse_args()

    payload_dir = Path(args.payload_dir)
    if not payload_dir.is_dir():
        print(f"payload directory not found: {payload_dir}", file=sys.stderr)
        return 2

    client = ConsoleClient(args.base_url)
    evidence = {
        "payload_dir": str(payload_dir),
        "payload_files": sorted(path.name for path in payload_dir.iterdir() if path.is_file()),
        "answer_template": load_json(payload_dir / "answer_template.json")
        if (payload_dir / "answer_template.json").exists()
        else None,
        "tickets": collect_tickets(client, payload_dir),
        "cases": collect_cases(client, payload_dir),
        "enterprise": collect_enterprise(client, payload_dir),
    }

    output = json.dumps(evidence, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
