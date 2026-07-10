# Private Wealth Advisory — Task-Group Structured Output Skill

## Overview

This skill covers generating structured JSON planning outputs for private wealth advisory engagements: Roth conversion RMD analysis, ILIT Crummey funding, GRAT vs. CRAT trust comparisons, and estate liquidity action plans. The advisory API hosts client records, account exports, life-insurance records, trust candidates, tax policy constants, and RMD factors. Records may conflict across source systems — source resolution is always required.

## Environment

The remote advisory API base URL is provided by the harness. Read `environment_access.md` for the active base URL. The API is reachable over HTTP via `curl` or equivalent local command-line HTTP clients. Do **not** start a local environment or use localhost/127.0.0.1 unless the environment file itself explicitly points there.

## Workflow (SOP)

### Step 1 — Read the task inputs

Always read these files in order:

1. **`input/prompt.txt`** — extracts: client ID, engagement name, analysis type, horizon year (if any).
2. **`input/payloads/request_memo.md`** — extracts: client ID, engagement description, planning horizon year, any special instructions.
3. **`input/payloads/answer_template.json`** — extracts: required top-level keys, field definitions, enum constraints, and ordering rules.

### Step 2 — Query the advisory API

Construct an API call using the base URL from `environment_access.md`. The advisory environment provides computed planning data keyed by client ID and engagement type. Query the relevant endpoint(s) for the client to retrieve:

- Client profile and demographic data
- Account balances and holdings (Traditional IRA, Roth IRA, taxable accounts)
- Life insurance policy records
- Trust candidates (GRAT, CRAT parameters)
- Tax policy constants and RMD factor tables
- Source metadata (which system each record came from)

**Key API usage habits:**

- Pass the `client_id` and `analysis_type` (or engagement parameters) as query parameters or in the request body as the API expects.
- The API returns structured JSON with source annotations — each data field may have a `source` or `origin` key indicating whether it came from `SIGNED_PROFILE`, `ATTORNEY_MEMO`, `CUSTODIAN_EXPORT`, `CRM_NOTE`, or `STALE_MARKETING_INTAKE`.
- Some fields may have multiple conflicting values from different sources; the API returns all of them and the task is to select the controlling value by source priority.

### Step 3 — Resolve source conflicts

When the same field appears in multiple source records with different values, resolve by this **strict priority order** (highest to lowest):

| Priority | Source | Use for |
|----------|--------|---------|
| 1 (highest) | `SIGNED_PROFILE` | Client demographics, goals, beneficiaries, policy elections, stated preferences |
| 2 | `ATTORNEY_MEMO` | Legal documents, asset characterizations, trust parameters, estate planning instruments |
| 3 | `CUSTODIAN_EXPORT` | Account balances, holdings, transaction history, IRA values — this is the **gold source for financial account data** |
| 4 | `CRM_NOTE` | Advisor notes; use only when no higher-tier source exists |
| 5 (lowest) | `STALE_MARKETING_INTAKE` | Legacy marketing-system imports; use only when nothing else exists |

**Default resolution rules observed across all training examples:**

- **`controlling_profile_source`** → `SIGNED_PROFILE` (always preferred for client identity/preferences)
- **`controlling_account_source`** → `CUSTODIAN_EXPORT` (always preferred for financial account values)
- **`controlling_goal_source`** → `SIGNED_PROFILE` (always preferred for stated planning goals)
- **`controlling_policy_source`** → `SIGNED_PROFILE` (for insurance policy elections)
- **`controlling_beneficiary_source`** → `SIGNED_PROFILE` (for beneficiary designations)
- **`controlling_asset_source`** → `ATTORNEY_MEMO` (for legal characterization of assets)

### Step 4 — Fill the answer template

Construct a JSON object with every key listed in the template's `required_top_level_keys`. Populate fields according to the template's field definitions and enum constraints. Adhere to these formatting rules:

- **Numbers**: JSON numbers (not strings), rounded to two decimal places (cents).
- **Dates**: ISO 8601 `YYYY-MM-DD` strings.
- **Enums**: exact-case string from the template's `enum:` list — no abbreviations or variants.
- **Booleans**: JSON `true`/`false`.
- **Lists**: JSON arrays; when the template says "sorted alphabetically", sort the array elements alphabetically.
- **Extra context fields**: The API may return additional numeric fields (e.g., `planning_year`, `exemption_used`, `liquid_assets_available`) that are not in the template's required-top-level-keys list but provide useful context inside nested objects. Include them in the relevant section when the API provides them.

### Step 5 — Apply calculation conventions

#### Tax Rate Constants

| Constant | Rate | Applied To |
|----------|------|-----------|
| Income tax rate | 32% (0.32) | Roth conversion amounts, conversion tax |
| Estate tax rate | 40% (0.40) | Taxable estate, estate tax exposure, death benefit liquidity, estate tax reduction from trust remainder |
| Annual gift-tax exclusion (per beneficiary) | $20,000 (2026) | ILIT Crummey gift planning |

#### Conversion Plan (`roth_conversion_rmd`)

```
total_converted = annual_conversion_amount × conversion_years
total_conversion_tax = total_converted × 0.32
conversion_years_positive = conversion_years   (always equal)
first_conversion_year = planning_year           (typically 2026)
```

#### RMD Projection (`roth_conversion_rmd`)

```
rmd_tax_savings_through_horizon = baseline_rmd_tax_through_horizon - conversion_rmd_tax_through_horizon
```

The `horizon_year` comes from the request memo. The `first_rmd_year` depends on the client's age (age 73 triggers RMDs under current rules — the API provides this).

#### Gift Plan (`ilit_crummey_implementation`)

```
annual_exclusion_capacity = annual_exclusion_per_beneficiary × beneficiary_count
premium_gap = max(0, annual_premium - annual_exclusion_capacity)
notices_required = beneficiary_count
tax_liquidity_support = death_benefit × 0.40
```

When `estate_inclusion_risk` is `LOW_IF_FORMALITIES_MET`:
```
projected_outside_estate_if_implemented = death_benefit
```

#### ILIT Administration Timeline

Starting from the `contribution_date`:
- `notice_due_date` = contribution_date + 7 days
- `withdrawal_window_end` = contribution_date + 37 days (30 days after notice due)
- `earliest_premium_payment_date` = withdrawal_window_end + 1 day
- `dedicated_bank_account_required` = `true` (standard for proper Crummey administration)

#### Estate Context (`trust_comparison`, `estate_liquidity_action_plan`)

```
estate_tax_exposure = taxable_estate × 0.40
liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets_available)
```

#### Trust Projections (`trust_comparison`, `estate_liquidity_action_plan`)

```
estimated_estate_tax_reduction = projected_remainder_to_heirs × 0.40
```

GRAT term: typically 5 years. CRAT term: typically 20 years (or life of grantor). The `estimated_income_tax_deduction` for a CRAT is a present-value calculation the API provides.

#### Legacy Projection (`roth_conversion_rmd`)

The `projected_roth_balance_horizon` and `projected_traditional_balance_horizon` are API-computed future values at the horizon year. The `heir_tax_profile` is determined by the ratio of Roth to traditional assets:
- Roth significantly larger than traditional → `MOSTLY_TAX_FREE`
- Roughly balanced → `MIXED_TAXABLE_AND_TAX_FREE`
- Traditional significantly larger → `MOSTLY_TAXABLE`

### Step 6 — Validate and output

Before writing the final answer:

1. **Check every required top-level key** is present.
2. **Verify all enums** match the template's allowed values exactly (case-sensitive).
3. **Verify all derived calculations**: `rmd_tax_savings_through_horizon = baseline - conversion`, `total_converted = annual × years`, `total_conversion_tax = total_converted × 0.32`, etc.
4. **Verify source_resolution** keys match the template's controlling source fields.
5. **Check numbers are JSON numbers**, not strings. Use two decimal places for cents.
6. **Check `task_id`** matches the actual task directory name (e.g., from `prompt.txt` or the directory stem).
7. **Check `action_set`** arrays (if present) are sorted alphabetically.
8. Output **only** the JSON object — no prose before or after.

## Analysis-Type Quick Reference

### `roth_conversion_rmd`
- Used for: Roth conversion and RMD tax comparison
- Required sections: `recommendation`, `conversion_plan`, `rmd_projection`, `legacy_projection`, `source_resolution`
- Source fields: `controlling_profile_source`, `controlling_account_source`
- Recommendation enums: `primary_action` ∈ {STAGED_ROTH_CONVERSION, DEFER, NO_CONVERSION}, `suitability` ∈ {SUITABLE, BORDERLINE, DEFER}, `risk_flag` ∈ {TAX_BRACKET_MANAGEMENT, LIQUIDITY_CONSTRAINT, RMD_NEAR_TERM}

### `ilit_crummey_implementation`
- Used for: ILIT setup and first premium cycle
- Required sections: `recommendation`, `gift_plan`, `administration`, `estate_result`, `source_resolution`
- Source fields: `controlling_beneficiary_source`, `controlling_policy_source`
- Recommendation enums: `primary_action` ∈ {FUND_WITH_CRUMMEY_NOTICES, USE_LIFETIME_EXEMPTION_FOR_SHORTFALL, USE_NEW_POLICY_OR_ACCEPT_LOOKBACK, DISCLOSE_LOOKBACK_AND_USE_EXEMPTION}, `suitability` ∈ {SUITABLE_WITH_ADMINISTRATION, BORDERLINE, NOT_SUITABLE}, `risk_flag` ∈ {LOW_IF_FORMALITIES_MET, EXCLUSION_SHORTFALL, THREE_YEAR_LOOKBACK, THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL}
- `estate_result.estate_inclusion_risk` uses the same enum as `recommendation.risk_flag`

### `trust_comparison`
- Used for: GRAT vs CRAT numerical comparison and recommendation
- Required sections: `recommendation`, `estate_context`, `grat`, `crat`, `source_resolution`
- Source fields: `controlling_goal_source`, `controlling_asset_source`
- Recommendation enums: `preferred_strategy` ∈ {GRAT, CRAT}, `rationale_code` ∈ {CHILDREN_TRANSFER_PRIORITY, PHILANTHROPIC_PRIORITY}, `alternate_role` ∈ {SECONDARY_CHARITABLE_TOOL, SECONDARY_FAMILY_TRANSFER_TOOL}
- GRAT fields: `term_years` (int), `projected_remainder_to_heirs`, `estimated_estate_tax_reduction`, `mortality_inclusion_risk` ∈ {TERM_SURVIVAL_REQUIRED}
- CRAT fields: `term_years` (int), `projected_charitable_remainder`, `estimated_income_tax_deduction`, `family_transfer_fit` ∈ {LOW, MODERATE, HIGH}

### `estate_liquidity_action_plan`
- Used for: Combined ILIT + trust transfer + liquidity analysis
- Required sections: `recommendation`, `estate_context`, `ilit`, `trust_transfer`, `action_set`, `source_resolution`
- Source fields: `controlling_goal_source`, `controlling_policy_source`
- Recommendation enums: `primary_action` ∈ {COMBINE_ILIT_AND_GRAT, CRAT_WITH_LIQUIDITY_REVIEW, ILIT_WITH_EXEMPTION_REVIEW}, `sequencing` ∈ {ILIT_FIRST_THEN_GRAT, TRUST_DECISION_FIRST, ILIT_FIRST_THEN_ATTORNEY_REVIEW}, `risk_flag` ∈ {LOW_IF_FORMALITIES_MET, EXCLUSION_SHORTFALL, THREE_YEAR_LOOKBACK, THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL}
- `action_set`: array of enums ∈ {ATTORNEY_DRAFT_REVIEW, CRAT_FOR_CHARITABLE_REMAINDER, GRAT_FOR_APPRECIATING_SHARES, ILIT_CRUMMEY_NOTICE_CYCLE, LIFETIME_EXEMPTION_ALLOCATION}, **sorted alphabetically**
- `ilit.estate_inclusion_risk` uses the same risk_flag enums

## Common Pitfalls

1. **Not resolving conflicting sources.** Multiple source systems may return different values for the same field. Always pick the highest-priority source using the table above. Never average or merge conflicting numeric values.
2. **Wrong tax rate.** Use 32% for income tax (conversions), 40% for estate tax. Do not apply estate tax to Roth conversions or income tax to estate calculations.
3. **Forgetting `premium_gap` floor.** `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`. Never let it go negative.
4. **Forgetting `liquidity_gap_before_planning` floor.** `max(0, estate_tax_exposure - liquid_assets_available)`. Never negative.
5. **Using strings for numbers.** All dollar amounts must be JSON numbers, not strings. Round to two decimal places.
6. **Wrong `task_id`.** The `task_id` is the task directory name (e.g., `train_001`), not the client ID or a hardcoded string.
7. **Unsorted `action_set`.** When the template specifies alphabetical sorting, sort the array. The template for `estate_liquidity_action_plan` explicitly requires this.
8. **Missing extra context fields.** The API returns fields like `planning_year`, `exemption_used`, `liquid_assets_available` that are not in the template's required-top-level-keys but should be included in the relevant nested object when available.
9. **Including prose outside JSON.** The output must be the raw JSON object only — no markdown fences, no explanatory text.
10. **Case sensitivity on enums.** All enum values are UPPER_SNAKE_CASE and must match exactly. `LOW_IF_FORMALITIES_MET` is not `low_if_formalities_met`.
11. **`conversion_years_positive` ≠ `conversion_years`.** In all solved examples these are equal, but the field exists separately — verify from API output.
12. **Administration date arithmetic.** The ILIT timeline follows a fixed cadence from the contribution date: +7d notice due, +37d withdrawal window end, +38d earliest premium payment. Count days inclusively from contribution date.
