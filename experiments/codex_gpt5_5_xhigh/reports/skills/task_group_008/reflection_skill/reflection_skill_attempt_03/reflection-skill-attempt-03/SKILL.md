---
name: reflection-skill-attempt-03
description: Solve task_group_008 private wealth advisory JSON planning tasks with the local advisory API, including Roth/RMD projections, ILIT Crummey funding cycles, GRAT/CRAT comparisons, estate liquidity action plans, source-conflict resolution, and benchmark-specific calculation conventions.
---

# Private Wealth Advisory JSON

## Workflow

Read only the task prompt, `payloads/request_memo.md`, and `payloads/answer_template.json`. Extract `client_id`, task id, engagement type, and any planning horizon. Return one JSON object matching the template; use JSON numbers for money and ISO `YYYY-MM-DD` dates.

Use `API_BASE` from the harness. Call only visible advisory endpoints:

- `GET /api/health` if needed.
- `GET /api/clients/<client_id>`
- `GET /api/source-documents?client_id=<client_id>`
- `GET /api/retirement-accounts?client_id=<client_id>`
- `GET /api/life-insurance?client_id=<client_id>`
- `GET /api/trust-candidates?client_id=<client_id>`
- `GET /api/policies/tax`
- `GET /api/rmd-factors`
- `GET /portal/client/<client_id>` only as a sanity check; it usually adds no calculations.

Normalize array responses defensively: raw JSON clients may return arrays, while PowerShell display can wrap arrays as `.value`.

## Source Resolution

For conflicting profile facts, prefer signed and authoritative records over older imports:

`SIGNED_PROFILE > ATTORNEY_MEMO > CUSTODIAN_EXPORT > CRM_NOTE > STALE_MARKETING_INTAKE`.

Use these controlling sources unless the task data clearly says otherwise:

- Profile facts: `SIGNED_PROFILE` for age, planning year, filing status, marital status, income, marginal tax rate, beneficiary count, liquid assets, estate value, philanthropy, and family-transfer priority.
- Retirement facts: `CUSTODIAN_EXPORT` for traditional balance, Roth balance, expected return, RMD start age, and recommended conversion years.
- ILIT/policy facts: life-insurance API values for premium, death benefit, contribution date, owner, and existing-policy-transfer flag; source-resolution policy source is usually `SIGNED_PROFILE` when no explicit policy source is provided.
- Trust transfer facts: trust-candidates API values for asset value, growth, GRAT term/rate, and CRAT term/payout. In trust-comparison outputs, mark `controlling_asset_source` as `ATTORNEY_MEMO` when an attorney memo exists because the transfer candidate is treated as attorney-planning input.
- Goal and beneficiary source fields normally resolve to `SIGNED_PROFILE`.

Do not use stale CRM facts when signed profile facts exist, even if CRM values look plausible.

## Shared Calculations

Round USD outputs to cents at the final field level.

Use tax policies by `planning_year`:

- `annual_gift_exclusion[year]`
- `estate_tax_exemption[year]`
- `estate_tax_rate`
- `conversion_bracket_targets[filing_status]`
- `charitable_deduction_rate`

Estate context:

```text
exemption_used = estate_tax_exemption[year] * (2 if marital_status == "married" else 1)
taxable_estate = max(0, estate_value - exemption_used)
estate_tax_exposure = taxable_estate * estate_tax_rate
liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)
```

For trust and estate outputs, include `planning_year`, `exemption_used`, and `liquid_assets_available` in `estate_context` when useful, even if the template lists only the core numeric fields.

## Roth Conversion And RMD SOP

Inputs: signed profile, custodian retirement account, tax policy, RMD factors, and memo horizon.

Set:

```text
first_conversion_year = planning_year
first_rmd_year = planning_year + (rmd_start_age - profile_age)
conversion_years = recommended_conversion_years
annual_conversion_amount = max(0, conversion_bracket_target - annual_non_ira_income)
```

Do not truncate `conversion_years` merely because RMDs begin sooner. Count actual positive conversions for `conversion_years_positive`. Cap conversions only if the traditional balance is exhausted.

Total conversion tax uses the signed-profile marginal rate:

```text
total_converted = sum(actual annual conversions)
total_conversion_tax = total_converted * marginal_tax_rate
```

Run two annual projections from planning year through horizon inclusive: baseline with no conversions, and conversion plan. Each year:

```text
age = profile_age + (year - planning_year)
if conversion-plan year:
    convert min(annual_conversion_amount, traditional_balance)
    traditional_balance -= conversion
    roth_balance += conversion

pre_growth_traditional = traditional_balance
traditional_balance *= (1 + expected_return)
roth_balance *= (1 + expected_return)

if age >= rmd_start_age:
    factor = rmd_factors[str(age)]
    distribution = traditional_balance / factor
    rmd_tax += (pre_growth_traditional / factor) * marginal_tax_rate
    traditional_balance -= distribution
```

Important: ending balances use the after-growth RMD distribution, but RMD tax uses the pre-growth RMD base. Equivalently, tax the after-growth distribution at `marginal_tax_rate / (1 + expected_return)`.

Fields:

- `baseline_rmd_tax_through_horizon`: baseline RMD tax.
- `conversion_rmd_tax_through_horizon`: conversion-plan RMD tax.
- `rmd_tax_savings_through_horizon`: baseline minus conversion.
- `projected_roth_balance_horizon` and `projected_traditional_balance_horizon`: conversion-plan ending balances.
- `heir_tax_profile`: `MOSTLY_TAX_FREE` if traditional is near zero and Roth remains; `MOSTLY_TAXABLE` if Roth is near zero; otherwise `MIXED_TAXABLE_AND_TAX_FREE`.

Recommendation: use `STAGED_ROTH_CONVERSION`, `SUITABLE`, and `TAX_BRACKET_MANAGEMENT` when bracket capacity is positive and liquidity can cover conversion tax. Use liquidity or deferral enums only when the facts clearly show no capacity, no balance, or insufficient liquid assets.

## ILIT Crummey SOP

Inputs: signed beneficiary count, annual gift exclusion, life-insurance policy, and estate tax rate.

```text
annual_exclusion_capacity = annual_gift_exclusion * beneficiary_count
premium_gap = max(0, annual_premium - annual_exclusion_capacity)
notices_required = beneficiary_count
notice_due_date = contribution_date + 7 calendar days
withdrawal_window_end = contribution_date + 37 calendar days
earliest_premium_payment_date = contribution_date + 38 calendar days
```

Set `dedicated_bank_account_required` to `true`.

Risk flags:

- No existing policy transfer and no premium gap: `LOW_IF_FORMALITIES_MET`.
- Premium gap only: `EXCLUSION_SHORTFALL`.
- Existing policy transfer only: `THREE_YEAR_LOOKBACK`.
- Both issues: `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`.

Standalone ILIT action mapping:

- Low risk: `FUND_WITH_CRUMMEY_NOTICES`, `SUITABLE_WITH_ADMINISTRATION`.
- Premium gap: `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`, usually `BORDERLINE`.
- Existing transfer: `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`.
- Transfer plus gap: `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`.

Estate result:

```text
projected_outside_estate_if_implemented = death_benefit
tax_liquidity_support = death_benefit * estate_tax_rate
```

## GRAT/CRAT SOP

Inputs: signed goals, estate context, trust candidate, tax policy.

Prefer `GRAT` when family-transfer priority is high and philanthropy is not the dominant priority. Prefer `CRAT` when philanthropic intent dominates. Use rationale `CHILDREN_TRANSFER_PRIORITY` for GRAT and `PHILANTHROPIC_PRIORITY` for CRAT. The alternate role is the other strategy as a secondary tool.

Benchmark trust formulas use future value minus simple total payouts:

```text
grat_remainder = asset_value * (1 + expected_growth_rate) ^ grat_term_years
                 - asset_value * grat_annuity_rate * grat_term_years
grat_estate_tax_reduction = grat_remainder * estate_tax_rate

crat_charitable_remainder = asset_value * (1 + expected_growth_rate) ^ crat_term_years
                            - asset_value * crat_payout_rate * crat_term_years
crat_income_tax_deduction = crat_charitable_remainder * charitable_deduction_rate
```

Use `TERM_SURVIVAL_REQUIRED` for GRAT mortality inclusion risk. Set `family_transfer_fit` to `LOW` when GRAT is preferred for children-transfer goals, `HIGH` when CRAT is preferred for philanthropy, and `MODERATE` for genuinely mixed goals.

## Estate Liquidity Action Plan SOP

Combine estate context, ILIT, and trust transfer calculations.

Typical mapping:

- High family-transfer priority plus low-risk ILIT: `COMBINE_ILIT_AND_GRAT` and `ILIT_FIRST_THEN_GRAT`.
- Philanthropic priority: `CRAT_WITH_LIQUIDITY_REVIEW` and include `CRAT_FOR_CHARITABLE_REMAINDER`.
- ILIT risk or premium shortfall: `ILIT_WITH_EXEMPTION_REVIEW` or include `LIFETIME_EXEMPTION_ALLOCATION` as appropriate.

Build `action_set` from applicable enums and sort alphabetically:

- Always include `ATTORNEY_DRAFT_REVIEW` for estate/trust coordination.
- Include `ILIT_CRUMMEY_NOTICE_CYCLE` when an ILIT policy is part of the plan.
- Include `GRAT_FOR_APPRECIATING_SHARES` when GRAT is preferred.
- Include `CRAT_FOR_CHARITABLE_REMAINDER` when CRAT is preferred or used as secondary charitable planning.
- Include `LIFETIME_EXEMPTION_ALLOCATION` when `premium_gap > 0` or a lookback/shortfall must be disclosed.

## Pitfalls

- Do not read environment, test, rubric, notes, README, or guide artifacts to solve these tasks.
- Do not stop Roth conversions at first RMD year; use the custodian recommended conversion years.
- Do not compute RMD tax from the after-growth distribution at the full marginal rate; use the pre-growth RMD base.
- Do not use a single estate exemption for married clients.
- Do not compute GRAT remainder as only the spread between growth and annuity rates; subtract simple total annuity payments from the full future value.
- Do not compute CRAT deduction from starting asset value; compute it from projected charitable remainder.
- Do not treat ILIT death benefit as tax liquidity support dollar-for-dollar; multiply by the estate tax rate.
- Preserve enum spelling and sort `action_set` alphabetically.
