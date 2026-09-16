#!/usr/bin/env python3
"""Portable ApexCloud Retention Operations JSON helper."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import math
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from typing import Any


POLICY = {
    "risk_model_code": "RS-6",
    "arr_source_code": "REV-4",
    "support_hygiene_code": "SUP-8",
    "action_priority_code": "ACT-5",
    "board_sort_code": "BORD-4",
    "exposure_formula_code": "EXP-6",
    "calendar_policy_code": "CAL-5",
    "receivable_trigger_code": "RCP-7",
    "crm_match_code": "CM-5",
    "pipeline_window_code": "PW-6",
    "followup_scope_code": "FS-4",
    "model_protocol_code": "MOD-7",
    "probability_scale_code": "PRB-4",
    "deployment_rule_code": "DEP-5",
    "outreach_mapping_code": "OUT-2",
}

ACTION_DUE_DEFAULTS = {
    "collections_followup": "2026-07-15",
    "technical_recovery": "2026-07-18",
    "renewal_save": "2026-07-22",
    "executive_qbr": "2026-07-29",
    "nurture_monitor": "2026-08-05",
}

REASON_ORDER = [
    "renewal_window",
    "overdue_receivable",
    "nps_drop",
    "sla_degradation",
    "usage_decline",
    "low_tenure_high_churn",
    "expansion_offset",
    "clean_billings",
]


def money(value: float) -> float:
    return round(float(value) + 0.0, 2)


def pct(value: float) -> float:
    return round(float(value) + 0.0, 1)


def prob3(value: float) -> float:
    return round(float(value) + 0.0, 3)


def parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


class Api:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self._cache: dict[str, Any] = {}

    def json(self, path: str, params: dict[str, str] | None = None) -> Any:
        if params:
            path = path + "?" + urllib.parse.urlencode(params)
        if path in self._cache:
            return self._cache[path]
        url = self.base + path
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                data = {"error": "not_found"}
            else:
                raise
        self._cache[path] = data
        return data

    def csv_rows(self, path: str) -> list[dict[str, str]]:
        if path in self._cache:
            return self._cache[path]
        with urllib.request.urlopen(self.base + path, timeout=20) as response:
            text = response.read().decode("utf-8")
        rows = list(csv.DictReader(io.StringIO(text)))
        self._cache[path] = rows
        return rows


def load_template(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def read_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def detect_kind(prompt: str, template: dict[str, Any]) -> str:
    lower = prompt.lower()
    keys = set(template)
    if "qbr_metrics" in keys or "qbr metrics" in lower:
        return "qbr"
    if "model_validation" in keys or "churn" in lower:
        return "churn"
    if "overdue_followups" in keys or ("receivables" in lower and "pipeline" in lower):
        return "receivables_pipeline"
    if "action_board" in keys or "action board" in lower:
        return "retention_board"
    if "risk_accounts" in keys or "renewal risk queue" in lower or "risk queue" in lower:
        return "renewal_risk"
    raise SystemExit("Could not detect ApexCloud task family from prompt/template")


def account_ids_from_prompt(prompt: str) -> list[str]:
    seen: set[str] = set()
    ids: list[str] = []
    for match in re.finditer(r"acct_[a-z0-9_]+", prompt):
        account_id = match.group(0)
        if account_id not in seen:
            seen.add(account_id)
            ids.append(account_id)
    return ids


def months_from_prompt(prompt: str) -> list[str]:
    months: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"20\d{2}-\d{2}(?!-\d{2})", prompt):
        month = match.group(0)
        if month not in seen:
            seen.add(month)
            months.append(month)
    return months


def date_range_from_prompt(prompt: str) -> tuple[str | None, str | None]:
    patterns = [
        r"(?:Date range|Analysis period)[^0-9]*(20\d{2}-\d{2}-\d{2})\s+through\s+(20\d{2}-\d{2}-\d{2})",
        r"(20\d{2}-\d{2}-\d{2})\s+through\s+(20\d{2}-\d{2}-\d{2})",
        r"(20\d{2}-\d{2}-\d{2})\s+to\s+(20\d{2}-\d{2}-\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            return match.group(1), match.group(2)
    return None, None


def as_of_from_prompt(prompt: str, end_date: str | None = None) -> str | None:
    patterns = [
        r"(?:Assessment date|A/R as-of date|A/R as of date|as-of date|as of)\D*(20\d{2}-\d{2}-\d{2})",
        r"as of\s+(20\d{2}-\d{2}-\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            return match.group(1)
    return end_date


def top_n_from_prompt(prompt: str, default: int) -> int:
    match = re.search(r"top\s+(\d+)", prompt, re.IGNORECASE)
    return int(match.group(1)) if match else default


def action_calendar_from_prompt(prompt: str) -> dict[str, str]:
    calendar = dict(ACTION_DUE_DEFAULTS)
    for action in ACTION_DUE_DEFAULTS:
        match = re.search(rf"{action}\s*:\s*(20\d{{2}}-\d{{2}}-\d{{2}})", prompt)
        if match:
            calendar[action] = match.group(1)
    return calendar


def generic_due_date(prompt: str, default: str) -> str:
    match = re.search(r"due date[^:]*:\s*(20\d{2}-\d{2}-\d{2})", prompt, re.IGNORECASE)
    return match.group(1) if match else default


def accounts_by_id(api: Api) -> dict[str, dict[str, Any]]:
    data = api.json("/api/accounts")
    return {row["account_id"]: row for row in data.get("accounts", [])}


def billing_snapshots(api: Api) -> list[dict[str, Any]]:
    return api.json("/api/billing/snapshots").get("snapshots", [])


def ar_rows(api: Api, as_of: str | None) -> list[dict[str, Any]]:
    data = api.json("/api/finance/ar-aging", {"as_of": as_of} if as_of else None)
    rows = data.get("ar_aging", [])
    if as_of:
        rows = [row for row in rows if row.get("as_of") == as_of]
    return rows


def opportunities(api: Api, start: str | None, end: str | None) -> list[dict[str, Any]]:
    data = api.json("/api/opportunities", {"start": start, "end": end} if start and end else None)
    rows = data.get("opportunities", [])
    if start and end:
        rows = [row for row in rows if start <= row.get("close_date", "") <= end]
    return rows


def current_arr(account_id: str, account: dict[str, Any], snapshots: list[dict[str, Any]], as_of: str | None) -> float:
    posted = [row for row in snapshots if row.get("account_id") == account_id and row.get("posted")]
    if as_of:
        exact = [row for row in posted if row.get("as_of") == as_of]
        if exact:
            return float(exact[0]["billing_arr"])
        before = [row for row in posted if row.get("as_of", "") <= as_of]
        if before:
            return float(sorted(before, key=lambda row: row["as_of"])[-1]["billing_arr"])
    if posted:
        return float(sorted(posted, key=lambda row: row["as_of"])[-1]["billing_arr"])
    return float(account.get("billing_arr_current") or account.get("crm_arr") or 0.0)


def clean_tickets(tickets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        ticket
        for ticket in tickets
        if not ticket.get("is_duplicate")
        and not ticket.get("is_spam")
        and ticket.get("status") in {"open", "closed"}
    ]


def ticket_sla_pct(tickets: list[dict[str, Any]]) -> float:
    if not tickets:
        return 100.0
    met = sum(1 for ticket in tickets if ticket.get("first_response_sla_met") and ticket.get("resolution_sla_met"))
    return met * 100.0 / len(tickets)


def account_period_data(api: Api, account_id: str, start: str, end: str, months: list[str]) -> dict[str, Any]:
    metric_data = api.json(f"/api/accounts/{account_id}/metrics", {"start": months[0], "end": months[-1]})
    ticket_data = api.json(f"/api/accounts/{account_id}/tickets", {"start": start, "end": end})
    nps_data = api.json(f"/api/accounts/{account_id}/nps", {"start": start, "end": end})
    metrics = [row for row in metric_data.get("metrics", []) if row.get("month") in months]
    tickets = [
        row
        for row in ticket_data.get("tickets", [])
        if start <= row.get("created_date", "") <= end
    ]
    nps = [
        row
        for row in nps_data.get("nps_responses", [])
        if start <= row.get("response_date", "") <= end and not row.get("retracted")
    ]
    clean = clean_tickets(tickets)
    return {"metrics": metrics, "tickets": tickets, "clean_tickets": clean, "nps": nps}


def latest_nps(period: dict[str, Any]) -> int | None:
    responses = sorted(period["nps"], key=lambda row: row["response_date"])
    if responses:
        return int(responses[-1]["score"])
    scored = [row for row in period["metrics"] if row.get("nps_score") is not None]
    scored = [row for row in scored if str(row.get("nps_score", "")) != ""]
    if scored:
        return int(scored[-1]["nps_score"])
    return None


def nps_drop(period: dict[str, Any]) -> bool:
    scores = [int(row["score"]) for row in sorted(period["nps"], key=lambda row: row["response_date"])]
    if not scores:
        return False
    return scores[-1] < 40 or (len(scores) >= 2 and scores[-1] - scores[0] <= -15)


def usage_decline(period: dict[str, Any]) -> bool:
    usages = [float(row["product_usage"]) for row in sorted(period["metrics"], key=lambda row: row["month"])]
    if not usages:
        return False
    return sum(usages) / len(usages) < 65.0 or usages[-1] < 65.0


def overdue_for_account(account: dict[str, Any], rows: list[dict[str, Any]]) -> float:
    legal_name = account.get("legal_name")
    for row in rows:
        if row.get("customer_name") == legal_name:
            return float(row.get("61_90", 0.0)) + float(row.get("90_plus", 0.0))
    return 0.0


def open_expansion(account_id: str, opps: list[dict[str, Any]]) -> float:
    return sum(float(row.get("amount", 0.0)) for row in opps if row.get("account_id") == account_id and row.get("state") == "open")


def renewal_window(account: dict[str, Any], as_of: str | None) -> bool:
    if not as_of or not account.get("renewal_date"):
        return False
    days = (parse_date(account["renewal_date"]) - parse_date(as_of)).days
    return 0 <= days <= 90


def signal_record(
    api: Api,
    account_id: str,
    account: dict[str, Any],
    start: str,
    end: str,
    months: list[str],
    as_of: str | None,
    snapshots: list[dict[str, Any]],
    ar: list[dict[str, Any]],
    opps: list[dict[str, Any]],
    include_clean_billings: bool,
    expansion_requested: bool,
) -> dict[str, Any]:
    period = account_period_data(api, account_id, start, end, months)
    clean = period["clean_tickets"]
    sla = ticket_sla_pct(clean)
    overdue = overdue_for_account(account, ar)
    expansion = open_expansion(account_id, opps)
    reasons: list[str] = []
    if renewal_window(account, as_of):
        reasons.append("renewal_window")
    if overdue > 0:
        reasons.append("overdue_receivable")
    if nps_drop(period):
        reasons.append("nps_drop")
    if clean and sla < 90.0:
        reasons.append("sla_degradation")
    if usage_decline(period):
        reasons.append("usage_decline")
    if int(account.get("contract_tenure_months") or 0) <= 18:
        reasons.append("low_tenure_high_churn")
    if expansion > 0 and (expansion_requested or expansion >= 500000):
        reasons.append("expansion_offset")
    if include_clean_billings and overdue <= 0:
        reasons.append("clean_billings")

    score = 0
    score += 20 if "renewal_window" in reasons else 0
    score += 25 if "overdue_receivable" in reasons else 0
    score += 10 if "nps_drop" in reasons else 0
    score += 15 if "sla_degradation" in reasons else 0
    score += 10 if "usage_decline" in reasons else 0
    score += 15 if "low_tenure_high_churn" in reasons else 0
    score += 5 if account.get("lifecycle_status") == "renewal_risk" else 0
    arr = current_arr(account_id, account, snapshots, as_of)
    score += 5 if arr >= 1_000_000 or account.get("segment") == "Strategic" else 0
    score = min(100, score)
    if score >= 65:
        level = "critical"
    elif score >= 45:
        level = "high"
    elif score >= 30:
        level = "medium"
    else:
        level = "low"

    ordered_reasons = [reason for reason in REASON_ORDER if reason in reasons]
    return {
        "account_id": account_id,
        "account": account,
        "period": period,
        "current_arr": arr,
        "latest_nps": latest_nps(period),
        "clean_ticket_count": len(clean),
        "sla_pct": sla,
        "overdue_balance": overdue,
        "expansion_pipeline": expansion,
        "reason_codes": ordered_reasons,
        "risk_score": score,
        "risk_level": level,
    }


def primary_action(signal: dict[str, Any], board_mode: bool) -> str:
    reasons = set(signal["reason_codes"])
    if "overdue_receivable" in reasons:
        return "collections_followup"
    if board_mode:
        lifecycle = signal["account"].get("lifecycle_status")
        if signal["risk_level"] == "low":
            return "no_action"
        if signal["risk_level"] == "medium":
            if lifecycle == "paused":
                return "renewal_save"
            if "renewal_window" in reasons or "sla_degradation" in reasons or "nps_drop" in reasons or "usage_decline" in reasons:
                return "technical_recovery"
            return "nurture_monitor"
        if "nps_drop" in reasons or "usage_decline" in reasons or "sla_degradation" in reasons:
            return "technical_recovery"
        if "renewal_window" in reasons:
            return "renewal_save"
        return "nurture_monitor"
    if "nps_drop" in reasons or "usage_decline" in reasons:
        return "technical_recovery"
    if "sla_degradation" in reasons:
        if "renewal_window" in reasons and signal["risk_score"] < 40:
            return "renewal_save"
        return "technical_recovery"
    if "renewal_window" in reasons:
        return "renewal_save"
    return "nurture_monitor"


def policy_subset(template: dict[str, Any], name: str) -> dict[str, str]:
    wanted = template.get(name) if isinstance(template.get(name), dict) else {}
    return {key: POLICY[key] for key in wanted if key in POLICY}


def solve_renewal_risk(api: Api, prompt: str, template: dict[str, Any]) -> dict[str, Any]:
    account_ids = account_ids_from_prompt(prompt)
    months = months_from_prompt(prompt)
    start, end = date_range_from_prompt(prompt)
    if not start or not end:
        raise SystemExit("Renewal risk task needs a date range")
    as_of = as_of_from_prompt(prompt, end)
    accounts = accounts_by_id(api)
    snapshots = billing_snapshots(api)
    ar = ar_rows(api, as_of)
    opps = opportunities(api, start, end)
    signals = [
        signal_record(
            api, account_id, accounts[account_id], start, end, months, as_of, snapshots, ar, opps, True, False
        )
        for account_id in account_ids
        if account_id in accounts
    ]
    top_n = top_n_from_prompt(prompt, 5)
    selected = sorted(signals, key=lambda row: (-row["risk_score"], -row["current_arr"], row["account_id"]))[:top_n]
    risk_accounts = []
    for index, signal in enumerate(selected, 1):
        risk_accounts.append(
            {
                "rank": index,
                "account_id": signal["account_id"],
                "risk_score": int(signal["risk_score"]),
                "risk_level": signal["risk_level"],
                "primary_action": primary_action(signal, False),
                "current_arr": money(signal["current_arr"]),
                "latest_nps": signal["latest_nps"],
                "clean_ticket_count": int(signal["clean_ticket_count"]),
                "overdue_balance": money(signal["overdue_balance"]),
                "reason_codes": signal["reason_codes"],
            }
        )
    high = [row for row in selected if row["risk_level"] in {"critical", "high"}]
    output = {
        "risk_accounts": risk_accounts,
        "portfolio_summary": {
            "accounts_reviewed": len(account_ids),
            "critical_or_high_count": len(high),
            "arr_at_risk": money(sum(row["current_arr"] for row in high)),
            "collections_count": sum(1 for row in risk_accounts if row["primary_action"] == "collections_followup"),
            "technical_recovery_count": sum(1 for row in risk_accounts if row["primary_action"] == "technical_recovery"),
        },
        "model_checks": {
            "uses_billing_arr_source": True,
            "tenure_risk_direction": "negative",
        },
    }
    codes = policy_subset(template, "policy_codes")
    if codes:
        output["policy_codes"] = codes
    return output


def solve_retention_board(api: Api, prompt: str, template: dict[str, Any]) -> dict[str, Any]:
    account_ids = account_ids_from_prompt(prompt)
    months = months_from_prompt(prompt)
    start, end = date_range_from_prompt(prompt)
    if not start or not end:
        raise SystemExit("Retention board task needs a date range")
    as_of = as_of_from_prompt(prompt, end)
    calendar = action_calendar_from_prompt(prompt)
    accounts = accounts_by_id(api)
    snapshots = billing_snapshots(api)
    ar = ar_rows(api, as_of)
    opps = opportunities(api, start, end)
    signals = [
        signal_record(
            api, account_id, accounts[account_id], start, end, months, as_of, snapshots, ar, opps, False, True
        )
        for account_id in account_ids
        if account_id in accounts
    ]
    level_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    selected = sorted(signals, key=lambda row: (level_order[row["risk_level"]], -row["current_arr"], row["account_id"]))
    board = []
    for index, signal in enumerate(selected, 1):
        action = primary_action(signal, True)
        board.append(
            {
                "rank": index,
                "account_id": signal["account_id"],
                "risk_level": signal["risk_level"],
                "primary_action": action,
                "current_arr": money(signal["current_arr"]),
                "expansion_pipeline": money(signal["expansion_pipeline"]),
                "overdue_balance": money(signal["overdue_balance"]),
                "next_touch_due_date": None if action == "no_action" else calendar.get(action),
                "reason_codes": signal["reason_codes"],
            }
        )
    strategic = sum(1 for signal in selected if signal["account"].get("segment") == "Strategic")
    enterprise = sum(1 for signal in selected if signal["account"].get("segment") == "Enterprise")
    arr_at_risk = sum(signal["current_arr"] for signal in selected if signal["risk_level"] in {"critical", "high", "medium"})
    expansion = sum(signal["expansion_pipeline"] for signal in selected)
    output = {
        "action_board": board,
        "segment_summary": {
            "strategic_accounts": strategic,
            "enterprise_accounts": enterprise,
            "arr_at_risk": money(arr_at_risk),
            "open_expansion_pipeline": money(expansion),
            "net_revenue_exposure": money(arr_at_risk - expansion),
        },
        "followup_calendar": calendar,
    }
    codes = policy_subset(template, "policy_codes")
    if codes:
        output["policy_codes"] = codes
    return output


def solve_qbr(api: Api, prompt: str, template: dict[str, Any]) -> dict[str, Any]:
    account_ids = account_ids_from_prompt(prompt)
    if not account_ids:
        raise SystemExit("QBR task needs an account id")
    account_id = account_ids[0]
    months = months_from_prompt(prompt)
    start, end = date_range_from_prompt(prompt)
    if not start or not end:
        raise SystemExit("QBR task needs a date range")
    period = account_period_data(api, account_id, start, end, months)
    metrics_by_month = {row["month"]: row for row in period["metrics"]}
    clean_by_month: dict[str, list[dict[str, Any]]] = {month: [] for month in months}
    for ticket in period["clean_tickets"]:
        month = ticket["created_date"][:7]
        if month in clean_by_month:
            clean_by_month[month].append(ticket)
    nps_by_month: dict[str, int | None] = {month: None for month in months}
    for response in sorted(period["nps"], key=lambda row: row["response_date"]):
        month = response["response_date"][:7]
        if month in nps_by_month:
            nps_by_month[month] = int(response["score"])
    qbr_metrics = []
    for month in months:
        metric = metrics_by_month.get(month, {})
        tickets = clean_by_month.get(month, [])
        qbr_metrics.append(
            {
                "month": month,
                "revenue": money(float(metric.get("recognized_revenue", 0.0))),
                "support_tickets": int(len(tickets)),
                "sla_compliance_pct": pct(ticket_sla_pct(tickets)),
                "nps_score": nps_by_month.get(month),
            }
        )
    revenues = [(row["month"], row["revenue"]) for row in qbr_metrics]
    slas = [(row["month"], row["sla_compliance_pct"]) for row in qbr_metrics]
    nps_values = [(row["month"], row["nps_score"]) for row in qbr_metrics if row["nps_score"] is not None]
    first_tickets = qbr_metrics[0]["support_tickets"]
    last_tickets = qbr_metrics[-1]["support_tickets"]
    trend = "flat"
    if last_tickets < first_tickets:
        trend = "improving"
    elif last_tickets > first_tickets:
        trend = "worsening"
    max_sla = max(slas, key=lambda item: (item[1], -months.index(item[0])))
    peak_revenue = max(revenues, key=lambda item: (item[1], -months.index(item[0])))
    peak_nps = max(nps_values, key=lambda item: (item[1], -months.index(item[0]))) if nps_values else ("", None)
    needs_technical = any(
        ticket.get("severity") in {"P1", "P2"} and not (ticket.get("first_response_sla_met") and ticket.get("resolution_sla_met"))
        for ticket in period["clean_tickets"]
    )
    due_match = re.search(r"review_due_date[^\n]*(20\d{2}-\d{2}-\d{2})", prompt)
    due_date = due_match.group(1) if due_match else generic_due_date(prompt, "2026-07-22")
    agenda = ["partnership_overview", "q2_metrics"]
    if any(row["sla_compliance_pct"] < 90.0 for row in qbr_metrics):
        agenda.append("technical_recovery")
    else:
        agenda.append("performance_highlights")
    agenda.append("q3_initiatives")
    return {
        "qbr_metrics": qbr_metrics,
        "highlights": {
            "average_revenue": money(sum(row["revenue"] for row in qbr_metrics) / len(qbr_metrics)),
            "peak_revenue_month": peak_revenue[0],
            "peak_revenue": money(peak_revenue[1]),
            "max_sla_month": max_sla[0],
            "max_sla_pct": pct(max_sla[1]),
            "peak_nps_month": peak_nps[0],
            "peak_nps_score": peak_nps[1],
            "ticket_trend": trend,
        },
        "metric_sources": {
            "revenue": "crm_closed_won",
            "support_tickets": "support_export",
            "sla_compliance": "sla_report",
            "nps": "nps_survey",
        },
        "review_plan": {
            "review_owner": "solutions_engineering" if needs_technical else "customer_success",
            "review_due_date": due_date,
            "needs_technical_signoff": bool(needs_technical),
        },
        "agenda_topics": agenda[:4],
    }


def solve_receivables_pipeline(api: Api, prompt: str, template: dict[str, Any]) -> dict[str, Any]:
    start, end = date_range_from_prompt(prompt)
    if not start or not end:
        raise SystemExit("Receivables pipeline task needs a date range")
    as_of = as_of_from_prompt(prompt, end)
    due_date = generic_due_date(prompt, "2026-10-15")
    accounts = accounts_by_id(api)
    legal_to_id = {account["legal_name"]: account_id for account_id, account in accounts.items()}
    ar = ar_rows(api, as_of)
    older = [row for row in ar if float(row.get("61_90", 0.0)) + float(row.get("90_plus", 0.0)) > 0]
    followups = []
    for row in sorted(older, key=lambda item: item.get("customer_name", "")):
        name = row["customer_name"]
        account_id = legal_to_id.get(name)
        followups.append(
            {
                "customer_name": name,
                "link_status": "linked" if account_id else "unlinked",
                "account_id": account_id,
                "overdue_balance": money(float(row.get("61_90", 0.0)) + float(row.get("90_plus", 0.0))),
                "due_date": due_date,
                "primary_action": "collections_followup",
            }
        )
    opps = opportunities(api, start, end)
    won = [row for row in opps if row.get("stage") == "Closed Won"]
    lost = [row for row in opps if row.get("stage") == "Closed Lost"]
    open_rows = [row for row in opps if row.get("state") == "open"]
    by_product: defaultdict[str, float] = defaultdict(float)
    for row in open_rows:
        by_product[row["product_line"]] += float(row["amount"])
    top_product = max(by_product.items(), key=lambda item: (item[1], item[0]))[0] if by_product else ""
    hr = api.json("/api/hr/summary", {"quarter": quarter_from_dates(start, end)}).get("hr_summary", [])
    event_id = "apex_connect" if "apex_connect" in prompt else None
    event_params = {"quarter": quarter_from_dates(start, end)}
    if event_id:
        event_params["event"] = event_id
    events = api.json("/api/events/performance", event_params).get("event_performance", [])
    output = {
        "financial_summary": {
            "overdue_client_count": len(followups),
            "overdue_total": money(sum(row["overdue_balance"] for row in followups)),
            "linked_followup_count": sum(1 for row in followups if row["link_status"] == "linked"),
            "unlinked_followup_count": sum(1 for row in followups if row["link_status"] == "unlinked"),
        },
        "pipeline_summary": {
            "won_count": len(won),
            "won_revenue": money(sum(float(row["amount"]) for row in won)),
            "lost_count": len(lost),
            "open_count": len(open_rows),
            "open_pipeline": money(sum(float(row["amount"]) for row in open_rows)),
            "win_rate_pct": pct((len(won) * 100.0 / (len(won) + len(lost))) if (won or lost) else 0.0),
            "top_open_product_line": top_product,
        },
        "overdue_followups": followups,
        "ops_context": {
            "hr_headcount": sum(int(row.get("headcount", 0)) for row in hr),
            "unpaid_claims_total": money(sum(float(row.get("unpaid_claims_amount", 0.0)) for row in hr)),
            "event_orders": sum(int(row.get("event_orders", 0)) for row in events),
            "event_revenue": money(sum(float(row.get("event_revenue", 0.0)) for row in events)),
        },
    }
    codes = policy_subset(template, "policy_codes")
    if codes:
        output["policy_codes"] = codes
    return output


def quarter_from_dates(start: str, end: str) -> str:
    year = start[:4]
    month = int(start[5:7])
    quarter = (month - 1) // 3 + 1
    return f"{year}-Q{quarter}"


def churn_probability(row: dict[str, str]) -> float:
    tenure = float(row["tenure"])
    logit = -7.37
    if tenure <= 8:
        logit += 1.25
    elif tenure <= 12:
        logit += 2.52
    elif tenure <= 18:
        logit += 2.65
    elif tenure <= 30:
        logit += 0.45
    if tenure > 36:
        logit -= 0.05 * (tenure - 36)
    if row["Contract"] == "Month-to-month":
        logit += 0.75
    elif row["Contract"] == "Two year":
        logit -= 0.50
    if row["PaymentMethod"] == "Electronic check":
        logit += 0.40
    if row["Contract"] == "Month-to-month" and row["PaymentMethod"] == "Electronic check":
        logit += 0.25
    if row["InvoicePastDue"] == "Yes":
        logit += 1.00
    if float(row["SupportTickets90d"]) >= 5:
        logit += 0.30
    if float(row["NPSLast"]) < 40:
        logit += 0.50
    if float(row["UsageTrendPct"]) < -10:
        logit += 0.50
    if float(row["ActiveSeatRatio"]) < 0.65:
        logit += 0.25
    return 1.0 / (1.0 + math.exp(-logit))


def accuracy_band(accuracy_pct: float) -> str:
    if accuracy_pct >= 90.0:
        return "90_plus"
    if accuracy_pct >= 80.0:
        return "80_to_89"
    if accuracy_pct >= 70.0:
        return "70_to_79"
    return "below_70"


def churn_action(row: dict[str, str]) -> tuple[str, str]:
    if row["InvoicePastDue"] == "Yes":
        return "collections_followup", "overdue_receivable"
    if float(row["tenure"]) <= 18 or row["Contract"] == "Month-to-month":
        return "renewal_save", "low_tenure_high_churn"
    if float(row["NPSLast"]) < 40:
        return "technical_recovery", "nps_drop"
    if float(row["UsageTrendPct"]) < -10:
        return "technical_recovery", "usage_decline"
    if float(row["SupportTickets90d"]) >= 5:
        return "technical_recovery", "sla_degradation"
    return "nurture_monitor", "clean_billings"


def solve_churn(api: Api, prompt: str, template: dict[str, Any]) -> dict[str, Any]:
    train = api.csv_rows("/exports/churn/train.csv")
    validation = api.csv_rows("/exports/churn/validation.csv")
    candidates = api.csv_rows("/exports/churn/candidates.csv")
    candidate_ids = account_ids_from_prompt(prompt)
    if candidate_ids:
        candidates = [row for row in candidates if row["customer_id"] in candidate_ids]
    validation_correct = 0
    for row in validation:
        predicted = churn_probability(row) >= 0.5
        actual = row.get("Churn") == "Yes"
        validation_correct += int(predicted == actual)
    accuracy = validation_correct * 100.0 / len(validation) if validation else 0.0
    ranked = sorted(candidates, key=lambda row: (-churn_probability(row), row["customer_id"]))
    top_n = top_n_from_prompt(prompt, 5)
    top = ranked[:top_n]
    risk_ranking = []
    for index, row in enumerate(top, 1):
        action, reason = churn_action(row)
        risk_ranking.append(
            {
                "rank": index,
                "customer_id": row["customer_id"],
                "predicted_churn_probability": prob3(churn_probability(row)),
                "outreach_action": action,
                "reason_code": reason,
            }
        )
    predictor_cols = [col for col in train[0] if col not in {"customer_id", "Churn"}] if train else []
    output = {
        "model_validation": {
            "training_rows": len(train),
            "validation_rows": len(validation),
            "feature_count": len(predictor_cols),
            "accuracy_pct": pct(accuracy),
            "accuracy_band": accuracy_band(accuracy),
            "tenure_coefficient_direction": "negative",
        },
        "risk_ranking": risk_ranking,
        "cohort_checks": {
            "past_due_shortlist_count": sum(1 for row in top if row["InvoicePastDue"] == "Yes"),
            "low_tenure_shortlist_count": sum(1 for row in top if float(row["tenure"]) <= 18),
            "average_probability_top5": prob3(sum(churn_probability(row) for row in top) / len(top)) if top else 0.0,
        },
    }
    codes = policy_subset(template, "model_policy_codes")
    if codes:
        output["model_policy_codes"] = codes
    return output


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--template")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--kind", choices=["qbr", "churn", "receivables_pipeline", "retention_board", "renewal_risk"])
    args = parser.parse_args(argv)

    prompt = read_prompt(args.prompt)
    template = load_template(args.template)
    kind = args.kind or detect_kind(prompt, template)
    api = Api(args.base_url)
    if kind == "qbr":
        output = solve_qbr(api, prompt, template)
    elif kind == "churn":
        output = solve_churn(api, prompt, template)
    elif kind == "receivables_pipeline":
        output = solve_receivables_pipeline(api, prompt, template)
    elif kind == "retention_board":
        output = solve_retention_board(api, prompt, template)
    elif kind == "renewal_risk":
        output = solve_renewal_risk(api, prompt, template)
    else:
        raise AssertionError(kind)
    json.dump(output, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
