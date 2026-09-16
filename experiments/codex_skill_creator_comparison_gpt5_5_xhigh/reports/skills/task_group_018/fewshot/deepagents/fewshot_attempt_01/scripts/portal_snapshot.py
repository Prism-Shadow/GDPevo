#!/usr/bin/env python3
"""Collect targeted Court Operations Portal records for closeout tasks.

The script intentionally requires explicit identifiers. It does not enumerate
all portal data.
"""

from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


def fetch(base_url: str, endpoint: str, params: dict[str, str]) -> dict:
    base = base_url.rstrip("/")
    url = f"{base}{endpoint}?{urlencode(params)}"
    try:
        with urlopen(url, timeout=20) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        return {"error": f"HTTP {exc.code}", "url": url}
    except URLError as exc:
        return {"error": str(exc.reason), "url": url}
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {"error": "non-json response", "url": url, "body": payload}
    return {"url": url, "data": data}


def add_request(out: dict, label: str, base_url: str, endpoint: str, params: dict[str, str]) -> None:
    out.setdefault(label, []).append(fetch(base_url, endpoint, params))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Portal base URL from the task prompt")
    parser.add_argument("--case", action="append", default=[], help="Case number to fetch")
    parser.add_argument("--citation", action="append", default=[], help="Citation number to fetch")
    parser.add_argument("--petition", action="append", default=[], help="Financial petition ID to fetch")
    parser.add_argument("--jurisdiction", action="append", default=[], help="Jurisdiction code to fetch")
    parser.add_argument("--out", help="Write JSON snapshot to this path instead of stdout")
    args = parser.parse_args()

    if not any([args.case, args.citation, args.petition, args.jurisdiction]):
        parser.error("provide at least one --case, --citation, --petition, or --jurisdiction")

    snapshot: dict[str, list[dict]] = {}

    for case_number in args.case:
        add_request(snapshot, "search", args.base_url, "/api/search", {"q": case_number})
        add_request(snapshot, "cases", args.base_url, "/api/cases", {"case_number": case_number})
        add_request(snapshot, "charges", args.base_url, "/api/charges", {"case_number": case_number})
        add_request(snapshot, "docket_entries", args.base_url, "/api/docket-entries", {"case_number": case_number})
        add_request(snapshot, "financial_petitions_by_case", args.base_url, "/api/financial-petitions", {"case_number": case_number})

    for citation_number in args.citation:
        add_request(snapshot, "citations", args.base_url, "/api/citations", {"citation_number": citation_number})
        add_request(snapshot, "search", args.base_url, "/api/search", {"q": citation_number})

    for petition_id in args.petition:
        add_request(snapshot, "financial_petitions", args.base_url, "/api/financial-petitions", {"petition_id": petition_id})
        add_request(snapshot, "search", args.base_url, "/api/search", {"q": petition_id})

    for jurisdiction_code in args.jurisdiction:
        params = {"jurisdiction_code": jurisdiction_code}
        add_request(snapshot, "jurisdictions", args.base_url, "/api/jurisdictions", params)
        add_request(snapshot, "fee_schedules", args.base_url, "/api/fee-schedules", params)
        add_request(snapshot, "payment_policies", args.base_url, "/api/payment-policies", params)
        add_request(snapshot, "forms", args.base_url, "/api/forms", params)

    text = json.dumps(snapshot, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.write("\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
