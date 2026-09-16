#!/usr/bin/env python3
"""Helpers for court closeout reconciliation tasks.

The script is intentionally generic: it fetches JSON from a task portal and
computes recurring payment/date math. It does not encode task-specific records.
"""

from __future__ import annotations

import argparse
import calendar
import json
import sys
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


CENT = Decimal("0.01")


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO date: {value}") from exc


def money(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def json_money(value: Decimal) -> float:
    return float(value.quantize(CENT, rounding=ROUND_HALF_UP))


def add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(start.day, last_day))


def advance_date(start: date, interval: str, steps: int) -> date:
    if steps <= 0:
        return start
    if interval == "monthly":
        return add_months(start, steps)
    if interval == "weekly":
        return start + timedelta(days=7 * steps)
    if interval == "biweekly":
        return start + timedelta(days=14 * steps)
    raise ValueError(f"unsupported interval: {interval}")


def schedule(args: argparse.Namespace) -> dict[str, Any]:
    balance = money(args.balance)
    down_payment = money(args.down_payment)
    installment = money(args.installment)
    remaining = max(money(balance - down_payment), Decimal("0.00"))

    if remaining > 0 and installment <= 0:
        raise SystemExit("installment must be greater than zero when a balance remains")

    if remaining == 0:
        full_count = 0
        total = 0
        final_payment = Decimal("0.00")
        final_due = None
    else:
        full_count = int(remaining // installment)
        remainder = money(remaining - (installment * full_count))
        if remainder == 0:
            total = full_count
            final_payment = installment
        else:
            total = full_count + 1
            final_payment = remainder
        final_due = advance_date(args.first_date, args.interval, total - 1)

    return_to_court = None
    if final_due is not None and args.return_offset_days is not None:
        return_to_court = final_due + timedelta(days=args.return_offset_days)

    return {
        "balance": json_money(balance),
        "down_payment": json_money(down_payment),
        "balance_after_down_payment": json_money(remaining),
        "interval": args.interval,
        "first_due_date": args.first_date.isoformat(),
        "regular_installment_amount": json_money(installment),
        "full_installment_count": full_count,
        "total_installments": total,
        "payment_count": total,
        "final_payment_amount": json_money(final_payment),
        "final_due_date": final_due.isoformat() if final_due else None,
        "return_to_court_date": return_to_court.isoformat() if return_to_court else None,
    }


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/"


def endpoint_url(base_url: str, endpoint: str, query: str | None) -> str:
    endpoint = endpoint.strip("/")
    if endpoint.startswith("api/"):
        endpoint = endpoint[4:]
    url = normalize_base_url(base_url) + "api/" + endpoint
    if query is not None:
        url += "?" + urlencode({"q": query})
    return url


def read_url_json(url: str) -> Any:
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code} fetching {url}") from exc
    except URLError as exc:
        raise SystemExit(f"error fetching {url}: {exc.reason}") from exc


def result_records(payload: Any) -> list[Any]:
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return payload["results"]
    if isinstance(payload, list):
        return payload
    return [payload]


def matches_any_id(record: Any, ids: set[str], fields: list[str]) -> bool:
    if not isinstance(record, dict):
        return False
    for field in fields:
        value = record.get(field)
        if value is not None and str(value) in ids:
            return True
    return False


def fetch(args: argparse.Namespace) -> dict[str, Any]:
    query_values = args.query or []
    if args.endpoint.strip("/") == "search" and not query_values and args.ids:
        query_values = args.ids

    if query_values:
        combined: list[Any] = []
        for query in query_values:
            payload = read_url_json(endpoint_url(args.base_url, args.endpoint, query))
            for record in result_records(payload):
                if record not in combined:
                    combined.append(record)
        records = combined
        count = len(records)
    else:
        payload = read_url_json(endpoint_url(args.base_url, args.endpoint, None))
        records = result_records(payload)
        count = payload.get("count", len(records)) if isinstance(payload, dict) else len(records)

    if args.ids:
        wanted = {str(item) for item in args.ids}
        records = [record for record in records if matches_any_id(record, wanted, args.id_fields)]

    return {
        "endpoint": args.endpoint.strip("/"),
        "count": len(records),
        "source_count": count,
        "results": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch and optionally filter portal JSON")
    fetch_parser.add_argument("--base-url", required=True)
    fetch_parser.add_argument("--endpoint", required=True)
    fetch_parser.add_argument("--ids", nargs="*", default=[])
    fetch_parser.add_argument("--query", nargs="*", default=[])
    fetch_parser.add_argument(
        "--id-fields",
        nargs="*",
        default=[
            "case_number",
            "citation_number",
            "petition_id",
            "jurisdiction_code",
            "fee_id",
            "policy_id",
            "form_id",
        ],
    )
    fetch_parser.set_defaults(func=fetch)

    schedule_parser = subparsers.add_parser("schedule", help="Compute installment schedule math")
    schedule_parser.add_argument("--balance", required=True)
    schedule_parser.add_argument("--installment", required=True)
    schedule_parser.add_argument("--down-payment", default="0.00")
    schedule_parser.add_argument("--first-date", required=True, type=parse_date)
    schedule_parser.add_argument("--interval", choices=["monthly", "weekly", "biweekly"], default="monthly")
    schedule_parser.add_argument("--return-offset-days", type=int)
    schedule_parser.set_defaults(func=schedule)

    add_months_parser = subparsers.add_parser("add-months", help="Add calendar months to an ISO date")
    add_months_parser.add_argument("--date", required=True, type=parse_date)
    add_months_parser.add_argument("--months", required=True, type=int)
    add_months_parser.set_defaults(
        func=lambda args: {
            "date": args.date.isoformat(),
            "months": args.months,
            "result": add_months(args.date, args.months).isoformat(),
        }
    )

    args = parser.parse_args()
    print(json.dumps(args.func(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
