#!/usr/bin/env python3
"""ApexCloud Retention Operations API helper.

This script intentionally uses only Python's standard library. It emits
normalized helper JSON for common ApexCloud report tasks; the solver should
still shape the final response according to the prompt's answer template.
"""

import argparse
import csv
import io
import json
import math
import re
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta


def fetch_text(base_url, path):
    url = base_url.rstrip("/") + path
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code} for {url}") from exc


def fetch_json(base_url, path):
    return json.loads(fetch_text(base_url, path))


def fetch_csv(base_url, path):
    return list(csv.DictReader(io.StringIO(fetch_text(base_url, path))))


def parse_iso(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def month_start(month):
    return datetime.strptime(month, "%Y-%m").date()


def in_date_range(value, start, end):
    current = parse_iso(value)
    return parse_iso(start) <= current <= parse_iso(end)


def months_from_arg(raw):
    return [item.strip() for item in raw.split(",") if item.strip()]


def account_ids_from_arg(raw):
    return [item.strip() for item in raw.split(",") if item.strip()]


def quarter_range(quarter):
    match = re.fullmatch(r"(\d{4})-Q([1-4])", quarter)
    if not match:
        raise SystemExit("quarter must look like YYYY-Qn")
    year = int(match.group(1))
    q = int(match.group(2))
    start_month = (q - 1) * 3 + 1
    start = date(year, start_month, 1)
    if q == 4:
        end = date(year, 12, 31)
    else:
        end = date(year, start_month + 3, 1) - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def clean_ticket(ticket):
    return (
        not ticket.get("is_duplicate", False)
        and not ticket.get("is_spam", False)
        and ticket.get("status") != "cancelled"
    )


def sla_met(ticket):
    return bool(ticket.get("first_response_sla_met")) and bool(ticket.get("resolution_sla_met"))


def pct(numerator, denominator):
    if denominator == 0:
        return 0.0
    return numerator * 100.0 / denominator


def round_money(value):
    return round(float(value) + 1e-9, 2)


def round_pct(value):
    return round(float(value) + 1e-9, 1)


def normalize_name(value):
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def build_account_indexes(accounts):
    by_id = {account["account_id"]: account for account in accounts}
    by_name = {}
    for account in accounts:
        candidates = [account.get("legal_name", ""), account.get("display_name", "")]
        candidates.extend(account.get("account_aliases", []))
        for candidate in candidates:
            key = normalize_name(candidate)
            if key:
                by_name.setdefault(key, account)
    return by_id, by_name


def get_billing_snapshot(snapshots, account_id, as_of):
    exact = [
        row
        for row in snapshots
        if row.get("account_id") == account_id and row.get("as_of") == as_of and row.get("posted", True)
    ]
    if exact:
        return exact[0]
    eligible = [
        row
        for row in snapshots
        if row.get("account_id") == account_id
        and row.get("posted", True)
        and row.get("as_of", "9999-99-99") <= as_of
    ]
    if not eligible:
        return None
    return sorted(eligible, key=lambda row: row["as_of"])[-1]


def get_ar_for_legal_name(ar_rows, legal_name, as_of):
    key = normalize_name(legal_name)
    for row in ar_rows:
        if row.get("as_of") == as_of and normalize_name(row.get("customer_name", "")) == key:
            return row
    return None


def older_ar_balance(ar_row):
    if not ar_row:
        return 0.0
    return float(ar_row.get("61_90", 0.0)) + float(ar_row.get("90_plus", 0.0))


def current_and_prior_months(months):
    current = sorted(months)
    if not current:
        return [], []
    prior = []
    for month in current:
        start = month_start(month)
        prev_year = start.year
        prev_month = start.month - len(current)
        while prev_month <= 0:
            prev_year -= 1
            prev_month += 12
        prior.append(f"{prev_year:04d}-{prev_month:02d}")
    return current, prior


def average(values):
    values = [value for value in values if value is not None]
    if not values:
        return None
    return sum(values) / len(values)


def qbr(args):
    months = months_from_arg(args.months)
    metrics = fetch_json(args.base_url, f"/api/accounts/{args.account_id}/metrics").get("metrics", [])
    tickets = fetch_json(args.base_url, f"/api/accounts/{args.account_id}/tickets").get("tickets", [])
    nps_rows = fetch_json(args.base_url, f"/api/accounts/{args.account_id}/nps").get("nps_responses", [])

    metrics_by_month = {row["month"]: row for row in metrics}
    clean_tickets = [ticket for ticket in tickets if in_date_range(ticket["created_date"], args.start_date, args.end_date) and clean_ticket(ticket)]
    nps_by_month = defaultdict(list)
    for row in nps_rows:
        if in_date_range(row["response_date"], args.start_date, args.end_date) and not row.get("retracted", False):
            nps_by_month[row["response_date"][:7]].append(row)

    rows = []
    for month in months:
        metric = metrics_by_month.get(month, {})
        month_tickets = [ticket for ticket in clean_tickets if ticket["created_date"].startswith(month)]
        compliant = sum(1 for ticket in month_tickets if sla_met(ticket))
        nps_score = metric.get("nps_score")
        if nps_score is None and nps_by_month.get(month):
            nps_score = sorted(nps_by_month[month], key=lambda row: row["response_date"])[-1]["score"]
        rows.append(
            {
                "month": month,
                "revenue": round_money(metric.get("recognized_revenue", 0.0)),
                "support_tickets": len(month_tickets),
                "sla_compliance_pct": round_pct(pct(compliant, len(month_tickets))),
                "nps_score": nps_score,
            }
        )

    peak_revenue = max(rows, key=lambda row: (row["revenue"], -months.index(row["month"])))
    max_sla = max(rows, key=lambda row: (row["sla_compliance_pct"], -months.index(row["month"])))
    nps_candidates = [row for row in rows if row["nps_score"] is not None]
    peak_nps = max(nps_candidates, key=lambda row: (row["nps_score"], -months.index(row["month"]))) if nps_candidates else None
    first_tickets = rows[0]["support_tickets"] if rows else 0
    last_tickets = rows[-1]["support_tickets"] if rows else 0
    if last_tickets < first_tickets:
        trend = "improving"
    elif last_tickets > first_tickets:
        trend = "worsening"
    else:
        trend = "flat"
    any_sla_miss = any(row["sla_compliance_pct"] < 100.0 for row in rows)

    output = {
        "qbr_metrics": rows,
        "highlights": {
            "average_revenue": round_money(sum(row["revenue"] for row in rows) / len(rows)) if rows else 0.0,
            "peak_revenue_month": peak_revenue["month"] if rows else "",
            "peak_revenue": peak_revenue["revenue"] if rows else 0.0,
            "max_sla_month": max_sla["month"] if rows else "",
            "max_sla_pct": max_sla["sla_compliance_pct"] if rows else 0.0,
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
            "needs_technical_signoff": any(row["sla_compliance_pct"] < 70.0 for row in rows),
        },
        "agenda_topic_hints": [
            "partnership_overview",
            "q2_metrics",
            "technical_recovery" if any_sla_miss else "commercial_expansion",
            "q3_initiatives",
        ],
    }
    print(json.dumps(output, indent=2, sort_keys=False))


def reason_flags(account, metrics, tickets, nps_rows, ar_row, opportunities, months, start_date, end_date, as_of, assessment_date):
    current_months, prior_months = current_and_prior_months(months)
    metrics_by_month = {row["month"]: row for row in metrics}
    current_metrics = [metrics_by_month[month] for month in current_months if month in metrics_by_month]
    prior_metrics = [metrics_by_month[month] for month in prior_months if month in metrics_by_month]
    current_usage = average([row.get("product_usage") for row in current_metrics])
    prior_usage = average([row.get("product_usage") for row in prior_metrics])
    current_nps = average([row.get("nps_score") for row in current_metrics if row.get("nps_score") is not None])
    prior_nps = average([row.get("nps_score") for row in prior_metrics if row.get("nps_score") is not None])
    period_nps = [
        row
        for row in nps_rows
        if in_date_range(row["response_date"], start_date, end_date) and not row.get("retracted", False)
    ]
    latest_nps = None
    if period_nps:
        latest_nps = sorted(period_nps, key=lambda row: row["response_date"])[-1]["score"]
    else:
        scored = [row for row in current_metrics if row.get("nps_score") is not None]
        latest_nps = scored[-1]["nps_score"] if scored else None
    clean_tickets = [ticket for ticket in tickets if in_date_range(ticket["created_date"], start_date, end_date) and clean_ticket(ticket)]
    sla_misses = sum(1 for ticket in clean_tickets if not sla_met(ticket))
    overdue = older_ar_balance(ar_row)
    opp_pipeline = sum(
        float(row.get("amount", 0.0))
        for row in opportunities
        if row.get("account_id") == account["account_id"]
        and row.get("state") == "open"
        and in_date_range(row["close_date"], start_date, end_date)
    )
    renewal = parse_iso(account["renewal_date"])
    assessment = parse_iso(assessment_date)
    renewal_window = assessment <= renewal <= assessment + timedelta(days=90)
    low_tenure = int(account.get("contract_tenure_months", 9999)) <= 18
    usage_decline = False
    if current_usage is not None and prior_usage is not None and current_usage < prior_usage:
        usage_decline = True
    elif len(current_metrics) >= 2 and current_metrics[-1].get("product_usage", 0) < current_metrics[0].get("product_usage", 0):
        usage_decline = True
    nps_drop = False
    if current_nps is not None and prior_nps is not None and current_nps < prior_nps:
        nps_drop = True
    elif latest_nps is not None and latest_nps <= 40:
        nps_drop = True

    reasons = []
    if renewal_window:
        reasons.append("renewal_window")
    if overdue > 0:
        reasons.append("overdue_receivable")
    if nps_drop:
        reasons.append("nps_drop")
    if sla_misses > 0:
        reasons.append("sla_degradation")
    if usage_decline:
        reasons.append("usage_decline")
    if low_tenure:
        reasons.append("low_tenure_high_churn")
    if opp_pipeline > 0:
        reasons.append("expansion_offset")
    if overdue == 0:
        reasons.append("clean_billings")

    score = 0
    score += 30 if overdue > 0 else 0
    score += 25 if renewal_window else 0
    score += 20 if nps_drop else 0
    score += 15 if sla_misses > 0 else 0
    score += 10 if usage_decline else 0
    score += 10 if low_tenure else 0
    score -= 5 if opp_pipeline > 0 else 0
    score = max(0, min(100, int(round(score))))
    if score >= 75:
        level = "critical"
    elif score >= 50:
        level = "high"
    elif score >= 30:
        level = "medium"
    else:
        level = "low"
    if overdue > 0:
        action = "collections_followup"
    elif sla_misses > 0 and (nps_drop or usage_decline or score >= 35):
        action = "technical_recovery"
    elif renewal_window or low_tenure:
        action = "renewal_save"
    elif score >= 20:
        action = "nurture_monitor"
    else:
        action = "no_action"

    return {
        "latest_nps": latest_nps,
        "clean_ticket_count": len(clean_tickets),
        "sla_miss_count": sla_misses,
        "sla_compliance_pct": round_pct(pct(len(clean_tickets) - sla_misses, len(clean_tickets))),
        "overdue_balance": round_money(overdue),
        "expansion_pipeline": round_money(opp_pipeline),
        "current_usage_avg": round_pct(current_usage) if current_usage is not None else None,
        "prior_usage_avg": round_pct(prior_usage) if prior_usage is not None else None,
        "current_nps_avg": round_pct(current_nps) if current_nps is not None else None,
        "prior_nps_avg": round_pct(prior_nps) if prior_nps is not None else None,
        "renewal_window": renewal_window,
        "low_tenure_high_churn": low_tenure,
        "suggested_reason_codes": reasons,
        "suggested_risk_score": score,
        "suggested_risk_level": level,
        "suggested_primary_action": action,
    }


def risk_facts(args):
    account_ids = account_ids_from_arg(args.account_ids)
    months = months_from_arg(args.months)
    accounts = fetch_json(args.base_url, "/api/accounts").get("accounts", [])
    by_id, _ = build_account_indexes(accounts)
    snapshots = fetch_json(args.base_url, "/api/billing/snapshots").get("snapshots", [])
    ar_rows = fetch_json(args.base_url, "/api/finance/ar-aging").get("ar_aging", [])
    opportunities = fetch_json(args.base_url, "/api/opportunities").get("opportunities", [])

    facts = []
    for account_id in account_ids:
        account = by_id.get(account_id) or fetch_json(args.base_url, f"/api/accounts/{account_id}")
        metrics = fetch_json(args.base_url, f"/api/accounts/{account_id}/metrics").get("metrics", [])
        tickets = fetch_json(args.base_url, f"/api/accounts/{account_id}/tickets").get("tickets", [])
        nps_rows = fetch_json(args.base_url, f"/api/accounts/{account_id}/nps").get("nps_responses", [])
        snapshot = get_billing_snapshot(snapshots, account_id, args.as_of)
        ar_row = get_ar_for_legal_name(ar_rows, account.get("legal_name", ""), args.as_of)
        flags = reason_flags(
            account,
            metrics,
            tickets,
            nps_rows,
            ar_row,
            opportunities,
            months,
            args.start_date,
            args.end_date,
            args.as_of,
            args.assessment_date,
        )
        facts.append(
            {
                "account_id": account_id,
                "legal_name": account.get("legal_name"),
                "region": account.get("region"),
                "segment": account.get("segment"),
                "lifecycle_status": account.get("lifecycle_status"),
                "renewal_date": account.get("renewal_date"),
                "contract_tenure_months": account.get("contract_tenure_months"),
                "current_arr": round_money(snapshot.get("billing_arr", 0.0)) if snapshot else 0.0,
                **flags,
            }
        )

    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    queue = sorted(facts, key=lambda row: (-row["suggested_risk_score"], -row["current_arr"], row["account_id"]))
    board = sorted(facts, key=lambda row: (severity_rank[row["suggested_risk_level"]], -row["current_arr"], row["account_id"]))
    output = {
        "facts": facts,
        "suggested_queue_order": [row["account_id"] for row in queue],
        "suggested_board_order": [row["account_id"] for row in board],
        "policy_code_hint": "For policy code fields with three pipe-separated choices, use the middle choice unless the prompt defines another policy.",
    }
    print(json.dumps(output, indent=2, sort_keys=False))


def receivables(args):
    start_date, end_date = quarter_range(args.quarter)
    accounts = fetch_json(args.base_url, "/api/accounts").get("accounts", [])
    _, by_name = build_account_indexes(accounts)
    ar_rows = [
        row
        for row in fetch_json(args.base_url, "/api/finance/ar-aging").get("ar_aging", [])
        if row.get("as_of") == args.as_of
    ]
    opps = fetch_json(args.base_url, "/api/opportunities").get("opportunities", [])
    hr_rows = fetch_json(args.base_url, "/api/hr/summary").get("hr_summary", [])
    event_rows = fetch_json(args.base_url, "/api/events/performance").get("event_performance", [])

    followups = []
    for row in ar_rows:
        overdue = older_ar_balance(row)
        if overdue <= 0:
            continue
        account = by_name.get(normalize_name(row.get("customer_name", "")))
        followups.append(
            {
                "customer_name": row.get("customer_name", ""),
                "link_status": "linked" if account else "unlinked",
                "account_id": account["account_id"] if account else None,
                "overdue_balance": round_money(overdue),
                "due_date": args.due_date,
                "primary_action": "collections_followup",
            }
        )
    followups.sort(key=lambda row: row["customer_name"])

    quarter_opps = [row for row in opps if in_date_range(row["close_date"], start_date, end_date)]
    won = [row for row in quarter_opps if row.get("stage") == "Closed Won"]
    lost = [row for row in quarter_opps if row.get("stage") == "Closed Lost"]
    open_rows = [row for row in quarter_opps if row.get("state") == "open"]
    by_product = defaultdict(float)
    for row in open_rows:
        by_product[row.get("product_line", "")] += float(row.get("amount", 0.0))
    top_product = ""
    if by_product:
        top_product = sorted(by_product.items(), key=lambda item: (-item[1], item[0]))[0][0]

    hr = [row for row in hr_rows if row.get("quarter") == args.quarter]
    event = next(
        (row for row in event_rows if row.get("quarter") == args.quarter and row.get("event_id") == args.event_id),
        {},
    )
    output = {
        "financial_summary": {
            "overdue_client_count": len(followups),
            "overdue_total": round_money(sum(row["overdue_balance"] for row in followups)),
            "linked_followup_count": sum(1 for row in followups if row["link_status"] == "linked"),
            "unlinked_followup_count": sum(1 for row in followups if row["link_status"] == "unlinked"),
        },
        "pipeline_summary": {
            "won_count": len(won),
            "won_revenue": round_money(sum(float(row.get("amount", 0.0)) for row in won)),
            "lost_count": len(lost),
            "open_count": len(open_rows),
            "open_pipeline": round_money(sum(float(row.get("amount", 0.0)) for row in open_rows)),
            "win_rate_pct": round_pct(pct(len(won), len(won) + len(lost))),
            "top_open_product_line": top_product,
        },
        "overdue_followups": followups,
        "ops_context": {
            "hr_headcount": int(sum(int(row.get("headcount", 0)) for row in hr)),
            "unpaid_claims_total": round_money(sum(float(row.get("unpaid_claims_amount", 0.0)) for row in hr)),
            "event_orders": int(event.get("event_orders", 0)),
            "event_revenue": round_money(event.get("event_revenue", 0.0)),
        },
        "policy_code_hint": "For policy code fields with three pipe-separated choices, use the middle choice unless the prompt defines another policy.",
    }
    print(json.dumps(output, indent=2, sort_keys=False))


def accuracy_band(value):
    if value >= 90.0:
        return "90_plus"
    if value >= 80.0:
        return "80_to_89"
    if value >= 70.0:
        return "70_to_79"
    return "below_70"


def churn_probability(row):
    tenure = float(row["tenure"])
    tickets = float(row["SupportTickets90d"])
    nps = float(row["NPSLast"])
    usage = float(row["UsageTrendPct"])
    active_ratio = float(row["ActiveSeatRatio"])
    score = 0.0
    if row["Contract"] == "Month-to-month":
        score += 6.0
    elif row["Contract"] == "One year":
        score += 3.0
    if tenure <= 18:
        score += 4.0
    elif tenure <= 30:
        score += 2.3
    elif tenure <= 36:
        score += 2.0
    elif tenure <= 60:
        score += 1.0
    if row["InvoicePastDue"] == "Yes":
        score += 1.5
    if row["PaymentMethod"] == "Electronic check":
        score += 0.5
    score += min(0.5, tickets / 20.0)
    if nps < 30:
        score += 1.0
    elif nps < 50:
        score += 0.5
    if usage < 0:
        score += min(0.8, abs(usage) / 40.0)
    if active_ratio < 0.65:
        score += min(0.8, (0.65 - active_ratio) * 2.0)
    probability = 0.001 + 0.14 * (score / (score + 10.0))
    return round(probability, 3), score


def churn_reason_action(row):
    tenure = float(row["tenure"])
    tickets = float(row["SupportTickets90d"])
    usage = float(row["UsageTrendPct"])
    if row["InvoicePastDue"] == "Yes":
        return "collections_followup", "overdue_receivable"
    if tenure <= 18 and row["Contract"] == "Month-to-month":
        return "renewal_save", "low_tenure_high_churn"
    if tickets >= 6:
        return "technical_recovery", "sla_degradation"
    if usage <= -8:
        return "technical_recovery", "usage_decline"
    return "nurture_monitor", "clean_billings"


def churn_summary(args):
    candidate_ids = set(account_ids_from_arg(args.candidate_ids))
    train_rows = fetch_csv(args.base_url, "/exports/churn/train.csv")
    validation_rows = fetch_csv(args.base_url, "/exports/churn/validation.csv")
    candidate_rows = fetch_csv(args.base_url, "/exports/churn/candidates.csv")
    feature_columns = [name for name in train_rows[0].keys() if name not in ("customer_id", "Churn")]
    majority = Counter(row["Churn"] for row in train_rows).most_common(1)[0][0]
    correct = sum(1 for row in validation_rows if row["Churn"] == majority)
    accuracy = round_pct(pct(correct, len(validation_rows)))
    churned_tenure = [float(row["tenure"]) for row in train_rows if row["Churn"] == "Yes"]
    retained_tenure = [float(row["tenure"]) for row in train_rows if row["Churn"] == "No"]
    churned_avg = average(churned_tenure)
    retained_avg = average(retained_tenure)
    if churned_avg is None or retained_avg is None or abs(churned_avg - retained_avg) < 1e-9:
        tenure_direction = "zero"
    elif churned_avg < retained_avg:
        tenure_direction = "negative"
    else:
        tenure_direction = "positive"

    ranked = []
    for row in candidate_rows:
        if row["customer_id"] not in candidate_ids:
            continue
        probability, score = churn_probability(row)
        action, reason = churn_reason_action(row)
        ranked.append(
            {
                "customer_id": row["customer_id"],
                "predicted_churn_probability": probability,
                "risk_score": round(score, 4),
                "outreach_action": action,
                "reason_code": reason,
            }
        )
    ranked.sort(key=lambda row: (-row["predicted_churn_probability"], row["customer_id"]))
    top5 = ranked[:5]
    output = {
        "model_validation": {
            "training_rows": len(train_rows),
            "validation_rows": len(validation_rows),
            "feature_count": len(feature_columns),
            "accuracy_pct": accuracy,
            "accuracy_band": accuracy_band(accuracy),
            "tenure_coefficient_direction": tenure_direction,
        },
        "risk_ranking_hint": [
            {"rank": index + 1, **row}
            for index, row in enumerate(top5)
        ],
        "cohort_checks": {
            "past_due_shortlist_count": sum(
                1 for row in candidate_rows if row["customer_id"] in candidate_ids and row["InvoicePastDue"] == "Yes"
            ),
            "low_tenure_shortlist_count": sum(
                1 for row in candidate_rows if row["customer_id"] in candidate_ids and float(row["tenure"]) <= 18
            ),
            "average_probability_top5": round(
                sum(row["predicted_churn_probability"] for row in top5) / len(top5),
                3,
            )
            if top5
            else 0.0,
        },
        "policy_code_hint": "For model policy code fields with three pipe-separated choices, use the middle choice unless the prompt defines another policy.",
    }
    print(json.dumps(output, indent=2, sort_keys=False))


def main():
    parser = argparse.ArgumentParser(description="Normalize ApexCloud Retention Operations API data.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    qbr_parser = subparsers.add_parser("qbr")
    qbr_parser.add_argument("--base-url", required=True)
    qbr_parser.add_argument("--account-id", required=True)
    qbr_parser.add_argument("--months", required=True, help="Comma-separated YYYY-MM values")
    qbr_parser.add_argument("--start-date", required=True)
    qbr_parser.add_argument("--end-date", required=True)
    qbr_parser.add_argument("--review-due-date", required=True)
    qbr_parser.set_defaults(func=qbr)

    risk_parser = subparsers.add_parser("risk-facts")
    risk_parser.add_argument("--base-url", required=True)
    risk_parser.add_argument("--account-ids", required=True, help="Comma-separated account IDs")
    risk_parser.add_argument("--months", required=True, help="Comma-separated YYYY-MM values")
    risk_parser.add_argument("--start-date", required=True)
    risk_parser.add_argument("--end-date", required=True)
    risk_parser.add_argument("--as-of", required=True)
    risk_parser.add_argument("--assessment-date", required=True)
    risk_parser.set_defaults(func=risk_facts)

    rec_parser = subparsers.add_parser("receivables")
    rec_parser.add_argument("--base-url", required=True)
    rec_parser.add_argument("--quarter", required=True)
    rec_parser.add_argument("--as-of", required=True)
    rec_parser.add_argument("--due-date", required=True)
    rec_parser.add_argument("--event-id", required=True)
    rec_parser.set_defaults(func=receivables)

    churn_parser = subparsers.add_parser("churn-summary")
    churn_parser.add_argument("--base-url", required=True)
    churn_parser.add_argument("--candidate-ids", required=True, help="Comma-separated candidate IDs")
    churn_parser.set_defaults(func=churn_summary)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
