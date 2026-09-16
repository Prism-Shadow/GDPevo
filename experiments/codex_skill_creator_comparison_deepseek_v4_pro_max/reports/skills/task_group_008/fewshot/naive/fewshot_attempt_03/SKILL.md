---
name: private-wealth-advisory
description: Solve private wealth advisory planning tasks (Roth conversion RMD analysis, ILIT Crummey implementation, trust comparison, and estate liquidity action plans) using the advisory API and deterministic formulas.
---

# Private Wealth Advisory Skill

Use this skill when the task involves private wealth advisory planning: Roth conversion and RMD tax summaries, ILIT Crummey funding cycles, GRAT vs CRAT comparisons, or estate liquidity action plans.

## Environment

The task environment provides a private wealth advisory API. Locate the base URL from the harness-supplied `API_BASE` environment variable; if unset, default to `http://task-env:9008/`.

## Step 1 — Fetch all advisory data

Pull every relevant endpoint in parallel. All data is JSON.

```
GET {API_BASE}/api/health            — verify service is available
GET {API_BASE}/api/clients           — all client records
GET {API_BASE}/api/clients/{client_id} — single client detail (if needed)
GET {API_BASE}/api/source-documents  — signed profiles, attorney memos, CRM notes
GET {API_BASE}/api/retirement-accounts — custodian IRA/401(k) exports
GET {API_BASE}/api/life-insurance    — ILIT policy records
GET {API_BASE}/api/trust-candidates  — GRAT/CRAT trust candidates
GET {API_BASE}/api/policies/tax      — tax constants (exclusions, brackets, rates)
GET {API_BASE}/api/rmd-factors       — RMD divisors keyed by integer age
```

## Step 2 — Determine the analysis type and target client

Read the prompt and request memo to find:
- The `client_id` (e.g. CLT-1001, CLT-2001)
- The `analysis_type`: one of `roth_conversion_rmd`, `ilit_crummey_implementation`, `trust_comparison`, or `estate_liquidity_action_plan`
- The `planning_year` (always 2026 in staged environments)
- Any horizon year (e.g. 2046) from the memo
- The `task_id` as supplied (e.g. train_001, test_001)

The analysis type dictates which sections of the output template to populate. The train examples cover four distinct templates; match the template shape to the analysis type exactly.

## Step 3 — Resolve conflicting source records

Some client facts appear in multiple source documents with different values. Always resolve conflicts using the priority rules below, derived from the pattern in five training answers.

### Source priority for profile facts

Higher-trust sources override lower-trust sources. Choose the *most recent* record from the highest available tier:

1. `SIGNED_PROFILE` (most authoritative)
2. `ATTORNEY_MEMO`
3. `CUSTODIAN_EXPORT`
4. `CRM_NOTE`
5. `STALE_MARKETING_INTAKE` (least authoritative)

**Profile facts** resolved this way include: `annual_non_ira_income`, `marginal_tax_rate`, `beneficiary_count`, `philanthropic_intent`, `family_transfer_priority`, `filing_status`, `age`, `liquid_assets`, `estate_value`.

### Source priority for account balances

1. `CUSTODIAN_EXPORT` (authoritative for balances)
2. `SIGNED_PROFILE`
3. `CRM_NOTE`

Use the `/api/retirement-accounts` data as `CUSTODIAN_EXPORT` authority for `traditional_balance`, `roth_balance`, `expected_return`, `rmd_start_age`, `recommended_conversion_years`.

### Source priority for life-insurance / ILIT facts

1. `SIGNED_PROFILE`
2. `ATTORNEY_MEMO`
3. `CUSTODIAN_EXPORT`
4. `CRM_NOTE`

Use `/api/life-insurance` data for `death_benefit`, `annual_premium`, `planned_contribution_date`, `is_existing_policy_transfer`.

### Source priority for trust assets

1. `ATTORNEY_MEMO`
2. `SIGNED_PROFILE`
3. `CRM_NOTE`

Use `/api/trust-candidates` data for trust parameters.

### Source priority for beneficiary count

1. `SIGNED_PROFILE`
2. `ATTORNEY_MEMO`
3. `CUSTODIAN_EXPORT`
4. `CRM_NOTE`
5. `STALE_MARKETING_INTAKE`

### Source priority for goals (philanthropic intent, family transfer priority)

1. `SIGNED_PROFILE`
2. `ATTORNEY_MEMO`
3. `CUSTODIAN_EXPORT`
4. `CRM_NOTE`
5. `STALE_MARKETING_INTAKE`

### In the source_resolution section

For every output template that has a `source_resolution` block, report the source type that *actually controlled* the key facts:

- `controlling_profile_source`: the source type (one of the five enums above) whose profile facts were used
- `controlling_account_source`: the source type for account balances
- `controlling_beneficiary_source`: for ILIT tasks
- `controlling_policy_source`: for ILIT/estate tasks
- `controlling_goal_source`: for trust comparison and estate planning tasks
- `controlling_asset_source`: for trust comparison tasks

## Step 4 — Compute the analysis-specific values

Use the step-by-step formulas below for each analysis type. Run the calculations with the deterministic Python scripts from [calc.py](calc.py). Do not hand-derive values; invoke the script functions with the resolved parameters.

### 4a. Roth conversion / RMD analysis (`roth_conversion_rmd`)

**Parameters from data:**

- `income` = `annual_non_ira_income` from the controlling profile
- `bracket_target` from `/api/policies/tax` → `conversion_bracket_targets[filing_status]`
- `marginal_rate` from the controlling profile
- `traditional_balance`, `roth_balance`, `expected_return` from the controlling account source
- `recommended_conversion_years` from the controlling account source
- `rmd_start_age` from the controlling account source
- `horizon_year` from the memo

**Conversion plan formulas:**

```
annual_conversion_amount = bracket_target - income
total_converted = annual_conversion_amount × recommended_conversion_years
total_conversion_tax = total_converted × marginal_rate
first_conversion_year = planning_year
conversion_years = recommended_conversion_years
conversion_years_positive = recommended_conversion_years
```

**RMD projection formulas:**

Two scenarios: baseline (no conversion) and conversion.

RMD at age = `traditional_balance / rmd_divisor[age]`; divisor from `/api/rmd-factors`.

For baseline: grow the traditional balance from the starting balance at `expected_return` each year. At each year where `age >= rmd_start_age`, compute RMD, tax = RMD × marginal_rate, subtract RMD from balance, then grow. Sum taxes through horizon.

For conversion: same, but also subtract `annual_conversion_amount` from the traditional balance (and add to Roth) during each conversion year (starting in `planning_year`, for `conversion_years` years). The Roth grows at the same `expected_return`. Sum RMD taxes through horizon.

```
baseline_rmd_tax_through_horizon = sum of RMD taxes in baseline scenario
conversion_rmd_tax_through_horizon = sum of RMD taxes in conversion scenario
rmd_tax_savings_through_horizon = baseline - conversion
```

**Legacy projection formulas:**

```
projected_roth_balance_horizon = Roth balance after horizon-year growth
projected_traditional_balance_horizon = Traditional balance after horizon-year growth
```

`heir_tax_profile`: `MOSTLY_TAX_FREE` if Roth > 1.5 × Trad at horizon; `MOSTLY_TAXABLE` if Trad > 1.5 × Roth; `MIXED_TAXABLE_AND_TAX_FREE` otherwise.

**Recommendation rules:**

- `primary_action`: `STAGED_ROTH_CONVERSION` if positive RMD tax savings and bracket headroom exists; `DEFER` if near-term RMD (< 2 years out) but bracket headroom; `NO_CONVERSION` if no savings
- `suitability`: `SUITABLE` if savings > 0 and conversion feasible; `BORDERLINE` if near-RMD; `DEFER` otherwise
- `risk_flag`: `TAX_BRACKET_MANAGEMENT` if tax bracket is the primary concern; `LIQUIDITY_CONSTRAINT` if conversion tax exceeds liquid assets; `RMD_NEAR_TERM` if RMDs begin within 2 years

### 4b. ILIT Crummey implementation (`ilit_crummey_implementation`)

**Parameters:**

- `annual_exclusion_per_beneficiary` from `/api/policies/tax` → `annual_gift_exclusion[planning_year]`
- `beneficiary_count` from controlling beneficiary source
- `annual_premium`, `death_benefit`, `planned_contribution_date`, `is_existing_policy_transfer` from controlling policy source

**Gift plan formulas:**

```
annual_exclusion_capacity = annual_exclusion_per_beneficiary × beneficiary_count
premium_gap = max(0, annual_premium - annual_exclusion_capacity)
```

**Administration timeline (Crummey mechanics):**

- `contribution_date` = `planned_contribution_date`
- `notice_due_date` = contribution_date + 7 days
- `withdrawal_window_end` = notice_due_date + 30 days
- `earliest_premium_payment_date` = withdrawal_window_end + 1 day
- `notices_required` = `beneficiary_count`
- `dedicated_bank_account_required` = true when premium_gap == 0

**Estate result:**

- `death_benefit` as provided
- `estate_inclusion_risk`: `LOW_IF_FORMALITIES_MET` if new policy and formalities followed; `EXCLUSION_SHORTFALL` if premium > exclusion capacity; `THREE_YEAR_LOOKBACK` if existing policy transfer; `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` if both
- `projected_outside_estate_if_implemented` = death_benefit if LOW_IF_FORMALITIES_MET else 0
- `tax_liquidity_support` = death_benefit × 0.4

**Recommendation rules:**

- `primary_action`: `FUND_WITH_CRUMMEY_NOTICES` if premium fits within exclusion; `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` if premium gap > 0 without lookback; `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` if existing transfer without gap; `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` if existing transfer with gap
- `suitability`: `SUITABLE_WITH_ADMINISTRATION` if low risk; `BORDERLINE` if gap exists; `NOT_SUITABLE` if lookback + gap
- `risk_flag`: matches `estate_inclusion_risk`

### 4c. Trust comparison (`trust_comparison`)

**Parameters from trust candidate:**

- `asset_value`, `expected_growth_rate`, `grat_term_years`, `grat_annuity_rate`, `crat_term_years`, `crat_payout_rate`

**Tax parameters:** `estate_tax_rate` (0.4), `charitable_deduction_rate` (0.35) from `/api/policies/tax`

**GRAT formulas:**

```
projected_remainder_to_heirs = asset_value × (1 + expected_growth_rate)^grat_term_years - asset_value × grat_annuity_rate × grat_term_years
estimated_estate_tax_reduction = projected_remainder_to_heirs × estate_tax_rate
mortality_inclusion_risk = "TERM_SURVIVAL_REQUIRED"
term_years = grat_term_years
```

**CRAT formulas:**

```
projected_charitable_remainder = asset_value × (1 + expected_growth_rate)^crat_term_years - asset_value × crat_payout_rate × crat_term_years
estimated_income_tax_deduction = projected_charitable_remainder × charitable_deduction_rate
family_transfer_fit = "LOW" (CRATs go to charity)
term_years = crat_term_years
```

**Estate context:**

- `taxable_estate` = estate_value - estate_tax_exemption (from `/api/policies/tax`)
- `estate_tax_exposure` = taxable_estate × estate_tax_rate
- `liquid_assets_available` = liquid_assets
- `liquidity_gap_before_planning` = max(0, estate_tax_exposure - liquid_assets)

**Recommendation rules:**

- `preferred_strategy`: `GRAT` if family_transfer_priority is "high" and philanthropic_intent is "low" or "moderate"; `CRAT` if philanthropic_intent is "high"
- `rationale_code`: `CHILDREN_TRANSFER_PRIORITY` for GRAT preference; `PHILANTHROPIC_PRIORITY` for CRAT
- `alternate_role`: `SECONDARY_CHARITABLE_TOOL` when GRAT preferred; `SECONDARY_FAMILY_TRANSFER_TOOL` when CRAT preferred

### 4d. Estate liquidity action plan (`estate_liquidity_action_plan`)

This is a compound analysis combining ILIT and trust comparison with an action set.

Compute the ILIT section using 4b formulas and the trust_transfer section using 4c formulas.

**Estate context:**

- `taxable_estate` = estate_value - estate_tax_exemption
- `estate_tax_exposure` = taxable_estate × 0.4
- `liquidity_gap_before_planning` = max(0, estate_tax_exposure - liquid_assets)

**Action set:** Choose from these alphabetically-sorted actions based on the gap analysis:

- `ATTORNEY_DRAFT_REVIEW` — always include
- `CRAT_FOR_CHARITABLE_REMAINDER` — include when philanthropic_intent is "high"
- `GRAT_FOR_APPRECIATING_SHARES` — include when family_transfer_priority is "high" and trust candidate has positive GRAT remainder
- `ILIT_CRUMMEY_NOTICE_CYCLE` — include when ILIT premium gap is 0
- `LIFETIME_EXEMPTION_ALLOCATION` — include when liquidity gap > 0

**Recommendation rules:**

- `primary_action`: `COMBINE_ILIT_AND_GRAT` when both ILIT and GRAT are feasible; `CRAT_WITH_LIQUIDITY_REVIEW` when philanthropic intent dominates; `ILIT_WITH_EXEMPTION_REVIEW` when ILIT is feasible but GRAT is not
- `sequencing`: `ILIT_FIRST_THEN_GRAT` when both are needed and no lookback issue; `TRUST_DECISION_FIRST` when trust dominates; `ILIT_FIRST_THEN_ATTORNEY_REVIEW` when lookback exists
- `risk_flag`: `LOW_IF_FORMALITIES_MET` when no concerns; `EXCLUSION_SHORTFALL` when premium > exclusion capacity; `THREE_YEAR_LOOKBACK` when existing policy transfer; `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` when both

## Step 5 — Produce the JSON output

Follow the exact answer template shape for the analysis type. Templates are provided in [templates/](templates/). The template dictates every required key, enum value, and data type.

Rules:
- All dollar amounts are JSON numbers rounded to cents (two decimal places)
- All years are JSON integers
- All dates are ISO 8601 YYYY-MM-DD strings
- All enums use EXACTLY the values from each template's `fields` specification
- `task_id` is the stable task identifier from the prompt
- Output only the JSON object; no prose outside it

See [calc.py](calc.py) for the deterministic implementation of all formulas.
