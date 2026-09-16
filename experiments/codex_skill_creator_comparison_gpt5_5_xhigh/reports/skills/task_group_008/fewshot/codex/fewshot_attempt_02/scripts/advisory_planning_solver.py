#!/usr/bin/env python3
"""Solve the staged advisory planning JSON task family from API records."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any


SOURCE_PRIORITY = [
    "SIGNED_PROFILE",
    "ATTORNEY_MEMO",
    "CUSTODIAN_EXPORT",
    "CRM_NOTE",
    "STALE_MARKETING_INTAKE",
]


def cents(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def source_rank(source_type: str | None) -> int:
    if source_type in SOURCE_PRIORITY:
        return SOURCE_PRIORITY.index(source_type)
    return len(SOURCE_PRIORITY)


def latest_date_key(doc: dict[str, Any]) -> str:
    return str(doc.get("effective_date") or "")


def select_doc_for_fact(docs: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    candidates = [doc for doc in docs if key in (doc.get("facts") or {})]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda doc: (source_rank(doc.get("source_type")), latest_date_key(doc)),
    )[0]


def fact(
    docs: list[dict[str, Any]],
    client: dict[str, Any],
    key: str,
    default: Any = None,
) -> tuple[Any, str]:
    doc = select_doc_for_fact(docs, key)
    if doc is not None:
        return (doc.get("facts") or {}).get(key), str(doc.get("source_type"))
    if key in client:
        return client[key], "SIGNED_PROFILE"
    return default, "SIGNED_PROFILE"


class AdvisoryApi:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/") + "/"

    def get(self, path: str, params: dict[str, str] | None = None) -> Any:
        url = urllib.parse.urljoin(self.base_url, path.lstrip("/"))
        if params:
            url += "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = response.read().decode("utf-8")
        return json.loads(payload)


def filtered(records: Any, client_id: str) -> list[dict[str, Any]]:
    if not isinstance(records, list):
        return []
    return [record for record in records if record.get("client_id") == client_id]


def infer_task_id(input_dir: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    for path in [input_dir, *input_dir.parents]:
        if re.fullmatch(r"(?:train|test)_\d+", path.name):
            return path.name
    raise SystemExit("Could not infer task_id; pass --task-id.")


def infer_client_id(prompt: str, memo: str) -> str:
    text = memo + "\n" + prompt
    match = re.search(r"Client ID:\s*([A-Z]{2,}-\d+)", text)
    if not match:
        match = re.search(r"\bclient\s+([A-Z]{2,}-\d+)\b", text, flags=re.I)
    if not match:
        raise SystemExit("Could not infer client_id from prompt or memo.")
    return match.group(1)


def infer_horizon(memo: str, default: int | None = None) -> int:
    match = re.search(r"Planning horizon year:\s*(\d{4})", memo)
    if match:
        return int(match.group(1))
    if default is None:
        raise SystemExit("Could not infer planning horizon year.")
    return default


def infer_analysis_type(template: dict[str, Any]) -> str:
    raw = str((template.get("fields") or {}).get("analysis_type", ""))
    match = re.search(r"enum:\s*([a-z0-9_]+)", raw)
    if match:
        return match.group(1)
    required = set(template.get("required_top_level_keys") or [])
    if "conversion_plan" in required:
        return "roth_conversion_rmd"
    if "gift_plan" in required:
        return "ilit_crummey_implementation"
    if "trust_transfer" in required:
        return "estate_liquidity_action_plan"
    if {"grat", "crat"}.issubset(required):
        return "trust_comparison"
    raise SystemExit("Could not infer analysis_type from answer_template.json.")


def first_record(records: list[dict[str, Any]], label: str) -> dict[str, Any]:
    if not records:
        raise SystemExit(f"No {label} record found for client.")
    return records[0]


def policy_amount_by_year(policy: dict[str, Any], key: str, year: int) -> float:
    values = policy.get(key) or {}
    if str(year) in values:
        return float(values[str(year)])
    eligible = sorted(int(candidate) for candidate in values if int(candidate) <= year)
    if eligible:
        return float(values[str(eligible[-1])])
    latest = sorted(int(candidate) for candidate in values)[-1]
    return float(values[str(latest)])


def rmd_factor(factors: dict[str, Any], age: int) -> float:
    if str(age) in factors:
        return float(factors[str(age)])
    ages = sorted(int(candidate) for candidate in factors)
    if age < ages[0]:
        return float(factors[str(ages[0])])
    return float(factors[str(ages[-1])])


def simulate_retirement(
    traditional_balance: float,
    roth_balance: float,
    age: int,
    planning_year: int,
    horizon_year: int,
    expected_return: float,
    rmd_start_age: int,
    rmd_factors: dict[str, Any],
    tax_rate: float,
    annual_conversion: float = 0.0,
    conversion_years: int = 0,
) -> tuple[float, float, float, list[float]]:
    traditional = float(traditional_balance)
    roth = float(roth_balance)
    rmd_tax = 0.0
    conversions: list[float] = []

    for year in range(planning_year, horizon_year + 1):
        current_age = age + (year - planning_year)
        if year < planning_year + conversion_years and annual_conversion > 0:
            converted = min(float(annual_conversion), traditional)
            traditional -= converted
            roth += converted
        else:
            converted = 0.0
        conversions.append(converted)

        if current_age >= rmd_start_age:
            rmd = traditional / rmd_factor(rmd_factors, current_age)
            traditional -= rmd
            rmd_tax += rmd * tax_rate

        traditional *= 1 + expected_return
        roth *= 1 + expected_return

    return rmd_tax, traditional, roth, conversions


def estate_context(
    client: dict[str, Any],
    docs: list[dict[str, Any]],
    tax_policy: dict[str, Any],
) -> dict[str, Any]:
    planning_year = int(fact(docs, client, "planning_year")[0])
    filing_status = str(fact(docs, client, "filing_status")[0] or "").upper()
    marital_status = str(fact(docs, client, "marital_status")[0] or "").lower()
    multiplier = 2 if filing_status == "MFJ" or marital_status == "married" else 1
    exemption = policy_amount_by_year(tax_policy, "estate_tax_exemption", planning_year)
    exemption_used = exemption * multiplier
    estate_value = float(fact(docs, client, "estate_value")[0])
    liquid_assets = float(fact(docs, client, "liquid_assets")[0])
    taxable_estate = max(0.0, estate_value - exemption_used)
    estate_tax_exposure = taxable_estate * float(tax_policy["estate_tax_rate"])
    return {
        "planning_year": planning_year,
        "exemption_used": cents(exemption_used),
        "taxable_estate": cents(taxable_estate),
        "estate_tax_exposure": cents(estate_tax_exposure),
        "liquid_assets_available": cents(liquid_assets),
        "liquidity_gap_before_planning": cents(max(0.0, estate_tax_exposure - liquid_assets)),
    }


def solve_roth(ctx: dict[str, Any]) -> dict[str, Any]:
    client = ctx["client"]
    docs = ctx["docs"]
    account = first_record(ctx["retirement_accounts"], "retirement account")
    tax_policy = ctx["tax_policy"]

    planning_year = int(fact(docs, client, "planning_year")[0])
    age = int(fact(docs, client, "age")[0])
    filing_status = str(fact(docs, client, "filing_status")[0]).upper()
    annual_income = float(fact(docs, client, "annual_non_ira_income", 0)[0])
    marginal_tax_rate = float(fact(docs, client, "marginal_tax_rate", 0)[0])
    liquid_assets = float(fact(docs, client, "liquid_assets", 0)[0])

    bracket_target = float((tax_policy.get("conversion_bracket_targets") or {})[filing_status])
    annual_conversion = max(0.0, min(bracket_target - annual_income, float(account["traditional_balance"])))
    conversion_years = int(account.get("recommended_conversion_years") or 0)
    horizon_year = ctx["horizon_year"]
    rmd_start_age = int(account["rmd_start_age"])
    first_rmd_year = planning_year + max(0, rmd_start_age - age)

    baseline_tax, _, _, _ = simulate_retirement(
        float(account["traditional_balance"]),
        float(account.get("roth_balance") or 0),
        age,
        planning_year,
        horizon_year,
        float(account["expected_return"]),
        rmd_start_age,
        ctx["rmd_factors"],
        marginal_tax_rate,
    )
    conversion_tax, traditional_horizon, roth_horizon, conversions = simulate_retirement(
        float(account["traditional_balance"]),
        float(account.get("roth_balance") or 0),
        age,
        planning_year,
        horizon_year,
        float(account["expected_return"]),
        rmd_start_age,
        ctx["rmd_factors"],
        marginal_tax_rate,
        annual_conversion,
        conversion_years,
    )

    planned_conversions = conversions[:conversion_years]
    total_converted = sum(planned_conversions)
    total_conversion_tax = total_converted * marginal_tax_rate
    conversion_years_positive = sum(1 for amount in planned_conversions if amount > 0)

    if total_converted <= 0:
        primary_action = "NO_CONVERSION"
        suitability = "DEFER"
        risk_flag = "TAX_BRACKET_MANAGEMENT"
    elif total_conversion_tax > liquid_assets:
        primary_action = "DEFER"
        suitability = "BORDERLINE"
        risk_flag = "LIQUIDITY_CONSTRAINT"
    else:
        primary_action = "STAGED_ROTH_CONVERSION"
        suitability = "SUITABLE"
        risk_flag = "TAX_BRACKET_MANAGEMENT"

    total_horizon = roth_horizon + traditional_horizon
    roth_ratio = roth_horizon / total_horizon if total_horizon else 1.0
    if roth_ratio >= 0.8:
        heir_profile = "MOSTLY_TAX_FREE"
    elif roth_ratio <= 0.2:
        heir_profile = "MOSTLY_TAXABLE"
    else:
        heir_profile = "MIXED_TAXABLE_AND_TAX_FREE"

    return {
        "task_id": ctx["task_id"],
        "client_id": ctx["client_id"],
        "analysis_type": "roth_conversion_rmd",
        "recommendation": {
            "primary_action": primary_action,
            "suitability": suitability,
            "risk_flag": risk_flag,
        },
        "conversion_plan": {
            "first_conversion_year": planning_year,
            "conversion_years": conversion_years,
            "conversion_years_positive": conversion_years_positive,
            "annual_conversion_amount": cents(annual_conversion),
            "total_converted": cents(total_converted),
            "total_conversion_tax": cents(total_conversion_tax),
        },
        "rmd_projection": {
            "horizon_year": horizon_year,
            "first_rmd_year": first_rmd_year,
            "baseline_rmd_tax_through_horizon": cents(baseline_tax),
            "conversion_rmd_tax_through_horizon": cents(conversion_tax),
            "rmd_tax_savings_through_horizon": cents(baseline_tax - conversion_tax),
        },
        "legacy_projection": {
            "projected_roth_balance_horizon": cents(roth_horizon),
            "projected_traditional_balance_horizon": cents(traditional_horizon),
            "heir_tax_profile": heir_profile,
        },
        "source_resolution": {
            "controlling_profile_source": fact(docs, client, "annual_non_ira_income")[1],
            "controlling_account_source": account.get("source_type") or "CUSTODIAN_EXPORT",
        },
    }


def ilit_common(ctx: dict[str, Any]) -> dict[str, Any]:
    client = ctx["client"]
    docs = ctx["docs"]
    policy = first_record(ctx["life_insurance"], "life insurance")
    planning_year = int(fact(docs, client, "planning_year")[0])
    beneficiary_count, beneficiary_source = fact(docs, client, "beneficiary_count", 0)
    beneficiary_count = int(beneficiary_count)
    exclusion = policy_amount_by_year(ctx["tax_policy"], "annual_gift_exclusion", planning_year)
    capacity = exclusion * beneficiary_count
    annual_premium = float(policy["annual_premium"])
    premium_gap = max(0.0, annual_premium - capacity)
    existing_transfer = bool(policy.get("is_existing_policy_transfer"))

    if existing_transfer and premium_gap > 0:
        risk = "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL"
        primary = "DISCLOSE_LOOKBACK_AND_USE_EXEMPTION"
        suitability = "BORDERLINE"
    elif existing_transfer:
        risk = "THREE_YEAR_LOOKBACK"
        primary = "USE_NEW_POLICY_OR_ACCEPT_LOOKBACK"
        suitability = "BORDERLINE"
    elif premium_gap > 0:
        risk = "EXCLUSION_SHORTFALL"
        primary = "USE_LIFETIME_EXEMPTION_FOR_SHORTFALL"
        suitability = "BORDERLINE"
    else:
        risk = "LOW_IF_FORMALITIES_MET"
        primary = "FUND_WITH_CRUMMEY_NOTICES"
        suitability = "SUITABLE_WITH_ADMINISTRATION"

    contribution_date = date.fromisoformat(str(policy["planned_contribution_date"]))
    notice_due = contribution_date + timedelta(days=7)
    withdrawal_end = notice_due + timedelta(days=30)
    earliest_premium = withdrawal_end + timedelta(days=1)
    policy_source = policy.get("source_type") or "SIGNED_PROFILE"

    return {
        "policy": policy,
        "planning_year": planning_year,
        "beneficiary_count": beneficiary_count,
        "beneficiary_source": beneficiary_source,
        "annual_exclusion": exclusion,
        "capacity": capacity,
        "annual_premium": annual_premium,
        "premium_gap": premium_gap,
        "risk": risk,
        "primary": primary,
        "suitability": suitability,
        "policy_source": policy_source,
        "administration": {
            "notices_required": beneficiary_count,
            "contribution_date": contribution_date.isoformat(),
            "notice_due_date": notice_due.isoformat(),
            "withdrawal_window_end": withdrawal_end.isoformat(),
            "earliest_premium_payment_date": earliest_premium.isoformat(),
            "dedicated_bank_account_required": True,
        },
    }


def solve_ilit(ctx: dict[str, Any]) -> dict[str, Any]:
    values = ilit_common(ctx)
    policy = values["policy"]
    death_benefit = float(policy["death_benefit"])
    estate_rate = float(ctx["tax_policy"]["estate_tax_rate"])

    return {
        "task_id": ctx["task_id"],
        "client_id": ctx["client_id"],
        "analysis_type": "ilit_crummey_implementation",
        "recommendation": {
            "primary_action": values["primary"],
            "suitability": values["suitability"],
            "risk_flag": values["risk"],
        },
        "gift_plan": {
            "planning_year": values["planning_year"],
            "annual_exclusion_per_beneficiary": cents(values["annual_exclusion"]),
            "beneficiary_count": values["beneficiary_count"],
            "annual_exclusion_capacity": cents(values["capacity"]),
            "annual_premium": cents(values["annual_premium"]),
            "premium_gap": cents(values["premium_gap"]),
        },
        "administration": values["administration"],
        "estate_result": {
            "death_benefit": cents(death_benefit),
            "estate_inclusion_risk": values["risk"],
            "projected_outside_estate_if_implemented": cents(death_benefit),
            "tax_liquidity_support": cents(death_benefit * estate_rate),
        },
        "source_resolution": {
            "controlling_beneficiary_source": values["beneficiary_source"],
            "controlling_policy_source": values["policy_source"],
        },
    }


def trust_common(ctx: dict[str, Any]) -> dict[str, Any]:
    client = ctx["client"]
    docs = ctx["docs"]
    candidate = first_record(ctx["trust_candidates"], "trust candidate")
    asset = float(candidate["asset_value"])
    growth = float(candidate["expected_growth_rate"])
    grat_term = int(candidate["grat_term_years"])
    annuity_rate = float(candidate["grat_annuity_rate"])
    crat_term = int(candidate["crat_term_years"])
    payout_rate = float(candidate["crat_payout_rate"])
    estate_rate = float(ctx["tax_policy"]["estate_tax_rate"])
    charitable_rate = float(ctx["tax_policy"]["charitable_deduction_rate"])

    family_priority, family_source = fact(docs, client, "family_transfer_priority", "moderate")
    philanthropy, philanthropy_source = fact(docs, client, "philanthropic_intent", "moderate")
    family_priority = str(family_priority).lower()
    philanthropy = str(philanthropy).lower()

    if philanthropy == "high" and family_priority != "high":
        preferred = "CRAT"
        rationale = "PHILANTHROPIC_PRIORITY"
        alternate = "SECONDARY_FAMILY_TRANSFER_TOOL"
        goal_source = philanthropy_source
    else:
        preferred = "GRAT"
        rationale = "CHILDREN_TRANSFER_PRIORITY"
        alternate = "SECONDARY_CHARITABLE_TOOL"
        goal_source = family_source

    grat_remainder = asset * (1 + growth) ** grat_term - asset * annuity_rate * grat_term
    crat_remainder = asset * (1 + growth) ** crat_term - asset * payout_rate * crat_term
    if family_priority == "high":
        crat_family_fit = "LOW"
    elif family_priority == "moderate":
        crat_family_fit = "MODERATE"
    else:
        crat_family_fit = "HIGH"

    return {
        "preferred": preferred,
        "rationale": rationale,
        "alternate": alternate,
        "goal_source": goal_source,
        "asset_source": candidate.get("source_type") or "ATTORNEY_MEMO",
        "grat": {
            "term_years": grat_term,
            "projected_remainder_to_heirs": cents(grat_remainder),
            "estimated_estate_tax_reduction": cents(grat_remainder * estate_rate),
            "mortality_inclusion_risk": "TERM_SURVIVAL_REQUIRED",
        },
        "crat": {
            "term_years": crat_term,
            "projected_charitable_remainder": cents(crat_remainder),
            "estimated_income_tax_deduction": cents(crat_remainder * charitable_rate),
            "family_transfer_fit": crat_family_fit,
        },
        "trust_transfer": {
            "preferred_strategy": preferred,
            "projected_remainder_to_heirs": cents(grat_remainder),
            "estimated_estate_tax_reduction": cents(grat_remainder * estate_rate),
            "projected_charitable_remainder": cents(crat_remainder),
        },
    }


def solve_trust_comparison(ctx: dict[str, Any]) -> dict[str, Any]:
    trust = trust_common(ctx)
    return {
        "task_id": ctx["task_id"],
        "client_id": ctx["client_id"],
        "analysis_type": "trust_comparison",
        "recommendation": {
            "preferred_strategy": trust["preferred"],
            "rationale_code": trust["rationale"],
            "alternate_role": trust["alternate"],
        },
        "estate_context": estate_context(ctx["client"], ctx["docs"], ctx["tax_policy"]),
        "grat": trust["grat"],
        "crat": trust["crat"],
        "source_resolution": {
            "controlling_goal_source": trust["goal_source"],
            "controlling_asset_source": trust["asset_source"],
        },
    }


def solve_estate_liquidity(ctx: dict[str, Any]) -> dict[str, Any]:
    ilit = ilit_common(ctx)
    trust = trust_common(ctx)
    if trust["preferred"] == "CRAT":
        primary = "CRAT_WITH_LIQUIDITY_REVIEW"
        sequencing = "TRUST_DECISION_FIRST"
    elif ilit["risk"] == "LOW_IF_FORMALITIES_MET":
        primary = "COMBINE_ILIT_AND_GRAT"
        sequencing = "ILIT_FIRST_THEN_GRAT"
    else:
        primary = "ILIT_WITH_EXEMPTION_REVIEW"
        sequencing = "ILIT_FIRST_THEN_ATTORNEY_REVIEW"

    actions = {"ATTORNEY_DRAFT_REVIEW", "ILIT_CRUMMEY_NOTICE_CYCLE"}
    if trust["preferred"] == "GRAT":
        actions.add("GRAT_FOR_APPRECIATING_SHARES")
    else:
        actions.add("CRAT_FOR_CHARITABLE_REMAINDER")
    if ilit["premium_gap"] > 0 or "LOOKBACK" in ilit["risk"]:
        actions.add("LIFETIME_EXEMPTION_ALLOCATION")

    return {
        "task_id": ctx["task_id"],
        "client_id": ctx["client_id"],
        "analysis_type": "estate_liquidity_action_plan",
        "recommendation": {
            "primary_action": primary,
            "sequencing": sequencing,
            "risk_flag": ilit["risk"],
        },
        "estate_context": estate_context(ctx["client"], ctx["docs"], ctx["tax_policy"]),
        "ilit": {
            "annual_exclusion_capacity": cents(ilit["capacity"]),
            "premium_gap": cents(ilit["premium_gap"]),
            "estate_inclusion_risk": ilit["risk"],
            "projected_outside_estate_if_implemented": cents(float(ilit["policy"]["death_benefit"])),
        },
        "trust_transfer": trust["trust_transfer"],
        "action_set": sorted(actions),
        "source_resolution": {
            "controlling_goal_source": trust["goal_source"],
            "controlling_policy_source": ilit["policy_source"],
        },
    }


def build_context(args: argparse.Namespace) -> dict[str, Any]:
    input_dir = Path(args.input_dir or ".").resolve()
    prompt = read_text(input_dir / "prompt.txt")
    memo = read_text(input_dir / "payloads" / "request_memo.md")
    template = load_json(input_dir / "payloads" / "answer_template.json")
    task_id = infer_task_id(input_dir, args.task_id)
    client_id = infer_client_id(prompt, memo)
    api_base = args.api_base or os.environ.get("API_BASE") or "http://task-env:9008/"
    api = AdvisoryApi(api_base)

    client = api.get(f"/api/clients/{urllib.parse.quote(client_id)}")
    docs = filtered(api.get("/api/source-documents", {"client_id": client_id}), client_id)
    retirement_accounts = filtered(api.get("/api/retirement-accounts", {"client_id": client_id}), client_id)
    life_insurance = filtered(api.get("/api/life-insurance", {"client_id": client_id}), client_id)
    trust_candidates = filtered(api.get("/api/trust-candidates", {"client_id": client_id}), client_id)
    tax_policy = api.get("/api/policies/tax")
    rmd_factors = api.get("/api/rmd-factors")
    analysis_type = infer_analysis_type(template)

    horizon_default = None
    if analysis_type == "roth_conversion_rmd":
        horizon_default = int(fact(docs, client, "planning_year")[0]) + 20

    return {
        "task_id": task_id,
        "client_id": client_id,
        "prompt": prompt,
        "memo": memo,
        "template": template,
        "analysis_type": analysis_type,
        "horizon_year": infer_horizon(memo, horizon_default) if analysis_type == "roth_conversion_rmd" else None,
        "client": client,
        "docs": docs,
        "retirement_accounts": retirement_accounts,
        "life_insurance": life_insurance,
        "trust_candidates": trust_candidates,
        "tax_policy": tax_policy,
        "rmd_factors": rmd_factors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Solve advisory planning JSON tasks.")
    parser.add_argument("--input-dir", help="Directory containing prompt.txt and payloads/.")
    parser.add_argument("--task-id", help="Stable task id to emit when it cannot be inferred.")
    parser.add_argument("--api-base", help="Advisory API base URL. Defaults to API_BASE.")
    args = parser.parse_args()

    ctx = build_context(args)
    if ctx["analysis_type"] == "roth_conversion_rmd":
        answer = solve_roth(ctx)
    elif ctx["analysis_type"] == "ilit_crummey_implementation":
        answer = solve_ilit(ctx)
    elif ctx["analysis_type"] == "trust_comparison":
        answer = solve_trust_comparison(ctx)
    elif ctx["analysis_type"] == "estate_liquidity_action_plan":
        answer = solve_estate_liquidity(ctx)
    else:
        raise SystemExit(f"Unsupported analysis_type: {ctx['analysis_type']}")

    json.dump(answer, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
