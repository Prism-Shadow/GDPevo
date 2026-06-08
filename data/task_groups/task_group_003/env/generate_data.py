#!/usr/bin/env python3
from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path


SEED = 43003
BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"


def account(account_id, name, status="Active", auth="SUCCESS", recovery="", service_area="SA-00", tier="standard"):
    return {
        "account_id": account_id,
        "name": name,
        "status": status,
        "authentication": {
            "last_login_status": auth,
            "account_recovery_status": recovery,
            "last_login_at": "2026-05-30T14:10:00Z",
        },
        "service_area": service_area,
        "tier": tier,
    }


def ticket(ticket_id, account_id, service_type, subscribed_mbps, service_area, issue, created_at):
    return {
        "ticket_id": ticket_id,
        "account_id": account_id,
        "service_type": service_type,
        "subscribed_mbps": subscribed_mbps,
        "service_area": service_area,
        "issue_summary": issue,
        "created_at": created_at,
        "status": "OPEN",
    }


def diagnostics(ticket_id, latency, jitter, bandwidth, root_causes):
    return {
        "ticket_id": ticket_id,
        "started_at": "2026-06-01T09:15:00Z",
        "completed_at": "2026-06-01T09:27:00Z",
        "latency_ms": latency,
        "jitter_ms": jitter,
        "bandwidth_mbps": bandwidth,
        "root_causes": root_causes,
    }


def troubleshooting(ticket_id, steps, latency, jitter, bandwidth):
    return {
        "ticket_id": ticket_id,
        "started_at": "2026-06-01T09:33:00Z",
        "completed_at": "2026-06-01T09:49:00Z",
        "steps": steps,
        "post_latency_ms": latency,
        "post_jitter_ms": jitter,
        "post_bandwidth_mbps": bandwidth,
    }


def outage(outage_id, service_area, service_types, impact, eta_hours, active=True):
    return {
        "outage_id": outage_id,
        "service_area": service_area,
        "service_types": service_types,
        "impact_score": impact,
        "eta_hours": eta_hours,
        "active": active,
        "started_at": "2026-06-01T07:05:00Z",
    }


def plan(plan_id, name, limit_gb, monthly_price, refuel_price):
    return {
        "plan_id": plan_id,
        "name": name,
        "data_limit_gb": limit_gb,
        "monthly_price_usd": monthly_price,
        "data_refueling_price_per_gb": refuel_price,
    }


def line(
    line_id,
    customer_id,
    phone,
    plan_id,
    device_id,
    status="Active",
    data_used=3.0,
    roaming=True,
    contract_end="2027-12-31",
    suspension_reason="",
):
    return {
        "line_id": line_id,
        "customer_id": customer_id,
        "phone_number": phone,
        "plan_id": plan_id,
        "device_id": device_id,
        "status": status,
        "data_used_gb": data_used,
        "roaming_enabled": roaming,
        "contract_end_date": contract_end,
        "suspension_reason": suspension_reason,
    }


def device(device_id, model, **state):
    base = {
        "device_id": device_id,
        "model": model,
        "sim_status": "active",
        "airplane_mode": False,
        "signal_strength": "good",
        "mobile_data_enabled": True,
        "phone_roaming_enabled": True,
        "network_mode_preference": "4g_5g_preferred",
        "data_saver_mode": False,
        "vpn_connected": False,
        "wifi_calling_enabled": False,
        "mmsc_url_present": True,
        "messaging_permissions": {"sms": True, "storage": True},
        "speed_test": "excellent",
        "can_send_mms": True,
    }
    base.update(state)
    return base


def bill(bill_id, customer_id, amount, status="Paid", due_date="2026-05-20"):
    return {
        "bill_id": bill_id,
        "customer_id": customer_id,
        "amount_due_usd": amount,
        "status": status,
        "due_date": due_date,
    }


def case(case_id, customer_id, line_id, device_id, issue_type, summary, location="home"):
    return {
        "case_id": case_id,
        "customer_id": customer_id,
        "line_id": line_id,
        "device_id": device_id,
        "issue_type": issue_type,
        "summary": summary,
        "customer_location": location,
        "opened_at": "2026-06-01T10:10:00Z",
    }


def enterprise_account(account_id, name, tier, account_owner, finance_owner):
    return {
        "enterprise_account_id": account_id,
        "name": name,
        "tier": tier,
        "account_owner": account_owner,
        "finance_owner": finance_owner,
    }


def incident(incident_id, account_id, product, severity, summary, engineering_owner, account_owner, received):
    return {
        "incident_id": incident_id,
        "enterprise_account_id": account_id,
        "product": product,
        "severity": severity,
        "summary": summary,
        "engineering_owner": engineering_owner,
        "account_owner": account_owner,
        "received_at": received,
        "status": "UNDER_INVESTIGATION",
    }


def export_run(run_id, account_id, incident_id, run_date, status, failure_code="", records=0):
    return {
        "run_id": run_id,
        "enterprise_account_id": account_id,
        "incident_id": incident_id,
        "run_date": run_date,
        "status": status,
        "failure_code": failure_code,
        "exported_record_count": records,
    }


def main() -> None:
    rng = random.Random(SEED)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    accounts = [
        account("ACC-5107", "Northbank Fiber", "Active", service_area="SA-17"),
        account("ACC-5131", "Harborview Media", "Active", service_area="SA-31"),
        account("ACC-5184", "Westmere Clinic", "Active", service_area="SA-44"),
        account("ACC-5202", "Pine Fork Co-op", "Suspended", service_area="SA-52"),
        account("ACC-5401", "Cedar Street Books", "Active", service_area="SA-61"),
        account("ACC-5402", "Lumen Dental", "Active", service_area="SA-62"),
        account("ACC-5404", "Orchid Labs", "Active", auth="FAILURE", recovery="FAILURE", service_area="SA-64"),
        account("ACC-5405", "Moss Hill Studio", "Suspended", service_area="SA-65"),
        account("ACC-5406", "Evergreen Legal", "Active", service_area="SA-66"),
        account("ACC-5407", "Fringe Theater", "Active", service_area="SA-67"),
        account("ACC-6101", "Teralink Press", "Active", service_area="SA-71"),
        account("ACC-6102", "Blue Nine Foods", "Active", auth="FAILURE", recovery="FAILURE", service_area="SA-72"),
        account("ACC-6103", "Meadow City Clinic", "Active", service_area="SA-73"),
        account("ACC-6104", "Canyon Education", "Active", service_area="SA-74"),
        account("ACC-6105", "Juniper Law", "Active", service_area="SA-75"),
    ]
    for idx in range(36):
        accounts.append(
            account(
                f"ACC-{7000 + idx}",
                f"Generated Customer {idx:02d}",
                rng.choice(["Active", "Active", "Suspended"]),
                service_area=f"SA-{80 + idx % 12}",
            )
        )

    tickets = [
        ticket(
            "TCK-5107",
            "ACC-5107",
            "internet",
            300,
            "SA-17",
            "Intermittent internet and poor speed",
            "2026-06-01T08:05:00Z",
        ),
        ticket(
            "TCK-5131",
            "ACC-5131",
            "video",
            750,
            "SA-31",
            "Video stream outage for entire site",
            "2026-06-01T08:12:00Z",
        ),
        ticket(
            "TCK-5184",
            "ACC-5184",
            "internet",
            500,
            "SA-44",
            "Internet latency and packet loss after line work",
            "2026-06-01T08:18:00Z",
        ),
        ticket(
            "TCK-5202",
            "ACC-5202",
            "internet",
            300,
            "SA-52",
            "Cannot connect after account hold notice",
            "2026-06-01T08:26:00Z",
        ),
        ticket(
            "TCK-5401",
            "ACC-5401",
            "internet",
            300,
            "SA-61",
            "Neighborhood service interruption",
            "2026-06-01T07:48:00Z",
        ),
        ticket("TCK-5402", "ACC-5402", "voice", 100, "SA-62", "Voice profile drops calls", "2026-06-01T07:51:00Z"),
        ticket(
            "TCK-5403", "BAD-5403", "internet", 300, "SA-63", "No matching account in intake", "2026-06-01T07:56:00Z"
        ),
        ticket(
            "TCK-5404", "ACC-5404", "video", 750, "SA-64", "Authentication never recovered", "2026-06-01T08:02:00Z"
        ),
        ticket(
            "TCK-5405", "ACC-5405", "internet", 200, "SA-65", "Suspended after overdue notice", "2026-06-01T08:06:00Z"
        ),
        ticket("TCK-5406", "ACC-5406", "internet", 500, "SA-66", "Backbone capacity errors", "2026-06-01T08:11:00Z"),
        ticket(
            "TCK-5407", "ACC-5407", "video", 750, "SA-67", "Provisioning mismatch after move", "2026-06-01T08:15:00Z"
        ),
        ticket("TCK-6101", "ACC-6101", "internet", 300, "SA-71", "Area-wide interruption", "2026-06-01T09:05:00Z"),
        ticket(
            "TCK-6102", "ACC-6102", "video", 750, "SA-72", "Account login validation failed", "2026-06-01T09:08:00Z"
        ),
        ticket(
            "TCK-6103",
            "ACC-6103",
            "voice",
            100,
            "SA-73",
            "Voice quality degraded after profile update",
            "2026-06-01T09:12:00Z",
        ),
        ticket("TCK-6104", "ACC-6104", "internet", 500, "SA-74", "Regional backbone loss", "2026-06-01T09:18:00Z"),
        ticket(
            "TCK-6105", "ACC-6105", "internet", 500, "SA-75", "Fiber drop damage suspected", "2026-06-01T09:21:00Z"
        ),
    ]
    for idx in range(70):
        acc = rng.choice(accounts)["account_id"]
        tickets.append(
            ticket(
                f"TCK-{8000 + idx}",
                acc,
                rng.choice(["internet", "video", "voice"]),
                rng.choice([100, 200, 300, 500, 750]),
                f"SA-{80 + idx % 12}",
                "Generated support ticket",
                "2026-05-31T12:00:00Z",
            )
        )

    outages = [
        outage("OUT-9102", "SA-31", ["video", "internet"], 0.94, 6),
        outage("OUT-9401", "SA-61", ["internet"], 0.88, 4),
        outage("OUT-9601", "SA-71", ["internet", "voice"], 0.91, 8),
    ]
    for idx in range(30):
        outages.append(
            outage(
                f"OUT-{9700 + idx}",
                f"SA-{80 + idx % 12}",
                [rng.choice(["internet", "video", "voice"])],
                round(rng.uniform(0.2, 0.8), 2),
                rng.choice([2, 4, 6, 12]),
                active=rng.choice([True, False, False]),
            )
        )

    diagnostics_records = {
        "TCK-5107": diagnostics("TCK-5107", 142.8, 33.5, 209.0, ["CONFIGURATION_DRIFT"]),
        "TCK-5184": diagnostics("TCK-5184", 188.4, 44.2, 318.0, ["FIBER_DROP_DAMAGE", "SIGNAL_LOSS"]),
        "TCK-5402": diagnostics("TCK-5402", 97.0, 24.0, 61.0, ["VOICE_PROFILE_STALE"]),
        "TCK-5406": diagnostics("TCK-5406", 210.5, 49.7, 285.0, ["BACKBONE_CAPACITY"]),
        "TCK-5407": diagnostics("TCK-5407", 136.0, 34.0, 515.0, ["PROVISIONING_STALE"]),
        "TCK-6103": diagnostics("TCK-6103", 94.0, 22.0, 58.0, ["VOICE_PROFILE_STALE"]),
        "TCK-6104": diagnostics("TCK-6104", 225.0, 52.0, 260.0, ["BACKBONE_CAPACITY"]),
        "TCK-6105": diagnostics("TCK-6105", 184.0, 45.0, 310.0, ["FIBER_DROP_DAMAGE"]),
    }
    troubleshooting_records = {
        "TCK-5107": troubleshooting("TCK-5107", ["PROFILE_REFRESH", "PROVISIONING_SYNC"], 82.0, 21.0, 272.0),
        "TCK-5184": troubleshooting("TCK-5184", ["LINE_TEST", "SIGNAL_REFRESH"], 176.0, 41.0, 332.0),
        "TCK-5402": troubleshooting("TCK-5402", ["VOICE_PROFILE_REFRESH"], 79.0, 18.0, 93.0),
        "TCK-5406": troubleshooting("TCK-5406", ["BACKBONE_REROUTE_ATTEMPT"], 198.0, 43.0, 298.0),
        "TCK-5407": troubleshooting("TCK-5407", ["PROVISIONING_ADJUSTMENT"], 121.0, 32.0, 610.0),
        "TCK-6103": troubleshooting("TCK-6103", ["VOICE_PROFILE_REFRESH"], 78.0, 19.0, 91.0),
        "TCK-6104": troubleshooting("TCK-6104", ["BACKBONE_REROUTE_ATTEMPT"], 206.0, 46.0, 280.0),
        "TCK-6105": troubleshooting("TCK-6105", ["SIGNAL_REFRESH", "LINE_TEST"], 171.0, 40.0, 326.0),
    }
    for t in tickets[:55]:
        diagnostics_records.setdefault(
            t["ticket_id"],
            diagnostics(
                t["ticket_id"], rng.uniform(40, 180), rng.uniform(8, 45), rng.uniform(50, 700), ["GENERATED_NOISE"]
            ),
        )
        troubleshooting_records.setdefault(
            t["ticket_id"],
            troubleshooting(
                t["ticket_id"], ["GENERATED_CHECK"], rng.uniform(40, 160), rng.uniform(8, 42), rng.uniform(50, 730)
            ),
        )

    plans = [
        plan("PLAN-BASIC", "Basic 5", 5.0, 40.0, 5.0),
        plan("PLAN-PREMIUM", "Premium 15", 15.0, 65.0, 2.0),
        plan("PLAN-PLUS", "Unlimited Plus", 999.0, 85.0, 0.1),
        plan("PLAN-FAMILY", "Family Share", 25.0, 120.0, 3.0),
    ]
    for idx in range(8):
        plans.append(
            plan(
                f"PLAN-G{idx}",
                f"Generated Plan {idx}",
                rng.choice([1, 5, 10, 20, 50]),
                rng.choice([15, 35, 55, 75]),
                rng.choice([1.5, 2.0, 3.0, 5.0]),
            )
        )

    customers = []
    lines = []
    devices = []
    bills = []
    cases = []

    def add_case(
        case_id,
        phone,
        issue_type,
        summary,
        dev_state,
        line_state=None,
        bill_state=None,
        plan_id="PLAN-PREMIUM",
        data_used=4.0,
        location="home",
    ):
        num = case_id.split("-")[1]
        cust_id = f"CUST-{num}"
        line_id = f"LINE-{num}"
        dev_id = f"DEV-{num}"
        customers.append(
            {"customer_id": cust_id, "name": f"Case Customer {num}", "phone_number": phone, "status": "Active"}
        )
        devices.append(device(dev_id, "Pixel Work", **dev_state))
        line_kwargs = line_state or {}
        lines.append(line(line_id, cust_id, phone, plan_id, dev_id, data_used=data_used, **line_kwargs))
        if bill_state:
            bills.append(bill_state)
        else:
            bills.append(bill(f"BILL-{num}", cust_id, 0.0, "Paid"))
        cases.append(case(case_id, cust_id, line_id, dev_id, issue_type, summary, location))

    add_case(
        "CASE-2101",
        "555-2101",
        "NO_SERVICE",
        "Phone shows no service after a commute.",
        {"sim_status": "missing", "signal_strength": "none", "speed_test": "no_connection", "can_send_mms": False},
    )
    add_case(
        "CASE-2102",
        "555-2102",
        "NO_SERVICE",
        "Line is suspended and user will pay overdue amount.",
        {"signal_strength": "none", "speed_test": "no_connection"},
        {"status": "Suspended", "suspension_reason": "OVERDUE_BILL"},
        bill("BILL-2102", "CUST-2102", 86.40, "Overdue"),
    )
    add_case(
        "CASE-2103",
        "555-2103",
        "MOBILE_DATA",
        "Traveler cannot use mobile data abroad.",
        {"phone_roaming_enabled": False, "speed_test": "no_connection"},
        {"roaming": True},
        location="abroad",
    )
    add_case(
        "CASE-2104",
        "555-2104",
        "MMS",
        "Messaging app cannot send photos.",
        {"messaging_permissions": {"sms": True, "storage": False}, "can_send_mms": False},
    )
    add_case(
        "CASE-2105",
        "555-2105",
        "SLOW_DATA",
        "Mobile data works but is slow.",
        {"vpn_connected": True, "speed_test": "poor"},
    )
    add_case(
        "CASE-2501",
        "555-2501",
        "MOBILE_DATA",
        "Data stopped after usage limit.",
        {"speed_test": "no_connection"},
        {"roaming": True},
        None,
        "PLAN-PREMIUM",
        data_used=16.2,
    )
    add_case(
        "CASE-2502",
        "555-2502",
        "MOBILE_DATA",
        "Traveler has roaming on phone but no data.",
        {"phone_roaming_enabled": True, "speed_test": "no_connection"},
        {"roaming": False},
        location="abroad",
    )
    add_case(
        "CASE-2503",
        "555-2503",
        "SLOW_DATA",
        "Slow data and data-saver icon visible.",
        {"data_saver_mode": True, "speed_test": "fair"},
    )
    add_case(
        "CASE-2504",
        "555-2504",
        "SLOW_DATA",
        "Slow data on older network mode.",
        {"network_mode_preference": "3g_only", "speed_test": "poor"},
    )
    add_case(
        "CASE-2505",
        "555-2505",
        "MOBILE_DATA",
        "No data after settings change.",
        {"mobile_data_enabled": False, "speed_test": "no_connection"},
    )
    add_case(
        "CASE-3101",
        "555-3101",
        "NO_SERVICE",
        "SIM locked after repeated PIN attempts.",
        {"sim_status": "locked_pin", "signal_strength": "none", "speed_test": "no_connection"},
    )
    add_case(
        "CASE-3102",
        "555-3102",
        "NO_SERVICE",
        "Line suspended after contract ended.",
        {"signal_strength": "none", "speed_test": "no_connection"},
        {"status": "Suspended", "suspension_reason": "CONTRACT_ENDED", "contract_end": "2026-04-30"},
    )
    add_case(
        "CASE-3103",
        "555-3103",
        "MMS",
        "MMS fails after APN profile edit.",
        {"mmsc_url_present": False, "can_send_mms": False},
    )
    add_case(
        "CASE-3104",
        "555-3104",
        "MOBILE_DATA",
        "Data stopped after the shared allowance was exceeded.",
        {"speed_test": "no_connection"},
        data_used=16.8,
    )
    add_case(
        "CASE-3105",
        "555-3105",
        "MOBILE_DATA",
        "Traveler abroad has no data despite phone roaming on.",
        {"phone_roaming_enabled": True, "speed_test": "no_connection"},
        {"roaming": False},
        location="abroad",
    )

    for idx in range(42):
        cust_id = f"CUST-G{idx:03d}"
        dev_id = f"DEV-G{idx:03d}"
        line_id = f"LINE-G{idx:03d}"
        customers.append(
            {
                "customer_id": cust_id,
                "name": f"Generated Mobile Customer {idx}",
                "phone_number": f"555-7{idx:03d}",
                "status": "Active",
            }
        )
        devices.append(
            device(
                dev_id, rng.choice(["Pixel", "Galaxy", "iPhone"]), speed_test=rng.choice(["excellent", "good", "fair"])
            )
        )
        lines.append(
            line(
                line_id,
                cust_id,
                f"555-7{idx:03d}",
                rng.choice(plans)["plan_id"],
                dev_id,
                data_used=round(rng.uniform(0, 20), 1),
            )
        )
        bills.append(
            bill(f"BILL-G{idx:03d}", cust_id, round(rng.uniform(20, 140), 2), rng.choice(["Paid", "Paid", "Issued"]))
        )

    enterprise_accounts = [
        enterprise_account("ENT-3001", "Asteri Retail Inc.", "Enterprise", "stephany.lo", "laura.brown"),
        enterprise_account("ENT-4001", "Quanta Ledger Group", "Strategic", "omar.chen", "maya.patel"),
        enterprise_account("ENT-4102", "Helio Metrics", "Enterprise", "jules.martin", "nora.yu"),
    ]
    for idx in range(8):
        enterprise_accounts.append(
            enterprise_account(
                f"ENT-{5000 + idx}",
                f"Generated Enterprise {idx}",
                rng.choice(["Enterprise", "Strategic"]),
                "acct.owner",
                "finance.owner",
            )
        )

    incidents = [
        incident(
            "INC-7301",
            "ENT-3001",
            "monthly_export",
            "Critical",
            "Monthly export failed for three consecutive days.",
            "delana.rao",
            "stephany.lo",
            "2026-05-15T13:40:00Z",
        ),
        incident(
            "INC-8301",
            "ENT-4001",
            "monthly_export",
            "Critical",
            "Month-end export staging failed for four consecutive days.",
            "priya.shah",
            "omar.chen",
            "2026-05-29T09:10:00Z",
        ),
        incident(
            "INC-8402",
            "ENT-4102",
            "dashboard_refresh",
            "High",
            "Dashboard refresh delayed after export retry.",
            "marin.kim",
            "jules.martin",
            "2026-05-28T12:20:00Z",
        ),
    ]
    generated_incidents = []
    for idx in range(14):
        generated_incidents.append(
            incident(
                f"INC-{9000 + idx}",
                rng.choice(enterprise_accounts)["enterprise_account_id"],
                "generated_product",
                rng.choice(["Medium", "High"]),
                "Generated enterprise incident.",
                "eng.owner",
                "acct.owner",
                "2026-05-20T10:00:00Z",
            )
        )
    incidents.extend(generated_incidents)

    export_runs = []
    for i, day in enumerate(["2026-05-12", "2026-05-13", "2026-05-14"]):
        export_runs.append(export_run(f"RUN-AST-{i}", "ENT-3001", "INC-7301", day, "FAILED", "STALE_CREDENTIAL", 0))
    export_runs.append(export_run("RUN-AST-3", "ENT-3001", "INC-7301", "2026-05-15", "SUCCEEDED", "", 124803))
    for i, day in enumerate(["2026-05-25", "2026-05-26", "2026-05-27", "2026-05-28"]):
        export_runs.append(
            export_run(f"RUN-QUA-{i}", "ENT-4001", "INC-8301", day, "FAILED", "STAGING_STORAGE_QUOTA", 0)
        )
    export_runs.append(export_run("RUN-QUA-4", "ENT-4001", "INC-8301", "2026-05-29", "SUCCEEDED", "", 320118))
    for idx in range(80):
        generated_incident = rng.choice(generated_incidents)
        export_runs.append(
            export_run(
                f"RUN-G{idx:03d}",
                generated_incident["enterprise_account_id"],
                generated_incident["incident_id"],
                f"2026-05-{1 + idx % 28:02d}",
                rng.choice(["SUCCEEDED", "SUCCEEDED", "FAILED"]),
                rng.choice(["", "RATE_LIMIT", "TIMEOUT"]),
                rng.randint(2000, 90000),
            )
        )

    messages = [
        {
            "message_id": "MSG-7301-A",
            "channel": "export-alerts-archive",
            "author": "delana.rao",
            "body": "Asteri export worker credential rotation completed; scheduler pod still references old secret.",
            "created_at": "2026-05-12T09:20:00Z",
        },
        {
            "message_id": "MSG-7301-B",
            "channel": "account-escalations",
            "author": "stephany.lo",
            "body": "Asteri contract requires 15 percent SLA credit after three consecutive failed monthly export runs.",
            "created_at": "2026-05-15T14:05:00Z",
        },
        {
            "message_id": "MSG-8301-A",
            "channel": "data-platform",
            "author": "priya.shah",
            "body": "Quanta export staging bucket reached quota during month-end run; four days require manual backfill.",
            "created_at": "2026-05-29T10:20:00Z",
        },
        {
            "message_id": "MSG-8301-B",
            "channel": "account-escalations",
            "author": "omar.chen",
            "body": "Quanta strategic contract uses 20 percent SLA credit for critical export outage longer than 72 hours.",
            "created_at": "2026-05-29T11:00:00Z",
        },
    ]
    for idx in range(60):
        messages.append(
            {
                "message_id": f"MSG-G{idx:03d}",
                "channel": rng.choice(["support", "data-platform", "account-escalations"]),
                "author": "generated.user",
                "body": f"Generated support message {idx}",
                "created_at": "2026-05-20T10:00:00Z",
            }
        )

    sla_contracts = [
        {
            "enterprise_account_id": "ENT-3001",
            "monthly_export_credit_percent": 15,
            "credit_trigger": "3 consecutive failed export runs",
            "executive_contact": "maya.singh@asteri.example",
        },
        {
            "enterprise_account_id": "ENT-4001",
            "monthly_export_credit_percent": 20,
            "credit_trigger": "critical export outage longer than 72 hours",
            "executive_contact": "liam.park@quanta.example",
        },
        {
            "enterprise_account_id": "ENT-4102",
            "monthly_export_credit_percent": 10,
            "credit_trigger": "missed dashboard refresh SLA",
            "executive_contact": "ren.ito@helio.example",
        },
    ]
    for ent in enterprise_accounts[3:]:
        sla_contracts.append(
            {
                "enterprise_account_id": ent["enterprise_account_id"],
                "monthly_export_credit_percent": rng.choice([5, 10, 15]),
                "credit_trigger": "generated terms",
                "executive_contact": "generated@example.com",
            }
        )

    data = {
        "accounts": accounts,
        "tickets": tickets,
        "outages": outages,
        "diagnostics": list(diagnostics_records.values()),
        "troubleshooting": list(troubleshooting_records.values()),
        "plans": plans,
        "customers": customers,
        "lines": lines,
        "devices": devices,
        "bills": bills,
        "cases": cases,
        "enterprise_accounts": enterprise_accounts,
        "enterprise_incidents": incidents,
        "export_runs": export_runs,
        "messages": messages,
        "sla_contracts": sla_contracts,
    }

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_counts": {k: len(v) for k, v in data.items()},
        "endpoints": [
            "/health",
            "/api/catalog",
            "/api/accounts",
            "/api/accounts/<account_id>",
            "/api/tickets",
            "/api/tickets/<ticket_id>",
            "/api/outages",
            "/api/diagnostics/<ticket_id>",
            "/api/troubleshooting/<ticket_id>",
            "/api/customers",
            "/api/lines",
            "/api/lines/<line_id>",
            "/api/devices/<device_id>",
            "/api/plans/<plan_id>",
            "/api/bills",
            "/api/cases",
            "/api/cases/<case_id>",
            "/api/enterprise/accounts",
            "/api/enterprise/incidents",
            "/api/enterprise/export-runs",
            "/api/enterprise/messages",
            "/api/enterprise/sla/<enterprise_account_id>",
        ],
        "notes": "Public support-console catalog. It lists endpoints and aggregate record counts only; task targets and construction seeds are not exposed.",
    }

    (DATA_DIR / "support_data.json").write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    (DATA_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {DATA_DIR / 'support_data.json'}")
    print(f"Wrote {DATA_DIR / 'manifest.json'}")


if __name__ == "__main__":
    main()
