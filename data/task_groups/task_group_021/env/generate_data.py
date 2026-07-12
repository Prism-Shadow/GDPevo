#!/usr/bin/env python3
"""Generate deterministic AsterOps environment data."""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path


SEED = 21013
GENERATED_AT = "2026-07-07T00:00:00Z"
VERSION = "asterops-env-v1"
BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
DOWNLOADS_DIR = DATA_DIR / "downloads"


FIELDNAMES = {
    "crm_contact_rows": [
        "row_id",
        "batch_id",
        "person_key",
        "source_system",
        "source_updated_at",
        "full_name",
        "email",
        "phone",
        "city",
        "company",
        "contact_status",
        "consent_status",
        "quality_notes",
    ],
    "crm_campaign_members": [
        "member_id",
        "campaign_id",
        "person_key",
        "raw_segment",
        "member_status",
        "score",
        "source_file",
    ],
    "fleet_vehicles": [
        "vehicle_id",
        "region",
        "vehicle_type",
        "expected_fuel",
        "active",
        "exemption_code",
    ],
    "fleet_purchases": [
        "purchase_id",
        "transaction_key",
        "vehicle_id",
        "region",
        "purchase_date",
        "vendor",
        "product_description",
        "gallons",
        "amount_usd",
        "record_status",
        "amends_purchase_id",
        "source_system",
    ],
    "reference_fuel_aliases": ["alias", "canonical_fuel", "priority", "notes"],
    "facilities_charges": [
        "charge_id",
        "business_key",
        "scope",
        "charge_date",
        "vendor",
        "raw_category",
        "description",
        "amount",
        "currency",
        "record_status",
        "amends_charge_id",
        "location",
    ],
    "reference_category_aliases": ["alias", "canonical_category", "priority"],
    "logistics_cost_events": [
        "event_id",
        "business_key",
        "wave_id",
        "event_type",
        "lane",
        "event_date",
        "amount",
        "currency",
        "quantity",
        "unit",
        "record_status",
        "amends_event_id",
        "source_system",
        "quality_notes",
    ],
    "reference_quality_rules": ["rule_id", "domain", "summary", "controlled_values"],
}

DOWNLOADS = {
    "crm_contact_rows_export.csv": "crm_contact_rows",
    "campaign_members_export.csv": "crm_campaign_members",
    "fleet_purchases_export.csv": "fleet_purchases",
    "fleet_vehicles_export.csv": "fleet_vehicles",
    "facilities_charges_export.csv": "facilities_charges",
    "logistics_cost_events_export.csv": "logistics_cost_events",
    "fuel_aliases.csv": "reference_fuel_aliases",
    "category_aliases.csv": "reference_category_aliases",
}


def add_contact(rows, row_id, batch_id, person_key, source_system, updated, name, email, phone, city, company, status, consent, notes):
    rows.append(
        {
            "row_id": row_id,
            "batch_id": batch_id,
            "person_key": person_key,
            "source_system": source_system,
            "source_updated_at": updated,
            "full_name": name,
            "email": email,
            "phone": phone,
            "city": city,
            "company": company,
            "contact_status": status,
            "consent_status": consent,
            "quality_notes": notes,
        }
    )


def curated_contacts():
    rows = []
    specs = [
        ("spring_summit_2026", "SPR", "Austin"),
        ("expo_followup_2026", "EXP", "Denver"),
        ("partner_onboarding_wave2", "POW", "Raleigh"),
        ("renewal_webinar_q3", "REN", "Chicago"),
    ]
    source_rows = [
        ("crm_verified", "2026-06-11", "Opted Lead", "Opted@example.COM ", "(312) 555-0144", "active", "opted_in", ["case_email"]),
        ("event_import", "2026-06-18", "Opted Lead", " opted+event@example.com", "312.555.0144", "active", "unknown", ["duplicate_person"]),
        ("partner_roster", "2026-06-15", "No Phone", "", "", "active", "opted_in", ["missing_channel"]),
        ("steward_override", "2026-06-20", "Suppressed Buyer", "buyer@example.com", "3125550188", "do_not_contact", "opted_in", ["suppressed"]),
        ("crm_verified", "2026-06-09", "Revoked Contact", "revoked@example.com", "(312)555-0199", "active", "revoked", ["revoked_consent"]),
        ("partner_roster", "2026-06-21", "Fresh Roster", "fresh@example.com", "312 555 0155", "active", "unknown", ["fresh_source"]),
        ("event_import", "2026-06-22", "Case Clash", "CASE@EXAMPLE.COM", "", "inactive", "unknown", ["stale_status"]),
        ("steward_override", "2026-06-23", "Case Clash", "case@example.com", "+1-312-555-0166", "active", "opted_in", ["steward_corrected"]),
    ]
    idx = 1
    for batch, prefix, city in specs:
        for offset, src in enumerate(source_rows, start=1):
            person_key = f"P_{prefix}_{(offset + 1) // 2:03d}" if offset in (1, 2, 7, 8) else f"P_{prefix}_{offset:03d}"
            add_contact(
                rows,
                f"CR_{prefix}_{idx:03d}",
                batch,
                person_key,
                src[0],
                src[1],
                f"{src[2]} {prefix}",
                src[3],
                src[4],
                city,
                f"{prefix} Analytics",
                src[5],
                src[6],
                src[7],
            )
            idx += 1
    return rows


def partner_onboarding_wave2_extra_contacts():
    rows = []
    add_contact(
        rows,
        "CR_POW_025",
        "partner_onboarding_wave2",
        "P_POW_007",
        "crm_verified",
        "2026-06-24",
        "Kelly Nimbus POW",
        "kelly@nimbusfreight.co",
        "+1 919 555 0177",
        "Raleigh",
        "Nimbus Freight Partners",
        "active",
        "opted_in",
        ["new_partner_domain"],
    )
    add_contact(
        rows,
        "CR_POW_026",
        "partner_onboarding_wave2",
        "P_POW_008",
        "partner_roster",
        "2026-06-24",
        "Jordan Manual POW",
        "",
        "",
        "Raleigh",
        "POW Analytics",
        "active",
        "opted_in",
        ["missing_channel"],
    )
    add_contact(
        rows,
        "CR_POW_027",
        "partner_onboarding_wave2",
        "P_POW_009",
        "steward_override",
        "2026-06-25",
        "Morgan Suppressed POW",
        "morgan@harborchainlogistics.com",
        "919-555-0189",
        "Raleigh",
        "Harbor Chain Logistics",
        "do_not_contact",
        "revoked",
        ["suppressed", "revoked_consent"],
    )
    add_contact(
        rows,
        "CR_POW_028",
        "partner_onboarding_wave2",
        "P_POW_007",
        "event_import",
        "2026-06-19",
        "Kelly Nimbus POW",
        "kelly+summit@nimbusfreight.co",
        "",
        "Raleigh",
        "Nimbus Freight Partners",
        "inactive",
        "unknown",
        ["duplicate_person", "stale_status", "missing_channel"],
    )
    return rows


def background_contacts(rng, count=128):
    rows = []
    batches = ["vendor_newsletter", "field_ops_roster", "customer_roundtable", "legacy_sync", "support_migration"]
    sources = ["crm_verified", "event_import", "partner_roster", "steward_override"]
    statuses = ["active", "inactive", "do_not_contact"]
    consents = ["opted_in", "unknown", "revoked"]
    cities = ["Seattle", "Phoenix", "Boston", "Atlanta", "Portland", "Miami"]
    for i in range(count):
        batch = rng.choice(batches)
        person = f"P_BG_{i // 2:04d}" if i % 17 in (0, 1) else f"P_BG_{i:04d}"
        email = f"user{i}@example{rng.randint(1, 9)}.com"
        if i % 23 == 0:
            email = ""
        elif i % 11 == 0:
            email = f" USER{i}@Example{rng.randint(1, 9)}.COM "
        phone = f"({rng.randint(200, 999)}) 555-{rng.randint(1000, 9999)}"
        if i % 29 == 0:
            phone = ""
        notes = []
        if i % 17 in (0, 1):
            notes.append("duplicate_person")
        if not email or not phone:
            notes.append("missing_channel")
        add_contact(
            rows,
            f"CR_BG_{i:04d}",
            batch,
            person,
            rng.choice(sources),
            f"2026-{rng.randint(1, 9):02d}-{rng.randint(1, 28):02d}",
            f"Background Contact {i}",
            email,
            phone,
            rng.choice(cities),
            f"Company {rng.randint(1, 60)}",
            rng.choices(statuses, weights=[82, 13, 5])[0],
            rng.choices(consents, weights=[70, 22, 8])[0],
            notes,
        )
    return rows


def campaign_members(rng):
    rows = [
        {
            "member_id": "CM_REN_001",
            "campaign_id": "renewal_webinar_q3",
            "person_key": "P_REN_001",
            "raw_segment": "Renewal - Enterprise",
            "member_status": "attended",
            "score": 94,
            "source_file": "renewal_q3_upload_a.csv",
        },
        {
            "member_id": "CM_REN_002",
            "campaign_id": "renewal_webinar_q3",
            "person_key": "P_REN_004",
            "raw_segment": " renewal / strategic ",
            "member_status": "registered",
            "score": 81,
            "source_file": "renewal_q3_upload_a.csv",
        },
        {
            "member_id": "CM_REN_003",
            "campaign_id": "renewal_webinar_q3",
            "person_key": "P_REN_005",
            "raw_segment": "SMB churn risk",
            "member_status": "bounced",
            "score": 42,
            "source_file": "renewal_q3_bounces.csv",
        },
        {
            "member_id": "CM_REN_004",
            "campaign_id": "renewal_webinar_q3",
            "person_key": "P_REN_006",
            "raw_segment": "Partner",
            "member_status": "unsubscribed",
            "score": 37,
            "source_file": "renewal_q3_suppression.csv",
        },
        {
            "member_id": "CM_REN_005",
            "campaign_id": "renewal_webinar_q3",
            "person_key": "P_REN_004",
            "raw_segment": "Enterprise Renewal Duplicate",
            "member_status": "attended",
            "score": 86,
            "source_file": "renewal_q3_upload_b.csv",
        },
    ]
    campaigns = ["field_demo_may", "maintenance_roundtable", "fuel_policy_briefing", "carrier_claims_forum"]
    statuses = ["registered", "attended", "no_show", "bounced", "unsubscribed"]
    for i in range(86):
        rows.append(
            {
                "member_id": f"CM_BG_{i:04d}",
                "campaign_id": rng.choice(campaigns),
                "person_key": f"P_BG_{rng.randint(0, 127):04d}",
                "raw_segment": rng.choice(["Enterprise", "SMB", "Partner ", " renewal", "Ops-lead"]),
                "member_status": rng.choices(statuses, weights=[35, 32, 18, 9, 6])[0],
                "score": rng.randint(1, 100),
                "source_file": f"campaign_export_{rng.randint(1, 5)}.csv",
            }
        )
    return rows


def vehicles(rng):
    rows = []
    target = [
        ("N-100", "north", "box_truck", "diesel", True, "none"),
        ("N-101", "north", "sedan", "premium_unleaded", True, "none"),
        ("N-102", "north", "service_van", "electric", True, "none"),
        ("N-103", "north", "pickup", "diesel", True, "field_generator"),
        ("S-200", "south", "box_truck", "diesel", True, "none"),
        ("S-201", "south", "sedan", "unleaded", True, "none"),
        ("S-202", "south", "service_van", "electric", True, "none"),
        ("S-203", "south", "rental_van", "hybrid", True, "rental_substitution"),
        ("W-300", "west", "pickup", "diesel", True, "none"),
        ("W-301", "west", "sedan", "premium_unleaded", True, "none"),
    ]
    for vehicle_id, region, vtype, fuel, active, exemption in target:
        rows.append(
            {
                "vehicle_id": vehicle_id,
                "region": region,
                "vehicle_type": vtype,
                "expected_fuel": fuel,
                "active": active,
                "exemption_code": exemption,
            }
        )
    regions = ["north", "south", "west", "east"]
    types = ["box_truck", "sedan", "service_van", "pickup", "rental_van"]
    fuels = ["diesel", "unleaded", "premium_unleaded", "electric", "hybrid"]
    exemptions = ["none", "none", "none", "rental_substitution", "field_generator"]
    for i in range(64):
        region = rng.choice(regions)
        rows.append(
            {
                "vehicle_id": f"{region[0].upper()}-{400 + i}",
                "region": region,
                "vehicle_type": rng.choice(types),
                "expected_fuel": rng.choice(fuels),
                "active": rng.random() > 0.08,
                "exemption_code": rng.choice(exemptions),
            }
        )
    return rows


def fuel_aliases():
    return [
        {"alias": "renewable diesel b20", "canonical_fuel": "diesel", "priority": 98, "notes": "specific blend"},
        {"alias": "renewable diesel", "canonical_fuel": "diesel", "priority": 95, "notes": "specific diesel"},
        {"alias": "b20", "canonical_fuel": "diesel", "priority": 93, "notes": "diesel blend"},
        {"alias": "diesel", "canonical_fuel": "diesel", "priority": 90, "notes": "generic diesel"},
        {"alias": "premium unleaded", "canonical_fuel": "premium_unleaded", "priority": 92, "notes": "specific gasoline"},
        {"alias": "super unleaded", "canonical_fuel": "premium_unleaded", "priority": 91, "notes": "specific gasoline"},
        {"alias": "regular unleaded", "canonical_fuel": "unleaded", "priority": 80, "notes": "regular gasoline"},
        {"alias": "unleaded regular", "canonical_fuel": "unleaded", "priority": 80, "notes": "regular gasoline"},
        {"alias": "unleaded", "canonical_fuel": "unleaded", "priority": 50, "notes": "generic gasoline"},
        {"alias": "ev fast charge", "canonical_fuel": "electric", "priority": 97, "notes": "charging"},
        {"alias": "ev charge", "canonical_fuel": "electric", "priority": 95, "notes": "charging"},
        {"alias": "electric", "canonical_fuel": "electric", "priority": 80, "notes": "charging"},
        {"alias": "hybrid service fuel", "canonical_fuel": "hybrid", "priority": 88, "notes": "hybrid fleet"},
        {"alias": "fuel service", "canonical_fuel": "unknown", "priority": 10, "notes": "ambiguous"},
        {"alias": "misc fuel", "canonical_fuel": "unknown", "priority": 5, "notes": "ambiguous"},
    ]


def purchases(rng, vehicle_rows):
    rows = [
        {
            "purchase_id": "FP_N_001",
            "transaction_key": "TXN-N-001",
            "vehicle_id": "N-100",
            "region": "north",
            "purchase_date": "2026-07-03",
            "vendor": "FleetCard",
            "product_description": "Renewable Diesel B20",
            "gallons": 42.3,
            "amount_usd": 174.35,
            "record_status": "posted",
            "amends_purchase_id": "",
            "source_system": "vendor_card",
        },
        {
            "purchase_id": "FP_N_002",
            "transaction_key": "TXN-N-002",
            "vehicle_id": "N-101",
            "region": "north",
            "purchase_date": "2026-07-04",
            "vendor": "FuelHub",
            "product_description": "Unleaded regular",
            "gallons": 15.1,
            "amount_usd": 58.14,
            "record_status": "posted",
            "amends_purchase_id": "",
            "source_system": "vendor_card",
        },
        {
            "purchase_id": "FP_N_003",
            "transaction_key": "TXN-N-003",
            "vehicle_id": "N-101",
            "region": "north",
            "purchase_date": "2026-07-07",
            "vendor": "FuelHub",
            "product_description": "Premium unleaded",
            "gallons": 13.8,
            "amount_usd": 62.83,
            "record_status": "posted",
            "amends_purchase_id": "",
            "source_system": "vendor_card",
        },
        {
            "purchase_id": "FP_N_004",
            "transaction_key": "TXN-N-004",
            "vehicle_id": "N-102",
            "region": "north",
            "purchase_date": "2026-07-09",
            "vendor": "ChargeNet",
            "product_description": "EV fast charge",
            "gallons": 0,
            "amount_usd": 31.22,
            "record_status": "posted",
            "amends_purchase_id": "",
            "source_system": "vendor_card",
        },
        {
            "purchase_id": "FP_N_005",
            "transaction_key": "TXN-N-005",
            "vehicle_id": "N-103",
            "region": "north",
            "purchase_date": "2026-07-12",
            "vendor": "FleetCard",
            "product_description": "Diesel",
            "gallons": 18.5,
            "amount_usd": 72.8,
            "record_status": "void",
            "amends_purchase_id": "",
            "source_system": "vendor_card",
        },
        {
            "purchase_id": "FP_N_006",
            "transaction_key": "TXN-N-005",
            "vehicle_id": "N-103",
            "region": "north",
            "purchase_date": "2026-07-12",
            "vendor": "FleetCard",
            "product_description": "Diesel generator fill",
            "gallons": 19.0,
            "amount_usd": 75.1,
            "record_status": "amended",
            "amends_purchase_id": "FP_N_005",
            "source_system": "vendor_amendment",
        },
        {
            "purchase_id": "FP_S_001",
            "transaction_key": "TXN-S-001",
            "vehicle_id": "S-200",
            "region": "south",
            "purchase_date": "2026-08-02",
            "vendor": "FuelHub",
            "product_description": "Diesel",
            "gallons": 38.9,
            "amount_usd": 151.7,
            "record_status": "posted",
            "amends_purchase_id": "",
            "source_system": "vendor_card",
        },
        {
            "purchase_id": "FP_S_002",
            "transaction_key": "TXN-S-002",
            "vehicle_id": "S-201",
            "region": "south",
            "purchase_date": "2026-08-03",
            "vendor": "QuickFuel",
            "product_description": "Premium unleaded",
            "gallons": 14.2,
            "amount_usd": 66.9,
            "record_status": "posted",
            "amends_purchase_id": "",
            "source_system": "vendor_card",
        },
        {
            "purchase_id": "FP_S_003",
            "transaction_key": "TXN-S-003",
            "vehicle_id": "S-202",
            "region": "south",
            "purchase_date": "2026-08-05",
            "vendor": "ChargeNet",
            "product_description": "EV charge",
            "gallons": 0,
            "amount_usd": 27.3,
            "record_status": "posted",
            "amends_purchase_id": "",
            "source_system": "vendor_card",
        },
        {
            "purchase_id": "FP_S_004",
            "transaction_key": "TXN-S-004",
            "vehicle_id": "S-203",
            "region": "south",
            "purchase_date": "2026-08-08",
            "vendor": "FleetCard",
            "product_description": "Hybrid service fuel",
            "gallons": 9.3,
            "amount_usd": 39.4,
            "record_status": "posted",
            "amends_purchase_id": "",
            "source_system": "manual_adjustment",
        },
        {
            "purchase_id": "FP_S_005",
            "transaction_key": "TXN-S-005",
            "vehicle_id": "S-201",
            "region": "south",
            "purchase_date": "2026-08-09",
            "vendor": "QuickFuel",
            "product_description": "Regular unleaded",
            "gallons": 12.0,
            "amount_usd": 45.12,
            "record_status": "void",
            "amends_purchase_id": "",
            "source_system": "vendor_card",
        },
        {
            "purchase_id": "FP_S_006",
            "transaction_key": "TXN-S-005",
            "vehicle_id": "S-201",
            "region": "south",
            "purchase_date": "2026-08-09",
            "vendor": "QuickFuel",
            "product_description": "Premium unleaded corrected",
            "gallons": 12.5,
            "amount_usd": 51.0,
            "record_status": "amended",
            "amends_purchase_id": "FP_S_005",
            "source_system": "vendor_amendment",
        },
        {
            "purchase_id": "FP_S_007",
            "transaction_key": "TXN-S-007",
            "vehicle_id": "S-200",
            "region": "south",
            "purchase_date": "2026-08-11",
            "vendor": "FleetCard",
            "product_description": "Renewable Diesel B20",
            "gallons": 20.1,
            "amount_usd": 84.42,
            "record_status": "posted",
            "amends_purchase_id": "",
            "source_system": "vendor_card",
        },
        {
            "purchase_id": "FP_S_008",
            "transaction_key": "TXN-S-008",
            "vehicle_id": "S-446",
            "region": "south",
            "purchase_date": "2026-08-13",
            "vendor": "FuelHub",
            "product_description": "Super unleaded",
            "gallons": 16.4,
            "amount_usd": 70.52,
            "record_status": "posted",
            "amends_purchase_id": "",
            "source_system": "vendor_card",
        },
        {
            "purchase_id": "FP_S_009",
            "transaction_key": "TXN-S-009",
            "vehicle_id": "S-428",
            "region": "south",
            "purchase_date": "2026-08-14",
            "vendor": "FleetCard",
            "product_description": "CNG pilot fuel",
            "gallons": 7.7,
            "amount_usd": 24.64,
            "record_status": "posted",
            "amends_purchase_id": "",
            "source_system": "manual_adjustment",
        },
        {
            "purchase_id": "FP_S_010",
            "transaction_key": "TXN-S-010",
            "vehicle_id": "S-423",
            "region": "south",
            "purchase_date": "2026-08-18",
            "vendor": "QuickFuel",
            "product_description": "misc fuel",
            "gallons": 18.25,
            "amount_usd": 59.31,
            "record_status": "posted",
            "amends_purchase_id": "",
            "source_system": "vendor_card",
        },
        {
            "purchase_id": "FP_S_011",
            "transaction_key": "TXN-S-011",
            "vehicle_id": "S-407",
            "region": "south",
            "purchase_date": "2026-08-19",
            "vendor": "QuickFuel",
            "product_description": "Premium unleaded",
            "gallons": 11.1,
            "amount_usd": 49.06,
            "record_status": "posted",
            "amends_purchase_id": "",
            "source_system": "vendor_card",
        },
    ]
    products = ["Diesel", "Regular unleaded", "Unleaded regular", "Premium unleaded", "Super unleaded", "EV charge", "Fuel service", "Renewable Diesel", "misc fuel"]
    statuses = ["posted", "posted", "posted", "void"]
    vehicle_ids = [v["vehicle_id"] for v in vehicle_rows]
    region_by_vehicle = {v["vehicle_id"]: v["region"] for v in vehicle_rows}
    for i in range(218):
        vid = rng.choice(vehicle_ids)
        purchase_id = f"FP_BG_{i:04d}"
        rows.append(
            {
                "purchase_id": purchase_id,
                "transaction_key": f"TXN-BG-{i // 2:04d}" if i % 31 in (0, 1) else f"TXN-BG-{i:04d}",
                "vehicle_id": vid,
                "region": region_by_vehicle[vid],
                "purchase_date": f"2026-{rng.randint(1, 9):02d}-{rng.randint(1, 28):02d}",
                "vendor": rng.choice(["FleetCard", "FuelHub", "QuickFuel", "ChargeNet"]),
                "product_description": rng.choice(products),
                "gallons": round(rng.uniform(0, 55), 2),
                "amount_usd": round(rng.uniform(8, 240), 2),
                "record_status": rng.choice(statuses),
                "amends_purchase_id": "",
                "source_system": rng.choice(["vendor_card", "manual_adjustment"]),
            }
        )
        if i in (40, 113, 177):
            rows[-1]["record_status"] = "amended"
            rows[-1]["amends_purchase_id"] = f"FP_BG_{i - 1:04d}"
            rows[-1]["source_system"] = "vendor_amendment"
    return rows


def category_aliases():
    return [
        {"alias": "fuel", "canonical_category": "fuel", "priority": 90},
        {"alias": "diesel fuel", "canonical_category": "fuel", "priority": 95},
        {"alias": "preventive maintenance", "canonical_category": "maintenance", "priority": 95},
        {"alias": "repair", "canonical_category": "maintenance", "priority": 85},
        {"alias": "freight", "canonical_category": "freight", "priority": 90},
        {"alias": "linehaul", "canonical_category": "freight", "priority": 88},
        {"alias": "accessorial", "canonical_category": "accessorial", "priority": 92},
        {"alias": "detention", "canonical_category": "accessorial", "priority": 90},
        {"alias": "claim", "canonical_category": "claim", "priority": 90},
        {"alias": "damage claim", "canonical_category": "claim", "priority": 95},
        {"alias": "tax", "canonical_category": "tax_fee", "priority": 80},
        {"alias": "regulatory fee", "canonical_category": "tax_fee", "priority": 88},
        {"alias": "misc", "canonical_category": "unknown", "priority": 10},
    ]


def facilities_charges(rng):
    rows = [
        {
            "charge_id": "FC_W_001",
            "business_key": "WEST-AUG-001",
            "scope": "facilities_west",
            "charge_date": "2026-08-04",
            "vendor": "Bay Maintenance",
            "raw_category": "Preventive maintenance",
            "description": "Dock door PM",
            "amount": 1280.0,
            "currency": "USD",
            "record_status": "posted",
            "amends_charge_id": "",
            "location": "Oakland DC",
        },
        {
            "charge_id": "FC_W_002",
            "business_key": "WEST-AUG-002",
            "scope": "facilities_west",
            "charge_date": "2026-08-06",
            "vendor": "West Fuel",
            "raw_category": "Diesel fuel",
            "description": "Generator tank refill",
            "amount": 740.5,
            "currency": "USD",
            "record_status": "posted",
            "amends_charge_id": "",
            "location": "Reno Hub",
        },
        {
            "charge_id": "FC_W_003",
            "business_key": "WEST-AUG-003",
            "scope": "facilities_west",
            "charge_date": "2026-08-08",
            "vendor": "Bay Maintenance",
            "raw_category": "Repair",
            "description": "Void duplicate work order",
            "amount": 415.0,
            "currency": "USD",
            "record_status": "void",
            "amends_charge_id": "",
            "location": "Oakland DC",
        },
        {
            "charge_id": "FC_W_004",
            "business_key": "WEST-AUG-003",
            "scope": "facilities_west",
            "charge_date": "2026-08-09",
            "vendor": "Bay Maintenance",
            "raw_category": "Repair",
            "description": "Corrected conveyor work order",
            "amount": 455.0,
            "currency": "USD",
            "record_status": "amended",
            "amends_charge_id": "FC_W_003",
            "location": "Oakland DC",
        },
        {
            "charge_id": "FC_W_005",
            "business_key": "WEST-AUG-004",
            "scope": "facilities_west",
            "charge_date": "2026-08-10",
            "vendor": "Port Freight",
            "raw_category": "Accessorial",
            "description": "Detention at facility gate",
            "amount": 310.25,
            "currency": "USD",
            "record_status": "posted",
            "amends_charge_id": "",
            "location": "Long Beach Crossdock",
        },
    ]
    scopes = ["facilities_west", "facilities_east", "facilities_north", "partner_onboarding"]
    raw_categories = ["Fuel", "Preventive maintenance", "Repair", "Freight", "Accessorial", "Tax", "misc"]
    for i in range(164):
        rows.append(
            {
                "charge_id": f"FC_BG_{i:04d}",
                "business_key": f"FAC-{i // 2:04d}" if i % 43 in (0, 1) else f"FAC-{i:04d}",
                "scope": rng.choice(scopes),
                "charge_date": f"2026-{rng.randint(1, 9):02d}-{rng.randint(1, 28):02d}",
                "vendor": rng.choice(["Bay Maintenance", "Port Freight", "GridWorks", "North Repair", "TaxDesk"]),
                "raw_category": rng.choice(raw_categories),
                "description": rng.choice(["monthly service", "dock repair", "fuel surcharge", "gate detention", "regulatory fee"]),
                "amount": round(rng.uniform(20, 5000), 2),
                "currency": "USD",
                "record_status": rng.choices(["posted", "void"], weights=[91, 9])[0],
                "amends_charge_id": "",
                "location": rng.choice(["Oakland DC", "Reno Hub", "Atlanta DC", "Albany Depot"]),
            }
        )
        if i in (52, 119):
            rows[-1]["record_status"] = "amended"
            rows[-1]["amends_charge_id"] = f"FC_BG_{i - 1:04d}"
    return rows


def logistics_events(rng):
    rows = [
        {
            "event_id": "LC_SEA_001",
            "business_key": "SEA-1001",
            "wave_id": "SEA_Q3_2026",
            "event_type": "freight",
            "lane": "Shanghai-Los Angeles",
            "event_date": "2026-07-12",
            "amount": 8400.0,
            "currency": "USD",
            "quantity": 18000,
            "unit": "kg",
            "record_status": "posted",
            "amends_event_id": "",
            "source_system": "carrier_invoice",
            "quality_notes": [],
        },
        {
            "event_id": "LC_SEA_002",
            "business_key": "SEA-1002",
            "wave_id": "SEA_Q3_2026",
            "event_type": "accessorial",
            "lane": "Shenzhen-Oakland",
            "event_date": "2026-07-15",
            "amount": 725.0,
            "currency": "USD",
            "quantity": 1,
            "unit": "shipment",
            "record_status": "posted",
            "amends_event_id": "",
            "source_system": "carrier_invoice",
            "quality_notes": ["detention"],
        },
        {
            "event_id": "LC_SEA_003",
            "business_key": "SEA-1003",
            "wave_id": "SEA_Q3_2026",
            "event_type": "freight",
            "lane": "Ningbo-Seattle",
            "event_date": "2026-08-02",
            "amount": -100.0,
            "currency": "USD",
            "quantity": 8000,
            "unit": "kg",
            "record_status": "posted",
            "amends_event_id": "",
            "source_system": "manual_adjustment",
            "quality_notes": ["invalid_negative_amount"],
        },
        {
            "event_id": "LC_AIR_001",
            "business_key": "AIR-2001",
            "wave_id": "AIR_Q4_2026",
            "event_type": "freight",
            "lane": "Frankfurt-Atlanta",
            "event_date": "2026-10-03",
            "amount": 6200.0,
            "currency": "EUR",
            "quantity": 4300,
            "unit": "kg",
            "record_status": "posted",
            "amends_event_id": "",
            "source_system": "carrier_invoice",
            "quality_notes": [],
        },
        {
            "event_id": "LC_AIR_002",
            "business_key": "AIR-2002",
            "wave_id": "AIR_Q4_2026",
            "event_type": "accessorial",
            "lane": "London-Boston",
            "event_date": "2026-10-07",
            "amount": 910.0,
            "currency": "GBP",
            "quantity": 1,
            "unit": "shipment",
            "record_status": "posted",
            "amends_event_id": "",
            "source_system": "carrier_invoice",
            "quality_notes": [],
        },
        {
            "event_id": "LC_AIR_003",
            "business_key": "AIR-2002",
            "wave_id": "AIR_Q4_2026",
            "event_type": "accessorial",
            "lane": "London-Boston",
            "event_date": "2026-10-08",
            "amount": 870.0,
            "currency": "GBP",
            "quantity": 1,
            "unit": "shipment",
            "record_status": "amended",
            "amends_event_id": "LC_AIR_002",
            "source_system": "carrier_amendment",
            "quality_notes": ["amended_amount"],
        },
        {
            "event_id": "LC_CLM_001",
            "business_key": "CLM-3001",
            "wave_id": "CLAIMS_SEP_2026",
            "event_type": "claim",
            "lane": "Toronto-Chicago",
            "event_date": "2026-09-11",
            "amount": 2500.0,
            "currency": "CAD",
            "quantity": 1,
            "unit": "claim",
            "record_status": "posted",
            "amends_event_id": "",
            "source_system": "claims_portal",
            "quality_notes": [],
        },
        {
            "event_id": "LC_CLM_002",
            "business_key": "CLM-3002",
            "wave_id": "CLAIMS_SEP_2026",
            "event_type": "tax_fee",
            "lane": "Montreal-Newark",
            "event_date": "2026-09-13",
            "amount": "",
            "currency": "CAD",
            "quantity": 1,
            "unit": "shipment",
            "record_status": "posted",
            "amends_event_id": "",
            "source_system": "claims_portal",
            "quality_notes": ["missing_amount"],
        },
    ]
    waves = ["SEA_Q3_2026", "AIR_Q4_2026", "CLAIMS_SEP_2026", "ROAD_Q2_2026", "WAREHOUSE_REBILL_2026"]
    event_types = ["freight", "accessorial", "claim", "tax_fee"]
    currencies = ["USD", "EUR", "GBP", "CAD"]
    units = ["kg", "lb", "mile", "shipment", "claim"]
    for i in range(268):
        event_type = rng.choice(event_types)
        amount = round(rng.uniform(25, 9000), 2)
        notes = []
        if i % 67 == 0:
            amount = -round(rng.uniform(10, 250), 2)
            notes.append("invalid_negative_amount")
        elif i % 71 == 0:
            amount = ""
            notes.append("missing_amount")
        unit = rng.choice(units)
        if i % 79 == 0:
            unit = "pallet"
            notes.append("invalid_unit")
        rows.append(
            {
                "event_id": f"LC_BG_{i:04d}",
                "business_key": f"LOG-{i // 2:04d}" if i % 41 in (0, 1) else f"LOG-{i:04d}",
                "wave_id": rng.choice(waves),
                "event_type": event_type,
                "lane": rng.choice(["LA-Dallas", "Seattle-Denver", "Toronto-Chicago", "London-Boston", "Frankfurt-Atlanta"]),
                "event_date": f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
                "amount": amount,
                "currency": rng.choice(currencies),
                "quantity": rng.randint(1, 25000),
                "unit": unit,
                "record_status": rng.choices(["posted", "void"], weights=[92, 8])[0],
                "amends_event_id": "",
                "source_system": rng.choice(["carrier_invoice", "claims_portal", "manual_adjustment"]),
                "quality_notes": notes,
            }
        )
        if i in (66, 144, 221):
            rows[-1]["record_status"] = "amended"
            rows[-1]["amends_event_id"] = f"LC_BG_{i - 1:04d}"
            rows[-1]["source_system"] = "carrier_amendment"
    return rows


def quality_rules():
    return [
        {
            "rule_id": "QR_CRM_ENUMS",
            "domain": "crm",
            "summary": "CRM fields use controlled source, contact, and consent status values.",
            "controlled_values": {
                "source_system": ["crm_verified", "event_import", "partner_roster", "steward_override"],
                "contact_status": ["active", "inactive", "do_not_contact"],
                "consent_status": ["opted_in", "unknown", "revoked"],
            },
        },
        {
            "rule_id": "QR_EFFECTIVE_RECORDS",
            "domain": "records",
            "summary": "Record status values distinguish normal, voided, and amendment source rows.",
            "controlled_values": {"record_status": ["posted", "void", "amended"]},
        },
        {
            "rule_id": "QR_CURRENCY",
            "domain": "logistics",
            "summary": "Use deterministic USD conversion rates for non-USD cost-event amounts.",
            "controlled_values": {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "CAD": 0.74},
        },
        {
            "rule_id": "QR_COST_UNITS",
            "domain": "logistics",
            "summary": "Valid logistics quantity units are controlled by cost event type.",
            "controlled_values": {"unit": ["kg", "lb", "mile", "shipment", "claim"]},
        },
    ]


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            clean = {}
            for field in fieldnames:
                value = row.get(field, "")
                clean[field] = json.dumps(value, sort_keys=True) if isinstance(value, (list, dict)) else value
            writer.writerow(clean)


def fleet_purchases_export_rows(rows):
    stale_rows = []
    omitted_amendments = {"FP_N_006", "FP_S_006"}
    stale_overrides = {
        "FP_N_005": {
            "product_description": "Diesel",
            "gallons": 18.5,
            "amount_usd": 72.8,
            "record_status": "posted",
            "amends_purchase_id": "",
            "source_system": "vendor_card",
        },
        "FP_S_005": {
            "product_description": "Regular unleaded",
            "gallons": 12.0,
            "amount_usd": 45.12,
            "record_status": "posted",
            "amends_purchase_id": "",
            "source_system": "vendor_card",
        },
    }
    csv_only_legacy_rows = {
        "FP_N_005": {
            "purchase_id": "FP_CSV_N_901",
            "transaction_key": "TXN-CSV-N-901",
            "vehicle_id": "N-100",
            "region": "north",
            "purchase_date": "2026-07-18",
            "vendor": "FleetCard",
            "product_description": "Yard tractor diesel",
            "gallons": 11.4,
            "amount_usd": 44.46,
            "record_status": "posted",
            "amends_purchase_id": "",
            "source_system": "legacy_monthly_export",
        },
        "FP_S_005": {
            "purchase_id": "FP_CSV_S_901",
            "transaction_key": "TXN-CSV-S-901",
            "vehicle_id": "S-200",
            "region": "south",
            "purchase_date": "2026-08-16",
            "vendor": "FuelHub",
            "product_description": "Bulk diesel receipt",
            "gallons": 22.6,
            "amount_usd": 91.08,
            "record_status": "posted",
            "amends_purchase_id": "",
            "source_system": "legacy_monthly_export",
        },
    }

    for row in rows:
        purchase_id = row["purchase_id"]
        if purchase_id in omitted_amendments:
            continue
        export_row = dict(row)
        export_row.update(stale_overrides.get(purchase_id, {}))
        stale_rows.append(export_row)
        if purchase_id in csv_only_legacy_rows:
            stale_rows.append(csv_only_legacy_rows[purchase_id])
    return stale_rows


def main():
    rng = random.Random(SEED)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    contacts = curated_contacts()
    contacts.extend(partner_onboarding_wave2_extra_contacts())
    contacts.extend(background_contacts(rng))
    vehicle_rows = vehicles(rng)
    data = {
        "crm_contact_rows": contacts,
        "crm_campaign_members": campaign_members(rng),
        "fleet_vehicles": vehicle_rows,
        "fleet_purchases": purchases(rng, vehicle_rows),
        "reference_fuel_aliases": fuel_aliases(),
        "facilities_charges": facilities_charges(rng),
        "reference_category_aliases": category_aliases(),
        "logistics_cost_events": logistics_events(rng),
        "reference_quality_rules": quality_rules(),
    }

    with (DATA_DIR / "asterops_data.json").open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")

    for filename, key in DOWNLOADS.items():
        rows = fleet_purchases_export_rows(data[key]) if key == "fleet_purchases" else data[key]
        write_csv(DOWNLOADS_DIR / filename, rows, FIELDNAMES[key])

    manifest = {
        "version": VERSION,
        "generated_at": GENERATED_AT,
        "seed": SEED,
        "record_counts": {key: len(value) for key, value in data.items()},
        "files": ["asterops_data.json", "manifest.json"]
        + [f"downloads/{name}" for name in sorted(DOWNLOADS)],
        "target_slices": {
            "crm_batches": [
                "spring_summit_2026",
                "renewal_webinar_q3",
                "expo_followup_2026",
                "partner_onboarding_wave2",
            ],
            "campaigns": ["renewal_webinar_q3"],
            "fleet_periods": [{"region": "north", "period": "2026-07"}, {"region": "south", "period": "2026-08"}],
            "facilities": [{"scope": "facilities_west", "period": "2026-08"}],
            "logistics_waves": ["SEA_Q3_2026", "AIR_Q4_2026", "CLAIMS_SEP_2026"],
        },
        "currency_rates_usd": {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "CAD": 0.74},
    }
    with (DATA_DIR / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    main()
