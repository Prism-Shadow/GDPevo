#!/usr/bin/env python3
"""Fetch a HarborCRM task snapshot with only stdlib dependencies.

The script is intentionally permissive about optional endpoints: it records
404s as missing so the solver can still use task-specific endpoint lists from
the prompt.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen


def get_json(base_url: str, path: str) -> tuple[Any | None, str | None]:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=20) as response:
            return json.load(response), None
    except HTTPError as exc:
        if exc.code == 404:
            return None, "404"
        return None, f"HTTP {exc.code}: {exc.reason}"
    except (URLError, TimeoutError) as exc:
        return None, str(exc)


def add(snapshot: dict[str, Any], base_url: str, key: str, path: str) -> None:
    data, error = get_json(base_url, path)
    if error is None:
        snapshot["data"][key] = data
        snapshot["fetched"][key] = path
    else:
        snapshot["missing"][key] = {"path": path, "error": error}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task API base URL")
    parser.add_argument("--event-id", help="Event identifier from the prompt")
    parser.add_argument("--show-id", help="Trade-show identifier from the prompt")
    parser.add_argument("--batch-id", help="Import batch identifier from the prompt")
    parser.add_argument("--out", help="Write snapshot JSON to this path")
    parser.add_argument(
        "--skip-crm",
        action="store_true",
        help="Do not fetch shared CRM and policy endpoints",
    )
    args = parser.parse_args()

    snapshot: dict[str, Any] = {"fetched": {}, "missing": {}, "data": {}}
    base_url = args.base_url

    if args.event_id:
        event_id = quote(args.event_id, safe="")
        add(snapshot, base_url, "events", "/api/events")
        add(snapshot, base_url, "event", f"/api/events/{event_id}")
        add(snapshot, base_url, "event_badges", f"/api/events/{event_id}/badges")
        add(snapshot, base_url, "event_sponsors", f"/api/events/{event_id}/sponsors")
        add(snapshot, base_url, "event_orders", f"/api/events/{event_id}/orders")
        add(
            snapshot,
            base_url,
            "event_sponsor_packages",
            f"/api/events/{event_id}/sponsor_packages",
        )
        add(
            snapshot,
            base_url,
            "event_invoices",
            f"/api/finance/invoices?event_id={event_id}",
        )

    if args.show_id:
        show_id = quote(args.show_id, safe="")
        add(snapshot, base_url, "tradeshows", "/api/tradeshows")
        add(snapshot, base_url, "tradeshow", f"/api/tradeshows/{show_id}")
        add(snapshot, base_url, "exhibitors", f"/api/tradeshows/{show_id}/exhibitors")
        add(
            snapshot,
            base_url,
            "meeting_interest",
            f"/api/tradeshows/{show_id}/meeting_interest",
        )

    if args.batch_id:
        batch_id = quote(args.batch_id, safe="")
        add(snapshot, base_url, "import_batches", "/api/import_batches")
        add(snapshot, base_url, "import_batch", f"/api/import_batches/{batch_id}")
        add(
            snapshot,
            base_url,
            "raw_contacts",
            f"/api/import_batches/{batch_id}/raw_contacts",
        )
        add(
            snapshot,
            base_url,
            "suppression",
            f"/api/import_batches/{batch_id}/suppression",
        )

    if not args.skip_crm:
        add(snapshot, base_url, "crm_accounts", "/api/crm/accounts")
        add(snapshot, base_url, "crm_contacts", "/api/crm/contacts")
        add(snapshot, base_url, "crm_opportunities", "/api/crm/opportunities")
        add(snapshot, base_url, "crm_campaign_members", "/api/crm/campaign_members")
        add(snapshot, base_url, "policies", "/api/policies")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
        print(str(out_path))
    else:
        json.dump(snapshot, sys.stdout, indent=2, sort_keys=True)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
