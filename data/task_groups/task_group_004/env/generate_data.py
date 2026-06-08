#!/usr/bin/env python3
"""Generate the ApexCloud Retention Operations shared dataset."""

from __future__ import annotations

import csv
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path


SEED = 4004
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

MONTHS_2026 = [f"2026-{month:02d}" for month in range(1, 13)]
QUARTER_ENDS = {
    "2026-Q1": "2026-03-31",
    "2026-Q2": "2026-06-30",
    "2026-Q3": "2026-09-30",
    "2026-Q4": "2026-12-31",
}
REGIONS = ["North America", "EMEA", "APAC", "LATAM"]
CSMS = [
    "Maya Chen",
    "Owen Patel",
    "Riley Brooks",
    "Ari Morgan",
    "Samira Khan",
    "Jordan Lee",
    "Elena Ruiz",
    "Noah Becker",
]
PRODUCT_AREAS = ["identity", "workflow", "analytics", "billing", "integrations", "mobile"]
PRODUCT_LINES = ["Core Retention", "Workflow Plus", "Data Cloud", "AI Assist"]
PLANS = ["Launch", "Growth", "Scale", "Enterprise", "Strategic"]
SEGMENTS = ["SMB", "Mid-Market", "Enterprise", "Strategic"]


ACCOUNT_SEEDS = [
    ("acct_globex_north", "Globex North Holdings LLC", "Globex North", "Enterprise", "North America"),
    ("acct_northstar_finance", "Northstar Finance Group Inc.", "Northstar Finance", "Strategic", "North America"),
    ("acct_northstar_retail", "Northstar Retail Services LLC", "Northstar Retail", "Mid-Market", "North America"),
    ("acct_polaris_health", "Polaris Health Network Inc.", "Polaris Health", "Enterprise", "North America"),
    ("acct_meridian_energy", "Meridian Energy Partners LLC", "Meridian Energy", "Enterprise", "EMEA"),
    ("acct_cobalt_media", "Cobalt Media Works Inc.", "Cobalt Media", "Mid-Market", "North America"),
    ("acct_zenith_labs", "Zenith Labs GmbH", "Zenith Labs", "Enterprise", "EMEA"),
    ("acct_lumen_rail", "Lumen Rail Systems Ltd.", "Lumen Rail", "Strategic", "EMEA"),
    ("acct_orbitax", "Orbitax Solutions Pty Ltd.", "Orbitax", "Mid-Market", "APAC"),
    ("acct_arcstone", "Arcstone Manufacturing Inc.", "Arcstone", "Enterprise", "North America"),
    ("acct_bluepeak", "BluePeak Outdoors LLC", "BluePeak Outdoors", "SMB", "North America"),
    ("acct_summit_grid", "Summit Grid Cooperative", "Summit Grid", "Mid-Market", "North America"),
    ("acct_harborbyte", "HarborByte Systems Inc.", "HarborByte", "SMB", "North America"),
    ("acct_kiteworks", "Kiteworks Digital Ltd.", "Kiteworks Digital", "Mid-Market", "EMEA"),
    ("acct_saffron_hotel", "Saffron Hotel Group Pte. Ltd.", "Saffron Hotel", "Enterprise", "APAC"),
    ("acct_terra_nova", "Terra Nova Foods SA", "Terra Nova Foods", "Mid-Market", "LATAM"),
    ("acct_riverbend_bank", "Riverbend Bank Corp.", "Riverbend Bank", "Enterprise", "North America"),
    ("acct_metrobyte", "MetroByte Telecom LLC", "MetroByte", "Enterprise", "North America"),
    ("acct_quartz_insure", "Quartz Insurance PLC", "Quartz Insurance", "Strategic", "EMEA"),
    ("acct_apexia", "Apexia Robotics KK", "Apexia Robotics", "Enterprise", "APAC"),
    ("acct_redwood_school", "Redwood School District", "Redwood Schools", "SMB", "North America"),
    ("acct_eastwind", "Eastwind Logistics BV", "Eastwind Logistics", "Mid-Market", "EMEA"),
    ("acct_mint_leaf", "Mint Leaf Markets Inc.", "Mint Leaf", "SMB", "North America"),
    ("acct_stellar_auto", "Stellar Auto Components GmbH", "Stellar Auto", "Enterprise", "EMEA"),
    ("acct_canyon_state", "Canyon State Health LLC", "Canyon State Health", "Mid-Market", "North America"),
    ("acct_silverline", "Silverline Credit Union", "Silverline CU", "SMB", "North America"),
    ("acct_aurora_textiles", "Aurora Textiles Ltd.", "Aurora Textiles", "Mid-Market", "APAC"),
    ("acct_bayside_bio", "Bayside Biotech Inc.", "Bayside Biotech", "Enterprise", "North America"),
    ("acct_greenfield", "Greenfield Agritech SA", "Greenfield Agritech", "Mid-Market", "LATAM"),
    ("acct_cloudnine", "CloudNine Travel Group Inc.", "CloudNine Travel", "Mid-Market", "North America"),
    ("acct_valence", "Valence Payment Services LLC", "Valence Payments", "Enterprise", "North America"),
    ("acct_peakstone", "Peakstone Capital Ltd.", "Peakstone Capital", "Strategic", "EMEA"),
    ("acct_brightharbor", "BrightHarbor Clinics Inc.", "BrightHarbor", "Enterprise", "North America"),
    ("acct_tandemworks", "TandemWorks Software Oy", "TandemWorks", "SMB", "EMEA"),
    ("acct_nimbus_fleet", "Nimbus Fleet Services Pty Ltd.", "Nimbus Fleet", "Mid-Market", "APAC"),
    ("acct_solstice", "Solstice Renewables Inc.", "Solstice Renewables", "Enterprise", "North America"),
    ("acct_opalcare", "OpalCare Pharmacy Group", "OpalCare", "Mid-Market", "APAC"),
    ("acct_everline", "Everline Apparel LLC", "Everline Apparel", "SMB", "North America"),
    ("acct_westport", "Westport Port Authority", "Westport Port", "Enterprise", "North America"),
    ("acct_helios", "Helios Medical Devices AG", "Helios Devices", "Enterprise", "EMEA"),
    ("acct_foxtrot", "Foxtrot Foodservice Inc.", "Foxtrot Foodservice", "Mid-Market", "North America"),
    ("acct_southridge", "Southridge Mining Ltd.", "Southridge Mining", "Enterprise", "LATAM"),
    ("acct_lakeshore", "Lakeshore Public Media", "Lakeshore Media", "SMB", "North America"),
    ("acct_vectorline", "Vectorline Security Systems LLC", "Vectorline Security", "Mid-Market", "North America"),
]


def write_json(path: Path, rows: object) -> None:
    path.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def month_start(month_key: str) -> date:
    return datetime.strptime(month_key + "-01", "%Y-%m-%d").date()


def end_of_month(month_key: str) -> date:
    start = month_start(month_key)
    if start.month == 12:
        return date(start.year, 12, 31)
    return date(start.year, start.month + 1, 1) - timedelta(days=1)


def quarter_for_month(month_key: str) -> str:
    month = int(month_key[-2:])
    return f"2026-Q{((month - 1) // 3) + 1}"


def normalize_account_name(name: str) -> str:
    words = []
    for token in name.lower().replace(".", "").replace(",", "").split():
        if token not in {"inc", "llc", "ltd", "gmbh", "corp", "plc", "sa", "bv", "oy", "ag", "kk"}:
            words.append(token)
    return " ".join(words)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def generate_accounts(rng: random.Random) -> list[dict]:
    accounts = []
    stale_ids = {
        "acct_northstar_finance",
        "acct_globex_north",
        "acct_lumen_rail",
        "acct_quartz_insure",
        "acct_solstice",
        "acct_valence",
        "acct_southridge",
        "acct_bayside_bio",
    }
    lifecycle_by_index = ["active"] * 34 + ["renewal_risk"] * 6 + ["implementation"] * 2 + ["paused"] * 2
    rng.shuffle(lifecycle_by_index)

    for index, (account_id, legal_name, display_name, segment, region) in enumerate(ACCOUNT_SEEDS):
        plan = {
            "SMB": rng.choice(["Launch", "Growth"]),
            "Mid-Market": rng.choice(["Growth", "Scale"]),
            "Enterprise": rng.choice(["Scale", "Enterprise"]),
            "Strategic": rng.choice(["Enterprise", "Strategic"]),
        }[segment]
        base_arr = {
            "SMB": rng.randrange(36000, 120000, 3000),
            "Mid-Market": rng.randrange(120000, 360000, 6000),
            "Enterprise": rng.randrange(360000, 950000, 12000),
            "Strategic": rng.randrange(900000, 1750000, 25000),
        }[segment]
        if account_id == "acct_globex_north":
            base_arr = 1188000
        if account_id == "acct_northstar_finance":
            base_arr = 1425000

        renewal_month = rng.randint(1, 12)
        renewal_day = min(rng.randint(5, 27), end_of_month(f"2026-{renewal_month:02d}").day)
        tenure = rng.randint(8, 86)
        if account_id in {"acct_northstar_retail", "acct_tandemworks", "acct_everline"}:
            tenure = rng.randint(5, 14)

        billing_arr = float(base_arr)
        crm_arr = billing_arr
        if account_id in stale_ids:
            crm_arr = round(billing_arr * rng.choice([0.84, 0.89, 0.93, 1.11]), 2)

        alias_root = display_name.replace(" ", "")
        aliases = [
            display_name,
            normalize_account_name(legal_name).title(),
            f"{alias_root} Ops",
        ]
        if account_id in {"acct_globex_north", "acct_northstar_finance", "acct_quartz_insure", "acct_valence"}:
            aliases.append(f"{display_name} Subsidiary")

        accounts.append(
            {
                "account_id": account_id,
                "legal_name": legal_name,
                "display_name": display_name,
                "segment": segment,
                "region": region,
                "csm_owner": CSMS[index % len(CSMS)],
                "renewal_date": date(2026, renewal_month, renewal_day).isoformat(),
                "crm_arr": round(crm_arr, 2),
                "billing_arr_current": round(billing_arr, 2),
                "contract_tenure_months": tenure,
                "product_plan": plan,
                "lifecycle_status": lifecycle_by_index[index],
                "account_aliases": aliases,
            }
        )
    return accounts


def account_risk_base(account: dict, rng: random.Random) -> float:
    score = 0.0
    if account["lifecycle_status"] == "renewal_risk":
        score += 0.22
    if account["contract_tenure_months"] < 15:
        score += 0.18
    if account["segment"] in {"Enterprise", "Strategic"}:
        score += 0.04
    if account["account_id"] in {"acct_northstar_finance", "acct_lumen_rail", "acct_quartz_insure", "acct_valence"}:
        score += 0.16
    if account["account_id"] in {"acct_tandemworks", "acct_northstar_retail", "acct_everline"}:
        score += 0.14
    return clamp(score + rng.uniform(0.03, 0.24), 0.05, 0.75)


def generate_metrics(accounts: list[dict], rng: random.Random) -> list[dict]:
    metrics = []
    for account in accounts:
        risk = account_risk_base(account, rng)
        base_usage = clamp(88 - risk * 54 + rng.uniform(-7, 6), 31, 98)
        seats = max(8, int(account["billing_arr_current"] / rng.uniform(5200, 9800)))
        for month_key in MONTHS_2026:
            month_index = int(month_key[-2:])
            seasonal = 1 + (0.035 if month_index in {3, 6, 9, 12} else 0)
            revenue = account["billing_arr_current"] / 12 * seasonal * rng.uniform(0.965, 1.035)
            usage_drift = (month_index - 1) * rng.uniform(-0.55, 0.42)
            usage = clamp(base_usage + usage_drift + rng.uniform(-5, 5), 18, 99)
            active_seats = max(1, int(seats * clamp(usage / 100 + rng.uniform(-0.05, 0.04), 0.35, 1.04)))
            ticket_count = max(0, int(rng.gauss(1.8 + risk * 7.0, 1.8)))
            sla = clamp(99.0 - risk * 24 + rng.uniform(-4.5, 3.2), 62.0, 100.0)
            nps_score = None
            status = "missing"
            if rng.random() > (0.14 + risk * 0.12):
                status = "completed"
                nps_score = int(clamp(rng.gauss(76 - risk * 82, 16), -35, 100))
                if rng.random() < 0.025:
                    status = "retracted"
            metrics.append(
                {
                    "account_id": account["account_id"],
                    "month": month_key,
                    "quarter": quarter_for_month(month_key),
                    "recognized_revenue": round(revenue, 2),
                    "support_ticket_count": ticket_count,
                    "sla_compliance": round(sla, 2),
                    "nps_score": nps_score,
                    "product_usage": round(usage, 2),
                    "active_seats": active_seats,
                    "survey_status": status,
                }
            )
    return metrics


def generate_tickets(metrics: list[dict], rng: random.Random) -> list[dict]:
    tickets = []
    counter = 10000
    for metric in metrics:
        for _ in range(metric["support_ticket_count"]):
            counter += 1
            month_end = end_of_month(metric["month"])
            created = month_start(metric["month"]) + timedelta(days=rng.randint(0, month_end.day - 1))
            is_spam = rng.random() < 0.045
            is_duplicate = (not is_spam) and rng.random() < 0.07
            status = rng.choices(
                ["closed", "open", "cancelled"],
                weights=[0.75, 0.18, 0.07],
                k=1,
            )[0]
            severity = rng.choices(["P1", "P2", "P3", "P4"], weights=[0.08, 0.23, 0.44, 0.25], k=1)[0]
            if metric["sla_compliance"] < 82 and severity in {"P1", "P2"}:
                first_sla = rng.random() < 0.64
                resolution_sla = rng.random() < 0.58
            else:
                first_sla = rng.random() < 0.91
                resolution_sla = rng.random() < 0.87
            tickets.append(
                {
                    "ticket_id": f"TCK-{counter}",
                    "account_id": metric["account_id"],
                    "created_date": created.isoformat(),
                    "status": status,
                    "severity": severity,
                    "is_duplicate": is_duplicate,
                    "is_spam": is_spam,
                    "first_response_sla_met": first_sla,
                    "resolution_sla_met": resolution_sla,
                    "product_area": rng.choice(PRODUCT_AREAS),
                }
            )
    return tickets


def generate_nps(metrics: list[dict], rng: random.Random) -> list[dict]:
    responses = []
    counter = 7000
    for metric in metrics:
        if metric["nps_score"] is None:
            continue
        counter += 1
        month_end = end_of_month(metric["month"])
        response_date = month_start(metric["month"]) + timedelta(days=rng.randint(2, month_end.day))
        retracted = metric["survey_status"] == "retracted"
        responses.append(
            {
                "response_id": f"NPS-{counter}",
                "account_id": metric["account_id"],
                "response_date": response_date.isoformat(),
                "score": metric["nps_score"],
                "retracted": retracted,
                "survey_channel": rng.choice(["email", "in_app", "csm_call"]),
            }
        )
        if rng.random() < 0.035:
            counter += 1
            responses.append(
                {
                    "response_id": f"NPS-{counter}",
                    "account_id": metric["account_id"],
                    "response_date": (response_date + timedelta(days=1)).isoformat(),
                    "score": int(clamp(metric["nps_score"] + rng.randint(-9, 9), -100, 100)),
                    "retracted": True,
                    "survey_channel": "email",
                }
            )
    return responses


def generate_billing(accounts: list[dict], rng: random.Random) -> list[dict]:
    snapshots = []
    for account in accounts:
        for quarter, as_of in QUARTER_ENDS.items():
            quarter_num = int(quarter[-1])
            drift = 1 + (quarter_num - 4) * rng.uniform(-0.015, 0.018)
            if quarter == "2026-Q4":
                drift = 1.0
            arr = account["billing_arr_current"] * drift
            snapshots.append(
                {
                    "snapshot_id": f"BILL-{account['account_id']}-{quarter}",
                    "account_id": account["account_id"],
                    "legal_name": account["legal_name"],
                    "as_of": as_of,
                    "billing_arr": round(arr, 2),
                    "mrr": round(arr / 12, 2),
                    "posted": True,
                    "source": "billing_snapshot",
                }
            )
    return snapshots


def generate_ar_aging(accounts: list[dict], rng: random.Random) -> list[dict]:
    rows = []
    noisy_names = [
        ("Globex North Subsidiary LLC", "North America"),
        ("North Star Finance Services", "North America"),
        ("Quartz Insurance Claims Ltd.", "EMEA"),
        ("Valence Payment Services Canada", "North America"),
        ("Riverbend Bank Foundation", "North America"),
    ]
    overdue_ids = {
        "acct_northstar_finance",
        "acct_globex_north",
        "acct_lumen_rail",
        "acct_valence",
        "acct_polaris_health",
        "acct_tandemworks",
        "acct_southridge",
        "acct_aurora_textiles",
    }
    for account in accounts:
        for quarter, as_of in QUARTER_ENDS.items():
            arr = account["billing_arr_current"]
            current = round(arr / 12 * rng.uniform(0.15, 0.42), 2)
            b1 = round(arr / 12 * rng.uniform(0.00, 0.12), 2)
            b31 = round(arr / 12 * rng.uniform(0.00, 0.08), 2)
            b61 = 0.0
            b90 = 0.0
            if account["account_id"] in overdue_ids and quarter in {"2026-Q2", "2026-Q3", "2026-Q4"}:
                b61 = round(arr / 12 * rng.uniform(0.05, 0.22), 2)
                b90 = round(arr / 12 * rng.uniform(0.02, 0.16), 2) if rng.random() < 0.62 else 0.0
            rows.append(
                {
                    "aging_id": f"AR-{account['account_id']}-{quarter}",
                    "as_of": as_of,
                    "quarter": quarter,
                    "customer_name": account["legal_name"],
                    "region": account["region"],
                    "current": current,
                    "1_30": b1,
                    "31_60": b31,
                    "61_90": b61,
                    "90_plus": b90,
                }
            )
    for name, region in noisy_names:
        for quarter, as_of in QUARTER_ENDS.items():
            rows.append(
                {
                    "aging_id": f"AR-noise-{normalize_account_name(name).replace(' ', '-')}-{quarter}",
                    "as_of": as_of,
                    "quarter": quarter,
                    "customer_name": name,
                    "region": region,
                    "current": round(rng.uniform(4500, 52000), 2),
                    "1_30": round(rng.uniform(0, 19000), 2),
                    "31_60": round(rng.uniform(0, 11000), 2),
                    "61_90": round(rng.uniform(0, 26000), 2) if quarter in {"2026-Q3", "2026-Q4"} else 0.0,
                    "90_plus": round(rng.uniform(0, 18000), 2) if quarter == "2026-Q3" else 0.0,
                }
            )
    return rows


def generate_opportunities(accounts: list[dict], rng: random.Random) -> list[dict]:
    opportunities = []
    counter = 500
    stages = ["Prospecting", "Discovery", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]
    for account in accounts:
        opp_count = rng.randint(1, 4)
        for _ in range(opp_count):
            counter += 1
            stage = rng.choices(stages, weights=[0.17, 0.18, 0.18, 0.18, 0.18, 0.11], k=1)[0]
            close_month = rng.randint(1, 12)
            close_day = rng.randint(4, 26)
            close = date(2026, close_month, close_day)
            created = close - timedelta(days=rng.randint(22, 180))
            amount = account["billing_arr_current"] * rng.uniform(0.05, 0.34)
            if account["segment"] in {"Strategic", "Enterprise"}:
                amount *= rng.uniform(1.05, 1.65)
            opportunities.append(
                {
                    "opportunity_id": f"OPP-{counter}",
                    "account_id": account["account_id"],
                    "account_legal_name": account["legal_name"],
                    "stage": stage,
                    "amount": round(amount, 2),
                    "close_date": close.isoformat(),
                    "created_date": created.isoformat(),
                    "region": account["region"],
                    "product_line": rng.choice(PRODUCT_LINES),
                    "state": "closed" if stage in {"Closed Won", "Closed Lost"} else "open",
                }
            )
    for old_index in range(10):
        account = rng.choice(accounts)
        counter += 1
        old_close = date(2025, rng.randint(7, 12), rng.randint(3, 24))
        opportunities.append(
            {
                "opportunity_id": f"OPP-{counter}",
                "account_id": account["account_id"],
                "account_legal_name": account["legal_name"],
                "stage": rng.choice(["Closed Won", "Closed Lost"]),
                "amount": round(account["billing_arr_current"] * rng.uniform(0.04, 0.16), 2),
                "close_date": old_close.isoformat(),
                "created_date": (old_close - timedelta(days=rng.randint(30, 140))).isoformat(),
                "region": account["region"],
                "product_line": rng.choice(PRODUCT_LINES),
                "state": "closed",
            }
        )
    return opportunities


def generate_hr_summary(rng: random.Random) -> list[dict]:
    rows = []
    for quarter in QUARTER_ENDS:
        for region in REGIONS:
            headcount = rng.randint(46, 138)
            rows.append(
                {
                    "quarter": quarter,
                    "region": region,
                    "headcount": headcount,
                    "attendance_rate": round(rng.uniform(92.0, 98.8), 2),
                    "high_absence_employees": rng.randint(1, max(2, headcount // 12)),
                    "unpaid_claims_count": rng.randint(2, 19),
                    "unpaid_claims_amount": round(rng.uniform(4200, 38000), 2),
                    "leave_liability_hours": round(rng.uniform(180, 1280), 1),
                    "open_advances_count": rng.randint(1, 13),
                    "open_advances_amount": round(rng.uniform(2500, 46000), 2),
                }
            )
    return rows


def generate_event_performance(rng: random.Random) -> list[dict]:
    event_ids = ["retention_summit", "apex_connect", "field_roundtable", "renewal_lab", "customer_ops_day"]
    rows = []
    for quarter in QUARTER_ENDS:
        for event_id in event_ids:
            orders = rng.randint(84, 560)
            cancelled = rng.randint(2, max(4, int(orders * 0.08)))
            refunded = rng.randint(1, max(3, int(orders * 0.035)))
            pending = rng.randint(1, max(3, int(orders * 0.06)))
            complete = orders - cancelled - refunded - pending
            ticket_rev = complete * rng.uniform(220, 690)
            product_rev = complete * rng.uniform(80, 340)
            rows.append(
                {
                    "event_id": event_id,
                    "quarter": quarter,
                    "event_orders": orders,
                    "event_revenue": round(ticket_rev + product_rev, 2),
                    "product_revenue": round(product_rev, 2),
                    "completed_orders": complete,
                    "cancelled_orders": cancelled,
                    "refunded_orders": refunded,
                    "pending_orders": pending,
                }
            )
    return rows


CHURN_FEATURES = [
    "tenure",
    "MonthlyCharges",
    "TotalCharges",
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
    "SupportTickets90d",
    "NPSLast",
    "UsageTrendPct",
    "InvoicePastDue",
    "ActiveSeatRatio",
]


def churn_row(rng: random.Random, customer_id: str, account: dict | None = None, include_churn: bool = True) -> dict:
    if account:
        tenure = account["contract_tenure_months"]
        monthly = round(account["billing_arr_current"] / 12 / max(8, account["billing_arr_current"] / 7800), 2)
        total = round(monthly * tenure, 2)
        contract = "Two year" if tenure > 36 else ("One year" if tenure > 14 else "Month-to-month")
        invoice_past_due = "Yes" if account["lifecycle_status"] == "renewal_risk" or rng.random() < 0.18 else "No"
        tickets = rng.randint(1, 12) if invoice_past_due == "Yes" else rng.randint(0, 5)
        nps = int(clamp(rng.gauss(42 if invoice_past_due == "Yes" else 68, 22), -55, 100))
        usage_trend = round(rng.uniform(-24, 4) if invoice_past_due == "Yes" else rng.uniform(-8, 18), 2)
        seat_ratio = round(clamp(rng.gauss(0.62 if invoice_past_due == "Yes" else 0.83, 0.13), 0.25, 1.08), 3)
    else:
        tenure = rng.randint(1, 72)
        monthly = round(rng.uniform(42, 182), 2)
        total = round(monthly * tenure * rng.uniform(0.86, 1.04), 2)
        contract = rng.choices(["Month-to-month", "One year", "Two year"], weights=[0.48, 0.28, 0.24], k=1)[0]
        invoice_past_due = rng.choices(["Yes", "No"], weights=[0.22, 0.78], k=1)[0]
        tickets = rng.randint(0, 14)
        nps = int(clamp(rng.gauss(58 - tickets * 3.2 - (10 if invoice_past_due == "Yes" else 0), 24), -80, 100))
        usage_trend = round(rng.uniform(-30, 24), 2)
        seat_ratio = round(rng.uniform(0.28, 1.04), 3)

    risk_score = -2.3
    risk_score += 1.15 if contract == "Month-to-month" else (-0.35 if contract == "Two year" else 0.0)
    risk_score += 0.75 if invoice_past_due == "Yes" else 0.0
    risk_score += max(0, 18 - tenure) * 0.055
    risk_score += tickets * 0.085
    risk_score += -0.018 * nps
    risk_score += -0.022 * usage_trend
    risk_score += -1.15 * seat_ratio
    probability = 1 / (1 + pow(2.718281828, -risk_score))
    churn = "Yes" if rng.random() < probability else "No"

    row = {
        "customer_id": customer_id,
        "tenure": tenure,
        "MonthlyCharges": monthly,
        "TotalCharges": total,
        "Contract": contract,
        "PaymentMethod": rng.choice(["Bank transfer", "Credit card", "Electronic check", "Mailed check"]),
        "PaperlessBilling": rng.choice(["Yes", "No"]),
        "Partner": rng.choice(["Yes", "No"]),
        "Dependents": rng.choice(["Yes", "No"]),
        "OnlineSecurity": rng.choice(["Yes", "No", "No internet service"]),
        "OnlineBackup": rng.choice(["Yes", "No", "No internet service"]),
        "DeviceProtection": rng.choice(["Yes", "No", "No internet service"]),
        "TechSupport": rng.choice(["Yes", "No", "No internet service"]),
        "StreamingTV": rng.choice(["Yes", "No", "No internet service"]),
        "StreamingMovies": rng.choice(["Yes", "No", "No internet service"]),
        "SupportTickets90d": tickets,
        "NPSLast": nps,
        "UsageTrendPct": usage_trend,
        "InvoicePastDue": invoice_past_due,
        "ActiveSeatRatio": seat_ratio,
    }
    if include_churn:
        row["Churn"] = churn
    return row


def generate_churn_exports(accounts: list[dict], rng: random.Random) -> tuple[list[dict], list[dict], list[dict]]:
    train = [churn_row(rng, f"train_{idx:04d}", include_churn=True) for idx in range(1, 181)]
    validation = [churn_row(rng, f"valid_{idx:04d}", include_churn=True) for idx in range(1, 61)]
    candidates = [churn_row(rng, account["account_id"], account=account, include_churn=False) for account in accounts]
    return train, validation, candidates


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_account_metric_extract(accounts: list[dict], metrics: list[dict], tickets: list[dict]) -> list[dict]:
    account_by_id = {row["account_id"]: row for row in accounts}
    clean_tickets = [
        ticket
        for ticket in tickets
        if not ticket["is_spam"] and not ticket["is_duplicate"] and ticket["status"] != "cancelled"
    ]
    ticket_counts: dict[tuple[str, str], int] = {}
    for ticket in clean_tickets:
        key = (ticket["account_id"], ticket["created_date"][:7])
        ticket_counts[key] = ticket_counts.get(key, 0) + 1
    rows = []
    for metric in metrics:
        account = account_by_id[metric["account_id"]]
        rows.append(
            {
                "account_id": metric["account_id"],
                "legal_name": account["legal_name"],
                "segment": account["segment"],
                "region": account["region"],
                "month": metric["month"],
                "recognized_revenue": metric["recognized_revenue"],
                "clean_ticket_count": ticket_counts.get((metric["account_id"], metric["month"]), 0),
                "sla_compliance": metric["sla_compliance"],
                "nps_score": "" if metric["nps_score"] is None else metric["nps_score"],
                "product_usage": metric["product_usage"],
                "active_seats": metric["active_seats"],
            }
        )
    return rows


def main() -> None:
    rng = random.Random(SEED)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    accounts = generate_accounts(rng)
    metrics = generate_metrics(accounts, rng)
    tickets = generate_tickets(metrics, rng)
    nps = generate_nps(metrics, rng)
    billing = generate_billing(accounts, rng)
    ar_aging = generate_ar_aging(accounts, rng)
    opportunities = generate_opportunities(accounts, rng)
    hr_summary = generate_hr_summary(rng)
    event_performance = generate_event_performance(rng)
    churn_train, churn_validation, churn_candidates = generate_churn_exports(accounts, rng)
    account_metric_extract = generate_account_metric_extract(accounts, metrics, tickets)

    json_files = {
        "accounts.json": accounts,
        "account_metrics.json": metrics,
        "support_tickets.json": tickets,
        "nps_responses.json": nps,
        "billing_snapshots.json": billing,
        "ar_aging.json": ar_aging,
        "opportunities.json": opportunities,
        "hr_summary.json": hr_summary,
        "event_performance.json": event_performance,
    }
    for filename, rows in json_files.items():
        write_json(DATA_DIR / filename, rows)

    churn_fields = ["customer_id"] + CHURN_FEATURES + ["Churn"]
    candidate_fields = ["customer_id"] + CHURN_FEATURES
    write_csv(DATA_DIR / "churn_train.csv", churn_train, churn_fields)
    write_csv(DATA_DIR / "churn_validation.csv", churn_validation, churn_fields)
    write_csv(DATA_DIR / "churn_candidates.csv", churn_candidates, candidate_fields)
    metric_fields = [
        "account_id",
        "legal_name",
        "segment",
        "region",
        "month",
        "recognized_revenue",
        "clean_ticket_count",
        "sla_compliance",
        "nps_score",
        "product_usage",
        "active_seats",
    ]
    write_csv(DATA_DIR / "account_metric_extract.csv", account_metric_extract, metric_fields)

    row_counts = {filename: len(rows) for filename, rows in json_files.items()}
    row_counts.update(
        {
            "churn_train.csv": len(churn_train),
            "churn_validation.csv": len(churn_validation),
            "churn_candidates.csv": len(churn_candidates),
            "account_metric_extract.csv": len(account_metric_extract),
        }
    )
    manifest = {
        "environment": "ApexCloud Retention Operations",
        "task_group": "task_group_004",
        "seed": SEED,
        "generated_at": "2026-06-01T00:00:00Z",
        "data_files": sorted(row_counts),
        "row_counts": row_counts,
        "construction_notes": [
            "CRM ARR can be stale; latest posted billing snapshots carry current ARR.",
            "A/R customer names include exact CRM legal names plus noisy subsidiaries and similar names.",
            "Support exports include spam, duplicate, and cancelled records for convention learning.",
            "NPS exports include missing and retracted responses.",
            "Churn candidates omit the Churn label; train and validation include it.",
        ],
        "public_endpoints": [
            "/api/health",
            "/api/accounts",
            "/api/accounts/<account_id>",
            "/api/accounts/<account_id>/metrics?start=YYYY-MM&end=YYYY-MM",
            "/api/accounts/<account_id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD",
            "/api/accounts/<account_id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD",
            "/api/billing/snapshots",
            "/api/finance/ar-aging?as_of=YYYY-MM-DD",
            "/api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD&region=<optional>",
            "/api/hr/summary?quarter=YYYY-QN&region=<optional>",
            "/api/events/performance?event=<event_id>&quarter=YYYY-QN",
            "/exports/churn/train.csv",
            "/exports/churn/validation.csv",
            "/exports/churn/candidates.csv",
            "/exports/account_metric_extract.csv",
        ],
    }
    write_json(BASE_DIR / "manifest.json", manifest)
    print(f"Generated {len(row_counts)} files in {DATA_DIR}")


if __name__ == "__main__":
    main()
