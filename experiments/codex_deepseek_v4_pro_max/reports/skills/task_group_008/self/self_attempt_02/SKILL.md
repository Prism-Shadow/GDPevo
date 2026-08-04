## Overview

This skill equips an agent to act as a private wealth advisory support analyst. The agent queries a task-group advisory API for client records, source documents, account exports, life-insurance records, trust candidates, tax policy constants, and RMD factors. It resolves conflicts across data sources imported from different advisory systems at different times, computes tax-aware projections, and returns a structured JSON output conforming to an engagement-specific answer template.

## API Reference

The advisory API base URL is supplied by the harness, typically as the environment variable `API_BASE`. Use only the following endpoints; do not fabricate additional endpoints.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Health / root |
| GET | `/api/clients` | List all client records |
| GET | `/api/clients/{client_id}` | Single client record |
| GET | `/api/source-documents` | Source documents (signed profiles, attorney memos, CRM notes, custodian exports, marketing intakes) |
| GET | `/api/retirement-accounts` | Retirement account balances, holdings, and custodian exports |
| GET | `/api/life-insurance` | Life-insurance policy records |
| GET | `/api/trust-candidates` | Trust structures and candidate recommendations |
| GET | `/api/policies/tax` | Tax policy constants (rates, brackets, exemptions, exclusions) |
| GET | `/api/rmd-factors` | IRS RMD distribution-period factors by age |
| GET | `/portal/client/{client_id}` | Client portal summary view (HTML) |

Always start by calling `/api/clients/{client_id}` to retrieve the client profile, then pull supporting records as needed by the engagement type.

## Workflow

1. **Read the request memo** (`input/payloads/request_memo.md`) for the client ID, engagement type, planning horizon, and any special instructions.
2. **Read the answer template** (`input/payloads/answer_template.json`) to understand the required output shape and field constraints.
3. **Fetch client data** from the API: client record, source documents, retirement accounts, life insurance, trust candidates, tax policies, and RMD factors.
4. **Resolve source conflicts** using the source-resolution methodology below.
5. **Compute projections** following the computation patterns for the analysis type.
6. **Fill the template** with the resolved and computed values.
7. **Return only the JSON object** — no prose, no markdown fences, no commentary outside the JSON.

## Source Resolution

Client records may conflict because they were imported from different advisory systems at different times. When values diverge, prefer sources in this order:

```
SIGNED_PROFILE > ATTORNEY_MEMO > CUSTODIAN_EXPORT > CRM_NOTE > STALE_MARKETING_INTAKE
```

Every output includes a `source_resolution` block that identifies the controlling source for each data domain. Map each domain to the most authoritative source that supplied a usable value:

- **Profile domain** (`controlling_profile_source`): client demographics, goals, beneficiary designations, estate-planning intent. Valid enum values: `SIGNED_PROFILE`, `ATTORNEY_MEMO`, `CUSTODIAN_EXPORT`, `CRM_NOTE`, `STALE_MARKETING_INTAKE`.
- **Account domain** (`controlling_account_source`): retirement account balances, holdings, custodian data. Valid enum values: `CUSTODIAN_EXPORT`, `SIGNED_PROFILE`, `CRM_NOTE`.
- **Beneficiary domain** (`controlling_beneficiary_source`): beneficiary counts, named beneficiaries. Valid enum values: `SIGNED_PROFILE`, `ATTORNEY_MEMO`, `CUSTODIAN_EXPORT`, `CRM_NOTE`, `STALE_MARKETING_INTAKE`.
- **Policy domain** (`controlling_policy_source`): life-insurance policy details, death benefit, premium. Valid enum values: `SIGNED_PROFILE`, `ATTORNEY_MEMO`, `CUSTODIAN_EXPORT`, `CRM_NOTE`.
- **Goal domain** (`controlling_goal_source`): client goals and priorities (e.g., children vs. philanthropic). Valid enum values: `SIGNED_PROFILE`, `ATTORNEY_MEMO`, `CUSTODIAN_EXPORT`, `CRM_NOTE`, `STALE_MARKETING_INTAKE`.
- **Asset domain** (`controlling_asset_source`): asset types, values, liquidity-event details. Valid enum values: `ATTORNEY_MEMO`, `SIGNED_PROFILE`, `CRM_NOTE`.

When a more authoritative source is silent on a field, fall through to the next source in the hierarchy. Document only the source that ultimately provides the controlling values.

## Analysis Types and Output Schemas

### 1. `roth_conversion_rmd`

Used for engagements evaluating staged Roth conversions before or near Required Minimum Distributions.

**Top-level keys**: `task_id`, `client_id`, `analysis_type`, `recommendation`, `conversion_plan`, `rmd_projection`, `legacy_projection`, `source_resolution`

**Recommendation fields**:
- `primary_action`: `STAGED_ROTH_CONVERSION` | `DEFER` | `NO_CONVERSION`
- `suitability`: `SUITABLE` | `BORDERLINE` | `DEFER`
- `risk_flag`: `TAX_BRACKET_MANAGEMENT` | `LIQUIDITY_CONSTRAINT` | `RMD_NEAR_TERM`

**Conversion plan**: `first_conversion_year` (integer), `conversion_years` (integer, total planned years), `conversion_years_positive` (integer, years with positive conversion amounts), `annual_conversion_amount` (USD), `total_converted` (USD), `total_conversion_tax` (USD).

**RMD projection**: `horizon_year` (integer), `first_rmd_year` (integer), `baseline_rmd_tax_through_horizon` (USD, tax without conversions), `conversion_rmd_tax_through_horizon` (USD, tax with conversions), `rmd_tax_savings_through_horizon` (USD, difference).

**Legacy projection**: `projected_roth_balance_horizon` (USD), `projected_traditional_balance_horizon` (USD), `heir_tax_profile`: `MOSTLY_TAX_FREE` | `MIXED_TAXABLE_AND_TAX_FREE` | `MOSTLY_TAXABLE`.

**Source resolution**: `controlling_profile_source`, `controlling_account_source`.

### 2. `ilit_crummey_implementation`

Used for ILIT (Irrevocable Life Insurance Trust) Crummey funding-cycle engagements.

**Top-level keys**: `task_id`, `client_id`, `analysis_type`, `recommendation`, `gift_plan`, `administration`, `estate_result`, `source_resolution`

**Recommendation fields**:
- `primary_action`: `FUND_WITH_CRUMMEY_NOTICES` | `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` | `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` | `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`
- `suitability`: `SUITABLE_WITH_ADMINISTRATION` | `BORDERLINE` | `NOT_SUITABLE`
- `risk_flag`: `LOW_IF_FORMALITIES_MET` | `EXCLUSION_SHORTFALL` | `THREE_YEAR_LOOKBACK` | `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`

**Gift plan**: `planning_year` (integer), `annual_exclusion_per_beneficiary` (USD), `beneficiary_count` (integer), `annual_exclusion_capacity` (USD = exclusion × count), `annual_premium` (USD), `premium_gap` (USD = premium − capacity, non-negative or zero).

**Administration**: `notices_required` (integer, equals beneficiary_count), `contribution_date` (ISO date), `notice_due_date` (ISO date), `withdrawal_window_end` (ISO date), `earliest_premium_payment_date` (ISO date), `dedicated_bank_account_required` (boolean).

**Estate result**: `death_benefit` (USD), `estate_inclusion_risk` (same enum as risk_flag), `projected_outside_estate_if_implemented` (USD), `tax_liquidity_support` (USD).

**Source resolution**: `controlling_beneficiary_source`, `controlling_policy_source`.

### 3. `trust_comparison`

Used for GRAT vs. CRAT comparison engagements after a liquidity event.

**Top-level keys**: `task_id`, `client_id`, `analysis_type`, `recommendation`, `estate_context`, `grat`, `crat`, `source_resolution`

**Recommendation fields**:
- `preferred_strategy`: `GRAT` | `CRAT`
- `rationale_code`: `CHILDREN_TRANSFER_PRIORITY` | `PHILANTHROPIC_PRIORITY`
- `alternate_role`: describes what the non-preferred strategy could be used for instead.

**Estate context**: `total_estate` (USD), `estate_tax_exemption_remaining` (USD), `liquidity_event_amount` (USD).

**GRAT**:
- `funding_amount` (USD), `term_years` (integer), `hurdle_rate` (number, decimal)
- `projected_remainder_to_heirs` (USD), `estimated_estate_tax_savings` (USD)
- `children_transfer_fit`: `LOW` | `MODERATE` | `HIGH`

**CRAT**:
- `funding_amount` (USD), `payout_rate` (number, decimal), `term_years` (integer)
- `projected_charitable_remainder` (USD), `estimated_income_tax_deduction` (USD)
- `family_transfer_fit`: `LOW` | `MODERATE` | `HIGH`

**Source resolution**: `controlling_goal_source`, `controlling_asset_source`.

### 4. `estate_liquidity_action_plan`

Used for estate liquidity planning combining ILIT, trust transfer, and attorney coordination.

**Top-level keys**: `task_id`, `client_id`, `analysis_type`, `recommendation`, `estate_context`, `ilit`, `trust_transfer`, `action_set`, `source_resolution`

**Recommendation fields**:
- `primary_action`: `COMBINE_ILIT_AND_GRAT` | `CRAT_WITH_LIQUIDITY_REVIEW` | `ILIT_WITH_EXEMPTION_REVIEW`
- `sequencing`: `ILIT_FIRST_THEN_GRAT` | `TRUST_DECISION_FIRST` | `ILIT_FIRST_THEN_ATTORNEY_REVIEW`
- `risk_flag`: same ILIT risk flags (`LOW_IF_FORMALITIES_MET`, `EXCLUSION_SHORTFALL`, `THREE_YEAR_LOOKBACK`, `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`)

**Estate context**: `taxable_estate` (USD), `estate_tax_exposure` (USD), `liquidity_gap_before_planning` (USD).

**ILIT** (same shape as ilit_crummey_implementation): `annual_exclusion_capacity`, `premium_gap`, `estate_inclusion_risk`, `projected_outside_estate_if_implemented`.

**Trust transfer**: `preferred_strategy` (`GRAT` | `CRAT`), `projected_remainder_to_heirs` (USD), `estimated_estate_tax_reduction` (USD), `projected_charitable_remainder` (USD).

**Action set**: alphabetically sorted list drawn from: `ATTORNEY_DRAFT_REVIEW`, `CRAT_FOR_CHARITABLE_REMAINDER`, `GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`, `LIFETIME_EXEMPTION_ALLOCATION`.

**Source resolution**: `controlling_goal_source`, `controlling_policy_source`.

## Output Formatting Rules

- Return **only** the JSON object. No prose, no markdown fences, no commentary.
- All USD amounts must be JSON numbers (not strings), rounded to two decimal places (cents).
- All dates must be ISO 8601 `YYYY-MM-DD` strings.
- All years must be JSON integers.
- Boolean fields must be JSON `true` or `false`.
- `task_id` is a stable identifier matching the task name (e.g. `train_001`).
- `action_set` arrays must be sorted alphabetically.
- Object key order is not scored unless explicitly noted in the template.

## Computation Patterns

### RMD Calculation

1. Determine the client's age in each projection year. The first RMD year is the year the client reaches RMD age (use `/api/policies/tax` for the current RMD age threshold).
2. For each year from the first RMD year through the horizon year, compute the RMD as: `prior-year-end traditional IRA balance / IRS distribution-period factor for that age` (from `/api/rmd-factors`).
3. Multiply each year's RMD by the applicable marginal tax rate (from `/api/policies/tax`) to get the RMD tax for that year.
4. Sum RMD taxes from the first RMD year through the horizon year for the baseline scenario.
5. For the conversion scenario, reduce traditional IRA balances by conversion amounts in the conversion years, then recompute RMDs and RMD taxes.
6. RMD tax savings = baseline RMD tax − conversion-scenario RMD tax.

### Roth Conversion Plan

1. Determine the conversion window: start year, number of years, and annual amount that stays within the current marginal tax bracket (to avoid bracket creep). Use `/api/policies/tax` for bracket thresholds.
2. Total converted = annual conversion amount × number of positive-conversion years.
3. Total conversion tax = total converted × applicable tax rate.
4. Project Roth balance at horizon = `(current Roth balance × (1 + assumed growth rate)^years) + sum of (annual conversion × (1 + growth rate)^remaining years)`.
5. Project traditional balance at horizon = `(current traditional balance − total converted) × (1 + growth rate)^years` minus RMDs taken along the way.

### ILIT / Crummey Analysis

1. Retrieve the annual gift-tax exclusion amount from `/api/policies/tax`.
2. Annual exclusion capacity = annual exclusion per beneficiary × beneficiary count.
3. Premium gap = annual premium − annual exclusion capacity. If gap > 0, the shortfall requires lifetime exemption allocation.
4. Crummey timeline: contribution date → notice due date (typically within 30 days of contribution) → withdrawal window end (typically 30 days after notice) → earliest premium payment date (after withdrawal window).
5. Estate inclusion risk assessment:
   - `LOW_IF_FORMALITIES_MET`: Crummey formalities followed, no three-year lookback issue.
   - `EXCLUSION_SHORTFALL`: Premium exceeds annual exclusion capacity.
   - `THREE_YEAR_LOOKBACK`: Policy transferred to ILIT within three years; death benefit may be includible under IRC §2035.
   - `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`: Both conditions apply.
6. Projected outside estate = death benefit (if ILIT properly structured and no lookback/exclusion issues); otherwise estimate includible portion.

### Trust Comparison (GRAT vs. CRAT)

1. Retrieve the applicable federal rate (hurdle rate) and CRAT payout-rate rules from `/api/policies/tax`.
2. **GRAT**: fund with appreciating assets. Remainder to heirs = funding amount × ((1 + assumed appreciation rate)^term − (1 + hurdle rate)^term). Estate tax savings = remainder × estate tax rate.
3. **CRAT**: fund with assets; fixed annual payout to charity. Charitable remainder = funding amount × (1 − (payout rate × term, capped at exhaustion)). Income tax deduction = present value of remainder based on AFR.
4. Recommendation logic:
   - If client goals prioritize children/legacy: prefer GRAT, code `CHILDREN_TRANSFER_PRIORITY`.
   - If client goals prioritize philanthropy: prefer CRAT, code `PHILANTHROPIC_PRIORITY`.

### Estate Liquidity

1. Taxable estate = total estate − applicable exclusion amount (from `/api/policies/tax`).
2. Estate tax exposure = taxable estate × estate tax rate.
3. Liquidity gap = estate tax exposure − liquid assets available.
4. Select action set based on gap and available strategies: ILIT for death-benefit liquidity, GRAT/CRAT for asset transfer, lifetime exemption for shortfall coverage.

## Risk Flag Taxonomy

| Risk Flag | Context | Meaning |
|-----------|---------|---------|
| `TAX_BRACKET_MANAGEMENT` | Roth conversion | Conversions must stay within current bracket |
| `LIQUIDITY_CONSTRAINT` | Roth conversion | Client may lack cash to pay conversion taxes |
| `RMD_NEAR_TERM` | Roth conversion | RMD age is close, limiting conversion runway |
| `LOW_IF_FORMALITIES_MET` | ILIT / estate | Crummey formalities followed; low risk |
| `EXCLUSION_SHORTFALL` | ILIT / estate | Premium exceeds annual exclusion capacity |
| `THREE_YEAR_LOOKBACK` | ILIT / estate | Policy transferred within three-year §2035 window |
| `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` | ILIT / estate | Both lookback and shortfall issues present |

## Suitability Taxonomy

| Suitability | Context | Meaning |
|-------------|---------|---------|
| `SUITABLE` | Roth conversion | Good candidate; proceed with staged conversions |
| `BORDERLINE` | Roth conversion | Marginal benefit; requires closer review |
| `DEFER` | Roth conversion | Not currently suitable; reassess later |
| `SUITABLE_WITH_ADMINISTRATION` | ILIT | Workable if Crummey formalities are followed |
| `BORDERLINE` | ILIT | Marginal; may need structural changes |
| `NOT_SUITABLE` | ILIT | Do not proceed under current conditions |

## Primary Action Taxonomy

| Primary Action | Context | Meaning |
|----------------|---------|---------|
| `STAGED_ROTH_CONVERSION` | Roth | Execute multi-year Roth conversions |
| `DEFER` | Roth | Delay conversion decision |
| `NO_CONVERSION` | Roth | Conversion not recommended |
| `FUND_WITH_CRUMMEY_NOTICES` | ILIT | Use annual exclusion gifts with Crummey notices |
| `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` | ILIT | Cover premium gap with lifetime exemption |
| `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` | ILIT | Accept three-year lookback or use a new policy |
| `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` | ILIT | Disclose lookback risk and allocate exemption |
| `COMBINE_ILIT_AND_GRAT` | Estate | Use both ILIT and GRAT together |
| `CRAT_WITH_LIQUIDITY_REVIEW` | Estate | Use CRAT with liquidity assessment |
| `ILIT_WITH_EXEMPTION_REVIEW` | Estate | ILIT with exemption allocation review |
