#!/usr/bin/env python3
"""Fetch ApexCloud retention facts from the task environment.

This helper is intentionally source-oriented. It gathers live account,
billing, A/R, ticket, NPS, and opportunity facts so a solver can derive the
requested JSON without hard-coding example outputs.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Any


def _get_json(url: str) -> Any:
    with urllib.request.urlopen(url) as resp:
        return json.load(resp)


def _get_text(url: str) -> str:
    with urllib.request.urlopen(url) as resp:
        return resp.read().decode("utf-8")


def _dt(value: str) -> date:
    return date.fromisoformat(value)


def _month(value: str) -> str:
    return value[:7]


def _clean_tickets(tickets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        t
        for t in tickets
        if not t.get("is_duplicate") and not t.get("is_spam") and t.get("status") != "cancelled"
    ]


def _safe_mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def _safe_pct(numer: int, denom: int) -> float:
    return round((numer / denom) * 100.0, 1) if denom else 0.0


@dataclass
class AccountFacts:
    account_id: str
    legal_name: str
    region: str
    segment: str
    renewal_date: str | None
    contract_tenure_months: int | None
    current_arr: float
    overdue_balance: float
    clean_ticket_count: int
    ticket_sla_pct: float
    latest_nps: int | None
    usage_first: float | None
    usage_last: float | None
    usage_delta: float | None
    open_expansion_pipeline: float
    reason_flags: list[str]


def build_facts(base_url: str, account_ids: list[str], as_of: str, start: str, end: str) -> dict[str, Any]:
    accounts_payload = _get_json(f"{base_url}/api/accounts")
    accounts = {a["account_id"]: a for a in accounts_payload.get("accounts", [])}

    billing_payload = _get_json(f"{base_url}/api/billing/snapshots?as_of={urllib.parse.quote(as_of)}")
    billing = {b["account_id"]: b for b in billing_payload.get("snapshots", []) if b.get("posted", True)}

    ar_payload = _get_json(f"{base_url}/api/finance/ar-aging?as_of={urllib.parse.quote(as_of)}")
    ar_rows = ar_payload.get("ar_aging", [])
    ar_by_account: dict[str, dict[str, Any]] = {}
    for aid, acc in accounts.items():
        legal = acc.get("legal_name")
        aliases = {legal, *acc.get("account_aliases", [])}
        for row in ar_rows:
            if row.get("customer_name") in aliases:
                ar_by_account[aid] = row
                break

    opp_payload = _get_json(f"{base_url}/api/opportunities?start={urllib.parse.quote(start)}&end={urllib.parse.quote(end)}")
    open_expansion: dict[str, float] = defaultdict(float)
    for opp in opp_payload.get("opportunities", []):
        if opp.get("state") == "open":
            open_expansion[opp["account_id"]] += float(opp.get("amount", 0.0))

    facts: list[AccountFacts] = []
    as_of_date = _dt(as_of)

    for aid in account_ids:
        acc = accounts.get(aid, {})
        metrics = _get_json(
            f"{base_url}/api/accounts/{aid}/metrics?start={urllib.parse.quote(start[:7])}&end={urllib.parse.quote(end[:7])}"
        ).get("metrics", [])
        tickets = _clean_tickets(
            _get_json(
                f"{base_url}/api/accounts/{aid}/tickets?start={urllib.parse.quote(start)}&end={urllib.parse.quote(end)}"
            ).get("tickets", [])
        )
        nps = [
            r
            for r in _get_json(
                f"{base_url}/api/accounts/{aid}/nps?start={urllib.parse.quote(start)}&end={urllib.parse.quote(end)}"
            ).get("nps_responses", [])
            if not r.get("retracted")
        ]

        current_arr = float(billing.get(aid, {}).get("billing_arr", acc.get("billing_arr_current", 0.0)) or 0.0)
        ar_row = ar_by_account.get(aid, {})
        overdue_balance = round(float(ar_row.get("61_90", 0.0)) + float(ar_row.get("90_plus", 0.0)), 2)

        ticket_sla_pct = _safe_pct(
            sum(1 for t in tickets if t.get("first_response_sla_met") and t.get("resolution_sla_met")),
            len(tickets),
        )
        latest_nps = None
        if nps:
            nps_sorted = sorted(nps, key=lambda r: r["response_date"])
            latest_nps = int(nps_sorted[-1]["score"])

        usage_first = usage_last = usage_delta = None
        if metrics:
            metrics_sorted = sorted(metrics, key=lambda r: r["month"])
            usage_first = float(metrics_sorted[0].get("product_usage", 0.0))
            usage_last = float(metrics_sorted[-1].get("product_usage", 0.0))
            usage_delta = round(usage_last - usage_first, 2)

        reason_flags: list[str] = []
        renewal_date = acc.get("renewal_date")
        if renewal_date and 0 <= (_dt(renewal_date) - as_of_date).days <= 90:
            reason_flags.append("renewal_window")
        if overdue_balance > 0:
            reason_flags.append("overdue_receivable")
        if latest_nps is not None and latest_nps < 50:
            reason_flags.append("nps_drop")
        if tickets and any(
            not t.get("first_response_sla_met") or not t.get("resolution_sla_met") for t in tickets
        ):
            reason_flags.append("sla_degradation")
        if usage_delta is not None and usage_delta < 0:
            reason_flags.append("usage_decline")
        if (acc.get("contract_tenure_months") or 0) <= 18:
            reason_flags.append("low_tenure_high_churn")
        if open_expansion.get(aid, 0.0) > 0:
            reason_flags.append("expansion_offset")
        if overdue_balance == 0:
            reason_flags.append("clean_billings")

        facts.append(
            AccountFacts(
                account_id=aid,
                legal_name=acc.get("legal_name", ""),
                region=acc.get("region", ""),
                segment=acc.get("segment", ""),
                renewal_date=renewal_date,
                contract_tenure_months=acc.get("contract_tenure_months"),
                current_arr=current_arr,
                overdue_balance=overdue_balance,
                clean_ticket_count=len(tickets),
                ticket_sla_pct=ticket_sla_pct,
                latest_nps=latest_nps,
                usage_first=usage_first,
                usage_last=usage_last,
                usage_delta=usage_delta,
                open_expansion_pipeline=round(float(open_expansion.get(aid, 0.0)), 2),
                reason_flags=reason_flags,
            )
        )

    return {
        "as_of": as_of,
        "window_start": start,
        "window_end": end,
        "accounts": [asdict(f) for f in facts],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--accounts", required=True, help="Comma-separated account IDs")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()

    payload = build_facts(
        base_url=args.base_url.rstrip("/"),
        account_ids=[x for x in args.accounts.split(",") if x],
        as_of=args.as_of,
        start=args.start,
        end=args.end,
    )
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
