#!/usr/bin/env python3
"""
Filter correspondence records for stale/unverified items.

Reads a JSON array of correspondence objects from stdin. Each object should have
at least an "id" field and a "status" field. Outputs a sorted, deduplicated list
of IDs whose status indicates they are stale, unverified, unconfirmed, or pending.

Usage:
    cat correspondence.json | python3 correspondence_filter.py
    curl -s $BASE/api/contractor/correspondence | python3 correspondence_filter.py
"""

import json
import sys

STALE_STATUSES = {
    "stale",
    "unverified",
    "unconfirmed",
    "pending",
    "open",
    "awaiting_response",
    "outstanding",
}


def is_stale(record):
    status = (record.get("status") or "").strip().lower()
    return status in STALE_STATUSES


def main():
    data = json.load(sys.stdin)

    if isinstance(data, dict):
        records = data.get("correspondence", data.get("records", data.get("items", [])))
        if not isinstance(records, list):
            records = [data]
    elif isinstance(data, list):
        records = data
    else:
        records = [data]

    stale_ids = sorted(
        {record["id"] for record in records if is_stale(record) and "id" in record}
    )

    json.dump(stale_ids, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
