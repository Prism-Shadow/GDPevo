#!/usr/bin/env python3
"""Generate the shared credit office environment data."""

from __future__ import annotations

import csv
import json
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path


SEED = 11011
POLICY_VERSION = "credit_policy_v2025Q1"
FDIC_VERSION = "fdic_q4_2024"
NCUA_VERSION = "ncua_q1_2025"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "credit_office.db"


ENDPOINTS = [
    "/api/health",
    "/api/manifest",
    "/api/branches",
    "/api/branches/{branch_id}",
    "/api/branches/{branch_id}/metrics",
    "/api/branches/{branch_id}/loans",
    "/api/branches/{branch_id}/sector-exposures",
    "/api/branches/{branch_id}/applications",
    "/api/policies",
    "/api/benchmarks/fdic/q4-2024",
    "/api/benchmarks/ncua/q1-2025",
    "/api/credit-union-segments/{segment_id}",
]


BRANCHES = [
    {
        "branch_id": "REDWOOD",
        "branch_name": "Redwood Branch",
        "institution_type": "bank",
        "total_assets": 482500000.0,
        "lending_capacity_q1": 8200000.0,
        "sector_ceiling_pct": 0.23,
        "cre_policy_limit_pct": 0.31,
        "fdic_benchmark_set": FDIC_VERSION,
        "state_code": "CA",
    },
    {
        "branch_id": "LAKEVIEW",
        "branch_name": "Lakeview Branch",
        "institution_type": "bank",
        "total_assets": 368200000.0,
        "lending_capacity_q1": 5900000.0,
        "sector_ceiling_pct": 0.21,
        "cre_policy_limit_pct": 0.28,
        "fdic_benchmark_set": FDIC_VERSION,
        "state_code": "MI",
    },
    {
        "branch_id": "SUMMIT",
        "branch_name": "Summit Branch",
        "institution_type": "bank",
        "total_assets": 427900000.0,
        "lending_capacity_q1": 6400000.0,
        "sector_ceiling_pct": 0.22,
        "cre_policy_limit_pct": 0.30,
        "fdic_benchmark_set": FDIC_VERSION,
        "state_code": "CO",
    },
    {
        "branch_id": "HARBOR",
        "branch_name": "Harbor Branch",
        "institution_type": "bank",
        "total_assets": 511600000.0,
        "lending_capacity_q1": 7600000.0,
        "sector_ceiling_pct": 0.24,
        "cre_policy_limit_pct": 0.29,
        "fdic_benchmark_set": FDIC_VERSION,
        "state_code": "WA",
    },
    {
        "branch_id": "NORTHSTAR",
        "branch_name": "Northstar Branch",
        "institution_type": "bank",
        "total_assets": 623400000.0,
        "lending_capacity_q1": 9100000.0,
        "sector_ceiling_pct": 0.20,
        "cre_policy_limit_pct": 0.27,
        "fdic_benchmark_set": FDIC_VERSION,
        "state_code": "MN",
    },
    {
        "branch_id": "EASTGATE",
        "branch_name": "Eastgate Branch",
        "institution_type": "bank",
        "total_assets": 389100000.0,
        "lending_capacity_q1": 4700000.0,
        "sector_ceiling_pct": 0.19,
        "cre_policy_limit_pct": 0.26,
        "fdic_benchmark_set": FDIC_VERSION,
        "state_code": "PA",
    },
    {
        "branch_id": "CENTRAL",
        "branch_name": "Central Branch",
        "institution_type": "bank",
        "total_assets": 548300000.0,
        "lending_capacity_q1": 7200000.0,
        "sector_ceiling_pct": 0.22,
        "cre_policy_limit_pct": 0.30,
        "fdic_benchmark_set": FDIC_VERSION,
        "state_code": "OH",
    },
    {
        "branch_id": "SOUTHPORT",
        "branch_name": "Southport Branch",
        "institution_type": "bank",
        "total_assets": 456700000.0,
        "lending_capacity_q1": 5300000.0,
        "sector_ceiling_pct": 0.20,
        "cre_policy_limit_pct": 0.25,
        "fdic_benchmark_set": FDIC_VERSION,
        "state_code": "SC",
    },
    {
        "branch_id": "CIVIC_NC_FIRE_EMS",
        "branch_name": "Civic Carolinas Public Safety Credit Union",
        "institution_type": "credit_union",
        "total_assets": 214800000.0,
        "lending_capacity_q1": 2900000.0,
        "sector_ceiling_pct": 0.26,
        "cre_policy_limit_pct": 0.16,
        "fdic_benchmark_set": "",
        "state_code": "NC",
    },
    {
        "branch_id": "TRISTATE_GA_AMBULANCE",
        "branch_name": "TriState Ambulance Services Credit Union",
        "institution_type": "credit_union",
        "total_assets": 186500000.0,
        "lending_capacity_q1": 2250000.0,
        "sector_ceiling_pct": 0.24,
        "cre_policy_limit_pct": 0.14,
        "fdic_benchmark_set": "",
        "state_code": "GA",
    },
]


POLICIES = {
    "policy_version": POLICY_VERSION,
    "risk_rating": {
        "dscr_thresholds": [
            {"min": 1.50, "rating": 3},
            {"min": 1.25, "rating": 4},
            {"min": 1.05, "rating": 5},
            {"min": 1.00, "rating": 6},
            {"max_below": 1.00, "rating": 7},
        ],
        "ltv_thresholds": [
            {"max": 0.65, "rating": 3},
            {"max": 0.75, "rating": 4},
            {"max": 0.85, "rating": 5},
            {"max": 1.00, "rating": 6},
            {"min_above": 1.00, "rating": 7},
        ],
        "delinquency_minimums": {
            "Current": None,
            "30 Days Past Due": 4,
            "60 Days Past Due": 5,
            "90+ Days Past Due": 7,
            "Nonaccrual": 8,
        },
        "dominant_factor_rule": "Final re-derived rating is the worst numeric rating from available DSCR, LTV or collateral, and delinquency factors.",
        "material_downgrade_notches": 2,
    },
    "cdfi_factor_scores": {
        "ltv": [
            {"range": "<0.40", "score": 0},
            {"range": "0.40-0.60", "score": 2},
            {"range": "0.60-0.80", "score": 4},
            {"range": ">0.80", "score": 6},
        ],
        "fico": [
            {"range": ">720", "score": 0},
            {"range": "680-720", "score": 1},
            {"range": "580-679", "score": 3},
            {"range": "<580", "score": 5},
        ],
        "debt_to_asset": [
            {"range": "<0.40", "score": 0},
            {"range": "0.40-0.60", "score": 2},
            {"range": "0.60-0.80", "score": 4},
            {"range": ">0.80", "score": 6},
        ],
        "liquidity_months": [
            {"range": ">12", "score": 0},
            {"range": "6-12", "score": 1},
            {"range": "3-6", "score": 3},
            {"range": "<3", "score": 5},
        ],
        "classes": [
            {"score_range": "0-5", "class": "Prime"},
            {"score_range": "6-9", "class": "Desirable"},
            {"score_range": "10-13", "class": "Satisfactory"},
            {"score_range": "14-18", "class": "Watch"},
            {"score_range": ">=19", "class": "Doubtful"},
            {"score_range": ">=19 and ltv>1.0", "class": "Projected Loss"},
        ],
    },
    "cre_weighted_score": {
        "weights": {
            "collateral_exposure": 0.36,
            "capacity": 0.45,
            "character": 0.05,
            "conditions": 0.11,
            "capital": 0.03,
        },
        "classes": [
            {"max": 2.0, "class": "approve_quality"},
            {"max": 3.0, "class": "conditional"},
            {"min_above": 3.0, "class": "weak"},
        ],
    },
    "capacity_concentration": {
        "lending_capacity_field": "branches.lending_capacity_q1",
        "single_sector_default_field": "branches.sector_ceiling_pct",
        "branch_sector_override_table": "sector_exposures",
        "allowed_mitigations": [
            "participation_required",
            "reduced_amount",
            "board_exception",
        ],
        "grandfathering_note": "Existing over-ceiling exposure may be grandfathered, but new approvals may not worsen that sector without mitigation.",
    },
    "stress": {
        "watch_list_parallel_shock": "+200bp",
        "watch_list_formula": "stressed_dscr = dscr / (1 + 0.18)",
        "cre_dual_stress_formula": "stressed_dscr = dscr * 0.85 / (1 + 0.18)",
        "coverage_breach_threshold": 1.00,
    },
}


FDIC_Q4_2024 = {
    "benchmark_version": FDIC_VERSION,
    "total_loans_noncurrent_pct": 0.0098,
    "total_real_estate_noncurrent_pct": 0.0121,
    "total_real_estate_30_89_pct": 0.0051,
    "construction_development_noncurrent_pct": 0.0076,
    "construction_development_30_89_pct": 0.0042,
}


NCUA_ROWS = [
    {
        "state_code": "US",
        "delinquency_bps": 58,
        "loan_to_share_pct": 69,
        "roaa_bps": 62,
        "positive_net_income_pct": 84,
    },
    {
        "state_code": "NC",
        "delinquency_bps": 79,
        "loan_to_share_pct": 76,
        "roaa_bps": 44,
        "positive_net_income_pct": 76,
    },
    {
        "state_code": "SC",
        "delinquency_bps": 72,
        "loan_to_share_pct": 73,
        "roaa_bps": 51,
        "positive_net_income_pct": 79,
    },
    {
        "state_code": "GA",
        "delinquency_bps": 88,
        "loan_to_share_pct": 74,
        "roaa_bps": 68,
        "positive_net_income_pct": 82,
    },
    {
        "state_code": "TN",
        "delinquency_bps": 64,
        "loan_to_share_pct": 71,
        "roaa_bps": 59,
        "positive_net_income_pct": 81,
    },
    {
        "state_code": "VA",
        "delinquency_bps": 53,
        "loan_to_share_pct": 67,
        "roaa_bps": 65,
        "positive_net_income_pct": 85,
    },
    {
        "state_code": "FL",
        "delinquency_bps": 91,
        "loan_to_share_pct": 78,
        "roaa_bps": 55,
        "positive_net_income_pct": 78,
    },
    {
        "state_code": "AL",
        "delinquency_bps": 83,
        "loan_to_share_pct": 72,
        "roaa_bps": 42,
        "positive_net_income_pct": 75,
    },
    {
        "state_code": "PA",
        "delinquency_bps": 61,
        "loan_to_share_pct": 70,
        "roaa_bps": 57,
        "positive_net_income_pct": 80,
    },
    {
        "state_code": "OH",
        "delinquency_bps": 66,
        "loan_to_share_pct": 68,
        "roaa_bps": 60,
        "positive_net_income_pct": 83,
    },
    {
        "state_code": "MI",
        "delinquency_bps": 74,
        "loan_to_share_pct": 75,
        "roaa_bps": 46,
        "positive_net_income_pct": 77,
    },
    {
        "state_code": "MN",
        "delinquency_bps": 49,
        "loan_to_share_pct": 65,
        "roaa_bps": 71,
        "positive_net_income_pct": 87,
    },
]


CREDIT_UNION_SEGMENTS = [
    {
        "segment_id": "CIVIC_NC_FIRE_EMS",
        "segment_name": "Civic Carolinas fire and EMS equipment loans",
        "state_code": "NC",
        "member_profile": "Municipal fire districts, volunteer rescue squads, and county EMS support entities.",
        "portfolio_focus": ["fire apparatus", "ambulance remounts", "thermal imaging", "station generators"],
        "current_outstanding": 16850000.0,
        "quarterly_capacity": 2900000.0,
        "risk_tolerance": "moderate",
        "minimum_checklist": [
            "board_authorization",
            "equipment_invoice",
            "public_contract_or_tax_support",
            "proof_of_insurance",
            "ucc_or_title_lien",
        ],
        "internal_context": {
            "recent_delinquency_bps": 86,
            "portfolio_yield_pct": 6.35,
            "staffing_constraint": "One senior underwriter is assigned to equipment renewals through Q2.",
            "control_issue": "Two files missed insurance binder follow-up before close.",
        },
        "peer_states": ["SC", "TN", "VA"],
        "notes": "External state delinquency is above national median, but capacity remains available when added closing controls are used.",
    },
    {
        "segment_id": "TRISTATE_GA_AMBULANCE",
        "segment_name": "TriState ambulance and rescue equipment loans",
        "state_code": "GA",
        "member_profile": "Private ambulance contractors, nonprofit rescue squads, and county-backed EMS providers.",
        "portfolio_focus": ["ambulance chassis", "cardiac monitors", "fleet replacement", "dispatch systems"],
        "current_outstanding": 14240000.0,
        "quarterly_capacity": 2250000.0,
        "risk_tolerance": "restrained",
        "minimum_checklist": [
            "board_authorization",
            "fleet_replacement_plan",
            "payer_contract_summary",
            "proof_of_insurance",
            "ucc_or_title_lien",
        ],
        "internal_context": {
            "recent_delinquency_bps": 93,
            "portfolio_yield_pct": 6.55,
            "staffing_constraint": "Field audits are running six weeks behind schedule.",
            "control_issue": "A prior borrower submitted stale payer-contract documentation.",
        },
        "peer_states": ["FL", "AL", "TN"],
        "notes": "Georgia earnings are stronger than the national median, while delinquency is materially weaker.",
    },
]


BORROWER_ROOTS = [
    "Avery",
    "Bennett",
    "Cedar",
    "Cobalt",
    "Crescent",
    "Elm",
    "Harbor",
    "Juniper",
    "Keystone",
    "Lumen",
    "Meridian",
    "Northpoint",
    "Oakline",
    "Pioneer",
    "Redstone",
    "Ridge",
    "Silver",
    "Stonebridge",
    "Summit",
    "Willow",
]

BUSINESS_SUFFIXES = [
    "Holdings LLC",
    "Properties LLC",
    "Services Inc",
    "Supply Co",
    "Partners LP",
    "Medical Group",
    "Transport LLC",
    "Manufacturing Inc",
    "Retail Group",
    "Ventures LLC",
]

LOAN_TYPES = ["CRE", "C&I", "SBA", "Residential Mortgage", "HELOC", "Consumer", "Equipment"]
PAYMENT_STATUSES = ["Current", "30 Days Past Due", "60 Days Past Due", "90+ Days Past Due", "Nonaccrual"]
GUARANTOR_STRENGTHS = ["none", "limited", "standard", "strong"]

SECTORS_BY_TYPE = {
    "CRE": ["Office", "Retail CRE", "Multifamily", "Hospitality", "Construction"],
    "C&I": ["Healthcare", "Manufacturing", "Logistics", "Retail Trade", "Professional Services"],
    "SBA": ["Healthcare", "Hospitality", "Personal Services", "Contractor"],
    "Residential Mortgage": ["Residential"],
    "HELOC": ["Residential"],
    "Consumer": ["Consumer"],
    "Equipment": ["Public Safety", "Transportation", "Construction", "Medical Equipment"],
}


def money(value: float) -> float:
    return round(float(value), 2)


def ratio(value: float) -> float:
    return round(float(value), 4)


def maybe(value, probability: float, rng: random.Random):
    return None if rng.random() < probability else value


def annual_review(rng: random.Random, stale: bool = False) -> str:
    base = date(2025, 3, 31)
    days_back = rng.randint(390, 820) if stale else rng.randint(20, 360)
    return (base - timedelta(days=days_back)).isoformat()


def random_borrower(rng: random.Random) -> str:
    return f"{rng.choice(BORROWER_ROOTS)} {rng.choice(BUSINESS_SUFFIXES)}"


def status_days(status: str, rng: random.Random) -> int:
    if status == "Current":
        return 0
    if status == "30 Days Past Due":
        return rng.randint(30, 55)
    if status == "60 Days Past Due":
        return rng.randint(60, 88)
    if status == "90+ Days Past Due":
        return rng.randint(90, 140)
    return rng.randint(120, 260)


def random_status(rng: random.Random) -> str:
    return rng.choices(PAYMENT_STATUSES, weights=[75, 10, 6, 5, 4], k=1)[0]


def random_rating(rng: random.Random, status: str) -> int:
    base = {
        "Current": rng.choices([2, 3, 4, 5, 6], weights=[12, 34, 32, 16, 6], k=1)[0],
        "30 Days Past Due": rng.choices([3, 4, 5, 6], weights=[12, 45, 31, 12], k=1)[0],
        "60 Days Past Due": rng.choices([4, 5, 6, 7], weights=[18, 36, 34, 12], k=1)[0],
        "90+ Days Past Due": rng.choices([5, 6, 7, 8], weights=[18, 25, 37, 20], k=1)[0],
        "Nonaccrual": rng.choices([6, 7, 8, 9], weights=[12, 26, 44, 18], k=1)[0],
    }[status]
    if rng.random() < 0.14:
        return max(2, base - rng.choice([1, 2]))
    return base


def make_loan(rng: random.Random, branch_id: str, index: int, loan_type: str | None = None, **overrides):
    loan_type = loan_type or rng.choice(LOAN_TYPES)
    sector = overrides.pop("sector", rng.choice(SECTORS_BY_TYPE[loan_type]))
    status = overrides.pop("payment_status", random_status(rng))
    days = overrides.pop("days_past_due", status_days(status, rng))
    balance = overrides.pop("outstanding_balance", money(rng.uniform(85000, 1750000)))
    is_consumer = loan_type in {"Consumer", "Residential Mortgage", "HELOC"}
    ltv = overrides.pop("ltv", None if is_consumer and rng.random() < 0.35 else ratio(rng.uniform(0.42, 1.12)))
    collateral_value = overrides.pop(
        "collateral_value",
        None if ltv is None else money(balance / max(ltv, 0.05)),
    )
    dscr = overrides.pop("dscr", None if is_consumer and rng.random() < 0.75 else round(rng.uniform(0.78, 1.82), 2))
    fico = overrides.pop("fico", rng.randint(545, 792) if is_consumer or rng.random() < 0.12 else None)
    liquidity_months = overrides.pop("liquidity_months", None if is_consumer else round(rng.uniform(1.2, 18.0), 1))
    debt_to_asset = overrides.pop(
        "debt_to_asset", None if is_consumer and rng.random() < 0.55 else ratio(rng.uniform(0.24, 0.91))
    )
    stale = overrides.pop("stale_review", rng.random() < 0.22)
    note_options = [
        "Metrics align with prior file except updated collateral tickler.",
        "Relationship manager notes borrower dispute on payment timing.",
        "Annual review package has stale guarantor liquidity exhibit.",
        "Current rating was not refreshed after covenant update.",
        "Collateral value comes from an older desktop appraisal.",
        "Borrower name resembles another customer in a different branch.",
    ]
    loan = {
        "loan_id": overrides.pop("loan_id", f"{branch_id[:3]}-LN-{index:03d}"),
        "branch_id": branch_id,
        "borrower_name": overrides.pop("borrower_name", random_borrower(rng)),
        "loan_type": loan_type,
        "sector": sector,
        "outstanding_balance": money(balance),
        "current_rating": overrides.pop("current_rating", random_rating(rng, status)),
        "payment_status": status,
        "days_past_due": days,
        "dscr": dscr,
        "ltv": ltv,
        "collateral_value": collateral_value,
        "fico": fico,
        "liquidity_months": liquidity_months,
        "debt_to_asset": debt_to_asset,
        "interest_rate": overrides.pop("interest_rate", round(rng.uniform(4.85, 10.75), 2)),
        "annual_debt_service": overrides.pop("annual_debt_service", money(balance * rng.uniform(0.075, 0.185))),
        "guarantor_strength": overrides.pop("guarantor_strength", rng.choice(GUARANTOR_STRENGTHS)),
        "annual_review_date": overrides.pop("annual_review_date", annual_review(rng, stale=stale)),
        "notes": overrides.pop("notes", rng.choice(note_options)),
    }
    loan.update(overrides)
    return loan


def special_loans(rng: random.Random):
    specials = {
        "REDWOOD": [
            make_loan(
                rng,
                "REDWOOD",
                901,
                "CRE",
                loan_id="RED-LN-901",
                borrower_name="Cedar Harbor Properties LLC",
                sector="Office",
                outstanding_balance=1725000,
                current_rating=4,
                payment_status="Nonaccrual",
                days_past_due=182,
                dscr=0.92,
                ltv=1.08,
                guarantor_strength="limited",
                notes="Nonaccrual credit still carried near pass rating after missed renewal.",
            ),
            make_loan(
                rng,
                "REDWOOD",
                902,
                "C&I",
                loan_id="RED-LN-902",
                borrower_name="Cedar Harbor Services Inc",
                sector="Healthcare",
                outstanding_balance=980000,
                current_rating=3,
                payment_status="60 Days Past Due",
                days_past_due=64,
                dscr=1.03,
                ltv=0.74,
                guarantor_strength="standard",
                notes="Similar borrower name appears in Harbor records; this is a Redwood C&I exposure.",
            ),
            make_loan(
                rng,
                "REDWOOD",
                903,
                "CRE",
                loan_id="RED-LN-903",
                borrower_name="Willow Market Properties LLC",
                sector="Retail CRE",
                outstanding_balance=1350000,
                current_rating=5,
                payment_status="Current",
                days_past_due=0,
                dscr=1.19,
                ltv=0.89,
                guarantor_strength="standard",
                notes="Current payment status masks thin coverage and high leverage.",
            ),
        ],
        "SUMMIT": [
            make_loan(
                rng,
                "SUMMIT",
                901,
                "Equipment",
                loan_id="SUM-LN-901",
                borrower_name="Summit Ridge Transport LLC",
                sector="Transportation",
                outstanding_balance=1220000,
                current_rating=7,
                payment_status="Current",
                days_past_due=0,
                dscr=1.09,
                ltv=0.93,
                liquidity_months=2.4,
                debt_to_asset=0.82,
                notes="Watch-list borrower is current but structurally weak.",
            ),
            make_loan(
                rng,
                "SUMMIT",
                902,
                "CRE",
                loan_id="SUM-LN-902",
                borrower_name="Keystone Lodge Holdings LLC",
                sector="Hospitality",
                outstanding_balance=1860000,
                current_rating=8,
                payment_status="Nonaccrual",
                days_past_due=155,
                dscr=0.84,
                ltv=1.18,
                liquidity_months=1.6,
                debt_to_asset=0.88,
                notes="Underwater collateral and nonaccrual status indicate projected loss review.",
            ),
        ],
        "NORTHSTAR": [
            make_loan(
                rng,
                "NORTHSTAR",
                901,
                "CRE",
                loan_id="NOR-LN-901",
                borrower_name="Northpoint Medical Properties LLC",
                sector="Healthcare",
                outstanding_balance=2380000,
                current_rating=4,
                payment_status="90+ Days Past Due",
                days_past_due=96,
                dscr=1.42,
                ltv=0.69,
                notes="Adequate DSCR but severe delinquency overrides the metric.",
            ),
            make_loan(
                rng,
                "NORTHSTAR",
                902,
                "C&I",
                loan_id="NOR-LN-902",
                borrower_name="Lumen Logistics Supply Co",
                sector="Logistics",
                outstanding_balance=1640000,
                current_rating=3,
                payment_status="Current",
                days_past_due=0,
                dscr=0.97,
                ltv=0.78,
                notes="Current rating is stale after covenant default.",
            ),
        ],
        "CENTRAL": [
            make_loan(
                rng,
                "CENTRAL",
                901,
                "CRE",
                loan_id="CEN-LN-901",
                borrower_name="Central Harbor Hotel Partners LP",
                sector="Hospitality",
                outstanding_balance=3210000,
                current_rating=7,
                payment_status="Nonaccrual",
                days_past_due=204,
                dscr=0.81,
                ltv=1.21,
                liquidity_months=1.1,
                debt_to_asset=0.89,
                notes="Large hotel exposure dominates nonperforming balance.",
            ),
            make_loan(
                rng,
                "CENTRAL",
                902,
                "C&I",
                loan_id="CEN-LN-902",
                borrower_name="Cobalt Medical Group",
                sector="Healthcare",
                outstanding_balance=735000,
                current_rating=6,
                payment_status="Current",
                days_past_due=0,
                dscr=1.04,
                ltv=0.86,
                liquidity_months=3.8,
                debt_to_asset=0.74,
                notes="Current borrower but factor scores point to watch status.",
            ),
        ],
    }
    return specials


def build_loans(rng: random.Random):
    loans = []
    counts = {
        "REDWOOD": 18,
        "LAKEVIEW": 16,
        "SUMMIT": 18,
        "HARBOR": 17,
        "NORTHSTAR": 22,
        "EASTGATE": 16,
        "CENTRAL": 18,
        "SOUTHPORT": 16,
        "CIVIC_NC_FIRE_EMS": 10,
        "TRISTATE_GA_AMBULANCE": 10,
    }
    specials = special_loans(rng)
    for branch_id, count in counts.items():
        existing = specials.get(branch_id, [])
        loans.extend(existing)
        for i in range(1, count - len(existing) + 1):
            if branch_id.endswith("FIRE_EMS") or branch_id.endswith("AMBULANCE"):
                loan_type = "Equipment"
            else:
                loan_type = rng.choices(LOAN_TYPES, weights=[26, 22, 10, 14, 9, 10, 9], k=1)[0]
            loans.append(make_loan(rng, branch_id, i, loan_type))
    return loans


def make_application(rng: random.Random, branch_id: str, index: int, loan_type: str, **overrides):
    sector = overrides.pop("sector", rng.choice(SECTORS_BY_TYPE[loan_type]))
    amount = overrides.pop("requested_amount", money(rng.uniform(180000, 1850000)))
    is_consumer = loan_type in {"Consumer", "Residential Mortgage", "HELOC"}
    ltv = overrides.pop("ltv", ratio(rng.uniform(0.46, 1.08)))
    collateral_value = overrides.pop("collateral_value", money(amount / max(ltv, 0.05)))
    dscr = overrides.pop("dscr", None if is_consumer and rng.random() < 0.75 else round(rng.uniform(0.88, 1.75), 2))
    fico = overrides.pop("fico", rng.randint(555, 808) if is_consumer or rng.random() < 0.18 else None)
    app = {
        "application_id": overrides.pop("application_id", f"{branch_id[:3]}-APP-{index:03d}"),
        "branch_id": branch_id,
        "applicant_name": overrides.pop(
            "applicant_name",
            f"{rng.choice(['Alex', 'Jordan', 'Morgan', 'Taylor', 'Casey', 'Riley'])} {rng.choice(['Avery', 'Bennett', 'Cole', 'Hayes', 'Reed'])}",
        ),
        "business_name": overrides.pop("business_name", random_borrower(rng) if not is_consumer else ""),
        "loan_type": loan_type,
        "sector": sector,
        "requested_amount": money(amount),
        "purpose": overrides.pop(
            "purpose",
            rng.choice(
                [
                    "working capital",
                    "equipment purchase",
                    "property acquisition",
                    "refinance",
                    "line renewal",
                    "fleet replacement",
                ]
            ),
        ),
        "proposed_rate": overrides.pop("proposed_rate", round(rng.uniform(6.0, 11.25), 2)),
        "term_months": overrides.pop("term_months", rng.choice([36, 48, 60, 84, 120, 180, 240])),
        "collateral_value": overrides.pop("collateral_value_override", collateral_value),
        "ltv": ltv,
        "dscr": dscr,
        "fico": fico,
        "years_in_business": overrides.pop(
            "years_in_business", None if is_consumer else round(rng.uniform(0.5, 22.0), 1)
        ),
        "annual_revenue": overrides.pop(
            "annual_revenue", None if is_consumer else money(rng.uniform(450000, 9200000))
        ),
        "net_income": overrides.pop("net_income", None if is_consumer else money(rng.uniform(-50000, 1150000))),
        "total_debt": overrides.pop("total_debt", None if is_consumer else money(rng.uniform(150000, 5400000))),
        "total_assets": overrides.pop("total_assets", None if is_consumer else money(rng.uniform(400000, 9800000))),
        "dti": overrides.pop("dti", ratio(rng.uniform(0.22, 0.64)) if is_consumer else None),
        "sba_guaranty_pct": overrides.pop(
            "sba_guaranty_pct", rng.choice([0.5, 0.75, 0.85]) if loan_type == "SBA" else None
        ),
        "bankruptcy_months_ago": overrides.pop(
            "bankruptcy_months_ago", None if rng.random() < 0.88 else rng.randint(9, 72)
        ),
        "prior_delinquencies_12m": overrides.pop(
            "prior_delinquencies_12m", rng.choices([0, 1, 2, 3, 4], weights=[54, 22, 13, 7, 4], k=1)[0]
        ),
        "existing_relationship_years": overrides.pop("existing_relationship_years", round(rng.uniform(0.0, 16.0), 1)),
        "co_guarantor_strength": overrides.pop("co_guarantor_strength", rng.choice(GUARANTOR_STRENGTHS)),
        "relationship_deposit_balance": overrides.pop("relationship_deposit_balance", money(rng.uniform(0, 1250000))),
        "documentation_complete": overrides.pop("documentation_complete", 0 if rng.random() < 0.18 else 1),
        "notes": overrides.pop("notes", "Relationship manager package includes mixed qualitative mitigants."),
    }
    app.update(overrides)
    return app


def build_applications(rng: random.Random):
    branch_types = {
        "REDWOOD": ["CRE", "C&I", "SBA", "Consumer", "Equipment"],
        "LAKEVIEW": ["CRE", "C&I", "SBA", "Consumer", "Equipment", "Residential Mortgage"],
        "SUMMIT": ["Equipment", "C&I", "CRE", "Consumer", "SBA"],
        "HARBOR": ["CRE", "CRE", "C&I", "SBA", "Consumer"],
        "NORTHSTAR": ["CRE", "C&I", "SBA", "Residential Mortgage", "Equipment"],
        "EASTGATE": ["C&I", "CRE", "SBA", "Residential Mortgage", "Healthcare", "Consumer"],
        "CENTRAL": ["CRE", "C&I", "SBA", "Equipment", "Consumer"],
        "SOUTHPORT": ["CRE", "C&I", "SBA", "Residential Mortgage", "Consumer", "Equipment"],
        "CIVIC_NC_FIRE_EMS": ["Equipment", "Equipment", "Consumer"],
        "TRISTATE_GA_AMBULANCE": ["Equipment", "Equipment", "Consumer"],
    }
    applications = []
    idx_by_branch = {}
    for branch_id, types in branch_types.items():
        idx_by_branch[branch_id] = 0
        for loan_type in types:
            if loan_type == "Healthcare":
                loan_type = "C&I"
                sector = "Healthcare"
            else:
                sector = None
            idx_by_branch[branch_id] += 1
            applications.append(
                make_application(
                    rng,
                    branch_id,
                    idx_by_branch[branch_id],
                    loan_type,
                    sector=sector or rng.choice(SECTORS_BY_TYPE[loan_type]),
                )
            )

    overrides = [
        make_application(
            rng,
            "LAKEVIEW",
            901,
            "C&I",
            application_id="LAK-APP-901",
            business_name="Avery Surgical Partners LP",
            sector="Healthcare",
            requested_amount=1650000,
            dscr=1.62,
            ltv=0.58,
            years_in_business=12.0,
            documentation_complete=1,
            notes="Strong borrower but healthcare sector is already near its branch exposure ceiling.",
        ),
        make_application(
            rng,
            "LAKEVIEW",
            902,
            "SBA",
            application_id="LAK-APP-902",
            business_name="Cedar Cafe Ventures LLC",
            sector="Hospitality",
            requested_amount=840000,
            dscr=1.18,
            ltv=0.79,
            sba_guaranty_pct=0.75,
            years_in_business=1.4,
            documentation_complete=1,
            notes="Startup risk is partly mitigated by SBA guaranty and deposit relationship.",
        ),
        make_application(
            rng,
            "LAKEVIEW",
            903,
            "Consumer",
            application_id="LAK-APP-903",
            requested_amount=95000,
            fico=548,
            ltv=0.93,
            bankruptcy_months_ago=14,
            prior_delinquencies_12m=3,
            documentation_complete=1,
            notes="Consumer borrower has recent bankruptcy and repeated delinquencies.",
        ),
        make_application(
            rng,
            "HARBOR",
            901,
            "CRE",
            application_id="HAR-APP-901",
            business_name="Harbor Cold Storage LLC",
            sector="Industrial CRE",
            requested_amount=2100000,
            dscr=1.47,
            ltv=0.68,
            years_in_business=8.5,
            documentation_complete=1,
            notes="CRE request has stable tenant roll but branch CRE exposure is elevated.",
        ),
        make_application(
            rng,
            "HARBOR",
            902,
            "CRE",
            application_id="HAR-APP-902",
            business_name="Willow Bay Hotel Partners LP",
            sector="Hospitality",
            requested_amount=2050000,
            dscr=1.32,
            ltv=0.76,
            years_in_business=5.0,
            documentation_complete=1,
            notes="Competing CRE request depends on seasonal cash flow and sponsor support.",
        ),
        make_application(
            rng,
            "EASTGATE",
            901,
            "C&I",
            application_id="EAS-APP-901",
            business_name="Eastgate Home Health LLC",
            sector="Healthcare",
            requested_amount=1900000,
            dscr=1.55,
            ltv=0.62,
            years_in_business=10.0,
            documentation_complete=1,
            notes="Strong applicant, but healthcare exposure would exceed sector limit without mitigation.",
        ),
        make_application(
            rng,
            "EASTGATE",
            902,
            "CRE",
            application_id="EAS-APP-902",
            business_name="Redstone Retail Plaza LLC",
            sector="Retail CRE",
            requested_amount=1750000,
            dscr=1.48,
            ltv=0.64,
            years_in_business=9.0,
            documentation_complete=1,
            notes="Strong CRE applicant competes with limited branch capacity.",
        ),
        make_application(
            rng,
            "EASTGATE",
            903,
            "SBA",
            application_id="EAS-APP-903",
            business_name="Juniper Dental Lab LLC",
            sector="Healthcare",
            requested_amount=760000,
            dscr=1.14,
            ltv=0.82,
            sba_guaranty_pct=0.85,
            years_in_business=1.1,
            documentation_complete=1,
            notes="Startup SBA request has high guaranty and a documented mentor contract.",
        ),
        make_application(
            rng,
            "SOUTHPORT",
            901,
            "CRE",
            application_id="SOU-APP-901",
            business_name="Southport Medical Plaza LLC",
            sector="Medical Office CRE",
            requested_amount=2200000,
            dscr=1.64,
            ltv=0.61,
            years_in_business=11.0,
            documentation_complete=1,
            notes="Excellent CRE metrics, but branch CRE exposure is above policy limit before approval.",
        ),
        make_application(
            rng,
            "SOUTHPORT",
            902,
            "C&I",
            application_id="SOU-APP-902",
            business_name="Crescent Marine Supply Co",
            sector="Manufacturing",
            requested_amount=920000,
            dscr=1.41,
            ltv=0.70,
            years_in_business=14.0,
            documentation_complete=1,
            notes="Smaller C&I request preserves capacity and diversifies away from CRE.",
        ),
    ]
    applications.extend(overrides)
    return applications


def build_sector_exposures(branches, loans):
    branches_by_id = {b["branch_id"]: b for b in branches}
    exposure_map = {}
    for loan in loans:
        key = (loan["branch_id"], loan["sector"])
        exposure_map[key] = exposure_map.get(key, 0.0) + loan["outstanding_balance"]

    rows = []
    for (branch_id, sector), exposure in sorted(exposure_map.items()):
        branch = branches_by_id[branch_id]
        override = None
        grandfathered = 0
        if branch_id in {"LAKEVIEW", "EASTGATE"} and sector == "Healthcare":
            override = branch["sector_ceiling_pct"] - 0.02
        if branch_id in {"HARBOR", "SOUTHPORT"} and (
            "CRE" in sector or sector in {"Hospitality", "Office", "Retail CRE", "Medical Office CRE"}
        ):
            override = branch["cre_policy_limit_pct"]
        if branch_id == "SOUTHPORT" and sector in {"Retail CRE", "Office"}:
            grandfathered = 1
        if branch_id == "HARBOR" and sector == "Hospitality":
            grandfathered = 1
        rows.append(
            {
                "branch_id": branch_id,
                "sector": sector,
                "current_exposure": money(exposure),
                "grandfathered": grandfathered,
                "limit_pct": ratio(override if override is not None else branch["sector_ceiling_pct"]),
            }
        )
    return rows


def build_metrics(rng, branches, loans):
    loans_by_branch = {}
    for loan in loans:
        loans_by_branch.setdefault(loan["branch_id"], []).append(loan)
    metrics = []
    for branch in branches:
        branch_loans = loans_by_branch.get(branch["branch_id"], [])
        total = sum(loan["outstanding_balance"] for loan in branch_loans)
        nonperforming = sum(
            loan["outstanding_balance"]
            for loan in branch_loans
            if loan["payment_status"] in {"90+ Days Past Due", "Nonaccrual"}
        )
        delinquency_30 = (
            sum(loan["outstanding_balance"] for loan in branch_loans if loan["payment_status"] != "Current") / total
            if total
            else 0.0
        )
        allowance = total * rng.uniform(0.012, 0.024)
        chargeoffs = total * rng.uniform(0.001, 0.009)
        deposits = branch["total_assets"] * rng.uniform(0.68, 0.88)
        metrics.append(
            {
                "branch_id": branch["branch_id"],
                "quarter": "2025Q1",
                "total_loans_outstanding": money(total),
                "nonperforming_loans": money(nonperforming),
                "delinquency_30_plus_pct": ratio(delinquency_30),
                "allowance_for_loan_losses": money(allowance),
                "net_charge_offs": money(chargeoffs),
                "total_deposits": money(deposits),
            }
        )
        metrics.append(
            {
                "branch_id": branch["branch_id"],
                "quarter": "2024Q4",
                "total_loans_outstanding": money(total * rng.uniform(0.94, 1.02)),
                "nonperforming_loans": money(nonperforming * rng.uniform(0.82, 1.08)),
                "delinquency_30_plus_pct": ratio(max(0.0, delinquency_30 + rng.uniform(-0.008, 0.006))),
                "allowance_for_loan_losses": money(allowance * rng.uniform(0.94, 1.04)),
                "net_charge_offs": money(chargeoffs * rng.uniform(0.80, 1.10)),
                "total_deposits": money(deposits * rng.uniform(0.96, 1.03)),
            }
        )
    return metrics


def write_json(path: Path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="ascii")


def create_schema(conn: sqlite3.Connection):
    conn.executescript(
        """
        drop table if exists branches;
        drop table if exists branch_metrics;
        drop table if exists loans;
        drop table if exists sector_exposures;
        drop table if exists applications;
        drop table if exists policies;
        drop table if exists fdic_benchmarks;
        drop table if exists ncua_benchmarks;
        drop table if exists credit_union_segments;

        create table branches (
            branch_id text primary key,
            branch_name text not null,
            institution_type text not null,
            total_assets real not null,
            lending_capacity_q1 real not null,
            sector_ceiling_pct real not null,
            cre_policy_limit_pct real not null,
            fdic_benchmark_set text not null,
            state_code text
        );

        create table branch_metrics (
            branch_id text not null,
            quarter text not null,
            total_loans_outstanding real not null,
            nonperforming_loans real not null,
            delinquency_30_plus_pct real not null,
            allowance_for_loan_losses real not null,
            net_charge_offs real not null,
            total_deposits real not null
        );

        create table loans (
            loan_id text primary key,
            branch_id text not null,
            borrower_name text not null,
            loan_type text not null,
            sector text not null,
            outstanding_balance real not null,
            current_rating integer not null,
            payment_status text not null,
            days_past_due integer not null,
            dscr real,
            ltv real,
            collateral_value real,
            fico integer,
            liquidity_months real,
            debt_to_asset real,
            interest_rate real not null,
            annual_debt_service real not null,
            guarantor_strength text not null,
            annual_review_date text not null,
            notes text not null
        );

        create table sector_exposures (
            branch_id text not null,
            sector text not null,
            current_exposure real not null,
            grandfathered integer not null,
            limit_pct real not null
        );

        create table applications (
            application_id text primary key,
            branch_id text not null,
            applicant_name text not null,
            business_name text,
            loan_type text not null,
            sector text not null,
            requested_amount real not null,
            purpose text not null,
            proposed_rate real not null,
            term_months integer not null,
            collateral_value real,
            ltv real,
            dscr real,
            fico integer,
            years_in_business real,
            annual_revenue real,
            net_income real,
            total_debt real,
            total_assets real,
            dti real,
            sba_guaranty_pct real,
            bankruptcy_months_ago integer,
            prior_delinquencies_12m integer not null,
            existing_relationship_years real,
            co_guarantor_strength text,
            relationship_deposit_balance real,
            documentation_complete integer not null,
            notes text not null
        );

        create table policies (
            policy_version text primary key,
            policy_json text not null
        );

        create table fdic_benchmarks (
            benchmark_version text primary key,
            total_loans_noncurrent_pct real not null,
            total_real_estate_noncurrent_pct real not null,
            total_real_estate_30_89_pct real not null,
            construction_development_noncurrent_pct real not null,
            construction_development_30_89_pct real not null
        );

        create table ncua_benchmarks (
            state_code text primary key,
            delinquency_bps integer not null,
            loan_to_share_pct integer not null,
            roaa_bps integer not null,
            positive_net_income_pct integer not null
        );

        create table credit_union_segments (
            segment_id text primary key,
            segment_json text not null
        );
        """
    )


def insert_rows(conn: sqlite3.Connection, table: str, rows: list[dict]):
    if not rows:
        return
    columns = list(rows[0].keys())
    placeholders = ", ".join(["?"] * len(columns))
    sql = f"insert into {table} ({', '.join(columns)}) values ({placeholders})"
    conn.executemany(sql, [[row.get(column) for column in columns] for row in rows])


def table_count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"select count(*) from {table}").fetchone()[0]


def main():
    rng = random.Random(SEED)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    loans = build_loans(rng)
    applications = build_applications(rng)
    sector_exposures = build_sector_exposures(BRANCHES, loans)
    metrics = build_metrics(rng, BRANCHES, loans)

    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)
    insert_rows(conn, "branches", BRANCHES)
    insert_rows(conn, "branch_metrics", metrics)
    insert_rows(conn, "loans", loans)
    insert_rows(conn, "sector_exposures", sector_exposures)
    insert_rows(conn, "applications", applications)
    conn.execute(
        "insert into policies (policy_version, policy_json) values (?, ?)",
        (POLICY_VERSION, json.dumps(POLICIES, sort_keys=True)),
    )
    insert_rows(conn, "fdic_benchmarks", [FDIC_Q4_2024])
    insert_rows(conn, "ncua_benchmarks", NCUA_ROWS)
    for segment in CREDIT_UNION_SEGMENTS:
        conn.execute(
            "insert into credit_union_segments (segment_id, segment_json) values (?, ?)",
            (segment["segment_id"], json.dumps(segment, sort_keys=True)),
        )
    conn.commit()

    write_json(DATA_DIR / "branches.json", BRANCHES)
    write_json(DATA_DIR / "policies.json", POLICIES)
    write_json(DATA_DIR / "fdic_q4_2024.json", FDIC_Q4_2024)
    write_json(DATA_DIR / "credit_union_segments.json", CREDIT_UNION_SEGMENTS)
    with (DATA_DIR / "ncua_q1_2025.csv").open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["state_code", "delinquency_bps", "loan_to_share_pct", "roaa_bps", "positive_net_income_pct"],
        )
        writer.writeheader()
        writer.writerows(NCUA_ROWS)

    generated_files = [
        "data/credit_office.db",
        "data/public_manifest.json",
        "data/branches.json",
        "data/policies.json",
        "data/fdic_q4_2024.json",
        "data/ncua_q1_2025.csv",
        "data/credit_union_segments.json",
    ]
    counts = {
        table: table_count(conn, table)
        for table in [
            "branches",
            "branch_metrics",
            "loans",
            "sector_exposures",
            "applications",
            "policies",
            "fdic_benchmarks",
            "ncua_benchmarks",
            "credit_union_segments",
        ]
    }
    manifest = {
        "generated_seed": SEED,
        "generated_at": "2025-03-31T00:00:00Z",
        "generated_files": generated_files,
        "public_api_endpoints": ENDPOINTS,
        "record_counts": counts,
        "policy_version": POLICY_VERSION,
        "benchmark_versions": {
            "fdic": FDIC_VERSION,
            "ncua": NCUA_VERSION,
        },
    }
    write_json(DATA_DIR / "public_manifest.json", manifest)
    conn.close()
    print(json.dumps({"status": "generated", "seed": SEED, "record_counts": counts}, sort_keys=True))


if __name__ == "__main__":
    main()
