#!/usr/bin/env python3
"""
Fetch all HarborCRM endpoints needed for a task in one invocation.

Usage:
    python3 fetch_api.py <base_url> <subject_type> <subject_id> [--outdir <dir>]

subject_type: event | tradeshow | import_batch

Writes one JSON file per endpoint to --outdir (default: ./api_data).
Prints a summary of what was fetched to stdout.
"""

import json
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

ENDPOINTS = {
    "event": [
        "/api/events/{id}",
        "/api/events/{id}/orders",
        "/api/events/{id}/badges",
        "/api/events/{id}/sponsor_packages",
        "/api/finance/invoices?event_id={id}",
        "/api/crm/accounts",
        "/api/crm/contacts",
        "/api/crm/opportunities?event_id={id}",
        "/api/crm/campaign_members?event_id={id}",
        "/api/policies",
    ],
    "tradeshow": [
        "/api/tradeshows/{id}",
        "/api/tradeshows/{id}/exhibitors",
        "/api/tradeshows/{id}/meeting_interest",
        "/api/crm/accounts",
        "/api/crm/contacts",
        "/api/policies",
    ],
    "import_batch": [
        "/api/import_batches/{id}",
        "/api/import_batches/{id}/raw_contacts",
        "/api/import_batches/{id}/suppression",
        "/api/crm/accounts",
        "/api/crm/contacts",
        "/api/policies",
    ],
}


def safe_name(path):
    return path.replace("/", "_").replace("?", "_").replace("=", "_").strip("_")


def fetch(base_url, subject_type, subject_id, outdir):
    paths = ENDPOINTS.get(subject_type)
    if not paths:
        print(f"ERROR: unknown subject_type '{subject_type}'")
        sys.exit(1)

    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    results = {}
    for path in paths:
        url = base_url.rstrip("/") + path.format(id=subject_id)
        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except URLError as e:
            print(f"WARN: fetch failed for {url}: {e}")
            data = None
        except json.JSONDecodeError as e:
            print(f"WARN: invalid JSON from {url}: {e}")
            data = None

        fname = safe_name(path) + ".json"
        outfile = outdir / fname
        with open(outfile, "w") as f:
            json.dump(data, f, indent=2, default=str)
        results[path] = str(outfile)
        print(f"  {path} -> {outfile}")

    print(f"\nFetched {len(results)} endpoints to {outdir}")
    return results


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: fetch_api.py <base_url> <subject_type> <subject_id> [--outdir <dir>]")
        sys.exit(1)

    base_url = sys.argv[1]
    subject_type = sys.argv[2]
    subject_id = sys.argv[3]
    outdir = "api_data"

    if len(sys.argv) > 4 and sys.argv[4] == "--outdir":
        outdir = sys.argv[5]

    fetch(base_url, subject_type, subject_id, outdir)
