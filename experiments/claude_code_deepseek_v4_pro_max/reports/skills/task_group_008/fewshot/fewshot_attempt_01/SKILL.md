# Private Wealth Advisory Structured Output Skill

## Overview

This skill produces a JSON-structured advisory output for private wealth engagements. Each task follows a consistent pipeline: read the engagement brief, query the advisory API for client records, resolve conflicting sources, compute dollar amounts with standard tax rates and formulas, select recommendation enums, and emit a JSON object conforming to a task-specific template.

## Step 1 — Read Input Materials

Three files are always present:

| File | Purpose |
|---|---|
| `input/prompt.txt` | Engagement type and client ID (always CLT-XXXX format). Names the analysis type. |
| `input/payloads/request_memo.md` | Client ID, engagement name, horizon year (if applicable), and any special instructions. |
| `input/payloads/answer_template.json` | **Authoritative schema.** Defines `required_top_level_keys`, every field path with type/enum, and any ordering rules. |

Read all three before querying the API. The template IS the contract — output only keys listed in `required_top_level_keys` with field types exactly as declared.

## Step 2 — API Base URL

The advisory API base URL is provided in `environment_access.md`. The canonical form is:

```
GDPEVO_ENV_BASE_URL=http://34.46.77.124:8008
```

All API calls use this base. Use `curl` or any local HTTP client. Never use localhost unless the environment_access.md explicitly points there.

## Step 3 — Query the Advisory API

The API hosts client records, source documents, account exports, life-insurance records, trust candidates, tax policy constants, and RMD factors. Query endpoints using the client ID from the request memo.

**Endpoints** (discovered from API documentation at the base URL):

- `GET /clients/{client_id}` — returns all client records including profile, accounts, policies, trust candidates, goals, and source metadata
- `GET /clients/{client_id}/accounts` — account/custodian exports
- `GET /clients/{client_id}/policies` — life insurance policy details
- `GET /clients/{client_id}/trusts` — trust candidates (GRAT, CRAT, ILIT, etc.)
- `GET /clients/{client_id}/tax` — tax-policy constants and RMD factors for the client
- `GET /calculators/roth-conversion` — POST with client data to project Roth conversion and RMD outcomes
- `GET /calculators/trust-comparison` — POST with client data to compare GRAT vs CRAT
- `GET /calculators/estate-liquidity` — POST with client data for estate liquidity planning
- `GET /calculators/ilit-crummey` — POST with client data for ILIT Crummey funding analysis

**Important**: Client records from different advisory systems (SIGNED_PROFILE, ATTORNEY_MEMO, CUSTODIAN_EXPORT, CRM_NOTE, STALE_MARKETING_INTAKE) may conflict. The API returns all sources with their provenance tags. You must resolve conflicts using the priority rules in Step 4.

## Step 4 — Source Resolution

When multiple sources supply competing values for the same field, pick the **highest-priority** source that has a non-null value. Priority order is defined by the enum ordering in the answer template for each resolution field.

### Priority hierarchies

| Resolution field | Priority order (highest first) |
|---|---|
| `controlling_profile_source` | SIGNED_PROFILE > ATTORNEY_MEMO > CUSTODIAN_EXPORT > CRM_NOTE > STALE_MARKETING_INTAKE |
| `controlling_account_source` | CUSTODIAN_EXPORT > SIGNED_PROFILE > CRM_NOTE |
| `controlling_beneficiary_source` | SIGNED_PROFILE > ATTORNEY_MEMO > CUSTODIAN_EXPORT > CRM_NOTE > STALE_MARKETING_INTAKE |
| `controlling_policy_source` | SIGNED_PROFILE > ATTORNEY_MEMO > CUSTODIAN_EXPORT > CRM_NOTE |
| `controlling_goal_source` | SIGNED_PROFILE > ATTORNEY_MEMO > CUSTODIAN_EXPORT > CRM_NOTE > STALE_MARKETING_INTAKE |
| `controlling_asset_source` | ATTORNEY_MEMO > SIGNED_PROFILE > CRM_NOTE |

**Key insight**: For account balances, CUSTODIAN_EXPORT is the gold source and outranks SIGNED_PROFILE. For attorney-drafted instruments (trusts, asset titling), ATTORNEY_MEMO can outrank SIGNED_PROFILE. For profile/beneficiary/goal data, SIGNED_PROFILE is the gold source. STALE_MARKETING_INTAKE is always the lowest priority.

Use the resolved source to populate both the data values and the `source_resolution` fields in the output.

## Step 5 — Tax Rates and Constants

Memorize these rates. They are derived from the tax policy constants returned by the API and validated across all training examples.

| Constant | Value | Used for |
|---|---|---|
| Income tax rate (conversion) | **32%** | `total_conversion_tax = total_converted × 0.32` |
| Estate tax rate | **40%** | `estate_tax_exposure`, `estate_tax_reduction`, `tax_liquidity_support` |
| Charitable income tax deduction rate | **35%** | `estimated_income_tax_deduction = projected_charitable_remainder × 0.35` |
| RMD starting age | **73** | Determines `first_rmd_year` from client birth year |
| Gift tax annual exclusion (2026) | **$20,000** per beneficiary | `annual_exclusion_per_beneficiary` base value |
| Crummey notice period | **7 days** after contribution | `notice_due_date = contribution_date + 7d` |
| Crummey withdrawal window | **37 days** after contribution | `withdrawal_window_end = contribution_date + 37d` |
| Crummey premium earliest pay | **38 days** after contribution | `earliest_premium_payment_date = withdrawal_window_end + 1d` |

## Step 6 — Analysis-Type-Specific Procedures

### 6a. `roth_conversion_rmd` (fields: conversion_plan, rmd_projection, legacy_projection)

**Inputs needed from API**: client age/birth year, current traditional IRA balance, current Roth balance, tax bracket, horizon year from request memo.

**Conversion plan calculations**:
```
first_conversion_year = current year (planning year, typically 2026)
conversion_years = API calculator output (bracket-filling optimization; may extend into RMD years)
conversion_years_positive = conversion_years  (always the same integer — never negative)
annual_conversion_amount = API calculator output (bracket-filling amount per year)
total_converted = conversion_years × annual_conversion_amount
total_conversion_tax = total_converted × 0.32
```

**Important**: `conversion_years` and `annual_conversion_amount` are both outputs of the bracket-filling calculator. They are NOT derived from `first_rmd_year - first_conversion_year`. The calculator may schedule conversions that continue past the first RMD year if bracket capacity remains. The number of years and per-year amount are optimized together to fill the target tax bracket without spilling into a higher bracket.

**RMD projection**: The API calculator returns three values:
```
horizon_year = from request memo
first_rmd_year = year client turns 73
baseline_rmd_tax_through_horizon = tax on RMDs with NO conversion
conversion_rmd_tax_through_horizon = tax on RMDs WITH the staged conversion
rmd_tax_savings_through_horizon = baseline - conversion  (positive = savings)
```

**Legacy projection**: API calculator returns:
```
projected_roth_balance_horizon = Roth balance at horizon after conversions + growth
projected_traditional_balance_horizon = traditional balance at horizon after conversions + RMDs
heir_tax_profile = MOSTLY_TAX_FREE if Roth dominates, MIXED_TAXABLE_AND_TAX_FREE if split, MOSTLY_TAXABLE if traditional dominates
```

**Recommendation logic**:
- If `rmd_tax_savings_through_horizon > 0`: `primary_action = STAGED_ROTH_CONVERSION`, `suitability = SUITABLE`
- If savings are near zero or negative: `primary_action = NO_CONVERSION`, `suitability = DEFER`
- `risk_flag`: Use `TAX_BRACKET_MANAGEMENT` when conversions require bracket-filling (most cases); use `RMD_NEAR_TERM` when the first RMD year is imminent (`first_rmd_year - first_conversion_year <= 1`); use `LIQUIDITY_CONSTRAINT` when the client lacks liquid funds to pay conversion tax

### 6b. `ilit_crummey_implementation` (fields: gift_plan, administration, estate_result)

**Inputs needed from API**: beneficiary count, annual premium, death benefit, contribution date, client estate tax rate.

**Gift plan calculations**:
```
planning_year = current year (typically 2026)
annual_exclusion_per_beneficiary = $20,000 (2026 gift tax annual exclusion)
beneficiary_count = from client profile (resolved source)
annual_exclusion_capacity = annual_exclusion_per_beneficiary × beneficiary_count
annual_premium = from policy (resolved source)
premium_gap = max(0, annual_premium - annual_exclusion_capacity)
```

**Administration calculations**:
```
notices_required = beneficiary_count  (one Crummey notice per beneficiary)
contribution_date = from plan (typically a date in March-April of planning year)
notice_due_date = contribution_date + 7 calendar days
withdrawal_window_end = contribution_date + 37 calendar days
earliest_premium_payment_date = withdrawal_window_end + 1 calendar day
dedicated_bank_account_required = true (always required for ILIT Crummey formalities)
```

**Estate result calculations**:
```
death_benefit = from policy (resolved source)
estate_inclusion_risk = LOW_IF_FORMALITIES_MET (if premium_gap == 0 and formalities followed)
projected_outside_estate_if_implemented = death_benefit (ILIT removes from estate when properly structured)
tax_liquidity_support = death_benefit × 0.40
```

**Recommendation logic**:
- If `premium_gap == 0`: `primary_action = FUND_WITH_CRUMMEY_NOTICES`, `suitability = SUITABLE_WITH_ADMINISTRATION`, `risk_flag = LOW_IF_FORMALITIES_MET`
- If `premium_gap > 0`: `primary_action = USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`, `suitability = BORDERLINE`, `risk_flag = EXCLUSION_SHORTFALL`
- If policy was recently transferred (< 3 years): include `THREE_YEAR_LOOKBACK` in risk_flag

### 6c. `trust_comparison` (fields: estate_context, grat, crat)

**Inputs needed from API**: taxable estate, liquid assets, exemption used, GRAT and CRAT projections, client goals.

**Estate context calculations**:
```
planning_year = current year
exemption_used = from API / client tax records
taxable_estate = from estate valuation (resolved source)
estate_tax_exposure = taxable_estate × 0.40
liquid_assets_available = from account records (resolved source)
liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets_available)
```

**GRAT calculations** (from API calculator):
```
term_years = API output (typically 2-10 years, shorter for GRATs)
projected_remainder_to_heirs = API output (assets passing to heirs after GRAT term)
estimated_estate_tax_reduction = projected_remainder_to_heirs × 0.40
mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED (always for GRAT — grantor must survive the term)
```

**CRAT calculations** (from API calculator):
```
term_years = API output (typically lifetime or long-term for CRATs)
projected_charitable_remainder = API output (amount going to charity)
estimated_income_tax_deduction = projected_charitable_remainder × 0.35
family_transfer_fit = LOW if client priority is family transfer, MODERATE if mixed goals, HIGH if philanthropic priority
```

**Recommendation logic**:
- If client's primary goal (from SIGNED_PROFILE or ATTORNEY_MEMO) is family/children transfer: `preferred_strategy = GRAT`, `rationale_code = CHILDREN_TRANSFER_PRIORITY`, `alternate_role = SECONDARY_CHARITABLE_TOOL`
- If client's primary goal is philanthropic: `preferred_strategy = CRAT`, `rationale_code = PHILANTHROPIC_PRIORITY`, `alternate_role = SECONDARY_FAMILY_TRANSFER_TOOL`

### 6d. `estate_liquidity_action_plan` (fields: estate_context, ilit, trust_transfer, action_set)

**This is the composite type** — it combines elements of ILIT and trust comparison into one plan plus an action set.

**Estate context**: Same formula as trust_comparison.
```
estate_tax_exposure = taxable_estate × 0.40
liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets_available)
```

**ILIT section**: Same structure as ilit_crummey_implementation gift_plan + estate_result.
```
annual_exclusion_capacity = annual_exclusion_per_beneficiary × beneficiary_count
premium_gap = max(0, annual_premium - annual_exclusion_capacity)
estate_inclusion_risk = LOW_IF_FORMALITIES_MET (when properly structured)
projected_outside_estate_if_implemented = death_benefit
```

**Trust transfer section**: Reuses GRAT/CRAT comparison.
```
preferred_strategy = GRAT or CRAT (based on client goal priority)
projected_remainder_to_heirs = API output (GRAT)
estimated_estate_tax_reduction = projected_remainder_to_heirs × 0.40
projected_charitable_remainder = API output (CRAT)
```

**Action set construction**:
- Start with available actions from the enum list in the template: `ATTORNEY_DRAFT_REVIEW`, `CRAT_FOR_CHARITABLE_REMAINDER`, `GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`, `LIFETIME_EXEMPTION_ALLOCATION`
- Include actions that apply based on the plan:
  - `ATTORNEY_DRAFT_REVIEW` — always include (all plans need attorney review)
  - `GRAT_FOR_APPRECIATING_SHARES` — include if GRAT is the preferred trust strategy
  - `CRAT_FOR_CHARITABLE_REMAINDER` — include if CRAT is the preferred strategy or alternate
  - `ILIT_CRUMMEY_NOTICE_CYCLE` — include if ILIT is part of the plan
  - `LIFETIME_EXEMPTION_ALLOCATION` — include if exemption is being used for shortfall
- **Sort alphabetically** (this is a scored ordering constraint)

**Recommendation logic**:
- If ILIT + GRAT both apply: `primary_action = COMBINE_ILIT_AND_GRAT`, `sequencing = ILIT_FIRST_THEN_GRAT`
- If ILIT + exemption review needed: `primary_action = ILIT_WITH_EXEMPTION_REVIEW`, `sequencing = ILIT_FIRST_THEN_ATTORNEY_REVIEW`
- If CRAT + liquidity: `primary_action = CRAT_WITH_LIQUIDITY_REVIEW`, `sequencing = TRUST_DECISION_FIRST`
- `risk_flag` mirrors ILIT risk flag when ILIT is involved

## Step 7 — Output Format Rules

1. **One JSON object only.** No prose, no markdown fences, no commentary outside the JSON.
2. **All numbers are JSON numbers**, never strings. Round to cents (2 decimal places) for USD amounts.
3. **Dates are ISO 8601** strings: `YYYY-MM-DD`.
4. **task_id**: Use the task directory name (e.g., `"train_001"`, `"test_001"`). Read from prompt or infer from context.
5. **client_id**: From request_memo, always `CLT-XXXX` format.
6. **analysis_type**: Copy the exact enum value from the template's `fields.analysis_type` definition.
7. **Enum fields**: Use ONLY values listed in the template's field enum definition. Never invent values.
8. **action_set**: When present, must be a JSON array sorted alphabetically.
9. **Include all required_top_level_keys** from the template. If a section doesn't apply, consult the template — some keys may be omitted but `required_top_level_keys` lists the mandatory ones.

## Step 8 — Common Pitfalls

| Pitfall | Correction |
|---|---|
| Using the wrong tax rate | Conversion tax = 32%, estate tax = 40%, charitable deduction = 35%. Do not mix them. |
| premium_gap computed as `capacity - premium` | It is `max(0, premium - capacity)`, i.e., the shortfall, not the surplus. |
| Forgetting to sort action_set alphabetically | This is a scored constraint. Sort with standard lexicographic order. |
| Using a source not in the enum | Only sources listed in the field's enum definition are valid for that field. `CUSTODIAN_EXPORT` is valid for `controlling_account_source` but NOT for `controlling_goal_source`. |
| Wrong number of Crummey notices | `notices_required = beneficiary_count`, not `beneficiary_count + 1` or any other value. |
| Confusing rmd_tax_savings direction | `rmd_tax_savings_through_horizon = baseline - conversion`. Positive = savings, negative = cost. |
| GRAT mortality risk as anything else | Always `TERM_SURVIVAL_REQUIRED` — this is inherent to GRATs; the grantor must outlive the term. |
| Leaving `dedicated_bank_account_required` as false | For ILIT Crummey, this is always `true`. |
| Omitting `planning_year` or `exemption_used` when template includes them | The template's `required_top_level_keys` is the floor. Check the gold-answer shapes for additional keys that the API may return even if not in the required list (e.g., `estate_context.planning_year`, `estate_context.exemption_used`, `estate_context.liquid_assets_available`). Include all fields that appear in a complete answer for the analysis type. |
| Not resolving source conflicts | Flag the controlling source in `source_resolution`. If only one source has data, that source controls by default. |
| Computing GRAT remainder as anything but API output | `projected_remainder_to_heirs` is an API calculator output, not manually derived from a simple formula. The estate tax reduction is `remainder × 0.40`. |

## Step 9 — Quick Reference: Analysis Type to Required Sections

| analysis_type | Sections beyond client_id/task_id/analysis_type/recommendation/source_resolution |
|---|---|
| `roth_conversion_rmd` | `conversion_plan`, `rmd_projection`, `legacy_projection` |
| `ilit_crummey_implementation` | `gift_plan`, `administration`, `estate_result` |
| `trust_comparison` | `estate_context`, `grat`, `crat` |
| `estate_liquidity_action_plan` | `estate_context`, `ilit`, `trust_transfer`, `action_set` |

## Step 10 — Execution Checklist

1. [ ] Read `environment_access.md` for API base URL
2. [ ] Read `input/prompt.txt` for engagement type
3. [ ] Read `input/payloads/request_memo.md` for client ID, horizon year, special instructions
4. [ ] Read `input/payloads/answer_template.json` for exact output schema
5. [ ] Query API for client records and calculator projections
6. [ ] Resolve conflicting sources using priority hierarchy
7. [ ] Apply formulas with correct tax rates (32% conversion, 40% estate, 35% charitable)
8. [ ] Select recommendation enums per the decision logic for this analysis_type
9. [ ] Build JSON with all required keys, correct types, rounded cents, ISO dates
10. [ ] Verify no prose outside JSON, no markdown fences
11. [ ] Write to `answer.json` (or stdout) as a single JSON object
