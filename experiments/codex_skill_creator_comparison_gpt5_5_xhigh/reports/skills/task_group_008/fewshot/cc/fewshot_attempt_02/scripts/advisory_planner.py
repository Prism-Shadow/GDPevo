#!/usr/bin/env python3
"""Generate private-wealth advisory planning JSON from the task API."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import urlopen


SOURCE_PRIORITY = {
    "SIGNED_PROFILE": 50,
    "ATTORNEY_MEMO": 40,
    "CUSTODIAN_EXPORT": 30,
    "CRM_NOTE": 20,
    "STALE_MARKETING_INTAKE": 10,
}


def money(value: float) -> float:
    return round(float(value) + 1e-12, 2)


def http_get_json(api_base: str, path: str) -> Any:
    url = urljoin(api_base.rstrip("/") + "/", path.lstrip("/"))
    try:
        with urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        raise SystemExit(f"HTTP error for {url}: {exc.code} {exc.reason}") from exc
    except URLError as exc:
        raise SystemExit(f"Network error for {url}: {exc.reason}") from exc


def pick_client_item(items: list[dict[str, Any]], client_id: str) -> dict[str, Any]:
    for item in items:
        if item.get("client_id") == client_id:
            return item
    raise SystemExit(f"No record found for client_id={client_id}")


def filter_client_items(items: list[dict[str, Any]], client_id: str) -> list[dict[str, Any]]:
    return [item for item in items if item.get("client_id") == client_id]


def source_rank(source_type: str | None) -> int:
    return SOURCE_PRIORITY.get(source_type or "", 0)


def parse_iso_date(text: str) -> date:
    return date.fromisoformat(text)


def choose_source(records: list[dict[str, Any]], fact_keys: set[str], default: str) -> str:
    best: dict[str, Any] | None = None
    for record in records:
        facts = record.get("facts", {})
        if not fact_keys.intersection(facts):
            continue
        if best is None:
            best = record
            continue
        best_rank = source_rank(best.get("source_type"))
        rank = source_rank(record.get("source_type"))
        if rank > best_rank:
            best = record
            continue
        if rank == best_rank:
            best_date = best.get("effective_date", "")
            date_value = record.get("effective_date", "")
            if date_value > best_date:
                best = record
    return best.get("source_type", default) if best else default


def select_fact_value(records: list[dict[str, Any]], fact_key: str, default: Any = None) -> Any:
    best_value = default
    best_record: dict[str, Any] | None = None
    for record in records:
        facts = record.get("facts", {})
        if fact_key not in facts:
            continue
        if best_record is None:
            best_record = record
            best_value = facts[fact_key]
            continue
        best_rank = source_rank(best_record.get("source_type"))
        rank = source_rank(record.get("source_type"))
        if rank > best_rank:
            best_record = record
            best_value = facts[fact_key]
            continue
        if rank == best_rank:
            best_date = best_record.get("effective_date", "")
            date_value = record.get("effective_date", "")
            if date_value > best_date:
                best_record = record
                best_value = facts[fact_key]
    return best_value


def load_context(api_base: str, client_id: str) -> dict[str, Any]:
    client = http_get_json(api_base, f"/api/clients/{client_id}")
    source_docs = filter_client_items(http_get_json(api_base, "/api/source-documents"), client_id)
    retirement_accounts = filter_client_items(http_get_json(api_base, "/api/retirement-accounts"), client_id)
    life_insurance = filter_client_items(http_get_json(api_base, "/api/life-insurance"), client_id)
    trust_candidates = filter_client_items(http_get_json(api_base, "/api/trust-candidates"), client_id)
    tax_policies = http_get_json(api_base, "/api/policies/tax")
    rmd_factors = http_get_json(api_base, "/api/rmd-factors")

    retirement = pick_client_item(retirement_accounts, client_id)
    life = pick_client_item(life_insurance, client_id)
    trust = pick_client_item(trust_candidates, client_id)

    return {
        "client": client,
        "source_docs": source_docs,
        "retirement": retirement,
        "life": life,
        "trust": trust,
        "tax": tax_policies,
        "rmd_factors": {int(k): float(v) for k, v in rmd_factors.items()},
    }


def first_matching_number(texts: list[str], patterns: list[str]) -> int | None:
    for text in texts:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return int(match.group(1))
    return None


def extract_client_id(*texts: str) -> str | None:
    for text in texts:
        match = re.search(r"\bCLT-\d{4}\b", text)
        if match:
            return match.group(0)
    return None


def extract_task_id(*texts: str) -> str | None:
    for text in texts:
        match = re.search(r"\b(?:train|test)_\d{3,4}\b", text)
        if match:
            return match.group(0)
    return None


def infer_analysis_type(template: dict[str, Any]) -> str:
    required = set(template.get("required_top_level_keys", []))
    fields = template.get("fields", {})
    if "conversion_plan" in required and "rmd_projection" in required:
        return "roth_conversion_rmd"
    if "gift_plan" in required and "administration" in required:
        return "ilit_crummey_implementation"
    if "grat" in required and "crat" in required and "trust_transfer" not in required:
        return "trust_comparison"
    if "action_set" in required and "trust_transfer" in required:
        return "estate_liquidity_action_plan"
    analysis_schema = fields.get("analysis_type", "")
    match = re.search(r"enum:\s*([a-zA-Z0-9_]+)", analysis_schema)
    if match:
        return match.group(1)
    raise SystemExit("Unable to infer analysis type from template")


def get_policy_value(policies: dict[str, Any], category: str, year: int) -> float:
    values = policies.get(category, {})
    if str(year) in values:
        return float(values[str(year)])
    years = sorted(int(k) for k in values)
    chosen = max((y for y in years if y <= year), default=years[-1] if years else None)
    if chosen is None:
        raise SystemExit(f"Missing policy value for {category}")
    return float(values[str(chosen)])


def round_date(d: date) -> str:
    return d.isoformat()


def simulate_rmd(
    opening_traditional: float,
    opening_roth: float,
    expected_return: float,
    start_age: int,
    current_age: int,
    planning_year: int,
    horizon_year: int,
    conversion_amount: float = 0.0,
    conversion_years: int = 0,
    rmd_factors: dict[int, float] | None = None,
    marginal_tax_rate: float = 0.0,
) -> dict[str, Any]:
    trad = float(opening_traditional)
    roth = float(opening_roth)
    rmd_tax = 0.0
    for year in range(planning_year, horizon_year + 1):
        age = current_age + (year - planning_year)
        if conversion_years and conversion_amount > 0 and year < planning_year + conversion_years:
            conv = min(conversion_amount, trad)
            trad -= conv
            roth += conv
        if age >= start_age:
            if rmd_factors is None or age not in rmd_factors:
                raise SystemExit(f"Missing RMD factor for age {age}")
            rmd = trad / rmd_factors[age]
            rmd_tax += rmd * marginal_tax_rate
            trad -= rmd
        trad *= 1 + expected_return
        roth *= 1 + expected_return
    return {
        "rmd_tax": rmd_tax,
        "traditional_balance": trad,
        "roth_balance": roth,
    }


def build_roth_output(ctx: dict[str, Any], template: dict[str, Any], task_id: str, memo_text: str, prompt_text: str) -> dict[str, Any]:
    profile = ctx["client"]
    retirement = ctx["retirement"]
    tax = ctx["tax"]
    docs = ctx["source_docs"]
    planning_year = int(profile["planning_year"])
    horizon_year = first_matching_number(
        [memo_text, prompt_text],
        [r"Planning horizon year:\s*(\d{4})", r"horizon through\s*(\d{4})"],
    ) or planning_year + 20
    filing_status = profile["filing_status"]
    annual_income = float(select_fact_value(docs, "annual_non_ira_income", profile.get("annual_non_ira_income", 0.0)))
    marginal_tax_rate = float(select_fact_value(docs, "marginal_tax_rate", 0.0))
    if marginal_tax_rate == 0.0:
        raise SystemExit("Missing marginal tax rate in source documents")
    target_bracket = float(tax["conversion_bracket_targets"][filing_status])
    capacity = max(target_bracket - annual_income, 0.0)
    recommended_years = int(retirement.get("recommended_conversion_years", 0))
    traditional_balance = float(retirement["traditional_balance"])
    roth_balance = float(retirement.get("roth_balance", 0.0))
    rmd_start_age = int(retirement.get("rmd_start_age", 73))
    age = int(profile["age"])
    first_rmd_year = planning_year if age >= rmd_start_age else planning_year + (rmd_start_age - age)
    conversion_years = recommended_years if capacity > 0 and recommended_years > 0 else 0
    annual_conversion_amount = 0.0
    if conversion_years > 0:
        annual_conversion_amount = min(capacity, traditional_balance / conversion_years)
    total_converted = annual_conversion_amount * conversion_years
    total_conversion_tax = total_converted * marginal_tax_rate

    baseline = simulate_rmd(
        opening_traditional=traditional_balance,
        opening_roth=roth_balance,
        expected_return=float(retirement["expected_return"]),
        start_age=rmd_start_age,
        current_age=age,
        planning_year=planning_year,
        horizon_year=horizon_year,
        rmd_factors=ctx["rmd_factors"],
        marginal_tax_rate=marginal_tax_rate,
    )
    with_conversion = simulate_rmd(
        opening_traditional=traditional_balance,
        opening_roth=roth_balance,
        expected_return=float(retirement["expected_return"]),
        start_age=rmd_start_age,
        current_age=age,
        planning_year=planning_year,
        horizon_year=horizon_year,
        conversion_amount=annual_conversion_amount,
        conversion_years=conversion_years,
        rmd_factors=ctx["rmd_factors"],
        marginal_tax_rate=marginal_tax_rate,
    )
    savings = baseline["rmd_tax"] - with_conversion["rmd_tax"]
    liquid_assets = float(profile.get("liquid_assets", 0.0))

    if total_converted <= 0 or savings <= 0:
        primary_action = "NO_CONVERSION"
        suitability = "DEFER"
        risk_flag = "RMD_NEAR_TERM" if first_rmd_year <= planning_year else "TAX_BRACKET_MANAGEMENT"
    elif total_conversion_tax > liquid_assets:
        primary_action = "DEFER"
        suitability = "BORDERLINE"
        risk_flag = "LIQUIDITY_CONSTRAINT"
    else:
        primary_action = "STAGED_ROTH_CONVERSION"
        suitability = "SUITABLE"
        risk_flag = "TAX_BRACKET_MANAGEMENT"

    tax_free_ratio = 0.0
    total_legacy = with_conversion["traditional_balance"] + with_conversion["roth_balance"]
    if total_legacy > 0:
        tax_free_ratio = with_conversion["roth_balance"] / total_legacy
    if tax_free_ratio >= 0.75:
        heir_tax_profile = "MOSTLY_TAX_FREE"
    elif tax_free_ratio <= 0.25:
        heir_tax_profile = "MOSTLY_TAXABLE"
    else:
        heir_tax_profile = "MIXED_TAXABLE_AND_TAX_FREE"

    profile_source = choose_source(
        docs,
        {"annual_non_ira_income", "marginal_tax_rate", "beneficiary_count", "philanthropic_intent", "family_transfer_priority"},
        "SIGNED_PROFILE",
    )
    account_source = retirement.get("source_type", "CUSTODIAN_EXPORT")

    return {
        "task_id": task_id,
        "client_id": profile["client_id"],
        "analysis_type": "roth_conversion_rmd",
        "recommendation": {
            "primary_action": primary_action,
            "suitability": suitability,
            "risk_flag": risk_flag,
        },
        "conversion_plan": {
            "first_conversion_year": planning_year,
            "conversion_years": conversion_years,
            "conversion_years_positive": conversion_years if conversion_years > 0 else 0,
            "annual_conversion_amount": money(annual_conversion_amount),
            "total_converted": money(total_converted),
            "total_conversion_tax": money(total_conversion_tax),
        },
        "rmd_projection": {
            "horizon_year": horizon_year,
            "first_rmd_year": first_rmd_year,
            "baseline_rmd_tax_through_horizon": money(baseline["rmd_tax"]),
            "conversion_rmd_tax_through_horizon": money(with_conversion["rmd_tax"]),
            "rmd_tax_savings_through_horizon": money(savings),
        },
        "legacy_projection": {
            "projected_roth_balance_horizon": money(with_conversion["roth_balance"]),
            "projected_traditional_balance_horizon": money(with_conversion["traditional_balance"]),
            "heir_tax_profile": heir_tax_profile,
        },
        "source_resolution": {
            "controlling_profile_source": profile_source,
            "controlling_account_source": account_source,
        },
    }


def build_ilit_output(ctx: dict[str, Any], task_id: str) -> dict[str, Any]:
    profile = ctx["client"]
    life = ctx["life"]
    tax = ctx["tax"]
    docs = ctx["source_docs"]
    planning_year = int(profile["planning_year"])
    annual_exclusion = get_policy_value(tax, "annual_gift_exclusion", planning_year)
    contribution_date = parse_iso_date(life["planned_contribution_date"])
    beneficiary_count = select_fact_value(docs, "beneficiary_count", None)
    if beneficiary_count is None:
        raise SystemExit("Missing beneficiary count in source documents")
    beneficiary_count = int(beneficiary_count)
    annual_capacity = annual_exclusion * beneficiary_count
    annual_premium = float(life["annual_premium"])
    premium_gap = max(annual_premium - annual_capacity, 0.0)
    if life.get("is_existing_policy_transfer"):
        if premium_gap > 0:
            risk_flag = "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL"
            primary_action = "DISCLOSE_LOOKBACK_AND_USE_EXEMPTION"
            suitability = "NOT_SUITABLE"
        else:
            risk_flag = "THREE_YEAR_LOOKBACK"
            primary_action = "USE_NEW_POLICY_OR_ACCEPT_LOOKBACK"
            suitability = "BORDERLINE"
    elif premium_gap > 0:
        risk_flag = "EXCLUSION_SHORTFALL"
        primary_action = "USE_LIFETIME_EXEMPTION_FOR_SHORTFALL"
        suitability = "BORDERLINE"
    else:
        risk_flag = "LOW_IF_FORMALITIES_MET"
        primary_action = "FUND_WITH_CRUMMEY_NOTICES"
        suitability = "SUITABLE_WITH_ADMINISTRATION"
    notice_due = contribution_date + timedelta(days=7)
    withdrawal_window_end = notice_due + timedelta(days=30)
    earliest_payment = withdrawal_window_end + timedelta(days=1)
    profile_source = choose_source(
        docs,
        {"beneficiary_count", "annual_non_ira_income", "marginal_tax_rate", "family_transfer_priority", "philanthropic_intent"},
        "SIGNED_PROFILE",
    )
    policy_source = life.get("source_type", "SIGNED_PROFILE")
    death_benefit = float(life["death_benefit"])
    estate_inclusion_risk = risk_flag
    projected_outside_estate = death_benefit if risk_flag == "LOW_IF_FORMALITIES_MET" else 0.0
    tax_liquidity_support = death_benefit * float(tax["estate_tax_rate"])
    return {
        "task_id": task_id,
        "client_id": profile["client_id"],
        "analysis_type": "ilit_crummey_implementation",
        "recommendation": {
            "primary_action": primary_action,
            "suitability": suitability,
            "risk_flag": risk_flag,
        },
        "gift_plan": {
            "planning_year": planning_year,
            "annual_exclusion_per_beneficiary": money(annual_exclusion),
            "beneficiary_count": beneficiary_count,
            "annual_exclusion_capacity": money(annual_capacity),
            "annual_premium": money(annual_premium),
            "premium_gap": money(premium_gap),
        },
        "administration": {
            "notices_required": beneficiary_count,
            "contribution_date": round_date(contribution_date),
            "notice_due_date": round_date(notice_due),
            "withdrawal_window_end": round_date(withdrawal_window_end),
            "earliest_premium_payment_date": round_date(earliest_payment),
            "dedicated_bank_account_required": True,
        },
        "estate_result": {
            "death_benefit": money(death_benefit),
            "estate_inclusion_risk": estate_inclusion_risk,
            "projected_outside_estate_if_implemented": money(projected_outside_estate),
            "tax_liquidity_support": money(tax_liquidity_support),
        },
        "source_resolution": {
            "controlling_beneficiary_source": profile_source,
            "controlling_policy_source": policy_source,
        },
    }


def build_trust_comparison(ctx: dict[str, Any], task_id: str) -> dict[str, Any]:
    profile = ctx["client"]
    tax = ctx["tax"]
    trust = ctx["trust"]
    docs = ctx["source_docs"]
    planning_year = int(profile["planning_year"])
    family_priority = {"low": 1, "moderate": 2, "high": 3}.get(
        str(select_fact_value(docs, "family_transfer_priority", "moderate")).lower(),
        0,
    )
    philanthropic = {"low": 1, "moderate": 2, "high": 3}.get(
        str(select_fact_value(docs, "philanthropic_intent", "moderate")).lower(),
        0,
    )
    preferred_strategy = "GRAT" if family_priority >= philanthropic else "CRAT"
    rationale_code = "CHILDREN_TRANSFER_PRIORITY" if preferred_strategy == "GRAT" else "PHILANTHROPIC_PRIORITY"
    alternate_role = "SECONDARY_CHARITABLE_TOOL" if preferred_strategy == "GRAT" else "SECONDARY_FAMILY_TRANSFER_TOOL"
    taxable_estate = float(profile["estate_value"])
    exemption_used = get_policy_value(tax, "estate_tax_exemption", planning_year) * (2 if profile.get("filing_status") == "MFJ" or profile.get("marital_status") == "married" else 1)
    estate_tax_exposure = max(taxable_estate - exemption_used, 0.0) * float(tax["estate_tax_rate"])
    liquid_assets = float(profile.get("liquid_assets", 0.0))
    liquidity_gap = max(estate_tax_exposure - liquid_assets, 0.0)
    asset_value = float(trust["asset_value"])
    growth = float(trust["expected_growth_rate"])
    grat_term = int(trust["grat_term_years"])
    crat_term = min(int(trust["crat_term_years"]), int(tax["max_crat_term_years"]))
    grat_annuity = float(trust["grat_annuity_rate"])
    crat_payout = float(trust["crat_payout_rate"])
    grat_remainder = max(asset_value * ((1 + growth) ** grat_term - grat_annuity * grat_term), 0.0)
    crat_remainder = max(asset_value * ((1 + growth) ** crat_term - crat_payout * crat_term), 0.0)
    deduction = crat_remainder * float(tax["charitable_deduction_rate"])
    family_fit = "LOW" if family_priority >= 3 else "MODERATE" if family_priority == 2 else "HIGH"
    return {
        "task_id": task_id,
        "client_id": profile["client_id"],
        "analysis_type": "trust_comparison",
        "recommendation": {
            "preferred_strategy": preferred_strategy,
            "rationale_code": rationale_code,
            "alternate_role": alternate_role,
        },
        "estate_context": {
            "planning_year": planning_year,
            "exemption_used": money(exemption_used),
            "taxable_estate": money(taxable_estate - exemption_used),
            "estate_tax_exposure": money(estate_tax_exposure),
            "liquid_assets_available": money(liquid_assets),
            "liquidity_gap_before_planning": money(liquidity_gap),
        },
        "grat": {
            "term_years": grat_term,
            "projected_remainder_to_heirs": money(grat_remainder),
            "estimated_estate_tax_reduction": money(grat_remainder * float(tax["estate_tax_rate"])),
            "mortality_inclusion_risk": "TERM_SURVIVAL_REQUIRED",
        },
        "crat": {
            "term_years": crat_term,
            "projected_charitable_remainder": money(crat_remainder),
            "estimated_income_tax_deduction": money(deduction),
            "family_transfer_fit": family_fit,
        },
        "source_resolution": {
            "controlling_goal_source": choose_source(
                docs,
                {"family_transfer_priority", "philanthropic_intent"},
                "SIGNED_PROFILE",
            ),
            "controlling_asset_source": trust.get("source_type", "ATTORNEY_MEMO"),
        },
    }


def build_estate_action_plan(ctx: dict[str, Any], task_id: str) -> dict[str, Any]:
    profile = ctx["client"]
    tax = ctx["tax"]
    life = ctx["life"]
    trust = ctx["trust"]
    docs = ctx["source_docs"]
    planning_year = int(profile["planning_year"])
    annual_exclusion = get_policy_value(tax, "annual_gift_exclusion", planning_year)
    contribution_date = parse_iso_date(life["planned_contribution_date"])
    beneficiary_count = select_fact_value(docs, "beneficiary_count", None)
    if beneficiary_count is None:
        raise SystemExit("Missing beneficiary count in source documents")
    beneficiary_count = int(beneficiary_count)
    annual_capacity = annual_exclusion * beneficiary_count
    premium_gap = max(float(life["annual_premium"]) - annual_capacity, 0.0)
    ilit_risk = "LOW_IF_FORMALITIES_MET"
    if life.get("is_existing_policy_transfer"):
        ilit_risk = "THREE_YEAR_LOOKBACK"
        if premium_gap > 0:
            ilit_risk = "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL"
    elif premium_gap > 0:
        ilit_risk = "EXCLUSION_SHORTFALL"

    taxable_estate = float(profile["estate_value"])
    exemption_used = get_policy_value(tax, "estate_tax_exemption", planning_year) * (2 if profile.get("filing_status") == "MFJ" or profile.get("marital_status") == "married" else 1)
    taxable_after_exemption = max(taxable_estate - exemption_used, 0.0)
    estate_tax_exposure = taxable_after_exemption * float(tax["estate_tax_rate"])
    liquid_assets = float(profile.get("liquid_assets", 0.0))
    liquidity_gap = max(estate_tax_exposure - liquid_assets, 0.0)

    asset_value = float(trust["asset_value"])
    growth = float(trust["expected_growth_rate"])
    grat_term = int(trust["grat_term_years"])
    crat_term = min(int(trust["crat_term_years"]), int(tax["max_crat_term_years"]))
    grat_annuity = float(trust["grat_annuity_rate"])
    crat_payout = float(trust["crat_payout_rate"])
    grat_remainder = max(asset_value * ((1 + growth) ** grat_term - grat_annuity * grat_term), 0.0)
    crat_remainder = max(asset_value * ((1 + growth) ** crat_term - crat_payout * crat_term), 0.0)

    family_priority = {"low": 1, "moderate": 2, "high": 3}.get(
        str(select_fact_value(docs, "family_transfer_priority", "moderate")).lower(),
        0,
    )
    philanthropic = {"low": 1, "moderate": 2, "high": 3}.get(
        str(select_fact_value(docs, "philanthropic_intent", "moderate")).lower(),
        0,
    )
    preferred_strategy = "GRAT" if family_priority >= philanthropic else "CRAT"

    if ilit_risk == "LOW_IF_FORMALITIES_MET" and preferred_strategy == "GRAT":
        primary_action = "COMBINE_ILIT_AND_GRAT"
        sequencing = "ILIT_FIRST_THEN_GRAT"
    elif preferred_strategy == "CRAT":
        primary_action = "CRAT_WITH_LIQUIDITY_REVIEW"
        sequencing = "TRUST_DECISION_FIRST"
    else:
        primary_action = "ILIT_WITH_EXEMPTION_REVIEW"
        sequencing = "ILIT_FIRST_THEN_ATTORNEY_REVIEW"

    action_set = ["ATTORNEY_DRAFT_REVIEW", "ILIT_CRUMMEY_NOTICE_CYCLE"]
    if primary_action == "COMBINE_ILIT_AND_GRAT" or primary_action == "ILIT_WITH_EXEMPTION_REVIEW":
        action_set.append("GRAT_FOR_APPRECIATING_SHARES")
    if preferred_strategy == "CRAT":
        action_set.append("CRAT_FOR_CHARITABLE_REMAINDER")
    if premium_gap > 0 or ilit_risk != "LOW_IF_FORMALITIES_MET":
        action_set.append("LIFETIME_EXEMPTION_ALLOCATION")
    action_set = sorted(dict.fromkeys(action_set))

    return {
        "task_id": task_id,
        "client_id": profile["client_id"],
        "analysis_type": "estate_liquidity_action_plan",
        "recommendation": {
            "primary_action": primary_action,
            "sequencing": sequencing,
            "risk_flag": ilit_risk,
        },
        "estate_context": {
            "planning_year": planning_year,
            "exemption_used": money(exemption_used),
            "taxable_estate": money(taxable_after_exemption),
            "estate_tax_exposure": money(estate_tax_exposure),
            "liquid_assets_available": money(liquid_assets),
            "liquidity_gap_before_planning": money(liquidity_gap),
        },
        "ilit": {
            "annual_exclusion_capacity": money(annual_capacity),
            "premium_gap": money(premium_gap),
            "estate_inclusion_risk": ilit_risk,
            "projected_outside_estate_if_implemented": money(float(life["death_benefit"]) if ilit_risk == "LOW_IF_FORMALITIES_MET" else 0.0),
        },
        "trust_transfer": {
            "preferred_strategy": preferred_strategy,
            "projected_remainder_to_heirs": money(grat_remainder),
            "estimated_estate_tax_reduction": money(grat_remainder * float(tax["estate_tax_rate"])),
            "projected_charitable_remainder": money(crat_remainder),
        },
        "action_set": action_set,
        "source_resolution": {
            "controlling_goal_source": choose_source(
                docs,
                {"family_transfer_priority", "philanthropic_intent"},
                "SIGNED_PROFILE",
            ),
            "controlling_policy_source": choose_source(
                docs,
                {"beneficiary_count", "annual_non_ira_income", "marginal_tax_rate"},
                "SIGNED_PROFILE",
            ),
        },
    }


def build_output(ctx: dict[str, Any], template: dict[str, Any], task_id: str, memo_text: str, prompt_text: str) -> dict[str, Any]:
    analysis_type = infer_analysis_type(template)
    if analysis_type == "roth_conversion_rmd":
        return build_roth_output(ctx, template, task_id, memo_text, prompt_text)
    if analysis_type == "ilit_crummey_implementation":
        return build_ilit_output(ctx, task_id)
    if analysis_type == "trust_comparison":
        return build_trust_comparison(ctx, task_id)
    if analysis_type == "estate_liquidity_action_plan":
        return build_estate_action_plan(ctx, task_id)
    raise SystemExit(f"Unsupported analysis type: {analysis_type}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default=os.environ.get("API_BASE", "http://task-env:9008/"))
    parser.add_argument("--client-id")
    parser.add_argument("--task-id")
    parser.add_argument("--template", required=True, help="Path to input/payloads/answer_template.json")
    parser.add_argument("--memo", help="Path to input/payloads/request_memo.md")
    parser.add_argument("--prompt", help="Path to the task prompt")
    args = parser.parse_args()

    template = json.loads(Path(args.template).read_text())
    memo_text = Path(args.memo).read_text() if args.memo else ""
    prompt_text = Path(args.prompt).read_text() if args.prompt else ""
    client_id = args.client_id or extract_client_id(memo_text, prompt_text)
    task_id = args.task_id or extract_task_id(memo_text, prompt_text)
    if not client_id:
        raise SystemExit("Missing client_id; pass --client-id or include it in the memo/prompt")
    if not task_id:
        task_id = "unknown_task"
    ctx = load_context(args.api_base, client_id)
    output = build_output(ctx, template, task_id, memo_text, prompt_text)
    json.dump(output, sys.stdout, indent=2, ensure_ascii=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
