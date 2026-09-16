#!/usr/bin/env python3
"""Deterministic helper for private wealth advisory JSON tasks."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


SOURCE_PRIORITY = [
    "SIGNED_PROFILE",
    "ATTORNEY_MEMO",
    "CUSTODIAN_EXPORT",
    "CRM_NOTE",
    "STALE_MARKETING_INTAKE",
]


def money(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def load_text(path: str | None) -> str:
    if not path:
        return ""
    return Path(path).read_text()


def fetch_json(api_base: str, path: str) -> Any:
    url = api_base.rstrip("/") + path
    with urllib.request.urlopen(url, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def find_client_id(*texts: str) -> str:
    patterns = [
        r"Client ID:\s*([A-Z]+-\d+)",
        r"client\s+([A-Z]+-\d+)",
        r"\b([A-Z]{2,}-\d{4,})\b",
    ]
    for text in texts:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
    raise SystemExit("Could not infer client_id")


def infer_task_id(prompt_path: str | None, explicit: str | None) -> str:
    if explicit:
        return explicit
    if prompt_path:
        for parent in Path(prompt_path).resolve().parents:
            if re.fullmatch(r"(?:train|test)_\d+", parent.name):
                return parent.name
    raise SystemExit("Could not infer task_id; pass --task-id")


def infer_analysis_type(template: dict[str, Any], prompt: str, memo: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    field = template.get("fields", {}).get("analysis_type", "")
    match = re.search(r"enum:\s*([a-z_]+)", str(field))
    if match:
        return match.group(1)
    text = f"{prompt}\n{memo}".lower()
    if "roth" in text or "rmd" in text:
        return "roth_conversion_rmd"
    if "ilit" in text or "crummey" in text:
        return "ilit_crummey_implementation"
    if "liquidity action" in text:
        return "estate_liquidity_action_plan"
    if "grat" in text or "crat" in text:
        return "trust_comparison"
    raise SystemExit("Could not infer analysis_type")


def infer_horizon(memo: str, explicit: int | None) -> int | None:
    if explicit is not None:
        return explicit
    match = re.search(r"Planning horizon year:\s*(\d{4})", memo)
    if match:
        return int(match.group(1))
    return None


def latest_doc(docs: list[dict[str, Any]], source_type: str, facts: list[str]) -> dict[str, Any] | None:
    matches = [
        doc
        for doc in docs
        if doc.get("source_type") == source_type
        and any(fact in doc.get("facts", {}) for fact in facts)
    ]
    if not matches:
        return None
    return sorted(matches, key=lambda doc: doc.get("effective_date", ""), reverse=True)[0]


def choose_doc(docs: list[dict[str, Any]], facts: list[str]) -> dict[str, Any] | None:
    for source_type in SOURCE_PRIORITY:
        doc = latest_doc(docs, source_type, facts)
        if doc:
            return doc
    return None


def fact(
    client: dict[str, Any],
    docs: list[dict[str, Any]],
    name: str,
    default: Any = None,
) -> tuple[Any, str | None]:
    doc = choose_doc(docs, [name])
    if doc and name in doc.get("facts", {}):
        return doc["facts"][name], doc.get("source_type")
    if name in client:
        return client[name], "SIGNED_PROFILE"
    return default, None


def source_for(docs: list[dict[str, Any]], facts: list[str], fallback: str) -> str:
    doc = choose_doc(docs, facts)
    return doc.get("source_type", fallback) if doc else fallback


def policy_value(policy: dict[str, Any], key: str, year: int) -> float:
    values = policy[key]
    if str(year) in values:
        return float(values[str(year)])
    eligible = [int(k) for k in values if int(k) <= year]
    if not eligible:
        return float(values[sorted(values)[-1]])
    return float(values[str(max(eligible))])


def client_bundle(api_base: str, client_id: str) -> dict[str, Any]:
    client = fetch_json(api_base, f"/api/clients/{client_id}")

    def filtered(path: str) -> list[dict[str, Any]]:
        rows = fetch_json(api_base, path)
        return [row for row in rows if row.get("client_id") == client_id]

    return {
        "client": client,
        "docs": filtered("/api/source-documents"),
        "accounts": filtered("/api/retirement-accounts"),
        "policies": filtered("/api/life-insurance"),
        "trusts": filtered("/api/trust-candidates"),
        "tax": fetch_json(api_base, "/api/policies/tax"),
        "rmd": fetch_json(api_base, "/api/rmd-factors"),
    }


def first_or_die(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    if not rows:
        raise SystemExit(f"Missing {label} for client")
    return rows[0]


def rmd_factor(factors: dict[str, Any], age: int) -> float:
    if str(age) not in factors:
        raise SystemExit(f"Missing RMD factor for age {age}")
    return float(factors[str(age)])


def simulate_roth(
    traditional_balance: float,
    roth_balance: float,
    age: int,
    planning_year: int,
    horizon_year: int,
    expected_return: float,
    rmd_start_age: int,
    conversion_years: int,
    annual_conversion: float,
    marginal_tax_rate: float,
    factors: dict[str, Any],
) -> tuple[float, float, float, float, int]:
    traditional = float(traditional_balance)
    roth = float(roth_balance)
    rmd_tax = 0.0
    total_converted = 0.0
    positive_years = 0

    for year in range(planning_year, horizon_year + 1):
        current_age = age + (year - planning_year)
        if year < planning_year + conversion_years and annual_conversion > 0:
            converted = min(annual_conversion, traditional)
            if converted > 0:
                positive_years += 1
                total_converted += converted
                traditional -= converted
                roth += converted

        if current_age >= rmd_start_age and traditional > 0:
            distribution = traditional / rmd_factor(factors, current_age)
            traditional -= distribution
            rmd_tax += distribution * marginal_tax_rate

        traditional *= 1.0 + expected_return
        roth *= 1.0 + expected_return

    return rmd_tax, traditional, roth, total_converted, positive_years


def heir_tax_profile(roth: float, traditional: float) -> str:
    total = roth + traditional
    if total <= 0:
        return "MOSTLY_TAX_FREE"
    if traditional / total <= 0.1:
        return "MOSTLY_TAX_FREE"
    if roth / total <= 0.1:
        return "MOSTLY_TAXABLE"
    return "MIXED_TAXABLE_AND_TAX_FREE"


def roth_output(bundle: dict[str, Any], task_id: str, client_id: str, horizon_year: int | None) -> dict[str, Any]:
    client = bundle["client"]
    docs = bundle["docs"]
    account = first_or_die(bundle["accounts"], "retirement account")
    tax = bundle["tax"]

    planning_year = int(fact(client, docs, "planning_year")[0])
    age = int(fact(client, docs, "age")[0])
    filing_status = str(fact(client, docs, "filing_status")[0])
    income = float(fact(client, docs, "annual_non_ira_income")[0])
    marginal_tax_rate = float(fact(client, docs, "marginal_tax_rate")[0])
    liquid_assets = float(fact(client, docs, "liquid_assets")[0])
    if horizon_year is None:
        raise SystemExit("Roth/RMD tasks require a planning horizon year")

    target = float(tax["conversion_bracket_targets"][filing_status])
    annual_conversion = max(0.0, target - income)
    conversion_years = int(account.get("recommended_conversion_years", 0))

    baseline_tax, _, _, _, _ = simulate_roth(
        account["traditional_balance"],
        account.get("roth_balance", 0),
        age,
        planning_year,
        horizon_year,
        float(account["expected_return"]),
        int(account["rmd_start_age"]),
        0,
        0.0,
        marginal_tax_rate,
        bundle["rmd"],
    )
    conversion_taxable_rmd, ending_trad, ending_roth, total_converted, positive_years = simulate_roth(
        account["traditional_balance"],
        account.get("roth_balance", 0),
        age,
        planning_year,
        horizon_year,
        float(account["expected_return"]),
        int(account["rmd_start_age"]),
        conversion_years,
        annual_conversion,
        marginal_tax_rate,
        bundle["rmd"],
    )

    total_conversion_tax = total_converted * marginal_tax_rate
    if total_converted <= 0:
        primary_action = "NO_CONVERSION"
        suitability = "DEFER"
        risk_flag = "RMD_NEAR_TERM" if age >= int(account["rmd_start_age"]) else "TAX_BRACKET_MANAGEMENT"
    elif total_conversion_tax > liquid_assets:
        primary_action = "DEFER"
        suitability = "BORDERLINE"
        risk_flag = "LIQUIDITY_CONSTRAINT"
    else:
        primary_action = "STAGED_ROTH_CONVERSION"
        suitability = "SUITABLE"
        risk_flag = "TAX_BRACKET_MANAGEMENT"

    first_rmd_year = planning_year if age >= int(account["rmd_start_age"]) else planning_year + int(account["rmd_start_age"]) - age

    return {
        "task_id": task_id,
        "client_id": client_id,
        "analysis_type": "roth_conversion_rmd",
        "recommendation": {
            "primary_action": primary_action,
            "suitability": suitability,
            "risk_flag": risk_flag,
        },
        "conversion_plan": {
            "first_conversion_year": planning_year,
            "conversion_years": conversion_years,
            "conversion_years_positive": positive_years,
            "annual_conversion_amount": money(annual_conversion),
            "total_converted": money(total_converted),
            "total_conversion_tax": money(total_conversion_tax),
        },
        "rmd_projection": {
            "horizon_year": horizon_year,
            "first_rmd_year": first_rmd_year,
            "baseline_rmd_tax_through_horizon": money(baseline_tax),
            "conversion_rmd_tax_through_horizon": money(conversion_taxable_rmd),
            "rmd_tax_savings_through_horizon": money(baseline_tax - conversion_taxable_rmd),
        },
        "legacy_projection": {
            "projected_roth_balance_horizon": money(ending_roth),
            "projected_traditional_balance_horizon": money(ending_trad),
            "heir_tax_profile": heir_tax_profile(ending_roth, ending_trad),
        },
        "source_resolution": {
            "controlling_profile_source": source_for(
                docs,
                ["annual_non_ira_income", "marginal_tax_rate", "planning_year", "age"],
                "SIGNED_PROFILE",
            ),
            "controlling_account_source": account.get("source_type", "CUSTODIAN_EXPORT"),
        },
    }


def ilit_risk(existing_transfer: bool, premium_gap: float) -> str:
    has_gap = premium_gap > 0
    if existing_transfer and has_gap:
        return "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL"
    if existing_transfer:
        return "THREE_YEAR_LOOKBACK"
    if has_gap:
        return "EXCLUSION_SHORTFALL"
    return "LOW_IF_FORMALITIES_MET"


def ilit_recommendation(risk: str) -> tuple[str, str]:
    if risk == "LOW_IF_FORMALITIES_MET":
        return "FUND_WITH_CRUMMEY_NOTICES", "SUITABLE_WITH_ADMINISTRATION"
    if risk == "EXCLUSION_SHORTFALL":
        return "USE_LIFETIME_EXEMPTION_FOR_SHORTFALL", "BORDERLINE"
    if risk == "THREE_YEAR_LOOKBACK":
        return "USE_NEW_POLICY_OR_ACCEPT_LOOKBACK", "BORDERLINE"
    return "DISCLOSE_LOOKBACK_AND_USE_EXEMPTION", "NOT_SUITABLE"


def ilit_core(bundle: dict[str, Any]) -> dict[str, Any]:
    client = bundle["client"]
    docs = bundle["docs"]
    policy = first_or_die(bundle["policies"], "life-insurance policy")
    planning_year = int(fact(client, docs, "planning_year")[0])
    beneficiary_count = int(fact(client, docs, "beneficiary_count")[0])
    exclusion = policy_value(bundle["tax"], "annual_gift_exclusion", planning_year)
    capacity = exclusion * beneficiary_count
    premium = float(policy["annual_premium"])
    premium_gap = max(0.0, premium - capacity)
    risk = ilit_risk(bool(policy.get("is_existing_policy_transfer")), premium_gap)
    primary_action, suitability = ilit_recommendation(risk)
    contribution_date = date.fromisoformat(policy["planned_contribution_date"])
    notice_due = contribution_date + timedelta(days=7)
    withdrawal_end = notice_due + timedelta(days=30)
    premium_date = withdrawal_end + timedelta(days=1)
    death_benefit = float(policy["death_benefit"])

    return {
        "planning_year": planning_year,
        "annual_exclusion_per_beneficiary": exclusion,
        "beneficiary_count": beneficiary_count,
        "annual_exclusion_capacity": capacity,
        "annual_premium": premium,
        "premium_gap": premium_gap,
        "risk": risk,
        "primary_action": primary_action,
        "suitability": suitability,
        "notices_required": beneficiary_count,
        "contribution_date": contribution_date.isoformat(),
        "notice_due_date": notice_due.isoformat(),
        "withdrawal_window_end": withdrawal_end.isoformat(),
        "earliest_premium_payment_date": premium_date.isoformat(),
        "dedicated_bank_account_required": True,
        "death_benefit": death_benefit,
        "projected_outside_estate_if_implemented": death_benefit,
        "tax_liquidity_support": death_benefit * float(bundle["tax"]["estate_tax_rate"]),
        "beneficiary_source": source_for(docs, ["beneficiary_count"], "SIGNED_PROFILE"),
        "policy_source": policy.get("source_type", "SIGNED_PROFILE"),
    }


def ilit_output(bundle: dict[str, Any], task_id: str, client_id: str) -> dict[str, Any]:
    core = ilit_core(bundle)
    return {
        "task_id": task_id,
        "client_id": client_id,
        "analysis_type": "ilit_crummey_implementation",
        "recommendation": {
            "primary_action": core["primary_action"],
            "suitability": core["suitability"],
            "risk_flag": core["risk"],
        },
        "gift_plan": {
            "planning_year": core["planning_year"],
            "annual_exclusion_per_beneficiary": money(core["annual_exclusion_per_beneficiary"]),
            "beneficiary_count": core["beneficiary_count"],
            "annual_exclusion_capacity": money(core["annual_exclusion_capacity"]),
            "annual_premium": money(core["annual_premium"]),
            "premium_gap": money(core["premium_gap"]),
        },
        "administration": {
            "notices_required": core["notices_required"],
            "contribution_date": core["contribution_date"],
            "notice_due_date": core["notice_due_date"],
            "withdrawal_window_end": core["withdrawal_window_end"],
            "earliest_premium_payment_date": core["earliest_premium_payment_date"],
            "dedicated_bank_account_required": core["dedicated_bank_account_required"],
        },
        "estate_result": {
            "death_benefit": money(core["death_benefit"]),
            "estate_inclusion_risk": core["risk"],
            "projected_outside_estate_if_implemented": money(core["projected_outside_estate_if_implemented"]),
            "tax_liquidity_support": money(core["tax_liquidity_support"]),
        },
        "source_resolution": {
            "controlling_beneficiary_source": core["beneficiary_source"],
            "controlling_policy_source": core["policy_source"],
        },
    }


def strength(value: Any) -> int:
    return {"low": 0, "moderate": 1, "high": 2}.get(str(value).lower(), 0)


def estate_context(bundle: dict[str, Any]) -> dict[str, Any]:
    client = bundle["client"]
    docs = bundle["docs"]
    planning_year = int(fact(client, docs, "planning_year")[0])
    filing_status = str(fact(client, docs, "filing_status")[0])
    marital_status = str(fact(client, docs, "marital_status")[0]).lower()
    estate_value = float(fact(client, docs, "estate_value")[0])
    liquid_assets = float(fact(client, docs, "liquid_assets")[0])
    exemption = policy_value(bundle["tax"], "estate_tax_exemption", planning_year)
    exemption_units = 2 if filing_status == "MFJ" or marital_status == "married" else 1
    exemption_used = exemption * exemption_units
    taxable_estate = max(0.0, estate_value - exemption_used)
    exposure = taxable_estate * float(bundle["tax"]["estate_tax_rate"])
    gap = max(0.0, exposure - liquid_assets)
    return {
        "planning_year": planning_year,
        "exemption_used": money(exemption_used),
        "taxable_estate": money(taxable_estate),
        "estate_tax_exposure": money(exposure),
        "liquid_assets_available": money(liquid_assets),
        "liquidity_gap_before_planning": money(gap),
    }


def trust_core(bundle: dict[str, Any]) -> dict[str, Any]:
    client = bundle["client"]
    docs = bundle["docs"]
    trust = first_or_die(bundle["trusts"], "trust candidate")
    family_priority = fact(client, docs, "family_transfer_priority", "low")[0]
    philanthropic_intent = fact(client, docs, "philanthropic_intent", "low")[0]
    preferred = "CRAT" if strength(philanthropic_intent) > strength(family_priority) else "GRAT"
    asset = float(trust["asset_value"])
    growth = float(trust["expected_growth_rate"])
    grat_term = int(trust["grat_term_years"])
    grat_annuity = float(trust["grat_annuity_rate"])
    crat_term = int(trust["crat_term_years"])
    crat_payout = float(trust["crat_payout_rate"])
    grat_remainder = max(0.0, asset * (1.0 + growth) ** grat_term - asset * grat_annuity * grat_term)
    crat_remainder = max(0.0, asset * (1.0 + growth) ** crat_term - asset * crat_payout * crat_term)

    return {
        "preferred_strategy": preferred,
        "rationale_code": "PHILANTHROPIC_PRIORITY" if preferred == "CRAT" else "CHILDREN_TRANSFER_PRIORITY",
        "alternate_role": "SECONDARY_FAMILY_TRANSFER_TOOL" if preferred == "CRAT" else "SECONDARY_CHARITABLE_TOOL",
        "estate_context": estate_context(bundle),
        "grat_term_years": grat_term,
        "grat_remainder": grat_remainder,
        "grat_estate_tax_reduction": grat_remainder * float(bundle["tax"]["estate_tax_rate"]),
        "crat_term_years": crat_term,
        "crat_remainder": crat_remainder,
        "crat_income_tax_deduction": crat_remainder * float(bundle["tax"]["charitable_deduction_rate"]),
        "crat_family_transfer_fit": "MODERATE" if preferred == "CRAT" and strength(family_priority) >= 1 else "LOW",
        "goal_source": source_for(docs, ["family_transfer_priority", "philanthropic_intent"], "SIGNED_PROFILE"),
        "asset_source": trust.get("source_type", "ATTORNEY_MEMO"),
    }


def trust_output(bundle: dict[str, Any], task_id: str, client_id: str) -> dict[str, Any]:
    core = trust_core(bundle)
    return {
        "task_id": task_id,
        "client_id": client_id,
        "analysis_type": "trust_comparison",
        "recommendation": {
            "preferred_strategy": core["preferred_strategy"],
            "rationale_code": core["rationale_code"],
            "alternate_role": core["alternate_role"],
        },
        "estate_context": core["estate_context"],
        "grat": {
            "term_years": core["grat_term_years"],
            "projected_remainder_to_heirs": money(core["grat_remainder"]),
            "estimated_estate_tax_reduction": money(core["grat_estate_tax_reduction"]),
            "mortality_inclusion_risk": "TERM_SURVIVAL_REQUIRED",
        },
        "crat": {
            "term_years": core["crat_term_years"],
            "projected_charitable_remainder": money(core["crat_remainder"]),
            "estimated_income_tax_deduction": money(core["crat_income_tax_deduction"]),
            "family_transfer_fit": core["crat_family_transfer_fit"],
        },
        "source_resolution": {
            "controlling_goal_source": core["goal_source"],
            "controlling_asset_source": core["asset_source"],
        },
    }


def estate_liquidity_output(bundle: dict[str, Any], task_id: str, client_id: str) -> dict[str, Any]:
    ilit = ilit_core(bundle)
    trust = trust_core(bundle)
    risk = ilit["risk"]

    if risk != "LOW_IF_FORMALITIES_MET":
        primary_action = "ILIT_WITH_EXEMPTION_REVIEW"
        sequencing = "ILIT_FIRST_THEN_ATTORNEY_REVIEW"
    elif trust["preferred_strategy"] == "CRAT":
        primary_action = "CRAT_WITH_LIQUIDITY_REVIEW"
        sequencing = "TRUST_DECISION_FIRST"
    else:
        primary_action = "COMBINE_ILIT_AND_GRAT"
        sequencing = "ILIT_FIRST_THEN_GRAT"

    actions = {"ATTORNEY_DRAFT_REVIEW", "ILIT_CRUMMEY_NOTICE_CYCLE"}
    if trust["preferred_strategy"] == "CRAT":
        actions.add("CRAT_FOR_CHARITABLE_REMAINDER")
    else:
        actions.add("GRAT_FOR_APPRECIATING_SHARES")
    if ilit["premium_gap"] > 0:
        actions.add("LIFETIME_EXEMPTION_ALLOCATION")

    return {
        "task_id": task_id,
        "client_id": client_id,
        "analysis_type": "estate_liquidity_action_plan",
        "recommendation": {
            "primary_action": primary_action,
            "sequencing": sequencing,
            "risk_flag": risk,
        },
        "estate_context": trust["estate_context"],
        "ilit": {
            "annual_exclusion_capacity": money(ilit["annual_exclusion_capacity"]),
            "premium_gap": money(ilit["premium_gap"]),
            "estate_inclusion_risk": risk,
            "projected_outside_estate_if_implemented": money(ilit["projected_outside_estate_if_implemented"]),
        },
        "trust_transfer": {
            "preferred_strategy": trust["preferred_strategy"],
            "projected_remainder_to_heirs": money(trust["grat_remainder"]),
            "estimated_estate_tax_reduction": money(trust["grat_estate_tax_reduction"]),
            "projected_charitable_remainder": money(trust["crat_remainder"]),
        },
        "action_set": sorted(actions),
        "source_resolution": {
            "controlling_goal_source": trust["goal_source"],
            "controlling_policy_source": ilit["policy_source"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default=os.environ.get("API_BASE", "http://task-env:9008/"))
    parser.add_argument("--prompt")
    parser.add_argument("--memo")
    parser.add_argument("--template")
    parser.add_argument("--client-id")
    parser.add_argument("--task-id")
    parser.add_argument("--analysis-type")
    parser.add_argument("--horizon-year", type=int)
    args = parser.parse_args()

    prompt = load_text(args.prompt)
    memo = load_text(args.memo)
    template = json.loads(load_text(args.template)) if args.template else {"fields": {}}
    client_id = args.client_id or find_client_id(prompt, memo)
    task_id = infer_task_id(args.prompt, args.task_id)
    analysis_type = infer_analysis_type(template, prompt, memo, args.analysis_type)
    horizon_year = infer_horizon(memo, args.horizon_year)
    bundle = client_bundle(args.api_base, client_id)

    if analysis_type == "roth_conversion_rmd":
        output = roth_output(bundle, task_id, client_id, horizon_year)
    elif analysis_type == "ilit_crummey_implementation":
        output = ilit_output(bundle, task_id, client_id)
    elif analysis_type == "trust_comparison":
        output = trust_output(bundle, task_id, client_id)
    elif analysis_type == "estate_liquidity_action_plan":
        output = estate_liquidity_output(bundle, task_id, client_id)
    else:
        raise SystemExit(f"Unsupported analysis_type: {analysis_type}")

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
