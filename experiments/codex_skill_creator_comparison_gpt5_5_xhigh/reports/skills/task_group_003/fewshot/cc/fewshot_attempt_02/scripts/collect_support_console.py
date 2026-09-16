#!/usr/bin/env python3
"""Collect support-console evidence for payload-driven JSON tasks.

The script intentionally stops before making final decisions. It reads local
payload files, follows their IDs into the support-console API, and writes a
single evidence JSON file for the solver to inspect.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def get_json(base_url: str, path: str) -> Any | None:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def get_first(base_url: str, paths: list[str]) -> Any | None:
    for path in paths:
        result = get_json(base_url, path)
        if result is not None:
            return result
    return None


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def indexed_by(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {item[key]: item for item in items if key in item}


def collect_ticket_evidence(base_url: str, payloads: dict[str, Any]) -> dict[str, Any]:
    rows = payloads.get("ticket_batch.csv") or payloads.get("queue_snapshot.csv") or []
    outages = get_json(base_url, "/api/outages") or []
    tickets: list[dict[str, Any]] = []

    for row in rows:
        ticket_id = row.get("ticket_id", "")
        ticket = get_json(base_url, f"/api/tickets/{urllib.parse.quote(ticket_id)}")
        account_id = row.get("account_id") or (ticket or {}).get("account_id", "")
        account = get_first(
            base_url,
            [
                f"/api/accounts/{urllib.parse.quote(account_id)}",
                f"/api/customers/{urllib.parse.quote(account_id)}",
            ],
        )
        diagnostics = get_json(base_url, f"/api/diagnostics/{urllib.parse.quote(ticket_id)}")
        troubleshooting = get_json(base_url, f"/api/troubleshooting/{urllib.parse.quote(ticket_id)}")
        matching_outages = []
        if ticket:
            matching_outages = [
                outage
                for outage in outages
                if outage.get("active") is True
                and outage.get("service_area") == ticket.get("service_area")
                and ticket.get("service_type") in outage.get("service_types", [])
            ]
        tickets.append(
            {
                "source_row": row,
                "ticket": ticket,
                "account": account,
                "matching_active_outages": matching_outages,
                "diagnostics": diagnostics,
                "troubleshooting": troubleshooting,
            }
        )

    return {"tickets": tickets, "outages_count": len(outages)}


def collect_case_evidence(base_url: str, payloads: dict[str, Any]) -> dict[str, Any]:
    source = payloads.get("case_queue.json") or payloads.get("mobile_data_worklist.json") or {}
    input_cases = source.get("cases", [])
    bills = get_json(base_url, "/api/bills") or []
    bills_by_customer: dict[str, list[dict[str, Any]]] = {}
    for bill in bills:
        bills_by_customer.setdefault(bill.get("customer_id", ""), []).append(bill)

    cases: list[dict[str, Any]] = []
    for item in input_cases:
        case_id = item.get("case_id", "")
        case = get_first(
            base_url,
            [
                f"/api/cases/{urllib.parse.quote(case_id)}",
                f"/api/contact-center/cases/{urllib.parse.quote(case_id)}",
            ],
        )
        line = device = customer = plan = None
        related_bills: list[dict[str, Any]] = []
        if case:
            line_id = case.get("line_id", "")
            device_id = case.get("device_id", "")
            customer_id = case.get("customer_id", "")
            line = get_json(base_url, f"/api/lines/{urllib.parse.quote(line_id)}") if line_id else None
            device = get_json(base_url, f"/api/devices/{urllib.parse.quote(device_id)}") if device_id else None
            customer = get_json(base_url, f"/api/customers/{urllib.parse.quote(customer_id)}") if customer_id else None
            plan_id = (line or {}).get("plan_id", "")
            plan = get_json(base_url, f"/api/plans/{urllib.parse.quote(plan_id)}") if plan_id else None
            related_bills = bills_by_customer.get(customer_id, [])
        cases.append(
            {
                "source_case": item,
                "case": case,
                "customer": customer,
                "line": line,
                "device": device,
                "plan": plan,
                "bills": related_bills,
                "customer_preferences": source.get("customer_preferences", {}).get(case_id, {}),
            }
        )

    return {"cases": cases}


def compact_client_terms(text: str) -> list[str]:
    terms: list[str] = []
    client_match = re.search(r"(?im)^Client:\s*(.+?)\s*$", text)
    if client_match:
        terms.append(client_match.group(1).strip())
    incident_matches = re.findall(r"\bINC-\d+\b", text)
    terms.extend(incident_matches)
    subject_match = re.search(r"(?im)^Subject:\s*(.+?)\s*$", text)
    if subject_match:
        for word in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", subject_match.group(1)):
            if word.lower() not in {"critical", "failed", "three", "days"}:
                terms.append(word)
                break
    return list(dict.fromkeys(terms))


def collect_enterprise_evidence(base_url: str, payloads: dict[str, Any]) -> dict[str, Any]:
    complaint = payloads.get("client_complaint_email.txt", "")
    requirements = payloads.get("response_requirements.json", {})
    terms = compact_client_terms(complaint)
    search_results: list[dict[str, Any]] = []
    for term in terms:
        encoded = urllib.parse.urlencode({"q": term})
        result = get_json(base_url, f"/api/search?{encoded}")
        if isinstance(result, dict):
            search_results.extend(result.get("results", []))

    incident_id = ""
    incident_match = re.search(r"\bINC-\d+\b", complaint)
    if incident_match:
        incident_id = incident_match.group(0)
    if not incident_id:
        for result in search_results:
            record = result.get("record", {})
            if record.get("incident_id"):
                incident_id = record["incident_id"]
                break

    incident = None
    if incident_id:
        incident = get_json(base_url, f"/api/enterprise/incidents/{urllib.parse.quote(incident_id)}")

    enterprise_account_id = (incident or {}).get("enterprise_account_id", "")
    account = None
    sla = None
    if enterprise_account_id:
        account = get_json(
            base_url,
            f"/api/enterprise/accounts/{urllib.parse.quote(enterprise_account_id)}",
        )
        sla = get_json(base_url, f"/api/enterprise/sla/{urllib.parse.quote(enterprise_account_id)}")

    export_runs = get_json(base_url, "/api/enterprise/export-runs") or []
    messages = get_json(base_url, "/api/enterprise/messages") or []

    def relevant(record: dict[str, Any]) -> bool:
        if incident_id and record.get("incident_id") == incident_id:
            return True
        if enterprise_account_id and record.get("enterprise_account_id") == enterprise_account_id:
            return True
        return False

    relevant_runs = [run for run in export_runs if relevant(run)]
    term_text = " ".join(terms).lower()
    name = (account or {}).get("name", "")
    message_terms = [term.lower() for term in terms if term] + [part.lower() for part in name.split() if len(part) > 2]
    relevant_messages = [
        message
        for message in messages
        if any(term and term in (message.get("body", "") + " " + message.get("channel", "")).lower() for term in message_terms)
        or (term_text and term_text in (message.get("body", "") + " " + message.get("channel", "")).lower())
    ]

    return {
        "complaint_terms": terms,
        "requirements": requirements,
        "search_results": search_results,
        "incident": incident,
        "enterprise_account": account,
        "sla_contract": sla,
        "export_runs": sorted(relevant_runs, key=lambda item: item.get("run_date", "")),
        "messages": sorted(relevant_messages, key=lambda item: item.get("created_at", "")),
    }


def load_payloads(payload_dir: Path) -> dict[str, Any]:
    payloads: dict[str, Any] = {}
    for path in sorted(payload_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix == ".json":
            payloads[path.name] = read_json(path)
        elif path.suffix == ".csv":
            payloads[path.name] = read_csv_rows(path)
        else:
            payloads[path.name] = read_text(path)
    return payloads


def detect_modes(payloads: dict[str, Any]) -> list[str]:
    modes: list[str] = []
    if "ticket_batch.csv" in payloads or "queue_snapshot.csv" in payloads:
        modes.append("fixed_service_tickets")
    if "case_queue.json" in payloads or "mobile_data_worklist.json" in payloads:
        modes.append("mobile_or_contact_center_cases")
    if "client_complaint_email.txt" in payloads or "response_requirements.json" in payloads:
        modes.append("enterprise_export_response")
    return modes


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect support-console records for local task payloads.")
    parser.add_argument("payload_dir", help="Path to the task payloads directory.")
    parser.add_argument("--base-url", default=os.environ.get("TASK_ENV_BASE_URL", ""))
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    if not args.base_url:
        parser.error("Provide --base-url or set TASK_ENV_BASE_URL.")

    payload_dir = Path(args.payload_dir)
    if not payload_dir.is_dir():
        parser.error(f"payload_dir is not a directory: {payload_dir}")

    payloads = load_payloads(payload_dir)
    modes = detect_modes(payloads)
    evidence: dict[str, Any] = {
        "payload_dir": str(payload_dir),
        "payload_files": sorted(payloads),
        "modes": modes,
        "records": {},
    }

    if "fixed_service_tickets" in modes:
        evidence["records"]["fixed_service_tickets"] = collect_ticket_evidence(args.base_url, payloads)
    if "mobile_or_contact_center_cases" in modes:
        evidence["records"]["mobile_or_contact_center_cases"] = collect_case_evidence(args.base_url, payloads)
    if "enterprise_export_response" in modes:
        evidence["records"]["enterprise_export_response"] = collect_enterprise_evidence(args.base_url, payloads)

    output_text = json.dumps(evidence, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(output_text + "\n", encoding="utf-8")
    else:
        print(output_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
