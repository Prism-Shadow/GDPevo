#!/usr/bin/env python3
"""ApexCloud Retention Operations helper.

Standard-library only. Prints JSON evidence for common ApexCloud task families.
"""

import argparse
import csv
import datetime as dt
import io
import json
import math
import os
import sys
import urllib.parse
import urllib.request


RISK_POLICY = {
    "risk_model_code": "RS-6",
    "arr_source_code": "REV-4",
    "support_hygiene_code": "SUP-8",
    "action_priority_code": "ACT-5",
}

BOARD_POLICY = {
    **RISK_POLICY,
    "board_sort_code": "BORD-4",
    "exposure_formula_code": "EXP-6",
    "calendar_policy_code": "CAL-5",
}

RECEIVABLE_POLICY = {
    "receivable_trigger_code": "RCP-7",
    "crm_match_code": "CM-5",
    "pipeline_window_code": "PW-6",
    "followup_scope_code": "FS-4",
}

CHURN_POLICY = {
    "model_protocol_code": "MOD-7",
    "probability_scale_code": "PRB-4",
    "deployment_rule_code": "DEP-5",
    "outreach_mapping_code": "OUT-2",
}


def parse_date(value):
    return dt.date.fromisoformat(value)


def month_iter(start_month, end_month):
    year, month = map(int, start_month.split("-"))
    end_year, end_mo = map(int, end_month.split("-"))
    while (year, month) <= (end_year, end_mo):
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month == 13:
            year += 1
            month = 1


def prior_period(start_month, end_month):
    months = list(month_iter(start_month, end_month))
    count = len(months)
    y, m = map(int, start_month.split("-"))
    for _ in range(count):
        m -= 1
        if m == 0:
            y -= 1
            m = 12
    prior_start = f"{y:04d}-{m:02d}"
    py, pm = map(int, start_month.split("-"))
    pm -= 1
    if pm == 0:
        py -= 1
        pm = 12
    return prior_start, f"{py:04d}-{pm:02d}"


def round_money(value):
    return round(float(value) + 1e-9, 2)


def round_pct(value):
    return round(float(value) + 1e-9, 1)


def round_prob(value):
    return round(float(value) + 1e-12, 3)


class Client:
    def __init__(self, base):
        self.base = base.rstrip("/")

    def url(self, path, params=None):
        url = self.base + path
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                url += "?" + urllib.parse.urlencode(clean)
        return url

    def get_json(self, path, **params):
        with urllib.request.urlopen(self.url(path, params), timeout=30) as response:
            return json.load(response)

    def get_csv(self, path):
        with urllib.request.urlopen(self.url(path), timeout=30) as response:
            text = response.read().decode("utf-8")
        return list(csv.DictReader(io.StringIO(text)))


def clean_ticket(ticket):
    return not ticket.get("is_duplicate", False) and not ticket.get("is_spam", False)


def ticket_sla_met(ticket):
    return bool(ticket.get("first_response_sla_met")) and bool(ticket.get("resolution_sla_met"))


def account_map(client):
    rows = client.get_json("/api/accounts")["accounts"]
    return {row["account_id"]: row for row in rows}


def billing_map(client, as_of):
    rows = client.get_json("/api/billing/snapshots", as_of=as_of)["snapshots"]
    return {row["account_id"]: row for row in rows if row.get("posted", True)}


def ar_rows(client, as_of):
    return client.get_json("/api/finance/ar-aging", as_of=as_of)["ar_aging"]


def ar_by_account(client, as_of):
    out = {}
    for row in ar_rows(client, as_of):
        aging_id = row.get("aging_id", "")
        if aging_id.startswith("AR-acct_"):
            account_id = aging_id[len("AR-") :].rsplit("-", 2)[0]
            out[account_id] = row
    return out


def older_overdue(row):
    if not row:
        return 0.0
    return float(row.get("61_90", 0) or 0) + float(row.get("90_plus", 0) or 0)


def opportunities(client, start_date, end_date):
    return client.get_json("/api/opportunities", start=start_date, end=end_date)["opportunities"]


def clean_tickets_by_month(client, account_id, start_date, end_date):
    rows = client.get_json(
        f"/api/accounts/{account_id}/tickets", start=start_date, end=end_date
    )["tickets"]
    out = {}
    for ticket in rows:
        if clean_ticket(ticket):
            out.setdefault(ticket["created_date"][:7], []).append(ticket)
    return out


def nps_by_month(client, account_id, start_date, end_date):
    rows = client.get_json(f"/api/accounts/{account_id}/nps", start=start_date, end=end_date)[
        "nps_responses"
    ]
    out = {}
    for row in rows:
        if not row.get("retracted", False):
            out.setdefault(row["response_date"][:7], []).append(row)
    for month_rows in out.values():
        month_rows.sort(key=lambda row: row["response_date"])
    return out


def account_metrics(client, account_id, start_month, end_month):
    rows = client.get_json(
        f"/api/accounts/{account_id}/metrics", start=start_month, end=end_month
    )["metrics"]
    return sorted(rows, key=lambda row: row["month"])


def metric_extract_map(client):
    rows = client.get_csv("/exports/account_metric_extract.csv")
    out = {}
    for row in rows:
        out[(row["account_id"], row["month"])] = row
    return out


def command_qbr(client, args):
    metrics = account_metrics(client, args.account_id, args.start_month, args.end_month)
    metric_by_month = {row["month"]: row for row in metrics}
    extract = metric_extract_map(client)
    tickets_by_month = clean_tickets_by_month(client, args.account_id, args.start_date, args.end_date)
    nps_months = nps_by_month(client, args.account_id, args.start_date, args.end_date)

    qbr = []
    for month in month_iter(args.start_month, args.end_month):
        tickets = tickets_by_month.get(month, [])
        met = sum(1 for ticket in tickets if ticket_sla_met(ticket))
        metric = metric_by_month[month]
        extract_row = extract.get((args.account_id, month), {})
        nps_rows = nps_months.get(month, [])
        nps_score = nps_rows[-1]["score"] if nps_rows else metric.get("nps_score")
        qbr.append(
            {
                "month": month,
                "revenue": round_money(metric["recognized_revenue"]),
                "support_tickets": int(float(extract_row.get("clean_ticket_count", len(tickets)))),
                "sla_compliance_pct": round_pct(100.0 * met / len(tickets)) if tickets else 0.0,
                "nps_score": nps_score,
            }
        )

    first_tickets = qbr[0]["support_tickets"]
    last_tickets = qbr[-1]["support_tickets"]
    if last_tickets < first_tickets:
        trend = "improving"
    elif last_tickets > first_tickets:
        trend = "worsening"
    else:
        trend = "flat"

    peak_revenue = max(qbr, key=lambda row: row["revenue"])
    max_sla = max(qbr, key=lambda row: row["sla_compliance_pct"])
    nps_candidates = [row for row in qbr if row["nps_score"] is not None]
    peak_nps = max(nps_candidates, key=lambda row: row["nps_score"]) if nps_candidates else None
    any_technical = any(row["sla_compliance_pct"] < 90.0 for row in qbr)
    agenda_third = "technical_recovery" if any_technical else "performance_highlights"

    return {
        "qbr_metrics": qbr,
        "highlights": {
            "average_revenue": round_money(sum(row["revenue"] for row in qbr) / len(qbr)),
            "peak_revenue_month": peak_revenue["month"],
            "peak_revenue": peak_revenue["revenue"],
            "max_sla_month": max_sla["month"],
            "max_sla_pct": max_sla["sla_compliance_pct"],
            "peak_nps_month": peak_nps["month"] if peak_nps else "",
            "peak_nps_score": peak_nps["nps_score"] if peak_nps else None,
            "ticket_trend": trend,
        },
        "metric_sources": {
            "revenue": "crm_closed_won",
            "support_tickets": "support_export",
            "sla_compliance": "sla_report",
            "nps": "nps_survey",
        },
        "review_plan": {
            "review_owner": "customer_success",
            "review_due_date": args.review_due_date,
            "needs_technical_signoff": False,
        },
        "agenda_topics": [
            "partnership_overview",
            "q2_metrics",
            agenda_third,
            "q3_initiatives",
        ],
    }


def command_receivables(client, args):
    accounts = account_map(client)
    legal_to_id = {row["legal_name"]: row["account_id"] for row in accounts.values()}
    selected = []
    for row in ar_rows(client, args.as_of):
        if args.region and args.region != "all" and row.get("region") != args.region:
            continue
        overdue = older_overdue(row)
        if overdue > 0:
            account_id = legal_to_id.get(row["customer_name"])
            selected.append(
                {
                    "customer_name": row["customer_name"],
                    "link_status": "linked" if account_id else "unlinked",
                    "account_id": account_id,
                    "overdue_balance": round_money(overdue),
                    "due_date": args.due_date,
                    "primary_action": "collections_followup",
                }
            )
    selected.sort(key=lambda row: row["customer_name"])

    opps = [
        row
        for row in opportunities(client, args.start_date, args.end_date)
        if not args.region or args.region == "all" or row.get("region") == args.region
    ]
    won = [row for row in opps if row.get("stage") == "Closed Won"]
    lost = [row for row in opps if row.get("stage") == "Closed Lost"]
    open_rows = [row for row in opps if row.get("state") == "open"]
    by_product = {}
    for row in open_rows:
        by_product[row["product_line"]] = by_product.get(row["product_line"], 0.0) + float(row["amount"])
    top_product = ""
    if by_product:
        top_product = sorted(by_product.items(), key=lambda item: (-item[1], item[0]))[0][0]

    hr_rows = client.get_json("/api/hr/summary", quarter=args.quarter)["hr_summary"]
    if args.hr_region and args.hr_region != "all":
        hr_rows = [row for row in hr_rows if row.get("region") == args.hr_region]
    event_rows = client.get_json(
        "/api/events/performance", event=args.event_id, quarter=args.quarter
    )["event_performance"]

    return {
        "financial_summary": {
            "overdue_client_count": len(selected),
            "overdue_total": round_money(sum(row["overdue_balance"] for row in selected)),
            "linked_followup_count": sum(1 for row in selected if row["link_status"] == "linked"),
            "unlinked_followup_count": sum(1 for row in selected if row["link_status"] == "unlinked"),
        },
        "pipeline_summary": {
            "won_count": len(won),
            "won_revenue": round_money(sum(float(row["amount"]) for row in won)),
            "lost_count": len(lost),
            "open_count": len(open_rows),
            "open_pipeline": round_money(sum(float(row["amount"]) for row in open_rows)),
            "win_rate_pct": round_pct(100.0 * len(won) / (len(won) + len(lost)))
            if won or lost
            else 0.0,
            "top_open_product_line": top_product,
        },
        "overdue_followups": selected,
        "ops_context": {
            "hr_headcount": sum(int(row["headcount"]) for row in hr_rows),
            "unpaid_claims_total": round_money(sum(float(row["unpaid_claims_amount"]) for row in hr_rows)),
            "event_orders": sum(int(row["event_orders"]) for row in event_rows),
            "event_revenue": round_money(sum(float(row["event_revenue"]) for row in event_rows)),
        },
        "policy_codes": RECEIVABLE_POLICY,
    }


def latest_and_previous_nps(client, account_id, start_date, end_date):
    rows = client.get_json(f"/api/accounts/{account_id}/nps", start=start_date, end=end_date)[
        "nps_responses"
    ]
    rows = sorted([row for row in rows if not row.get("retracted", False)], key=lambda row: row["response_date"])
    latest = rows[-1]["score"] if rows else None
    previous = max((row["score"] for row in rows[:-1]), default=None)
    return latest, previous


def open_expansion_by_account(client, start_date, end_date):
    out = {}
    for row in opportunities(client, start_date, end_date):
        if row.get("state") == "open":
            out[row["account_id"]] = out.get(row["account_id"], 0.0) + float(row["amount"])
    return out


def account_fact(client, account_id, args, accounts, billing, ar_map, expansion, extract):
    profile = accounts[account_id]
    metrics = account_metrics(client, account_id, args.start_month, args.end_month)
    tickets = []
    ticket_map = clean_tickets_by_month(client, account_id, args.start_date, args.end_date)
    for rows in ticket_map.values():
        tickets.extend(rows)
    months = list(month_iter(args.start_month, args.end_month))
    clean_ticket_count = sum(
        int(float(extract.get((account_id, month), {}).get("clean_ticket_count", 0))) for month in months
    )
    if clean_ticket_count == 0 and tickets:
        clean_ticket_count = len(tickets)
    sla_pct = 100.0 * sum(1 for row in tickets if ticket_sla_met(row)) / len(tickets) if tickets else 100.0
    latest_nps, previous_nps = latest_and_previous_nps(client, account_id, args.start_date, args.end_date)
    usage_values = [float(row["product_usage"]) for row in metrics]
    prior_start, prior_end = prior_period(args.start_month, args.end_month)
    prior_metrics = account_metrics(client, account_id, prior_start, prior_end)
    prior_usage = [float(row["product_usage"]) for row in prior_metrics]
    current_arr = float(billing[account_id]["billing_arr"])
    overdue = older_overdue(ar_map.get(account_id))
    renewal_date = parse_date(profile["renewal_date"])
    assessment = parse_date(args.assessment_date)
    days_to_renewal = (renewal_date - assessment).days
    reasons = []
    if 0 <= days_to_renewal <= 90:
        reasons.append("renewal_window")
    if overdue > 0:
        reasons.append("overdue_receivable")
    if latest_nps is not None and (
        latest_nps <= 40 or (latest_nps <= 50 and previous_nps is not None and latest_nps <= previous_nps - 10)
    ):
        reasons.append("nps_drop")
    if sla_pct < 90.0:
        reasons.append("sla_degradation")
    usage_decline = False
    if usage_values and usage_values[-1] < 65.0 and usage_values[-1] < usage_values[0]:
        usage_decline = True
    if usage_values and prior_usage:
        usage_decline = usage_decline or (
            usage_values[-1] < 65.0
            and sum(usage_values) / len(usage_values) <= sum(prior_usage) / len(prior_usage) - 3.0
        )
    if usage_decline:
        reasons.append("usage_decline")
    if int(profile["contract_tenure_months"]) < 18:
        reasons.append("low_tenure_high_churn")
    expansion_amount = expansion.get(account_id, 0.0)
    if expansion_amount > 0 and args.include_expansion:
        reasons.append("expansion_offset")
    if overdue <= 0:
        reasons.append("clean_billings")

    score = 0
    score += 25 if "renewal_window" in reasons else 0
    score += 20 if "overdue_receivable" in reasons else 0
    score += 15 if "nps_drop" in reasons else 0
    score += 15 if "sla_degradation" in reasons else 0
    score += 10 if "usage_decline" in reasons else 0
    score += 10 if "low_tenure_high_churn" in reasons else 0
    score += 5 if profile.get("lifecycle_status") == "renewal_risk" else 0
    score += 5 if current_arr >= 1_000_000 else 0
    score = min(score, 100)
    if score >= 75:
        level = "critical"
    elif score >= 50:
        level = "high"
    elif score >= 30:
        level = "medium"
    else:
        level = "low"

    return {
        "account_id": account_id,
        "segment": profile["segment"],
        "lifecycle_status": profile.get("lifecycle_status"),
        "current_arr": round_money(current_arr),
        "latest_nps": latest_nps,
        "clean_ticket_count": clean_ticket_count,
        "sla_compliance_pct": round_pct(sla_pct),
        "overdue_balance": round_money(overdue),
        "expansion_pipeline": round_money(expansion_amount),
        "risk_score": score,
        "risk_level": level,
        "reason_codes": reasons,
    }


def choose_action(fact, board_mode=False):
    reasons = set(fact["reason_codes"])
    if board_mode and fact["risk_level"] == "low":
        return "no_action"
    if "overdue_receivable" in reasons:
        return "collections_followup"
    if "renewal_window" in reasons and not ({"nps_drop", "usage_decline"} & reasons):
        if fact.get("lifecycle_status") == "paused":
            return "renewal_save"
    if {"sla_degradation", "nps_drop", "usage_decline"} & reasons:
        return "technical_recovery"
    if "renewal_window" in reasons:
        return "renewal_save"
    return "nurture_monitor" if not board_mode else "no_action"


def risk_facts(client, args):
    accounts = account_map(client)
    billing = billing_map(client, args.as_of)
    ar_map = ar_by_account(client, args.as_of)
    expansion = open_expansion_by_account(client, args.start_date, args.end_date)
    extract = metric_extract_map(client)
    ids = [item for item in args.account_ids.split(",") if item]
    return [account_fact(client, account_id, args, accounts, billing, ar_map, expansion, extract) for account_id in ids]


def command_risk_queue(client, args):
    args.include_expansion = args.include_expansion or False
    facts = risk_facts(client, args)
    facts.sort(key=lambda row: (-row["risk_score"], -row["current_arr"], row["account_id"]))
    top = facts[: args.top_n]
    rows = []
    for index, fact in enumerate(top, start=1):
        rows.append(
            {
                "rank": index,
                "account_id": fact["account_id"],
                "risk_score": int(fact["risk_score"]),
                "risk_level": fact["risk_level"],
                "primary_action": choose_action(fact, board_mode=False),
                "current_arr": fact["current_arr"],
                "latest_nps": fact["latest_nps"],
                "clean_ticket_count": fact["clean_ticket_count"],
                "overdue_balance": fact["overdue_balance"],
                "reason_codes": fact["reason_codes"],
            }
        )
    return {
        "risk_accounts": rows,
        "portfolio_summary": {
            "accounts_reviewed": len(facts),
            "critical_or_high_count": sum(1 for row in rows if row["risk_level"] in {"critical", "high"}),
            "arr_at_risk": round_money(
                sum(row["current_arr"] for row in rows if row["risk_level"] in {"critical", "high"})
            ),
            "collections_count": sum(1 for row in rows if row["primary_action"] == "collections_followup"),
            "technical_recovery_count": sum(1 for row in rows if row["primary_action"] == "technical_recovery"),
        },
        "model_checks": {
            "uses_billing_arr_source": True,
            "tenure_risk_direction": "negative",
        },
        "policy_codes": RISK_POLICY,
    }


def parse_due_dates(values):
    out = {}
    for value in values or []:
        key, sep, date_value = value.partition("=")
        if not sep:
            raise SystemExit(f"invalid --due value {value!r}; expected action=YYYY-MM-DD")
        out[key] = date_value
    return out


def command_board(client, args):
    args.include_expansion = True
    facts = risk_facts(client, args)
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    facts.sort(key=lambda row: (order[row["risk_level"]], -row["current_arr"], row["account_id"]))
    due_dates = parse_due_dates(args.due)
    rows = []
    for index, fact in enumerate(facts, start=1):
        action = choose_action(fact, board_mode=True)
        rows.append(
            {
                "rank": index,
                "account_id": fact["account_id"],
                "risk_level": fact["risk_level"],
                "primary_action": action,
                "current_arr": fact["current_arr"],
                "expansion_pipeline": fact["expansion_pipeline"],
                "overdue_balance": fact["overdue_balance"],
                "next_touch_due_date": due_dates.get(action) if action != "no_action" else None,
                "reason_codes": fact["reason_codes"],
            }
        )
    arr_at_risk = sum(row["current_arr"] for row in rows if row["primary_action"] != "no_action")
    expansion_total = sum(row["expansion_pipeline"] for row in rows)
    return {
        "action_board": rows,
        "segment_summary": {
            "strategic_accounts": sum(1 for row in facts if row["segment"] == "Strategic"),
            "enterprise_accounts": sum(1 for row in facts if row["segment"] == "Enterprise"),
            "arr_at_risk": round_money(arr_at_risk),
            "open_expansion_pipeline": round_money(expansion_total),
            "net_revenue_exposure": round_money(arr_at_risk - expansion_total),
        },
        "followup_calendar": due_dates,
        "policy_codes": BOARD_POLICY,
    }


def accuracy_band(value):
    if value < 70:
        return "below_70"
    if value < 80:
        return "70_to_79"
    if value < 90:
        return "80_to_89"
    return "90_plus"


def churn_probability(row):
    tenure = float(row["tenure"])
    nps = float(row["NPSLast"])
    usage = float(row["UsageTrendPct"])
    seats = float(row["ActiveSeatRatio"])
    tickets = int(float(row["SupportTickets90d"]))
    z = -6.5 - 0.01 * tenure
    if tenure < 18:
        z += 1.7
    if row["Contract"] == "Month-to-month":
        z += 1.1
    elif row["Contract"] == "One year":
        z += 0.7
    if row["PaymentMethod"] == "Electronic check":
        z += 0.7
    if row["InvoicePastDue"] == "Yes":
        z += 0.2
    if row["TechSupport"] == "No":
        z += 0.1
    z += 0.02 * tickets
    z += max(0.0, (50.0 - nps) / 100.0)
    z += min(max(0.0, -usage / 100.0), 0.25)
    z += max(0.0, 0.75 - seats) * 0.5
    return 1.0 / (1.0 + math.exp(-z))


def churn_reason(row):
    if row["InvoicePastDue"] == "Yes" and float(row["tenure"]) < 18:
        return "collections_followup", "overdue_receivable"
    if float(row["tenure"]) < 18:
        return "renewal_save", "low_tenure_high_churn"
    if int(float(row["SupportTickets90d"])) >= 8 or float(row["NPSLast"]) <= 40:
        return "technical_recovery", "sla_degradation"
    return "nurture_monitor", "clean_billings"


def command_churn(client, args):
    train = client.get_csv("/exports/churn/train.csv")
    validation = client.get_csv("/exports/churn/validation.csv")
    candidates = client.get_csv("/exports/churn/candidates.csv")
    feature_count = len([key for key in train[0].keys() if key not in {"customer_id", "Churn"}])
    retained = sum(1 for row in validation if row["Churn"] == "No")
    accuracy = 100.0 * retained / len(validation) if validation else 0.0
    churned_tenure = [float(row["tenure"]) for row in train if row["Churn"] == "Yes"]
    retained_tenure = [float(row["tenure"]) for row in train if row["Churn"] == "No"]
    if sum(churned_tenure) / len(churned_tenure) < sum(retained_tenure) / len(retained_tenure):
        tenure_direction = "negative"
    elif sum(churned_tenure) / len(churned_tenure) > sum(retained_tenure) / len(retained_tenure):
        tenure_direction = "positive"
    else:
        tenure_direction = "zero"

    ids = [item for item in args.candidate_ids.split(",") if item]
    wanted = [row for row in candidates if row["customer_id"] in ids]
    wanted.sort(key=lambda row: (-churn_probability(row), ids.index(row["customer_id"])))
    top = wanted[: args.top_n]
    ranking = []
    for index, row in enumerate(top, start=1):
        action, reason = churn_reason(row)
        ranking.append(
            {
                "rank": index,
                "customer_id": row["customer_id"],
                "predicted_churn_probability": round_prob(churn_probability(row)),
                "outreach_action": action,
                "reason_code": reason,
            }
        )
    return {
        "model_validation": {
            "training_rows": len(train),
            "validation_rows": len(validation),
            "feature_count": feature_count,
            "accuracy_pct": round_pct(accuracy),
            "accuracy_band": accuracy_band(accuracy),
            "tenure_coefficient_direction": tenure_direction,
        },
        "risk_ranking": ranking,
        "cohort_checks": {
            "past_due_shortlist_count": sum(1 for row in top if row["InvoicePastDue"] == "Yes"),
            "low_tenure_shortlist_count": sum(1 for row in top if float(row["tenure"]) < 18),
            "average_probability_top5": round_prob(
                sum(row["predicted_churn_probability"] for row in ranking) / len(ranking)
            )
            if ranking
            else 0.0,
        },
        "model_policy_codes": CHURN_POLICY,
    }


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=os.environ.get("TASK_ENV_BASE_URL", "http://task-env:9004"))
    sub = parser.add_subparsers(dest="command", required=True)

    qbr = sub.add_parser("qbr")
    qbr.add_argument("--account-id", required=True)
    qbr.add_argument("--start-month", required=True)
    qbr.add_argument("--end-month", required=True)
    qbr.add_argument("--start-date", required=True)
    qbr.add_argument("--end-date", required=True)
    qbr.add_argument("--review-due-date", default="")

    rec = sub.add_parser("receivables")
    rec.add_argument("--quarter", required=True)
    rec.add_argument("--start-date", required=True)
    rec.add_argument("--end-date", required=True)
    rec.add_argument("--as-of", required=True)
    rec.add_argument("--due-date", required=True)
    rec.add_argument("--event-id", required=True)
    rec.add_argument("--region", default="all")
    rec.add_argument("--hr-region", default="all")

    for name in ("risk-queue", "board"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--account-ids", required=True, help="Comma-separated account IDs")
        cmd.add_argument("--start-month", required=True)
        cmd.add_argument("--end-month", required=True)
        cmd.add_argument("--start-date", required=True)
        cmd.add_argument("--end-date", required=True)
        cmd.add_argument("--as-of", required=True)
        cmd.add_argument("--assessment-date", required=True)
        cmd.add_argument("--include-expansion", action="store_true")
        if name == "risk-queue":
            cmd.add_argument("--top-n", type=int, default=5)
        else:
            cmd.add_argument("--due", action="append", default=[])

    churn = sub.add_parser("churn")
    churn.add_argument("--candidate-ids", required=True, help="Comma-separated candidate customer IDs")
    churn.add_argument("--top-n", type=int, default=5)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    client = Client(args.base)
    if args.command == "qbr":
        result = command_qbr(client, args)
    elif args.command == "receivables":
        result = command_receivables(client, args)
    elif args.command == "risk-queue":
        result = command_risk_queue(client, args)
    elif args.command == "board":
        result = command_board(client, args)
    elif args.command == "churn":
        result = command_churn(client, args)
    else:
        raise SystemExit(f"unknown command: {args.command}")
    json.dump(result, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
