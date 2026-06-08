#!/usr/bin/env python3
import json
import math
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SEED = 9009


def money(value):
    return round(float(value) + 0.0000001, 2)


def ratio(value):
    return round(float(value) + 0.0000000001, 6)


def write_json(name, data):
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / name).open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def build_finance_data(rng):
    branches = [
        {"branch_id": "BR-001", "branch_name": "Aurora North", "region_id": "REG-NORTH", "region_name": "North"},
        {"branch_id": "BR-002", "branch_name": "Granite Bay", "region_id": "REG-NORTH", "region_name": "North"},
        {"branch_id": "BR-003", "branch_name": "Lakeview", "region_id": "REG-NORTH", "region_name": "North"},
        {"branch_id": "BR-004", "branch_name": "Harbor North", "region_id": "REG-WEST", "region_name": "West"},
        {"branch_id": "BR-005", "branch_name": "Pine Hill", "region_id": "REG-WEST", "region_name": "West"},
        {"branch_id": "BR-006", "branch_name": "Mesa Ridge", "region_id": "REG-WEST", "region_name": "West"},
        {"branch_id": "BR-007", "branch_name": "Riverbend", "region_id": "REG-EAST", "region_name": "East"},
        {"branch_id": "BR-008", "branch_name": "Old Port", "region_id": "REG-EAST", "region_name": "East"},
        {"branch_id": "BR-009", "branch_name": "Beacon South", "region_id": "REG-SOUTH", "region_name": "South"},
        {"branch_id": "BR-010", "branch_name": "Coral Point", "region_id": "REG-SOUTH", "region_name": "South"},
        {"branch_id": "BR-011", "branch_name": "Summit Yard", "region_id": "REG-EAST", "region_name": "East"},
        {"branch_id": "BR-012", "branch_name": "Valley Forge", "region_id": "REG-SOUTH", "region_name": "South"},
    ]

    period_map = []
    for i in range(1, 25):
        fy = 2024 if i <= 12 else 2025
        month = i if i <= 12 else i - 12
        period_map.append(
            {
                "period": f"M{i}",
                "fiscal_year": fy,
                "month_number": month,
                "month_name": [
                    "Jan",
                    "Feb",
                    "Mar",
                    "Apr",
                    "May",
                    "Jun",
                    "Jul",
                    "Aug",
                    "Sep",
                    "Oct",
                    "Nov",
                    "Dec",
                ][month - 1],
            }
        )

    accounts = [
        {
            "account": "product_revenue",
            "display_name": "Product Revenue",
            "category": "revenue",
            "metric_type": "currency",
        },
        {
            "account": "service_revenue",
            "display_name": "Service Revenue",
            "category": "revenue",
            "metric_type": "currency",
        },
        {
            "account": "direct_materials_cogs",
            "display_name": "Direct Materials COGS",
            "category": "cogs",
            "metric_type": "currency",
        },
        {
            "account": "direct_labor_cogs",
            "display_name": "Direct Labor COGS",
            "category": "cogs",
            "metric_type": "currency",
        },
        {"account": "sales_sga", "display_name": "Sales SG&A", "category": "sga", "metric_type": "currency"},
        {"account": "admin_sga", "display_name": "Admin SG&A", "category": "sga", "metric_type": "currency"},
        {"account": "occupancy_sga", "display_name": "Occupancy SG&A", "category": "sga", "metric_type": "currency"},
        {
            "account": "shared_service_allocations",
            "display_name": "Shared Service Allocations",
            "category": "allocations",
            "metric_type": "currency",
        },
        {"account": "orders", "display_name": "Orders", "category": "operating", "metric_type": "count"},
        {"account": "revenue_units", "display_name": "Revenue Units", "category": "operating", "metric_type": "count"},
        {
            "account": "active_customers",
            "display_name": "Active Customers",
            "category": "operating",
            "metric_type": "count",
        },
        {
            "account": "labor_headcount",
            "display_name": "Labor Headcount",
            "category": "operating",
            "metric_type": "count",
        },
        {
            "account": "admin_headcount",
            "display_name": "Admin Headcount",
            "category": "operating",
            "metric_type": "count",
        },
        {"account": "backlog", "display_name": "Backlog", "category": "operating", "metric_type": "count"},
    ]

    region_adj = {"REG-NORTH": 1.03, "REG-WEST": 1.08, "REG-EAST": 0.98, "REG-SOUTH": 1.01}
    records = []
    for idx, branch in enumerate(branches, start=1):
        base = 190000 + idx * 15500 + rng.randint(-12000, 18000)
        growth = 0.045 + (idx % 5) * 0.012 + rng.uniform(-0.012, 0.018)
        cogs_adj = rng.uniform(-0.025, 0.035)
        sga_adj = rng.uniform(-0.02, 0.025)
        avg_order = 520 + idx * 17 + rng.randint(-25, 35)
        values = {account["account"]: {} for account in accounts}
        for period in period_map:
            pnum = int(period["period"][1:])
            month = period["month_number"]
            fy_lift = 1.0 if period["fiscal_year"] == 2024 else 1.0 + growth
            trend = 1 + (month - 6.5) * 0.004
            season = 1 + 0.08 * math.sin((month - 1) / 12 * 2 * math.pi) + (0.035 if month in (11, 12) else 0)
            noise = 1 + rng.uniform(-0.035, 0.035)
            revenue = base * region_adj[branch["region_id"]] * fy_lift * trend * season * noise
            product_revenue = money(revenue * (0.55 + rng.uniform(-0.035, 0.035)))
            service_revenue = money(revenue - product_revenue)
            direct_materials = money(product_revenue * (0.34 + cogs_adj + rng.uniform(-0.01, 0.012)))
            direct_labor = money(service_revenue * (0.41 + cogs_adj / 2 + rng.uniform(-0.012, 0.014)))
            sales_sga = money(revenue * (0.105 + sga_adj + rng.uniform(-0.006, 0.008)))
            admin_sga = money(
                (40500 + idx * 650)
                * (1.0 if period["fiscal_year"] == 2024 else 1.035)
                * (1 + rng.uniform(-0.02, 0.02))
            )
            occupancy = money(
                (25500 + idx * 480)
                * (1.0 if period["fiscal_year"] == 2024 else 1.025)
                * (1 + rng.uniform(-0.025, 0.025))
            )
            allocations = money(revenue * (0.032 + (idx % 4) * 0.002 + rng.uniform(-0.002, 0.002)))
            orders = int(round(revenue / avg_order * (1 + rng.uniform(-0.04, 0.04))))
            units = int(round(orders * (1.7 + rng.uniform(-0.12, 0.18))))
            customers = int(round(orders * (0.58 + rng.uniform(-0.05, 0.06))))
            labor_headcount = max(8, int(round(revenue / (23500 + idx * 350) + rng.uniform(-1.2, 1.2))))
            admin_headcount = max(2, int(round(labor_headcount * 0.22 + rng.uniform(-0.6, 0.7))))
            backlog = int(round(orders * (0.34 + rng.uniform(-0.04, 0.05))))

            values["product_revenue"][f"M{pnum}"] = product_revenue
            values["service_revenue"][f"M{pnum}"] = service_revenue
            values["direct_materials_cogs"][f"M{pnum}"] = direct_materials
            values["direct_labor_cogs"][f"M{pnum}"] = direct_labor
            values["sales_sga"][f"M{pnum}"] = sales_sga
            values["admin_sga"][f"M{pnum}"] = admin_sga
            values["occupancy_sga"][f"M{pnum}"] = occupancy
            values["shared_service_allocations"][f"M{pnum}"] = allocations
            values["orders"][f"M{pnum}"] = orders
            values["revenue_units"][f"M{pnum}"] = units
            values["active_customers"][f"M{pnum}"] = customers
            values["labor_headcount"][f"M{pnum}"] = labor_headcount
            values["admin_headcount"][f"M{pnum}"] = admin_headcount
            values["backlog"][f"M{pnum}"] = backlog

        for account in accounts:
            records.append(
                {
                    "branch_id": branch["branch_id"],
                    "branch_name": branch["branch_name"],
                    "region_id": branch["region_id"],
                    "account": account["account"],
                    "values": values[account["account"]],
                }
            )

    return branches, period_map, accounts, records


def build_compensation_data(rng):
    rate_book = {
        "current_year": 2026,
        "quarter_weeks": {"Q1": 13, "Q2": 13, "Q3": 13, "Q4": 13},
        "pay_types": [
            "Minimum Weekly Scale",
            "Titled Position Premium",
            "Seniority",
            "Overscale",
        ],
        "minimum_weekly_scale": 2520.0,
        "title_premium_pct": {
            "Principal": 0.20,
            "Associate Principal": 0.10,
            "Assistant Principal": 0.10,
            "Concertmaster": 0.22,
            "Section Lead": 0.15,
        },
        "seniority_weekly": [
            {"min_years": 0, "max_years": 4, "weekly_amount": 0.0},
            {"min_years": 5, "max_years": 9, "weekly_amount": 48.0},
            {"min_years": 10, "max_years": 14, "weekly_amount": 82.0},
            {"min_years": 15, "max_years": 19, "weekly_amount": 126.0},
            {"min_years": 20, "max_years": 24, "weekly_amount": 170.0},
            {"min_years": 25, "max_years": None, "weekly_amount": 215.0},
        ],
        "business_rules": [
            "Use roster quarter weeks, not a fixed 13-week quarter, when partial-quarter employees are listed.",
            "If combined_overscale_includes_title is true, do not add a titled position premium separately for that employee.",
            "For forecast years, add one year of service for Year + 1 and two years of service for Year + 2 before assigning seniority bands.",
        ],
    }

    scenarios = {
        "case_redwood_baseline": {
            "description": "Baseline board case for Redwood.",
            "year_plus_1": {
                "mws_growth": 0.03,
                "seniority_growth": 0.02,
                "overscale_growth": 0.01,
                "title_pct_multiplier": 1.0,
            },
            "year_plus_2": {
                "mws_growth": 0.032,
                "seniority_growth": 0.02,
                "overscale_growth": 0.012,
                "title_pct_multiplier": 1.0,
            },
        },
        "case_maple_board": {
            "description": "Maple board planning case.",
            "year_plus_1": {
                "mws_growth": 0.035,
                "seniority_growth": 0.018,
                "overscale_growth": 0.012,
                "title_pct_multiplier": 1.0,
            },
            "year_plus_2": {
                "mws_growth": 0.033,
                "seniority_growth": 0.02,
                "overscale_growth": 0.014,
                "title_pct_multiplier": 1.0,
            },
        },
        "case_cedar_negotiation": {
            "description": "Cedar negotiation sensitivity.",
            "year_plus_1": {
                "mws_growth": 0.042,
                "seniority_growth": 0.022,
                "overscale_growth": 0.016,
                "title_pct_multiplier": 1.03,
            },
            "year_plus_2": {
                "mws_growth": 0.038,
                "seniority_growth": 0.024,
                "overscale_growth": 0.018,
                "title_pct_multiplier": 1.04,
            },
        },
        "case_oak_sensitivity": {
            "description": "Oak board labor cost sensitivity.",
            "year_plus_1": {
                "mws_growth": 0.028,
                "seniority_growth": 0.015,
                "overscale_growth": 0.01,
                "title_pct_multiplier": 0.98,
            },
            "year_plus_2": {
                "mws_growth": 0.031,
                "seniority_growth": 0.018,
                "overscale_growth": 0.011,
                "title_pct_multiplier": 1.0,
            },
        },
    }

    ensembles = [
        ("ENS-REDWOOD", "Redwood Pops", 26),
        ("ENS-MAPLE", "Maple Chamber", 28),
        ("ENS-CEDAR", "Cedar Symphony", 31),
        ("ENS-OAK", "Oak Touring Orchestra", 24),
    ]
    titles = [
        None,
        None,
        None,
        None,
        "Principal",
        "Associate Principal",
        "Assistant Principal",
        "Section Lead",
        "Concertmaster",
    ]
    rosters = []
    for ensemble_id, ensemble_name, count in ensembles:
        for i in range(1, count + 1):
            title = rng.choice(titles)
            if i == 1:
                title = "Concertmaster"
            elif i in (2, 3, 4):
                title = "Principal"
            years = rng.randint(0, 31)
            overscale = 0.0
            if rng.random() < 0.38:
                overscale = float(rng.choice([40, 55, 75, 95, 125, 160, 210, 260, 325]))
            combined = bool(title and overscale and rng.random() < 0.24)
            weeks = {"Q1": 13, "Q2": 13, "Q3": 13, "Q4": 13}
            if rng.random() < 0.12:
                q = rng.choice(["Q1", "Q2", "Q3", "Q4"])
                weeks[q] = rng.choice([5, 7, 9, 10])
            if ensemble_id == "ENS-CEDAR" and i in (7, 18):
                weeks["Q3"] = 8
            if ensemble_id == "ENS-OAK" and i in (5, 13):
                weeks["Q1"] = 6
            note = ""
            if combined:
                note = "Overscale amount includes titled position premium per side letter."
            elif weeks != {"Q1": 13, "Q2": 13, "Q3": 13, "Q4": 13}:
                note = "Partial-quarter service schedule."
            rosters.append(
                {
                    "ensemble_id": ensemble_id,
                    "ensemble_name": ensemble_name,
                    "employee_id": f"{ensemble_id}-{i:03d}",
                    "title": title,
                    "overscale_weekly": overscale,
                    "combined_overscale_includes_title": combined,
                    "years_of_service": years,
                    "weeks_by_quarter": weeks,
                    "notes": note,
                }
            )
    return rate_book, rosters, scenarios


def schedule_item(service_id, date, service_type, start, end):
    sh, sm = (int(x) for x in start.split(":"))
    eh, em = (int(x) for x in end.split(":"))
    duration = (eh + em / 60) - (sh + sm / 60)
    return {
        "service_id": service_id,
        "date": date,
        "service_type": service_type,
        "start_time": start,
        "end_time": end,
        "duration_hours": round(duration, 2),
    }


def build_payroll_data(rng):
    rate_book = {
        "service_rates": {
            "Performance": 260.25,
            "Audit": 260.25,
            "Rehearsal": 58.75,
            "1hr Sound Check": 80.0,
            "2hr Sound Check": 142.5,
        },
        "weekly_guarantee": 2082.0,
        "service_time_limits": {
            "Performance": 3.0,
            "Audit": 3.0,
            "Rehearsal": 5.0,
            "1hr Sound Check": 1.0,
            "2hr Sound Check": 2.0,
        },
        "premium_pct": {
            "principal_or_lead": 0.15,
            "concertmaster": 0.20,
            "quartet": 0.15,
            "electronic": 0.25,
            "first_double": 0.25,
            "additional_double": 0.10,
            "vacation": 0.04,
        },
        "conflict_thresholds": {
            "rehearsal_earliest_start": "09:00",
            "rehearsal_latest_end": "18:30",
        },
        "business_rules": [
            "Service rates and premiums come from this rate book.",
            "Rehearsal pay is hourly with a three-hour minimum call.",
            "Performance, audit, and sound-check rates are per service.",
            "Premiums are applied to the musician's base service pay before vacation.",
            "The doubles premium is 25% for the first extra instrument and 10% for each additional extra instrument.",
            "Vacation is 4% of base service pay plus premiums when vacation_eligible is true.",
            "A weekly guarantee adjustment applies only to guaranteed regular players when base service pay is below weekly_guarantee.",
        ],
    }

    productions = [
        {
            "production_id": "PROD-HAMILTON-26",
            "title": "Hamilton Tour Week 26",
            "week_start": "2026-05-18",
            "schedule": [
                schedule_item("H26-S01", "2026-05-19", "Rehearsal", "08:45", "13:45"),
                schedule_item("H26-S02", "2026-05-19", "1hr Sound Check", "18:15", "19:15"),
                schedule_item("H26-S03", "2026-05-19", "Performance", "20:00", "22:30"),
                schedule_item("H26-S04", "2026-05-20", "Performance", "14:00", "16:35"),
                schedule_item("H26-S05", "2026-05-20", "Performance", "20:00", "22:35"),
                schedule_item("H26-S06", "2026-05-21", "Audit", "13:00", "15:30"),
                schedule_item("H26-S07", "2026-05-22", "Rehearsal", "10:00", "15:30"),
                schedule_item("H26-S08", "2026-05-22", "Performance", "20:00", "22:45"),
            ],
            "roster": [
                {
                    "musician_id": "M-H26-01",
                    "name": "Avery Cole",
                    "instrument": "Synthesizer",
                    "principal": False,
                    "lead": False,
                    "quartet": False,
                    "substitute": True,
                    "electronic": True,
                    "doubles": 1,
                    "vacation_eligible": False,
                    "assigned_service_ids": ["H26-S03", "H26-S04", "H26-S05", "H26-S06", "H26-S08"],
                },
                {
                    "musician_id": "M-H26-02",
                    "name": "Mira Stone",
                    "instrument": "Violin",
                    "principal": False,
                    "lead": True,
                    "quartet": True,
                    "substitute": False,
                    "electronic": False,
                    "doubles": 0,
                    "vacation_eligible": True,
                    "assigned_service_ids": [
                        "H26-S01",
                        "H26-S02",
                        "H26-S03",
                        "H26-S04",
                        "H26-S05",
                        "H26-S07",
                        "H26-S08",
                    ],
                },
                {
                    "musician_id": "M-H26-03",
                    "name": "Jon Reyes",
                    "instrument": "Trumpet",
                    "principal": True,
                    "lead": False,
                    "quartet": False,
                    "substitute": False,
                    "electronic": False,
                    "doubles": 2,
                    "vacation_eligible": True,
                    "assigned_service_ids": ["H26-S01", "H26-S03", "H26-S04", "H26-S05", "H26-S07", "H26-S08"],
                },
                {
                    "musician_id": "M-H26-04",
                    "name": "Nadia Kim",
                    "instrument": "Cello",
                    "principal": False,
                    "lead": False,
                    "quartet": True,
                    "substitute": False,
                    "electronic": False,
                    "doubles": 0,
                    "vacation_eligible": True,
                    "assigned_service_ids": ["H26-S01", "H26-S03", "H26-S04", "H26-S05", "H26-S07", "H26-S08"],
                },
                {
                    "musician_id": "M-H26-05",
                    "name": "Theo Park",
                    "instrument": "Drums",
                    "principal": True,
                    "lead": False,
                    "quartet": False,
                    "substitute": False,
                    "electronic": False,
                    "doubles": 1,
                    "vacation_eligible": True,
                    "assigned_service_ids": [
                        "H26-S01",
                        "H26-S02",
                        "H26-S03",
                        "H26-S04",
                        "H26-S05",
                        "H26-S06",
                        "H26-S07",
                        "H26-S08",
                    ],
                },
            ],
        },
        {
            "production_id": "PROD-LYRIC-27",
            "title": "Lyric Revival Week 27",
            "week_start": "2026-06-22",
            "schedule": [
                schedule_item("L27-S01", "2026-06-23", "Rehearsal", "09:15", "14:45"),
                schedule_item("L27-S02", "2026-06-23", "2hr Sound Check", "18:10", "20:25"),
                schedule_item("L27-S03", "2026-06-23", "Performance", "20:30", "23:40"),
                schedule_item("L27-S04", "2026-06-24", "Performance", "14:00", "16:30"),
                schedule_item("L27-S05", "2026-06-24", "Audit", "14:00", "16:30"),
                schedule_item("L27-S06", "2026-06-25", "Rehearsal", "08:30", "12:30"),
                schedule_item("L27-S07", "2026-06-26", "1hr Sound Check", "18:00", "18:45"),
                schedule_item("L27-S08", "2026-06-26", "Performance", "20:00", "22:40"),
                schedule_item("L27-S09", "2026-06-27", "Performance", "20:00", "22:30"),
            ],
            "roster": [
                {
                    "musician_id": "M-L27-01",
                    "name": "Iris Bloom",
                    "instrument": "Synthesizer",
                    "principal": False,
                    "lead": False,
                    "quartet": False,
                    "substitute": True,
                    "electronic": True,
                    "doubles": 0,
                    "vacation_eligible": False,
                    "assigned_service_ids": ["L27-S03", "L27-S04", "L27-S05", "L27-S08", "L27-S09"],
                },
                {
                    "musician_id": "M-L27-02",
                    "name": "Caleb Wynn",
                    "instrument": "French Horn",
                    "principal": True,
                    "lead": False,
                    "quartet": False,
                    "substitute": False,
                    "electronic": False,
                    "doubles": 1,
                    "vacation_eligible": True,
                    "assigned_service_ids": [
                        "L27-S01",
                        "L27-S02",
                        "L27-S03",
                        "L27-S04",
                        "L27-S06",
                        "L27-S08",
                        "L27-S09",
                    ],
                },
                {
                    "musician_id": "M-L27-03",
                    "name": "Selene Hart",
                    "instrument": "Violin",
                    "principal": False,
                    "lead": True,
                    "quartet": True,
                    "substitute": False,
                    "electronic": False,
                    "doubles": 0,
                    "vacation_eligible": True,
                    "assigned_service_ids": ["L27-S01", "L27-S03", "L27-S04", "L27-S06", "L27-S08", "L27-S09"],
                },
                {
                    "musician_id": "M-L27-04",
                    "name": "Owen Vale",
                    "instrument": "Woodwind",
                    "principal": False,
                    "lead": False,
                    "quartet": False,
                    "substitute": False,
                    "electronic": False,
                    "doubles": 3,
                    "vacation_eligible": True,
                    "assigned_service_ids": [
                        "L27-S01",
                        "L27-S02",
                        "L27-S03",
                        "L27-S04",
                        "L27-S06",
                        "L27-S07",
                        "L27-S08",
                        "L27-S09",
                    ],
                },
                {
                    "musician_id": "M-L27-05",
                    "name": "Rhea Singh",
                    "instrument": "Cello",
                    "principal": False,
                    "lead": False,
                    "quartet": True,
                    "substitute": False,
                    "electronic": False,
                    "doubles": 0,
                    "vacation_eligible": True,
                    "assigned_service_ids": ["L27-S01", "L27-S03", "L27-S04", "L27-S06", "L27-S08", "L27-S09"],
                },
                {
                    "musician_id": "M-L27-06",
                    "name": "Marco Bell",
                    "instrument": "Electric Bass",
                    "principal": True,
                    "lead": False,
                    "quartet": False,
                    "substitute": False,
                    "electronic": True,
                    "doubles": 1,
                    "vacation_eligible": True,
                    "assigned_service_ids": [
                        "L27-S01",
                        "L27-S02",
                        "L27-S03",
                        "L27-S04",
                        "L27-S05",
                        "L27-S06",
                        "L27-S07",
                        "L27-S08",
                        "L27-S09",
                    ],
                },
            ],
        },
        {
            "production_id": "PROD-MATINEE-26",
            "title": "Matinee Workshop Week 26",
            "week_start": "2026-05-04",
            "schedule": [
                schedule_item("M26-S01", "2026-05-05", "Rehearsal", "10:00", "13:00"),
                schedule_item("M26-S02", "2026-05-06", "Performance", "19:30", "22:00"),
            ],
            "roster": [
                {
                    "musician_id": "M-M26-01",
                    "name": "Dana Reed",
                    "instrument": "Piano",
                    "principal": False,
                    "lead": False,
                    "quartet": False,
                    "substitute": False,
                    "electronic": False,
                    "doubles": 0,
                    "vacation_eligible": True,
                    "assigned_service_ids": ["M26-S01", "M26-S02"],
                }
            ],
        },
    ]
    instruments = [
        ("Violin", False),
        ("Viola", False),
        ("Cello", False),
        ("Trumpet", False),
        ("French Horn", False),
        ("Woodwind", False),
        ("Drums", False),
        ("Electric Bass", True),
        ("Synthesizer", True),
        ("Keyboard", True),
        ("Guitar", False),
        ("Harp", False),
    ]
    first_names = [
        "Lena",
        "Grant",
        "Tessa",
        "Noel",
        "June",
        "Miles",
        "Harper",
        "Quinn",
        "Sage",
        "Rowan",
        "Elena",
        "Felix",
    ]
    last_names = [
        "Vale",
        "Mercer",
        "Hayes",
        "Chen",
        "Patel",
        "Stone",
        "Brooks",
        "Rivera",
        "Gray",
        "Morgan",
        "Lane",
        "Wells",
    ]
    titles = [
        "North Star",
        "Civic Light",
        "Arcadia",
        "Riverside",
        "Silver Room",
        "Juniper",
        "Meridian",
        "Fifth Avenue",
        "Grand Hall",
        "Beacon",
    ]

    def add_hours(start_hour, start_minute, hours):
        total = start_hour * 60 + start_minute + int(round(hours * 60))
        return f"{total // 60:02d}:{total % 60:02d}"

    def generated_schedule(prefix, week_index):
        base_day = 2 + (week_index % 18)
        items = []
        service_templates = [
            ("Rehearsal", 9, 0, rng.choice([3.0, 4.0, 5.0, 5.5])),
            (
                rng.choice(["1hr Sound Check", "2hr Sound Check"]),
                18,
                rng.choice([0, 10, 15, 30]),
                rng.choice([0.75, 1.0, 2.0, 2.25]),
            ),
            ("Performance", 20, 0, rng.choice([2.5, 2.75, 3.0, 3.25])),
            ("Performance", 14, 0, rng.choice([2.5, 2.75, 3.0])),
            ("Audit", 14, 0, rng.choice([2.5, 3.0, 3.25])),
            ("Performance", 20, 0, rng.choice([2.5, 2.75, 3.0])),
        ]
        if rng.random() < 0.35:
            service_templates[0] = ("Rehearsal", 8, rng.choice([30, 45]), rng.choice([4.0, 5.0]))
        for idx, (stype, hour, minute, dur) in enumerate(service_templates, start=1):
            day = base_day + min(idx // 2, 5)
            start = f"{hour:02d}:{minute:02d}"
            end = add_hours(hour, minute, dur)
            items.append(schedule_item(f"{prefix}-S{idx:02d}", f"2026-07-{day:02d}", stype, start, end))
        return items

    for prod_num in range(1, 15):
        prefix = f"G{prod_num:02d}"
        schedule = generated_schedule(prefix, prod_num)
        service_ids = [s["service_id"] for s in schedule]
        roster = []
        roster_size = rng.randint(5, 9)
        for idx in range(1, roster_size + 1):
            instrument, electronic_default = rng.choice(instruments)
            assigned = [sid for sid in service_ids if rng.random() > 0.18]
            if not assigned:
                assigned = [rng.choice(service_ids)]
            principal = idx in (1, 2) or rng.random() < 0.12
            lead = (not principal) and rng.random() < 0.18
            quartet = instrument in ("Violin", "Viola", "Cello") and rng.random() < 0.22
            substitute = rng.random() < 0.16
            electronic = electronic_default or (instrument == "Guitar" and rng.random() < 0.15)
            roster.append(
                {
                    "musician_id": f"M-{prefix}-{idx:02d}",
                    "name": f"{rng.choice(first_names)} {rng.choice(last_names)}",
                    "instrument": instrument,
                    "principal": principal,
                    "lead": lead,
                    "quartet": quartet,
                    "substitute": substitute,
                    "electronic": electronic,
                    "doubles": rng.choice([0, 0, 0, 1, 1, 2, 3]),
                    "vacation_eligible": not substitute and rng.random() > 0.12,
                    "assigned_service_ids": sorted(assigned),
                }
            )
        productions.append(
            {
                "production_id": f"PROD-GENERATED-{prod_num:02d}",
                "title": f"{titles[prod_num % len(titles)]} Generated Week {prod_num:02d}",
                "week_start": f"2026-07-{1 + (prod_num % 20):02d}",
                "schedule": schedule,
                "roster": roster,
            }
        )

    return rate_book, productions


def main():
    rng = random.Random(SEED)
    branches, period_map, accounts, finance_records = build_finance_data(rng)
    comp_rate_book, comp_rosters, comp_scenarios = build_compensation_data(rng)
    payroll_rate_book, payroll_productions = build_payroll_data(rng)

    write_json("finance_branches.json", branches)
    write_json("finance_period_map.json", period_map)
    write_json("finance_accounts.json", accounts)
    write_json("finance_records.json", finance_records)
    write_json("compensation_rate_book.json", comp_rate_book)
    write_json("compensation_rosters.json", comp_rosters)
    write_json("compensation_scenarios.json", comp_scenarios)
    write_json("payroll_rate_book.json", payroll_rate_book)
    write_json("payroll_productions.json", payroll_productions)

    manifest = {
        "service": "Crescent Finance Ops",
        "seed": SEED,
        "generated_at": "2026-06-02T00:00:00Z",
        "files": [
            "finance_branches.json",
            "finance_period_map.json",
            "finance_accounts.json",
            "finance_records.json",
            "compensation_rate_book.json",
            "compensation_rosters.json",
            "compensation_scenarios.json",
            "payroll_rate_book.json",
            "payroll_productions.json",
        ],
        "record_counts": {
            "finance_branches": len(branches),
            "finance_records": len(finance_records),
            "compensation_roster_rows": len(comp_rosters),
            "payroll_productions": len(payroll_productions),
        },
        "endpoints": [
            "/health",
            "/api/manifest",
            "/api/finance/branches",
            "/api/finance/period-map",
            "/api/finance/accounts",
            "/api/finance/records",
            "/api/compensation/rate-book",
            "/api/compensation/rosters",
            "/api/compensation/scenarios",
            "/api/payroll/rate-book",
            "/api/payroll/productions",
        ],
        "public_entities": {
            "branches": [
                {"branch_id": b["branch_id"], "branch_name": b["branch_name"], "region_id": b["region_id"]}
                for b in branches
            ],
            "ensembles": sorted({r["ensemble_id"]: r["ensemble_name"] for r in comp_rosters}.items()),
            "productions": [{"production_id": p["production_id"], "title": p["title"]} for p in payroll_productions],
        },
    }
    write_json("manifest.json", manifest)
    print(json.dumps({"generated": True, "manifest": str(DATA / "manifest.json")}, indent=2))


if __name__ == "__main__":
    main()
