#!/usr/bin/env python3
"""Generate the static public health evidence portal.

The generator intentionally creates realistic distractors and imperfect joins.
It writes only static pages, CSS, CSV downloads, and construction metadata.
"""

from __future__ import annotations

import csv
import json
import random
from datetime import datetime, timezone
from pathlib import Path


SEED = 20260707
ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
PAGES = WEB / "pages"
DATA = WEB / "data"
ASSETS = WEB / "assets"
GENERATED = ROOT / "generated"


STATES = [
    ("01", "AL", "Alabama", "South", "East South Central"),
    ("02", "AK", "Alaska", "West", "Pacific"),
    ("04", "AZ", "Arizona", "West", "Mountain"),
    ("05", "AR", "Arkansas", "South", "West South Central"),
    ("06", "CA", "California", "West", "Pacific"),
    ("08", "CO", "Colorado", "West", "Mountain"),
    ("09", "CT", "Connecticut", "Northeast", "New England"),
    ("10", "DE", "Delaware", "South", "South Atlantic"),
    ("11", "DC", "District of Columbia", "South", "South Atlantic"),
    ("12", "FL", "Florida", "South", "South Atlantic"),
    ("13", "GA", "Georgia", "South", "South Atlantic"),
    ("15", "HI", "Hawaii", "West", "Pacific"),
    ("16", "ID", "Idaho", "West", "Mountain"),
    ("17", "IL", "Illinois", "Midwest", "East North Central"),
    ("18", "IN", "Indiana", "Midwest", "East North Central"),
    ("19", "IA", "Iowa", "Midwest", "West North Central"),
    ("20", "KS", "Kansas", "Midwest", "West North Central"),
    ("21", "KY", "Kentucky", "South", "East South Central"),
    ("22", "LA", "Louisiana", "South", "West South Central"),
    ("23", "ME", "Maine", "Northeast", "New England"),
    ("24", "MD", "Maryland", "South", "South Atlantic"),
    ("25", "MA", "Massachusetts", "Northeast", "New England"),
    ("26", "MI", "Michigan", "Midwest", "East North Central"),
    ("27", "MN", "Minnesota", "Midwest", "West North Central"),
    ("28", "MS", "Mississippi", "South", "East South Central"),
    ("29", "MO", "Missouri", "Midwest", "West North Central"),
    ("30", "MT", "Montana", "West", "Mountain"),
    ("31", "NE", "Nebraska", "Midwest", "West North Central"),
    ("32", "NV", "Nevada", "West", "Mountain"),
    ("33", "NH", "New Hampshire", "Northeast", "New England"),
    ("34", "NJ", "New Jersey", "Northeast", "Middle Atlantic"),
    ("35", "NM", "New Mexico", "West", "Mountain"),
    ("36", "NY", "New York", "Northeast", "Middle Atlantic"),
    ("37", "NC", "North Carolina", "South", "South Atlantic"),
    ("38", "ND", "North Dakota", "Midwest", "West North Central"),
    ("39", "OH", "Ohio", "Midwest", "East North Central"),
    ("40", "OK", "Oklahoma", "South", "West South Central"),
    ("41", "OR", "Oregon", "West", "Pacific"),
    ("42", "PA", "Pennsylvania", "Northeast", "Middle Atlantic"),
    ("44", "RI", "Rhode Island", "Northeast", "New England"),
    ("45", "SC", "South Carolina", "South", "South Atlantic"),
    ("46", "SD", "South Dakota", "Midwest", "West North Central"),
    ("47", "TN", "Tennessee", "South", "East South Central"),
    ("48", "TX", "Texas", "South", "West South Central"),
    ("49", "UT", "Utah", "West", "Mountain"),
    ("50", "VT", "Vermont", "Northeast", "New England"),
    ("51", "VA", "Virginia", "South", "South Atlantic"),
    ("53", "WA", "Washington", "West", "Pacific"),
    ("54", "WV", "West Virginia", "South", "South Atlantic"),
    ("55", "WI", "Wisconsin", "Midwest", "East North Central"),
    ("56", "WY", "Wyoming", "West", "Mountain"),
]

TERRITORIES = [
    ("72", "PR", "Puerto Rico", "Territory", "Caribbean"),
    ("66", "GU", "Guam", "Territory", "Pacific Island Areas"),
    ("78", "VI", "U.S. Virgin Islands", "Territory", "Caribbean"),
]

STATE_HEALTH_MEASURES = [
    ("OBESITY", "Adult obesity prevalence", "Risk factor", "Percent", 31.0),
    ("DIAB_MORT", "Diabetes mortality rate", "Mortality", "Deaths per 100,000", 27.0),
    ("INACTIVE", "Physical inactivity prevalence", "Risk factor", "Percent", 24.0),
    ("SCREEN", "Preventive screening prevalence", "Prevention", "Percent", 71.0),
    ("LIFE_EXP", "Life expectancy", "Outcome", "Years", 78.5),
    ("VACC_COMP", "Vaccination completion", "Prevention", "Percent", 64.0),
]

COUNTY_MEASURES = [
    ("CASTHMA", "Current asthma among adults", "Health outcomes", 9.8),
    ("OBESITY", "Obesity among adults", "Health risk behaviors", 35.0),
    ("DIABETES", "Diagnosed diabetes among adults", "Health outcomes", 11.5),
    ("DEPRESSION", "Depression among adults", "Health outcomes", 20.0),
    ("CHD", "Coronary heart disease among adults", "Health outcomes", 6.5),
    ("LPA", "No leisure-time physical activity", "Health risk behaviors", 26.0),
    ("GHLTH", "Fair or poor self-rated health", "Health status", 18.0),
    ("CSMOKING", "Current smoking among adults", "Health risk behaviors", 17.0),
    ("SLEEP", "Short sleep duration among adults", "Health risk behaviors", 34.0),
    ("BINGE", "Binge drinking among adults", "Health risk behaviors", 17.5),
    ("MAMMOUSE", "Mammography use among eligible women", "Prevention", 73.0),
    ("BPMED", "Taking blood pressure medication", "Prevention", 59.0),
    ("CHECKUP", "Annual checkup among adults", "Prevention", 76.0),
    ("DENTAL", "Dental visit among adults", "Prevention", 64.0),
    ("COREM", "Core preventive services for older men", "Prevention", 42.0),
    ("COREW", "Core preventive services for older women", "Prevention", 39.0),
]


def ensure_dirs() -> None:
    for path in [PAGES, DATA, ASSETS, GENERATED]:
        path.mkdir(parents=True, exist_ok=True)


def write_csv(name: str, rows: list[dict[str, object]], fieldnames: list[str]) -> int:
    path = DATA / name
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def round_or_blank(value: float | None, digits: int = 1) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}f}"


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def state_score(abbr: str, rnd: random.Random) -> float:
    southern = {"AL", "AR", "KY", "LA", "MS", "OK", "TN", "WV"}
    coastal_healthy = {"CA", "CO", "CT", "HI", "MA", "MN", "UT", "VT", "WA"}
    score = rnd.uniform(-1.2, 1.2)
    if abbr in southern:
        score += 1.2
    if abbr in coastal_healthy:
        score -= 0.9
    if abbr in {"PR", "GU", "VI"}:
        score += 0.4
    return score


def generate_state_regions() -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    rows: list[dict[str, object]] = []
    lookup: dict[str, dict[str, object]] = {}
    for fips, abbr, name, region, division in STATES + TERRITORIES:
        is_territory = abbr in {"PR", "GU", "VI"}
        row = {
            "state_fips": fips,
            "state": abbr,
            "state_name": name,
            "region": region,
            "division": division,
            "state_level_analysis_flag": "N" if is_territory else "Y",
            "note": "Territory included as public-table distractor" if is_territory else "",
        }
        rows.append(row)
        lookup[abbr] = row
    return rows, lookup


def generate_state_health(rnd: random.Random) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    life_rows: list[dict[str, object]] = []
    profiles = {abbr: state_score(abbr, rnd) for _, abbr, _, _, _ in STATES + TERRITORIES}
    age_bands = ["18-44", "45-64", "65+"]
    sexes = ["Female", "Male"]
    incomes = ["Q1 lowest", "Q2", "Q3", "Q4 highest"]
    races = ["American Indian or Alaska Native", "Asian", "Black", "Hispanic", "White"]
    strata = [("Total", "Total")]
    strata += [("Age", item) for item in age_bands]
    strata += [("Sex", item) for item in sexes]
    strata += [("Income quartile", item) for item in incomes]
    strata += [("Race/ethnicity", item) for item in races]
    names = {abbr: name for _, abbr, name, _, _ in STATES + TERRITORIES}
    fips_lookup = {abbr: fips for fips, abbr, _, _, _ in STATES + TERRITORIES}

    for year in range(2019, 2025):
        year_effect = (year - 2019) * 0.18
        for abbr in fips_lookup:
            territory = abbr in {"PR", "GU", "VI"}
            profile = profiles[abbr]
            for measure_id, measure, category, value_type, base in STATE_HEALTH_MEASURES:
                for stratum_type, stratum in strata:
                    if (abbr, measure_id, year, stratum_type, stratum) in {
                        ("CA", "OBESITY", 2024, "Total", "Total"),
                        ("TX", "LIFE_EXP", 2024, "Total", "Total"),
                    }:
                        continue
                    shift = 0.0
                    if stratum_type == "Age":
                        shift += {"18-44": -4.2, "45-64": 1.8, "65+": 3.2}[stratum]
                    elif stratum_type == "Sex":
                        shift += {"Female": -0.6, "Male": 0.5}[stratum]
                    elif stratum_type == "Income quartile":
                        shift += {"Q1 lowest": 4.2, "Q2": 1.4, "Q3": -0.8, "Q4 highest": -3.2}[stratum]
                    elif stratum_type == "Race/ethnicity":
                        shift += {
                            "American Indian or Alaska Native": 3.4,
                            "Asian": -4.0,
                            "Black": 2.2,
                            "Hispanic": 0.8,
                            "White": -0.3,
                        }[stratum]

                    if measure_id == "LIFE_EXP":
                        value = base - profile * 1.15 + (year - 2019) * 0.07 - shift * 0.055 + rnd.gauss(0, 0.35)
                        low = value - rnd.uniform(0.3, 1.1)
                        high = value + rnd.uniform(0.3, 1.1)
                    elif measure_id == "DIAB_MORT":
                        value = base + profile * 4.5 + year_effect + shift * 0.25 + rnd.gauss(0, 1.7)
                        low = max(0.1, value - rnd.uniform(1.5, 4.0))
                        high = value + rnd.uniform(1.5, 4.0)
                    elif measure_id in {"SCREEN", "VACC_COMP"}:
                        value = base - profile * 2.2 + (year - 2019) * 0.55 - shift * 0.35 + rnd.gauss(0, 2.0)
                        value = clamp(value, 18, 96)
                        low = value - rnd.uniform(1.2, 3.6)
                        high = value + rnd.uniform(1.2, 3.6)
                    else:
                        value = base + profile * 2.4 + year_effect + shift * 0.48 + rnd.gauss(0, 1.5)
                        value = clamp(value, 5, 65)
                        low = value - rnd.uniform(1.0, 3.2)
                        high = value + rnd.uniform(1.0, 3.2)

                    blank_demo = measure_id == "SCREEN" and year == 2022 and stratum_type in {"Age", "Sex"}
                    sample_size = "" if measure_id in {"LIFE_EXP", "DIAB_MORT"} else int(rnd.uniform(850, 5800))
                    row = {
                        "year": year,
                        "state_fips": fips_lookup[abbr],
                        "state": abbr,
                        "state_name": names[abbr],
                        "territory_flag": "Y" if territory else "N",
                        "measure_id": measure_id,
                        "measure": measure,
                        "category": category,
                        "stratum_type": "" if blank_demo else stratum_type,
                        "stratum": "" if blank_demo else stratum,
                        "sample_size": sample_size,
                        "data_value_type": value_type,
                        "data_value": round_or_blank(value, 1),
                        "low_confidence_limit": round_or_blank(low, 1),
                        "high_confidence_limit": round_or_blank(high, 1),
                        "source_note": "",
                    }
                    rows.append(row)
                    if measure_id == "LIFE_EXP":
                        life_rows.append(
                            {
                                "year": year,
                                "state": abbr,
                                "state_name": names[abbr],
                                "territory_flag": "Y" if territory else "N",
                                "stratum_type": row["stratum_type"],
                                "stratum": row["stratum"],
                                "life_expectancy": row["data_value"],
                                "low_confidence_limit": row["low_confidence_limit"],
                                "high_confidence_limit": row["high_confidence_limit"],
                                "note": "Current-year Total missing for TX" if abbr == "TX" and year == 2024 else "",
                            }
                        )

    stale = [
        ("CA", "OBESITY", 2023, "Total", "Total", "Stale 2023 Total retained beside missing 2024 Total"),
        ("TX", "LIFE_EXP", 2023, "Total", "Total", "Stale 2023 Total retained beside missing 2024 Total"),
    ]
    for abbr, measure_id, year, stratum_type, stratum, note in stale:
        match = next(
            r
            for r in rows
            if r["state"] == abbr
            and r["measure_id"] == measure_id
            and r["year"] == year
            and r["stratum_type"] == stratum_type
            and r["stratum"] == stratum
        )
        dup = dict(match)
        dup["source_note"] = note
        rows.append(dup)

    duplicate_source = next(
        r
        for r in rows
        if r["state"] == "OH"
        and r["measure_id"] == "INACTIVE"
        and r["year"] == 2021
        and r["stratum_type"] == "Race/ethnicity"
        and r["stratum"] == "Black"
    )
    duplicate = dict(duplicate_source)
    duplicate["data_value"] = round_or_blank(float(duplicate["data_value"]) + 0.4, 1)
    duplicate["source_note"] = "Intentional duplicate stratified row from overlapping extract"
    rows.append(duplicate)
    return rows, life_rows


def generate_state_ses(rnd: random.Random) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    attributes = [
        ("PCTPOVALL_2023", "Percent in poverty, all ages", "percent"),
        ("MEDHHINC_2023", "Median household income, 2023", "dollars"),
        ("Unemployment_rate_2023", "Unemployment rate, 2023", "percent"),
        ("Percent_bachelors_or_higher_2019_23", "Bachelor degree or higher, 2019-23", "percent"),
        ("POP_ESTIMATE_2023", "Population estimate, 2023", "persons"),
        ("R_NET_MIG_2023", "Net migration rate, 2023", "per 1,000"),
    ]
    for fips, abbr, name, region, division in STATES + TERRITORIES:
        profile = state_score(abbr, rnd)
        base_income = 72000 - profile * 6200 + rnd.gauss(0, 5500)
        values = {
            "PCTPOVALL_2023": clamp(11.0 + profile * 2.4 + rnd.gauss(0, 1.8), 5, 28),
            "MEDHHINC_2023": clamp(base_income, 42000, 112000),
            "Unemployment_rate_2023": clamp(3.7 + profile * 0.45 + rnd.gauss(0, 0.5), 1.8, 8.5),
            "Percent_bachelors_or_higher_2019_23": clamp(34 - profile * 3.8 + rnd.gauss(0, 3.5), 16, 68),
            "POP_ESTIMATE_2023": rnd.randint(585000, 39500000) if abbr != "DC" else rnd.randint(650000, 720000),
            "R_NET_MIG_2023": rnd.uniform(-8, 18),
        }
        for attr, label, unit in attributes:
            rows.append(
                {
                    "geo_fips": f"{fips}000",
                    "state": abbr,
                    "state_name": name,
                    "geo_name": name,
                    "geo_level": "state" if abbr not in {"PR", "GU", "VI"} else "territory",
                    "attribute": attr,
                    "attribute_label": label,
                    "value": round_or_blank(values[attr], 1 if unit != "persons" else 0),
                    "unit": unit,
                    "extraction_note": "State rows end in 000; county-like rows below are distractors",
                }
            )
        for county_ix in range(1, 4):
            for attr, label, unit in attributes[:4]:
                rows.append(
                    {
                        "geo_fips": f"{fips}{county_ix:03d}",
                        "state": abbr,
                        "state_name": name,
                        "geo_name": f"{name} sample county {county_ix}",
                        "geo_level": "county-like distractor",
                        "attribute": attr,
                        "attribute_label": label,
                        "value": round_or_blank(float(values[attr]) + rnd.gauss(0, 3.0), 1),
                        "unit": unit,
                        "extraction_note": "County-like record included in state SES table",
                    }
                )
    return rows


def generate_counties(rnd: random.Random) -> list[dict[str, object]]:
    counts = {
        "AL": 18,
        "AK": 12,
        "AZ": 14,
        "CA": 40,
        "CO": 22,
        "FL": 34,
        "GA": 34,
        "HI": 5,
        "IL": 28,
        "KY": 24,
        "LA": 20,
        "MA": 12,
        "MI": 26,
        "MN": 22,
        "MS": 20,
        "NC": 32,
        "NY": 30,
        "OH": 30,
        "OR": 18,
        "PA": 30,
        "TN": 28,
        "TX": 48,
        "VA": 28,
        "WA": 18,
        "WV": 14,
        "WI": 22,
    }
    county_words = [
        "Adams",
        "Benton",
        "Cedar",
        "Clinton",
        "Columbia",
        "Douglas",
        "Franklin",
        "Grant",
        "Jackson",
        "Jefferson",
        "Lake",
        "Lincoln",
        "Madison",
        "Marion",
        "Monroe",
        "Montgomery",
        "Morgan",
        "Orange",
        "Pine",
        "Polk",
        "Riverside",
        "Summit",
        "Union",
        "Washington",
        "Wayne",
        "Woodland",
    ]
    state_info = {abbr: (fips, name, region, division) for fips, abbr, name, region, division in STATES}
    rows: list[dict[str, object]] = []
    for abbr, count in counts.items():
        fips, state_name, _region, division = state_info[abbr]
        used: set[str] = set()
        for i in range(1, count + 1):
            word = county_words[(i - 1) % len(county_words)]
            suffix = "" if word not in used else f" {i}"
            used.add(word)
            county = f"{word}{suffix} County"
            county_fips = f"{fips}{i:03d}"
            rucc = rnd.randint(1, 9)
            if abbr in {"AK", "HI", "WV"}:
                rucc = rnd.choice([6, 7, 8, 9])
            elif abbr in {"CA", "FL", "NY", "TX", "WA"}:
                rucc = rnd.choice([1, 2, 3, 4, 5])
            typology = rnd.choice(["Nonspecialized", "Manufacturing", "Federal/State government", "Recreation", "Farming", "Mining", "Persistent poverty"])
            rows.append(
                {
                    "fips": county_fips,
                    "state": abbr,
                    "state_name": state_name,
                    "county": county,
                    "rucc_code": rucc,
                    "economic_typology": typology,
                    "census_division": division,
                    "metadata_note": "",
                }
            )
    rows.extend(
        [
            {
                "fips": "00000",
                "state": "ZZ",
                "state_name": "Invalid state",
                "county": "Unknown County",
                "rucc_code": "",
                "economic_typology": "Invalid FIPS distractor",
                "census_division": "",
                "metadata_note": "Invalid FIPS county-like row",
            },
            {
                "fips": "46113",
                "state": "SD",
                "state_name": "South Dakota",
                "county": "Shannon County",
                "rucc_code": 9,
                "economic_typology": "Old name",
                "census_division": "West North Central",
                "metadata_note": "Old county name; current name is Oglala Lakota County",
            },
        ]
    )
    return rows


def generate_county_health(rnd: random.Random, counties: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for county in counties:
        if not str(county["fips"]).isdigit() or county["fips"] == "00000":
            continue
        state_factor = state_score(str(county["state"]), rnd)
        rucc = int(county["rucc_code"])
        population_base = rnd.randint(8000, 2300000) if rucc <= 3 else rnd.randint(1400, 180000)
        for year in [2021, 2022, 2023, 2024]:
            for measure_id, measure, category, base in COUNTY_MEASURES:
                if county["state"] == "AK" and measure_id == "MAMMOUSE" and year == 2024:
                    continue
                if county["fips"].endswith("007") and measure_id in {"DENTAL", "COREM"}:
                    continue
                value = base + state_factor * 1.8 + (rucc - 4) * 0.55 + (year - 2021) * rnd.uniform(-0.15, 0.25) + rnd.gauss(0, 2.0)
                if measure_id in {"MAMMOUSE", "BPMED", "CHECKUP", "DENTAL"}:
                    value = base - state_factor * 1.2 - (rucc - 4) * 0.4 + rnd.gauss(0, 2.4)
                value = clamp(value, 1, 98)
                missing_population = county["fips"].endswith("013") and measure_id == "SLEEP" and year == 2023
                low = max(0.0, value - rnd.uniform(1.5, 4.5))
                high = min(100.0, value + rnd.uniform(1.5, 4.5))
                rows.append(
                    {
                        "year": year,
                        "fips": county["fips"],
                        "state": county["state"],
                        "county": county["county"],
                        "measure_id": measure_id,
                        "measure": measure,
                        "category": category,
                        "data_value_type": "Age-adjusted prevalence",
                        "data_value": round_or_blank(value, 1),
                        "low_confidence_limit": round_or_blank(low, 1),
                        "high_confidence_limit": round_or_blank(high, 1),
                        "population": "" if missing_population else int(population_base * rnd.uniform(0.97, 1.04)),
                    }
                )
    return rows


def generate_county_ses(rnd: random.Random, counties: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    attributes = [
        ("PCTPOVALL_2023", "Percent poverty, all ages", "percent"),
        ("MEDHHINC_2023", "Median household income, 2023", "dollars"),
        ("Unemployment_rate_2010", "Unemployment rate, 2010", "percent"),
        ("Unemployment_rate_2023", "Unemployment rate, 2023", "percent"),
        ("Median_Household_Income_2022", "Median household income, 2022", "dollars"),
        ("Percent_bachelors_or_higher_2019_23", "Bachelor degree or higher, 2019-23", "percent"),
        ("POP_ESTIMATE_2023", "Population estimate, 2023", "persons"),
        ("CENSUS_2020_POP", "Census population, 2020", "persons"),
        ("R_NET_MIG_2023", "Net migration rate, 2023", "per 1,000"),
        ("R_NATURAL_CHG_2023", "Natural change rate, 2023", "per 1,000"),
        ("RUCC_2023", "Rural-urban continuum code, 2023", "code"),
        ("Economic_typology_2015", "Economic typology, 2015", "category"),
    ]
    for county in counties:
        fips = str(county["fips"])
        invalid = not fips.isdigit() or fips == "00000"
        rucc = int(county["rucc_code"]) if str(county["rucc_code"]).isdigit() else 9
        poverty = clamp(10 + (rucc - 3) * 1.4 + rnd.gauss(0, 3.0), 3.0, 36.0)
        income = clamp(79000 - poverty * 1100 + rnd.gauss(0, 6000), 31500, 146000)
        pop = rnd.randint(1600, 1850000) if not invalid else 0
        values: dict[str, object] = {
            "PCTPOVALL_2023": round_or_blank(poverty, 1),
            "MEDHHINC_2023": round_or_blank(income, 0),
            "Unemployment_rate_2010": round_or_blank(clamp(7.5 + poverty * 0.15 + rnd.gauss(0, 1.0), 2, 18), 1),
            "Unemployment_rate_2023": round_or_blank(clamp(3.4 + poverty * 0.08 + rnd.gauss(0, 0.7), 1.2, 12), 1),
            "Median_Household_Income_2022": round_or_blank(income * rnd.uniform(0.95, 1.01), 0),
            "Percent_bachelors_or_higher_2019_23": round_or_blank(clamp(40 - poverty * 0.8 + rnd.gauss(0, 5), 6, 78), 1),
            "POP_ESTIMATE_2023": pop,
            "CENSUS_2020_POP": int(pop * rnd.uniform(0.92, 1.04)) if pop else "",
            "R_NET_MIG_2023": round_or_blank(rnd.uniform(-18, 28), 1),
            "R_NATURAL_CHG_2023": round_or_blank(rnd.uniform(-8, 12), 1),
            "RUCC_2023": county["rucc_code"],
            "Economic_typology_2015": county["economic_typology"],
        }
        for attr, label, unit in attributes:
            if fips.endswith("019") and attr in {"Percent_bachelors_or_higher_2019_23", "POP_ESTIMATE_2023"}:
                continue
            rows.append(
                {
                    "fips": fips,
                    "state": county["state"],
                    "county": county["county"],
                    "attribute": attr,
                    "attribute_label": label,
                    "value": values[attr],
                    "unit": unit,
                    "join_note": county.get("metadata_note", ""),
                }
            )
    return rows


def generate_state_neighbors() -> list[dict[str, object]]:
    neighbor_map = {
        "AL": ["FL", "GA", "MS", "TN"],
        "AK": [],
        "AZ": ["CA", "CO", "NM", "NV", "UT"],
        "AR": ["LA", "MO", "MS", "OK", "TN", "TX"],
        "CA": ["AZ", "NV", "OR"],
        "CO": ["AZ", "KS", "NE", "NM", "OK", "UT", "WY"],
        "CT": ["MA", "NY", "RI"],
        "DE": ["MD", "NJ", "PA"],
        "DC": ["MD", "VA"],
        "FL": ["AL", "GA"],
        "GA": ["AL", "FL", "NC", "SC", "TN"],
        "HI": [],
        "IL": ["IA", "IN", "KY", "MO", "WI"],
        "KY": ["IL", "IN", "MO", "OH", "TN", "VA", "WV"],
        "MA": ["CT", "NH", "NY", "RI", "VT"],
        "NC": ["GA", "SC", "TN", "VA"],
        "NY": ["CT", "MA", "NJ", "PA", "VT"],
        "OH": ["IN", "KY", "MI", "PA", "WV"],
        "OR": ["CA", "ID", "NV", "WA"],
        "PA": ["DE", "MD", "NJ", "NY", "OH", "WV"],
        "TX": ["AR", "LA", "NM", "OK"],
        "WA": ["ID", "OR"],
        "WV": ["KY", "MD", "OH", "PA", "VA"],
    }
    state_names = {abbr: name for _, abbr, name, _, _ in STATES}
    rows = []
    for _fips, abbr, name, region, division in STATES:
        neighbors = neighbor_map.get(abbr, [])
        rows.append(
            {
                "state": abbr,
                "state_name": name,
                "region": region,
                "division": division,
                "neighbors": "|".join(neighbors),
                "neighbor_count": len(neighbors),
                "isolate_flag": "Y" if not neighbors else "N",
                "neighbor_names": "|".join(state_names.get(n, n) for n in neighbors),
                "note": "Isolate used for spatial residual summaries" if not neighbors else "",
            }
        )
    return rows


COUNTRIES = [
    ("Afghanistan", "AFG", "South Asia", "Low income"),
    ("Albania", "ALB", "Europe & Central Asia", "Upper middle income"),
    ("Algeria", "DZA", "Middle East & North Africa", "Upper middle income"),
    ("Angola", "AGO", "Sub-Saharan Africa", "Lower middle income"),
    ("Argentina", "ARG", "Latin America & Caribbean", "Upper middle income"),
    ("Armenia", "ARM", "Europe & Central Asia", "Upper middle income"),
    ("Australia", "AUS", "East Asia & Pacific", "High income"),
    ("Austria", "AUT", "Europe & Central Asia", "High income"),
    ("Bangladesh", "BGD", "South Asia", "Lower middle income"),
    ("Belgium", "BEL", "Europe & Central Asia", "High income"),
    ("Benin", "BEN", "Sub-Saharan Africa", "Lower middle income"),
    ("Bolivia", "BOL", "Latin America & Caribbean", "Lower middle income"),
    ("Brazil", "BRA", "Latin America & Caribbean", "Upper middle income"),
    ("Bulgaria", "BGR", "Europe & Central Asia", "High income"),
    ("Cambodia", "KHM", "East Asia & Pacific", "Lower middle income"),
    ("Cameroon", "CMR", "Sub-Saharan Africa", "Lower middle income"),
    ("Canada", "CAN", "North America", "High income"),
    ("Chile", "CHL", "Latin America & Caribbean", "High income"),
    ("China", "CHN", "East Asia & Pacific", "Upper middle income"),
    ("Colombia", "COL", "Latin America & Caribbean", "Upper middle income"),
    ("Costa Rica", "CRI", "Latin America & Caribbean", "Upper middle income"),
    ("Cote d'Ivoire", "CIV", "Sub-Saharan Africa", "Lower middle income"),
    ("Croatia", "HRV", "Europe & Central Asia", "High income"),
    ("Czechia", "CZE", "Europe & Central Asia", "High income"),
    ("Denmark", "DNK", "Europe & Central Asia", "High income"),
    ("Dominican Republic", "DOM", "Latin America & Caribbean", "Upper middle income"),
    ("Ecuador", "ECU", "Latin America & Caribbean", "Upper middle income"),
    ("Egypt", "EGY", "Middle East & North Africa", "Lower middle income"),
    ("El Salvador", "SLV", "Latin America & Caribbean", "Lower middle income"),
    ("Eswatini", "SWZ", "Sub-Saharan Africa", "Lower middle income"),
    ("Ethiopia", "ETH", "Sub-Saharan Africa", "Low income"),
    ("Finland", "FIN", "Europe & Central Asia", "High income"),
    ("France", "FRA", "Europe & Central Asia", "High income"),
    ("Georgia", "GEO", "Europe & Central Asia", "Upper middle income"),
    ("Germany", "DEU", "Europe & Central Asia", "High income"),
    ("Ghana", "GHA", "Sub-Saharan Africa", "Lower middle income"),
    ("Greece", "GRC", "Europe & Central Asia", "High income"),
    ("Guatemala", "GTM", "Latin America & Caribbean", "Upper middle income"),
    ("Haiti", "HTI", "Latin America & Caribbean", "Lower middle income"),
    ("Honduras", "HND", "Latin America & Caribbean", "Lower middle income"),
    ("Hungary", "HUN", "Europe & Central Asia", "High income"),
    ("India", "IND", "South Asia", "Lower middle income"),
    ("Indonesia", "IDN", "East Asia & Pacific", "Upper middle income"),
    ("Iran", "IRN", "Middle East & North Africa", "Upper middle income"),
    ("Iraq", "IRQ", "Middle East & North Africa", "Upper middle income"),
    ("Ireland", "IRL", "Europe & Central Asia", "High income"),
    ("Israel", "ISR", "Middle East & North Africa", "High income"),
    ("Italy", "ITA", "Europe & Central Asia", "High income"),
    ("Jamaica", "JAM", "Latin America & Caribbean", "Upper middle income"),
    ("Japan", "JPN", "East Asia & Pacific", "High income"),
    ("Jordan", "JOR", "Middle East & North Africa", "Lower middle income"),
    ("Kazakhstan", "KAZ", "Europe & Central Asia", "Upper middle income"),
    ("Kenya", "KEN", "Sub-Saharan Africa", "Lower middle income"),
    ("Korea, Rep.", "KOR", "East Asia & Pacific", "High income"),
    ("Kyrgyz Republic", "KGZ", "Europe & Central Asia", "Lower middle income"),
    ("Lao PDR", "LAO", "East Asia & Pacific", "Lower middle income"),
    ("Lebanon", "LBN", "Middle East & North Africa", "Lower middle income"),
    ("Liberia", "LBR", "Sub-Saharan Africa", "Low income"),
    ("Malaysia", "MYS", "East Asia & Pacific", "Upper middle income"),
    ("Mali", "MLI", "Sub-Saharan Africa", "Low income"),
    ("Mexico", "MEX", "Latin America & Caribbean", "Upper middle income"),
    ("Moldova", "MDA", "Europe & Central Asia", "Upper middle income"),
    ("Mongolia", "MNG", "East Asia & Pacific", "Lower middle income"),
    ("Morocco", "MAR", "Middle East & North Africa", "Lower middle income"),
    ("Mozambique", "MOZ", "Sub-Saharan Africa", "Low income"),
    ("Myanmar", "MMR", "East Asia & Pacific", "Lower middle income"),
    ("Namibia", "NAM", "Sub-Saharan Africa", "Upper middle income"),
    ("Nepal", "NPL", "South Asia", "Lower middle income"),
    ("Netherlands", "NLD", "Europe & Central Asia", "High income"),
    ("New Zealand", "NZL", "East Asia & Pacific", "High income"),
    ("Nicaragua", "NIC", "Latin America & Caribbean", "Lower middle income"),
    ("Niger", "NER", "Sub-Saharan Africa", "Low income"),
    ("Nigeria", "NGA", "Sub-Saharan Africa", "Lower middle income"),
    ("Norway", "NOR", "Europe & Central Asia", "High income"),
    ("Pakistan", "PAK", "South Asia", "Lower middle income"),
    ("Panama", "PAN", "Latin America & Caribbean", "High income"),
    ("Paraguay", "PRY", "Latin America & Caribbean", "Upper middle income"),
    ("Peru", "PER", "Latin America & Caribbean", "Upper middle income"),
    ("Philippines", "PHL", "East Asia & Pacific", "Lower middle income"),
    ("Poland", "POL", "Europe & Central Asia", "High income"),
    ("Portugal", "PRT", "Europe & Central Asia", "High income"),
    ("Romania", "ROU", "Europe & Central Asia", "High income"),
    ("Rwanda", "RWA", "Sub-Saharan Africa", "Low income"),
    ("Saudi Arabia", "SAU", "Middle East & North Africa", "High income"),
    ("Senegal", "SEN", "Sub-Saharan Africa", "Lower middle income"),
    ("Serbia", "SRB", "Europe & Central Asia", "Upper middle income"),
    ("Singapore", "SGP", "East Asia & Pacific", "High income"),
    ("Slovak Republic", "SVK", "Europe & Central Asia", "High income"),
    ("South Africa", "ZAF", "Sub-Saharan Africa", "Upper middle income"),
    ("Spain", "ESP", "Europe & Central Asia", "High income"),
    ("Sri Lanka", "LKA", "South Asia", "Lower middle income"),
    ("Sweden", "SWE", "Europe & Central Asia", "High income"),
    ("Switzerland", "CHE", "Europe & Central Asia", "High income"),
    ("Tajikistan", "TJK", "Europe & Central Asia", "Lower middle income"),
    ("Tanzania", "TZA", "Sub-Saharan Africa", "Lower middle income"),
    ("Thailand", "THA", "East Asia & Pacific", "Upper middle income"),
    ("Tunisia", "TUN", "Middle East & North Africa", "Lower middle income"),
    ("Turkiye", "TUR", "Europe & Central Asia", "Upper middle income"),
    ("Uganda", "UGA", "Sub-Saharan Africa", "Low income"),
    ("Ukraine", "UKR", "Europe & Central Asia", "Lower middle income"),
    ("United Arab Emirates", "ARE", "Middle East & North Africa", "High income"),
    ("United Kingdom", "GBR", "Europe & Central Asia", "High income"),
    ("United States", "USA", "North America", "High income"),
    ("Uruguay", "URY", "Latin America & Caribbean", "High income"),
    ("Uzbekistan", "UZB", "Europe & Central Asia", "Lower middle income"),
    ("Viet Nam", "VNM", "East Asia & Pacific", "Lower middle income"),
    ("Yemen", "YEM", "Middle East & North Africa", "Low income"),
    ("Zambia", "ZMB", "Sub-Saharan Africa", "Lower middle income"),
    ("Zimbabwe", "ZWE", "Sub-Saharan Africa", "Lower middle income"),
]


def generate_country_metadata() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    lending = {
        "High income": "Not classified",
        "Upper middle income": "IBRD",
        "Lower middle income": "Blend",
        "Low income": "IDA",
    }
    for country, iso3, region, income in COUNTRIES:
        rows.append(
            {
                "country": country,
                "iso3": iso3,
                "region": region,
                "income_group": income,
                "lending_category": lending[income],
                "metadata_note": "GDP intentionally blank in health panel" if iso3 == "JPN" else "",
            }
        )
    return rows


def generate_country_health(rnd: random.Random) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    income_base = {
        "High income": (81.5, 85, 28.0, 11.0, 13.0, 95.0, 13.5, 0.88, 47000, 4.0),
        "Upper middle income": (75.5, 130, 26.0, 6.5, 6.5, 89.0, 10.8, 0.72, 12500, 14.0),
        "Lower middle income": (68.0, 205, 23.5, 3.4, 4.3, 78.0, 8.0, 0.55, 4300, 33.0),
        "Low income": (62.0, 285, 21.6, 2.0, 3.2, 66.0, 5.5, 0.40, 1100, 51.0),
    }
    for country, iso3, region, income in COUNTRIES:
        life, mort, bmi, alcohol, expend, immun, school, inccomp, gdp, infant = income_base[income]
        country_noise = rnd.gauss(0, 1.8)
        for year in range(2015, 2025):
            trend = year - 2015
            adult_mortality = mort - trend * rnd.uniform(1.2, 3.0) + rnd.gauss(0, 11)
            if iso3 == "SWZ" and year >= 2021:
                adult_mortality = adult_mortality / 10.0
            bmi_value = bmi + trend * 0.05 + rnd.gauss(0, 0.7)
            if iso3 == "NRU" or (iso3 == "NAM" and 2018 <= year <= 2021):
                bmi_value *= 100.0
            gdp_value: float | None = gdp * rnd.uniform(0.72, 1.35) * (1 + trend * 0.018)
            if iso3 == "JPN":
                gdp_value = None
            schooling: float | None = school + trend * 0.04 + rnd.gauss(0, 0.45)
            if income in {"Low income", "Lower middle income"} and year in {2015, 2016} and rnd.random() < 0.22:
                schooling = None
            expenditure: float | None = expend + rnd.gauss(0, 1.0)
            if region == "Sub-Saharan Africa" and year in {2015, 2016, 2017} and rnd.random() < 0.18:
                expenditure = None
            rows.append(
                {
                    "country": country,
                    "iso3": iso3,
                    "year": year,
                    "life_expectancy": round_or_blank(life + trend * 0.16 + country_noise + rnd.gauss(0, 0.55), 1),
                    "adult_mortality": round_or_blank(max(5, adult_mortality), 1),
                    "bmi": round_or_blank(bmi_value, 1),
                    "alcohol": round_or_blank(max(0, alcohol + rnd.gauss(0, 1.2)), 1),
                    "health_expenditure": round_or_blank(expenditure, 1),
                    "immunization": round_or_blank(clamp(immun + trend * 0.35 + rnd.gauss(0, 4.0), 15, 99), 1),
                    "schooling": round_or_blank(schooling, 1),
                    "income_composition": round_or_blank(clamp(inccomp + trend * 0.004 + rnd.gauss(0, 0.025), 0.18, 0.96), 3),
                    "gdp": round_or_blank(gdp_value, 0),
                    "population": int(rnd.uniform(0.85, 1.18) * rnd.choice([750000, 2500000, 8200000, 18500000, 51000000, 146000000])),
                    "infant_mortality": round_or_blank(max(1, infant - trend * rnd.uniform(0.25, 1.0) + rnd.gauss(0, 2.3)), 1),
                    "missingness_note": "Japan GDP blank by design" if iso3 == "JPN" else "",
                }
            )
    return rows


def generate_country_variants() -> list[dict[str, object]]:
    variants = [
        ("United States", "United States of America", "USA", "Common formal name"),
        ("Cote d'Ivoire", "Ivory Coast", "CIV", "English exonym"),
        ("Bolivia", "Bolivia (Plurinational State of)", "BOL", "WHO-style formal name"),
        ("Czechia", "Czech Republic", "CZE", "Former short/formal name"),
        ("Eswatini", "Swaziland", "SWZ", "Former country name"),
        ("Korea, Rep.", "South Korea", "KOR", "Short press name"),
        ("Turkiye", "Turkey", "TUR", "Common variant"),
        ("Viet Nam", "Vietnam", "VNM", "Common variant"),
        ("Lao PDR", "Laos", "LAO", "Short name"),
        ("Kyrgyz Republic", "Kyrgyzstan", "KGZ", "Short name"),
        ("Slovak Republic", "Slovakia", "SVK", "Short name"),
        ("Egypt", "Egypt, Arab Rep.", "EGY", "World Bank variant"),
        ("Iran", "Iran, Islamic Rep.", "IRN", "World Bank variant"),
        ("Yemen", "Yemen, Rep.", "YEM", "World Bank variant"),
    ]
    return [
        {"canonical_country": c, "variant_name": v, "iso3": iso3, "reconciliation_note": note}
        for c, v, iso3, note in variants
    ]


def write_css() -> None:
    css = """
:root {
  color-scheme: light;
  --ink: #1f2a35;
  --muted: #5c6875;
  --line: #d8dee6;
  --panel: #ffffff;
  --surface: #f5f7fa;
  --accent: #0f766e;
  --accent-2: #7c3aed;
  --warn: #b45309;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Arial, Helvetica, sans-serif;
  color: var(--ink);
  background: var(--surface);
  line-height: 1.45;
}
a { color: #075985; }
header {
  background: #ffffff;
  border-bottom: 1px solid var(--line);
}
.wrap {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 0;
}
.brand {
  font-size: 1.08rem;
  font-weight: 700;
}
nav {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  font-size: 0.92rem;
}
nav a {
  text-decoration: none;
  color: var(--muted);
}
main { padding: 28px 0 48px; }
.hero {
  display: grid;
  gap: 10px;
  padding: 10px 0 24px;
}
h1 {
  margin: 0;
  font-size: clamp(1.8rem, 4vw, 3rem);
  line-height: 1.08;
  letter-spacing: 0;
}
h2 {
  margin: 28px 0 12px;
  font-size: 1.2rem;
}
p { max-width: 82ch; }
.lede {
  color: var(--muted);
  font-size: 1.05rem;
  margin: 0;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
}
.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 16px;
}
.card h2, .card h3 {
  margin-top: 0;
}
.downloads {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 16px 0;
}
.download {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 6px 10px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fff;
  text-decoration: none;
  color: #075985;
  font-size: 0.92rem;
}
.note {
  border-left: 4px solid var(--warn);
  background: #fff7ed;
  padding: 10px 12px;
  color: #5f370e;
  margin: 14px 0;
}
.searchbar {
  width: min(520px, 100%);
  min-height: 38px;
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: 6px;
  font-size: 1rem;
}
.table-wrap {
  overflow-x: auto;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 8px;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
th, td {
  text-align: left;
  padding: 9px 10px;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
}
th {
  background: #eef2f7;
  white-space: nowrap;
}
.pill {
  display: inline-block;
  border-radius: 999px;
  padding: 2px 8px;
  background: #e0f2fe;
  color: #075985;
  font-size: 0.78rem;
}
.footer {
  color: var(--muted);
  font-size: 0.86rem;
  padding: 24px 0;
  border-top: 1px solid var(--line);
}
@media (max-width: 760px) {
  .topbar { align-items: flex-start; flex-direction: column; }
  nav { gap: 8px 10px; }
}
""".strip()
    (ASSETS / "portal.css").write_text(css + "\n", encoding="utf-8")


def nav_html(current: str = "") -> str:
    links = [
        ("../index.html" if current else "index.html", "Home"),
        ("state-health.html", "State Health"),
        ("state-ses.html", "State SES"),
        ("state-regions.html", "Regions"),
        ("county-health.html", "County Health"),
        ("county-ses.html", "County SES"),
        ("county-neighbors.html", "Neighbors"),
        ("country-indicators.html", "Countries"),
        ("country-metadata.html", "Country Metadata"),
        ("name-reconciliation.html", "Names"),
        ("methodology.html", "Methodology"),
    ]
    if current:
        html_links = []
        for href, label in links:
            if href != "../index.html":
                href = href
            html_links.append(f'<a href="{href}">{label}</a>')
    else:
        html_links = []
        for href, label in links:
            if href.endswith(".html") and href != "index.html":
                href = f"pages/{href}"
            html_links.append(f'<a href="{href}">{label}</a>')
    return "\n".join(html_links)


def page_shell(title: str, body: str, in_pages: bool = True) -> str:
    css_href = "../assets/portal.css" if in_pages else "assets/portal.css"
    nav = nav_html("page" if in_pages else "")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} | Public Health Evidence Portal</title>
  <link rel="stylesheet" href="{css_href}">
</head>
<body>
  <header>
    <div class="wrap topbar">
      <div class="brand">Public Health Evidence Portal</div>
      <nav aria-label="Main navigation">
        {nav}
      </nav>
    </div>
  </header>
  <main class="wrap">
    {body}
  </main>
  <footer class="footer">
    <div class="wrap">Static Web portal. CSV downloads are served directly from <code>/data/</code>.</div>
  </footer>
</body>
</html>
"""


def table_html(rows: list[dict[str, object]], columns: list[str], limit: int = 12) -> str:
    head = "".join(f"<th>{col}</th>" for col in columns)
    body = []
    for row in rows[:limit]:
        body.append("<tr>" + "".join(f"<td>{row.get(col, '')}</td>" for col in columns) + "</tr>")
    return f'<div class="table-wrap"><table data-filterable><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def downloads_html(files: list[str], prefix: str = "../data/") -> str:
    return '<div class="downloads">' + "".join(f'<a class="download" href="{prefix}{name}" download>{name}</a>' for name in files) + "</div>"


def search_script() -> str:
    return """
<script>
const search = document.querySelector('[data-search]');
if (search) {
  const rows = Array.from(document.querySelectorAll('table[data-filterable] tbody tr'));
  search.addEventListener('input', () => {
    const q = search.value.trim().toLowerCase();
    rows.forEach(row => {
      row.hidden = q && !row.textContent.toLowerCase().includes(q);
    });
  });
}
</script>
""".strip()


def write_pages(row_counts: dict[str, int], samples: dict[str, list[dict[str, object]]]) -> list[str]:
    public_pages = [
        "/index.html",
        "/pages/state-health.html",
        "/pages/state-ses.html",
        "/pages/state-regions.html",
        "/pages/county-health.html",
        "/pages/county-ses.html",
        "/pages/county-neighbors.html",
        "/pages/country-indicators.html",
        "/pages/country-metadata.html",
        "/pages/name-reconciliation.html",
        "/pages/methodology.html",
    ]

    index_cards = [
        ("State health indicators", "Long-format health measures with strata, sample sizes, territories, stale rows, and duplicates.", "pages/state-health.html"),
        ("State socioeconomic indicators", "Attribute-Value SES extracts with state rows ending in 000 and county-like distractors.", "pages/state-ses.html"),
        ("State regions", "Census-like region and division lookup, including territory flags.", "pages/state-regions.html"),
        ("County health catalog", "CDC PLACES-style county measures in long format with missing measures and confidence limits.", "pages/county-health.html"),
        ("County SES tables", "County Attribute-Value tables, metadata notes, invalid FIPS rows, and old-name records.", "pages/county-ses.html"),
        ("Spatial neighbors", "State neighbor and isolate reference for residual summaries.", "pages/county-neighbors.html"),
        ("Country indicators", "WHO-like country-year panel with missingness and scale anomalies.", "pages/country-indicators.html"),
        ("Country metadata", "World Bank-like ISO3, region, income group, and lending category metadata.", "pages/country-metadata.html"),
        ("Name reconciliation", "Country variant hints for cross-source joins.", "pages/name-reconciliation.html"),
        ("Methodology", "General source-method notes and known data quality cautions.", "pages/methodology.html"),
    ]
    cards = "".join(f'<section class="card"><h2>{title}</h2><p>{desc}</p><a href="{href}">Open page</a></section>' for title, desc, href in index_cards)
    index_body = f"""
<section class="hero">
  <h1>Public Health Evidence Portal</h1>
  <p class="lede">Static public pages and downloadable CSV files for state, county, and country evidence audits.</p>
</section>
<section>
  <h2>Public Downloads</h2>
  {downloads_html(list(row_counts.keys()), prefix="data/")}
</section>
<section class="grid">{cards}</section>
"""
    (WEB / "index.html").write_text(page_shell("Home", index_body, in_pages=False), encoding="utf-8")

    pages = {
        "state-health.html": (
            "State Health Indicators",
            "State-year health measures include Total rows, age, sex, income quartile, and race/ethnicity strata. Territories appear as distractors and are flagged.",
            ["state_health_long.csv", "state_life_expectancy.csv"],
            "state_health",
            ["year", "state", "state_name", "measure_id", "stratum_type", "stratum", "data_value", "sample_size", "source_note"],
            "Known cautions: California 2024 Total obesity and Texas 2024 Total life expectancy are intentionally missing; stale 2023 Total rows remain; one Ohio stratified row is duplicated.",
        ),
        "state-ses.html": (
            "State Socioeconomic Indicators",
            "Long-format Attribute-Value SES records use FIPS-like geo codes. State-level records end in 000; county-like rows are included as distractors.",
            ["state_ses_long.csv"],
            "state_ses",
            ["geo_fips", "state", "geo_name", "geo_level", "attribute", "value", "unit", "extraction_note"],
            "Use geo_level and the 000 suffix together when extracting true state rows.",
        ),
        "state-regions.html": (
            "State Region And Division Lookup",
            "Census-like regions and divisions for 50 states, DC, and territory distractors.",
            ["state_regions.csv"],
            "state_regions",
            ["state_fips", "state", "state_name", "region", "division", "state_level_analysis_flag", "note"],
            "Territories are present but marked invalid for state-level analysis.",
        ),
        "county-health.html": (
            "County Health Measure Catalog",
            "County long-format CDC PLACES-style measures include measure IDs, confidence limits, population, and prevention categories.",
            ["county_health_long.csv", "county_metadata.csv"],
            "county_health",
            ["year", "fips", "state", "county", "measure_id", "measure", "category", "data_value", "population"],
            "Some counties intentionally lack selected measures; some county-year rows have blank population.",
        ),
        "county-ses.html": (
            "County Socioeconomic Attribute-Value Tables",
            "County SES rows are keyed by 5-digit FIPS and attribute. The metadata file includes RUCC, economic typology, census division, invalid FIPS, and old-name notes.",
            ["county_ses_long.csv", "county_metadata.csv"],
            "county_ses",
            ["fips", "state", "county", "attribute", "value", "unit", "join_note"],
            "Some counties intentionally lack population or education attributes; invalid FIPS and old county names are present.",
        ),
        "county-neighbors.html": (
            "State Neighbor And Isolate Reference",
            "State neighbor lists support spatial residual summaries. Alaska and Hawaii are isolates.",
            ["state_neighbors.csv"],
            "neighbors",
            ["state", "state_name", "region", "division", "neighbors", "neighbor_count", "isolate_flag", "note"],
            "Isolate states have no contiguous neighbors.",
        ),
        "country-indicators.html": (
            "Country Health Indicator Panel",
            "WHO-like country-year indicators cover 2015-2024 with life expectancy, adult mortality, BMI, health spending, immunization, schooling, GDP, population, and infant mortality.",
            ["country_health_panel.csv", "country_metadata.csv", "country_name_variants.csv"],
            "country_health",
            ["country", "iso3", "year", "life_expectancy", "adult_mortality", "bmi", "health_expenditure", "schooling", "gdp", "missingness_note"],
            "Known anomalies include scaled BMI for Namibia 2018-2021, a 10x adult mortality drop for Eswatini, and complete GDP gaps for Japan.",
        ),
        "country-metadata.html": (
            "Country Metadata And Income Groups",
            "World Bank-like metadata provides ISO3, region, income group, and lending-category fields for country joins.",
            ["country_metadata.csv", "country_health_panel.csv"],
            "country_meta",
            ["country", "iso3", "region", "income_group", "lending_category", "metadata_note"],
            "Lending category is included as a useful distractor and should not be confused with income group.",
        ),
        "name-reconciliation.html": (
            "Country Name Reconciliation",
            "Public crosswalk hints list systematic name variants seen across international health and development sources.",
            ["country_name_variants.csv", "country_metadata.csv"],
            "variants",
            ["canonical_country", "variant_name", "iso3", "reconciliation_note"],
            "The crosswalk is a hint table, not a complete authority list.",
        ),
    }
    for filename, (title, lede, files, sample_key, columns, note) in pages.items():
        body = f"""
<section class="hero">
  <h1>{title}</h1>
  <p class="lede">{lede}</p>
</section>
{downloads_html(files)}
<p class="note">{note}</p>
<input class="searchbar" type="search" data-search placeholder="Search visible sample rows">
{table_html(samples[sample_key], columns)}
{search_script()}
"""
        (PAGES / filename).write_text(page_shell(title, body), encoding="utf-8")

    methodology_body = f"""
<section class="hero">
  <h1>Methodology</h1>
  <p class="lede">The portal is synthetic but shaped like public health evidence sources used in state, county, and country audits.</p>
</section>
<section class="grid">
  <div class="card"><h2>Generation</h2><p>All CSV files are generated with fixed seed <code>{SEED}</code>. Values combine geographic profiles, year trends, and random noise.</p></div>
  <div class="card"><h2>State Tables</h2><p>State data include 50 states, DC, and territory distractors. Health measures are long-format with mixed demographic strata and survey sample sizes where relevant.</p></div>
  <div class="card"><h2>County Tables</h2><p>County data include hundreds of counties across diverse states, RUCC codes, economic typology, missing joins, invalid FIPS rows, and old-name records.</p></div>
  <div class="card"><h2>Country Tables</h2><p>Country data cover 2015-2024 and include WHO-like indicators, World Bank-like metadata, name variants, missingness, and scale anomalies.</p></div>
</section>
<h2>CSV Row Counts</h2>
<div class="table-wrap"><table><thead><tr><th>CSV</th><th>Rows</th></tr></thead><tbody>
{''.join(f'<tr><td>{name}</td><td>{count}</td></tr>' for name, count in sorted(row_counts.items()))}
</tbody></table></div>
"""
    (PAGES / "methodology.html").write_text(page_shell("Methodology", methodology_body), encoding="utf-8")
    return public_pages


def main() -> None:
    ensure_dirs()
    rnd = random.Random(SEED)
    row_counts: dict[str, int] = {}

    state_regions, _region_lookup = generate_state_regions()
    state_health, state_life = generate_state_health(rnd)
    state_ses = generate_state_ses(rnd)
    counties = generate_counties(rnd)
    county_health = generate_county_health(rnd, counties)
    county_ses = generate_county_ses(rnd, counties)
    state_neighbors = generate_state_neighbors()
    country_health = generate_country_health(rnd)
    country_meta = generate_country_metadata()
    country_variants = generate_country_variants()

    row_counts["state_health_long.csv"] = write_csv(
        "state_health_long.csv",
        state_health,
        ["year", "state_fips", "state", "state_name", "territory_flag", "measure_id", "measure", "category", "stratum_type", "stratum", "sample_size", "data_value_type", "data_value", "low_confidence_limit", "high_confidence_limit", "source_note"],
    )
    row_counts["state_life_expectancy.csv"] = write_csv(
        "state_life_expectancy.csv",
        state_life,
        ["year", "state", "state_name", "territory_flag", "stratum_type", "stratum", "life_expectancy", "low_confidence_limit", "high_confidence_limit", "note"],
    )
    row_counts["state_ses_long.csv"] = write_csv(
        "state_ses_long.csv",
        state_ses,
        ["geo_fips", "state", "state_name", "geo_name", "geo_level", "attribute", "attribute_label", "value", "unit", "extraction_note"],
    )
    row_counts["state_regions.csv"] = write_csv(
        "state_regions.csv",
        state_regions,
        ["state_fips", "state", "state_name", "region", "division", "state_level_analysis_flag", "note"],
    )
    row_counts["county_health_long.csv"] = write_csv(
        "county_health_long.csv",
        county_health,
        ["year", "fips", "state", "county", "measure_id", "measure", "category", "data_value_type", "data_value", "low_confidence_limit", "high_confidence_limit", "population"],
    )
    row_counts["county_ses_long.csv"] = write_csv(
        "county_ses_long.csv",
        county_ses,
        ["fips", "state", "county", "attribute", "attribute_label", "value", "unit", "join_note"],
    )
    row_counts["county_metadata.csv"] = write_csv(
        "county_metadata.csv",
        counties,
        ["fips", "state", "state_name", "county", "rucc_code", "economic_typology", "census_division", "metadata_note"],
    )
    row_counts["state_neighbors.csv"] = write_csv(
        "state_neighbors.csv",
        state_neighbors,
        ["state", "state_name", "region", "division", "neighbors", "neighbor_count", "isolate_flag", "neighbor_names", "note"],
    )
    row_counts["country_health_panel.csv"] = write_csv(
        "country_health_panel.csv",
        country_health,
        ["country", "iso3", "year", "life_expectancy", "adult_mortality", "bmi", "alcohol", "health_expenditure", "immunization", "schooling", "income_composition", "gdp", "population", "infant_mortality", "missingness_note"],
    )
    row_counts["country_metadata.csv"] = write_csv(
        "country_metadata.csv",
        country_meta,
        ["country", "iso3", "region", "income_group", "lending_category", "metadata_note"],
    )
    row_counts["country_name_variants.csv"] = write_csv(
        "country_name_variants.csv",
        country_variants,
        ["canonical_country", "variant_name", "iso3", "reconciliation_note"],
    )

    write_css()
    samples = {
        "state_health": state_health,
        "state_ses": state_ses,
        "state_regions": state_regions,
        "county_health": county_health,
        "county_ses": county_ses,
        "neighbors": state_neighbors,
        "country_health": country_health,
        "country_meta": country_meta,
        "variants": country_variants,
    }
    public_pages = write_pages(row_counts, samples)
    public_csvs = [f"/data/{name}" for name in sorted(row_counts)]
    manifest = {
        "name": "public_health_web_evidence_portal",
        "generator_seed": SEED,
        "generated_timestamp": datetime.now(timezone.utc).isoformat(),
        "row_counts": dict(sorted(row_counts.items())),
        "public_pages": public_pages,
        "public_csv_files": public_csvs,
        "notes": [
            "Static Web-page and CSV-download environment only.",
            "No solver-facing API services, answer endpoints, or task-specific pages are implemented.",
            "Intentional noise includes territory distractors, stale rows, duplicate strata, missing joins, invalid FIPS, old county names, country-name variants, missing GDP, and scaled indicator anomalies.",
        ],
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (GENERATED / "construction_summary.json").write_text(
        json.dumps(
            {
                "seed": SEED,
                "row_counts": dict(sorted(row_counts.items())),
                "generated_timestamp": manifest["generated_timestamp"],
                "intentional_noise": [
                    "CA 2024 Total obesity missing with stale 2023 Total row",
                    "TX 2024 Total life expectancy missing with stale 2023 Total row",
                    "OH 2021 Black physical inactivity duplicate stratified row",
                    "SCREEN 2022 age/sex rows have blank demographic fields",
                    "County health selected measures missing for AK and fips ending 007",
                    "County SES education/population missing for fips ending 019",
                    "Invalid FIPS 00000 and old Shannon County rows in county metadata",
                    "Japan GDP missing in country panel",
                    "Namibia BMI scaled by 100 for 2018-2021",
                    "Eswatini adult mortality drops 10x from 2021 onward",
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"seed": SEED, "row_counts": dict(sorted(row_counts.items()))}, indent=2))


if __name__ == "__main__":
    main()
