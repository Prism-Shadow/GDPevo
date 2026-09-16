#!/usr/bin/env python3
"""Solve private-wealth advisory JSON tasks from the task API.

This helper is intentionally data-driven: it reads the task memo/template,
fetches only the requested client's records, applies the planning formulas
documented in the skill, and writes one JSON object to stdout.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


SIGNED_PROFILE = "SIGNED_PROFILE"
ATTORNEY_MEMO = "ATTORNEY_MEMO"
CUSTODIAN_EXPORT = "CUSTODIAN_EXPORT"


def money(value: float) -> float:
    """Round USD outputs to cents while avoiding binary-float half-cent drift."""
    return round(float(value) + 1e-9, 2)


def fetch_json(api_base: str, path: str, params: dict[str, str] | None = None) -> Any:
    base = api_base.rstrip("/") + "/"
    url = urllib.parse.urljoin(base, path.lstrip("/"))
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def derive_task_id(task_dir: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    for part in reversed(task_dir.resolve().parts):
        if re.fullmatch(r"(?:train|test)_\d+", part):
            return part
    name = task_dir.name
    if re.fullmatch(r"(?:train|test)_\d+", name):
        return name
    raise SystemExit("Could not derive task_id; pass --task-id.")


def parse_client_id(text: str) -> str:
    match = re.search(r"Client ID:\s*(CLT-\d+)", text)
    if not match:
        match = re.search(r"\b(CLT-\d+)\b", text)
    if not match:
        raise SystemExit("Could not find client ID in prompt or request memo.")
    return match.group(1)


def parse_horizon(text: str) -> int | None:
    match = re.search(r"Planning horizon year:\s*(\d{4})", text)
    return int(match.group(1)) if match else None


def analysis_from_template(template: dict[str, Any]) -> str:
    keys = set(template.get("required_top_level_keys", []))
    if {"conversion_plan", "rmd_projection"} <= keys:
        return "roth_conversion_rmd"
    if {"gift_plan", "administration", "estate_result"} <= keys:
        return "ilit_crummey_implementation"
    if {"grat", "crat"} <= keys:
        return "trust_comparison"
    if {"ilit", "trust_transfer", "action_set"} <= keys:
        return "estate_liquidity_action_plan"

    fields = template.get("fields", {})
    analysis_spec = str(fields.get("analysis_type", ""))
    match = re.search(r"enum:\s*([A-Za-z0-9_]+)", analysis_spec)
    if match:
        return match.group(1)
    raise SystemExit("Could not infer analysis_type from answer_template.json.")


def first(records: list[dict[str, Any]], label: str) -> dict[str, Any]:
    if not records:
        raise SystemExit(f"No {label} records returned for client.")
    return records[0]


def docs_by_source(docs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {doc.get("source_type"): doc for doc in docs}


def facts(source_map: dict[str, dict[str, Any]], source_type: str) -> dict[str, Any]:
    return dict(source_map.get(source_type, {}).get("facts", {}))


def profile_value(
    client: dict[str, Any], source_map: dict[str, dict[str, Any]], key: str, default: Any = None
) -> Any:
    for source in (SIGNED_PROFILE, ATTORNEY_MEMO, "CRM_NOTE", "STALE_MARKETING_INTAKE"):
        source_facts = facts(source_map, source)
        if key in source_facts:
            return source_facts[key]
    return client.get(key, default)


def choose_account(accounts: list[dict[str, Any]]) -> dict[str, Any]:
    for account in accounts:
        if account.get("source_type") == CUSTODIAN_EXPORT:
            return account
    return first(accounts, "retirement account")


def choose_policy(policies: list[dict[str, Any]]) -> dict[str, Any]:
    for policy in policies:
        if policy.get("proposed_owner") == "ILIT":
            return policy
    return first(policies, "life insurance")


def choose_trust(trusts: list[dict[str, Any]]) -> dict[str, Any]:
    return first(trusts, "trust candidate")


def exemption_multiplier(filing_status: str) -> int:
    return 2 if filing_status == "MFJ" else 1


def estate_context(
    client: dict[str, Any],
    source_map: dict[str, dict[str, Any]],
    tax_policy: dict[str, Any],
) -> dict[str, float | int]:
    planning_year = int(profile_value(client, source_map, "planning_year", client["planning_year"]))
    filing_status = str(profile_value(client, source_map, "filing_status", client["filing_status"]))
    estate_value = float(profile_value(client, source_map, "estate_value", client["estate_value"]))
    liquid_assets = float(profile_value(client, source_map, "liquid_assets", client["liquid_assets"]))

    exemption = float(tax_policy["estate_tax_exemption"][str(planning_year)])
    exemption_used = exemption * exemption_multiplier(filing_status)
    taxable_estate = max(0.0, estate_value - exemption_used)
    estate_tax_exposure = taxable_estate * float(tax_policy["estate_tax_rate"])
    liquidity_gap = max(0.0, estate_tax_exposure - liquid_assets)

    return {
        "planning_year": planning_year,
        "exemption_used": money(exemption_used),
        "taxable_estate": money(taxable_estate),
        "estate_tax_exposure": money(estate_tax_exposure),
        "liquid_assets_available": money(liquid_assets),
        "liquidity_gap_before_planning": money(liquidity_gap),
    }


def rmd_factor(factors: dict[str, Any], age: int) -> float:
    key = str(age)
    if key in factors:
        return float(factors[key])
    available = sorted(int(k) for k in factors)
    if age > available[-1]:
        return float(factors[str(available[-1])])
    raise SystemExit(f"Missing RMD factor for age {age}.")


def project_retirement(
    *,
    traditional_balance: float,
    roth_balance: float,
    expected_return: float,
    current_age: int,
    planning_year: int,
    horizon_year: int,
    rmd_start_age: int,
    factors: dict[str, Any],
    marginal_tax_rate: float,
    annual_conversion: float = 0.0,
    conversion_years: int = 0,
) -> dict[str, float | int]:
    traditional = float(traditional_balance)
    roth = float(roth_balance)
    rmd_tax = 0.0
    actual_converted = 0.0
    positive_years = 0

    for year in range(planning_year, horizon_year + 1):
        age = current_age + (year - planning_year)
        year_index = year - planning_year

        if year_index < conversion_years and annual_conversion > 0 and traditional > 0:
            converted = min(float(annual_conversion), traditional)
            if converted > 0:
                traditional -= converted
                roth += converted
                actual_converted += converted
                positive_years += 1

        if age >= rmd_start_age:
            rmd = traditional / rmd_factor(factors, age)
            rmd_tax += rmd * marginal_tax_rate
            traditional -= rmd

        traditional *= 1.0 + expected_return
        roth *= 1.0 + expected_return

    return {
        "rmd_tax": rmd_tax,
        "traditional_balance": traditional,
        "roth_balance": roth,
        "actual_converted": actual_converted,
        "positive_years": positive_years,
    }


def solve_roth(
    task_id: str,
    client_id: str,
    horizon_year: int,
    client: dict[str, Any],
    source_map: dict[str, dict[str, Any]],
    accounts: list[dict[str, Any]],
    tax_policy: dict[str, Any],
    factors: dict[str, Any],
) -> dict[str, Any]:
    account = choose_account(accounts)
    planning_year = int(profile_value(client, source_map, "planning_year", client["planning_year"]))
    age = int(profile_value(client, source_map, "age", client["age"]))
    filing_status = str(profile_value(client, source_map, "filing_status", client["filing_status"]))
    annual_income = float(profile_value(client, source_map, "annual_non_ira_income", 0.0))
    marginal_tax_rate = float(profile_value(client, source_map, "marginal_tax_rate", 0.0))
    liquid_assets = float(profile_value(client, source_map, "liquid_assets", client["liquid_assets"]))

    target = float(tax_policy["conversion_bracket_targets"].get(filing_status, 0.0))
    annual_conversion = max(0.0, target - annual_income)
    conversion_years = int(account.get("recommended_conversion_years", 0))
    rmd_start_age = int(account.get("rmd_start_age", 73))
    expected_return = float(account["expected_return"])

    baseline = project_retirement(
        traditional_balance=float(account["traditional_balance"]),
        roth_balance=float(account.get("roth_balance", 0.0)),
        expected_return=expected_return,
        current_age=age,
        planning_year=planning_year,
        horizon_year=horizon_year,
        rmd_start_age=rmd_start_age,
        factors=factors,
        marginal_tax_rate=marginal_tax_rate,
    )
    conversion = project_retirement(
        traditional_balance=float(account["traditional_balance"]),
        roth_balance=float(account.get("roth_balance", 0.0)),
        expected_return=expected_return,
        current_age=age,
        planning_year=planning_year,
        horizon_year=horizon_year,
        rmd_start_age=rmd_start_age,
        factors=factors,
        marginal_tax_rate=marginal_tax_rate,
        annual_conversion=annual_conversion,
        conversion_years=conversion_years,
    )

    total_converted = float(conversion["actual_converted"])
    total_conversion_tax = total_converted * marginal_tax_rate
    annual_conversion_tax = annual_conversion * marginal_tax_rate

    if annual_conversion <= 0 or int(conversion["positive_years"]) == 0:
        recommendation = {
            "primary_action": "DEFER",
            "suitability": "DEFER",
            "risk_flag": "RMD_NEAR_TERM" if age >= rmd_start_age - 1 else "TAX_BRACKET_MANAGEMENT",
        }
    elif annual_conversion_tax > liquid_assets:
        recommendation = {
            "primary_action": "STAGED_ROTH_CONVERSION",
            "suitability": "BORDERLINE",
            "risk_flag": "LIQUIDITY_CONSTRAINT",
        }
    else:
        recommendation = {
            "primary_action": "STAGED_ROTH_CONVERSION",
            "suitability": "SUITABLE",
            "risk_flag": "TAX_BRACKET_MANAGEMENT",
        }

    roth_balance = float(conversion["roth_balance"])
    traditional_balance = float(conversion["traditional_balance"])
    if roth_balance > 0 and traditional_balance <= 1.0:
        heir_tax_profile = "MOSTLY_TAX_FREE"
    elif roth_balance > 0 and traditional_balance > 1.0:
        heir_tax_profile = "MIXED_TAXABLE_AND_TAX_FREE"
    else:
        heir_tax_profile = "MOSTLY_TAXABLE"

    first_rmd_year = planning_year + max(0, rmd_start_age - age)

    return {
        "task_id": task_id,
        "client_id": client_id,
        "analysis_type": "roth_conversion_rmd",
        "recommendation": recommendation,
        "conversion_plan": {
            "first_conversion_year": planning_year,
            "conversion_years": conversion_years,
            "conversion_years_positive": int(conversion["positive_years"]),
            "annual_conversion_amount": money(annual_conversion),
            "total_converted": money(total_converted),
            "total_conversion_tax": money(total_conversion_tax),
        },
        "rmd_projection": {
            "horizon_year": horizon_year,
            "first_rmd_year": first_rmd_year,
            "baseline_rmd_tax_through_horizon": money(float(baseline["rmd_tax"])),
            "conversion_rmd_tax_through_horizon": money(float(conversion["rmd_tax"])),
            "rmd_tax_savings_through_horizon": money(
                float(baseline["rmd_tax"]) - float(conversion["rmd_tax"])
            ),
        },
        "legacy_projection": {
            "projected_roth_balance_horizon": money(roth_balance),
            "projected_traditional_balance_horizon": money(traditional_balance),
            "heir_tax_profile": heir_tax_profile,
        },
        "source_resolution": {
            "controlling_profile_source": SIGNED_PROFILE,
            "controlling_account_source": account.get("source_type", CUSTODIAN_EXPORT),
        },
    }


def ilit_core(
    client: dict[str, Any],
    source_map: dict[str, dict[str, Any]],
    policies: list[dict[str, Any]],
    tax_policy: dict[str, Any],
) -> dict[str, Any]:
    policy = choose_policy(policies)
    planning_year = int(profile_value(client, source_map, "planning_year", client["planning_year"]))
    beneficiary_count = int(profile_value(client, source_map, "beneficiary_count", 0))
    annual_exclusion = float(tax_policy["annual_gift_exclusion"][str(planning_year)])
    capacity = annual_exclusion * beneficiary_count
    premium = float(policy["annual_premium"])
    premium_gap = max(0.0, premium - capacity)
    existing_transfer = bool(policy.get("is_existing_policy_transfer", False))

    if existing_transfer and premium_gap > 0:
        recommendation = {
            "primary_action": "DISCLOSE_LOOKBACK_AND_USE_EXEMPTION",
            "suitability": "BORDERLINE",
            "risk_flag": "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL",
        }
    elif existing_transfer:
        recommendation = {
            "primary_action": "USE_NEW_POLICY_OR_ACCEPT_LOOKBACK",
            "suitability": "BORDERLINE",
            "risk_flag": "THREE_YEAR_LOOKBACK",
        }
    elif premium_gap > 0:
        recommendation = {
            "primary_action": "USE_LIFETIME_EXEMPTION_FOR_SHORTFALL",
            "suitability": "BORDERLINE",
            "risk_flag": "EXCLUSION_SHORTFALL",
        }
    else:
        recommendation = {
            "primary_action": "FUND_WITH_CRUMMEY_NOTICES",
            "suitability": "SUITABLE_WITH_ADMINISTRATION",
            "risk_flag": "LOW_IF_FORMALITIES_MET",
        }

    contribution_date = dt.date.fromisoformat(policy["planned_contribution_date"])
    notice_due = contribution_date + dt.timedelta(days=7)
    withdrawal_end = notice_due + dt.timedelta(days=30)
    earliest_payment = withdrawal_end + dt.timedelta(days=1)

    return {
        "policy": policy,
        "recommendation": recommendation,
        "gift_plan": {
            "planning_year": planning_year,
            "annual_exclusion_per_beneficiary": money(annual_exclusion),
            "beneficiary_count": beneficiary_count,
            "annual_exclusion_capacity": money(capacity),
            "annual_premium": money(premium),
            "premium_gap": money(premium_gap),
        },
        "administration": {
            "notices_required": beneficiary_count,
            "contribution_date": contribution_date.isoformat(),
            "notice_due_date": notice_due.isoformat(),
            "withdrawal_window_end": withdrawal_end.isoformat(),
            "earliest_premium_payment_date": earliest_payment.isoformat(),
            "dedicated_bank_account_required": True,
        },
        "estate_result": {
            "death_benefit": money(float(policy["death_benefit"])),
            "estate_inclusion_risk": recommendation["risk_flag"],
            "projected_outside_estate_if_implemented": money(float(policy["death_benefit"])),
            "tax_liquidity_support": money(
                float(policy["death_benefit"]) * float(tax_policy["estate_tax_rate"])
            ),
        },
    }


def solve_ilit(
    task_id: str,
    client_id: str,
    client: dict[str, Any],
    source_map: dict[str, dict[str, Any]],
    policies: list[dict[str, Any]],
    tax_policy: dict[str, Any],
) -> dict[str, Any]:
    core = ilit_core(client, source_map, policies, tax_policy)
    return {
        "task_id": task_id,
        "client_id": client_id,
        "analysis_type": "ilit_crummey_implementation",
        "recommendation": core["recommendation"],
        "gift_plan": core["gift_plan"],
        "administration": core["administration"],
        "estate_result": core["estate_result"],
        "source_resolution": {
            "controlling_beneficiary_source": SIGNED_PROFILE,
            "controlling_policy_source": SIGNED_PROFILE,
        },
    }


def trust_values(trust: dict[str, Any], tax_policy: dict[str, Any]) -> dict[str, Any]:
    asset_value = float(trust["asset_value"])
    growth = float(trust["expected_growth_rate"])
    estate_tax_rate = float(tax_policy["estate_tax_rate"])
    charitable_deduction_rate = float(tax_policy["charitable_deduction_rate"])

    grat_term = int(trust["grat_term_years"])
    grat_remainder = (
        asset_value * (1.0 + growth) ** grat_term
        - asset_value * float(trust["grat_annuity_rate"]) * grat_term
    )
    crat_term = int(trust["crat_term_years"])
    crat_remainder = (
        asset_value * (1.0 + growth) ** crat_term
        - asset_value * float(trust["crat_payout_rate"]) * crat_term
    )

    return {
        "grat": {
            "term_years": grat_term,
            "projected_remainder_to_heirs": money(grat_remainder),
            "estimated_estate_tax_reduction": money(grat_remainder * estate_tax_rate),
            "mortality_inclusion_risk": "TERM_SURVIVAL_REQUIRED",
        },
        "crat": {
            "term_years": crat_term,
            "projected_charitable_remainder": money(crat_remainder),
            "estimated_income_tax_deduction": money(crat_remainder * charitable_deduction_rate),
            "family_transfer_fit": "LOW",
        },
        "trust_transfer": {
            "projected_remainder_to_heirs": money(grat_remainder),
            "estimated_estate_tax_reduction": money(grat_remainder * estate_tax_rate),
            "projected_charitable_remainder": money(crat_remainder),
        },
    }


def choose_trust_strategy(client: dict[str, Any], source_map: dict[str, dict[str, Any]]) -> dict[str, str]:
    family_priority = str(profile_value(client, source_map, "family_transfer_priority", "")).lower()
    philanthropic = str(profile_value(client, source_map, "philanthropic_intent", "")).lower()
    if philanthropic == "high" and family_priority != "high":
        return {
            "preferred_strategy": "CRAT",
            "rationale_code": "PHILANTHROPIC_PRIORITY",
            "alternate_role": "SECONDARY_FAMILY_TRANSFER_TOOL",
        }
    return {
        "preferred_strategy": "GRAT",
        "rationale_code": "CHILDREN_TRANSFER_PRIORITY",
        "alternate_role": "SECONDARY_CHARITABLE_TOOL",
    }


def solve_trust_comparison(
    task_id: str,
    client_id: str,
    client: dict[str, Any],
    source_map: dict[str, dict[str, Any]],
    trusts: list[dict[str, Any]],
    tax_policy: dict[str, Any],
) -> dict[str, Any]:
    trust = choose_trust(trusts)
    values = trust_values(trust, tax_policy)
    return {
        "task_id": task_id,
        "client_id": client_id,
        "analysis_type": "trust_comparison",
        "recommendation": choose_trust_strategy(client, source_map),
        "estate_context": estate_context(client, source_map, tax_policy),
        "grat": values["grat"],
        "crat": values["crat"],
        "source_resolution": {
            "controlling_goal_source": SIGNED_PROFILE,
            "controlling_asset_source": ATTORNEY_MEMO,
        },
    }


def solve_estate_liquidity(
    task_id: str,
    client_id: str,
    client: dict[str, Any],
    source_map: dict[str, dict[str, Any]],
    policies: list[dict[str, Any]],
    trusts: list[dict[str, Any]],
    tax_policy: dict[str, Any],
) -> dict[str, Any]:
    ilit = ilit_core(client, source_map, policies, tax_policy)
    trust = choose_trust(trusts)
    values = trust_values(trust, tax_policy)
    trust_strategy = choose_trust_strategy(client, source_map)["preferred_strategy"]
    risk_flag = ilit["recommendation"]["risk_flag"]

    if trust_strategy == "GRAT":
        primary_action = "COMBINE_ILIT_AND_GRAT"
        sequencing = "ILIT_FIRST_THEN_GRAT"
    else:
        primary_action = "CRAT_WITH_LIQUIDITY_REVIEW"
        sequencing = "TRUST_DECISION_FIRST"

    premium_gap = float(ilit["gift_plan"]["premium_gap"])
    actions = ["ATTORNEY_DRAFT_REVIEW", "ILIT_CRUMMEY_NOTICE_CYCLE"]
    if trust_strategy == "GRAT":
        actions.append("GRAT_FOR_APPRECIATING_SHARES")
    else:
        actions.append("CRAT_FOR_CHARITABLE_REMAINDER")
    if premium_gap > 0:
        actions.append("LIFETIME_EXEMPTION_ALLOCATION")

    return {
        "task_id": task_id,
        "client_id": client_id,
        "analysis_type": "estate_liquidity_action_plan",
        "recommendation": {
            "primary_action": primary_action,
            "sequencing": sequencing,
            "risk_flag": risk_flag,
        },
        "estate_context": estate_context(client, source_map, tax_policy),
        "ilit": {
            "annual_exclusion_capacity": ilit["gift_plan"]["annual_exclusion_capacity"],
            "premium_gap": ilit["gift_plan"]["premium_gap"],
            "estate_inclusion_risk": risk_flag,
            "projected_outside_estate_if_implemented": ilit["estate_result"][
                "projected_outside_estate_if_implemented"
            ],
        },
        "trust_transfer": {
            "preferred_strategy": trust_strategy,
            **values["trust_transfer"],
        },
        "action_set": sorted(actions),
        "source_resolution": {
            "controlling_goal_source": SIGNED_PROFILE,
            "controlling_policy_source": SIGNED_PROFILE,
        },
    }


def load_task(task_dir: Path) -> tuple[dict[str, Any], str, str]:
    payloads = task_dir / "input" / "payloads"
    template_path = payloads / "answer_template.json"
    try:
        template = json.loads(template_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"Missing {template_path}") from None
    memo = read_text(payloads / "request_memo.md")
    prompt = read_text(task_dir / "input" / "prompt.txt")
    return template, memo, prompt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-dir", default=".", help="Task directory containing input/payloads/.")
    parser.add_argument("--task-id", help="Stable task id, e.g. test_001.")
    parser.add_argument(
        "--api-base",
        default=os.environ.get("API_BASE", "http://task-env:9008/"),
        help="Advisory API base URL.",
    )
    args = parser.parse_args()

    task_dir = Path(args.task_dir)
    template, memo, prompt = load_task(task_dir)
    text = memo + "\n" + prompt
    task_id = derive_task_id(task_dir, args.task_id)
    client_id = parse_client_id(text)
    analysis_type = analysis_from_template(template)

    api_base = args.api_base
    client = fetch_json(api_base, f"/api/clients/{client_id}")
    source_docs = fetch_json(api_base, "/api/source-documents", {"client_id": client_id})
    source_map = docs_by_source(source_docs)
    tax_policy = fetch_json(api_base, "/api/policies/tax")

    if analysis_type == "roth_conversion_rmd":
        horizon = parse_horizon(text)
        if horizon is None:
            raise SystemExit("Roth/RMD tasks need a planning horizon year in the memo.")
        accounts = fetch_json(api_base, "/api/retirement-accounts", {"client_id": client_id})
        rmd_factors = fetch_json(api_base, "/api/rmd-factors")
        result = solve_roth(
            task_id, client_id, horizon, client, source_map, accounts, tax_policy, rmd_factors
        )
    elif analysis_type == "ilit_crummey_implementation":
        policies = fetch_json(api_base, "/api/life-insurance", {"client_id": client_id})
        result = solve_ilit(task_id, client_id, client, source_map, policies, tax_policy)
    elif analysis_type == "trust_comparison":
        trusts = fetch_json(api_base, "/api/trust-candidates", {"client_id": client_id})
        result = solve_trust_comparison(task_id, client_id, client, source_map, trusts, tax_policy)
    elif analysis_type == "estate_liquidity_action_plan":
        policies = fetch_json(api_base, "/api/life-insurance", {"client_id": client_id})
        trusts = fetch_json(api_base, "/api/trust-candidates", {"client_id": client_id})
        result = solve_estate_liquidity(
            task_id, client_id, client, source_map, policies, trusts, tax_policy
        )
    else:
        raise SystemExit(f"Unsupported analysis_type: {analysis_type}")

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
