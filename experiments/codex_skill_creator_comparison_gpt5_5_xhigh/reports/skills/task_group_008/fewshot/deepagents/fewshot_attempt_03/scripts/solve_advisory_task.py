#!/usr/bin/env python3
"""Solve private-wealth advisory JSON tasks from the local input folder."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any


SOURCE_PROFILE = "SIGNED_PROFILE"
SOURCE_ACCOUNT = "CUSTODIAN_EXPORT"
SOURCE_POLICY = "SIGNED_PROFILE"
SOURCE_ASSET = "ATTORNEY_MEMO"


def money(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def fetch_json(api_base: str, path: str) -> Any:
    url = api_base.rstrip("/") + path
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def one_for_client(rows: list[dict[str, Any]], client_id: str) -> dict[str, Any]:
    matches = [row for row in rows if row.get("client_id") == client_id]
    if not matches:
        raise SystemExit(f"No record found for {client_id}")
    return matches[0]


def signed_profile(source_docs: list[dict[str, Any]], client: dict[str, Any]) -> dict[str, Any]:
    signed = [
        doc
        for doc in source_docs
        if doc.get("client_id") == client["client_id"]
        and doc.get("source_type") == SOURCE_PROFILE
    ]
    facts = dict(client)
    if signed:
        facts.update(signed[0].get("facts", {}))
    return facts


def infer_task_id(input_path: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    parts = list(input_path.resolve().parts)
    for part in reversed(parts):
        if re.match(r"^(train|test)_\d+$", part):
            return part
    return input_path.parent.name


def load_task(input_path: Path, task_id: str | None) -> tuple[str, str, int | None, dict[str, Any], str]:
    prompt = (input_path / "prompt.txt").read_text()
    memo = (input_path / "payloads" / "request_memo.md").read_text()
    template = json.loads((input_path / "payloads" / "answer_template.json").read_text())
    text = prompt + "\n" + memo

    client_match = re.search(r"Client ID:\s*(CLT-[0-9]+)", text)
    if not client_match:
        client_match = re.search(r"client\s+(CLT-[0-9]+)", text, re.IGNORECASE)
    if not client_match:
        raise SystemExit("Could not infer client_id")

    horizon_match = re.search(r"Planning horizon year:\s*(\d{4})", text)
    horizon = int(horizon_match.group(1)) if horizon_match else None

    analysis_field = template.get("fields", {}).get("analysis_type", "")
    analysis_match = re.search(r"enum:\s*([a-z_]+)", analysis_field)
    if not analysis_match:
        raise SystemExit("Could not infer analysis_type")

    return (
        infer_task_id(input_path, task_id),
        client_match.group(1),
        horizon,
        template,
        analysis_match.group(1),
    )


def priority_score(value: str | None) -> int:
    return {"low": 1, "moderate": 2, "high": 3}.get(str(value).lower(), 0)


def exemption_used(profile: dict[str, Any], tax_policy: dict[str, Any]) -> float:
    year = str(profile["planning_year"])
    base = tax_policy["estate_tax_exemption"][year]
    return base * (2 if profile.get("marital_status") == "married" else 1)


def estate_context(profile: dict[str, Any], tax_policy: dict[str, Any]) -> dict[str, Any]:
    used = exemption_used(profile, tax_policy)
    taxable = max(float(profile["estate_value"]) - used, 0)
    exposure = taxable * float(tax_policy["estate_tax_rate"])
    liquid = float(profile["liquid_assets"])
    return {
        "planning_year": int(profile["planning_year"]),
        "exemption_used": money(used),
        "taxable_estate": money(taxable),
        "estate_tax_exposure": money(exposure),
        "liquid_assets_available": money(liquid),
        "liquidity_gap_before_planning": money(max(exposure - liquid, 0)),
    }


def project_rmd(
    *,
    profile: dict[str, Any],
    account: dict[str, Any],
    rmd_factors: dict[str, float],
    horizon: int,
    annual_conversion: float = 0,
    conversion_years: int = 0,
) -> tuple[float, float, float]:
    traditional = float(account["traditional_balance"])
    roth = float(account.get("roth_balance", 0))
    expected_return = float(account["expected_return"])
    tax_rate = float(profile["marginal_tax_rate"])
    planning_year = int(profile["planning_year"])
    age = int(profile["age"])
    rmd_start_age = int(account["rmd_start_age"])
    rmd_tax = 0.0

    for year in range(planning_year, horizon + 1):
        current_age = age + (year - planning_year)
        if year < planning_year + conversion_years and annual_conversion > 0:
            amount = min(annual_conversion, traditional)
            traditional -= amount
            roth += amount
        if current_age >= rmd_start_age:
            factor = float(rmd_factors[str(current_age)])
            rmd = traditional / factor
            rmd_tax += rmd * tax_rate
            traditional -= rmd
        traditional *= 1 + expected_return
        roth *= 1 + expected_return

    return rmd_tax, traditional, roth


def roth_conversion_rmd(
    task_id: str,
    client_id: str,
    horizon: int,
    profile: dict[str, Any],
    account: dict[str, Any],
    tax_policy: dict[str, Any],
    rmd_factors: dict[str, float],
) -> dict[str, Any]:
    planning_year = int(profile["planning_year"])
    annual = max(
        float(tax_policy["conversion_bracket_targets"][profile["filing_status"]])
        - float(profile["annual_non_ira_income"]),
        0,
    )
    years = int(account["recommended_conversion_years"])
    positive_years = years if annual > 0 else 0
    total_converted = annual * positive_years
    baseline_tax, _, _ = project_rmd(
        profile=profile, account=account, rmd_factors=rmd_factors, horizon=horizon
    )
    conversion_tax, traditional_horizon, roth_horizon = project_rmd(
        profile=profile,
        account=account,
        rmd_factors=rmd_factors,
        horizon=horizon,
        annual_conversion=annual,
        conversion_years=positive_years,
    )
    first_rmd_year = planning_year + max(int(account["rmd_start_age"]) - int(profile["age"]), 0)

    if roth_horizon > 0 and traditional_horizon > 0:
        heir_profile = "MIXED_TAXABLE_AND_TAX_FREE"
    elif roth_horizon > 0:
        heir_profile = "MOSTLY_TAX_FREE"
    else:
        heir_profile = "MOSTLY_TAXABLE"

    return {
        "task_id": task_id,
        "client_id": client_id,
        "analysis_type": "roth_conversion_rmd",
        "recommendation": {
            "primary_action": "STAGED_ROTH_CONVERSION" if annual > 0 else "DEFER",
            "suitability": "SUITABLE" if annual > 0 else "DEFER",
            "risk_flag": "TAX_BRACKET_MANAGEMENT"
            if annual > 0
            else "LIQUIDITY_CONSTRAINT",
        },
        "conversion_plan": {
            "first_conversion_year": planning_year,
            "conversion_years": years,
            "conversion_years_positive": positive_years,
            "annual_conversion_amount": money(annual),
            "total_converted": money(total_converted),
            "total_conversion_tax": money(total_converted * float(profile["marginal_tax_rate"])),
        },
        "rmd_projection": {
            "horizon_year": horizon,
            "first_rmd_year": first_rmd_year,
            "baseline_rmd_tax_through_horizon": money(baseline_tax),
            "conversion_rmd_tax_through_horizon": money(conversion_tax),
            "rmd_tax_savings_through_horizon": money(baseline_tax - conversion_tax),
        },
        "legacy_projection": {
            "projected_roth_balance_horizon": money(roth_horizon),
            "projected_traditional_balance_horizon": money(traditional_horizon),
            "heir_tax_profile": heir_profile,
        },
        "source_resolution": {
            "controlling_profile_source": SOURCE_PROFILE,
            "controlling_account_source": SOURCE_ACCOUNT,
        },
    }


def ilit_values(
    profile: dict[str, Any],
    policy: dict[str, Any],
    tax_policy: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], str, str, str]:
    year = int(profile["planning_year"])
    exclusion = float(tax_policy["annual_gift_exclusion"][str(year)])
    beneficiaries = int(profile["beneficiary_count"])
    capacity = exclusion * beneficiaries
    premium = float(policy["annual_premium"])
    gap = max(premium - capacity, 0)
    transfer = bool(policy.get("is_existing_policy_transfer"))

    if transfer and gap > 0:
        risk = "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL"
        action = "DISCLOSE_LOOKBACK_AND_USE_EXEMPTION"
        suitability = "NOT_SUITABLE"
    elif transfer:
        risk = "THREE_YEAR_LOOKBACK"
        action = "USE_NEW_POLICY_OR_ACCEPT_LOOKBACK"
        suitability = "BORDERLINE"
    elif gap > 0:
        risk = "EXCLUSION_SHORTFALL"
        action = "USE_LIFETIME_EXEMPTION_FOR_SHORTFALL"
        suitability = "BORDERLINE"
    else:
        risk = "LOW_IF_FORMALITIES_MET"
        action = "FUND_WITH_CRUMMEY_NOTICES"
        suitability = "SUITABLE_WITH_ADMINISTRATION"

    contribution = date.fromisoformat(policy["planned_contribution_date"])
    notice_due = contribution + timedelta(days=7)
    withdrawal_end = notice_due + timedelta(days=30)
    administration = {
        "notices_required": beneficiaries,
        "contribution_date": contribution.isoformat(),
        "notice_due_date": notice_due.isoformat(),
        "withdrawal_window_end": withdrawal_end.isoformat(),
        "earliest_premium_payment_date": (withdrawal_end + timedelta(days=1)).isoformat(),
        "dedicated_bank_account_required": policy.get("proposed_owner") == "ILIT",
    }
    gift_plan = {
        "planning_year": year,
        "annual_exclusion_per_beneficiary": money(exclusion),
        "beneficiary_count": beneficiaries,
        "annual_exclusion_capacity": money(capacity),
        "annual_premium": money(premium),
        "premium_gap": money(gap),
    }
    return gift_plan, administration, risk, action, suitability


def ilit_crummey(
    task_id: str,
    client_id: str,
    profile: dict[str, Any],
    policy: dict[str, Any],
    tax_policy: dict[str, Any],
) -> dict[str, Any]:
    gift_plan, administration, risk, action, suitability = ilit_values(
        profile, policy, tax_policy
    )
    death_benefit = float(policy["death_benefit"])
    return {
        "task_id": task_id,
        "client_id": client_id,
        "analysis_type": "ilit_crummey_implementation",
        "recommendation": {
            "primary_action": action,
            "suitability": suitability,
            "risk_flag": risk,
        },
        "gift_plan": gift_plan,
        "administration": administration,
        "estate_result": {
            "death_benefit": money(death_benefit),
            "estate_inclusion_risk": risk,
            "projected_outside_estate_if_implemented": money(death_benefit),
            "tax_liquidity_support": money(death_benefit * float(tax_policy["estate_tax_rate"])),
        },
        "source_resolution": {
            "controlling_beneficiary_source": SOURCE_PROFILE,
            "controlling_policy_source": SOURCE_POLICY,
        },
    }


def trust_values(
    trust: dict[str, Any],
    profile: dict[str, Any],
    tax_policy: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], str, str, str]:
    asset = float(trust["asset_value"])
    growth = float(trust["expected_growth_rate"])
    grat_years = int(trust["grat_term_years"])
    crat_years = int(trust["crat_term_years"])

    grat_remainder = asset * (1 + growth) ** grat_years - asset * float(trust["grat_annuity_rate"]) * grat_years
    crat_remainder = asset * (1 + growth) ** crat_years - asset * float(trust["crat_payout_rate"]) * crat_years
    family_score = priority_score(profile.get("family_transfer_priority"))
    philanthropy_score = priority_score(profile.get("philanthropic_intent"))

    if philanthropy_score > family_score and philanthropy_score >= 3:
        preferred = "CRAT"
        rationale = "PHILANTHROPIC_PRIORITY"
        alternate = "SECONDARY_FAMILY_TRANSFER_TOOL"
    else:
        preferred = "GRAT"
        rationale = "CHILDREN_TRANSFER_PRIORITY"
        alternate = "SECONDARY_CHARITABLE_TOOL"

    if preferred == "GRAT":
        family_fit = "LOW"
    elif family_score >= 3:
        family_fit = "HIGH"
    else:
        family_fit = "MODERATE"

    grat = {
        "term_years": grat_years,
        "projected_remainder_to_heirs": money(grat_remainder),
        "estimated_estate_tax_reduction": money(grat_remainder * float(tax_policy["estate_tax_rate"])),
        "mortality_inclusion_risk": "TERM_SURVIVAL_REQUIRED",
    }
    crat = {
        "term_years": crat_years,
        "projected_charitable_remainder": money(crat_remainder),
        "estimated_income_tax_deduction": money(
            crat_remainder * float(tax_policy["charitable_deduction_rate"])
        ),
        "family_transfer_fit": family_fit,
    }
    return grat, crat, preferred, rationale, alternate


def trust_comparison(
    task_id: str,
    client_id: str,
    profile: dict[str, Any],
    trust: dict[str, Any],
    tax_policy: dict[str, Any],
) -> dict[str, Any]:
    grat, crat, preferred, rationale, alternate = trust_values(trust, profile, tax_policy)
    return {
        "task_id": task_id,
        "client_id": client_id,
        "analysis_type": "trust_comparison",
        "recommendation": {
            "preferred_strategy": preferred,
            "rationale_code": rationale,
            "alternate_role": alternate,
        },
        "estate_context": estate_context(profile, tax_policy),
        "grat": grat,
        "crat": crat,
        "source_resolution": {
            "controlling_goal_source": SOURCE_PROFILE,
            "controlling_asset_source": SOURCE_ASSET,
        },
    }


def estate_liquidity_action_plan(
    task_id: str,
    client_id: str,
    profile: dict[str, Any],
    policy: dict[str, Any],
    trust: dict[str, Any],
    tax_policy: dict[str, Any],
) -> dict[str, Any]:
    gift_plan, _, ilit_risk, _, _ = ilit_values(profile, policy, tax_policy)
    grat, crat, preferred, _, _ = trust_values(trust, profile, tax_policy)
    death_benefit = float(policy["death_benefit"])
    trust_transfer = {
        "preferred_strategy": preferred,
        "projected_remainder_to_heirs": grat["projected_remainder_to_heirs"],
        "estimated_estate_tax_reduction": grat["estimated_estate_tax_reduction"],
        "projected_charitable_remainder": crat["projected_charitable_remainder"],
    }

    if preferred == "GRAT" and ilit_risk == "LOW_IF_FORMALITIES_MET":
        primary = "COMBINE_ILIT_AND_GRAT"
        sequencing = "ILIT_FIRST_THEN_GRAT"
    elif preferred == "CRAT":
        primary = "CRAT_WITH_LIQUIDITY_REVIEW"
        sequencing = "TRUST_DECISION_FIRST"
    else:
        primary = "ILIT_WITH_EXEMPTION_REVIEW"
        sequencing = "ILIT_FIRST_THEN_ATTORNEY_REVIEW"

    actions = {"ATTORNEY_DRAFT_REVIEW", "ILIT_CRUMMEY_NOTICE_CYCLE"}
    if preferred == "GRAT":
        actions.add("GRAT_FOR_APPRECIATING_SHARES")
    else:
        actions.add("CRAT_FOR_CHARITABLE_REMAINDER")
    if gift_plan["premium_gap"] > 0:
        actions.add("LIFETIME_EXEMPTION_ALLOCATION")

    return {
        "task_id": task_id,
        "client_id": client_id,
        "analysis_type": "estate_liquidity_action_plan",
        "recommendation": {
            "primary_action": primary,
            "sequencing": sequencing,
            "risk_flag": ilit_risk,
        },
        "estate_context": estate_context(profile, tax_policy),
        "ilit": {
            "annual_exclusion_capacity": gift_plan["annual_exclusion_capacity"],
            "premium_gap": gift_plan["premium_gap"],
            "estate_inclusion_risk": ilit_risk,
            "projected_outside_estate_if_implemented": money(death_benefit),
        },
        "trust_transfer": trust_transfer,
        "action_set": sorted(actions),
        "source_resolution": {
            "controlling_goal_source": SOURCE_PROFILE,
            "controlling_policy_source": SOURCE_POLICY,
        },
    }


def prune_to_template(answer: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    required = template.get("required_top_level_keys", [])
    if not required:
        return answer
    return {key: answer[key] for key in required if key in answer}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path", type=Path)
    parser.add_argument("--api-base", default=os.environ.get("API_BASE"))
    parser.add_argument("--task-id")
    parser.add_argument("--no-prune", action="store_true")
    args = parser.parse_args()

    if not args.api_base:
        raise SystemExit("Pass --api-base or set API_BASE")

    task_id, client_id, horizon, template, analysis_type = load_task(args.input_path, args.task_id)

    client = fetch_json(args.api_base, f"/api/clients/{client_id}")
    source_docs = fetch_json(args.api_base, "/api/source-documents")
    tax_policy = fetch_json(args.api_base, "/api/policies/tax")
    rmd_factors = fetch_json(args.api_base, "/api/rmd-factors")
    account = one_for_client(fetch_json(args.api_base, "/api/retirement-accounts"), client_id)
    policy = one_for_client(fetch_json(args.api_base, "/api/life-insurance"), client_id)
    trust = one_for_client(fetch_json(args.api_base, "/api/trust-candidates"), client_id)
    profile = signed_profile(source_docs, client)

    if analysis_type == "roth_conversion_rmd":
        if horizon is None:
            raise SystemExit("Roth/RMD tasks require a planning horizon year in the memo")
        answer = roth_conversion_rmd(
            task_id, client_id, horizon, profile, account, tax_policy, rmd_factors
        )
    elif analysis_type == "ilit_crummey_implementation":
        answer = ilit_crummey(task_id, client_id, profile, policy, tax_policy)
    elif analysis_type == "trust_comparison":
        answer = trust_comparison(task_id, client_id, profile, trust, tax_policy)
    elif analysis_type == "estate_liquidity_action_plan":
        answer = estate_liquidity_action_plan(
            task_id, client_id, profile, policy, trust, tax_policy
        )
    else:
        raise SystemExit(f"Unsupported analysis_type: {analysis_type}")

    if not args.no_prune:
        answer = prune_to_template(answer, template)
    print(json.dumps(answer, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
