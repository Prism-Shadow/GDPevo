#!/usr/bin/env python3
import json
import sys
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parents[1]
ANSWER_PATH = TASK_DIR / "output" / "answer.json"


SCORING_POINTS = [
    ("SP001", "sponsor_status_set", 3),
    ("SP002", "sponsor_revenue_totals", 2),
    ("SP003", "qualified_non_sponsor_leads", 3),
    ("SP004", "excluded_records", 2),
    ("SP005", "lead_pipeline_total_and_average", 2),
    ("SP006", "follow_up_due_dates_and_counts", 3),
    ("SP007", "crm_action_counts", 1),
]


EXPECTED = {
    "sponsor_statuses": [
        {
            "account_id": "acct_fathom_ops",
            "account_name": "Fathom Ops",
            "status": "paid_deferred",
            "package_amount": 72000,
            "invoice_ids": ["inv_pops_3001"],
            "paid_amount": 72000,
            "open_balance": 0,
        },
        {
            "account_id": "acct_lumina_mfg",
            "account_name": "Lumina Manufacturing",
            "status": "open_invoice",
            "package_amount": 42000,
            "invoice_ids": ["inv_pops_3002a", "inv_pops_3002b"],
            "paid_amount": 26000,
            "open_balance": 16000,
        },
        {
            "account_id": "acct_orbitrail",
            "account_name": "OrbitRail Systems",
            "status": "proposal_only",
            "package_amount": 22000,
            "invoice_ids": [],
            "paid_amount": 0,
            "open_balance": 0,
        },
    ],
    "sponsor_revenue_totals": {
        "paid_deferred": 98000,
        "open_invoice": 16000,
        "proposal_only": 22000,
        "open_invoice_balance": 16000,
    },
    "qualified_lead_accounts": [
        {
            "account_name": "Cascadia Steel",
            "account_id": None,
            "primary_contact": "Miles Chen",
            "normalized_email": "miles.chen@cascadiasteel.example",
            "normalized_phone": "5035550114",
            "crm_account_action": "create_account",
            "crm_contact_action": "create_contact",
            "campaign_member_action": "add_campaign_member",
            "opportunity_amount": 51000,
        },
        {
            "account_name": "Riverbend Chemical",
            "account_id": "acct_riverbend_chem",
            "primary_contact": "Hana Park",
            "normalized_email": "hana.park@riverbendchem.example",
            "normalized_phone": "17135550138",
            "crm_account_action": "update_existing",
            "crm_contact_action": "update_existing",
            "campaign_member_action": "update_campaign_member",
            "opportunity_amount": 51000,
        },
    ],
    "lead_pipeline_total": 102000,
    "average_deal_size": 51000.0,
    "excluded_records": [
        {
            "company_name": "Fathom Ops",
            "contact_name": "Cole Ivers",
            "source": "badge_scan",
            "reason": "sponsor_attendee",
        },
        {
            "company_name": "Fathom Ops",
            "contact_name": "Sofia Meyer",
            "source": "campaign_member",
            "reason": "stale_crm_duplicate",
        },
        {
            "company_name": "Keystone AGV",
            "contact_name": "Anika Shah",
            "source": "sponsor_package",
            "reason": "inactive_sponsor_record",
        },
        {
            "company_name": "Lumina Manufacturing",
            "contact_name": "Nadia Volk",
            "source": "badge_scan",
            "reason": "sponsor_attendee",
        },
        {
            "company_name": "Old Quarry Logistics",
            "contact_name": "Rhea Moon",
            "source": "badge_scan",
            "reason": "existing_disqualified",
        },
        {
            "company_name": "Pacific Robotics Review",
            "contact_name": "Dev Singh",
            "source": "badge_scan",
            "reason": "non_business_badge",
        },
    ],
    "follow_up": {
        "lead_due_date": "2027-04-01",
        "lead_task_count": 2,
        "sponsor_finance_due_date": "2027-03-28",
        "sponsor_finance_task_count": 2,
        "sponsor_finance_accounts": ["Lumina Manufacturing", "OrbitRail Systems"],
    },
    "crm_action_counts": {
        "accounts_create": 1,
        "accounts_update": 1,
        "contacts_create": 1,
        "contacts_update": 1,
        "campaign_members_create": 1,
        "campaign_members_update": 1,
    },
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def norm_scalar(value):
    if isinstance(value, str):
        return value.strip()
    return value


def norm_invoice_ids(value):
    if not isinstance(value, list):
        return []
    return sorted(str(item).strip() for item in value)


def project(obj, keys):
    projected = {}
    for key in keys:
        value = obj.get(key)
        projected[key] = norm_invoice_ids(value) if key == "invoice_ids" else norm_scalar(value)
    return projected


def sorted_projected(items, keys, sort_keys):
    if not isinstance(items, list):
        return []
    projected = [project(item, keys) for item in items if isinstance(item, dict)]
    return sorted(
        projected, key=lambda item: tuple("" if item.get(k) is None else str(item.get(k)) for k in sort_keys)
    )


def dict_subset(actual, expected):
    if not isinstance(actual, dict):
        return False
    for key, expected_value in expected.items():
        if actual.get(key) != expected_value:
            return False
    return True


def get_plan(pred):
    plan = pred.get("lead_opportunity_plan")
    return plan if isinstance(plan, dict) else {}


def sponsor_statuses_match(pred):
    keys = ["account_id", "account_name", "status", "package_amount", "invoice_ids", "paid_amount", "open_balance"]
    return sorted_projected(pred.get("sponsor_statuses"), keys, ["account_name"]) == sorted_projected(
        EXPECTED["sponsor_statuses"], keys, ["account_name"]
    )


def sponsor_revenue_match(pred):
    return dict_subset(pred.get("sponsor_revenue_totals"), EXPECTED["sponsor_revenue_totals"])


def qualified_leads_match(pred):
    keys = [
        "account_name",
        "account_id",
        "primary_contact",
        "normalized_email",
        "normalized_phone",
        "crm_account_action",
        "crm_contact_action",
        "campaign_member_action",
        "opportunity_amount",
    ]
    actual = get_plan(pred).get("qualified_lead_accounts")
    return sorted_projected(actual, keys, ["account_name"]) == sorted_projected(
        EXPECTED["qualified_lead_accounts"], keys, ["account_name"]
    )


def exclusions_match(pred):
    keys = ["company_name", "contact_name", "source", "reason"]
    return sorted_projected(pred.get("excluded_records"), keys, ["company_name", "contact_name"]) == sorted_projected(
        EXPECTED["excluded_records"], keys, ["company_name", "contact_name"]
    )


def pipeline_summary_match(pred):
    plan = get_plan(pred)
    try:
        average = round(float(plan.get("average_deal_size")), 2)
    except (TypeError, ValueError):
        return False
    return (
        plan.get("lead_pipeline_total") == EXPECTED["lead_pipeline_total"] and average == EXPECTED["average_deal_size"]
    )


def follow_up_match(pred):
    follow_up = pred.get("follow_up")
    if not isinstance(follow_up, dict):
        return False
    expected = EXPECTED["follow_up"]
    scalar_keys = [
        "lead_due_date",
        "lead_task_count",
        "sponsor_finance_due_date",
        "sponsor_finance_task_count",
    ]
    if any(follow_up.get(key) != expected[key] for key in scalar_keys):
        return False
    actual_accounts = follow_up.get("sponsor_finance_accounts")
    if not isinstance(actual_accounts, list):
        return False
    return sorted(actual_accounts) == sorted(expected["sponsor_finance_accounts"])


def crm_counts_match(pred):
    return dict_subset(pred.get("crm_action_counts"), EXPECTED["crm_action_counts"])


CHECKS = {
    "SP001": sponsor_statuses_match,
    "SP002": sponsor_revenue_match,
    "SP003": qualified_leads_match,
    "SP004": exclusions_match,
    "SP005": pipeline_summary_match,
    "SP006": follow_up_match,
    "SP007": crm_counts_match,
}


def evaluate(pred):
    results = []
    earned = 0
    possible = sum(weight for _, _, weight in SCORING_POINTS)
    for point_id, label, weight in SCORING_POINTS:
        passed = bool(CHECKS[point_id](pred))
        score = weight if passed else 0
        earned += score
        results.append(
            {
                "id": point_id,
                "label": label,
                "passed": passed,
                "score": score,
                "max_score": weight,
            }
        )
    return {
        "total_score": round(earned / possible if possible else 0.0, 6),
        "earned_score": earned,
        "max_score": possible,
        "points": results,
    }


def failure_result(exc):
    return {
        "total_score": 0.0,
        "earned_score": 0,
        "max_score": sum(weight for _, _, weight in SCORING_POINTS),
        "points": [
            {
                "id": point_id,
                "label": label,
                "passed": False,
                "score": 0,
                "max_score": weight,
            }
            for point_id, label, weight in SCORING_POINTS
        ],
        "error": str(exc),
    }


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ANSWER_PATH
    try:
        pred = load_json(path)
        result = evaluate(pred)
    except Exception as exc:
        result = failure_result(exc)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
