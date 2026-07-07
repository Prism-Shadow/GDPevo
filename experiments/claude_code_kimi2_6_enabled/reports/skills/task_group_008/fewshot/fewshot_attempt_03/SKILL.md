# Private Wealth Advisory Structured Output Skill

## Task Overview
Generate a structured JSON planning output for a private wealth advisory client by querying an advisory API, resolving conflicting source records, performing tax-aware calculations, and returning results that exactly conform to an answer template.

## API Access

- Base URL is exposed as the `API_BASE` environment variable after the shared environment starts.
- Query the API for: client records, source documents, account exports, life-insurance records, trust candidates, tax-policy constants, and RMD factors.
- Typical endpoint families:
  - `/clients/{client_id}` — profile, goals, demographics
  - `/clients/{client_id}/accounts` — custodian account balances (traditional IRA, Roth IRA, etc.)
  - `/clients/{client_id}/policies` — life insurance policy details
  - `/clients/{client_id}/trusts` — trust candidates and terms
  - `/tax-policy/constants` — estate tax rate, income tax brackets, annual gift exclusion
  - `/tax-policy/rmd-factors` — IRS life expectancy tables
- Explore the OpenAPI/swagger docs or root endpoint if the exact paths are not obvious.

## Source Conflict Resolution

Records may conflict because they were imported from different advisory systems at different times. Resolve using this hierarchy (highest authority wins):

1. `SIGNED_PROFILE`
2. `ATTORNEY_MEMO`
3. `CUSTODIAN_EXPORT`
4. `CRM_NOTE`
5. `STALE_MARKETING_INTAKE`

Report the winning source in the `source_resolution` block. For example:
- **Roth conversion tasks**: `controlling_profile_source` and `controlling_account_source`
- **ILIT tasks**: `controlling_beneficiary_source` and `controlling_policy_source`
- **Trust comparison / estate liquidity**: `controlling_goal_source` and `controlling_asset_source` (or `controlling_policy_source` when insurance is involved)

## Analysis Types and Required Output Structures

The `analysis_type` field determines the required top-level keys. Four types have been observed:

| Analysis Type | Required Top-Level Keys |
|---------------|------------------------|
| `roth_conversion_rmd` | `task_id`, `client_id`, `analysis_type`, `recommendation`, `conversion_plan`, `rmd_projection`, `legacy_projection`, `source_resolution` |
| `ilit_crummey_implementation` | `task_id`, `client_id`, `analysis_type`, `recommendation`, `gift_plan`, `administration`, `estate_result`, `source_resolution` |
| `trust_comparison` | `task_id`, `client_id`, `analysis_type`, `recommendation`, `estate_context`, `grat`, `crat`, `source_resolution` |
| `estate_liquidity_action_plan` | `task_id`, `client_id`, `analysis_type`, `recommendation`, `estate_context`, `ilit`, `trust_transfer`, `action_set`, `source_resolution` |

Always use the exact `analysis_type` enum value from the answer template.

## Financial Calculation Patterns

Perform all intermediate calculations with full floating-point precision and round **only at final output** to 2 decimal places. Standard rates observed across tasks:

- **Roth conversion income tax**: `0.32` (32%).
  - `total_converted = annual_conversion_amount × conversion_years`
  - `total_conversion_tax = total_converted × 0.32`
  - `conversion_years_positive` equals `conversion_years` when all years have positive conversions.
- **Estate tax**: `0.40` (40%).
  - `estate_tax_exposure = taxable_estate × 0.40`
  - `estimated_estate_tax_reduction` (GRAT or trust transfer) = `projected_remainder_to_heirs × 0.40`
- **Liquidity gap**: `max(0, estate_tax_exposure − liquid_assets_available)`
- **ILIT premium gap**: `max(0, annual_premium − annual_exclusion_capacity)`
  - `annual_exclusion_capacity = annual_exclusion_per_beneficiary × beneficiary_count`
- **Death benefit tax liquidity support**: `death_benefit × 0.40`
- **CRAT income tax deduction**: `projected_charitable_remainder × 0.35`
- **RMD tax savings**: `baseline_rmd_tax_through_horizon − conversion_rmd_tax_through_horizon` (compute from unrounded intermediates to avoid 1-cent drift).

## Crummey Administration Timing (ILIT Tasks)

When the analysis involves ILIT funding with Crummey notices, calculate dates in this sequence:

1. `contribution_date` — the date the gift is contributed to the trust.
2. `notice_due_date` — typically `contribution_date + 7` days.
3. `withdrawal_window_end` — typically `notice_due_date + 30` days (a ~30-day withdrawal window).
4. `earliest_premium_payment_date` — day after `withdrawal_window_end`.

Format all dates as ISO `YYYY-MM-DD`.

## Recommendation Logic

Choose recommendation enums **exactly** as specified in the answer template. Observed mappings:

- **Roth conversion**: `primary_action: STAGED_ROTH_CONVERSION`, `suitability: SUITABLE`, `risk_flag: TAX_BRACKET_MANAGEMENT` (or `LIQUIDITY_CONSTRAINT` / `RMD_NEAR_TERM` as appropriate).
- **ILIT with full exclusion capacity**: `primary_action: FUND_WITH_CRUMMEY_NOTICES`, `suitability: SUITABLE_WITH_ADMINISTRATION`, `risk_flag: LOW_IF_FORMALITIES_MET`.
- **GRAT vs CRAT when children are the priority**: `preferred_strategy: GRAT`, `rationale_code: CHILDREN_TRANSFER_PRIORITY`, `alternate_role: SECONDARY_CHARITABLE_TOOL`.
- **Estate liquidity combining ILIT and GRAT**: `primary_action: COMBINE_ILIT_AND_GRAT`, `sequencing: ILIT_FIRST_THEN_GRAT`, `risk_flag: LOW_IF_FORMALITIES_MET`.

The `action_set` in `estate_liquidity_action_plan` must be **sorted alphabetically** and contain only valid enums from the template (e.g., `ATTORNEY_DRAFT_REVIEW`, `GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`, `CRAT_FOR_CHARITABLE_REMAINDER`, `LIFETIME_EXEMPTION_ALLOCATION`).

## Heir Tax Profile

For Roth-conversion tasks, set `heir_tax_profile` based on the projected Roth vs. traditional balance at the horizon:

- `MOSTLY_TAX_FREE` — Roth dominates.
- `MIXED_TAXABLE_AND_TAX_FREE` — neither dominates (most common when both balances are material).
- `MOSTLY_TAXABLE` — Traditional dominates.

## Output Formatting Rules

1. **Return only the JSON object** — no markdown fences, no prose.
2. **Numbers must be JSON numbers**, not strings (e.g., `1234.56`, not `"1234.56"`).
3. **Round all currency values to cents** (2 decimal places). Whole-dollar values may still show `.0`.
4. **Dates must be ISO `YYYY-MM-DD`**.
5. **`action_set` must be sorted alphabetically** when present.
6. **`task_id`** must match the task identifier (e.g., `train_001`, `test_001`).
7. **Object key order is not scored** except where explicitly noted.

## Common Pitfalls

- **Source conflicts**: Do not blindly use the first record returned. Check the `source` field on each record and apply the hierarchy.
- **Rounding drift**: Computing `rmd_tax_savings` as `round(baseline) − round(conversion)` can produce a 1-cent mismatch. Calculate savings from the unrounded intermediate values, then round the final result.
- **Missing fields**: The answer template lists required keys; omitting any causes validation failure.
- **Enum spelling**: Values like `SUITABLE_WITH_ADMINISTRATION` and `LOW_IF_FORMALITIES_MET` must match the template exactly, including underscores.
- **GRAT mortality risk**: Always include `mortality_inclusion_risk: TERM_SURVIVAL_REQUIRED` for GRAT analyses.
