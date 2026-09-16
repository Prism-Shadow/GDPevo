#!/usr/bin/env python3
"""Utilities for Court Operations Portal closeout packets."""

from __future__ import annotations

import argparse
import calendar
import datetime as dt
import json
import sys
import urllib.parse
import urllib.request
from decimal import Decimal, ROUND_HALF_UP


ALLOWED_ENDPOINTS = {
    "jurisdictions",
    "cases",
    "charges",
    "docket-entries",
    "citations",
    "fee-schedules",
    "payment-policies",
    "forms",
    "financial-petitions",
    "search",
}


def parse_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected ISO date YYYY-MM-DD, got {value!r}") from exc


def add_months(date_value: dt.date, months: int) -> dt.date:
    month_index = date_value.month - 1 + months
    year = date_value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(date_value.day, calendar.monthrange(year, month)[1])
    return dt.date(year, month, day)


def cents(value: str) -> int:
    amount = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(amount * 100)


def money(cents_value: int) -> float:
    amount = (Decimal(cents_value) / Decimal(100)).quantize(Decimal("0.01"))
    return float(amount)


def installment_schedule(total: str, amount: str, down: str, first: dt.date, return_offset_days: int | None) -> dict:
    total_cents = cents(total)
    amount_cents = cents(amount)
    down_cents = cents(down)
    if amount_cents <= 0:
        raise ValueError("installment amount must be greater than zero")
    balance_cents = max(total_cents - down_cents, 0)
    if balance_cents == 0:
        result = {
            "balance_after_down_payment": money(balance_cents),
            "regular_installment_amount": money(amount_cents),
            "total_installments": 0,
            "payment_count": 0,
            "full_installment_count": 0,
            "full_payment_count": 0,
            "final_payment_amount": 0.0,
            "first_due_date": first.isoformat(),
            "final_due_date": None,
        }
    else:
        full_count, remainder = divmod(balance_cents, amount_cents)
        if remainder:
            total_installments = full_count + 1
            final_payment_cents = remainder
        else:
            total_installments = full_count
            final_payment_cents = amount_cents
        final_due = add_months(first, total_installments - 1)
        result = {
            "balance_after_down_payment": money(balance_cents),
            "regular_installment_amount": money(amount_cents),
            "total_installments": total_installments,
            "payment_count": total_installments,
            "full_installment_count": full_count if remainder else total_installments,
            "full_payment_count": full_count if remainder else total_installments,
            "final_payment_amount": money(final_payment_cents),
            "first_due_date": first.isoformat(),
            "final_due_date": final_due.isoformat(),
        }
    if return_offset_days is not None and result["final_due_date"] is not None:
        final_due_date = parse_date(result["final_due_date"])
        result["return_to_court_date"] = (final_due_date + dt.timedelta(days=return_offset_days)).isoformat()
    return result


def normalize_endpoint(endpoint: str) -> str:
    endpoint = endpoint.strip().lstrip("/")
    if endpoint.startswith("api/"):
        endpoint = endpoint[4:]
    if endpoint not in ALLOWED_ENDPOINTS:
        allowed = ", ".join(sorted(ALLOWED_ENDPOINTS))
        raise ValueError(f"endpoint {endpoint!r} is not allowed; use one of: {allowed}")
    return endpoint


def parse_param(values: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"--param value must be KEY=VALUE, got {item!r}")
        key, value = item.split("=", 1)
        if not key:
            raise ValueError("--param key cannot be empty")
        params[key] = value
    return params


def query_portal(base_url: str, endpoint: str, params: dict[str, str]) -> dict:
    endpoint = normalize_endpoint(endpoint)
    base = base_url.rstrip("/") + "/"
    url = urllib.parse.urljoin(base, f"api/{endpoint}")
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=20) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def command_installments(args: argparse.Namespace) -> None:
    result = installment_schedule(args.total, args.amount, args.down, args.first, args.return_offset_days)
    print(json.dumps(result, indent=2, sort_keys=True))


def command_add_months(args: argparse.Namespace) -> None:
    result = add_months(args.date, args.months)
    print(result.isoformat())


def command_query(args: argparse.Namespace) -> None:
    params = parse_param(args.param)
    result = query_portal(args.base_url, args.endpoint, params)
    print(json.dumps(result, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Court packet math and portal helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    query = subparsers.add_parser("query", help="Query an allowed Court Operations Portal endpoint")
    query.add_argument("--base-url", required=True, help="Portal base URL")
    query.add_argument("--endpoint", required=True, help="Endpoint name, with or without /api/")
    query.add_argument("--param", action="append", default=[], help="Query parameter as KEY=VALUE")
    query.set_defaults(func=command_query)

    installments = subparsers.add_parser("installments", help="Compute monthly installment schedule values")
    installments.add_argument("--total", required=True, help="Total due before down payment")
    installments.add_argument("--amount", required=True, help="Regular installment amount")
    installments.add_argument("--down", default="0", help="Down payment amount")
    installments.add_argument("--first", required=True, type=parse_date, help="First due date YYYY-MM-DD")
    installments.add_argument("--return-offset-days", type=int, default=None, help="Days after final due date")
    installments.set_defaults(func=command_installments)

    add_months_cmd = subparsers.add_parser("add-months", help="Add calendar months to an ISO date")
    add_months_cmd.add_argument("--date", required=True, type=parse_date, help="Start date YYYY-MM-DD")
    add_months_cmd.add_argument("--months", required=True, type=int, help="Calendar months to add")
    add_months_cmd.set_defaults(func=command_add_months)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except Exception as exc:  # noqa: BLE001 - CLI should print concise failure.
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
