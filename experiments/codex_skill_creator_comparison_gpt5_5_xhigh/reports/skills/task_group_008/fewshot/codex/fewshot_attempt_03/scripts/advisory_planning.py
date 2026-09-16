#!/usr/bin/env python3
"""Compute advisory planning JSON from the task memo, answer template, and API."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SOURCE_ORDER = {
    "SIGNED_PROFILE": 0,
    "ATTORNEY_MEMO": 1,
    "CUSTODIAN_EXPORT": 2,
    "CRM_NOTE": 3,
    "STALE_MARKETING_INTAKE": 4,
}

PRIORITY_SCORE = {"low": 1, "moderate": 2, "high": 3}


def money(value: float) -> float:
    rounded = round(float(value), 2)
    return 0.0 if rounded == -0.0 else rounded


def api_get(base_url: str, path: str, params: dict[str, str] | None = None):
    url = base_url.rstrip("/") + path
    if params:
        url += "?" + urlencode(params)
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def read_text(path: str | None) -> str:
    if not path:
        return ""
    return Path(path).read_text()


def parse_client_id(*texts: str) -> str | None:
    for text in texts:
        match = re.search(r"\bClient ID:\s*([A-Z]+-\d+)\b", text)
        if match:
            return match.group(1)
        match = re.search(r"\b(CLT-\d+)\b", text)
        if match:
            return match.group(1)
    return None


def parse_horizon(*texts: str) -> int | None:
    for text in texts:
        match = re.search(r"Planning horizon year:\s*(\d{4})", text)
        if match:
            return int(match.group(1))
    return None


def infer_task_id(*paths: str | None) -> str | None:
    pattern = re.compile(r"^(?:train|test)_\d+$")
    for raw_path in paths:
        if not raw_path:
            continue
        for part in reversed(Path(raw_path).resolve().parts):
            if pattern.match(part):
                return part
    cwd_name = Path.cwd().name
    return cwd_name if pattern.match(cwd_name) else None


def select_doc(docs: list[dict], key: str) -> tuple[object | None, str | None]:
    ordered = sorted(
        docs,
        key=lambda doc: (
            SOURCE_ORDER.get(doc.get("source_type", ""), 99),
            doc.get("effective_date", ""),
        ),
    )
    for doc in ordered:
        facts = doc.get("facts") or {}
        if key in facts:
            return facts[key], doc.get("source_type")
    return None, None


def fact(
    docs: list[dict],
    client: dict,
    key: str,
    default=None,
) -> tuple[object, str | None]:
    value, source = select_doc(docs, key)
    if value is not None:
        return value, source
    if key in client:
        return client[key], None
    return default, None


def policy_value(policy: dict, section: str, year: int) -> float:
    values = policy[section]
    if str(year) in values:
        return float(values[str(year)])
    eligible_years = sorted(int(candidate) for candidate in values if int(candidate) <= year)
    if eligible_years:
        return float(values[str(eligible_years[-1])])
    return float(values[str(sorted(int(candidate) for candidate in values)[0])])


def first_record(records: list[dict], label: str) -> dict:
    if not records:
        raise SystemExit(f"Missing {label} record for client")
    return records[0]


def context(args) -> dict:
    memo_text = read_text(args.memo)
    prompt_text = read_text(args.prompt)
    template = json.loads(Path(args.template).read_text())
    client_id = args.client_id or parse_client_id(memo_text, prompt_text)
    if not client_id:
        raise SystemExit("Could not infer client_id; pass --client-id")
    task_id = args.task_id or infer_task_id(args.memo, args.template, args.prompt)
    if not task_id:
        raise SystemExit("Could not infer task_id; pass --task-id")
    api_base = args.api_base or os.environ.get("API_BASE") or "http://task-env:9008/"

    client = api_get(api_base, f"/api/clients/{client_id}")
    docs = api_get(api_base, "/api/source-documents", {"client_id": client_id})
    retirement = api_get(api_base, "/api/retirement-accounts", {"client_id": client_id})
    life = api_get(api_base, "/api/life-insurance", {"client_id": client_id})
    trusts = api_get(api_base, "/api/trust-candidates", {"client_id": client_id})
    tax_policy = api_get(api_base, "/api/policies/tax")
    rmd_factors = {int(k): float(v) for k, v in api_get(api_base, "/api/rmd-factors").items()}

    return {
        "api_base": api_base,
        "task_id": task_id,
        "client_id": client_id,
        "memo": memo_text,
        "template": template,
        "client": client,
        "docs": docs,
        "retirement": retirement,
        "life": life,
        "trusts": trusts,
        "tax_policy": tax_policy,
        "rmd_factors": rmd_factors,
        "horizon": args.horizon or parse_horizon(memo_text, prompt_text),
    }


def analysis_type(template: dict) -> str:
    keys = set(template.get("required_top_level_keys") or [])
    if "conversion_plan" in keys:
        return "roth_conversion_rmd"
    if "gift_plan" in keys:
        return "ilit_crummey_implementation"
    if "action_set" in keys:
        return "estate_liquidity_action_plan"
    if "grat" in keys and "crat" in keys:
        return "trust_comparison"
    fields = template.get("fields") or {}
    raw = str(fields.get("analysis_type", ""))
    match = re.search(r"enum:\s*([a-z_]+)", raw)
    if match:
        return match.group(1)
    raise SystemExit("Could not determine analysis_type from template")


def profile(ctx: dict) -> dict:
    docs = ctx["docs"]
    client = ctx["client"]
    keys = [
        "annual_non_ira_income",
        "marginal_tax_rate",
        "beneficiary_count",
        "philanthropic_intent",
        "family_transfer_priority",
        "age",
        "planning_year",
        "filing_status",
        "marital_status",
        "liquid_assets",
        "estate_value",
    ]
    result = {}
    sources = {}
    for key in keys:
        value, source = fact(docs, client, key)
        result[key] = value
        if source:
            sources[key] = source
    return {"values": result, "sources": sources}


def rmd_tax(
    traditional_balance: float,
    age: int,
    planning_year: int,
    horizon_year: int,
    rmd_start_age: int,
    expected_return: float,
    marginal_tax_rate: float,
    rmd_factors: dict[int, float],
) -> tuple[float, float]:
    balance = float(traditional_balance)
    tax_total = 0.0
    for year in range(planning_year, horizon_year + 1):
        year_age = age + (year - planning_year)
        if year_age >= rmd_start_age:
            factor = rmd_factors[year_age]
            rmd = balance / factor
            balance -= rmd
            tax_total += rmd * marginal_tax_rate
        balance *= 1 + expected_return
    return tax_total, balance


def conversion_projection(
    account: dict,
    prof: dict,
    policy: dict,
    rmd_factors: dict[int, float],
    horizon_year: int,
) -> dict:
    age = int(prof["age"])
    planning_year = int(prof["planning_year"])
    filing_status = str(prof["filing_status"])
    income = float(prof["annual_non_ira_income"])
    marginal_rate = float(prof["marginal_tax_rate"])
    target = float(policy["conversion_bracket_targets"][filing_status])
    annual_amount = max(0.0, target - income)
    recommended_years = int(account.get("recommended_conversion_years", 0))
    first_rmd_year = planning_year + max(0, int(account["rmd_start_age"]) - age)

    traditional = float(account["traditional_balance"])
    roth = float(account.get("roth_balance", 0.0))
    expected_return = float(account["expected_return"])
    rmd_tax_total = 0.0
    total_converted = 0.0
    positive_years = 0

    for year in range(planning_year, horizon_year + 1):
        year_age = age + (year - planning_year)
        conversion = 0.0
        if year < planning_year + recommended_years and annual_amount > 0 and traditional > 0:
            conversion = min(annual_amount, traditional)
            traditional -= conversion
            roth += conversion
            total_converted += conversion
            if conversion > 0:
                positive_years += 1
        if year_age >= int(account["rmd_start_age"]):
            factor = rmd_factors[year_age]
            rmd = traditional / factor
            traditional -= rmd
            rmd_tax_total += rmd * marginal_rate
        traditional *= 1 + expected_return
        roth *= 1 + expected_return

    baseline_tax, _ = rmd_tax(
        float(account["traditional_balance"]),
        age,
        planning_year,
        horizon_year,
        int(account["rmd_start_age"]),
        expected_return,
        marginal_rate,
        rmd_factors,
    )

    savings = baseline_tax - rmd_tax_total
    liquid_assets = float(prof.get("liquid_assets") or 0.0)
    conversion_tax = total_converted * marginal_rate
    if total_converted <= 0:
        primary_action = "NO_CONVERSION"
        suitability = "DEFER"
        risk = "TAX_BRACKET_MANAGEMENT"
    elif conversion_tax > liquid_assets:
        primary_action = "STAGED_ROTH_CONVERSION"
        suitability = "BORDERLINE"
        risk = "LIQUIDITY_CONSTRAINT"
    elif savings <= 0:
        primary_action = "DEFER"
        suitability = "BORDERLINE"
        risk = "RMD_NEAR_TERM"
    else:
        primary_action = "STAGED_ROTH_CONVERSION"
        suitability = "SUITABLE"
        risk = "TAX_BRACKET_MANAGEMENT"

    if roth > 0 and traditional > 0:
        heir_profile = "MIXED_TAXABLE_AND_TAX_FREE"
    elif roth > 0:
        heir_profile = "MOSTLY_TAX_FREE"
    else:
        heir_profile = "MOSTLY_TAXABLE"

    return {
        "recommendation": {
            "primary_action": primary_action,
            "suitability": suitability,
            "risk_flag": risk,
        },
        "conversion_plan": {
            "first_conversion_year": planning_year,
            "conversion_years": recommended_years,
            "conversion_years_positive": positive_years,
            "annual_conversion_amount": money(annual_amount),
            "total_converted": money(total_converted),
            "total_conversion_tax": money(conversion_tax),
        },
        "rmd_projection": {
            "horizon_year": horizon_year,
            "first_rmd_year": first_rmd_year,
            "baseline_rmd_tax_through_horizon": money(baseline_tax),
            "conversion_rmd_tax_through_horizon": money(rmd_tax_total),
            "rmd_tax_savings_through_horizon": money(savings),
        },
        "legacy_projection": {
            "projected_roth_balance_horizon": money(roth),
            "projected_traditional_balance_horizon": money(traditional),
            "heir_tax_profile": heir_profile,
        },
    }


def ilit_values(life: dict, prof: dict, policy: dict) -> dict:
    planning_year = int(prof["planning_year"])
    beneficiary_count = int(prof["beneficiary_count"])
    exclusion = policy_value(policy, "annual_gift_exclusion", planning_year)
    annual_premium = float(life["annual_premium"])
    capacity = exclusion * beneficiary_count
    gap = max(0.0, annual_premium - capacity)
    transfer = bool(life.get("is_existing_policy_transfer", False))

    if transfer and gap > 0:
        risk = "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL"
        primary = "DISCLOSE_LOOKBACK_AND_USE_EXEMPTION"
        suitability = "NOT_SUITABLE"
    elif transfer:
        risk = "THREE_YEAR_LOOKBACK"
        primary = "USE_NEW_POLICY_OR_ACCEPT_LOOKBACK"
        suitability = "BORDERLINE"
    elif gap > 0:
        risk = "EXCLUSION_SHORTFALL"
        primary = "USE_LIFETIME_EXEMPTION_FOR_SHORTFALL"
        suitability = "BORDERLINE"
    else:
        risk = "LOW_IF_FORMALITIES_MET"
        primary = "FUND_WITH_CRUMMEY_NOTICES"
        suitability = "SUITABLE_WITH_ADMINISTRATION"

    contribution = date.fromisoformat(life["planned_contribution_date"])
    notice_due = contribution + timedelta(days=7)
    window_end = notice_due + timedelta(days=30)
    earliest_premium = window_end + timedelta(days=1)
    death_benefit = float(life["death_benefit"])

    return {
        "recommendation": {
            "primary_action": primary,
            "suitability": suitability,
            "risk_flag": risk,
        },
        "gift_plan": {
            "planning_year": planning_year,
            "annual_exclusion_per_beneficiary": money(exclusion),
            "beneficiary_count": beneficiary_count,
            "annual_exclusion_capacity": money(capacity),
            "annual_premium": money(annual_premium),
            "premium_gap": money(gap),
        },
        "administration": {
            "notices_required": beneficiary_count,
            "contribution_date": contribution.isoformat(),
            "notice_due_date": notice_due.isoformat(),
            "withdrawal_window_end": window_end.isoformat(),
            "earliest_premium_payment_date": earliest_premium.isoformat(),
            "dedicated_bank_account_required": True,
        },
        "estate_result": {
            "death_benefit": money(death_benefit),
            "estate_inclusion_risk": risk,
            "projected_outside_estate_if_implemented": money(death_benefit),
            "tax_liquidity_support": money(death_benefit * float(policy["estate_tax_rate"])),
        },
        "risk": risk,
        "premium_gap": gap,
        "capacity": capacity,
    }


def estate_context(prof: dict, policy: dict) -> dict:
    planning_year = int(prof["planning_year"])
    marital_status = str(prof.get("marital_status") or "").lower()
    filing_status = str(prof.get("filing_status") or "")
    multiplier = 2 if marital_status == "married" or filing_status == "MFJ" else 1
    exemption = policy_value(policy, "estate_tax_exemption", planning_year) * multiplier
    estate_value = float(prof["estate_value"])
    liquid_assets = float(prof["liquid_assets"])
    taxable = max(0.0, estate_value - exemption)
    exposure = taxable * float(policy["estate_tax_rate"])
    gap = max(0.0, exposure - liquid_assets)
    return {
        "planning_year": planning_year,
        "exemption_used": money(exemption),
        "taxable_estate": money(taxable),
        "estate_tax_exposure": money(exposure),
        "liquid_assets_available": money(liquid_assets),
        "liquidity_gap_before_planning": money(gap),
    }


def trust_values(trust: dict, prof: dict, policy: dict) -> dict:
    asset = float(trust["asset_value"])
    growth = float(trust["expected_growth_rate"])
    estate_rate = float(policy["estate_tax_rate"])
    grat_term = int(trust["grat_term_years"])
    crat_term = min(int(trust["crat_term_years"]), int(policy.get("max_crat_term_years", trust["crat_term_years"])))
    grat_remainder = asset * ((1 + growth) ** grat_term) - asset * float(trust["grat_annuity_rate"]) * grat_term
    crat_remainder = asset * ((1 + growth) ** crat_term) - asset * float(trust["crat_payout_rate"]) * crat_term

    family = str(prof.get("family_transfer_priority") or "moderate").lower()
    philanthropy = str(prof.get("philanthropic_intent") or "moderate").lower()
    family_score = PRIORITY_SCORE.get(family, 2)
    philanthropy_score = PRIORITY_SCORE.get(philanthropy, 2)
    prefer_grat = family_score >= philanthropy_score

    if prefer_grat:
        preferred = "GRAT"
        rationale = "CHILDREN_TRANSFER_PRIORITY"
        alternate = "SECONDARY_CHARITABLE_TOOL"
    else:
        preferred = "CRAT"
        rationale = "PHILANTHROPIC_PRIORITY"
        alternate = "SECONDARY_FAMILY_TRANSFER_TOOL"

    if prefer_grat:
        crat_fit = "LOW"
    elif family_score == philanthropy_score:
        crat_fit = "MODERATE"
    else:
        crat_fit = "MODERATE" if family_score >= 2 else "LOW"

    return {
        "recommendation": {
            "preferred_strategy": preferred,
            "rationale_code": rationale,
            "alternate_role": alternate,
        },
        "grat": {
            "term_years": grat_term,
            "projected_remainder_to_heirs": money(grat_remainder),
            "estimated_estate_tax_reduction": money(grat_remainder * estate_rate),
            "mortality_inclusion_risk": "TERM_SURVIVAL_REQUIRED",
        },
        "crat": {
            "term_years": crat_term,
            "projected_charitable_remainder": money(crat_remainder),
            "estimated_income_tax_deduction": money(crat_remainder * float(policy["charitable_deduction_rate"])),
            "family_transfer_fit": crat_fit,
        },
        "preferred_strategy": preferred,
        "grat_remainder": grat_remainder,
        "grat_tax_reduction": grat_remainder * estate_rate,
        "crat_remainder": crat_remainder,
    }


def solve_roth(ctx: dict) -> dict:
    prof_bundle = profile(ctx)
    prof = prof_bundle["values"]
    account = first_record(ctx["retirement"], "retirement account")
    horizon = ctx["horizon"]
    if horizon is None:
        raise SystemExit("Roth/RMD task requires a planning horizon year")
    values = conversion_projection(account, prof, ctx["tax_policy"], ctx["rmd_factors"], int(horizon))
    return {
        "task_id": ctx["task_id"],
        "client_id": ctx["client_id"],
        "analysis_type": "roth_conversion_rmd",
        **values,
        "source_resolution": {
            "controlling_profile_source": prof_bundle["sources"].get("annual_non_ira_income", "SIGNED_PROFILE"),
            "controlling_account_source": account.get("source_type", "CUSTODIAN_EXPORT"),
        },
    }


def solve_ilit(ctx: dict) -> dict:
    prof_bundle = profile(ctx)
    prof = prof_bundle["values"]
    life = first_record(ctx["life"], "life-insurance")
    values = ilit_values(life, prof, ctx["tax_policy"])
    return {
        "task_id": ctx["task_id"],
        "client_id": ctx["client_id"],
        "analysis_type": "ilit_crummey_implementation",
        "recommendation": values["recommendation"],
        "gift_plan": values["gift_plan"],
        "administration": values["administration"],
        "estate_result": values["estate_result"],
        "source_resolution": {
            "controlling_beneficiary_source": prof_bundle["sources"].get("beneficiary_count", "SIGNED_PROFILE"),
            "controlling_policy_source": life.get("source_type", "SIGNED_PROFILE"),
        },
    }


def solve_trust(ctx: dict) -> dict:
    prof_bundle = profile(ctx)
    prof = prof_bundle["values"]
    trust = first_record(ctx["trusts"], "trust candidate")
    values = trust_values(trust, prof, ctx["tax_policy"])
    return {
        "task_id": ctx["task_id"],
        "client_id": ctx["client_id"],
        "analysis_type": "trust_comparison",
        "recommendation": values["recommendation"],
        "estate_context": estate_context(prof, ctx["tax_policy"]),
        "grat": values["grat"],
        "crat": values["crat"],
        "source_resolution": {
            "controlling_goal_source": prof_bundle["sources"].get("family_transfer_priority", "SIGNED_PROFILE"),
            "controlling_asset_source": trust.get("source_type", "ATTORNEY_MEMO"),
        },
    }


def solve_estate_action(ctx: dict) -> dict:
    prof_bundle = profile(ctx)
    prof = prof_bundle["values"]
    life = first_record(ctx["life"], "life-insurance")
    trust = first_record(ctx["trusts"], "trust candidate")
    ilit = ilit_values(life, prof, ctx["tax_policy"])
    trust_calc = trust_values(trust, prof, ctx["tax_policy"])

    preferred = trust_calc["preferred_strategy"]
    if ilit["risk"] != "LOW_IF_FORMALITIES_MET":
        primary = "ILIT_WITH_EXEMPTION_REVIEW"
        sequencing = "ILIT_FIRST_THEN_ATTORNEY_REVIEW"
    elif preferred == "GRAT":
        primary = "COMBINE_ILIT_AND_GRAT"
        sequencing = "ILIT_FIRST_THEN_GRAT"
    else:
        primary = "CRAT_WITH_LIQUIDITY_REVIEW"
        sequencing = "TRUST_DECISION_FIRST"

    actions = {"ATTORNEY_DRAFT_REVIEW"}
    if life.get("proposed_owner") == "ILIT":
        actions.add("ILIT_CRUMMEY_NOTICE_CYCLE")
    if ilit["premium_gap"] > 0 or "LOOKBACK" in ilit["risk"]:
        actions.add("LIFETIME_EXEMPTION_ALLOCATION")
    if preferred == "GRAT":
        actions.add("GRAT_FOR_APPRECIATING_SHARES")
    else:
        actions.add("CRAT_FOR_CHARITABLE_REMAINDER")

    return {
        "task_id": ctx["task_id"],
        "client_id": ctx["client_id"],
        "analysis_type": "estate_liquidity_action_plan",
        "recommendation": {
            "primary_action": primary,
            "sequencing": sequencing,
            "risk_flag": ilit["risk"],
        },
        "estate_context": estate_context(prof, ctx["tax_policy"]),
        "ilit": {
            "annual_exclusion_capacity": money(ilit["capacity"]),
            "premium_gap": money(ilit["premium_gap"]),
            "estate_inclusion_risk": ilit["risk"],
            "projected_outside_estate_if_implemented": ilit["estate_result"]["projected_outside_estate_if_implemented"],
        },
        "trust_transfer": {
            "preferred_strategy": preferred,
            "projected_remainder_to_heirs": trust_calc["grat"]["projected_remainder_to_heirs"],
            "estimated_estate_tax_reduction": trust_calc["grat"]["estimated_estate_tax_reduction"],
            "projected_charitable_remainder": trust_calc["crat"]["projected_charitable_remainder"],
        },
        "action_set": sorted(actions),
        "source_resolution": {
            "controlling_goal_source": prof_bundle["sources"].get("family_transfer_priority", "SIGNED_PROFILE"),
            "controlling_policy_source": life.get("source_type", "SIGNED_PROFILE"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", help="API base URL; defaults to API_BASE")
    parser.add_argument("--memo", required=True, help="Path to request_memo.md")
    parser.add_argument("--template", required=True, help="Path to answer_template.json")
    parser.add_argument("--prompt", help="Optional path to prompt.txt")
    parser.add_argument("--client-id", help="Override client identifier")
    parser.add_argument("--task-id", help="Override task identifier")
    parser.add_argument("--horizon", type=int, help="Override planning horizon year")
    args = parser.parse_args()

    ctx = context(args)
    kind = analysis_type(ctx["template"])
    if kind == "roth_conversion_rmd":
        output = solve_roth(ctx)
    elif kind == "ilit_crummey_implementation":
        output = solve_ilit(ctx)
    elif kind == "trust_comparison":
        output = solve_trust(ctx)
    elif kind == "estate_liquidity_action_plan":
        output = solve_estate_action(ctx)
    else:
        raise SystemExit(f"Unsupported analysis_type: {kind}")

    json.dump(output, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
