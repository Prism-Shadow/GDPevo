#!/usr/bin/env python3
"""Fetch grouped evidence from the support-console API."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


def fetch_json(base_url: str, path: str):
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"_error": f"HTTP {exc.code}", "_path": path}
    except urllib.error.URLError as exc:
        return {"_error": str(exc.reason), "_path": path}


def list_records(base_url: str, path: str):
    data = fetch_json(base_url, path)
    return data if isinstance(data, list) else []


def by_id(records, key, value):
    for record in records:
        if isinstance(record, dict) and record.get(key) == value:
            return record
    return None


def first_working(base_url: str, paths: list[str]):
    for path in paths:
        data = fetch_json(base_url, path)
        if not (isinstance(data, dict) and data.get("_error")):
            return data
    return data


def ticket_bundle(base_url: str, ticket_id: str):
    ticket = fetch_json(base_url, f"/api/tickets/{ticket_id}")
    account_id = ticket.get("account_id") if isinstance(ticket, dict) else None
    account = fetch_json(base_url, f"/api/accounts/{account_id}") if account_id else None
    outages = list_records(base_url, "/api/outages")
    matching_outages = []
    if isinstance(ticket, dict):
        for outage in outages:
            if not isinstance(outage, dict) or not outage.get("active"):
                continue
            if outage.get("service_area") != ticket.get("service_area"):
                continue
            if ticket.get("service_type") in outage.get("service_types", []):
                matching_outages.append(outage)
    return {
        "ticket": ticket,
        "account": account,
        "matching_active_outages": matching_outages,
        "diagnostics": fetch_json(base_url, f"/api/diagnostics/{ticket_id}"),
        "troubleshooting": fetch_json(base_url, f"/api/troubleshooting/{ticket_id}"),
    }


def case_bundle(base_url: str, case_id: str):
    case = first_working(
        base_url,
        [f"/api/cases/{case_id}", f"/api/contact-center/cases/{case_id}"],
    )
    customer_id = case.get("customer_id") if isinstance(case, dict) else None
    line_id = case.get("line_id") if isinstance(case, dict) else None
    device_id = case.get("device_id") if isinstance(case, dict) else None
    line = fetch_json(base_url, f"/api/lines/{line_id}") if line_id else None
    if isinstance(line, dict):
        device_id = device_id or line.get("device_id")
        plan_id = line.get("plan_id")
    else:
        plan_id = None
    bills = [
        bill
        for bill in list_records(base_url, "/api/bills")
        if isinstance(bill, dict) and bill.get("customer_id") == customer_id
    ]
    return {
        "case": case,
        "customer": fetch_json(base_url, f"/api/customers/{customer_id}") if customer_id else None,
        "line": line,
        "device": fetch_json(base_url, f"/api/devices/{device_id}") if device_id else None,
        "plan": fetch_json(base_url, f"/api/plans/{plan_id}") if plan_id else None,
        "bills": bills,
    }


def enterprise_bundle(base_url: str, incident_id: str):
    incident = fetch_json(base_url, f"/api/enterprise/incidents/{incident_id}")
    if isinstance(incident, dict) and incident.get("_error"):
        incident = by_id(
            list_records(base_url, "/api/enterprise/incidents"),
            "incident_id",
            incident_id,
        ) or incident
    account_id = incident.get("enterprise_account_id") if isinstance(incident, dict) else None
    account = (
        fetch_json(base_url, f"/api/enterprise/accounts/{account_id}")
        if account_id
        else None
    )
    export_runs = [
        run
        for run in list_records(base_url, "/api/enterprise/export-runs")
        if isinstance(run, dict)
        and (
            run.get("incident_id") == incident_id
            or (account_id and run.get("enterprise_account_id") == account_id)
        )
    ]
    messages = list_records(base_url, "/api/enterprise/messages")
    terms = {
        str(value).lower()
        for value in [
            incident_id,
            incident.get("product") if isinstance(incident, dict) else None,
            incident.get("summary") if isinstance(incident, dict) else None,
            account.get("name") if isinstance(account, dict) else None,
        ]
        if value
    }
    relevant_messages = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        haystack = " ".join(str(v).lower() for v in message.values())
        if any(term and term in haystack for term in terms):
            relevant_messages.append(message)
    return {
        "incident": incident,
        "enterprise_account": account,
        "sla": fetch_json(base_url, f"/api/enterprise/sla/{account_id}") if account_id else None,
        "export_runs": export_runs,
        "messages": relevant_messages or messages,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--tickets", nargs="*", default=[])
    parser.add_argument("--cases", nargs="*", default=[])
    parser.add_argument("--enterprise-incidents", nargs="*", default=[])
    parser.add_argument("--search", nargs="*", default=[])
    args = parser.parse_args()

    output = {
        "health": fetch_json(args.base_url, "/health"),
        "catalog": fetch_json(args.base_url, "/api/catalog"),
    }
    if args.search:
        output["search"] = {
            query: fetch_json(args.base_url, "/api/search?" + urllib.parse.urlencode({"q": query}))
            for query in args.search
        }
    if args.tickets:
        output["tickets"] = {
            ticket_id: ticket_bundle(args.base_url, ticket_id) for ticket_id in args.tickets
        }
    if args.cases:
        output["cases"] = {
            case_id: case_bundle(args.base_url, case_id) for case_id in args.cases
        }
    if args.enterprise_incidents:
        output["enterprise_incidents"] = {
            incident_id: enterprise_bundle(args.base_url, incident_id)
            for incident_id in args.enterprise_incidents
        }
    json.dump(output, sys.stdout, indent=2, sort_keys=True)
    print()


if __name__ == "__main__":
    main()
