#!/usr/bin/env python3
import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


EXPECTED_PHASES = {
    "MS1": {
        "amount": "30000.00",
        "invoice_state": "PAID",
        "payment_state": "PAID",
        "paid_amount": "30000.00",
        "due_date": None,
        "recognition_status": "RECOGNIZED",
    },
    "MS2": {
        "amount": "45000.00",
        "invoice_state": "PAID",
        "payment_state": "PAID",
        "paid_amount": "45000.00",
        "due_date": None,
        "recognition_status": "MISSING_REVENUE_JOURNAL",
    },
    "MS3": {
        "amount": "25000.00",
        "invoice_state": "OPEN",
        "payment_state": "UNPAID",
        "paid_amount": "0.00",
        "due_date": "2026-07-15",
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
    return total == Decimal("100000.00")


def check_opportunity_equals_phases(data):
    eng = get_path(data, ["engagement_reconciliation"], {})
    return all(
        [
            norm_text(eng.get("opportunity_id")) == "OPP-TR-MERIDIAN",
            norm_text(eng.get("customer_id")) == "CUST-MERIDIAN",
            norm_enum(eng.get("stage")) == "WON",
            money_eq(eng.get("won_amount"), "100000.00"),
            money_eq(eng.get("phase_total_amount"), "100000.00"),
            bool_is(eng.get("opportunity_matches_phase_total"), True),
            phase_sum_matches(data),
        ]
    )


def check_invoice_payment_states(data):
    phases = phase_map(data)
    for phase_id, expected in EXPECTED_PHASES.items():
        phase = phases.get(phase_id, {})
        if not money_eq(phase.get("amount"), expected["amount"]):
            return False
        if norm_enum(phase.get("invoice_state")) != expected["invoice_state"]:
            return False
        if norm_enum(phase.get("payment_state")) != expected["payment_state"]:
            return False
        if not money_eq(phase.get("paid_amount"), expected["paid_amount"]):
            return False
        if phase.get("due_date") != expected["due_date"]:
            return False
    return True


def check_outstanding_balance(data):
    eng = get_path(data, ["engagement_reconciliation"], {})
    collection = get_path(data, ["invoice_actions", "collection_task"], {})
    return all(
        [
            money_eq(eng.get("total_paid_amount"), "75000.00"),
            money_eq(eng.get("outstanding_balance"), "25000.00"),
            norm_enum(collection.get("milestone_id")) == "MS3",
            money_eq(collection.get("amount"), "25000.00"),
            collection.get("due_date") == "2026-07-15",
        ]
    )


def check_revenue_recognition_status(data):
    phases = phase_map(data)
    for phase_id, expected in EXPECTED_PHASES.items():
        phase = phases.get(phase_id, {})
        if norm_enum(phase.get("recognition_status")) != expected["recognition_status"]:
            return False
    return True


def check_event_voucher_state(data):
    event = get_path(data, ["event_actions"], {})
    voucher = get_path(data, ["event_actions", "voucher"], {})
    return all(
        [
            norm_text(event.get("event_id")) == "EVT-MERIDIAN-BRIEFING",
            norm_enum(event.get("event_status")) == "SCHEDULED",
            norm_text(voucher.get("voucher_code")) == "MERIDIANBRIEF50",
            norm_enum(voucher.get("voucher_status")) == "ACTIVE",
            money_eq(voucher.get("discount_amount"), "50.00"),
            int_eq(voucher.get("max_uses"), 20),
        ]
    )


def check_crm_action_routing(data):
    invoice_actions = get_path(data, ["invoice_actions"], {})
    accounting = get_path(data, ["invoice_actions", "accounting_action"], {})
    collection = get_path(data, ["invoice_actions", "collection_task"], {})
    event = get_path(data, ["event_actions"], {})
    invite = get_path(data, ["event_actions", "invite_task"], {})
    return all(
        [
            norm_enum(invoice_actions.get("primary_accounting_action")) == "RECORD_REVENUE_MS2",
            norm_enum(accounting.get("action")) == "RECORD_REVENUE_MS2",
            norm_enum(accounting.get("milestone_id")) == "MS2",
            norm_enum(accounting.get("owner_queue")) == "ACCOUNTING",
            norm_enum(invoice_actions.get("collection_action")) == "MONITOR_UNPAID_NOT_DUE",
            norm_enum(collection.get("action")) == "MONITOR_UNPAID_NOT_DUE",
            norm_enum(collection.get("milestone_id")) == "MS3",
            norm_enum(collection.get("owner_queue")) == "ACCOUNT_MANAGEMENT",
            norm_enum(event.get("invite_action")) == "SEND_BRIEFING_INVITE",
            norm_enum(invite.get("action")) == "SEND_BRIEFING_INVITE",
            norm_text(invite.get("event_id")) == "EVT-MERIDIAN-BRIEFING",
            norm_text(invite.get("voucher_code")) == "MERIDIANBRIEF50",
            norm_enum(invite.get("owner_queue")) == "ACCOUNT_MANAGEMENT",
        ]
    )


def check_deferred_revenue_account_action(data):
    accounting = get_path(data, ["invoice_actions", "accounting_action"], {})
    return all(
        [
            norm_enum(accounting.get("action")) == "RECORD_REVENUE_MS2",
            norm_enum(accounting.get("milestone_id")) == "MS2",
            money_eq(accounting.get("amount"), "45000.00"),
            norm_enum(accounting.get("debit_account")) == "DEFERRED_REVENUE",
            norm_enum(accounting.get("credit_account")) == "IMPLEMENTATION_SERVICES_REVENUE",
        ]
    )


def check_contact_linkage(data):
    eng = get_path(data, ["engagement_reconciliation"], {})
    contact = get_path(data, ["engagement_reconciliation", "primary_contact"], {})
    collection = get_path(data, ["invoice_actions", "collection_task"], {})
    invite = get_path(data, ["event_actions", "invite_task"], {})
    return all(
        [
            norm_text(eng.get("customer_name")) == "Meridian Public Health",
            norm_text(contact.get("contact_name")) == "Daniel Rees",
            norm_text(contact.get("customer_id")) == "CUST-MERIDIAN",
            norm_text(collection.get("contact_name")) == "Daniel Rees",
            norm_text(invite.get("contact_name")) == "Daniel Rees",
            norm_text(invite.get("customer_id")) == "CUST-MERIDIAN",
        ]
    )


CHECKS = [
    ("opportunity_equals_phases", 2, check_opportunity_equals_phases),
    ("invoice_payment_states", 3, check_invoice_payment_states),
    ("outstanding_balance", 3, check_outstanding_balance),
    ("revenue_recognition_missing_present_status", 2, check_revenue_recognition_status),
    ("event_voucher_state", 2, check_event_voucher_state),
    ("crm_action_routing", 2, check_crm_action_routing),
    ("deferred_revenue_account_action", 1, check_deferred_revenue_account_action),
    ("contact_linkage", 1, check_contact_linkage),
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
    candidate_path = sys.argv[1] if len(sys.argv) > 1 else "../output/answer.json"
    try:
        with open(candidate_path, encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "earned": 0,
                    "total": sum(weight for _, weight, _ in CHECKS),
                    "error": f"Could not read candidate JSON: {exc}",
                    "checks": [
                        {
                            "name": name,
                            "weight": weight,
                            "passed": False,
                            "earned": 0,
                        }
                        for name, weight, _ in CHECKS
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    print(json.dumps(score(data), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
