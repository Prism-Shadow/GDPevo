#!/usr/bin/env python3
"""Build structured advisory-planning JSON from the task-group API.

The script uses only the standard library. It intentionally contains no
task-specific client IDs or expected answers.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


ANALYSIS_TYPES = {
    "roth_conversion_rmd",
    "ilit_crummey_implementation",
    "trust_comparison",
    "estate_liquidity_action_plan",
}

SOURCE_PRIORITY = ("SIGNED_PROFILE", "ATTORNEY_MEMO", "CRM_NOTE")
GOAL_SCORE = {"low": 1, "moderate": 2, "high": 3}


def money(value: float) -> float:
    return float(round(float(value) + 1e-9, 2))


def load_json_url(api_base: str, path: str):
    url = api_base.rstrip("/") + path
    try:
        with urlopen(url, timeout=15) as response:
            return json.load(response)
    except HTTPError as exc:
        raise SystemExit(f"API request failed for {url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise SystemExit(f"API request failed for {url}: {exc.reason}") from exc


def read_text(path: str | None) -> str:
    if not path:
        return ""
    return Path(path).read_text()


def parse_memo(path: str | None) -> dict:
    text = read_text(path)
    result: dict[str, object] = {}
    match = re.search(r"Client ID:\s*([A-Z]+-\d+)", text)
    if match:
        result["client_id"] = match.group(1)
    match = re.search(r"Planning horizon year:\s*(\d{4})", text)
    if match:
        result["horizon_year"] = int(match.group(1))

    lowered = text.lower()
    if "estate liquidity" in lowered or "action plan" in lowered:
        result["analysis_type"] = "estate_liquidity_action_plan"
    elif "roth" in lowered or "rmd" in lowered:
        result["analysis_type"] = "roth_conversion_rmd"
    elif "ilit" in lowered or "crummey" in lowered:
        result["analysis_type"] = "ilit_crummey_implementation"
    elif ("grat" in lowered and "crat" in lowered) or "trust" in lowered:
        result["analysis_type"] = "trust_comparison"
    return result


def parse_template(path: str | None) -> dict:
    if not path:
        return {}
    template = json.loads(Path(path).read_text())
    analysis_field = template.get("fields", {}).get("analysis_type", "")
    match = re.search(r"enum:\s*([a-z_]+)", analysis_field)
    return {"analysis_type": match.group(1)} if match else {}


def infer_task_id(*paths: str | None) -> str | None:
    env_task_id = os.environ.get("TASK_ID")
    if env_task_id:
        return env_task_id
    for path in paths:
        if not path:
            continue
        for part in Path(path).parts:
            if re.fullmatch(r"(?:train|test)_\d+", part):
                return part
    for part in Path.cwd().parts:
        if re.fullmatch(r"(?:train|test)_\d+", part):
            return part
    return None


def latest_doc(docs: list[dict], source_type: str) -> dict | None:
    matches = [doc for doc in docs if doc.get("source_type") == source_type]
    if not matches:
        return None
    return sorted(matches, key=lambda doc: doc.get("effective_date", ""))[-1]


def fetch_bundle(api_base: str, client_id: str) -> dict:
    client = load_json_url(api_base, f"/api/clients/{client_id}")
    all_docs = load_json_url(api_base, "/api/source-documents")
    all_accounts = load_json_url(api_base, "/api/retirement-accounts")
    all_life = load_json_url(api_base, "/api/life-insurance")
    all_trusts = load_json_url(api_base, "/api/trust-candidates")
    policy = load_json_url(api_base, "/api/policies/tax")
    rmd_factors = load_json_url(api_base, "/api/rmd-factors")

    docs = [doc for doc in all_docs if doc.get("client_id") == client_id]
    bundle = {
        "client": client,
        "docs": docs,
        "docs_by_source": {
            source: latest_doc(docs, source)
            for source in SOURCE_PRIORITY
            if latest_doc(docs, source)
        },
        "accounts": [item for item in all_accounts if item.get("client_id") == client_id],
        "life": [item for item in all_life if item.get("client_id") == client_id],
        "trusts": [item for item in all_trusts if item.get("client_id") == client_id],
        "policy": policy,
        "rmd_factors": rmd_factors,
    }
    return bundle


def one(items: list[dict], label: str) -> dict:
    if not items:
        raise SystemExit(f"No {label} record found for client")
    if len(items) > 1:
        return items[0]
    return items[0]


def fact(bundle: dict, key: str, sources: tuple[str, ...] = SOURCE_PRIORITY):
    for source in sources:
        doc = bundle["docs_by_source"].get(source)
        facts = (doc or {}).get("facts", {})
        if key in facts:
            return facts[key], source
    client = bundle["client"]
    if key in client:
        return client[key], "CLIENT"
    raise SystemExit(f"Missing required fact: {key}")


def controlling_profile_source(bundle: dict) -> str:
    for source in SOURCE_PRIORITY:
        if bundle["docs_by_source"].get(source):
            return source
    return "CRM_NOTE"


def add_days(date_text: str, days: int) -> str:
    return (date.fromisoformat(date_text) + timedelta(days=days)).isoformat()


def estate_context(bundle: dict) -> dict:
    planning_year = int(fact(bundle, "planning_year")[0])
    filing_status = str(fact(bundle, "filing_status")[0])
    marital_status = str(fact(bundle, "marital_status")[0])
    estate_value = float(fact(bundle, "estate_value", ("ATTORNEY_MEMO", "SIGNED_PROFILE", "CRM_NOTE"))[0])
    liquid_assets = float(fact(bundle, "liquid_assets")[0])

    exemption = float(bundle["policy"]["estate_tax_exemption"][str(planning_year)])
    if filing_status == "MFJ" or marital_status.lower() == "married":
        exemption *= 2
    taxable_estate = max(0.0, estate_value - exemption)
    estate_tax_exposure = taxable_estate * float(bundle["policy"]["estate_tax_rate"])
    liquidity_gap = max(0.0, estate_tax_exposure - liquid_assets)
    return {
        "planning_year": planning_year,
        "exemption_used": money(exemption),
        "taxable_estate": money(taxable_estate),
        "estate_tax_exposure": money(estate_tax_exposure),
        "liquid_assets_available": money(liquid_assets),
        "liquidity_gap_before_planning": money(liquidity_gap),
    }


def first_rmd_year(planning_year: int, age: int, rmd_start_age: int) -> int:
    if age >= rmd_start_age:
        return planning_year
    return planning_year + (rmd_start_age - age)


def rmd_factor(factors: dict, age: int) -> float:
    value = factors.get(str(age))
    if value is None:
        raise SystemExit(f"No RMD factor for age {age}")
    return float(value)


def project_baseline_rmd_tax(
    traditional_balance: float,
    expected_return: float,
    marginal_tax_rate: float,
    age: int,
    planning_year: int,
    horizon_year: int,
    rmd_start_age: int,
    factors: dict,
) -> float:
    balance = float(traditional_balance)
    total_tax = 0.0
    current_age = int(age)
    for _year in range(planning_year, horizon_year + 1):
        if current_age >= rmd_start_age:
            distribution = balance / rmd_factor(factors, current_age)
            total_tax += distribution * marginal_tax_rate
            balance -= distribution
        balance *= 1.0 + expected_return
        current_age += 1
    return total_tax


def project_conversion_rmd(
    traditional_balance: float,
    roth_balance: float,
    expected_return: float,
    marginal_tax_rate: float,
    age: int,
    planning_year: int,
    horizon_year: int,
    rmd_start_age: int,
    factors: dict,
    annual_conversion: float,
    conversion_years_positive: int,
) -> tuple[float, float, float]:
    traditional = float(traditional_balance)
    roth = float(roth_balance)
    total_rmd_tax = 0.0
    current_age = int(age)
    for index, _year in enumerate(range(planning_year, horizon_year + 1)):
        if index < conversion_years_positive and annual_conversion > 0:
            conversion = min(annual_conversion, traditional)
            traditional -= conversion
            roth += conversion
        if current_age >= rmd_start_age:
            distribution = traditional / rmd_factor(factors, current_age)
            total_rmd_tax += distribution * marginal_tax_rate
            traditional -= distribution
        traditional *= 1.0 + expected_return
        roth *= 1.0 + expected_return
        current_age += 1
    return total_rmd_tax, roth, traditional


def build_roth(task_id: str, client_id: str, bundle: dict, horizon_year: int) -> dict:
    account = one(bundle["accounts"], "retirement account")
    planning_year = int(fact(bundle, "planning_year")[0])
    age = int(fact(bundle, "age")[0])
    filing_status = str(fact(bundle, "filing_status")[0])
    annual_income = float(fact(bundle, "annual_non_ira_income")[0])
    marginal_tax_rate = float(fact(bundle, "marginal_tax_rate")[0])
    liquid_assets = float(fact(bundle, "liquid_assets")[0])

    bracket_target = float(bundle["policy"]["conversion_bracket_targets"][filing_status])
    suggested_years = int(account["recommended_conversion_years"])
    traditional_balance = float(account["traditional_balance"])
    annual_conversion = max(0.0, bracket_target - annual_income)
    if suggested_years > 0 and annual_conversion * suggested_years > traditional_balance:
        annual_conversion = traditional_balance / suggested_years
    conversion_years_positive = suggested_years if annual_conversion > 0 else 0
    conversion_years = conversion_years_positive
    total_converted = annual_conversion * conversion_years_positive
    total_conversion_tax = total_converted * marginal_tax_rate

    if traditional_balance <= 0 or annual_conversion <= 0:
        primary_action = "NO_CONVERSION" if traditional_balance <= 0 else "DEFER"
        suitability = "DEFER"
        risk_flag = "RMD_NEAR_TERM"
    elif total_conversion_tax > liquid_assets:
        primary_action = "STAGED_ROTH_CONVERSION"
        suitability = "BORDERLINE"
        risk_flag = "LIQUIDITY_CONSTRAINT"
    else:
        primary_action = "STAGED_ROTH_CONVERSION"
        suitability = "SUITABLE"
        risk_flag = "TAX_BRACKET_MANAGEMENT"

    baseline_tax = project_baseline_rmd_tax(
        traditional_balance,
        float(account["expected_return"]),
        marginal_tax_rate,
        age,
        planning_year,
        horizon_year,
        int(account["rmd_start_age"]),
        bundle["rmd_factors"],
    )
    conversion_tax, roth_horizon, traditional_horizon = project_conversion_rmd(
        traditional_balance,
        float(account.get("roth_balance", 0.0)),
        float(account["expected_return"]),
        marginal_tax_rate,
        age,
        planning_year,
        horizon_year,
        int(account["rmd_start_age"]),
        bundle["rmd_factors"],
        annual_conversion,
        conversion_years_positive,
    )

    if roth_horizon >= 2 * traditional_horizon:
        heir_tax_profile = "MOSTLY_TAX_FREE"
    elif traditional_horizon >= 2 * roth_horizon:
        heir_tax_profile = "MOSTLY_TAXABLE"
    else:
        heir_tax_profile = "MIXED_TAXABLE_AND_TAX_FREE"

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
            "conversion_years_positive": conversion_years_positive,
            "annual_conversion_amount": money(annual_conversion),
            "total_converted": money(total_converted),
            "total_conversion_tax": money(total_conversion_tax),
        },
        "rmd_projection": {
            "horizon_year": horizon_year,
            "first_rmd_year": first_rmd_year(planning_year, age, int(account["rmd_start_age"])),
            "baseline_rmd_tax_through_horizon": money(baseline_tax),
            "conversion_rmd_tax_through_horizon": money(conversion_tax),
            "rmd_tax_savings_through_horizon": money(baseline_tax - conversion_tax),
        },
        "legacy_projection": {
            "projected_roth_balance_horizon": money(roth_horizon),
            "projected_traditional_balance_horizon": money(traditional_horizon),
            "heir_tax_profile": heir_tax_profile,
        },
        "source_resolution": {
            "controlling_profile_source": controlling_profile_source(bundle),
            "controlling_account_source": account.get("source_type", "CUSTODIAN_EXPORT"),
        },
    }


def ilit_risk_and_recommendation(premium_gap: float, is_existing_transfer: bool) -> tuple[str, str, str]:
    has_shortfall = premium_gap > 0
    if is_existing_transfer and has_shortfall:
        return (
            "DISCLOSE_LOOKBACK_AND_USE_EXEMPTION",
            "BORDERLINE",
            "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL",
        )
    if is_existing_transfer:
        return (
            "USE_NEW_POLICY_OR_ACCEPT_LOOKBACK",
            "BORDERLINE",
            "THREE_YEAR_LOOKBACK",
        )
    if has_shortfall:
        return (
            "USE_LIFETIME_EXEMPTION_FOR_SHORTFALL",
            "BORDERLINE",
            "EXCLUSION_SHORTFALL",
        )
    return (
        "FUND_WITH_CRUMMEY_NOTICES",
        "SUITABLE_WITH_ADMINISTRATION",
        "LOW_IF_FORMALITIES_MET",
    )


def build_ilit(task_id: str, client_id: str, bundle: dict) -> dict:
    life = one(bundle["life"], "life-insurance")
    planning_year = int(fact(bundle, "planning_year")[0])
    beneficiary_count = int(fact(bundle, "beneficiary_count")[0])
    annual_exclusion = float(bundle["policy"]["annual_gift_exclusion"][str(planning_year)])
    capacity = annual_exclusion * beneficiary_count
    annual_premium = float(life["annual_premium"])
    premium_gap = max(0.0, annual_premium - capacity)
    primary_action, suitability, risk_flag = ilit_risk_and_recommendation(
        premium_gap,
        bool(life.get("is_existing_policy_transfer", False)),
    )

    contribution_date = life["planned_contribution_date"]
    notice_due_date = add_days(contribution_date, 7)
    withdrawal_window_end = add_days(notice_due_date, 30)
    earliest_payment_date = add_days(withdrawal_window_end, 1)
    death_benefit = float(life["death_benefit"])
    return {
        "task_id": task_id,
        "client_id": client_id,
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
            "annual_exclusion_capacity": money(capacity),
            "annual_premium": money(annual_premium),
            "premium_gap": money(premium_gap),
        },
        "administration": {
            "notices_required": beneficiary_count,
            "contribution_date": contribution_date,
            "notice_due_date": notice_due_date,
            "withdrawal_window_end": withdrawal_window_end,
            "earliest_premium_payment_date": earliest_payment_date,
            "dedicated_bank_account_required": True,
        },
        "estate_result": {
            "death_benefit": money(death_benefit),
            "estate_inclusion_risk": risk_flag,
            "projected_outside_estate_if_implemented": money(death_benefit),
            "tax_liquidity_support": money(death_benefit * float(bundle["policy"]["estate_tax_rate"])),
        },
        "source_resolution": {
            "controlling_beneficiary_source": controlling_profile_source(bundle),
            "controlling_policy_source": controlling_profile_source(bundle),
        },
    }


def trust_metrics(bundle: dict) -> dict:
    trust = one(bundle["trusts"], "trust candidate")
    asset_value = float(trust["asset_value"])
    growth = float(trust["expected_growth_rate"])
    grat_term = int(trust["grat_term_years"])
    annuity_rate = float(trust["grat_annuity_rate"])
    crat_term = int(trust["crat_term_years"])
    payout_rate = float(trust["crat_payout_rate"])

    grat_remainder = asset_value * ((1.0 + growth) ** grat_term) - asset_value * annuity_rate * grat_term
    crat_remainder = asset_value * ((1.0 + growth) ** crat_term) - asset_value * payout_rate * crat_term
    return {
        "grat_term": grat_term,
        "grat_remainder": grat_remainder,
        "grat_tax_reduction": grat_remainder * float(bundle["policy"]["estate_tax_rate"]),
        "crat_term": crat_term,
        "crat_remainder": crat_remainder,
        "crat_income_deduction": crat_remainder * float(bundle["policy"]["charitable_deduction_rate"]),
    }


def trust_preference(bundle: dict) -> tuple[str, str, str, str]:
    family_priority = str(fact(bundle, "family_transfer_priority")[0]).lower()
    philanthropic_intent = str(fact(bundle, "philanthropic_intent")[0]).lower()
    family_score = GOAL_SCORE.get(family_priority, 2)
    charity_score = GOAL_SCORE.get(philanthropic_intent, 2)
    if charity_score > family_score:
        return "CRAT", "PHILANTHROPIC_PRIORITY", "SECONDARY_FAMILY_TRANSFER_TOOL", family_priority
    return "GRAT", "CHILDREN_TRANSFER_PRIORITY", "SECONDARY_CHARITABLE_TOOL", family_priority


def crat_family_transfer_fit(family_priority: str) -> str:
    if family_priority == "high":
        return "LOW"
    if family_priority == "moderate":
        return "MODERATE"
    return "HIGH"


def asset_source(bundle: dict) -> str:
    for source in ("ATTORNEY_MEMO", "SIGNED_PROFILE", "CRM_NOTE"):
        doc = bundle["docs_by_source"].get(source)
        if doc and "estate_value" in doc.get("facts", {}):
            return source
    return "SIGNED_PROFILE"


def build_trust_comparison(task_id: str, client_id: str, bundle: dict) -> dict:
    metrics = trust_metrics(bundle)
    preferred, rationale, alternate, family_priority = trust_preference(bundle)
    return {
        "task_id": task_id,
        "client_id": client_id,
        "analysis_type": "trust_comparison",
        "recommendation": {
            "preferred_strategy": preferred,
            "rationale_code": rationale,
            "alternate_role": alternate,
        },
        "estate_context": estate_context(bundle),
        "grat": {
            "term_years": metrics["grat_term"],
            "projected_remainder_to_heirs": money(metrics["grat_remainder"]),
            "estimated_estate_tax_reduction": money(metrics["grat_tax_reduction"]),
            "mortality_inclusion_risk": "TERM_SURVIVAL_REQUIRED",
        },
        "crat": {
            "term_years": metrics["crat_term"],
            "projected_charitable_remainder": money(metrics["crat_remainder"]),
            "estimated_income_tax_deduction": money(metrics["crat_income_deduction"]),
            "family_transfer_fit": crat_family_transfer_fit(family_priority),
        },
        "source_resolution": {
            "controlling_goal_source": controlling_profile_source(bundle),
            "controlling_asset_source": asset_source(bundle),
        },
    }


def build_estate_liquidity(task_id: str, client_id: str, bundle: dict) -> dict:
    life = one(bundle["life"], "life-insurance")
    planning_year = int(fact(bundle, "planning_year")[0])
    beneficiary_count = int(fact(bundle, "beneficiary_count")[0])
    annual_exclusion = float(bundle["policy"]["annual_gift_exclusion"][str(planning_year)])
    capacity = annual_exclusion * beneficiary_count
    annual_premium = float(life["annual_premium"])
    premium_gap = max(0.0, annual_premium - capacity)
    _ilit_primary, _ilit_suitability, risk_flag = ilit_risk_and_recommendation(
        premium_gap,
        bool(life.get("is_existing_policy_transfer", False)),
    )
    preferred, _rationale, _alternate, _family_priority = trust_preference(bundle)
    metrics = trust_metrics(bundle)

    if risk_flag != "LOW_IF_FORMALITIES_MET":
        primary_action = "ILIT_WITH_EXEMPTION_REVIEW"
        sequencing = "ILIT_FIRST_THEN_ATTORNEY_REVIEW"
    elif preferred == "CRAT":
        primary_action = "CRAT_WITH_LIQUIDITY_REVIEW"
        sequencing = "TRUST_DECISION_FIRST"
    else:
        primary_action = "COMBINE_ILIT_AND_GRAT"
        sequencing = "ILIT_FIRST_THEN_GRAT"

    actions = {"ATTORNEY_DRAFT_REVIEW", "ILIT_CRUMMEY_NOTICE_CYCLE"}
    if premium_gap > 0:
        actions.add("LIFETIME_EXEMPTION_ALLOCATION")
    if preferred == "CRAT":
        actions.add("CRAT_FOR_CHARITABLE_REMAINDER")
    else:
        actions.add("GRAT_FOR_APPRECIATING_SHARES")

    return {
        "task_id": task_id,
        "client_id": client_id,
        "analysis_type": "estate_liquidity_action_plan",
        "recommendation": {
            "primary_action": primary_action,
            "sequencing": sequencing,
            "risk_flag": risk_flag,
        },
        "estate_context": estate_context(bundle),
        "ilit": {
            "annual_exclusion_capacity": money(capacity),
            "premium_gap": money(premium_gap),
            "estate_inclusion_risk": risk_flag,
            "projected_outside_estate_if_implemented": money(float(life["death_benefit"])),
        },
        "trust_transfer": {
            "preferred_strategy": preferred,
            "projected_remainder_to_heirs": money(metrics["grat_remainder"]),
            "estimated_estate_tax_reduction": money(metrics["grat_tax_reduction"]),
            "projected_charitable_remainder": money(metrics["crat_remainder"]),
        },
        "action_set": sorted(actions),
        "source_resolution": {
            "controlling_goal_source": controlling_profile_source(bundle),
            "controlling_policy_source": controlling_profile_source(bundle),
        },
    }


def build_answer(task_id: str, client_id: str, analysis_type: str, bundle: dict, horizon_year: int | None) -> dict:
    if analysis_type == "roth_conversion_rmd":
        if horizon_year is None:
            raise SystemExit("roth_conversion_rmd requires --horizon-year or a memo containing Planning horizon year")
        return build_roth(task_id, client_id, bundle, int(horizon_year))
    if analysis_type == "ilit_crummey_implementation":
        return build_ilit(task_id, client_id, bundle)
    if analysis_type == "trust_comparison":
        return build_trust_comparison(task_id, client_id, bundle)
    if analysis_type == "estate_liquidity_action_plan":
        return build_estate_liquidity(task_id, client_id, bundle)
    raise SystemExit(f"Unsupported analysis_type: {analysis_type}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build advisory planning JSON from task API records.")
    parser.add_argument("--api-base", default=os.environ.get("API_BASE", "http://task-env:9008"))
    parser.add_argument("--client-id")
    parser.add_argument("--task-id")
    parser.add_argument("--analysis-type", choices=sorted(ANALYSIS_TYPES))
    parser.add_argument("--horizon-year", type=int)
    parser.add_argument("--memo", help="Path to request_memo.md for inference")
    parser.add_argument("--template", help="Path to answer_template.json for inference")
    args = parser.parse_args()

    memo_info = parse_memo(args.memo)
    template_info = parse_template(args.template)

    client_id = args.client_id or memo_info.get("client_id")
    if not client_id:
        raise SystemExit("Missing client id. Pass --client-id or --memo.")
    task_id = args.task_id or infer_task_id(args.memo, args.template)
    if not task_id:
        raise SystemExit("Missing task id. Pass --task-id.")
    analysis_type = args.analysis_type or template_info.get("analysis_type") or memo_info.get("analysis_type")
    if analysis_type not in ANALYSIS_TYPES:
        raise SystemExit("Missing or unsupported analysis type. Pass --analysis-type or --template.")
    horizon_year = args.horizon_year if args.horizon_year is not None else memo_info.get("horizon_year")

    bundle = fetch_bundle(args.api_base, str(client_id))
    answer = build_answer(str(task_id), str(client_id), str(analysis_type), bundle, horizon_year)
    print(json.dumps(answer, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
