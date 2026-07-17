# Private Wealth Advisory Structured Output Skill

## Overview

This skill covers generating structured JSON planning outputs for private wealth advisory engagements. Five analysis types are supported: Roth conversion/RMD projections, ILIT Crummey funding cycles, GRAT-vs-CRAT trust comparisons, estate liquidity action plans, and near-RMD conversion comparisons. The advisory environment provides client records via REST API; source records may conflict due to imports from different advisory systems.

## API Usage

### Client Data Endpoint
- `GET /api/clients` — list all clients
- `GET /api/clients/{client_id}` — single client record
- The client object contains: `client_id`, `household_name`, `age`, `marital_status`, `filing_status`, `planning_year`, `estate_value`, `liquid_assets`, `record_status`, `advisor_team`
- `filing_status` is either `MFJ` (married filing jointly) or `SINGLE`
- `planning_year` is the current advisory year

### Sub-resource Endpoints
- `GET /api/clients/{client_id}/accounts` — account exports
- `GET /api/clients/{client_id}/policies` — life-insurance records
- `GET /api/clients/{client_id}/trusts` — trust candidates
- `GET /api/clients/{client_id}/documents` — source documents
- `GET /api/clients/{client_id}/records` — consolidated client records
- `GET /api/clients/{client_id}/profile` — signed profile data
- `GET /api/clients/{client_id}/sources` — source metadata and resolution hints

These sub-endpoints return detailed records used to compute plan values. When they return `{"error": "client not found"}`, the data must be derived from the base client record and standard advisory constants.

## Output Conventions

### General JSON Rules
- All output must be a single JSON object conforming exactly to the provided `answer_template.json`
- Numbers are JSON numbers, never strings
- USD amounts are rounded to cents (two decimal places)
- Dates are ISO 8601 `YYYY-MM-DD` strings
- `task_id` must match the input task identifier (e.g. `train_001`)
- `client_id` is the stable client identifier from the request memo (e.g. `CLT-1001`)

### Top-Level Keys by Analysis Type

| analysis_type | Required Top-Level Keys |
|---|---|
| `roth_conversion_rmd` | task_id, client_id, analysis_type, recommendation, conversion_plan, rmd_projection, legacy_projection, source_resolution |
| `ilit_crummey_implementation` | task_id, client_id, analysis_type, recommendation, gift_plan, administration, estate_result, source_resolution |
| `trust_comparison` | task_id, client_id, analysis_type, recommendation, estate_context, grat, crat, source_resolution |
| `estate_liquidity_action_plan` | task_id, client_id, analysis_type, recommendation, estate_context, ilit, trust_transfer, action_set, source_resolution |

## Calculation Conventions

### RMD Age Determination
- For clients turning age 73+ in the planning year, RMDs have already begun or begin immediately
- The RMD starting age under SECURE 2.0 depends on birth year:
  - Born 1951–1959: age 73
  - Born 1960 or later: age 75
- `first_rmd_year` = birth_year + rmd_starting_age
- Birth year ≈ `planning_year - age` (check if birthday has passed in the planning year)

### Roth Conversion Planning
- `conversion_years_positive` counts only years where the annual amount exceeds zero
- `conversion_years` includes all planned conversion years (including any zero-amount placeholder years if applicable)
- `total_converted` = sum of all annual conversion amounts over the plan
- `total_conversion_tax` is computed at the client's marginal tax rate applied to converted amounts
- `first_conversion_year` should be >= `planning_year` (current year conversions are possible)
- The horizon year is provided in the request memo

### RMD Tax Projections
- `baseline_rmd_tax_through_horizon`: total RMD-related tax if no conversions are done
- `conversion_rmd_tax_through_horizon`: RMD tax after executing the conversion plan
- `rmd_tax_savings_through_horizon` = baseline − conversion (always positive when conversions reduce RMDs)
- RMD amounts are computed using IRS life expectancy tables applied to year-end traditional IRA balances
- Tax is the RMD amount × client's marginal income tax rate

### ILIT / Crummey Administration
- `annual_exclusion_per_beneficiary` is the gift tax annual exclusion amount for the planning year (indexed annually; $18,000 for 2024–2025, check planning year)
- `annual_exclusion_capacity` = `annual_exclusion_per_beneficiary × beneficiary_count`
- `premium_gap` = `annual_premium − annual_exclusion_capacity` (positive when exclusion capacity is insufficient)
- Crummey notice timeline (standard convention):
  - `contribution_date`: date contributions are made to the ILIT
  - `notice_due_date`: 30 days after contribution_date
  - `withdrawal_window_end`: 30 days after notice_due_date (60 days after contribution)
  - `earliest_premium_payment_date`: day after withdrawal_window_end
- `notices_required` = `beneficiary_count` (one Crummey notice per beneficiary)
- `dedicated_bank_account_required`: true when ILIT must maintain a separate account for Crummey contributions

### Estate Tax Calculations
- `estate_tax_exposure`: the federal estate tax liability on the taxable estate, accounting for the lifetime exemption
- `liquidity_gap_before_planning`: shortfall between liquid assets and estimated estate tax + settlement costs
- When `liquid_assets >= estate_tax_exposure`, liquidity_gap can be zero
- `tax_liquidity_support`: the death benefit portion that covers estate tax liquidity needs

### GRAT vs CRAT Comparison
- GRAT (Grantor Retained Annuity Trust):
  - Short term typically (2 years)
  - `projected_remainder_to_heirs`: assets passing to heirs after annuity term
  - `estimated_estate_tax_reduction`: value removed from taxable estate
  - `mortality_inclusion_risk`: always `TERM_SURVIVAL_REQUIRED` (grantor must survive the term)
- CRAT (Charitable Remainder Annuity Trust):
  - Longer term (life or term-of-years, often 20 years for planning)
  - `projected_charitable_remainder`: value going to charity at trust termination
  - `estimated_income_tax_deduction`: present value of charitable remainder interest
  - `family_transfer_fit`: LOW for pure philanthropic intent, MODERATE/HIGH when family benefits from annuity stream

### Legacy Projections
- `heir_tax_profile`:
  - `MOSTLY_TAX_FREE`: when Roth assets dominate the projected inheritance
  - `MIXED_TAXABLE_AND_TAX_FREE`: significant balances in both Roth and traditional
  - `MOSTLY_TAXABLE`: when traditional IRA/estate assets dominate

## Enum Reference

### recommendation.primary_action (roth_conversion_rmd)
- `STAGED_ROTH_CONVERSION`: multi-year gradual conversions
- `DEFER`: postpone conversion decision
- `NO_CONVERSION`: conversion is not advantageous

### recommendation.suitability (roth_conversion_rmd)
- `SUITABLE`: conversion plan is appropriate
- `BORDERLINE`: marginal benefit or near-term RMD start
- `DEFER`: insufficient data or near-term liquidity concerns

### recommendation.risk_flag (roth_conversion_rmd)
- `TAX_BRACKET_MANAGEMENT`: risk of pushing into higher bracket
- `LIQUIDITY_CONSTRAINT`: insufficient liquid assets to pay conversion tax
- `RMD_NEAR_TERM`: RMDs starting soon limits conversion window

### recommendation.primary_action (ilit_crummey_implementation)
- `FUND_WITH_CRUMMEY_NOTICES`: use annual exclusion gifts with Crummey notices
- `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`: cover premium gap with lifetime exemption
- `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`: new policy or accept 3-year lookback risk
- `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`: disclose lookback and use exemption for shortfall

### recommendation.suitability (ilit)
- `SUITABLE_WITH_ADMINISTRATION`: plan works if Crummey formalities are followed
- `BORDERLINE`: marginal benefit or administrative complexity
- `NOT_SUITABLE`: plan cannot be implemented as structured

### recommendation.risk_flag (ilit/estate)
- `LOW_IF_FORMALITIES_MET`: minimal risk if Crummey procedures are followed
- `EXCLUSION_SHORTFALL`: premium exceeds annual exclusion capacity
- `THREE_YEAR_LOOKBACK`: policy transferred within 3 years of death risk
- `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`: both risks present

### recommendation.preferred_strategy (trust_comparison)
- `GRAT`: Grantor Retained Annuity Trust preferred
- `CRAT`: Charitable Remainder Annuity Trust preferred

### recommendation.rationale_code (trust_comparison)
- `CHILDREN_TRANSFER_PRIORITY`: primary goal is wealth transfer to children
- `PHILANTHROPIC_PRIORITY`: primary goal is charitable giving

### recommendation.alternate_role (trust_comparison)
- `SECONDARY_CHARITABLE_TOOL`: when GRAT is primary, CRAT serves charitable goals
- `SECONDARY_FAMILY_TRANSFER_TOOL`: when CRAT is primary, GRAT serves family goals

### recommendation.primary_action (estate_liquidity)
- `COMBINE_ILIT_AND_GRAT`: pair life insurance trust with GRAT for appreciating assets
- `CRAT_WITH_LIQUIDITY_REVIEW`: use CRAT and review estate liquidity separately
- `ILIT_WITH_EXEMPTION_REVIEW`: focus on ILIT and review lifetime exemption usage

### recommendation.sequencing (estate_liquidity)
- `ILIT_FIRST_THEN_GRAT`: establish insurance coverage before trust transfer
- `TRUST_DECISION_FIRST`: decide GRAT/CRAT strategy before ILIT implementation
- `ILIT_FIRST_THEN_ATTORNEY_REVIEW`: fund ILIT then have attorney review trust strategy

### action_set (estate_liquidity)
Must be an alphabetically sorted list. Valid values:
- `ATTORNEY_DRAFT_REVIEW`
- `CRAT_FOR_CHARITABLE_REMAINDER`
- `GRAT_FOR_APPRECIATING_SHARES`
- `ILIT_CRUMMEY_NOTICE_CYCLE`
- `LIFETIME_EXEMPTION_ALLOCATION`

### source_resolution.* enums
- `SIGNED_PROFILE`: client-signed profile document
- `ATTORNEY_MEMO`: attorney-prepared memorandum
- `CUSTODIAN_EXPORT`: custodian account export data
- `CRM_NOTE`: advisor CRM notes
- `STALE_MARKETING_INTAKE`: outdated marketing intake form (least reliable)

## Source Resolution Rules

When client records conflict across sources:
1. `CUSTODIAN_EXPORT` is the most reliable source for account balances, positions, and transaction history
2. `SIGNED_PROFILE` carries more weight than `CRM_NOTE` for client-stated facts (beneficiaries, goals, family structure)
3. `ATTORNEY_MEMO` takes precedence for legal structures (trust terms, estate planning documents, policy ownership)
4. `STALE_MARKETING_INTAKE` is deprecated — override with any other source
5. For account-level data: prefer `CUSTODIAN_EXPORT` > `SIGNED_PROFILE` > `CRM_NOTE`
6. For profile/goal data: prefer `SIGNED_PROFILE` > `ATTORNEY_MEMO` > `CUSTODIAN_EXPORT` > `CRM_NOTE` > `STALE_MARKETING_INTAKE`
7. For policy/insurance data: prefer `ATTORNEY_MEMO` or `CUSTODIAN_EXPORT` depending on the record type

## Common Pitfalls

1. **Missing top-level keys**: Every template key must be present; structural completeness is required for a valid output
2. **Wrong analysis_type enum**: Must match the template exactly — no typos or aliases
3. **action_set ordering**: Must be sorted alphabetically for `estate_liquidity_action_plan`
4. **Date format**: Always `YYYY-MM-DD`; no timestamps, no slashes
5. **Number vs string**: `18000.00` not `"18000.00"`; the template explicitly requires JSON numbers
6. **Enum case sensitivity**: All enums are UPPER_SNAKE_CASE exactly as listed in the template
7. **conversion_years vs conversion_years_positive**: These are different fields — `conversion_years_positive` counts only non-zero years
8. **premium_gap sign**: Always the shortfall amount (premium minus capacity); when capacity covers premium, gap is 0, never negative
9. **RMD first_rmd_year**: Check client age carefully — clients at or above RMD age have `first_rmd_year = planning_year`; younger clients' first RMD year depends on SECURE 2.0 age thresholds
10. **heir_tax_profile**: Must be consistent with the projected balances — if Roth dominates, use `MOSTLY_TAX_FREE`; if traditional dominates, use `MOSTLY_TAXABLE`
11. **liquidity_gap**: When liquid assets cover the estate tax exposure and settlement costs, the gap can be zero; otherwise compute as `estate_tax_exposure + settlement_costs − liquid_assets`
12. **Duplicate risk_flag consistency**: In `estate_liquidity_action_plan`, `ilit.estate_inclusion_risk` must match `recommendation.risk_flag` when the ILIT is the primary risk driver
