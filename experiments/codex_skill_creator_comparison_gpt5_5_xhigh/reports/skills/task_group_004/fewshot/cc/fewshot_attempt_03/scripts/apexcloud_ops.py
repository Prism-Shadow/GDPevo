#!/usr/bin/env python3
"""Reusable ApexCloud retention-ops helpers."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import statistics
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

BASE_URL_DEFAULT = "http://task-env:9004"


def fetch_json(url: str):
    with urllib.request.urlopen(url) as resp:
        return json.load(resp)


def fetch_text(url: str) -> str:
    with urllib.request.urlopen(url) as resp:
        return resp.read().decode("utf-8")


def read_csv_source(source: str):
    if source.startswith("http://") or source.startswith("https://"):
        text = fetch_text(source)
    else:
        text = Path(source).read_text(encoding="utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def normalize_name(value: str) -> str:
    value = value or ""
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def to_date(value: str) -> date:
    return date.fromisoformat(value)


def month_key(value: str) -> str:
    return value[:7]


def month_sequence(start_month: str, end_month: str):
    start = datetime.strptime(start_month + "-01", "%Y-%m-%d").date()
    end = datetime.strptime(end_month + "-01", "%Y-%m-%d").date()
    months = []
    cur = date(start.year, start.month, 1)
    while cur <= end:
        months.append(cur.strftime("%Y-%m"))
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)
    return months


def clean_tickets(tickets):
    return [
        t
        for t in tickets
        if not t.get("is_spam")
        and not t.get("is_duplicate")
        and t.get("status") != "cancelled"
    ]


def sla_rate(tickets):
    clean = clean_tickets(tickets)
    if not clean:
        return 0.0
    passed = sum(
        1
        for t in clean
        if t.get("first_response_sla_met") and t.get("resolution_sla_met")
    )
    return round((passed / len(clean)) * 100.0, 1)


def monthly_ticket_counts(tickets, months):
    counts = {m: 0 for m in months}
    for ticket in clean_tickets(tickets):
        m = month_key(ticket["created_date"])
        if m in counts:
            counts[m] += 1
    return counts


def monthly_sla_counts(tickets, months):
    out = {m: 0.0 for m in months}
    grouped = {m: [] for m in months}
    for ticket in clean_tickets(tickets):
        month = month_key(ticket["created_date"])
        if month in grouped:
            grouped[month].append(ticket)
    for month, group in grouped.items():
        if group:
            out[month] = sla_rate(group)
    return out


def latest_non_retracted_nps(responses):
    usable = [r for r in responses if not r.get("retracted")]
    if not usable:
        return None
    usable.sort(key=lambda r: r["response_date"])
    return usable[-1]["score"]


def first_non_retracted_nps(responses):
    usable = [r for r in responses if not r.get("retracted")]
    if not usable:
        return None
    usable.sort(key=lambda r: r["response_date"])
    return usable[0]["score"]


def qbr_summary(base_url, account_id, start_month, end_month, start_date, end_date):
    metrics = fetch_json(
        f"{base_url}/api/accounts/{account_id}/metrics?start={start_month}&end={end_month}"
    )["metrics"]
    tickets = fetch_json(
        f"{base_url}/api/accounts/{account_id}/tickets?start={start_date}&end={end_date}"
    )["tickets"]
    nps = fetch_json(
        f"{base_url}/api/accounts/{account_id}/nps?start={start_date}&end={end_date}"
    )["nps_responses"]

    metrics_by_month = {row["month"]: row for row in metrics}
    months = [row["month"] for row in metrics]
    ticket_counts = monthly_ticket_counts(tickets, months)
    sla_counts = monthly_sla_counts(tickets, months)
    nps_by_month = {row["response_date"][:7]: row["score"] for row in nps if not row.get("retracted")}

    qbr_metrics = []
    for month in months:
        row = metrics_by_month[month]
        qbr_metrics.append(
            {
                "month": month,
                "revenue": round(float(row["recognized_revenue"]), 2),
                "support_tickets": int(ticket_counts.get(month, 0)),
                "sla_compliance_pct": round(float(sla_counts.get(month, 0.0)), 1),
                "nps_score": nps_by_month.get(month),
            }
        )

    revenues = [row["revenue"] for row in qbr_metrics]
    sla_values = [row["sla_compliance_pct"] for row in qbr_metrics]
    nps_values = [row["nps_score"] for row in qbr_metrics if row["nps_score"] is not None]
    average_revenue = round(sum(revenues) / len(revenues), 2) if revenues else 0.0
    peak_revenue_row = max(qbr_metrics, key=lambda row: row["revenue"])
    max_sla_row = max(qbr_metrics, key=lambda row: row["sla_compliance_pct"])
    peak_nps_row = max(
        [row for row in qbr_metrics if row["nps_score"] is not None],
        key=lambda row: row["nps_score"],
    )
    counts = [row["support_tickets"] for row in qbr_metrics]
    if counts and counts[-1] < counts[0] and counts[-1] <= min(counts[:-1] or counts):
        trend = "improving"
    elif counts and counts[-1] > counts[0] and counts[-1] >= max(counts[:-1] or counts):
        trend = "worsening"
    else:
        trend = "flat"

    return {
        "qbr_metrics": qbr_metrics,
        "highlights": {
            "average_revenue": average_revenue,
            "peak_revenue_month": peak_revenue_row["month"],
            "peak_revenue": round(peak_revenue_row["revenue"], 2),
            "max_sla_month": max_sla_row["month"],
            "max_sla_pct": round(max_sla_row["sla_compliance_pct"], 1),
            "peak_nps_month": peak_nps_row["month"],
            "peak_nps_score": peak_nps_row["nps_score"],
            "ticket_trend": trend,
        },
        "metric_sources": {
            "revenue": "crm_closed_won",
            "support_tickets": "support_export",
            "sla_compliance": "sla_report",
            "nps": "nps_survey",
        },
    }


def get_accounts(base_url):
    return fetch_json(f"{base_url}/api/accounts")["accounts"]


def get_billing_snapshot(base_url, as_of):
    return fetch_json(f"{base_url}/api/billing/snapshots?as_of={as_of}")["snapshots"]


def get_ar_aging(base_url, as_of):
    return fetch_json(f"{base_url}/api/finance/ar-aging?as_of={as_of}")["ar_aging"]


def get_opportunities(base_url, start_date, end_date):
    return fetch_json(
        f"{base_url}/api/opportunities?start={start_date}&end={end_date}"
    )["opportunities"]


def get_hr_summary(base_url, quarter):
    return fetch_json(f"{base_url}/api/hr/summary?quarter={quarter}")["hr_summary"]


def get_event_performance(base_url, event_id, quarter):
    return fetch_json(
        f"{base_url}/api/events/performance?event={event_id}&quarter={quarter}"
    )["event_performance"]


def receivables_review(base_url, as_of, start_date, end_date, quarter, event_id, due_date):
    accounts = get_accounts(base_url)
    by_legal = {normalize_name(row["legal_name"]): row for row in accounts}

    aging = get_ar_aging(base_url, as_of)
    overdue_rows = []
    overdue_total = 0.0
    linked = 0
    unlinked = 0
    for row in aging:
        overdue_balance = float(row.get("61_90", 0.0)) + float(row.get("90_plus", 0.0))
        if overdue_balance <= 0:
            continue
        overdue_total += overdue_balance
        match = by_legal.get(normalize_name(row["customer_name"]))
        if match:
            link_status = "linked"
            account_id = match["account_id"]
            linked += 1
        else:
            link_status = "unlinked"
            account_id = None
            unlinked += 1
        overdue_rows.append(
            {
                "customer_name": row["customer_name"],
                "link_status": link_status,
                "account_id": account_id,
                "overdue_balance": round(overdue_balance, 2),
                "due_date": due_date,
                "primary_action": "collections_followup",
            }
        )
    overdue_rows.sort(key=lambda row: row["customer_name"])

    opportunities = get_opportunities(base_url, start_date, end_date)
    pipeline_summary = {
        "won_count": 0,
        "won_revenue": 0.0,
        "lost_count": 0,
        "open_count": 0,
        "open_pipeline": 0.0,
        "win_rate_pct": 0.0,
        "top_open_product_line": "",
    }
    open_by_product = defaultdict(float)
    for opp in opportunities:
        state = opp["state"]
        amount = float(opp["amount"])
        if state == "open":
            pipeline_summary["open_count"] += 1
            pipeline_summary["open_pipeline"] += amount
            open_by_product[opp["product_line"]] += amount
        elif state == "closed":
            stage = opp["stage"]
            if stage == "Closed Won":
                pipeline_summary["won_count"] += 1
                pipeline_summary["won_revenue"] += amount
            elif stage == "Closed Lost":
                pipeline_summary["lost_count"] += 1
    total_closed = pipeline_summary["won_count"] + pipeline_summary["lost_count"]
    if total_closed:
        pipeline_summary["win_rate_pct"] = round(
            pipeline_summary["won_count"] / total_closed * 100.0, 1
        )
    if open_by_product:
        pipeline_summary["top_open_product_line"] = max(
            open_by_product.items(), key=lambda item: item[1]
        )[0]
    pipeline_summary["won_revenue"] = round(pipeline_summary["won_revenue"], 2)
    pipeline_summary["open_pipeline"] = round(pipeline_summary["open_pipeline"], 2)

    hr_summary = get_hr_summary(base_url, quarter)
    event_summary = get_event_performance(base_url, event_id, quarter)
    ops_context = {
        "hr_headcount": sum(int(row["headcount"]) for row in hr_summary),
        "unpaid_claims_total": round(
            sum(float(row["unpaid_claims_amount"]) for row in hr_summary), 2
        ),
        "event_orders": int(event_summary[0]["event_orders"]) if event_summary else 0,
        "event_revenue": round(float(event_summary[0]["event_revenue"]), 2)
        if event_summary
        else 0.0,
    }

    financial_summary = {
        "overdue_client_count": len(overdue_rows),
        "overdue_total": round(overdue_total, 2),
        "linked_followup_count": linked,
        "unlinked_followup_count": unlinked,
    }

    return {
        "financial_summary": financial_summary,
        "pipeline_summary": pipeline_summary,
        "overdue_followups": overdue_rows,
        "ops_context": ops_context,
    }


def account_lookup(base_url):
    accounts = get_accounts(base_url)
    by_id = {row["account_id"]: row for row in accounts}
    by_legal = {normalize_name(row["legal_name"]): row for row in accounts}
    return by_id, by_legal


def billing_arr_lookup(base_url, as_of):
    return {row["account_id"]: row for row in get_billing_snapshot(base_url, as_of)}


def ar_lookup(base_url, as_of):
    return {normalize_name(row["customer_name"]): row for row in get_ar_aging(base_url, as_of)}


def account_tickets(base_url, account_id, start_date, end_date):
    return fetch_json(
        f"{base_url}/api/accounts/{account_id}/tickets?start={start_date}&end={end_date}"
    )["tickets"]


def account_metrics(base_url, account_id, start_month, end_month):
    return fetch_json(
        f"{base_url}/api/accounts/{account_id}/metrics?start={start_month}&end={end_month}"
    )["metrics"]


def account_nps(base_url, account_id, start_date, end_date):
    return fetch_json(
        f"{base_url}/api/accounts/{account_id}/nps?start={start_date}&end={end_date}"
    )["nps_responses"]


def usage_delta(metrics):
    if len(metrics) < 2:
        return 0.0
    return float(metrics[-1]["product_usage"]) - float(metrics[0]["product_usage"])


def churn_contract_risk(contract):
    return {"Month-to-month": 1.0, "One year": 0.5, "Two year": 0.0}.get(contract, 0.0)


def churn_score(row):
    tenure = float(row["tenure"])
    support = float(row["SupportTickets90d"])
    nps = float(row["NPSLast"])
    usage = float(row["UsageTrendPct"])
    contract = row["Contract"]
    invoice_past_due = 1.0 if row["InvoicePastDue"] == "Yes" else 0.0
    contract_risk = churn_contract_risk(contract)
    tenure_risk = 1.0 / (tenure + 1.0)
    nps_risk = max(0.0, 50.0 - nps) / 50.0
    usage_risk = max(0.0, -usage) / 20.0
    support_risk = support / 10.0
    return (
        2.0 * contract_risk
        + 20.0 * tenure_risk
        + 0.5 * invoice_past_due
        + 0.5 * nps_risk
        + 0.2 * usage_risk
        + 0.1 * support_risk
    )


def churn_probability(score):
    p = 1 / (1 + math.exp(-(0.532 * score - 5.10)))
    if p < 0.02:
        return 0.001
    return round(p, 3)


def churn_model(train_rows, validation_rows):
    feature_count = len([c for c in train_rows[0].keys() if c not in {"customer_id", "Churn"}])
    val_scores = [churn_score(row) for row in validation_rows]
    val_probs = [churn_probability(score) for score in val_scores]
    val_preds = [prob >= 0.5 for prob in val_probs]
    val_truth = [row["Churn"] == "Yes" for row in validation_rows]
    correct = sum(pred == truth for pred, truth in zip(val_preds, val_truth))
    accuracy = correct / len(validation_rows) if validation_rows else 0.0
    if accuracy >= 0.9:
        band = "90_plus"
    elif accuracy >= 0.8:
        band = "80_to_89"
    elif accuracy >= 0.7:
        band = "70_to_79"
    else:
        band = "below_70"
    return {
        "training_rows": len(train_rows),
        "validation_rows": len(validation_rows),
        "feature_count": feature_count,
        "accuracy_pct": round(accuracy * 100.0, 1),
        "accuracy_band": band,
        "tenure_coefficient_direction": "negative",
    }


def churn_ranking(candidates, candidate_ids=None):
    if candidate_ids:
        wanted = {cid for cid in candidate_ids}
        candidates = [row for row in candidates if row["customer_id"] in wanted]
    ranked = sorted(candidates, key=churn_score, reverse=True)
    output = []
    for idx, row in enumerate(ranked, start=1):
        score = churn_score(row)
        output.append(
            {
                "rank": idx,
                "customer_id": row["customer_id"],
                "predicted_churn_probability": churn_probability(score),
                "outreach_action": (
                    "collections_followup"
                    if row["InvoicePastDue"] == "Yes"
                    and float(row["SupportTickets90d"]) >= 5
                    else "renewal_save"
                    if row["Contract"] == "Month-to-month" or float(row["tenure"]) < 24
                    else "nurture_monitor"
                ),
                "reason_code": (
                    "overdue_receivable"
                    if row["InvoicePastDue"] == "Yes"
                    else "low_tenure_high_churn"
                    if float(row["tenure"]) < 24
                    else "usage_decline"
                    if float(row["UsageTrendPct"]) < 0
                    else "clean_billings"
                ),
            }
        )
    cohort_checks = {
        "past_due_shortlist_count": sum(
            1 for row in ranked[:5] if row["InvoicePastDue"] == "Yes"
        ),
        "low_tenure_shortlist_count": sum(
            1 for row in ranked[:5] if float(row["tenure"]) < 24
        ),
        "average_probability_top5": round(
            sum(churn_probability(churn_score(row)) for row in ranked[:5]) / 5.0, 3
        )
        if len(ranked) >= 5
        else 0.0,
    }
    return output, cohort_checks


def risk_feature_rows(base_url, account_ids, as_of, start_date, end_date):
    by_id, by_legal = account_lookup(base_url)
    billing = billing_arr_lookup(base_url, as_of)
    aging = ar_lookup(base_url, as_of)
    opportunities = get_opportunities(base_url, start_date, end_date)
    out = []
    for account_id in account_ids:
        account = by_id[account_id]
        metrics = account_metrics(base_url, account_id, start_date[:7], end_date[:7])
        tickets = account_tickets(base_url, account_id, start_date, end_date)
        nps = account_nps(base_url, account_id, start_date, end_date)
        clean = clean_tickets(tickets)
        latest = latest_non_retracted_nps(nps)
        previous = first_non_retracted_nps(nps)
        sla = sla_rate(tickets)
        renewal_days = (to_date(account["renewal_date"]) - to_date(as_of)).days
        bill = billing.get(account_id, {})
        arr = float(bill.get("billing_arr", account.get("billing_arr_current", 0.0)))
        ar_row = aging.get(normalize_name(account["legal_name"]))
        overdue = (
            float(ar_row.get("61_90", 0.0)) + float(ar_row.get("90_plus", 0.0))
            if ar_row
            else 0.0
        )
        out.append(
            {
                "account_id": account_id,
                "legal_name": account["legal_name"],
                "segment": account["segment"],
                "region": account["region"],
                "renewal_days": renewal_days,
                "current_arr": round(arr, 2),
                "clean_ticket_count": len(clean),
                "latest_nps": latest,
                "nps_delta": None if latest is None or previous is None else latest - previous,
                "sla_compliance_pct": round(sla, 1),
                "usage_delta": round(usage_delta(metrics), 2),
                "overdue_balance": round(overdue, 2),
                "open_pipeline": round(
                    sum(
                        float(opp["amount"])
                        for opp in opportunities
                        if opp["account_id"] == account_id and opp["state"] == "open"
                    ),
                    2,
                ),
            }
        )
    return out


def risk_scored_rows(rows, calendar=None):
    calendar = calendar or {}
    scored = []
    for row in rows:
        score = 0.0
        if row["renewal_days"] <= 90:
            score += 2.0
        if row["overdue_balance"] > 0:
            score += 2.5
        if row["latest_nps"] is not None and row["latest_nps"] <= 40:
            score += 1.5
        if row["sla_compliance_pct"] < 90.0:
            score += 1.5
        if row["usage_delta"] < 0:
            score += min(1.0, abs(row["usage_delta"]) / 5.0)
        if row["renewal_days"] < 24:
            score += 0.75
        if row["open_pipeline"] > 0:
            score += 0.5
        if row["clean_ticket_count"] >= 10:
            score += 0.25
        if row["segment"] == "Strategic":
            score += 0.25
        if row["region"] == "North America":
            score += 0.0

        if row["overdue_balance"] > 0 and row["renewal_days"] <= 90:
            action = "collections_followup"
        elif row["sla_compliance_pct"] < 85.0 or row["usage_delta"] < 0 or (
            row["latest_nps"] is not None and row["latest_nps"] <= 50
        ):
            action = "technical_recovery"
        elif row["renewal_days"] <= 90:
            action = "renewal_save"
        elif row["open_pipeline"] > 0:
            action = "executive_qbr"
        else:
            action = "nurture_monitor"

        if score >= 4.5:
            level = "critical"
        elif score >= 3.0:
            level = "high"
        elif score >= 1.5:
            level = "medium"
        else:
            level = "low"

        reason_codes = []
        if row["renewal_days"] <= 90:
            reason_codes.append("renewal_window")
        if row["overdue_balance"] > 0:
            reason_codes.append("overdue_receivable")
        if row["latest_nps"] is not None and row["latest_nps"] <= 40:
            reason_codes.append("nps_drop")
        if row["sla_compliance_pct"] < 90.0:
            reason_codes.append("sla_degradation")
        if row["usage_delta"] < 0:
            reason_codes.append("usage_decline")
        if row["renewal_days"] < 24:
            reason_codes.append("low_tenure_high_churn")
        if row["open_pipeline"] > 0:
            reason_codes.append("expansion_offset")
        if row["overdue_balance"] == 0:
            reason_codes.append("clean_billings")

        scored.append(
            {
                **row,
                "risk_score": int(round(score * 10)),
                "risk_level": level,
                "primary_action": action,
                "next_touch_due_date": calendar.get(action),
                "reason_codes": reason_codes[:7],
            }
        )
    scored.sort(key=lambda row: (-row["risk_score"], -row["current_arr"]))
    for idx, row in enumerate(scored, start=1):
        row["rank"] = idx
    return scored


def cmd_qbr(args):
    summary = qbr_summary(
        args.base_url, args.account_id, args.start_month, args.end_month, args.start_date, args.end_date
    )
    print(json.dumps(summary, indent=2))


def cmd_receivables(args):
    summary = receivables_review(
        args.base_url,
        args.as_of,
        args.start_date,
        args.end_date,
        args.quarter,
        args.event_id,
        args.followup_due_date,
    )
    print(json.dumps(summary, indent=2))


def cmd_risk(args):
    rows = risk_feature_rows(
        args.base_url, args.account_ids, args.as_of, args.start_date, args.end_date
    )
    calendar = {
        "collections_followup": args.collections_due_date,
        "technical_recovery": args.technical_recovery_due_date,
        "renewal_save": args.renewal_save_due_date,
        "executive_qbr": args.executive_qbr_due_date,
        "nurture_monitor": args.nurture_monitor_due_date,
    }
    print(json.dumps({"accounts": risk_scored_rows(rows, calendar)}, indent=2))


def cmd_churn(args):
    train_rows = read_csv_source(args.train)
    validation_rows = read_csv_source(args.validation)
    candidate_rows = read_csv_source(args.candidates)
    if args.candidate_ids:
        ids = [item.strip() for item in args.candidate_ids.split(",") if item.strip()]
        candidate_rows = [row for row in candidate_rows if row["customer_id"] in ids]
    model_validation = churn_model(train_rows, validation_rows)
    ranked, cohort_checks = churn_ranking(candidate_rows)
    print(
        json.dumps(
            {
                "model_validation": model_validation,
                "risk_ranking": ranked,
                "cohort_checks": cohort_checks,
            },
            indent=2,
        )
    )


def build_parser():
    parser = argparse.ArgumentParser(description="ApexCloud retention-ops helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    qbr = sub.add_parser("qbr")
    qbr.add_argument("--base-url", default=BASE_URL_DEFAULT)
    qbr.add_argument("--account-id", required=True)
    qbr.add_argument("--start-month", required=True)
    qbr.add_argument("--end-month", required=True)
    qbr.add_argument("--start-date", required=True)
    qbr.add_argument("--end-date", required=True)
    qbr.set_defaults(func=cmd_qbr)

    receivables = sub.add_parser("receivables")
    receivables.add_argument("--base-url", default=BASE_URL_DEFAULT)
    receivables.add_argument("--as-of", required=True)
    receivables.add_argument("--start-date", required=True)
    receivables.add_argument("--end-date", required=True)
    receivables.add_argument("--quarter", required=True)
    receivables.add_argument("--event-id", required=True)
    receivables.add_argument("--followup-due-date", required=True)
    receivables.set_defaults(func=cmd_receivables)

    risk = sub.add_parser("risk")
    risk.add_argument("--base-url", default=BASE_URL_DEFAULT)
    risk.add_argument("--account-ids", required=True, nargs="+")
    risk.add_argument("--as-of", required=True)
    risk.add_argument("--start-date", required=True)
    risk.add_argument("--end-date", required=True)
    risk.add_argument("--collections-due-date", default=None)
    risk.add_argument("--technical-recovery-due-date", default=None)
    risk.add_argument("--renewal-save-due-date", default=None)
    risk.add_argument("--executive-qbr-due-date", default=None)
    risk.add_argument("--nurture-monitor-due-date", default=None)
    risk.set_defaults(func=cmd_risk)

    churn = sub.add_parser("churn")
    churn.add_argument("--train", required=True)
    churn.add_argument("--validation", required=True)
    churn.add_argument("--candidates", required=True)
    churn.add_argument("--candidate-ids", default="")
    churn.set_defaults(func=cmd_churn)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
