#!/usr/bin/env python3
import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path


EXPECTED = {
    "as_of_date": "2026-06-01",
    "customer_id": "CUST-POLARIS",
    "customer_name": "Polaris Cold Chain",
    "opportunity_id": "OPP-TE-POLARIS",
    "stage": "WON",
    "won_amount": "120000.00",
    "contact_name": "Amara Singh",
    "outstanding_balance": "58000.00",
    "milestones": {
        "MS1": {
            "source_phase_id": "POL-P1",
            "phase_number": 1,
            "invoice_id": "INV-POLARIS-P1",
            "invoice_total": "62000.00",
            "payment_status": "PAID",
            "amount_paid": "62000.00",
            "amount_unpaid": "0.00",
            "due_date": None,
            "overdue": False,
            "revenue_recognition_status": "RECOGNIZED",
        },
        "MS2": {
            "source_phase_id": "POL-P2",
            "phase_number": 2,
            "invoice_id": "INV-POLARIS-P2",
            "invoice_total": "58000.00",
            "payment_status": "UNPAID",
            "amount_paid": "0.00",
            "amount_unpaid": "58000.00",
            "due_date": "2026-05-20",
            "overdue": True,
            "revenue_recognition_status": "NOT_REQUIRED_UNPAID",
        },
    },
    "event": {
        "event_id": "EVT-POLARIS-GALA",
        "event_date": "2026-06-18",
        "event_status": "LIVE",
        "voucher_code": "POLARIS100VIP",
        "voucher_discount": "100.00",
        "voucher_max_uses": 3,
    },
}


def norm_text(value):
    if value is None:
        return None
    return str(value).strip()


def norm_enum(value):
    if value is None:
        return None
    return str(value).strip().upper()


def norm_money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return None


def money_eq(value, expected):
    return norm_money(value) == Decimal(expected)


def int_eq(value, expected):
    try:
        return int(value) == int(expected)
    except (TypeError, ValueError):
        return False


def bool_is(value, expected):
    return value is expected


def list_eq(actual, expected):
    if not isinstance(actual, list):
        return False
    return sorted(norm_text(item) for item in actual) == sorted(expected)


def milestone_map(data):
    mapped = {}
    for item in data.get("milestones", []):
        if isinstance(item, dict) and item.get("milestone_id"):
            mapped[norm_enum(item["milestone_id"])] = item
    return mapped


def task_map(data):
    mapped = {}
    for item in data.get("follow_up_tasks", []):
        if isinstance(item, dict) and item.get("task_type"):
            mapped[norm_enum(item["task_type"])] = item
    return mapped


def add(points, point_id, weight, passed):
    points.append(
        {
            "id": point_id,
            "weight": weight,
            "passed": bool(passed),
            "earned_weight": weight if passed else 0,
        }
    )


def check_account_identity(data):
    status = data.get("account_status", {})
    return all(
        [
            norm_text(status.get("as_of_date")) == EXPECTED["as_of_date"],
            norm_text(status.get("customer_id")) == EXPECTED["customer_id"],
            norm_text(status.get("customer_name")) == EXPECTED["customer_name"],
            norm_text(status.get("opportunity_id")) == EXPECTED["opportunity_id"],
            norm_enum(status.get("opportunity_stage")) == EXPECTED["stage"],
            money_eq(status.get("won_amount"), EXPECTED["won_amount"]),
        ]
    )


def check_reporting_labels_and_totals(data):
    milestones = milestone_map(data)
    if set(milestones) != set(EXPECTED["milestones"]):
        return False
    total = Decimal("0.00")
    for mid, expected in EXPECTED["milestones"].items():
        actual = milestones.get(mid, {})
        if norm_text(actual.get("source_phase_id")) != expected["source_phase_id"]:
            return False
        if not int_eq(actual.get("phase_number"), expected["phase_number"]):
            return False
        if norm_text(actual.get("invoice_id")) != expected["invoice_id"]:
            return False
        if not money_eq(actual.get("invoice_total"), expected["invoice_total"]):
            return False
        total += Decimal(expected["invoice_total"])
    return (
        total == Decimal(EXPECTED["won_amount"])
        and data.get("account_status", {}).get("opportunity_matches_milestones") is True
    )


def check_payment_balance(data):
    milestones = milestone_map(data)
    for mid, expected in EXPECTED["milestones"].items():
        actual = milestones.get(mid, {})
        if norm_enum(actual.get("payment_status")) != expected["payment_status"]:
            return False
        if not money_eq(actual.get("amount_paid"), expected["amount_paid"]):
            return False
        if not money_eq(actual.get("amount_unpaid"), expected["amount_unpaid"]):
            return False
    return money_eq(data.get("account_status", {}).get("outstanding_balance"), EXPECTED["outstanding_balance"])


def check_due_dates_and_collection(data):
    milestones = milestone_map(data)
    task = task_map(data).get("COLLECTION", {})
    return all(
        [
            milestones.get("MS1", {}).get("due_date") is None,
            norm_text(milestones.get("MS2", {}).get("due_date")) == "2026-05-20",
            bool_is(milestones.get("MS2", {}).get("overdue"), True),
            norm_enum(task.get("next_action")) == "ESCALATE_COLLECTION",
            norm_text(task.get("milestone_id")) == "MS2",
            norm_text(task.get("due_date")) == "2026-06-01",
            money_eq(task.get("amount_due"), EXPECTED["outstanding_balance"]),
        ]
    )


def check_revenue_recognition(data):
    revenue = data.get("revenue_recognition", {})
    milestones = milestone_map(data)
    return all(
        [
            norm_enum(revenue.get("recognition_status")) == "COMPLETE_FOR_PAID_MILESTONES",
            list_eq(revenue.get("recognized_milestones"), ["MS1"]),
            list_eq(revenue.get("missing_required_milestones"), []),
            money_eq(revenue.get("recognized_amount"), "62000.00"),
            norm_enum(milestones.get("MS1", {}).get("revenue_recognition_status")) == "RECOGNIZED",
            norm_enum(milestones.get("MS2", {}).get("revenue_recognition_status")) == "NOT_REQUIRED_UNPAID",
        ]
    )


def check_event_voucher(data):
    event = data.get("event", {})
    invite = task_map(data).get("EVENT_INVITATION", {})
    exp = EXPECTED["event"]
    return all(
        [
            norm_text(event.get("event_id")) == exp["event_id"],
            norm_text(event.get("event_date")) == exp["event_date"],
            norm_enum(event.get("event_status")) == exp["event_status"],
            norm_text(event.get("voucher_code")) == exp["voucher_code"],
            money_eq(event.get("voucher_discount"), exp["voucher_discount"]),
            int_eq(event.get("voucher_max_uses"), exp["voucher_max_uses"]),
            norm_text(invite.get("event_id")) == exp["event_id"],
            norm_text(invite.get("voucher_code")) == exp["voucher_code"],
        ]
    )


def check_follow_up_actions(data):
    tasks = task_map(data)
    return all(
        [
            norm_enum(tasks.get("COLLECTION", {}).get("next_action")) == "ESCALATE_COLLECTION",
            norm_text(tasks.get("COLLECTION", {}).get("due_date")) == "2026-06-01",
            norm_enum(tasks.get("EVENT_INVITATION", {}).get("next_action")) == "SEND_EVENT_INVITATION",
            norm_text(tasks.get("EVENT_INVITATION", {}).get("due_date")) == "2026-06-10",
        ]
    )


def check_contact(data):
    contact = data.get("account_status", {}).get("contact", {})
    tasks = task_map(data)
    return all(
        [
            norm_text(contact.get("name")) == EXPECTED["contact_name"],
            norm_text(contact.get("linked_customer_id")) == EXPECTED["customer_id"],
            norm_text(contact.get("linked_opportunity_id")) == EXPECTED["opportunity_id"],
            norm_text(tasks.get("COLLECTION", {}).get("contact_name")) == EXPECTED["contact_name"],
            norm_text(tasks.get("EVENT_INVITATION", {}).get("contact_name")) == EXPECTED["contact_name"],
        ]
    )


CHECKS = [
    ("opportunity_account_identity", 1, check_account_identity),
    ("reporting_labels_and_phase_totals", 3, check_reporting_labels_and_totals),
    ("payment_and_outstanding_balance", 2, check_payment_balance),
    ("due_date_and_collection_convention", 10, check_due_dates_and_collection),
    ("revenue_recognition_state", 3, check_revenue_recognition),
    ("event_voucher_action", 2, check_event_voucher),
    ("crm_follow_up_actions", 2, check_follow_up_actions),
    ("contact_linkage", 1, check_contact),
]


def score_candidate(data, parse_error=None):
    points = []
    for point_id, weight, fn in CHECKS:
        add(points, point_id, weight, False if parse_error else fn(data))
    earned = sum(p["earned_weight"] for p in points)
    total = sum(p["weight"] for p in points)
    return {
        "score": earned,
        "max_score": total,
        "score_fraction": round(earned / total, 6),
        "passed": earned == total,
        "parse_error": parse_error,
        "checks": points,
    }


def main():
    if len(sys.argv) > 2:
        raise SystemExit("Usage: eval.py [candidate_answer.json]")
    candidate = (
        Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).resolve().parents[1] / "output" / "answer.json"
    )
    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
        parse_error = None
    except Exception as exc:
        data = {}
        parse_error = str(exc)
    print(json.dumps(score_candidate(data, parse_error), indent=2))


if __name__ == "__main__":
    main()
