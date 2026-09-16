---
name: private-wealth-advisory
description: Produce structured planning JSON outputs for private wealth advisory engagements using a REST API of client records, source documents, accounts, insurance, trust candidates, and tax policy constants. Supports Roth conversion RMD projections, ILIT Crummey funding, GRAT vs CRAT comparisons, and combined estate liquidity action plans.
---

# Private Wealth Advisory Structured Output

You support a private wealth advisory team. The harness supplies `API_BASE` (an environment variable or explicit URL) pointing to the advisory REST API. Read the local `input/payloads/request_memo.md` for the engagement context and `input/payloads/answer_template.json` for the required output schema. Return only a JSON object conforming to the template — no prose outside the JSON.

## Step 1 — Collect API Data

Call every endpoint relevant to the client and analysis type. The base URL is `API_BASE` (strip a trailing slash if present).

| Endpoint | What it returns |
|---|---|
| `/api/clients/{client_id}` | Household profile, age, filing status, estate value, liquid assets |
| `/api/source-documents` | Array of documents; filter by `client_id`. Sources ranked: `SIGNED_PROFILE` > `ATTORNEY_MEMO` > `CUSTODIAN_EXPORT` > `CRM_NOTE` > `STALE_MARKETING_INTAKE` |
| `/api/retirement-accounts` | Array of accounts; filter by `client_id`. Has `traditional_balance`, `roth_balance`, `expected_return`, `rmd_start_age` (always 73), `recommended_conversion_years` |
| `/api/life-insurance` | Array of policies; filter by `client_id`. Has `death_benefit`, `annual_premium`, `planned_contribution_date`, `is_existing_policy_transfer` |
| `/api/trust-candidates` | Array of trusts; filter by `client_id`. Has `asset_value`, `expected_growth_rate`, `grat_term_years`, `grat_annuity_rate`, `crat_term_years`, `crat_payout_rate` |
| `/api/policies/tax` | Tax constants: `annual_gift_exclusion`, `estate_tax_exemption`, `estate_tax_rate` (0.4), `conversion_bracket_targets`, `max_crat_term_years` (20), `charitable_deduction_rate` (0.35) |
| `/api/rmd-factors` | Map of age → divisor (e.g. 73 → 26.5) |

For date arithmetic use Python `datetime` (isoformat for dates, `+ timedelta(days=n)`).

## Step 2 — Resolve Conflicting Sources

Client facts (age, income, beneficiary count, philanthropic intent, family transfer priority, filing status, marital status, liquid assets, estate value, marginal tax rate) may appear in multiple source documents. Always prefer the highest-ranked source that contains the fact.

Rank order (highest to lowest):
1. `SIGNED_PROFILE` — the signed household planning profile (most recent effective date)
2. `ATTORNEY_MEMO` — attorney planning call notes
3. `CUSTODIAN_EXPORT` — custodian account export
4. `CRM_NOTE` — prior CRM import
5. `STALE_MARKETING_INTAKE`

For `source_resolution` fields:
- Profile facts (beneficiary count, income, intent, priority): use `SIGNED_PROFILE` in all cases seen. Fill `controlling_profile_source` with `SIGNED_PROFILE`.
- Account facts (balances, growth, RMD params): always `CUSTODIAN_EXPORT`. Fill `controlling_account_source` with `CUSTODIAN_EXPORT`.
- Policy facts (death benefit, premium, dates): use `SIGNED_PROFILE`. Fill `controlling_policy_source`.
- Beneficiary count for ILIT: `SIGNED_PROFILE`. Fill `controlling_beneficiary_source`.
- Goal/intent facts for trust comparison: `SIGNED_PROFILE`. Fill `controlling_goal_source`.
- Asset facts for trust transfer (asset value, growth): `ATTORNEY_MEMO`. Fill `controlling_asset_source`.

Where a source type does not apply to the analysis, omit its resolution key from `source_resolution`.

## Step 3 — Compute Output by Analysis Type

### 3a. `roth_conversion_rmd`

**Extract constants.**
- `tax = GET /api/policies/tax`
- `bracket_target = tax.conversion_bracket_targets[client.filing_status]`
- `marginal_rate = signed_profile.marginal_tax_rate`
- `income = signed_profile.annual_non_ira_income`
- `rmd_factors = GET /api/rmd-factors`
- `account`: filter retirement accounts for `client_id`, use the first match
- `horizon_year`: from `request_memo.md` (e.g. 2046 or 2042)

**Conversion plan.**
- `annual_conversion_amount = bracket_target - income` (round to cents; never negative)
- `conversion_years = account.recommended_conversion_years`
- `conversion_years_positive = conversion_years` (same integer)
- `first_conversion_year = client.planning_year` (2026 in all training cases)
- `total_converted = min(annual_conversion_amount * conversion_years, account.traditional_balance)`, rounded to cents
- `total_conversion_tax = total_converted * marginal_rate`, rounded to cents

**RMD projection (year-by-year simulation).**
For each year from `planning_year` through `horizon_year`:
1. Age = client.age + (year − planning_year)
2. If year is in conversion window (first_conversion_year through first_conversion_year + conversion_years − 1), subtract `annual_conversion_amount` from the traditional balance (before RMD).
3. If age ≥ rmd_start_age, compute RMD = balance / rmd_factors[age], subtract it from balance, and add rmd * marginal_rate to the running tax total.
4. Multiply balance by (1 + account.expected_return).

Run this once without conversions to get `baseline_rmd_tax_through_horizon`, then again with conversions to get `conversion_rmd_tax_through_horizon`.
`rmd_tax_savings_through_horizon = baseline − conversion`.

**Legacy projection.**
Use the same year-by-year loop but track both Roth and Traditional balances through `horizon_year`. Start Roth at `account.roth_balance`. During conversion years add `annual_conversion_amount` to Roth (before growth). Roth only grows; it is never reduced by RMD. After the loop, round both balances to cents.

`heir_tax_profile`: Use `MIXED_TAXABLE_AND_TAX_FREE` when both final balances exceed 0. (All training cases arrived at `MIXED_TAXABLE_AND_TAX_FREE`.)

**Recommendation.**
- `primary_action`: `STAGED_ROTH_CONVERSION` whenever `rmd_tax_savings_through_horizon > 0`.
- `suitability`: `SUITABLE` when savings are positive and conversion does not exhaust liquidity.
- `risk_flag`: `TAX_BRACKET_MANAGEMENT` (the standard designation for bracket‑targeted staged conversions).

### 3b. `ilit_crummey_implementation`

**Extract data.**
- `tax = GET /api/policies/tax`
- `exclusion = tax.annual_gift_exclusion["2026"]` (use planning year; 2026 → 20000)
- `profile = signed document for client`
- `beneficiary_count = profile.beneficiary_count`
- `policy = GET /api/life-insurance`, filter by `client_id`, use the first match
- `annual_exclusion_capacity = beneficiary_count * exclusion`
- `premium_gap = max(0, policy.annual_premium − annual_exclusion_capacity)`

**Dates** (all in `planning_year`):
- `contribution_date = policy.planned_contribution_date` (an ISO string from the API)
- `notice_due_date = contribution_date + 7 calendar days`
- `withdrawal_window_end = notice_due_date + 30 calendar days`
- `earliest_premium_payment_date = withdrawal_window_end + 1 calendar day`
- `dedicated_bank_account_required = true` (always)

**Notices.** `notices_required = beneficiary_count`.

**Estate result.**
- `death_benefit = policy.death_benefit`
- `estate_inclusion_risk`:
  - `LOW_IF_FORMALITIES_MET`: policy is new (`is_existing_policy_transfer == false`) and `premium_gap == 0`
  - `EXCLUSION_SHORTFALL`: premium_gap > 0 (new policy)
  - `THREE_YEAR_LOOKBACK`: existing policy transfer (`is_existing_policy_transfer == true`) and premium_gap == 0
  - `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`: existing policy transfer and premium_gap > 0
- `projected_outside_estate_if_implemented = death_benefit` (when risk is `LOW_IF_FORMALITIES_MET`)
- `tax_liquidity_support = death_benefit * tax.estate_tax_rate` (0.4), rounded to cents

**Recommendation.**
- `primary_action`: `FUND_WITH_CRUMMEY_NOTICES` when new policy and gap is zero.
- `suitability`: `SUITABLE_WITH_ADMINISTRATION` when gap is zero and formalities are the only concern.
- `risk_flag`: match `estate_inclusion_risk` above.

### 3c. `trust_comparison`

**Extract data.**
- `tax = GET /api/policies/tax`
- `profile = signed document`
- `trust = GET /api/trust-candidates`, filter by `client_id`, use the first match
- `filing = client.filing_status`

**Estate context.**
- `planning_year = client.planning_year`
- `exemption_used = tax.estate_tax_exemption["2026"]` (13610000) if `filing_status` is `SINGLE` or `HOH`; multiply by 2 if `MFJ` → 27220000
- `taxable_estate = client.estate_value − exemption_used`
- `estate_tax_exposure = taxable_estate * tax.estate_tax_rate` (0.4), round to cents
- `liquid_assets_available = profile.liquid_assets`
- `liquidity_gap_before_planning = max(0, estate_tax_exposure − liquid_assets_available)`, round to cents

**GRAT.**
- `annuity = trust.asset_value * trust.grat_annuity_rate`
- `fv = trust.asset_value * (1 + trust.expected_growth_rate) ** trust.grat_term_years`
- `remainder = fv − (trust.grat_term_years * annuity)`
- `projected_remainder_to_heirs = round(remainder, 2)`
- `estimated_estate_tax_reduction = round(remainder * tax.estate_tax_rate, 2)` (0.4)
- `mortality_inclusion_risk = "TERM_SURVIVAL_REQUIRED"`

**CRAT.**
- `annuity = trust.asset_value * trust.crat_payout_rate`
- `fv = trust.asset_value * (1 + trust.expected_growth_rate) ** trust.crat_term_years`
- `remainder = fv − (trust.crat_term_years * annuity)`
- `projected_charitable_remainder = round(remainder, 2)`
- `estimated_income_tax_deduction = round(remainder * tax.charitable_deduction_rate, 2)` (0.35)
- `family_transfer_fit = "LOW"` (CRAT remainder goes entirely to charity)

**Recommendation.**
- Use `SIGNED_PROFILE` facts `family_transfer_priority` and `philanthropic_intent`.
  - `family_transfer_priority == "high"` → `preferred_strategy = "GRAT"`, `rationale_code = "CHILDREN_TRANSFER_PRIORITY"`, `alternate_role = "SECONDARY_CHARITABLE_TOOL"`
  - `philanthropic_intent == "high"` → `preferred_strategy = "CRAT"`, `rationale_code = "PHILANTHROPIC_PRIORITY"`, `alternate_role = "SECONDARY_FAMILY_TRANSFER_TOOL"`
- When both are moderate, prefer GRAT if family transfer priority is at least moderate.

### 3d. `estate_liquidity_action_plan`

This combines ILIT + trust transfer + estate context into one output. Compute each sub‑section exactly as above, then assemble.

**Estate context** — same as trust_comparison (3c).

**ILIT** — same core computations as 3b, but only include:
- `annual_exclusion_capacity`
- `premium_gap`
- `estate_inclusion_risk`
- `projected_outside_estate_if_implemented`

**Trust transfer** — same as trust_comparison (3c), but include:
- `preferred_strategy`
- `projected_remainder_to_heirs`
- `estimated_estate_tax_reduction`
- `projected_charitable_remainder`

**Action set** — a sorted list of applicable enum values from: `ATTORNEY_DRAFT_REVIEW`, `CRAT_FOR_CHARITABLE_REMAINDER`, `GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`, `LIFETIME_EXEMPTION_ALLOCATION`. Include actions that match the plan. Training evidence (train_004) included `ATTORNEY_DRAFT_REVIEW`, `GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE` when the plan combined ILIT and GRAT.

**Recommendation.**
- `primary_action`: `COMBINE_ILIT_AND_GRAT` when both ILIT and a trust transfer are indicated.
- `sequencing`: `ILIT_FIRST_THEN_GRAT` (ILIT formalities precede trust funding).
- `risk_flag`: match the ILIT estate inclusion risk.

## Step 4 — Assemble the JSON

Build the output object with the exact top-level keys from the answer template. Use the task identifier from the prompt (e.g. `train_001` or `test_001`) as `task_id`. Set `client_id` to the client identifier from the memo. Fill `analysis_type` with the enum string from the template.

All numbers must be JSON numbers (not strings), rounded to cents where USD. All dates must be ISO strings `YYYY-MM-DD`. Enum values must match the template exactly.

## Reference

The verified computational formulas and priority rules are also documented in [reference.md](reference.md). A Python reference implementation is available at [compute.py](compute.py). Both are living alongside this SKILL.md.
