#!/usr/bin/env python3
"""Small Cedar Ridge portal fetch helper.

This script intentionally fetches only caller-specified records. It is useful
for formatting REST and SQL responses while solving Cedar Ridge intake tasks.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request


def _base_url(value: str | None) -> str:
    base = value or os.environ.get("TASK_ENV_BASE_URL") or os.environ.get("CEDAR_BASE_URL")
    if not base:
        raise SystemExit("Provide --base-url or set TASK_ENV_BASE_URL.")
    return base.rstrip("/") + "/"


def _get(base: str, path: str) -> object:
    url = urllib.parse.urljoin(base, path.lstrip("/"))
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(base: str, path: str, payload: object) -> object:
    url = urllib.parse.urljoin(base, path.lstrip("/"))
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _print_json(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Fetch scoped Cedar Ridge portal data.")
    parser.add_argument("--base-url", help="Task environment base URL.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    patient = subparsers.add_parser("patient", help="GET /patients/{patient_id}")
    patient.add_argument("patient_id")

    chart = subparsers.add_parser("chart", help="GET /chart/{patient_id}")
    chart.add_argument("patient_id")

    referrals = subparsers.add_parser("referrals", help="GET /referrals?batch_id=...")
    referrals.add_argument("batch_id")

    referral = subparsers.add_parser("referral", help="GET /referrals/{referral_id}")
    referral.add_argument("referral_id")

    transfers = subparsers.add_parser("transfers", help="GET /transfers?batch_id=...")
    transfers.add_argument("batch_id")

    transfer = subparsers.add_parser("transfer", help="GET /transfers/{transfer_id}")
    transfer.add_argument("transfer_id")

    program = subparsers.add_parser("program", help="GET /programs/{program_code}/candidates")
    program.add_argument("program_code")

    icd = subparsers.add_parser("icd", help="GET /icd/{code}")
    icd.add_argument("code")

    subparsers.add_parser("pharmacies", help="GET /pharmacies")
    subparsers.add_parser("documents", help="GET /documents")

    sql = subparsers.add_parser("sql", help="POST /query with a SQL string")
    sql.add_argument("sql")

    args = parser.parse_args(argv)
    base = _base_url(args.base_url)

    if args.command == "patient":
        result = _get(base, f"patients/{urllib.parse.quote(args.patient_id)}")
    elif args.command == "chart":
        result = _get(base, f"chart/{urllib.parse.quote(args.patient_id)}")
    elif args.command == "referrals":
        result = _get(base, "referrals?" + urllib.parse.urlencode({"batch_id": args.batch_id}))
    elif args.command == "referral":
        result = _get(base, f"referrals/{urllib.parse.quote(args.referral_id)}")
    elif args.command == "transfers":
        result = _get(base, "transfers?" + urllib.parse.urlencode({"batch_id": args.batch_id}))
    elif args.command == "transfer":
        result = _get(base, f"transfers/{urllib.parse.quote(args.transfer_id)}")
    elif args.command == "program":
        code = urllib.parse.quote(args.program_code)
        result = _get(base, f"programs/{code}/candidates")
    elif args.command == "icd":
        result = _get(base, f"icd/{urllib.parse.quote(args.code)}")
    elif args.command == "pharmacies":
        result = _get(base, "pharmacies")
    elif args.command == "documents":
        result = _get(base, "documents")
    elif args.command == "sql":
        result = _post_json(base, "query", {"sql": args.sql})
    else:
        parser.error(f"Unknown command: {args.command}")

    _print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
