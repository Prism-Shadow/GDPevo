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
    ("SP005", "lead_pipeline_total", 2),
    ("SP006", "follow_up_due_dates_and_counts", 2),
    ("SP007", "crm_action_counts", 1),
]


EXPECTED = {
    "event_id": "neuralops_2026",
    "event_name": "Summit NeuralOps 2026",
    "sponsor_statuses": [
        {
            "account_id": "acct_atlas_grid",
            "account_name": "Atlas Grid Analytics",
            "status": "paid_deferred",
            "package_amount": 60000,
            "invoice_id": "inv_nops_1001",
            "paid_amount": 60000,
            "open_balance": 0,
        },
        {
            "account_id": "acct_bluepeak",
            "account_name": "BluePeak Systems",
            "status": "open_invoice",
            "package_amount": 35000,
            "invoice_id": "inv_nops_1002",
            "paid_amount": 10000,
            "open_balance": 25000,
        },
        {
            "account_id": "acct_copperline",
            "account_name": "Copperline Robotics",
            "status": "proposal_only",
            "package_amount": 18000,
            "invoice_id": None,
            "paid_amount": 0,
            "open_balance": 0,
        },
    ],
    "sponsor_revenue_totals": {
        "paid_deferred": 60000,
        "open_invoice": 35000,
        "proposal_only": 18000,
        "open_invoice_balance": 25000,
    },
    "qualified_lead_accounts": [
        {
            "account_name": "HelioWare Manufacturing",
            "account_id": "acct_helio_ware",
            "primary_contact": "Dana Ruiz",
            "normalized_email": "dana.ruiz@helioware.example",
            "normalized_phone": "4155550188",
            "crm_account_action": "update_existing",
            "crm_contact_action": "create_contact",
            "campaign_member_action": "add_campaign_member",
            "opportunity_amount": 42000,
        },
        {
            "account_name": "Monarch Foods",
            "account_id": None,
            "primary_contact": "Kenji Sato",
            "normalized_email": "kenji.sato@monarchfoods.example",
            "normalized_phone": "12065550177",
            "crm_account_action": "create_account",
            "crm_contact_action": "create_contact",
            "campaign_member_action": "add_campaign_member",
            "opportunity_amount": 42000,
        },
    ],
    "lead_pipeline_total": 84000,
    "excluded_records": [
        {
            "company_name": "Atlas Grid Analytics",
            "contact_name": "Iris Stone",
            "reason": "sponsor_attendee",
        },
        {
            "company_name": "BluePeak Systems",
            "contact_name": "Maya Chen",
            "reason": "sponsor_attendee",
        },
        {
            "company_name": "City College Robotics Lab",
            "contact_name": "Nora Webb",
            "reason": "non_business_badge",
        },
        {
            "company_name": "Copperline Robotics",
            "contact_name": "Jon Patel",
            "reason": "sponsor_attendee",
        },
        {
            "company_name": "Northstar Sensors",
            "contact_name": "Priya Raman",
            "reason": "existing_disqualified",
        },
        {
            "company_name": "Old Quarry Logistics",
            "contact_name": "Rhea Moon",
            "reason": "existing_disqualified",
        },
    ],
    "follow_up": {
        "lead_due_date": "2026-09-23",
        "lead_task_count": 2,
        "sponsor_finance_due_date": "2026-09-19",
        "sponsor_finance_task_count": 2,
        "sponsor_finance_accounts": ["BluePeak Systems", "Copperline Robotics"],
    },
    "crm_action_counts": {
        "accounts_create": 1,
        "accounts_update": 1,
        "contacts_create": 2,
        "contacts_update": 0,
        "campaign_members_create": 2,
        "campaign_members_update": 0,
    },
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def norm_scalar(value):
    if isinstance(value, str):
        return value.strip()
    return value


def project(obj, keys):
    return {key: norm_scalar(obj.get(key)) for key in keys}


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


def sponsor_statuses_match(pred):
    keys = ["account_id", "account_name", "status", "package_amount", "invoice_id", "paid_amount", "open_balance"]
    sort_keys = ["account_name"]
    return sorted_projected(pred.get("sponsor_statuses"), keys, sort_keys) == sorted_projected(
        EXPECTED["sponsor_statuses"], keys, sort_keys
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
    sort_keys = ["account_name"]
    return sorted_projected(pred.get("qualified_lead_accounts"), keys, sort_keys) == sorted_projected(
        EXPECTED["qualified_lead_accounts"], keys, sort_keys
    )


def exclusions_match(pred):
    keys = ["company_name", "contact_name", "reason"]
    sort_keys = ["company_name", "contact_name"]
    return sorted_projected(pred.get("excluded_records"), keys, sort_keys) == sorted_projected(
        EXPECTED["excluded_records"], keys, sort_keys
    )


def pipeline_total_match(pred):
    return pred.get("lead_pipeline_total") == EXPECTED["lead_pipeline_total"]


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
    return sorted(follow_up.get("sponsor_finance_accounts", [])) == sorted(expected["sponsor_finance_accounts"])


def crm_counts_match(pred):
    return dict_subset(pred.get("crm_action_counts"), EXPECTED["crm_action_counts"])


CHECKS = {
    "SP001": sponsor_statuses_match,
    "SP002": sponsor_revenue_match,
    "SP003": qualified_leads_match,
    "SP004": exclusions_match,
    "SP005": pipeline_total_match,
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
    total_score = earned / possible if possible else 0.0
    return {
        "total_score": round(total_score, 6),
        "earned_score": earned,
        "max_score": possible,
        "points": results,
    }


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ANSWER_PATH
    try:
        pred = load_json(path)
        result = evaluate(pred)
    except Exception as exc:
        result = {
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
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
