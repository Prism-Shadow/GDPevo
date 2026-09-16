#!/usr/bin/env python3
"""Collect targeted Court Operations Portal records for closeout tasks."""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


ENDPOINTS = {
    "jurisdictions": "/api/jurisdictions",
    "cases": "/api/cases",
    "charges": "/api/charges",
    "docket_entries": "/api/docket-entries",
    "citations": "/api/citations",
    "fee_schedules": "/api/fee-schedules",
    "payment_policies": "/api/payment-policies",
    "forms": "/api/forms",
    "financial_petitions": "/api/financial-petitions",
    "search": "/api/search",
}


def unique(values):
    seen = set()
    out = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def fetch(base_url, endpoint_key, params=None):
    base = base_url.rstrip("/")
    query = urllib.parse.urlencode(params or {})
    url = f"{base}{ENDPOINTS[endpoint_key]}"
    if query:
        url = f"{url}?{query}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{url} returned HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{url} failed: {exc}") from exc


def collect(args):
    snapshot = {
        "cases": {},
        "charges": {},
        "docket_entries": {},
        "citations": {},
        "financial_petitions": {},
        "jurisdictions": {},
        "fee_schedules": {},
        "payment_policies": {},
        "forms": {},
        "search": {},
    }

    for case_number in unique(args.case):
        params = {"case_number": case_number}
        snapshot["cases"][case_number] = fetch(args.base_url, "cases", params)
        snapshot["charges"][case_number] = fetch(args.base_url, "charges", params)
        snapshot["docket_entries"][case_number] = fetch(args.base_url, "docket_entries", params)

    for citation_number in unique(args.citation):
        snapshot["citations"][citation_number] = fetch(
            args.base_url,
            "citations",
            {"citation_number": citation_number},
        )

    for petition_id in unique(args.petition):
        snapshot["financial_petitions"][petition_id] = fetch(
            args.base_url,
            "financial_petitions",
            {"petition_id": petition_id},
        )

    for jurisdiction_code in unique(args.jurisdiction):
        params = {"jurisdiction_code": jurisdiction_code}
        snapshot["jurisdictions"][jurisdiction_code] = fetch(args.base_url, "jurisdictions", params)
        snapshot["fee_schedules"][jurisdiction_code] = fetch(args.base_url, "fee_schedules", params)
        snapshot["payment_policies"][jurisdiction_code] = fetch(args.base_url, "payment_policies", params)
        snapshot["forms"][jurisdiction_code] = fetch(args.base_url, "forms", params)

    for query in unique(args.search):
        snapshot["search"][query] = fetch(args.base_url, "search", {"q": query})

    return snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument("--case", action="append", default=[], help="Case number to collect")
    parser.add_argument("--citation", action="append", default=[], help="Citation number to collect")
    parser.add_argument("--petition", action="append", default=[], help="Financial petition ID to collect")
    parser.add_argument("--jurisdiction", action="append", default=[], help="Jurisdiction code to collect")
    parser.add_argument("--search", action="append", default=[], help="Portal search query to run")
    args = parser.parse_args()

    try:
        print(json.dumps(collect(args), indent=2, sort_keys=True))
    except RuntimeError as exc:
        print(f"portal_collect.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
