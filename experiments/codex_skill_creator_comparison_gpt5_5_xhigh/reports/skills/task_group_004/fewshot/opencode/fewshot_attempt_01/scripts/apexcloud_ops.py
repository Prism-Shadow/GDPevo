#!/usr/bin/env python3
"""Standard-library helpers for ApexCloud Retention Operations API tasks."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import statistics
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date


NUMERIC_CHURN_COLUMNS = [
    "tenure",
    "MonthlyCharges",
    "TotalCharges",
    "SupportTickets90d",
    "NPSLast",
    "UsageTrendPct",
    "ActiveSeatRatio",
]

CATEGORICAL_CHURN_COLUMNS = [
    "Contract",
    "PaymentMethod",
    "PaperlessBilling",
    "Partner",
    "Dependents",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "InvoicePastDue",
]

CHURN_MODEL_NUMERIC_COLUMNS = ["tenure", "MonthlyCharges", "TotalCharges"]
CHURN_MODEL_CATEGORICAL_COLUMNS = ["Contract", "PaymentMethod", "InvoicePastDue"]


def fetch_json(base_url: str, path: str, params: dict[str, str] | None = None) -> dict:
    url = base_url.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as response:
        return json.load(response)


def fetch_csv(base_url: str, path: str) -> list[dict[str, str]]:
    url = base_url.rstrip("/") + path
    with urllib.request.urlopen(url) as response:
        text = response.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def clean_tickets(tickets: list[dict]) -> list[dict]:
    return [
        ticket
        for ticket in tickets
        if not ticket.get("is_duplicate")
        and not ticket.get("is_spam")
        and ticket.get("status") != "cancelled"
    ]


def older_overdue(row: dict) -> float:
    return round(float(row.get("61_90", 0) or 0) + float(row.get("90_plus", 0) or 0), 2)


def risk_level(score: int) -> str:
    if score >= 70:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def parse_ids(raw: str) -> list[str]:
    return [item.strip() for item in raw.replace("\n", ",").split(",") if item.strip()]


def date_month(value: str) -> str:
    return value[:7]


def load_common(base_url: str, as_of: str, opp_start: str | None, opp_end: str | None):
    accounts = fetch_json(base_url, "/api/accounts")["accounts"]
    account_by_id = {account["account_id"]: account for account in accounts}
    account_by_legal = {account["legal_name"]: account for account in accounts}
    snapshots = fetch_json(base_url, "/api/billing/snapshots", {"as_of": as_of})["snapshots"]
    billing_by_id = {row["account_id"]: row for row in snapshots if row.get("posted", True)}
    ar_rows = fetch_json(base_url, "/api/finance/ar-aging", {"as_of": as_of})["ar_aging"]

    ar_by_account_id = {}
    for row in ar_rows:
        account = account_by_legal.get(row.get("customer_name"))
        if account:
            ar_by_account_id[account["account_id"]] = row

    opps = []
    if opp_start and opp_end:
        opps = fetch_json(base_url, "/api/opportunities", {"start": opp_start, "end": opp_end})[
            "opportunities"
        ]

    return account_by_id, account_by_legal, billing_by_id, ar_rows, ar_by_account_id, opps


def account_features(args: argparse.Namespace) -> None:
    account_ids = parse_ids(args.account_ids)
    account_by_id, _, billing_by_id, _, ar_by_id, opps = load_common(
        args.base_url, args.as_of, args.opportunity_start, args.opportunity_end
    )
    open_pipeline = defaultdict(float)
    for opp in opps:
        if opp.get("state") == "open":
            open_pipeline[opp["account_id"]] += float(opp["amount"])

    assessment = date.fromisoformat(args.assessment_date)
    features = []
    for account_id in account_ids:
        account = account_by_id[account_id]
        metrics = fetch_json(
            args.base_url,
            f"/api/accounts/{account_id}/metrics",
            {"start": args.start_month, "end": args.end_month},
        )["metrics"]
        tickets = fetch_json(
            args.base_url,
            f"/api/accounts/{account_id}/tickets",
            {"start": args.start_date, "end": args.end_date},
        )["tickets"]
        nps_rows = fetch_json(
            args.base_url,
            f"/api/accounts/{account_id}/nps",
            {"start": args.start_date, "end": args.end_date},
        )["nps_responses"]

        cleaned = clean_tickets(tickets)
        sla_misses = sum(
            1
            for ticket in cleaned
            if not (ticket.get("first_response_sla_met") and ticket.get("resolution_sla_met"))
        )
        sla_pct = round(100.0 * (len(cleaned) - sla_misses) / len(cleaned), 1) if cleaned else 100.0

        nps_scores = [int(row["score"]) for row in nps_rows if not row.get("retracted")]
        latest_nps = nps_scores[-1] if nps_scores else None
        nps_drop = bool(
            nps_scores
            and (latest_nps <= 40 or (len(nps_scores) > 1 and latest_nps - nps_scores[0] <= -10))
        )

        usage = [float(row["product_usage"]) for row in metrics]
        seats = [int(row["active_seats"]) for row in metrics]
        usage_decline = bool(
            nps_drop
            and usage
            and (
                usage[-1] < usage[0]
                or any(curr < prev for prev, curr in zip(usage, usage[1:]))
                or (seats and seats[-1] < seats[0])
            )
        )

        renewal_date = date.fromisoformat(account["renewal_date"])
        renewal_days = (renewal_date - assessment).days
        renewal_window = 0 <= renewal_days <= 90
        ar_row = ar_by_id.get(account_id, {})
        overdue = older_overdue(ar_row)
        low_tenure = int(account["contract_tenure_months"]) < 18
        expansion = round(open_pipeline[account_id], 2)

        reason_codes = []
        score = 0
        if renewal_window:
            reason_codes.append("renewal_window")
            score += 20
        if overdue > 0:
            reason_codes.append("overdue_receivable")
            score += 20
        if nps_drop:
            reason_codes.append("nps_drop")
            score += 10
        if sla_misses:
            reason_codes.append("sla_degradation")
            score += 15 if sla_misses == 1 else 20
        if usage_decline:
            reason_codes.append("usage_decline")
            score += 10
        if low_tenure:
            reason_codes.append("low_tenure_high_churn")
            score += 10
        material_expansion = expansion >= args.material_expansion_threshold
        if args.include_all_expansion_reasons and expansion > 0:
            material_expansion = True
        if material_expansion:
            reason_codes.append("expansion_offset")
        if overdue == 0:
            reason_codes.append("clean_billings")
        if renewal_window and float(billing_by_id[account_id]["billing_arr"]) >= 1_000_000:
            score += 10

        score = min(100, int(score))
        if overdue > 0:
            action = "collections_followup"
        elif "sla_degradation" in reason_codes or "usage_decline" in reason_codes or "nps_drop" in reason_codes:
            action = "technical_recovery"
        elif renewal_window or low_tenure:
            action = "renewal_save"
        elif score > 0:
            action = "nurture_monitor"
        else:
            action = "no_action"

        features.append(
            {
                "account_id": account_id,
                "legal_name": account["legal_name"],
                "segment": account["segment"],
                "current_arr": round(float(billing_by_id[account_id]["billing_arr"]), 2),
                "renewal_days": renewal_days,
                "contract_tenure_months": account["contract_tenure_months"],
                "latest_nps": latest_nps,
                "clean_ticket_count": len(cleaned),
                "clean_sla_miss_count": sla_misses,
                "clean_sla_pct": sla_pct,
                "overdue_balance": overdue,
                "open_expansion_pipeline": expansion,
                "reason_codes": reason_codes,
                "risk_score": score,
                "risk_level": risk_level(score),
                "primary_action": action,
            }
        )

    features.sort(
        key=lambda row: (
            -row["risk_score"],
            -row["current_arr"],
            row["account_id"],
        )
    )
    for rank, row in enumerate(features, start=1):
        row["rank"] = rank
    print(json.dumps({"account_features": features}, indent=2))


def qbr_metrics(args: argparse.Namespace) -> None:
    months = parse_ids(args.months)
    metrics = fetch_json(
        args.base_url,
        f"/api/accounts/{args.account_id}/metrics",
        {"start": months[0], "end": months[-1]},
    )["metrics"]
    tickets = clean_tickets(
        fetch_json(
            args.base_url,
            f"/api/accounts/{args.account_id}/tickets",
            {"start": args.start_date, "end": args.end_date},
        )["tickets"]
    )
    nps_rows = [
        row
        for row in fetch_json(
            args.base_url,
            f"/api/accounts/{args.account_id}/nps",
            {"start": args.start_date, "end": args.end_date},
        )["nps_responses"]
        if not row.get("retracted")
    ]
    tickets_by_month = defaultdict(list)
    for ticket in tickets:
        tickets_by_month[date_month(ticket["created_date"])].append(ticket)
    nps_by_month = {date_month(row["response_date"]): int(row["score"]) for row in nps_rows}
    metrics_by_month = {row["month"]: row for row in metrics}

    rows = []
    for month in months:
        month_tickets = tickets_by_month[month]
        sla_pass = sum(
            1
            for ticket in month_tickets
            if ticket.get("first_response_sla_met") and ticket.get("resolution_sla_met")
        )
        sla_pct = round(100.0 * sla_pass / len(month_tickets), 1) if month_tickets else 100.0
        metric = metrics_by_month[month]
        rows.append(
            {
                "month": month,
                "revenue": round(float(metric["recognized_revenue"]), 2),
                "support_tickets": len(month_tickets),
                "sla_compliance_pct": sla_pct,
                "nps_score": nps_by_month.get(month, metric.get("nps_score")),
            }
        )

    first_tickets = rows[0]["support_tickets"]
    last_tickets = rows[-1]["support_tickets"]
    if last_tickets < first_tickets:
        ticket_trend = "improving"
    elif last_tickets > first_tickets:
        ticket_trend = "worsening"
    else:
        ticket_trend = "flat"

    output = {
        "qbr_metrics": rows,
        "highlights": {
            "average_revenue": round(sum(row["revenue"] for row in rows) / len(rows), 2),
            "peak_revenue_month": max(rows, key=lambda row: row["revenue"])["month"],
            "peak_revenue": max(row["revenue"] for row in rows),
            "max_sla_month": max(rows, key=lambda row: row["sla_compliance_pct"])["month"],
            "max_sla_pct": max(row["sla_compliance_pct"] for row in rows),
            "peak_nps_month": max(rows, key=lambda row: row["nps_score"] if row["nps_score"] is not None else -999)[
                "month"
            ],
            "peak_nps_score": max(row["nps_score"] for row in rows if row["nps_score"] is not None),
            "ticket_trend": ticket_trend,
        },
        "metric_sources": {
            "revenue": "crm_closed_won",
            "support_tickets": "support_export",
            "sla_compliance": "sla_report",
            "nps": "nps_survey",
        },
    }
    print(json.dumps(output, indent=2))


def receivables_pipeline(args: argparse.Namespace) -> None:
    account_by_id, account_by_legal, _, ar_rows, _, opps = load_common(
        args.base_url, args.as_of, args.opportunity_start, args.opportunity_end
    )
    followups = []
    for row in ar_rows:
        overdue = older_overdue(row)
        if overdue <= 0:
            continue
        account = account_by_legal.get(row["customer_name"])
        followups.append(
            {
                "customer_name": row["customer_name"],
                "link_status": "linked" if account else "unlinked",
                "account_id": account["account_id"] if account else None,
                "overdue_balance": overdue,
                "due_date": args.due_date,
                "primary_action": "collections_followup",
            }
        )
    followups.sort(key=lambda row: row["customer_name"])

    won = [opp for opp in opps if opp.get("stage") == "Closed Won"]
    lost = [opp for opp in opps if opp.get("stage") == "Closed Lost"]
    open_opps = [opp for opp in opps if opp.get("state") == "open"]
    open_by_product = defaultdict(float)
    for opp in open_opps:
        open_by_product[opp["product_line"]] += float(opp["amount"])
    top_open_product = (
        sorted(open_by_product.items(), key=lambda item: (-item[1], item[0]))[0][0]
        if open_by_product
        else ""
    )

    hr_rows = fetch_json(args.base_url, "/api/hr/summary", {"quarter": args.quarter})["hr_summary"]
    event_rows = fetch_json(
        args.base_url,
        "/api/events/performance",
        {"event": args.event, "quarter": args.quarter},
    )["event_performance"]
    event = event_rows[0] if event_rows else {}

    output = {
        "financial_summary": {
            "overdue_client_count": len(followups),
            "overdue_total": round(sum(row["overdue_balance"] for row in followups), 2),
            "linked_followup_count": sum(1 for row in followups if row["link_status"] == "linked"),
            "unlinked_followup_count": sum(1 for row in followups if row["link_status"] == "unlinked"),
        },
        "pipeline_summary": {
            "won_count": len(won),
            "won_revenue": round(sum(float(row["amount"]) for row in won), 2),
            "lost_count": len(lost),
            "open_count": len(open_opps),
            "open_pipeline": round(sum(float(row["amount"]) for row in open_opps), 2),
            "win_rate_pct": round(100.0 * len(won) / (len(won) + len(lost)), 1)
            if won or lost
            else 0.0,
            "top_open_product_line": top_open_product,
        },
        "overdue_followups": followups,
        "ops_context": {
            "hr_headcount": sum(int(row["headcount"]) for row in hr_rows),
            "unpaid_claims_total": round(sum(float(row["unpaid_claims_amount"]) for row in hr_rows), 2),
            "event_orders": int(event.get("event_orders", 0)),
            "event_revenue": round(float(event.get("event_revenue", 0.0)), 2),
        },
    }
    print(json.dumps(output, indent=2))


def sigmoid(value: float) -> float:
    value = max(-50.0, min(50.0, value))
    return 1.0 / (1.0 + math.exp(-value))


def churn_model(args: argparse.Namespace) -> None:
    train = fetch_csv(args.base_url, "/exports/churn/train.csv")
    validation = fetch_csv(args.base_url, "/exports/churn/validation.csv")
    candidates = fetch_csv(args.base_url, "/exports/churn/candidates.csv")
    requested = set(parse_ids(args.candidate_ids))

    categories = {
        column: sorted({row[column] for row in train}) for column in CHURN_MODEL_CATEGORICAL_COLUMNS
    }
    means = {
        column: statistics.mean(float(row[column]) for row in train)
        for column in CHURN_MODEL_NUMERIC_COLUMNS
    }
    stds = {
        column: statistics.pstdev(float(row[column]) for row in train) or 1.0
        for column in CHURN_MODEL_NUMERIC_COLUMNS
    }

    def vector(row: dict[str, str]) -> list[float]:
        values = [1.0]
        for column in CHURN_MODEL_NUMERIC_COLUMNS:
            values.append((float(row[column]) - means[column]) / stds[column])
        for column in CHURN_MODEL_CATEGORICAL_COLUMNS:
            for category in categories[column][1:]:
                values.append(1.0 if row[column] == category else 0.0)
        return values

    x_train = [vector(row) for row in train]
    y_train = [1.0 if row["Churn"] == "Yes" else 0.0 for row in train]
    weights = [0.0 for _ in x_train[0]]
    learning_rate = args.learning_rate
    alpha = args.l2
    for _ in range(args.epochs):
        gradient = [0.0 for _ in weights]
        for features, target in zip(x_train, y_train):
            prediction = sigmoid(sum(weight * value for weight, value in zip(weights, features)))
            diff = (prediction - target) / len(x_train)
            for index, value in enumerate(features):
                gradient[index] += diff * value
        for index in range(1, len(weights)):
            gradient[index] += alpha * weights[index]
        for index in range(len(weights)):
            weights[index] -= learning_rate * gradient[index]

    def probability(row: dict[str, str]) -> float:
        return sigmoid(sum(weight * value for weight, value in zip(weights, vector(row))))

    validation_correct = sum(
        (probability(row) >= 0.5) == (row["Churn"] == "Yes") for row in validation
    )
    accuracy = round(100.0 * validation_correct / len(validation), 1)
    if accuracy >= 90:
        band = "90_plus"
    elif accuracy >= 80:
        band = "80_to_89"
    elif accuracy >= 70:
        band = "70_to_79"
    else:
        band = "below_70"

    scored = []
    for row in candidates:
        if row["customer_id"] not in requested:
            continue
        prob = probability(row)
        if row["InvoicePastDue"] == "Yes":
            action = "collections_followup"
            reason = "overdue_receivable"
        elif int(float(row["tenure"])) < 18:
            action = "renewal_save"
            reason = "low_tenure_high_churn"
        elif float(row["NPSLast"]) <= 40 or float(row["UsageTrendPct"]) < -10:
            action = "technical_recovery"
            reason = "nps_drop" if float(row["NPSLast"]) <= 40 else "usage_decline"
        else:
            action = "nurture_monitor"
            reason = "clean_billings"
        scored.append(
            {
                "customer_id": row["customer_id"],
                "probability": prob,
                "outreach_action": action,
                "reason_code": reason,
                "tenure": int(float(row["tenure"])),
                "invoice_past_due": row["InvoicePastDue"],
            }
        )
    scored.sort(key=lambda row: (-row["probability"], row["customer_id"]))
    top = scored[: args.top_n]

    output = {
        "model_validation": {
            "training_rows": len(train),
            "validation_rows": len(validation),
            "feature_count": len(NUMERIC_CHURN_COLUMNS) + len(CATEGORICAL_CHURN_COLUMNS),
            "accuracy_pct": accuracy,
            "accuracy_band": band,
            "tenure_coefficient_direction": "negative"
            if weights[1] < 0
            else "positive"
            if weights[1] > 0
            else "zero",
        },
        "risk_ranking": [
            {
                "rank": index,
                "customer_id": row["customer_id"],
                "predicted_churn_probability": round(row["probability"], 3),
                "outreach_action": row["outreach_action"],
                "reason_code": row["reason_code"],
            }
            for index, row in enumerate(top, start=1)
        ],
        "cohort_checks": {
            "past_due_shortlist_count": sum(1 for row in scored if row["invoice_past_due"] == "Yes"),
            "low_tenure_shortlist_count": sum(1 for row in scored if row["tenure"] < 18),
            "average_probability_top5": round(
                sum(row["probability"] for row in top) / len(top), 3
            )
            if top
            else 0.0,
        },
    }
    print(json.dumps(output, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)

    account_parser = subparsers.add_parser("account-features")
    account_parser.add_argument("--account-ids", required=True)
    account_parser.add_argument("--assessment-date", required=True)
    account_parser.add_argument("--start-date", required=True)
    account_parser.add_argument("--end-date", required=True)
    account_parser.add_argument("--start-month", required=True)
    account_parser.add_argument("--end-month", required=True)
    account_parser.add_argument("--as-of", required=True)
    account_parser.add_argument("--opportunity-start")
    account_parser.add_argument("--opportunity-end")
    account_parser.add_argument("--material-expansion-threshold", type=float, default=float("inf"))
    account_parser.add_argument("--include-all-expansion-reasons", action="store_true")
    account_parser.set_defaults(func=account_features)

    qbr_parser = subparsers.add_parser("qbr-metrics")
    qbr_parser.add_argument("--account-id", required=True)
    qbr_parser.add_argument("--months", required=True)
    qbr_parser.add_argument("--start-date", required=True)
    qbr_parser.add_argument("--end-date", required=True)
    qbr_parser.set_defaults(func=qbr_metrics)

    receivables_parser = subparsers.add_parser("receivables-pipeline")
    receivables_parser.add_argument("--as-of", required=True)
    receivables_parser.add_argument("--opportunity-start", required=True)
    receivables_parser.add_argument("--opportunity-end", required=True)
    receivables_parser.add_argument("--quarter", required=True)
    receivables_parser.add_argument("--event", required=True)
    receivables_parser.add_argument("--due-date", required=True)
    receivables_parser.set_defaults(func=receivables_pipeline)

    churn_parser = subparsers.add_parser("churn-model")
    churn_parser.add_argument("--candidate-ids", required=True)
    churn_parser.add_argument("--top-n", type=int, default=5)
    churn_parser.add_argument("--epochs", type=int, default=10000)
    churn_parser.add_argument("--learning-rate", type=float, default=0.1)
    churn_parser.add_argument("--l2", type=float, default=0.1)
    churn_parser.set_defaults(func=churn_model)

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
