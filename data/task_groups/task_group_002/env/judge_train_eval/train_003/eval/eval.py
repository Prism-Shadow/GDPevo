#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


EXPECTED = {
    "customer_id": "CUST-HELIOS",
    "customer_name": "Helios Health Alliance",
    "opportunity_id": "OPP-TR-HELIOS",
    "stage": "WON",
    "won_amount": 120000.00,
    "contact_name": "Mara Okafor",
    "milestones": {
        "MS1": {
            "phase_number": 1,
            "invoice_total": 50000.00,
            "payment_status": "PAID",
            "amount_paid": 50000.00,
            "amount_unpaid": 0.00,
            "due_date": None,
            "revenue_recognition_status": "RECOGNIZED",
        },
        "MS2": {
            "phase_number": 2,
            "invoice_total": 70000.00,
            "payment_status": "UNPAID",
            "amount_paid": 0.00,
            "amount_unpaid": 70000.00,
            "due_date": "2026-07-10",
            "revenue_recognition_status": "NOT_REQUIRED_UNPAID",
        },
    },
    "outstanding_balance": 70000.00,
    "recognition_status": "COMPLETE_FOR_PAID_MILESTONES",
    "recognized_milestones": ["MS1"],
    "missing_required_milestones": [],
    "recognized_amount": 50000.00,
    "event": {
        "event_id": "EVT-HELIOS-CELEBRATION",
        "event_date": "2026-07-22",
        "voucher_code": "HELIOSVIP100",
        "voucher_discount": 100.00,
        "voucher_max_uses": 4,
    },
}


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def get(obj, path, default=None):
    cur = obj
    for part in path:
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def norm_str(value):
    if value is None:
        return None
    return str(value).strip()


def norm_enum(value):
    if value is None:
        return None
    return str(value).strip().upper()


def money_eq(actual, expected):
    try:
        return math.isclose(float(actual), float(expected), abs_tol=0.005)
    except (TypeError, ValueError):
        return False


def int_eq(actual, expected):
    try:
        return int(actual) == int(expected)
    except (TypeError, ValueError):
        return False


def milestone_map(candidate):
    items = candidate.get("milestones", [])
    if not isinstance(items, list):
        return {}
    mapped = {}
    for item in items:
        if isinstance(item, dict):
            milestone_id = norm_str(item.get("milestone_id"))
            if milestone_id:
                mapped[milestone_id] = item
    return mapped


def task_map(candidate):
    items = candidate.get("follow_up_tasks", [])
    if not isinstance(items, list):
        return {}
    mapped = {}
    for item in items:
        if isinstance(item, dict):
            task_type = norm_enum(item.get("task_type"))
            if task_type:
                mapped[task_type] = item
    return mapped


def set_eq(actual, expected):
    if not isinstance(actual, list):
        return False
    return sorted(norm_str(v) for v in actual) == sorted(expected)


def check_crm_opportunity(candidate):
    status = candidate.get("account_status", {})
    return (
        norm_str(status.get("opportunity_id")) == EXPECTED["opportunity_id"]
        and norm_enum(status.get("opportunity_stage")) == EXPECTED["stage"]
        and money_eq(status.get("won_amount"), EXPECTED["won_amount"])
    )


def check_milestone_totals(candidate):
    milestones = milestone_map(candidate)
    if set(milestones) != set(EXPECTED["milestones"]):
        return False
    total_ok = all(
        money_eq(milestones[mid].get("invoice_total"), expected["invoice_total"])
        and int_eq(milestones[mid].get("phase_number"), expected["phase_number"])
        for mid, expected in EXPECTED["milestones"].items()
    )
    sum_actual = sum(float(milestones[mid].get("invoice_total", 0)) for mid in milestones)
    return (
        total_ok
        and money_eq(sum_actual, EXPECTED["won_amount"])
        and get(candidate, ["account_status", "opportunity_matches_milestones"]) is True
    )


def check_payment_balance(candidate):
    milestones = milestone_map(candidate)
    if set(milestones) != set(EXPECTED["milestones"]):
        return False
    for mid, expected in EXPECTED["milestones"].items():
        actual = milestones[mid]
        if norm_enum(actual.get("payment_status")) != expected["payment_status"]:
            return False
        if not money_eq(actual.get("amount_paid"), expected["amount_paid"]):
            return False
        if not money_eq(actual.get("amount_unpaid"), expected["amount_unpaid"]):
            return False
    return money_eq(
        get(candidate, ["account_status", "outstanding_balance"]),
        EXPECTED["outstanding_balance"],
    )


def check_revenue_recognition(candidate):
    revenue = candidate.get("revenue_recognition", {})
    milestones = milestone_map(candidate)
    if norm_enum(revenue.get("recognition_status")) != EXPECTED["recognition_status"]:
        return False
    if not set_eq(revenue.get("recognized_milestones"), EXPECTED["recognized_milestones"]):
        return False
    if not set_eq(revenue.get("missing_required_milestones"), EXPECTED["missing_required_milestones"]):
        return False
    if not money_eq(revenue.get("recognized_amount"), EXPECTED["recognized_amount"]):
        return False
    return (
        norm_enum(milestones.get("MS1", {}).get("revenue_recognition_status")) == "RECOGNIZED"
        and norm_enum(milestones.get("MS2", {}).get("revenue_recognition_status")) == "NOT_REQUIRED_UNPAID"
    )


def check_event_voucher(candidate):
    event = candidate.get("event", {})
    expected = EXPECTED["event"]
    return (
        norm_str(event.get("event_id")) == expected["event_id"]
        and norm_str(event.get("event_date")) == expected["event_date"]
        and norm_str(event.get("voucher_code")) == expected["voucher_code"]
        and money_eq(event.get("voucher_discount"), expected["voucher_discount"])
        and int_eq(event.get("voucher_max_uses"), expected["voucher_max_uses"])
    )


def check_collection_task(candidate):
    task = task_map(candidate).get("COLLECTION", {})
    return (
        norm_str(task.get("linked_customer_id")) == EXPECTED["customer_id"]
        and norm_str(task.get("linked_opportunity_id")) == EXPECTED["opportunity_id"]
        and norm_str(task.get("contact_name")) == EXPECTED["contact_name"]
        and norm_str(task.get("due_date")) == "2026-07-10"
        and norm_enum(task.get("next_action")) == "COLLECT_UNPAID_MILESTONE"
        and norm_str(task.get("milestone_id")) == "MS2"
        and money_eq(task.get("amount_due"), 70000.00)
    )


def check_invite_task(candidate):
    task = task_map(candidate).get("EVENT_INVITATION", {})
    return (
        norm_str(task.get("linked_customer_id")) == EXPECTED["customer_id"]
        and norm_str(task.get("linked_opportunity_id")) == EXPECTED["opportunity_id"]
        and norm_str(task.get("contact_name")) == EXPECTED["contact_name"]
        and norm_str(task.get("due_date")) == "2026-07-01"
        and norm_enum(task.get("next_action")) == "SEND_EVENT_INVITATION"
        and norm_str(task.get("event_id")) == EXPECTED["event"]["event_id"]
        and norm_str(task.get("voucher_code")) == EXPECTED["event"]["voucher_code"]
    )


def check_contact_linkage(candidate):
    status = candidate.get("account_status", {})
    contact = status.get("contact", {})
    return (
        norm_str(status.get("customer_id")) == EXPECTED["customer_id"]
        and norm_str(status.get("customer_name")) == EXPECTED["customer_name"]
        and norm_str(contact.get("name")) == EXPECTED["contact_name"]
        and norm_str(contact.get("linked_customer_id")) == EXPECTED["customer_id"]
        and norm_str(contact.get("linked_opportunity_id")) == EXPECTED["opportunity_id"]
    )


SCORING_POINTS = [
    ("crm_opportunity_total_stage", 2, check_crm_opportunity),
    ("milestone_invoice_totals", 2, check_milestone_totals),
    ("paid_unpaid_balance", 3, check_payment_balance),
    ("revenue_recognition_entry_status", 2, check_revenue_recognition),
    ("event_voucher_facts", 2, check_event_voucher),
    ("collection_task_fields", 2, check_collection_task),
    ("invite_task_fields", 1, check_invite_task),
    ("contact_linkage", 1, check_contact_linkage),
]


def main():
    if len(sys.argv) > 2:
        raise SystemExit("Usage: eval.py [candidate_answer.json]")
    candidate_path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path("../output/answer.json")

    try:
        candidate = load_json(candidate_path)
        parse_error = None
    except Exception as exc:
        candidate = {}
        parse_error = str(exc)

    total_weight = sum(weight for _, weight, _ in SCORING_POINTS)
    points = []
    earned_weight = 0

    for point_id, weight, checker in SCORING_POINTS:
        passed = False if parse_error else bool(checker(candidate))
        earned = weight if passed else 0
        earned_weight += earned
        points.append(
            {
                "id": point_id,
                "weight": weight,
                "passed": passed,
                "earned_weight": earned,
                "normalized_score": earned / total_weight,
            }
        )

    result = {
        "score": earned_weight / total_weight,
        "earned_weight": earned_weight,
        "total_weight": total_weight,
        "parse_error": parse_error,
        "points": points,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
