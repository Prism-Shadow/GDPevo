#!/usr/bin/env python3
"""Collect filtered Court Operations Portal records for closeout tasks."""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


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


def fetch_json(base_url, endpoint_key, params=None):
    path = ENDPOINTS[endpoint_key]
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    if params:
        url = f"{url}?{urlencode(params)}"

    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        return url, json.load(response)


def collect(base_url, args):
    records = []
    derived_jurisdictions = set(args.jurisdiction)

    def add(endpoint_key, params=None):
        try:
            url, response = fetch_json(base_url, endpoint_key, params)
            records.append(
                {
                    "endpoint": ENDPOINTS[endpoint_key],
                    "params": params or {},
                    "url": url,
                    "response": response,
                }
            )
            for item in response.get("results", []):
                code = item.get("jurisdiction_code")
                if code:
                    derived_jurisdictions.add(code)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            records.append(
                {
                    "endpoint": ENDPOINTS[endpoint_key],
                    "params": params or {},
                    "error": str(exc),
                }
            )

    for case_number in args.case:
        params = {"case_number": case_number}
        add("cases", params)
        add("charges", params)
        add("docket_entries", params)
        add("search", {"q": case_number})

    for citation_number in args.citation:
        add("citations", {"citation_number": citation_number})
        add("search", {"q": citation_number})

    for petition_id in args.petition:
        add("financial_petitions", {"petition_id": petition_id})
        add("search", {"q": petition_id})

    for jurisdiction_code in sorted(derived_jurisdictions):
        params = {"jurisdiction_code": jurisdiction_code}
        add("jurisdictions", params)
        add("fee_schedules", params)
        add("payment_policies", params)
        add("forms", params)

    return {
        "queries": {
            "cases": args.case,
            "citations": args.citation,
            "petitions": args.petition,
            "jurisdictions": sorted(derived_jurisdictions),
        },
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Court Operations Portal evidence by identifier."
    )
    parser.add_argument("--base-url", required=True, help="Portal base URL")
    parser.add_argument("--case", action="append", default=[], help="Case number")
    parser.add_argument(
        "--citation", action="append", default=[], help="Citation number"
    )
    parser.add_argument("--petition", action="append", default=[], help="Petition ID")
    parser.add_argument(
        "--jurisdiction", action="append", default=[], help="Jurisdiction code"
    )
    args = parser.parse_args()

    if not (args.case or args.citation or args.petition or args.jurisdiction):
        parser.error("provide at least one --case, --citation, --petition, or --jurisdiction")

    json.dump(collect(args.base_url, args), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
