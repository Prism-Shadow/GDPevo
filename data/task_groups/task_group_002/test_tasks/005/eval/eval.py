#!/usr/bin/env python3
import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path


EXPECTED_PHASES = {
    "MS1": {
        "source_phase_id": "SUN-P1",
        "amount": "40000.00",
        "invoice_state": "PAID",
        "payment_state": "PAID",
        "paid_amount": "40000.00",
        "unpaid_amount": "0.00",
        "due_date": None,
        "recognition_status": "RECOGNIZED",
    },
    "MS2": {
        "source_phase_id": "SUN-P2",
        "amount": "35000.00",
        "invoice_state": "PAID",
        "payment_state": "PAID",
        "paid_amount": "35000.00",
        "unpaid_amount": "0.00",
        "due_date": None,
        "recognition_status": "MISSING_REVENUE_JOURNAL",
    },
    "MS3": {
        "source_phase_id": "SUN-P3",
        "amount": "45000.00",
        "invoice_state": "OPEN",
        "payment_state": "UNPAID",
        "paid_amount": "0.00",
        "unpaid_amount": "45000.00",
        "due_date": "2026-07-01",
        "recognition_status": "NOT_REQUIRED_UNPAID",
    },
}


def get_path(data, path, default=None):
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def norm_text(value):
    if value is None:
        return ""
    return str(value).strip()


def norm_enum(value):
    return norm_text(value).upper()


def norm_money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return None


def money_eq(value, expected):
    return norm_money(value) == Decimal(expected)


def int_eq(value, expected):
    try:
        return int(value) == expected
    except (TypeError, ValueError):
        return False


def bool_is(value, expected):
    return value is expected


def phase_map(data):
    milestones = get_path(data, ["engagement_reconciliation", "milestones"], [])
    if not isinstance(milestones, list):
        return {}
    return {norm_enum(item.get("milestone_id")): item for item in milestones if isinstance(item, dict)}


def phase_sum_matches(data):
    phases = phase_map(data)
    total = Decimal("0.00")
    for phase_id in ("MS1", "MS2", "MS3"):
        amount = norm_money(phases.get(phase_id, {}).get("amount"))
        if amount is None:
            return False
        total += amount
    return total == Decimal("120000.00")


def check_phase_sum_and_opportunity_total(data):
    eng = get_path(data, ["engagement_reconciliation"], {})
    return all(
        [
            eng.get("as_of_date") == "2026-06-01",
            norm_text(eng.get("opportunity_id")) == "OPP-TE-SUNRISE",
            norm_text(eng.get("customer_id")) == "CUST-SUNRISE",
            norm_enum(eng.get("stage")) == "WON",
            money_eq(eng.get("won_amount"), "120000.00"),
            money_eq(eng.get("phase_total_amount"), "120000.00"),
            bool_is(eng.get("opportunity_matches_phase_total"), True),
            phase_sum_matches(data),
        ]
    )


def check_paid_unpaid_invoice_state(data):
    phases = phase_map(data)
    for phase_id, expected in EXPECTED_PHASES.items():
        phase = phases.get(phase_id, {})
        if norm_text(phase.get("source_phase_id")) != expected["source_phase_id"]:
            return False
        if not money_eq(phase.get("amount"), expected["amount"]):
            return False
        if norm_enum(phase.get("invoice_state")) != expected["invoice_state"]:
            return False
        if norm_enum(phase.get("payment_state")) != expected["payment_state"]:
            return False
        if not money_eq(phase.get("paid_amount"), expected["paid_amount"]):
            return False
        if not money_eq(phase.get("unpaid_amount"), expected["unpaid_amount"]):
            return False
        if phase.get("due_date") != expected["due_date"]:
            return False
    return True


def check_missing_revenue_recognition_action(data):
    phases = phase_map(data)
    accounting = get_path(data, ["invoice_actions", "accounting_action"], {})
    for phase_id, expected in EXPECTED_PHASES.items():
        phase = phases.get(phase_id, {})
        if norm_enum(phase.get("recognition_status")) != expected["recognition_status"]:
            return False
    return all(
        [
            norm_enum(accounting.get("action")) == "RECORD_REVENUE_MS2",
            norm_enum(accounting.get("milestone_id")) == "MS2",
            money_eq(accounting.get("amount"), "35000.00"),
            accounting.get("due_date") == "2026-06-01",
            norm_enum(accounting.get("debit_account")) == "DEFERRED_REVENUE",
            norm_enum(accounting.get("credit_account")) == "IMPLEMENTATION_SERVICES_REVENUE",
            norm_enum(accounting.get("owner_queue")) == "ACCOUNTING",
        ]
    )


def check_outstanding_balance(data):
    eng = get_path(data, ["engagement_reconciliation"], {})
    collection = get_path(data, ["invoice_actions", "collection_task"], {})
    return all(
        [
            money_eq(eng.get("total_paid_amount"), "75000.00"),
            money_eq(eng.get("outstanding_balance"), "45000.00"),
            norm_enum(collection.get("milestone_id")) == "MS3",
            money_eq(collection.get("amount"), "45000.00"),
            collection.get("due_date") == "2026-07-01",
        ]
    )


def check_training_event_voucher_facts(data):
    event = get_path(data, ["event_actions"], {})
    voucher = get_path(data, ["event_actions", "voucher"], {})
    return all(
        [
            norm_text(event.get("event_id")) == "EVT-SUNRISE-TRAINING",
            event.get("event_date") == "2026-06-20",
            norm_enum(event.get("event_status")) == "LIVE",
            norm_text(voucher.get("voucher_code")) == "SUNRISESTAFF100",
            norm_enum(voucher.get("voucher_status")) == "ACTIVE",
            money_eq(voucher.get("discount_amount"), "100.00"),
            int_eq(voucher.get("max_uses"), 25),
        ]
    )


def check_crm_follow_up_task_routing(data):
    collection = get_path(data, ["invoice_actions", "collection_task"], {})
    invite = get_path(data, ["event_actions", "invite_task"], {})
    return all(
        [
            norm_enum(collection.get("action")) == "MONITOR_UNPAID_NOT_DUE",
            norm_enum(collection.get("milestone_id")) == "MS3",
            norm_enum(collection.get("owner_queue")) == "ACCOUNT_MANAGEMENT",
            norm_text(collection.get("contact_name")) == "Priya Raman",
            norm_text(collection.get("customer_id")) == "CUST-SUNRISE",
            norm_text(collection.get("opportunity_id")) == "OPP-TE-SUNRISE",
            norm_enum(invite.get("action")) == "SEND_TRAINING_INVITE",
            invite.get("due_date") == "2026-06-10",
            norm_text(invite.get("event_id")) == "EVT-SUNRISE-TRAINING",
            norm_text(invite.get("voucher_code")) == "SUNRISESTAFF100",
            norm_enum(invite.get("owner_queue")) == "ACCOUNT_MANAGEMENT",
            norm_text(invite.get("contact_name")) == "Priya Raman",
            norm_text(invite.get("customer_id")) == "CUST-SUNRISE",
            norm_text(invite.get("opportunity_id")) == "OPP-TE-SUNRISE",
        ]
    )


def check_collection_versus_accounting_action_enum(data):
    invoice_actions = get_path(data, ["invoice_actions"], {})
    accounting = get_path(data, ["invoice_actions", "accounting_action"], {})
    collection = get_path(data, ["invoice_actions", "collection_task"], {})
    event = get_path(data, ["event_actions"], {})
    invite = get_path(data, ["event_actions", "invite_task"], {})
    return all(
        [
            norm_enum(invoice_actions.get("primary_accounting_action")) == "RECORD_REVENUE_MS2",
            norm_enum(accounting.get("action")) == "RECORD_REVENUE_MS2",
            norm_enum(invoice_actions.get("collection_action")) == "MONITOR_UNPAID_NOT_DUE",
            norm_enum(collection.get("action")) == "MONITOR_UNPAID_NOT_DUE",
            norm_enum(event.get("invite_action")) == "SEND_TRAINING_INVITE",
            norm_enum(invite.get("action")) == "SEND_TRAINING_INVITE",
        ]
    )


def reconciliation_controls(data):
    controls = get_path(data, ["invoice_actions", "reconciliation_controls"], {})
    return controls if isinstance(controls, dict) else {}


def check_paid_due_date_policy(data):
    return norm_enum(reconciliation_controls(data).get("paid_milestone_due_date_policy")) == "NULL_WHEN_SETTLED"


def check_recognition_trigger_policy(data):
    return norm_enum(reconciliation_controls(data).get("recognition_trigger")) == "PAID_COMPLETE_MILESTONES"


def check_unpaid_future_policy(data):
    return norm_enum(reconciliation_controls(data).get("unpaid_future_policy")) == "MONITOR_NOT_COLLECT"


def check_action_priority_policy(data):
    return norm_enum(reconciliation_controls(data).get("action_priority")) == "ACCOUNTING_BEFORE_COLLECTION"


def check_contact_linkage(data):
    eng = get_path(data, ["engagement_reconciliation"], {})
    contact = get_path(data, ["engagement_reconciliation", "primary_contact"], {})
    collection = get_path(data, ["invoice_actions", "collection_task"], {})
    invite = get_path(data, ["event_actions", "invite_task"], {})
    return all(
        [
            norm_text(eng.get("customer_name")) == "Sunrise Relief Network",
            norm_text(contact.get("contact_name")) == "Priya Raman",
            norm_text(contact.get("customer_id")) == "CUST-SUNRISE",
            norm_text(contact.get("opportunity_id")) == "OPP-TE-SUNRISE",
            norm_text(collection.get("contact_name")) == "Priya Raman",
            norm_text(collection.get("customer_id")) == "CUST-SUNRISE",
            norm_text(collection.get("opportunity_id")) == "OPP-TE-SUNRISE",
            norm_text(invite.get("contact_name")) == "Priya Raman",
            norm_text(invite.get("customer_id")) == "CUST-SUNRISE",
            norm_text(invite.get("opportunity_id")) == "OPP-TE-SUNRISE",
        ]
    )


CHECKS = [
    ("phase_sum_and_opportunity_total", 2, check_phase_sum_and_opportunity_total),
    ("paid_unpaid_invoice_state", 3, check_paid_unpaid_invoice_state),
    ("missing_revenue_recognition_action", 3, check_missing_revenue_recognition_action),
    ("outstanding_balance", 2, check_outstanding_balance),
    ("training_event_voucher_facts", 2, check_training_event_voucher_facts),
    ("crm_follow_up_task_routing", 2, check_crm_follow_up_task_routing),
    ("collection_versus_accounting_action_enum", 2, check_collection_versus_accounting_action_enum),
    ("paid_due_date_policy_control", 3, check_paid_due_date_policy),
    ("recognition_trigger_policy_control", 3, check_recognition_trigger_policy),
    ("unpaid_future_policy_control", 3, check_unpaid_future_policy),
    ("action_priority_policy_control", 3, check_action_priority_policy),
    ("contact_linkage", 1, check_contact_linkage),
]


def blank_checks():
    return [
        {
            "name": name,
            "weight": weight,
            "passed": False,
            "earned": 0,
        }
        for name, weight, _ in CHECKS
    ]


def score(data):
    total = sum(weight for _, weight, _ in CHECKS)
    details = []
    earned = 0
    for name, weight, func in CHECKS:
        passed = bool(func(data))
        if passed:
            earned += weight
        details.append(
            {
                "name": name,
                "weight": weight,
                "passed": passed,
                "earned": weight if passed else 0,
            }
        )
    return {
        "score": earned / total,
        "earned": earned,
        "total": total,
        "checks": details,
    }


def main():
    script_dir = Path(__file__).resolve().parent
    candidate_path = Path(sys.argv[1]) if len(sys.argv) > 1 else script_dir / "../output/answer.json"
    try:
        with candidate_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "earned": 0,
                    "total": sum(weight for _, weight, _ in CHECKS),
                    "error": f"Could not read candidate JSON: {exc}",
                    "checks": blank_checks(),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    print(json.dumps(score(data), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
