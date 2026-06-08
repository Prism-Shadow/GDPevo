#!/usr/bin/env python3
"""Generate deterministic shared data for the Asteria Investment Office env."""

from __future__ import annotations

import json
import random
from pathlib import Path


SEED = 20260603
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_issuers():
    base = [
        (
            "ISS_AURORA_EN",
            "Aurora Energy Partners",
            "Energy",
            "Integrated Oil",
            "IG",
            False,
            "stable",
            ["BALANCE_SHEET_SCALE", "OIL_LEVERAGE"],
        ),
        (
            "ISS_BLUEGAS",
            "BlueGas LNG Holdings",
            "Energy",
            "Natural Gas/LNG",
            "IG",
            False,
            "positive",
            ["LNG_CONTRACTS", "EXPORT_CAPACITY"],
        ),
        (
            "ISS_CASCADE_MID",
            "Cascade Midstream",
            "Energy",
            "Midstream",
            "IG",
            False,
            "stable",
            ["PIPELINE_TOLLS", "LOW_COMMODITY_BETA"],
        ),
        (
            "ISS_DRIFTWOOD",
            "Driftwood Shale Finance",
            "Energy",
            "Exploration & Production",
            "HY",
            True,
            "negative",
            ["HIGH_LEVERAGE", "REFINANCING_RISK"],
        ),
        (
            "ISS_EASTERN_LNG",
            "Eastern LNG Terminals",
            "Energy",
            "Natural Gas/LNG",
            "HY",
            False,
            "positive",
            ["LNG_DEMAND", "PROJECT_RAMP"],
        ),
        (
            "ISS_FJORD_WIND",
            "Fjord Offshore Wind",
            "Energy",
            "Renewables",
            "HY",
            False,
            "stable",
            ["SUBSIDY_SUPPORT", "CONSTRUCTION_RISK"],
        ),
        (
            "ISS_GRANITE_PIPE",
            "Granite PipeCo",
            "Energy",
            "Midstream",
            "IG",
            False,
            "positive",
            ["FEE_BASED_REVENUE", "DELEVERAGING"],
        ),
        (
            "ISS_HELIOS_SOLAR",
            "Helios Solar Trust",
            "Energy",
            "Renewables",
            "IG",
            False,
            "stable",
            ["CONTRACTED_CASHFLOW", "LOW_SPREAD"],
        ),
        ("ISS_IRON_ORE", "IronOre Global", "Materials", "Mining", "IG", False, "stable", ["CYCLICAL_DEMAND"]),
        (
            "ISS_JUNIPER_TEL",
            "Juniper Telecom",
            "Communications",
            "Telecom",
            "HY",
            True,
            "negative",
            ["DOWNGRADE_RISK", "CAPEX_PRESSURE"],
        ),
        (
            "ISS_KODIAK_UTIL",
            "Kodiak Utilities",
            "Utilities",
            "Regulated Utility",
            "IG",
            False,
            "stable",
            ["DEFENSIVE_DURATION"],
        ),
        (
            "ISS_LUMEN_AUTO",
            "Lumen Auto Finance",
            "Consumer",
            "Auto Finance",
            "HY",
            False,
            "stable",
            ["CONSUMER_CREDIT"],
        ),
        ("ISS_MERIDIAN_BANK", "Meridian Bank", "Financials", "Banking", "IG", False, "positive", ["CAPITAL_RETURN"]),
        (
            "ISS_NOVA_CHEM",
            "Nova Chemicals",
            "Materials",
            "Chemicals",
            "HY",
            False,
            "stable",
            ["SPREAD_CARRY", "INPUT_COST"],
        ),
        (
            "ISS_ORBIT_REIT",
            "Orbit Logistics REIT",
            "Real Estate",
            "Industrial REIT",
            "IG",
            False,
            "stable",
            ["LEASE_DURATION"],
        ),
        (
            "ISS_PACIFIC_REFIN",
            "Pacific Refining",
            "Energy",
            "Refining",
            "HY",
            True,
            "negative",
            ["MARGIN_VOLATILITY", "WATCHLIST"],
        ),
        (
            "ISS_QUARTZ_DATA",
            "Quartz Data Centers",
            "Technology",
            "Data Centers",
            "IG",
            False,
            "positive",
            ["AI_DEMAND", "POWER_COST"],
        ),
        (
            "ISS_RIVER_POWER",
            "Riverbend Power",
            "Utilities",
            "Merchant Power",
            "HY",
            False,
            "stable",
            ["POWER_PRICE_BETA"],
        ),
    ]
    return [
        {
            "issuer_id": issuer_id,
            "issuer_name": issuer_name,
            "sector": sector,
            "subsector": subsector,
            "rating_bucket": rating_bucket,
            "watchlist": watchlist,
            "credit_outlook": outlook,
            "research_tags": tags,
        }
        for issuer_id, issuer_name, sector, subsector, rating_bucket, watchlist, outlook, tags in base
    ]


def make_bonds(issuers):
    issuer_by_id = {issuer["issuer_id"]: issuer for issuer in issuers}
    specs = [
        (
            "BND_AURORA_2029",
            "ISS_AURORA_EN",
            4.75,
            "2029-09-15",
            "BBB",
            3.1,
            5.35,
            132,
            True,
            False,
            ["OIL_DISCIPLINE"],
        ),
        (
            "BND_AURORA_2032",
            "ISS_AURORA_EN",
            5.20,
            "2032-05-01",
            "BBB",
            5.8,
            5.80,
            155,
            True,
            True,
            ["OIL_UPSIDE", "DURATION_LONG"],
        ),
        (
            "BND_BLUEGAS_2030",
            "ISS_BLUEGAS",
            5.10,
            "2030-02-20",
            "BBB-",
            4.0,
            5.95,
            168,
            True,
            True,
            ["LNG_EXPORTS", "GAS_DEMAND"],
        ),
        (
            "BND_BLUEGAS_2034",
            "ISS_BLUEGAS",
            5.65,
            "2034-06-30",
            "BBB-",
            6.7,
            6.20,
            184,
            True,
            True,
            ["LNG_EXPORTS", "DURATION_LONG"],
        ),
        (
            "BND_CASCADE_2028",
            "ISS_CASCADE_MID",
            4.40,
            "2028-11-15",
            "A-",
            2.5,
            4.95,
            105,
            True,
            False,
            ["MIDSTREAM_DEFENSIVE"],
        ),
        (
            "BND_CASCADE_2031",
            "ISS_CASCADE_MID",
            4.95,
            "2031-04-15",
            "BBB+",
            4.5,
            5.55,
            138,
            True,
            True,
            ["MIDSTREAM_TOLLS"],
        ),
        (
            "BND_DRIFTWOOD_2028",
            "ISS_DRIFTWOOD",
            8.25,
            "2028-07-01",
            "B+",
            2.9,
            9.80,
            545,
            True,
            True,
            ["HIGH_CARRY", "WATCHLIST_RISK"],
        ),
        (
            "BND_DRIFTWOOD_2031",
            "ISS_DRIFTWOOD",
            9.00,
            "2031-10-01",
            "B",
            4.9,
            10.70,
            640,
            True,
            True,
            ["HIGH_CARRY", "REFINANCING_RISK"],
        ),
        (
            "BND_EASTERN_LNG_2029",
            "ISS_EASTERN_LNG",
            7.10,
            "2029-03-01",
            "BB",
            3.6,
            8.05,
            390,
            True,
            True,
            ["LNG_DEMAND", "HY_CARRY"],
        ),
        (
            "BND_EASTERN_LNG_2032",
            "ISS_EASTERN_LNG",
            7.65,
            "2032-12-15",
            "BB-",
            5.4,
            8.70,
            455,
            True,
            True,
            ["LNG_DEMAND", "DURATION_LONG"],
        ),
        (
            "BND_FJORD_WIND_2029",
            "ISS_FJORD_WIND",
            7.45,
            "2029-08-30",
            "BB-",
            3.8,
            8.20,
            430,
            True,
            True,
            ["RENEWABLES", "HY_CARRY"],
        ),
        (
            "BND_FJORD_WIND_2033",
            "ISS_FJORD_WIND",
            8.10,
            "2033-05-30",
            "B+",
            5.9,
            9.05,
            510,
            True,
            True,
            ["RENEWABLES", "DURATION_LONG"],
        ),
        (
            "BND_GRANITE_2030",
            "ISS_GRANITE_PIPE",
            5.35,
            "2030-01-15",
            "BBB",
            4.1,
            5.90,
            162,
            True,
            True,
            ["MIDSTREAM_TOLLS", "DELEVERAGING"],
        ),
        (
            "BND_HELIOS_2028",
            "ISS_HELIOS_SOLAR",
            4.65,
            "2028-12-01",
            "BBB",
            3.0,
            5.25,
            126,
            True,
            True,
            ["RENEWABLES", "IG_DIVERSIFIER"],
        ),
        (
            "BND_IRONORE_2030",
            "ISS_IRON_ORE",
            5.25,
            "2030-03-30",
            "BBB",
            4.3,
            5.75,
            150,
            False,
            True,
            ["MINING_CYCLICAL"],
        ),
        (
            "BND_JUNIPER_2028",
            "ISS_JUNIPER_TEL",
            8.70,
            "2028-09-01",
            "B+",
            2.8,
            9.60,
            540,
            False,
            False,
            ["WATCHLIST_RISK"],
        ),
        (
            "BND_JUNIPER_2030",
            "ISS_JUNIPER_TEL",
            9.15,
            "2030-12-01",
            "B",
            4.2,
            10.10,
            610,
            False,
            True,
            ["WATCHLIST_RISK", "HIGH_CARRY"],
        ),
        (
            "BND_KODIAK_2031",
            "ISS_KODIAK_UTIL",
            4.85,
            "2031-01-15",
            "A-",
            4.9,
            5.05,
            98,
            False,
            True,
            ["DEFENSIVE_DURATION"],
        ),
        (
            "BND_LUMEN_AUTO_2029",
            "ISS_LUMEN_AUTO",
            7.80,
            "2029-06-15",
            "BB",
            3.4,
            8.55,
            420,
            False,
            False,
            ["HY_CONSUMER"],
        ),
        (
            "BND_LUMEN_AUTO_2031",
            "ISS_LUMEN_AUTO",
            8.05,
            "2031-02-15",
            "BB-",
            4.6,
            9.10,
            475,
            False,
            True,
            ["HY_CARRY", "CONSUMER_CREDIT"],
        ),
        (
            "BND_MERIDIAN_2030",
            "ISS_MERIDIAN_BANK",
            4.95,
            "2030-08-01",
            "A-",
            4.2,
            5.20,
            112,
            False,
            True,
            ["BANK_CAPITAL"],
        ),
        ("BND_NOVA_2029", "ISS_NOVA_CHEM", 7.55, "2029-04-01", "BB", 3.5, 8.35, 410, False, True, ["CHEMICALS_CARRY"]),
        ("BND_ORBIT_2030", "ISS_ORBIT_REIT", 5.15, "2030-09-15", "BBB", 4.4, 5.70, 148, False, True, ["REAL_ESTATE"]),
        (
            "BND_PACREF_2028",
            "ISS_PACIFIC_REFIN",
            8.60,
            "2028-02-01",
            "B+",
            2.3,
            9.90,
            585,
            True,
            True,
            ["REFINING_MARGIN", "WATCHLIST_RISK"],
        ),
        (
            "BND_PACREF_2030",
            "ISS_PACIFIC_REFIN",
            9.25,
            "2030-07-15",
            "B",
            4.1,
            10.80,
            675,
            True,
            True,
            ["HIGH_CARRY", "WATCHLIST_RISK"],
        ),
        ("BND_QUARTZ_2031", "ISS_QUARTZ_DATA", 5.60, "2031-03-01", "BBB", 4.8, 5.95, 170, False, True, ["AI_DEMAND"]),
        (
            "BND_RIVER_2029",
            "ISS_RIVER_POWER",
            7.95,
            "2029-10-01",
            "BB-",
            3.7,
            8.85,
            470,
            True,
            True,
            ["POWER_PRICE_BETA", "HY_CARRY"],
        ),
    ]
    bonds = []
    for instrument_id, issuer_id, coupon, maturity, rating, duration, ytm, spread, energy, candidate, tags in specs:
        issuer = issuer_by_id[issuer_id]
        bonds.append(
            {
                "instrument_id": instrument_id,
                "issuer_id": issuer_id,
                "issuer_name": issuer["issuer_name"],
                "sector": issuer["sector"],
                "subsector": issuer["subsector"],
                "coupon_pct": coupon,
                "maturity": maturity,
                "rating": rating,
                "rating_bucket": issuer["rating_bucket"],
                "modified_duration_years": duration,
                "yield_to_maturity_pct": ytm,
                "spread_bps": spread,
                "energy_linked": energy,
                "candidate": candidate,
                "recommended_theme_tags": tags,
            }
        )
    return bonds


def holding(instrument_id, quantity, asset_class, sleeve, notes=""):
    return {
        "instrument_id": instrument_id,
        "quantity_usd_m": round(quantity, 2),
        "asset_class": asset_class,
        "sleeve": sleeve,
        "notes": notes,
    }


def make_portfolios():
    portfolio_specs = [
        {
            "portfolio_id": "PF-EN-ALTA",
            "name": "Alta Energy Income Sleeve",
            "strategy": "Energy credit carry with issuer diversification",
            "as_of_date": "2026-05-29",
            "base_currency": "USD",
            "objective": "Raise energy-linked carry while keeping HY and duration inside CIO constraints.",
            "constraints": {
                "policy_id": "POL_CREDIT_DEFAULT",
                "max_hy_allocation_pct": 20.0,
                "duration_band_years": [3.0, 5.0],
            },
            "holdings": [
                holding("BND_AURORA_2029", 18.0, "Fixed Income", "Energy Credit", "Core IG oil exposure"),
                holding("BND_CASCADE_2028", 14.0, "Fixed Income", "Energy Credit", "Short midstream ballast"),
                holding("BND_GRANITE_2030", 13.0, "Fixed Income", "Energy Credit", "Fee-based midstream"),
                holding("BND_HELIOS_2028", 10.0, "Fixed Income", "Energy Credit", "Renewables diversifier"),
                holding("BND_EASTERN_LNG_2029", 5.0, "Fixed Income", "Energy Credit", "Existing HY LNG carry"),
            ],
        },
        {
            "portfolio_id": "PF-INT-NEXVEN",
            "name": "NexVen International Equity Risk Sleeve",
            "strategy": "Non-US equity diversification review",
            "as_of_date": "2026-05-29",
            "base_currency": "USD",
            "objective": "Monitor regional equity correlation and identify diversifying sleeves.",
            "constraints": {
                "policy_id": "POL_CORRELATION_DEFAULT",
                "correlation_high_threshold": 0.8,
                "correlation_low_threshold": 0.2,
            },
            "holdings": [
                holding("IDX_EM", 24.0, "Equity", "Emerging Markets", "Policy EM sleeve"),
                holding("IDX_AC_ASIA_PAC_EX_JP", 18.0, "Equity", "Asia Pacific ex Japan", "Asia beta"),
                holding("IDX_CHINA", 12.0, "Equity", "China", "Dedicated China sleeve"),
                holding("IDX_INDIA", 8.0, "Equity", "India", "Domestic growth"),
                holding("IDX_LATAM", 6.0, "Equity", "Latin America", "Commodity diversifier"),
                holding("IDX_EAFE", 20.0, "Equity", "EAFE", "Developed ex-US core"),
                holding("IDX_WORLD", 12.0, "Equity", "World ex overlay", "Global beta reference"),
            ],
        },
        {
            "portfolio_id": "PF-FI-LUMEN",
            "name": "Lumen Opportunistic Credit",
            "strategy": "Mixed credit risk-reduction rotation",
            "as_of_date": "2026-05-29",
            "base_currency": "USD",
            "objective": "Lower HY and watchlist exposure while preserving carry and duration.",
            "constraints": {
                "policy_id": "POL_CREDIT_RISK_REDUCTION",
                "max_hy_allocation_pct": 20.0,
                "target_hy_reduction_pct": 4.0,
                "duration_band_years": [3.0, 5.0],
            },
            "holdings": [
                holding("BND_JUNIPER_2028", 12.0, "Fixed Income", "High Yield Credit", "Watchlist telecom"),
                holding("BND_LUMEN_AUTO_2029", 11.0, "Fixed Income", "High Yield Credit", "Consumer HY"),
                holding("BND_NOVA_2029", 8.0, "Fixed Income", "High Yield Credit", "Chemicals HY"),
                holding("BND_KODIAK_2031", 17.0, "Fixed Income", "Investment Grade Credit", "Defensive utility"),
                holding("BND_MERIDIAN_2030", 16.0, "Fixed Income", "Financial Credit", "Bank IG"),
                holding("BND_ORBIT_2030", 14.0, "Fixed Income", "Investment Grade Credit", "REIT IG"),
            ],
        },
        {
            "portfolio_id": "PF-MA-HELIO",
            "name": "Helio Multi-Asset Committee Sleeve",
            "strategy": "Allocation view and international equity linkage",
            "as_of_date": "2026-05-29",
            "base_currency": "USD",
            "objective": "Combine non-US equity concentration signals with active allocation views.",
            "constraints": {"policy_id": "POL_MULTI_ASSET_DEFAULT"},
            "holdings": [
                holding("IDX_EM", 14.0, "Equity", "Emerging Markets", "EM allocation"),
                holding("IDX_CHINA", 8.0, "Equity", "China", "China allocation"),
                holding("IDX_INDIA", 6.0, "Equity", "India", "India allocation"),
                holding("IDX_LATAM", 5.0, "Equity", "Latin America", "LatAm allocation"),
                holding("BND_BLUEGAS_2030", 8.0, "Fixed Income", "Energy Credit", "LNG credit"),
                holding("BND_MERIDIAN_2030", 12.0, "Fixed Income", "Credit", "IG credit"),
            ],
        },
        {
            "portfolio_id": "PF-EN-BOREAL",
            "name": "Boreal Gas Transition Sleeve",
            "strategy": "Natural gas and LNG credit tilt",
            "as_of_date": "2026-05-29",
            "base_currency": "USD",
            "objective": "Add LNG/gas carry while overriding stale worksheets with current API records.",
            "constraints": {
                "policy_id": "POL_CREDIT_DEFAULT",
                "max_hy_allocation_pct": 20.0,
                "duration_band_years": [3.0, 5.0],
            },
            "holdings": [
                holding("BND_BLUEGAS_2030", 12.0, "Fixed Income", "Energy Credit", "Existing LNG IG"),
                holding("BND_CASCADE_2031", 14.0, "Fixed Income", "Energy Credit", "Midstream"),
                holding("BND_AURORA_2029", 13.0, "Fixed Income", "Energy Credit", "Oil IG"),
                holding("BND_RIVER_2029", 6.0, "Fixed Income", "Energy Credit", "HY merchant power"),
                holding("BND_KODIAK_2031", 10.0, "Fixed Income", "Utility Credit", "Non-energy IG ballast"),
            ],
        },
        {
            "portfolio_id": "PF-INT-ORION",
            "name": "Orion Expanded International Equity",
            "strategy": "International equity correlation board",
            "as_of_date": "2026-05-29",
            "base_currency": "USD",
            "objective": "Refresh 12-month regional correlation and diversification actions.",
            "constraints": {
                "policy_id": "POL_CORRELATION_DEFAULT",
                "correlation_high_threshold": 0.8,
                "correlation_low_threshold": 0.2,
            },
            "holdings": [
                holding("IDX_ACWI_IMI", 18.0, "Equity", "Global IMI", "Global benchmark"),
                holding("IDX_WORLD", 16.0, "Equity", "Developed World", "Developed benchmark"),
                holding("IDX_EUROPE", 11.0, "Equity", "Europe", "Europe sleeve"),
                holding("IDX_JAPAN", 9.0, "Equity", "Japan", "Japan sleeve"),
                holding("IDX_EM", 15.0, "Equity", "Emerging Markets", "EM sleeve"),
                holding("IDX_CHINA", 9.0, "Equity", "China", "China sleeve"),
                holding("IDX_INDIA", 8.0, "Equity", "India", "India sleeve"),
                holding("IDX_LATAM", 7.0, "Equity", "Latin America", "LatAm sleeve"),
            ],
        },
        {
            "portfolio_id": "PF-MA-CYGNUS",
            "name": "Cygnus Multi-Asset Risk Board",
            "strategy": "Credit and international correlation exception review",
            "as_of_date": "2026-05-29",
            "base_currency": "USD",
            "objective": "Rank material portfolio-risk exceptions across credit and equity sleeves.",
            "constraints": {
                "policy_id": "POL_MULTI_ASSET_RISK",
                "max_hy_allocation_pct": 20.0,
                "duration_band_years": [3.0, 5.0],
                "correlation_high_threshold": 0.8,
            },
            "holdings": [
                holding("BND_DRIFTWOOD_2028", 9.0, "Fixed Income", "Energy Credit", "Watchlist HY E&P"),
                holding("BND_PACREF_2028", 8.0, "Fixed Income", "Energy Credit", "Watchlist refining HY"),
                holding("BND_CASCADE_2031", 13.0, "Fixed Income", "Energy Credit", "Midstream IG"),
                holding("BND_MERIDIAN_2030", 16.0, "Fixed Income", "Credit", "Bank IG"),
                holding("IDX_EM", 11.0, "Equity", "Emerging Markets", "EM sleeve"),
                holding("IDX_AC_ASIA_PAC_EX_JP", 10.0, "Equity", "Asia Pacific ex Japan", "Asia concentration"),
                holding("IDX_CHINA", 7.0, "Equity", "China", "China sleeve"),
            ],
        },
        {
            "portfolio_id": "PF-MA-VEGA",
            "name": "Vega CIO Composite Portfolio",
            "strategy": "Committee decision portfolio",
            "as_of_date": "2026-05-29",
            "base_currency": "USD",
            "objective": "Integrate energy credit action, correlation findings, and allocation views.",
            "constraints": {
                "policy_id": "POL_MULTI_ASSET_DEFAULT",
                "max_hy_allocation_pct": 20.0,
                "duration_band_years": [3.0, 5.0],
            },
            "holdings": [
                holding("BND_EASTERN_LNG_2029", 7.0, "Fixed Income", "Energy Credit", "HY LNG"),
                holding("BND_BLUEGAS_2030", 10.0, "Fixed Income", "Energy Credit", "IG LNG"),
                holding("BND_GRANITE_2030", 10.0, "Fixed Income", "Energy Credit", "Midstream"),
                holding("IDX_EM", 10.0, "Equity", "Emerging Markets", "EM sleeve"),
                holding("IDX_CHINA", 7.0, "Equity", "China", "China sleeve"),
                holding("IDX_INDIA", 6.0, "Equity", "India", "India sleeve"),
                holding("IDX_LATAM", 5.0, "Equity", "Latin America", "LatAm sleeve"),
                holding("IDX_WORLD", 15.0, "Equity", "Developed World", "Developed sleeve"),
            ],
        },
        {
            "portfolio_id": "PF-FI-SABLE",
            "name": "Sable Defensive Income",
            "strategy": "IG-biased fixed income reserve",
            "as_of_date": "2026-05-29",
            "base_currency": "USD",
            "objective": "Maintain defensive income with limited HY exposure.",
            "constraints": {
                "policy_id": "POL_CREDIT_DEFAULT",
                "max_hy_allocation_pct": 15.0,
                "duration_band_years": [2.5, 5.5],
            },
            "holdings": [
                holding("BND_KODIAK_2031", 20.0, "Fixed Income", "Investment Grade Credit", "Utility ballast"),
                holding("BND_MERIDIAN_2030", 18.0, "Fixed Income", "Financial Credit", "Bank IG"),
                holding("BND_QUARTZ_2031", 12.0, "Fixed Income", "Technology Credit", "Data center IG"),
            ],
        },
        {
            "portfolio_id": "PF-INT-MIRA",
            "name": "Mira Developed International",
            "strategy": "Developed-market ex-US benchmark review",
            "as_of_date": "2026-05-29",
            "base_currency": "USD",
            "objective": "Monitor developed-market sleeve relationships.",
            "constraints": {"policy_id": "POL_CORRELATION_DEFAULT"},
            "holdings": [
                holding("IDX_EAFE", 20.0, "Equity", "EAFE", "Developed ex-US"),
                holding("IDX_EUROPE", 13.0, "Equity", "Europe", "Europe sleeve"),
                holding("IDX_JAPAN", 10.0, "Equity", "Japan", "Japan sleeve"),
                holding("IDX_UK", 8.0, "Equity", "United Kingdom", "UK sleeve"),
                holding("IDX_AUSTRALIA", 5.0, "Equity", "Australia", "Australia sleeve"),
                holding("IDX_CANADA", 6.0, "Equity", "Canada", "Canada sleeve"),
            ],
        },
    ]
    for portfolio in portfolio_specs:
        portfolio["market_value_usd_m"] = round(sum(row["quantity_usd_m"] for row in portfolio["holdings"]), 2)
    return portfolio_specs


def make_policies():
    return {
        "policy_id": "POLICY_SET_2026_05",
        "as_of_date": "2026-05-29",
        "credit_default": {
            "policy_id": "POL_CREDIT_DEFAULT",
            "max_hy_allocation_pct": 20.0,
            "target_hy_reduction_pct": 0.0,
            "duration_band_years": [3.0, 5.0],
            "issuer_concentration_limit_pct": 12.0,
            "subsector_min_count_for_diversified": 2,
        },
        "credit_risk_reduction": {
            "policy_id": "POL_CREDIT_RISK_REDUCTION",
            "max_hy_allocation_pct": 20.0,
            "target_hy_reduction_pct": 4.0,
            "duration_band_years": [3.0, 5.0],
            "issuer_concentration_limit_pct": 12.0,
            "subsector_min_count_for_diversified": 2,
        },
        "correlation": {
            "policy_id": "POL_CORRELATION_DEFAULT",
            "correlation_high_threshold": 0.80,
            "correlation_low_threshold": 0.20,
            "review_window_start": "2025-05-30",
            "review_window_end": "2026-04-30",
        },
        "allocation_mapping": {
            "policy_id": "POL_ALLOCATION_MAPPING",
            "view_score_thresholds": {"OW_min": 0.35, "UW_max": -0.35, "neutral_between": [-0.35, 0.35]},
            "conviction_thresholds": {"HIGH_abs_min": 0.70, "MEDIUM_abs_min": 0.35, "LOW_abs_below": 0.35},
            "view_rank": {"UW": -1, "N": 0, "OW": 1},
        },
        "multi_asset": {
            "policy_id": "POL_MULTI_ASSET_DEFAULT",
            "uses_credit_default": True,
            "uses_correlation_default": True,
            "uses_allocation_mapping": True,
        },
        "multi_asset_risk": {
            "policy_id": "POL_MULTI_ASSET_RISK",
            "uses_credit_risk_reduction": True,
            "uses_correlation_default": True,
            "committee_escalation_threshold": "two_or_more_material_exceptions",
        },
    }


def make_energy_market():
    return {
        "as_of_date": "2026-05-29",
        "source": "Asteria macro and commodities desk",
        "signals": [
            {
                "signal_id": "OIL_RANGE_BOUND",
                "commodity": "Brent crude",
                "score": 0.18,
                "direction": "neutral_to_positive",
                "summary": "OPEC discipline offsets slower industrial demand.",
            },
            {
                "signal_id": "US_GAS_TIGHTENS",
                "commodity": "Henry Hub natural gas",
                "score": 0.46,
                "direction": "positive",
                "summary": "Storage surplus has narrowed after hotter weather revisions.",
            },
            {
                "signal_id": "LNG_EXPORT_PULL",
                "commodity": "Global LNG",
                "score": 0.72,
                "direction": "positive",
                "summary": "Asia procurement and European refill demand support contracted LNG exporters.",
            },
            {
                "signal_id": "REFINING_VOLATILE",
                "commodity": "Refined products",
                "score": -0.41,
                "direction": "negative",
                "summary": "Crack spreads remain volatile and debt markets penalize watchlisted refiners.",
            },
            {
                "signal_id": "RENEWABLES_STABILIZE",
                "commodity": "Power and renewables",
                "score": 0.22,
                "direction": "neutral_to_positive",
                "summary": "Rate-cut expectations help contracted renewables, but project execution still matters.",
            },
        ],
        "pitch_themes": [
            "LNG_EXPORT_GROWTH",
            "MIDSTREAM_DEFENSIVE_CARRY",
            "OIL_DISCIPLINE",
            "RENEWABLES_RATE_RELIEF",
            "AVOID_REFINING_WATCHLIST",
        ],
        "stale_data_warning": "Desk worksheets dated before 2026-05-15 should be reconciled to this service before portfolio decisions.",
    }


def make_index_metadata():
    rows = [
        ("IDX_EM", "Asteria EM Equity", "Emerging Markets", "USD"),
        ("IDX_ACWI_IMI", "Asteria ACWI IMI", "Global", "USD"),
        ("IDX_WORLD", "Asteria Developed World", "Developed Global", "USD"),
        ("IDX_EM_EX_CHINA", "Asteria EM ex China", "Emerging Markets", "USD"),
        ("IDX_EAFE", "Asteria EAFE", "Developed ex North America", "USD"),
        ("IDX_CHINA", "Asteria China", "China", "USD"),
        ("IDX_INDIA", "Asteria India", "India", "USD"),
        ("IDX_LATAM", "Asteria Latin America", "Latin America", "USD"),
        ("IDX_AC_ASIA_PAC_EX_JP", "Asteria AC Asia Pacific ex Japan", "Asia Pacific ex Japan", "USD"),
        ("IDX_EUROPE", "Asteria Europe", "Europe", "USD"),
        ("IDX_JAPAN", "Asteria Japan", "Japan", "USD"),
        ("IDX_UK", "Asteria United Kingdom", "United Kingdom", "USD"),
        ("IDX_AUSTRALIA", "Asteria Australia", "Australia", "USD"),
        ("IDX_CANADA", "Asteria Canada", "Canada", "USD"),
    ]
    return [
        {
            "index_id": index_id,
            "display_name": display_name,
            "region": region,
            "currency": currency,
            "frequency": "monthly",
            "level_start_date": "2025-05-30",
            "level_end_date": "2026-04-30",
        }
        for index_id, display_name, region, currency in rows
    ]


def correlated_noise(rng, scale):
    return rng.gauss(0.0, scale)


def make_index_levels(rng):
    dates = [
        "2025-05-30",
        "2025-06-30",
        "2025-07-31",
        "2025-08-29",
        "2025-09-30",
        "2025-10-31",
        "2025-11-28",
        "2025-12-31",
        "2026-01-30",
        "2026-02-27",
        "2026-03-31",
        "2026-04-30",
    ]
    global_factor = [0.013, 0.021, -0.018, 0.016, 0.009, -0.023, 0.028, 0.018, -0.011, 0.006, 0.024]
    asia_factor = [0.018, 0.026, -0.025, 0.020, 0.015, -0.029, 0.033, 0.024, -0.014, 0.009, 0.030]
    china_factor = [0.010, 0.032, -0.041, 0.012, 0.004, -0.035, 0.039, 0.018, -0.027, 0.003, 0.020]
    latam_factor = [-0.009, 0.012, 0.018, -0.014, 0.025, 0.011, -0.006, 0.007, 0.020, -0.016, 0.004]
    india_factor = [0.025, 0.018, -0.006, 0.024, 0.021, -0.010, 0.026, 0.016, 0.010, 0.018, 0.028]
    return_map = {}
    for index_id in [row["index_id"] for row in make_index_metadata()]:
        rows = []
        level = 1000.0 + rng.uniform(-35.0, 35.0)
        rows.append({"date": dates[0], "level": round(level, 4)})
        for i in range(len(dates) - 1):
            g = global_factor[i]
            a = asia_factor[i]
            c = china_factor[i]
            l = latam_factor[i]
            ind = india_factor[i]
            if index_id == "IDX_ACWI_IMI":
                ret = 0.95 * g + correlated_noise(rng, 0.003)
            elif index_id == "IDX_WORLD":
                ret = 0.92 * g + correlated_noise(rng, 0.004)
            elif index_id == "IDX_EAFE":
                ret = 0.70 * g + 0.18 * a + correlated_noise(rng, 0.006)
            elif index_id == "IDX_EM":
                ret = 0.30 * g + 0.62 * a + correlated_noise(rng, 0.006)
            elif index_id == "IDX_AC_ASIA_PAC_EX_JP":
                ret = 0.22 * g + 0.72 * a + correlated_noise(rng, 0.005)
            elif index_id == "IDX_CHINA":
                ret = 0.18 * g + 0.38 * a + 0.42 * c + correlated_noise(rng, 0.010)
            elif index_id == "IDX_EM_EX_CHINA":
                ret = 0.32 * g + 0.28 * a + 0.20 * ind + 0.12 * l + correlated_noise(rng, 0.008)
            elif index_id == "IDX_INDIA":
                ret = 0.18 * g + 0.18 * a + 0.58 * ind - 0.10 * c + correlated_noise(rng, 0.009)
            elif index_id == "IDX_LATAM":
                ret = -0.10 * g + 0.82 * l + correlated_noise(rng, 0.010)
            elif index_id == "IDX_EUROPE":
                ret = 0.76 * g + correlated_noise(rng, 0.007)
            elif index_id == "IDX_JAPAN":
                ret = 0.50 * g + 0.12 * a + correlated_noise(rng, 0.010)
            elif index_id == "IDX_UK":
                ret = 0.55 * g + correlated_noise(rng, 0.008)
            elif index_id == "IDX_AUSTRALIA":
                ret = 0.45 * g + 0.17 * a + 0.16 * l + correlated_noise(rng, 0.011)
            elif index_id == "IDX_CANADA":
                ret = 0.52 * g + 0.18 * l + correlated_noise(rng, 0.009)
            else:
                ret = g + correlated_noise(rng, 0.01)
            level *= 1.0 + ret
            rows.append({"date": dates[i + 1], "level": round(level, 4)})
        return_map[index_id] = rows
    return return_map


def make_opportunity_sets():
    rows = []

    def add(name, asset_class, sub_asset_class):
        rows.append(
            {
                "opportunity_set": name,
                "asset_class": asset_class,
                "sub_asset_class": sub_asset_class,
                "display_order": len(rows) + 1,
            }
        )

    for name in [
        "U.S. Large Cap",
        "U.S. Small Cap",
        "Europe",
        "Japan",
        "U.K.",
        "Australia",
        "Canada",
        "Hong Kong",
        "Emerging Markets",
        "India",
        "Latin America",
    ]:
        add(name, "Equities", name)
    for name in [
        "U.S. Treasuries",
        "German Bunds",
        "Japanese Government Bonds",
        "U.K. Gilts",
        "Australia Bonds",
        "Canada Bonds",
        "Italy Fixed Income",
    ]:
        add(name, "Duration", name)
    for name in ["Corporate Investment Grade", "Corporate High Yield", "EMD Sovereign"]:
        add(name, "Credit", name)
    for name in ["USD", "EUR", "JPY", "CHF"]:
        add(name, "Currency", name)
    return rows


def prior_view_for(name, quarter):
    q2 = {
        "U.S. Large Cap": ("OW", "MEDIUM"),
        "U.S. Small Cap": ("N", "LOW"),
        "Europe": ("N", "LOW"),
        "Japan": ("OW", "MEDIUM"),
        "U.K.": ("UW", "LOW"),
        "Australia": ("N", "LOW"),
        "Canada": ("N", "LOW"),
        "Hong Kong": ("UW", "MEDIUM"),
        "Emerging Markets": ("N", "LOW"),
        "India": ("OW", "MEDIUM"),
        "Latin America": ("N", "LOW"),
        "U.S. Treasuries": ("N", "LOW"),
        "German Bunds": ("N", "LOW"),
        "Japanese Government Bonds": ("UW", "MEDIUM"),
        "U.K. Gilts": ("N", "LOW"),
        "Australia Bonds": ("N", "LOW"),
        "Canada Bonds": ("N", "LOW"),
        "Italy Fixed Income": ("UW", "MEDIUM"),
        "Corporate Investment Grade": ("OW", "MEDIUM"),
        "Corporate High Yield": ("N", "LOW"),
        "EMD Sovereign": ("N", "LOW"),
        "USD": ("OW", "MEDIUM"),
        "EUR": ("N", "LOW"),
        "JPY": ("UW", "MEDIUM"),
        "CHF": ("N", "LOW"),
    }
    q3 = {
        "U.S. Large Cap": ("OW", "MEDIUM"),
        "U.S. Small Cap": ("N", "LOW"),
        "Europe": ("OW", "MEDIUM"),
        "Japan": ("N", "LOW"),
        "U.K.": ("N", "LOW"),
        "Australia": ("N", "LOW"),
        "Canada": ("N", "LOW"),
        "Hong Kong": ("UW", "MEDIUM"),
        "Emerging Markets": ("UW", "MEDIUM"),
        "India": ("OW", "HIGH"),
        "Latin America": ("OW", "MEDIUM"),
        "U.S. Treasuries": ("OW", "MEDIUM"),
        "German Bunds": ("OW", "MEDIUM"),
        "Japanese Government Bonds": ("UW", "LOW"),
        "U.K. Gilts": ("N", "LOW"),
        "Australia Bonds": ("N", "LOW"),
        "Canada Bonds": ("N", "LOW"),
        "Italy Fixed Income": ("UW", "MEDIUM"),
        "Corporate Investment Grade": ("OW", "MEDIUM"),
        "Corporate High Yield": ("UW", "MEDIUM"),
        "EMD Sovereign": ("N", "LOW"),
        "USD": ("N", "LOW"),
        "EUR": ("OW", "MEDIUM"),
        "JPY": ("UW", "MEDIUM"),
        "CHF": ("N", "LOW"),
    }
    source = q2 if quarter == "Q2_2026" else q3
    return source[name]


def make_prior_views(opportunity_sets):
    rows = []
    for quarter in ["Q2_2026", "Q3_2026"]:
        previous_quarter = "Q1_2026" if quarter == "Q2_2026" else "Q2_2026"
        for item in opportunity_sets:
            view, conviction = prior_view_for(item["opportunity_set"], quarter)
            rows.append(
                {
                    "quarter": quarter,
                    "previous_quarter": previous_quarter,
                    "opportunity_set": item["opportunity_set"],
                    "view": view,
                    "conviction": conviction,
                }
            )
    return rows


def make_macro_signals(opportunity_sets, rng):
    q2_scores = {
        "U.S. Large Cap": (0.42, "GROWTH_IMPROVES", ["earnings_revision", "quality_bid"]),
        "U.S. Small Cap": (0.12, "NEUTRAL_BALANCE", ["financing_cost", "domestic_demand"]),
        "Europe": (0.38, "EUROPE_RECOVERY", ["real_income", "rate_cut_support"]),
        "Japan": (-0.44, "JAPAN_POLICY_RISK", ["yen_volatility", "policy_normalization"]),
        "U.K.": (-0.18, "NEUTRAL_BALANCE", ["valuation_support", "weak_growth"]),
        "Australia": (0.08, "NEUTRAL_BALANCE", ["commodities", "housing_drag"]),
        "Canada": (0.05, "NEUTRAL_BALANCE", ["oil_support", "consumer_softness"]),
        "Hong Kong": (-0.56, "CHINA_DEPENDENCE", ["china_property", "flow_pressure"]),
        "Emerging Markets": (-0.37, "CHINA_DEPENDENCE", ["china_drag", "dollar_sensitivity"]),
        "India": (0.73, "INDIA_OFFSET", ["domestic_growth", "policy_continuity"]),
        "Latin America": (0.48, "LATAM_DIVERSIFIER", ["real_rates", "commodity_income"]),
        "U.S. Treasuries": (0.51, "DURATION_SUPPORT", ["disinflation", "fed_cuts"]),
        "German Bunds": (0.46, "RATE_CUT_SUPPORT", ["ecb_cuts", "weak_growth"]),
        "Japanese Government Bonds": (-0.39, "JAPAN_POLICY_RISK", ["boj_normalization"]),
        "U.K. Gilts": (0.28, "RATE_CUT_SUPPORT", ["boe_cuts", "fiscal_risk"]),
        "Australia Bonds": (0.22, "NEUTRAL_BALANCE", ["rba_pause", "inflation_sticky"]),
        "Canada Bonds": (0.31, "RATE_CUT_SUPPORT", ["boc_cuts", "housing"]),
        "Italy Fixed Income": (-0.42, "CREDIT_SPREAD_RISK", ["fiscal_spread", "election_risk"]),
        "Corporate Investment Grade": (0.44, "RATE_CUT_SUPPORT", ["quality_carry", "spread_cushion"]),
        "Corporate High Yield": (-0.49, "HY_VALUATION_RISK", ["tight_spreads", "default_pickup"]),
        "EMD Sovereign": (0.18, "NEUTRAL_BALANCE", ["carry", "dollar_risk"]),
        "USD": (-0.22, "NEUTRAL_BALANCE", ["rate_cuts", "risk_appetite"]),
        "EUR": (0.41, "EUROPE_RECOVERY", ["growth_stabilization", "rate_path"]),
        "JPY": (-0.51, "JAPAN_POLICY_RISK", ["policy_uncertainty", "carry_cost"]),
        "CHF": (0.14, "DOLLAR_DEFENSIVE", ["defensive_demand", "low_yield"]),
    }
    q3_scores = {
        "U.S. Large Cap": (0.31, "NEUTRAL_BALANCE", ["margin_strength", "crowding"]),
        "U.S. Small Cap": (0.39, "RATE_CUT_SUPPORT", ["refinancing_relief", "domestic_growth"]),
        "Europe": (0.58, "EUROPE_RECOVERY", ["credit_impulse", "earnings_bottom"]),
        "Japan": (-0.28, "JAPAN_POLICY_RISK", ["yen_rebound", "policy_normalization"]),
        "U.K.": (0.36, "RATE_CUT_SUPPORT", ["rate_relief", "valuation"]),
        "Australia": (0.16, "NEUTRAL_BALANCE", ["china_drag", "yield_support"]),
        "Canada": (0.24, "NEUTRAL_BALANCE", ["oil_income", "consumer_debt"]),
        "Hong Kong": (-0.61, "CHINA_DEPENDENCE", ["property_stress", "flow_pressure"]),
        "Emerging Markets": (-0.41, "CHINA_DEPENDENCE", ["china_slowdown", "dollar_liquidity"]),
        "India": (0.78, "INDIA_OFFSET", ["domestic_demand", "reform_momentum"]),
        "Latin America": (0.52, "LATAM_DIVERSIFIER", ["carry", "resource_income"]),
        "U.S. Treasuries": (0.62, "DURATION_SUPPORT", ["fed_cut_path", "growth_cooling"]),
        "German Bunds": (0.57, "RATE_CUT_SUPPORT", ["ecb_cuts", "weak_inflation"]),
        "Japanese Government Bonds": (-0.45, "JAPAN_POLICY_RISK", ["boj_hikes", "curve_risk"]),
        "U.K. Gilts": (0.33, "RATE_CUT_SUPPORT", ["boe_cut_path", "issuance"]),
        "Australia Bonds": (0.26, "NEUTRAL_BALANCE", ["inflation", "employment"]),
        "Canada Bonds": (0.38, "RATE_CUT_SUPPORT", ["boc_easing", "housing_slowdown"]),
        "Italy Fixed Income": (-0.55, "CREDIT_SPREAD_RISK", ["spread_beta", "fiscal_slippage"]),
        "Corporate Investment Grade": (0.47, "RATE_CUT_SUPPORT", ["duration_carry", "quality_preference"]),
        "Corporate High Yield": (-0.63, "HY_VALUATION_RISK", ["spread_asymmetry", "downgrade_cycle"]),
        "EMD Sovereign": (0.27, "NEUTRAL_BALANCE", ["carry", "china_drag"]),
        "USD": (-0.38, "DOLLAR_DEFENSIVE", ["fed_cuts", "risk_on"]),
        "EUR": (0.49, "EUROPE_RECOVERY", ["growth_recovery", "policy_support"]),
        "JPY": (-0.57, "JAPAN_POLICY_RISK", ["boj_shift", "carry_pressure"]),
        "CHF": (0.19, "DOLLAR_DEFENSIVE", ["defensive_bid", "low_beta"]),
    }
    rows = []
    for quarter, scores in [("Q2_2026", q2_scores), ("Q3_2026", q3_scores)]:
        for item in opportunity_sets:
            name = item["opportunity_set"]
            score, rationale, drivers = scores[name]
            rows.append(
                {
                    "quarter": quarter,
                    "opportunity_set": name,
                    "score": round(score + rng.uniform(-0.005, 0.005), 3),
                    "drivers": drivers,
                    "rationale_code": rationale,
                }
            )
    return rows


def make_manifest(files):
    return {
        "environment": "Asteria Investment Office",
        "task_group_id": "task_group_010_institutional_portfolio_risk",
        "seed": SEED,
        "generated_at": "2026-06-03",
        "public_entrypoints": [
            "/",
            "/api/catalog",
            "/api/policies",
            "/api/portfolios",
            "/api/portfolios/<portfolio_id>",
            "/api/instruments/bonds",
            "/api/issuers",
            "/api/market/energy",
            "/api/indices",
            "/api/index-levels",
            "/api/index-levels/<index_id>",
            "/api/allocation/opportunity-sets",
            "/api/allocation/prior-views",
            "/api/macro-signals",
        ],
        "files": files,
        "lineage": {
            "index_levels": "Generated from deterministic factor returns; no correlations are precomputed or stored.",
            "portfolios": "Shared office records with current holdings, policy references, and distractor portfolios.",
            "credit_data": "Issuer and bond universe includes held instruments, candidates, watchlist risks, and duration-ineligible distractors.",
            "allocation_data": "Prior views and macro signals are shared policy inputs, not task-specific answers.",
        },
    }


def main():
    rng = random.Random(SEED)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    issuers = make_issuers()
    bonds = make_bonds(issuers)
    portfolios = make_portfolios()
    policies = make_policies()
    energy_market = make_energy_market()
    indices = make_index_metadata()
    index_levels = make_index_levels(rng)
    opportunity_sets = make_opportunity_sets()
    prior_views = make_prior_views(opportunity_sets)
    macro_signals = make_macro_signals(opportunity_sets, rng)

    payloads = {
        "issuers.json": issuers,
        "bonds.json": bonds,
        "portfolios.json": portfolios,
        "policies.json": policies,
        "energy_market.json": energy_market,
        "indices.json": indices,
        "index_levels.json": index_levels,
        "opportunity_sets.json": opportunity_sets,
        "prior_views.json": prior_views,
        "macro_signals.json": macro_signals,
    }

    file_records = []
    for filename, payload in payloads.items():
        path = DATA_DIR / filename
        write_json(path, payload)
        if isinstance(payload, list):
            records = len(payload)
        elif isinstance(payload, dict):
            records = len(payload)
        else:
            records = None
        file_records.append({"path": f"data/{filename}", "records": records})

    manifest = make_manifest(file_records)
    write_json(ROOT / "manifest.json", manifest)
    print(f"Generated {len(payloads)} data files and manifest with seed {SEED}.")


if __name__ == "__main__":
    main()
