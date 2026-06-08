from __future__ import annotations

import json
import random
from pathlib import Path


SEED = 802608
random.seed(SEED)
DATA_DIR = Path(__file__).resolve().parent / "data"


TAX_POLICY = {
    "policy_label": "Advisory internal 2026 planning constants",
    "annual_gift_exclusion": {"2025": 19000, "2026": 20000},
    "estate_tax_exemption": {"2025": 13990000, "2026": 13610000},
    "estate_tax_rate": 0.40,
    "conversion_bracket_targets": {
        "MFJ": 394600,
        "SINGLE": 197300,
        "HOH": 263500,
    },
    "max_crat_term_years": 20,
    "charitable_deduction_rate": 0.35,
}

RMD_FACTORS = {
    73: 26.5,
    74: 25.5,
    75: 24.6,
    76: 23.7,
    77: 22.9,
    78: 22.0,
    79: 21.1,
    80: 20.2,
    81: 19.4,
    82: 18.5,
    83: 17.7,
    84: 16.8,
    85: 16.0,
    86: 15.2,
    87: 14.4,
    88: 13.7,
    89: 12.9,
    90: 12.2,
    91: 11.5,
    92: 10.8,
    93: 10.1,
    94: 9.5,
    95: 8.9,
    96: 8.4,
    97: 7.8,
    98: 7.3,
    99: 6.8,
}

TARGETS = [
    {
        "client_id": "CLT-1001",
        "household_name": "Mercer Household",
        "age": 66,
        "marital_status": "married",
        "filing_status": "MFJ",
        "planning_year": 2026,
        "estate_value": 18400000,
        "liquid_assets": 2100000,
        "annual_non_ira_income": 185000,
        "marginal_tax_rate": 0.32,
        "beneficiary_count": 3,
        "philanthropic_intent": "low",
        "family_transfer_priority": "high",
        "retirement": {
            "traditional_balance": 2800000,
            "roth_balance": 0,
            "expected_return": 0.065,
            "rmd_start_age": 73,
            "recommended_conversion_years": 7,
        },
        "life": {
            "death_benefit": 3200000,
            "annual_premium": 54000,
            "planned_contribution_date": "2026-02-12",
            "is_existing_policy_transfer": False,
        },
        "trust": {
            "asset_value": 4600000,
            "expected_growth_rate": 0.075,
            "grat_term_years": 5,
            "grat_annuity_rate": 0.045,
            "crat_term_years": 20,
            "crat_payout_rate": 0.055,
        },
        "stale_income": 215000,
        "stale_beneficiaries": 2,
        "stale_goal": "moderate",
    },
    {
        "client_id": "CLT-1002",
        "household_name": "Keating Household",
        "age": 59,
        "marital_status": "married",
        "filing_status": "MFJ",
        "planning_year": 2026,
        "estate_value": 24600000,
        "liquid_assets": 1800000,
        "annual_non_ira_income": 260000,
        "marginal_tax_rate": 0.35,
        "beneficiary_count": 4,
        "philanthropic_intent": "low",
        "family_transfer_priority": "high",
        "retirement": {
            "traditional_balance": 1200000,
            "roth_balance": 0,
            "expected_return": 0.055,
            "rmd_start_age": 73,
            "recommended_conversion_years": 6,
        },
        "life": {
            "death_benefit": 4500000,
            "annual_premium": 78000,
            "planned_contribution_date": "2026-03-10",
            "is_existing_policy_transfer": False,
        },
        "trust": {
            "asset_value": 6200000,
            "expected_growth_rate": 0.072,
            "grat_term_years": 6,
            "grat_annuity_rate": 0.042,
            "crat_term_years": 20,
            "crat_payout_rate": 0.055,
        },
        "stale_income": 240000,
        "stale_beneficiaries": 3,
        "stale_goal": "moderate",
    },
    {
        "client_id": "CLT-1003",
        "household_name": "Alvarez Family",
        "age": 62,
        "marital_status": "married",
        "filing_status": "MFJ",
        "planning_year": 2026,
        "estate_value": 38800000,
        "liquid_assets": 6200000,
        "annual_non_ira_income": 310000,
        "marginal_tax_rate": 0.35,
        "beneficiary_count": 2,
        "philanthropic_intent": "moderate",
        "family_transfer_priority": "high",
        "retirement": {
            "traditional_balance": 900000,
            "roth_balance": 0,
            "expected_return": 0.058,
            "rmd_start_age": 73,
            "recommended_conversion_years": 5,
        },
        "life": {
            "death_benefit": 2500000,
            "annual_premium": 42000,
            "planned_contribution_date": "2026-04-04",
            "is_existing_policy_transfer": False,
        },
        "trust": {
            "asset_value": 8000000,
            "expected_growth_rate": 0.08,
            "grat_term_years": 5,
            "grat_annuity_rate": 0.04,
            "crat_term_years": 20,
            "crat_payout_rate": 0.055,
        },
        "stale_income": 350000,
        "stale_beneficiaries": 3,
        "stale_goal": "high",
    },
    {
        "client_id": "CLT-1004",
        "household_name": "Chen Executive Household",
        "age": 57,
        "marital_status": "single",
        "filing_status": "SINGLE",
        "planning_year": 2026,
        "estate_value": 31200000,
        "liquid_assets": 2400000,
        "annual_non_ira_income": 420000,
        "marginal_tax_rate": 0.37,
        "beneficiary_count": 3,
        "philanthropic_intent": "low",
        "family_transfer_priority": "high",
        "retirement": {
            "traditional_balance": 600000,
            "roth_balance": 0,
            "expected_return": 0.06,
            "rmd_start_age": 73,
            "recommended_conversion_years": 4,
        },
        "life": {
            "death_benefit": 5200000,
            "annual_premium": 56000,
            "planned_contribution_date": "2026-05-01",
            "is_existing_policy_transfer": False,
        },
        "trust": {
            "asset_value": 9500000,
            "expected_growth_rate": 0.09,
            "grat_term_years": 6,
            "grat_annuity_rate": 0.045,
            "crat_term_years": 20,
            "crat_payout_rate": 0.055,
        },
        "stale_income": 390000,
        "stale_beneficiaries": 2,
        "stale_goal": "moderate",
    },
    {
        "client_id": "CLT-1005",
        "household_name": "Patel Household",
        "age": 72,
        "marital_status": "single",
        "filing_status": "SINGLE",
        "planning_year": 2026,
        "estate_value": 16800000,
        "liquid_assets": 1150000,
        "annual_non_ira_income": 92000,
        "marginal_tax_rate": 0.32,
        "beneficiary_count": 2,
        "philanthropic_intent": "moderate",
        "family_transfer_priority": "high",
        "retirement": {
            "traditional_balance": 1850000,
            "roth_balance": 120000,
            "expected_return": 0.052,
            "rmd_start_age": 73,
            "recommended_conversion_years": 4,
        },
        "life": {
            "death_benefit": 1900000,
            "annual_premium": 36000,
            "planned_contribution_date": "2026-03-25",
            "is_existing_policy_transfer": False,
        },
        "trust": {
            "asset_value": 3300000,
            "expected_growth_rate": 0.064,
            "grat_term_years": 5,
            "grat_annuity_rate": 0.042,
            "crat_term_years": 20,
            "crat_payout_rate": 0.055,
        },
        "stale_income": 120000,
        "stale_beneficiaries": 3,
        "stale_goal": "high",
    },
    {
        "client_id": "CLT-2001",
        "household_name": "Whitman Household",
        "age": 64,
        "marital_status": "married",
        "filing_status": "MFJ",
        "planning_year": 2026,
        "estate_value": 22900000,
        "liquid_assets": 2600000,
        "annual_non_ira_income": 205000,
        "marginal_tax_rate": 0.32,
        "beneficiary_count": 3,
        "philanthropic_intent": "low",
        "family_transfer_priority": "high",
        "retirement": {
            "traditional_balance": 3450000,
            "roth_balance": 0,
            "expected_return": 0.07,
            "rmd_start_age": 73,
            "recommended_conversion_years": 8,
        },
        "life": {
            "death_benefit": 3800000,
            "annual_premium": 62000,
            "planned_contribution_date": "2026-02-20",
            "is_existing_policy_transfer": False,
        },
        "trust": {
            "asset_value": 7200000,
            "expected_growth_rate": 0.078,
            "grat_term_years": 6,
            "grat_annuity_rate": 0.044,
            "crat_term_years": 20,
            "crat_payout_rate": 0.055,
        },
        "stale_income": 242000,
        "stale_beneficiaries": 2,
        "stale_goal": "moderate",
    },
    {
        "client_id": "CLT-2002",
        "household_name": "Okafor Household",
        "age": 61,
        "marital_status": "married",
        "filing_status": "MFJ",
        "planning_year": 2026,
        "estate_value": 28400000,
        "liquid_assets": 1900000,
        "annual_non_ira_income": 275000,
        "marginal_tax_rate": 0.35,
        "beneficiary_count": 5,
        "philanthropic_intent": "low",
        "family_transfer_priority": "high",
        "retirement": {
            "traditional_balance": 1450000,
            "roth_balance": 0,
            "expected_return": 0.058,
            "rmd_start_age": 73,
            "recommended_conversion_years": 6,
        },
        "life": {
            "death_benefit": 6000000,
            "annual_premium": 110000,
            "planned_contribution_date": "2026-06-03",
            "is_existing_policy_transfer": True,
        },
        "trust": {
            "asset_value": 6700000,
            "expected_growth_rate": 0.074,
            "grat_term_years": 6,
            "grat_annuity_rate": 0.043,
            "crat_term_years": 20,
            "crat_payout_rate": 0.055,
        },
        "stale_income": 248000,
        "stale_beneficiaries": 4,
        "stale_goal": "moderate",
    },
    {
        "client_id": "CLT-2003",
        "household_name": "Rossi Foundation Household",
        "age": 68,
        "marital_status": "single",
        "filing_status": "SINGLE",
        "planning_year": 2026,
        "estate_value": 21200000,
        "liquid_assets": 3100000,
        "annual_non_ira_income": 185000,
        "marginal_tax_rate": 0.35,
        "beneficiary_count": 1,
        "philanthropic_intent": "high",
        "family_transfer_priority": "moderate",
        "retirement": {
            "traditional_balance": 1250000,
            "roth_balance": 0,
            "expected_return": 0.055,
            "rmd_start_age": 73,
            "recommended_conversion_years": 5,
        },
        "life": {
            "death_benefit": 2100000,
            "annual_premium": 35000,
            "planned_contribution_date": "2026-04-18",
            "is_existing_policy_transfer": False,
        },
        "trust": {
            "asset_value": 5400000,
            "expected_growth_rate": 0.062,
            "grat_term_years": 5,
            "grat_annuity_rate": 0.043,
            "crat_term_years": 20,
            "crat_payout_rate": 0.055,
        },
        "stale_income": 205000,
        "stale_beneficiaries": 2,
        "stale_goal": "low",
    },
    {
        "client_id": "CLT-2004",
        "household_name": "Stein Technology Household",
        "age": 55,
        "marital_status": "single",
        "filing_status": "SINGLE",
        "planning_year": 2026,
        "estate_value": 35800000,
        "liquid_assets": 2800000,
        "annual_non_ira_income": 510000,
        "marginal_tax_rate": 0.37,
        "beneficiary_count": 4,
        "philanthropic_intent": "moderate",
        "family_transfer_priority": "high",
        "retirement": {
            "traditional_balance": 750000,
            "roth_balance": 0,
            "expected_return": 0.06,
            "rmd_start_age": 73,
            "recommended_conversion_years": 4,
        },
        "life": {
            "death_benefit": 7500000,
            "annual_premium": 82000,
            "planned_contribution_date": "2026-08-09",
            "is_existing_policy_transfer": False,
        },
        "trust": {
            "asset_value": 11800000,
            "expected_growth_rate": 0.092,
            "grat_term_years": 6,
            "grat_annuity_rate": 0.046,
            "crat_term_years": 20,
            "crat_payout_rate": 0.055,
        },
        "stale_income": 470000,
        "stale_beneficiaries": 3,
        "stale_goal": "high",
    },
    {
        "client_id": "CLT-2005",
        "household_name": "Nakamura Household",
        "age": 70,
        "marital_status": "married",
        "filing_status": "MFJ",
        "planning_year": 2026,
        "estate_value": 30500000,
        "liquid_assets": 3900000,
        "annual_non_ira_income": 168000,
        "marginal_tax_rate": 0.32,
        "beneficiary_count": 2,
        "philanthropic_intent": "moderate",
        "family_transfer_priority": "high",
        "retirement": {
            "traditional_balance": 4100000,
            "roth_balance": 250000,
            "expected_return": 0.06,
            "rmd_start_age": 73,
            "recommended_conversion_years": 5,
        },
        "life": {
            "death_benefit": 4600000,
            "annual_premium": 74000,
            "planned_contribution_date": "2026-09-14",
            "is_existing_policy_transfer": False,
        },
        "trust": {
            "asset_value": 7000000,
            "expected_growth_rate": 0.07,
            "grat_term_years": 5,
            "grat_annuity_rate": 0.044,
            "crat_term_years": 20,
            "crat_payout_rate": 0.055,
        },
        "stale_income": 198000,
        "stale_beneficiaries": 3,
        "stale_goal": "high",
    },
]


def add_target_records(clients, docs, accounts, life_policies, trusts):
    for t in TARGETS:
        clients.append(
            {
                "client_id": t["client_id"],
                "household_name": t["household_name"],
                "age": t["age"],
                "marital_status": t["marital_status"],
                "filing_status": t["filing_status"],
                "planning_year": t["planning_year"],
                "estate_value": t["estate_value"],
                "liquid_assets": t["liquid_assets"],
                "record_status": "active",
                "advisor_team": "Private Wealth Tax and Estate Desk",
            }
        )
        docs.extend(
            [
                {
                    "document_id": f"DOC-{t['client_id']}-CRM",
                    "client_id": t["client_id"],
                    "source_type": "CRM_NOTE",
                    "effective_date": "2025-11-20",
                    "title": "Prior CRM profile import",
                    "facts": {
                        "annual_non_ira_income": t["stale_income"],
                        "beneficiary_count": t["stale_beneficiaries"],
                        "philanthropic_intent": t["stale_goal"],
                        "family_transfer_priority": "moderate",
                    },
                },
                {
                    "document_id": f"DOC-{t['client_id']}-ATTY",
                    "client_id": t["client_id"],
                    "source_type": "ATTORNEY_MEMO",
                    "effective_date": "2026-01-18",
                    "title": "Attorney planning call notes",
                    "facts": {
                        "estate_value": t["estate_value"],
                        "family_transfer_priority": t["family_transfer_priority"],
                        "philanthropic_intent": t["philanthropic_intent"],
                    },
                },
                {
                    "document_id": f"DOC-{t['client_id']}-SIGNED",
                    "client_id": t["client_id"],
                    "source_type": "SIGNED_PROFILE",
                    "effective_date": "2026-02-06",
                    "title": "Signed household planning profile",
                    "facts": {
                        "annual_non_ira_income": t["annual_non_ira_income"],
                        "marginal_tax_rate": t["marginal_tax_rate"],
                        "beneficiary_count": t["beneficiary_count"],
                        "philanthropic_intent": t["philanthropic_intent"],
                        "family_transfer_priority": t["family_transfer_priority"],
                        "age": t["age"],
                        "planning_year": t["planning_year"],
                        "filing_status": t["filing_status"],
                        "marital_status": t["marital_status"],
                        "liquid_assets": t["liquid_assets"],
                        "estate_value": t["estate_value"],
                    },
                },
            ]
        )
        accounts.append(
            {
                "account_id": f"IRA-{t['client_id']}",
                "client_id": t["client_id"],
                "source_type": "CUSTODIAN_EXPORT",
                **t["retirement"],
            }
        )
        life_policies.append(
            {
                "policy_id": f"LIFE-{t['client_id']}",
                "client_id": t["client_id"],
                "proposed_owner": "ILIT",
                **t["life"],
            }
        )
        trusts.append(
            {
                "trust_case_id": f"TRUST-{t['client_id']}",
                "client_id": t["client_id"],
                **t["trust"],
            }
        )


def add_filler_records(clients, docs, accounts, life_policies, trusts):
    surnames = [
        "Arden",
        "Bishop",
        "Caldwell",
        "Dorsey",
        "Egan",
        "Fletcher",
        "Gibson",
        "Hale",
        "Irving",
        "Jensen",
        "Keller",
        "Larsen",
        "Morris",
        "Novak",
        "Olsen",
        "Parker",
        "Quinn",
        "Reed",
        "Sato",
        "Turner",
        "Ulrich",
        "Vega",
        "Warren",
        "Young",
    ]
    for i in range(1, 141):
        cid = f"CLT-{3000 + i:04d}"
        married = random.random() < 0.58
        filing = "MFJ" if married else random.choice(["SINGLE", "HOH"])
        age = random.randint(45, 78)
        estate = random.randint(4_500_000, 44_000_000)
        liquid = random.randint(250_000, 7_500_000)
        beneficiaries = random.randint(1, 5)
        income = random.randint(80_000, 620_000)
        philanthropic = random.choice(["low", "moderate", "high"])
        family_priority = random.choice(["moderate", "high"])
        surname = random.choice(surnames)
        clients.append(
            {
                "client_id": cid,
                "household_name": f"{surname} Household {i}",
                "age": age,
                "marital_status": "married" if married else "single",
                "filing_status": filing,
                "planning_year": 2026,
                "estate_value": estate,
                "liquid_assets": liquid,
                "record_status": random.choice(["active", "active", "monitoring"]),
                "advisor_team": random.choice(
                    ["Private Wealth Tax and Estate Desk", "Executive Advisory", "Family Office Services"]
                ),
            }
        )
        docs.append(
            {
                "document_id": f"DOC-{cid}-SIGNED",
                "client_id": cid,
                "source_type": "SIGNED_PROFILE",
                "effective_date": f"2026-{random.randint(1, 5):02d}-{random.randint(1, 26):02d}",
                "title": "Signed household planning profile",
                "facts": {
                    "annual_non_ira_income": income,
                    "marginal_tax_rate": random.choice([0.24, 0.32, 0.35, 0.37]),
                    "beneficiary_count": beneficiaries,
                    "philanthropic_intent": philanthropic,
                    "family_transfer_priority": family_priority,
                    "age": age,
                    "planning_year": 2026,
                    "filing_status": filing,
                    "marital_status": "married" if married else "single",
                    "liquid_assets": liquid,
                    "estate_value": estate,
                },
            }
        )
        docs.append(
            {
                "document_id": f"DOC-{cid}-CRM",
                "client_id": cid,
                "source_type": "CRM_NOTE",
                "effective_date": "2025-10-15",
                "title": "CRM import before spring refresh",
                "facts": {
                    "annual_non_ira_income": max(40000, income + random.randint(-50000, 50000)),
                    "beneficiary_count": max(1, beneficiaries + random.choice([-1, 0, 1])),
                    "philanthropic_intent": random.choice(["low", "moderate", "high"]),
                },
            }
        )
        accounts.append(
            {
                "account_id": f"IRA-{cid}",
                "client_id": cid,
                "source_type": "CUSTODIAN_EXPORT",
                "traditional_balance": random.randint(150_000, 5_200_000),
                "roth_balance": random.randint(0, 420_000),
                "expected_return": round(random.uniform(0.045, 0.08), 3),
                "rmd_start_age": 73,
                "recommended_conversion_years": random.randint(4, 8),
            }
        )
        life_policies.append(
            {
                "policy_id": f"LIFE-{cid}",
                "client_id": cid,
                "proposed_owner": "ILIT",
                "death_benefit": random.randint(1_000_000, 8_500_000),
                "annual_premium": random.randint(18_000, 135_000),
                "planned_contribution_date": f"2026-{random.randint(2, 10):02d}-{random.randint(1, 24):02d}",
                "is_existing_policy_transfer": random.random() < 0.22,
            }
        )
        trusts.append(
            {
                "trust_case_id": f"TRUST-{cid}",
                "client_id": cid,
                "asset_value": random.randint(1_500_000, 12_500_000),
                "expected_growth_rate": round(random.uniform(0.045, 0.095), 3),
                "grat_term_years": random.randint(4, 8),
                "grat_annuity_rate": round(random.uniform(0.035, 0.052), 3),
                "crat_term_years": 20,
                "crat_payout_rate": 0.055,
            }
        )


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    clients, docs, accounts, life_policies, trusts = [], [], [], [], []
    add_target_records(clients, docs, accounts, life_policies, trusts)
    add_filler_records(clients, docs, accounts, life_policies, trusts)
    files = {
        "clients.json": clients,
        "source_documents.json": docs,
        "retirement_accounts.json": accounts,
        "life_insurance.json": life_policies,
        "trust_candidates.json": trusts,
        "tax_policy.json": TAX_POLICY,
        "rmd_factors.json": {str(k): v for k, v in RMD_FACTORS.items()},
    }
    for name, payload in files.items():
        (DATA_DIR / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "seed": SEED,
        "generated_files": sorted(files),
        "record_counts": {
            "clients": len(clients),
            "source_documents": len(docs),
            "retirement_accounts": len(accounts),
            "life_insurance": len(life_policies),
            "trust_candidates": len(trusts),
        },
        "solver_entry_points": [
            "/api/clients",
            "/api/clients/{client_id}",
            "/api/source-documents?client_id=...",
            "/api/retirement-accounts?client_id=...",
            "/api/life-insurance?client_id=...",
            "/api/trust-candidates?client_id=...",
            "/api/policies/tax",
            "/api/rmd-factors",
        ],
    }
    (DATA_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
