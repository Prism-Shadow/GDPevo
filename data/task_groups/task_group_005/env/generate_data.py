#!/usr/bin/env python3
"""Generate deterministic ERP finance fixture data for task_group_005."""

from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path


SEED = 5005
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"


def money(value: float) -> float:
    return round(value + 0.0000001, 2)


def write_json(name: str, rows) -> None:
    path = DATA_DIR / name
    with path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2, sort_keys=True)
        handle.write("\n")


def iso(day: date) -> str:
    return day.isoformat()


def month_add(day: date, months: int) -> date:
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    month_lengths = [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return date(year, month, min(day.day, month_lengths[month - 1]))


def build_vendors(rng: random.Random):
    industries = [
        "Software",
        "Travel",
        "Insurance",
        "Legal",
        "Facilities",
        "Marketing",
        "Healthcare",
        "Payroll",
        "Cloud",
        "Consulting",
        "Logistics",
        "Training",
    ]
    prefixes = [
        "Aster",
        "Northstar",
        "Bluefield",
        "Vertex",
        "Cobalt",
        "Lattice",
        "Summit",
        "Brightline",
        "Keystone",
        "Harbor",
        "Civic",
        "Pioneer",
        "Redwood",
        "Silvergate",
        "Atlas",
        "Evergreen",
        "Orchard",
        "Nexus",
    ]
    suffixes = ["Systems", "Partners", "Group", "Services", "Labs", "Works", "Advisors", "Solutions"]
    vendors = []
    for i in range(1, 81):
        name = f"{rng.choice(prefixes)} {rng.choice(suffixes)}"
        if i % 19 == 0:
            name = vendors[-1]["vendor_name"] if vendors else name
        vendor = {
            "vendor_id": f"VEN-{i:04d}",
            "vendor_name": name,
            "legal_name": name + (", Inc." if i % 3 else " LLC"),
            "status": rng.choices(["active", "inactive", "on_hold"], [72, 5, 3])[0],
            "industry": rng.choice(industries),
            "tax_id": f"TIN{rng.randint(100000, 999999)}",
            "bank_account_last4": f"{rng.randint(0, 9999):04d}",
            "payment_terms": rng.choice(["Net 15", "Net 30", "Net 45", "Due on receipt"]),
            "default_account": rng.choice(["6100", "6200", "6250", "6500", "1250", "1251"]),
            "updated_at": iso(date(2025, 1, 1) + timedelta(days=rng.randint(0, 145))),
        }
        if i in (7, 33, 58):
            vendor["tax_id"] = "TIN111111"
        if i in (12, 44):
            vendor["bank_account_last4"] = None
        vendors.append(vendor)
    return vendors


def build_claims(rng: random.Random, vendors):
    employees = [
        "Avery Lee",
        "Jordan Patel",
        "Morgan Chen",
        "Casey Brooks",
        "Taylor Reed",
        "Riley Morgan",
        "Quinn Evans",
        "Skyler Diaz",
        "Jamie Hughes",
        "Cameron Price",
    ]
    categories = ["Travel", "Meals", "Software", "Training", "Mileage", "Client event", "Office supplies"]
    claims = []
    for i in range(1, 91):
        submitted = date(2025, 1, 2) + timedelta(days=rng.randint(0, 135))
        amount = money(rng.uniform(80, 7800))
        status = rng.choices(["submitted", "approved", "rejected", "paid", "needs_receipt"], [18, 24, 5, 34, 9])[0]
        claim = {
            "claim_id": f"CLM-2025-{i:04d}",
            "employee_name": rng.choice(employees),
            "department": rng.choice(["Sales", "Engineering", "Finance", "Operations", "People", "Customer Success"]),
            "category": rng.choice(categories),
            "vendor_id": rng.choice(vendors)["vendor_id"] if rng.random() < 0.55 else None,
            "submitted_date": iso(submitted),
            "approved_date": iso(submitted + timedelta(days=rng.randint(1, 12)))
            if status in ("approved", "paid")
            else None,
            "amount": amount,
            "currency": "USD",
            "status": status,
            "receipt_status": rng.choices(["attached", "missing", "partial"], [75, 12, 13])[0],
            "policy_flags": rng.sample(
                ["late_receipt", "weekend_spend", "over_limit", "duplicate_amount", "manual_rate"], rng.randint(0, 2)
            ),
            "notes": rng.choice(["", "", "", "Manager comment pending", "Imported from legacy expense feed"]),
        }
        claims.append(claim)
    claims.extend(
        [
            {
                "claim_id": "CLM-2025-OPS-017",
                "employee_name": "Avery Lee",
                "department": "Operations",
                "category": "Travel",
                "vendor_id": "VEN-0007",
                "submitted_date": "2025-04-18",
                "approved_date": "2025-04-22",
                "amount": 1842.36,
                "currency": "USD",
                "status": "approved",
                "receipt_status": "attached",
                "policy_flags": ["manual_rate"],
                "notes": "Reimbursement batch candidate",
            },
            {
                "claim_id": "CLM-2025-FIN-042",
                "employee_name": "Jordan Patel",
                "department": "Finance",
                "category": "Software",
                "vendor_id": "VEN-0033",
                "submitted_date": "2025-03-29",
                "approved_date": "2025-04-02",
                "amount": 2675.00,
                "currency": "USD",
                "status": "paid",
                "receipt_status": "partial",
                "policy_flags": ["duplicate_amount"],
                "notes": "Payment matched to bill AP-2025-0068",
            },
        ]
    )
    return claims


def build_bills(rng: random.Random, vendors, claims):
    bills = []
    for i in range(1, 111):
        vendor = rng.choice(vendors)
        bill_date = date(2025, 1, 1) + timedelta(days=rng.randint(0, 145))
        amount = money(rng.uniform(250, 45000))
        account = rng.choice(["6100", "6200", "6250", "6500", "1250", "1251", "2100"])
        status = rng.choices(["draft", "approved", "scheduled", "paid", "void"], [8, 25, 20, 52, 5])[0]
        bill = {
            "bill_id": f"AP-2025-{i:04d}",
            "vendor_id": vendor["vendor_id"],
            "invoice_number": f"INV-{rng.randint(10000, 99999)}",
            "bill_date": iso(bill_date),
            "due_date": iso(bill_date + timedelta(days=rng.choice([15, 30, 45]))),
            "amount": amount,
            "currency": "USD",
            "account": account,
            "status": status,
            "claim_id": rng.choice(claims)["claim_id"] if rng.random() < 0.20 else None,
            "memo": rng.choice(["", "Accrual review", "Imported from AP inbox", "Duplicate check required"]),
        }
        bills.append(bill)
    bills.extend(
        [
            {
                "bill_id": "AP-2025-REIM-017",
                "vendor_id": "VEN-0007",
                "invoice_number": "REIM-CLM-OPS-017",
                "bill_date": "2025-04-23",
                "due_date": "2025-05-08",
                "amount": 1842.36,
                "currency": "USD",
                "account": "6200",
                "status": "scheduled",
                "claim_id": "CLM-2025-OPS-017",
                "memo": "Employee reimbursement clearing bill",
            },
            {
                "bill_id": "AP-2025-0068",
                "vendor_id": "VEN-0033",
                "invoice_number": "SW-32991",
                "bill_date": "2025-04-03",
                "due_date": "2025-04-18",
                "amount": 2675.00,
                "currency": "USD",
                "account": "1250",
                "status": "paid",
                "claim_id": "CLM-2025-FIN-042",
                "memo": "Partial receipt support noted",
            },
        ]
    )
    return bills


def build_payments(rng: random.Random, bills):
    payments = []
    paid_bills = [bill for bill in bills if bill["status"] in ("paid", "scheduled")]
    for i, bill in enumerate(rng.sample(paid_bills, min(96, len(paid_bills))), start=1):
        paid_date = datetime.fromisoformat(bill["due_date"]).date() + timedelta(days=rng.randint(-8, 9))
        payments.append(
            {
                "payment_id": f"PAY-2025-{i:04d}",
                "bill_id": bill["bill_id"],
                "vendor_id": bill["vendor_id"],
                "payment_date": iso(paid_date),
                "amount": bill["amount"] if rng.random() > 0.08 else money(bill["amount"] * rng.uniform(0.45, 0.90)),
                "method": rng.choice(["ACH", "Wire", "Check", "Virtual card"]),
                "status": "cleared" if bill["status"] == "paid" else rng.choice(["scheduled", "processing"]),
                "bank_reference": f"BNK{rng.randint(1000000, 9999999)}",
            }
        )
    return payments


def build_compliance(rng: random.Random, vendors):
    jurisdictions = ["Delaware", "New York", "California", "Texas", "Ontario", "United Kingdom", "Cayman Islands"]
    objects = []
    for i in range(1, 66):
        vendor = vendors[(i * 7) % len(vendors)]
        license_expiry = date(2025, 1, 1) + timedelta(days=rng.randint(-90, 210))
        tax_id = vendor["tax_id"]
        if i in (9, 27, 54):
            tax_id = "TIN999999"
        if i == 41:
            tax_id = "TIN12X899"
        sanctions = rng.choices(["clear", "possible_match", "confirmed_match", "not_run"], [53, 7, 1, 4])[0]
        pep = rng.choices(["none", "possible_pep", "confirmed_pep", "not_run"], [55, 6, 1, 3])[0]
        missing = rng.sample(
            ["website", "address", "beneficial_owner_id", "bank_statement", "license"], rng.randint(0, 2)
        )
        objects.append(
            {
                "business_id": f"BUS-2025-{i:04d}",
                "vendor_id": vendor["vendor_id"],
                "business_name": vendor["vendor_name"],
                "registration_number": f"REG-{rng.randint(100000, 999999)}",
                "tax_id": tax_id,
                "jurisdiction": rng.choice(jurisdictions),
                "license_expiry": iso(license_expiry),
                "ubo_list": [
                    {
                        "name": rng.choice(["Alex Stone", "Priya Rao", "Mina Alvarez", "Owen Grant", "Samir Bell"]),
                        "ownership_pct": rng.choice([10, 18, 24, 25, 30, 45, 60]),
                    }
                    for _ in range(rng.randint(1, 4))
                ],
                "ownership_layer_count": rng.randint(1, 5),
                "shell_company_suspected": rng.random() < 0.10,
                "sanctions_check_status": sanctions,
                "pep_status": pep,
                "bank_account_status": rng.choices(
                    ["verified", "name_mismatch", "not_verified", "closed"], [48, 6, 9, 2]
                )[0],
                "risk_score": rng.randint(8, 96),
                "missing_fields": missing,
                "review_status": rng.choice(
                    ["not_started", "in_review", "approved", "awaiting_information", "escalated"]
                ),
            }
        )
    return objects


def build_prepaids(rng: random.Random, vendors):
    invoices = []
    service_vendors = [v for v in vendors if v["default_account"] in ("1250", "6100", "6500")]
    insurance_vendors = [v for v in vendors if v["industry"] in ("Insurance", "Healthcare")]
    for i in range(1, 43):
        account = "1251" if i % 4 == 0 else "1250"
        vendor_pool = insurance_vendors if account == "1251" and insurance_vendors else service_vendors
        start_month = rng.randint(1, 4)
        start_day = rng.choice([1, 1, 1, 15])
        start = date(2025, start_month, start_day)
        term = rng.choice([3, 6, 9, 12])
        original = money(rng.uniform(3200, 98000))
        invoices.append(
            {
                "prepaid_invoice_id": f"PPD-2025-{i:04d}",
                "vendor_id": rng.choice(vendor_pool)["vendor_id"],
                "invoice_number": f"PP-{rng.randint(1000, 9999)}",
                "account": account,
                "description": rng.choice(
                    [
                        "Annual software subscription",
                        "Insurance premium",
                        "Maintenance contract",
                        "Training seats",
                        "Managed services retainer",
                    ]
                ),
                "invoice_date": iso(start),
                "service_start": iso(start),
                "service_end": iso(month_add(start, term) - timedelta(days=1)),
                "original_amount": original,
                "monthly_amortization": money(original / term),
                "recognition_method": "straight_line",
                "source_document": rng.choice(["AP invoice", "Renewal notice", "Policy binder", "Email approval"]),
                "data_quality_flags": rng.sample(
                    ["missing_contract_dates", "rounded_amount", "duplicate_invoice_number", "manual_override"],
                    rng.randint(0, 1),
                ),
            }
        )
    invoices.extend(
        [
            {
                "prepaid_invoice_id": "PPD-AUR-1250-JAN-001",
                "vendor_id": "VEN-0012",
                "invoice_number": "AUR-SVC-2025-01",
                "account": "1250",
                "description": "Operations platform annual subscription",
                "invoice_date": "2025-01-01",
                "service_start": "2025-01-01",
                "service_end": "2025-12-31",
                "original_amount": 144000.00,
                "monthly_amortization": 12000.00,
                "recognition_method": "straight_line",
                "source_document": "January prepaid expense packet",
                "data_quality_flags": [],
            },
            {
                "prepaid_invoice_id": "PPD-AUR-1251-GOOD-001",
                "vendor_id": "VEN-0024",
                "invoice_number": "GOOD-POL-2025",
                "account": "1251",
                "description": "General liability policy",
                "invoice_date": "2025-01-01",
                "service_start": "2025-01-01",
                "service_end": "2025-12-31",
                "original_amount": 546725.10,
                "monthly_amortization": 45560.43,
                "recognition_method": "straight_line",
                "source_document": "Insurance packet",
                "data_quality_flags": ["rounded_amount"],
            },
        ]
    )
    return invoices


def build_gl_balances():
    months = ["2024-12", "2025-01", "2025-02", "2025-03", "2025-04"]
    balances = {
        "1250": [0.00, 518934.86, 426673.13, 473655.55, 559377.61],
        "1251": [0.00, 506657.98, 461097.55, 415537.13, 369976.70],
        "2100": [87520.44, 94415.19, 102004.52, 118920.17, 109882.83],
        "6200": [0.00, 34120.88, 71104.91, 99012.40, 128551.67],
    }
    rows = []
    for account, values in balances.items():
        for period, amount in zip(months, values):
            rows.append(
                {
                    "entity": "Aurisic US",
                    "period": period,
                    "account": account,
                    "account_name": {
                        "1250": "Prepaid Expenses",
                        "1251": "Prepaid Insurance",
                        "2100": "Accounts Payable",
                        "6200": "Employee Reimbursements",
                    }[account],
                    "ending_balance": amount,
                    "source": "close ledger export",
                    "loaded_at": "2025-05-03T09:30:00Z",
                }
            )
    return rows


def build_close_logs(rng: random.Random):
    logs = []
    areas = ["AP", "Expense", "Prepaids", "GL", "Compliance", "Treasury"]
    owners = ["Nora Singh", "Evan Wright", "Maya Stone", "Leo Martin", "Iris Chen"]
    for i in range(1, 37):
        period = rng.choice(["2025-01", "2025-02", "2025-03", "2025-04"])
        logs.append(
            {
                "log_id": f"CLOSE-{period}-{i:03d}",
                "period": period,
                "area": rng.choice(areas),
                "owner": rng.choice(owners),
                "status": rng.choices(["open", "blocked", "ready_for_review", "closed"], [5, 4, 8, 19])[0],
                "created_at": f"{period}-{rng.randint(1, 25):02d}T{rng.randint(8, 18):02d}:{rng.choice([0, 15, 30, 45]):02d}:00Z",
                "message": rng.choice(
                    [
                        "Variance review pending",
                        "Support uploaded",
                        "Waiting on AP export refresh",
                        "Reviewer cleared variance",
                        "Manual journal entry posted",
                        "Legacy import created duplicate line",
                    ]
                ),
                "related_account": rng.choice(["1250", "1251", "2100", "6200", None]),
            }
        )
    return logs


def main() -> None:
    rng = random.Random(SEED)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    vendors = build_vendors(rng)
    claims = build_claims(rng, vendors)
    bills = build_bills(rng, vendors, claims)
    payments = build_payments(rng, bills)
    compliance = build_compliance(rng, vendors)
    prepaids = build_prepaids(rng, vendors)
    gl_balances = build_gl_balances()
    close_logs = build_close_logs(rng)

    datasets = {
        "claims.json": claims,
        "bills.json": bills,
        "payments.json": payments,
        "vendors.json": vendors,
        "compliance_objects.json": compliance,
        "prepaid_invoices.json": prepaids,
        "gl_balances.json": gl_balances,
        "close_logs.json": close_logs,
    }
    for filename, rows in datasets.items():
        write_json(filename, rows)

    manifest = {
        "task_group": "task_group_005",
        "seed": SEED,
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "data_dir": "data",
        "files": [{"file": filename, "records": len(rows)} for filename, rows in sorted(datasets.items())],
        "notes": [
            "Shared ERP finance environment data.",
            "Includes realistic duplicates, missing fields, stale statuses, and noisy risk values.",
            "No task-specific answer endpoint is generated.",
        ],
    }
    with (ROOT / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(json.dumps({"seed": SEED, "files": manifest["files"]}, indent=2))


if __name__ == "__main__":
    main()
