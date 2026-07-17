# Private Wealth Advisory — Structured Planning Skill

## Environment

The advisory API is reachable at the base URL provided in `environment_access.md` (the `GDPEVO_ENV_BASE_URL`). All endpoints are under `/api/`. Use `curl` to fetch records; all responses are JSON arrays or objects. Query-parameter filtering is supported on list endpoints with `?client_id=CLT-XXXX`.

### Known API Endpoints

| Endpoint | Filterable | Key Fields |
|---|---|---|
| `/api/clients` | `?client_id=X` | `client_id`, `household_name`, `age`, `marital_status`, `filing_status`, `planning_year`, `estate_value`, `liquid_assets` |
| `/api/retirement-accounts` | `?client_id=X` | `account_id`, `traditional_balance`, `roth_balance`, `expected_return`, `rmd_start_age`, `recommended_conversion_years` |
| `/api/life-insurance` | no (filter client-side) | `policy_id`, `death_benefit`, `annual_premium`, `planned_contribution_date`, `is_existing_policy_transfer` |
| `/api/trust-candidates` | no (filter client-side) | `trust_case_id`, `asset_value`, `expected_growth_rate`, `grat_term_years`, `grat_annuity_rate`, `crat_term_years`, `crat_payout_rate` |
| `/api/source-documents` | `?client_id=X` | `document_id`, `source_type`, `effective_date`, `title`, `facts` (dict) |
| `/api/rmd-factors` | no | age→divisor mapping for ages 73–99 |

**Single-client lookup**: `/api/clients/CLT-XXXX` returns the client object directly.

### Source Document Types and Resolution

Three source types exist, listed in descending authority:

| Priority | Source Type | Typical `effective_date` | Notes |
|---|---|---|---|
| 1 (highest) | `SIGNED_PROFILE` | 2026-02-06 | Most recent, most complete, signed by client. Contains `marginal_tax_rate`, `beneficiary_count`, `philanthropic_intent`, `family_transfer_priority`, income, age, filing status. |
| 2 | `ATTORNEY_MEMO` | 2026-01-18 | Attorney notes. Contains `estate_value`, `family_transfer_priority`, `philanthropic_intent`. |
| 3 (lowest) | `CRM_NOTE` | 2025-11-20 or 2025-10-15 | Stale CRM import. Often conflicts with signed profile on beneficiary count, income, philanthropic intent. Two titles: "Prior CRM profile import" (train clients) and "CRM import before spring refresh" (other clients). |

**Resolution rule**: Prefer `SIGNED_PROFILE` > `ATTORNEY_MEMO` > `CRM_NOTE`. When a fact is present in the higher-authority source, use that value. The CRM note is the stale/marketing intake equivalent — it was imported from an older system and may have outdated beneficiary counts, income figures, or intent flags.

**For `source_resolution` fields**:
- `controlling_profile_source`: `SIGNED_PROFILE` (unless facts only come from attorney memo or CRM)
- `controlling_account_source`: `CUSTODIAN_EXPORT` (retirement account data always comes from custodian)
- `controlling_beneficiary_source`: The source providing the beneficiary count used
- `controlling_policy_source`: The source providing the insurance policy data used
- `controlling_goal_source`: The source providing philanthropic/family transfer intent
- `controlling_asset_source`: The source providing asset valuation used

### Tax Policy Constants (2026)

The API provides RMD factors but not tax rate schedules. Use these standard 2026 values:

| Constant | 2026 Value | Notes |
|---|---|---|
| Estate tax exemption (per person) | $13,610,000 | Indexed annually; verify against client estate data |
| Estate tax rate (top marginal) | 40% | Applied to taxable estate above exemption |
| Gift tax annual exclusion (per beneficiary) | $19,000 | For Crummey withdrawal right calculations |
| Lifetime gift/estate exemption | Same as estate exemption | Unified credit |
| Section 7520 rate (GRAT/CRAT discount) | Varies monthly | The API trust-candidate `grat_annuity_rate` embeds this |

The client's marginal income tax rate comes from the `SIGNED_PROFILE` document facts (`marginal_tax_rate` field).

## Analysis Types and Output Schemas

### 1. Roth Conversion + RMD (`analysis_type: "roth_conversion_rmd"`)

Used for: Train 001, Train 005, and similar tasks with `conversion_plan`, `rmd_projection`, `legacy_projection`.

**Computation rules:**

- `first_conversion_year` = `planning_year` (2026) unless client is already taking RMDs
- `conversion_years` = `recommended_conversion_years` from retirement-accounts endpoint (capped by years until RMD start if pre-RMD strategy)
- `conversion_years_positive` = same as `conversion_years` (all years have positive conversion amounts)
- `annual_conversion_amount` = `traditional_balance / conversion_years`, rounded to cents
- `total_converted` = `traditional_balance` (full conversion), rounded to cents
- `total_conversion_tax` = `total_converted × marginal_tax_rate`, rounded to cents

**RMD projection (no-conversion baseline)**:
1. Grow the traditional balance at `expected_return` from `planning_year` through the year before `first_rmd_year`
2. For each RMD year: RMD = prior-year-end balance ÷ RMD factor for that age; tax = RMD × `marginal_tax_rate`; remaining balance grows at `expected_return`
3. Sum RMD taxes from `first_rmd_year` through `horizon_year`

**RMD projection (with conversion)**:
1. For each conversion year (before RMDs): subtract `annual_conversion_amount`, then grow remaining balance
2. For years where RMDs overlap with conversions: subtract conversion amount first, then compute RMD on the remaining balance
3. Roth balance grows tax-free; converted amount each year is added to Roth and compounds

**Key formulas**:
- `baseline_rmd_tax_through_horizon` = sum of (year-end-balance / rmd_factor × marginal_rate) for all RMD years without any conversion
- `conversion_rmd_tax_through_horizon` = same calculation but on the reduced balance after conversions
- `rmd_tax_savings_through_horizon` = baseline − conversion (always positive; larger is better)

**Legacy projection**:
- `projected_roth_balance_horizon`: sum of each annual conversion compounded at `expected_return` to horizon year
- `projected_traditional_balance_horizon`: remaining traditional balance after all RMDs through horizon
- `heir_tax_profile`: `MOSTLY_TAX_FREE` if Roth dominates, `MIXED_TAXABLE_AND_TAX_FREE` if both substantial, `MOSTLY_TAXABLE` if traditional dominates

**Risk flags**:
- `TAX_BRACKET_MANAGEMENT`: large conversions may push client into a higher bracket
- `LIQUIDITY_CONSTRAINT`: client may not have liquid assets to pay conversion tax
- `RMD_NEAR_TERM`: client is within 1–2 years of RMD start age, limiting conversion runway
- `DEFER`: the conversion strategy should be deferred (when suitability is DEFER)

**Suitability**:
- `SUITABLE`: ample conversion runway (3+ years before RMDs), manageable tax impact
- `BORDERLINE`: narrow runway (1–2 years) or tax bracket risks
- `DEFER`: already in RMD phase or conversion would cause bracket jump without offsetting benefit

### 2. ILIT Crummey Implementation (`analysis_type: "ilit_crummey_implementation"`)

Used for: Train 002 and tasks with `gift_plan`, `administration`, `estate_result`.

**Computation rules**:
- `planning_year` = 2026 (current planning year)
- `beneficiary_count` = from SIGNED_PROFILE (NOT CRM which may be stale)
- `annual_exclusion_per_beneficiary` = $19,000 (2026 gift tax annual exclusion)
- `annual_exclusion_capacity` = `annual_exclusion_per_beneficiary × beneficiary_count`
- `annual_premium` = from life-insurance endpoint
- `premium_gap` = `annual_premium − annual_exclusion_capacity` (0 if capacity covers premium; positive if shortfall exists)

**Administration dates** (based on `planned_contribution_date` from life-insurance):
- `contribution_date` = `planned_contribution_date` (ISO YYYY-MM-DD)
- `notice_due_date` = contribution_date + 30 days
- `withdrawal_window_end` = contribution_date + 60 days
- `earliest_premium_payment_date` = `contribution_date` (ILIT pays premium after contribution clears)
- `notices_required` = `beneficiary_count` (one Crummey notice per beneficiary)
- `dedicated_bank_account_required` = `true` (standard ILIT best practice; always true for proper administration)

**Estate result**:
- `death_benefit` = from life-insurance endpoint
- `estate_inclusion_risk`:
  - `LOW_IF_FORMALITIES_MET` — standard new policy with proper Crummey administration
  - `EXCLUSION_SHORTFALL` — premium exceeds gift tax exclusion capacity
  - `THREE_YEAR_LOOKBACK` — existing policy was transferred within 3 years of death (when `is_existing_policy_transfer` is true)
  - `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` — both risks present
- `projected_outside_estate_if_implemented` = `death_benefit` (if ILIT properly structured, full DB outside estate)
- `tax_liquidity_support` = `death_benefit` (death benefit provides estate tax liquidity)

**Recommendation**:
- `FUND_WITH_CRUMMEY_NOTICES`: standard case with manageable premium gap (≤ annual exclusion or small shortfall)
- `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`: premium gap is material and client should allocate exemption
- `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`: existing policy with lookback risk — consider new policy
- `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`: existing policy transfer with unavoidable lookback

**Suitability**:
- `SUITABLE_WITH_ADMINISTRATION`: plan works if Crummey formalities are followed
- `BORDERLINE`: material premium gap or minor administration concerns
- `NOT_SUITABLE`: significant lookback risk or premium far exceeds capacity

### 3. GRAT vs CRAT Comparison (`analysis_type: "trust_comparison"`)

Used for: Train 003 and trust comparison tasks.

**Estate context**:
- `taxable_estate` = max(0, `estate_value − exemption_amount`). For MFJ: exemption = 2 × per-person; for SINGLE/HOH: exemption = 1 × per-person.
- `estate_tax_exposure` = `taxable_estate × 0.40` (estate tax rate)
- `liquidity_gap_before_planning` = max(0, `estate_tax_exposure − liquid_assets`)

**GRAT computation** (Grantor Retained Annuity Trust):
- `term_years` = `grat_term_years` from trust-candidates
- Annual annuity = `asset_value × grat_annuity_rate`
- Year-by-year simulation: balance = (balance × (1 + growth_rate)) − annuity; repeat for `term_years`
- `projected_remainder_to_heirs` = max(0, ending balance)
- `estimated_estate_tax_reduction` = `projected_remainder_to_heirs × 0.40`
- `mortality_inclusion_risk` = `TERM_SURVIVAL_REQUIRED` (grantor must survive the GRAT term)

**CRAT computation** (Charitable Remainder Annuity Trust):
- `term_years` = `crat_term_years` from trust-candidates (typically 20)
- Annual payout = `asset_value × crat_payout_rate` (typically 0.055)
- Year-by-year simulation same as GRAT but with crat term and payout rate
- `projected_charitable_remainder` = max(0, ending balance)
- `estimated_income_tax_deduction` = present value of charitable remainder; compute as `projected_charitable_remainder / (1 + discount_rate)^term` where discount rate ≈ Section 7520 rate (~5%)
- `family_transfer_fit`:
  - `LOW` — CRAT primarily benefits charity, minimal family transfer
  - `MODERATE` — some family benefit through income stream or tax savings
  - `HIGH` — significant family benefit (rare for CRATs; typically LOW)

**Recommendation**:
- `preferred_strategy`:
  - `GRAT` when `family_transfer_priority` = "high" and `philanthropic_intent` ≠ "high"
  - `CRAT` when `philanthropic_intent` = "high" and `family_transfer_priority` ≠ "high"
  - When both are "high" or both are "moderate": default to `GRAT` (family priority typically dominates in private wealth)
- `rationale_code`:
  - `CHILDREN_TRANSFER_PRIORITY` when GRAT is preferred
  - `PHILANTHROPIC_PRIORITY` when CRAT is preferred
- `alternate_role`:
  - When GRAT preferred: `SECONDARY_CHARITABLE_TOOL` (CRAT as backup charitable vehicle)
  - When CRAT preferred: `SECONDARY_FAMILY_TRANSFER_TOOL` (GRAT as backup family transfer vehicle)

### 4. Estate Liquidity Action Plan (`analysis_type: "estate_liquidity_action_plan"`)

Used for: Train 004 and multi-strategy estate planning tasks.

**Estate context**: Same computation as trust_comparison (taxable estate, estate tax exposure, liquidity gap).

**ILIT section**: Same computation pattern as ILIT Crummey (exclusion capacity, premium gap, inclusion risk, projected outside estate).

**Trust transfer section**: GRAT/CRAT computation from trust_comparison type, using trust-candidate data.

**Recommendation**:
- `primary_action`:
  - `COMBINE_ILIT_AND_GRAT`: when liquidity gap > 0 and both ILIT and GRAT data are present
  - `CRAT_WITH_LIQUIDITY_REVIEW`: when philanthropic intent is high and CRAT can address liquidity
  - `ILIT_WITH_EXEMPTION_REVIEW`: when ILIT alone could suffice with exemption allocation
- `sequencing`:
  - `ILIT_FIRST_THEN_GRAT`: fund life insurance first for death benefit certainty, then transfer assets
  - `TRUST_DECISION_FIRST`: when trust choice (GRAT vs CRAT) drives the overall plan
  - `ILIT_FIRST_THEN_ATTORNEY_REVIEW`: when documentation formalities need attorney review after ILIT setup
- `risk_flag`: same enum as ILIT inclusion risk

**Action set**: Build from applicable strategies, then **sort alphabetically** (required by schema):
- `ATTORNEY_DRAFT_REVIEW` — when trust documents need attorney review
- `CRAT_FOR_CHARITABLE_REMAINDER` — when CRAT is part of the strategy
- `GRAT_FOR_APPRECIATING_SHARES` — when GRAT is part of the strategy
- `ILIT_CRUMMEY_NOTICE_CYCLE` — when ILIT with Crummey notices is part of the strategy
- `LIFETIME_EXEMPTION_ALLOCATION` — when lifetime exemption use is recommended

## General Output Conventions

### JSON Formatting
- All numbers are JSON numbers, **never strings**
- USD amounts rounded to **cents** (2 decimal places)
- Dates are ISO 8601 strings `YYYY-MM-DD`
- Years are integers
- Booleans are JSON `true`/`false`
- Enum values: UPPERCASE_WITH_UNDERSCORES, case-sensitive
- `task_id`: use the task identifier from prompt context (e.g., `"train_001"`, `"test_001"`)
- `client_id`: match the client ID from the request memo exactly (e.g., `"CLT-1001"`)

### Enum Values Reference

**Roth conversion**:
- `primary_action`: `STAGED_ROTH_CONVERSION`, `DEFER`, `NO_CONVERSION`
- `suitability`: `SUITABLE`, `BORDERLINE`, `DEFER`
- `risk_flag`: `TAX_BRACKET_MANAGEMENT`, `LIQUIDITY_CONSTRAINT`, `RMD_NEAR_TERM`
- `heir_tax_profile`: `MOSTLY_TAX_FREE`, `MIXED_TAXABLE_AND_TAX_FREE`, `MOSTLY_TAXABLE`

**ILIT Crummey**:
- `primary_action`: `FUND_WITH_CRUMMEY_NOTICES`, `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`, `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`, `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`
- `suitability`: `SUITABLE_WITH_ADMINISTRATION`, `BORDERLINE`, `NOT_SUITABLE`
- `risk_flag` / `estate_inclusion_risk`: `LOW_IF_FORMALITIES_MET`, `EXCLUSION_SHORTFALL`, `THREE_YEAR_LOOKBACK`, `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`

**Trust comparison**:
- `preferred_strategy`: `GRAT`, `CRAT`
- `rationale_code`: `CHILDREN_TRANSFER_PRIORITY`, `PHILANTHROPIC_PRIORITY`
- `alternate_role`: `SECONDARY_CHARITABLE_TOOL`, `SECONDARY_FAMILY_TRANSFER_TOOL`
- `family_transfer_fit`: `LOW`, `MODERATE`, `HIGH`

**Estate liquidity**:
- `primary_action`: `COMBINE_ILIT_AND_GRAT`, `CRAT_WITH_LIQUIDITY_REVIEW`, `ILIT_WITH_EXEMPTION_REVIEW`
- `sequencing`: `ILIT_FIRST_THEN_GRAT`, `TRUST_DECISION_FIRST`, `ILIT_FIRST_THEN_ATTORNEY_REVIEW`
- `action_set`: alphabetically sorted subset of `ATTORNEY_DRAFT_REVIEW`, `CRAT_FOR_CHARITABLE_REMAINDER`, `GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`, `LIFETIME_EXEMPTION_ALLOCATION`

**Source resolution (all types)**:
- Profile/doc sources: `SIGNED_PROFILE`, `ATTORNEY_MEMO`, `CUSTODIAN_EXPORT`, `CRM_NOTE`, `STALE_MARKETING_INTAKE`
- Account sources: `CUSTODIAN_EXPORT`, `SIGNED_PROFILE`, `CRM_NOTE`
- Asset sources: `ATTORNEY_MEMO`, `SIGNED_PROFILE`, `CRM_NOTE`

## Common Pitfalls

1. **Stale CRM data**: CRM documents often have different beneficiary counts, income figures, and intent flags than the signed profile. Always prefer SIGNED_PROFILE facts over CRM_NOTE facts when both exist. The CRM beneficiary count is frequently wrong.

2. **RMD factor lookups**: RMD factors are keyed by integer age strings (`"73"`, not `73`). The divisor for age 73 is 26.5. Use the factor for the age the client turns in the RMD year.

3. **Conversion timing**: Conversions happen at the beginning of the year (subtract from balance before growth), RMDs happen at year-end (subtract after growth). For years with both, convert first, then grow, then compute RMD.

4. **Roth balance accumulation**: The Roth balance at horizon is the sum of each converted tranche compounded forward to the horizon year, plus any pre-existing Roth balance compounded forward. Each conversion year's amount compounds for `(horizon_year − conversion_year)` years.

5. **Premium gap sign**: When `annual_exclusion_capacity ≥ annual_premium`, `premium_gap` is 0 (not negative). The gap represents the uncovered portion of the premium.

6. **GRAT vs CRAT asset value**: Both use the same `asset_value` from trust-candidates but with different terms and rates. The GRAT transfers remainder to heirs; the CRAT transfers remainder to charity.

7. **action_set sorting**: Must be sorted alphabetically (lexicographically as strings). The schema explicitly requires this.

8. **Estate tax exemption for married couples**: MFJ clients get 2× the per-person exemption. SINGLE and HOH get 1×.

9. **is_existing_policy_transfer**: When `true`, the THREE_YEAR_LOOKBACK risk flag applies (IRC §2035). When `false`, standard ILIT treatment applies.

10. **conversion_years vs conversion_years_positive**: In typical cases these are equal. They differ only if some conversion years have a zero conversion amount (e.g., waiting until a future year to start).

## Workflow Recipe

1. **Fetch all data**: Query all six endpoints. Filter by `client_id` where supported, otherwise filter client-side.
2. **Resolve conflicts**: For each fact category, select the controlling source by authority (SIGNED_PROFILE > ATTORNEY_MEMO > CRM_NOTE > CUSTODIAN_EXPORT for non-account facts; CUSTODIAN_EXPORT for account balances).
3. **Identify analysis type**: From the prompt or request memo, determine which analysis type schema applies.
4. **Compute numeric values**: Follow the computation rules for the specific analysis type. Use the client's `marginal_tax_rate` from the signed profile for all tax calculations.
5. **Select enums**: Choose enum values based on computed results and intent signals from the controlling source.
6. **Build and validate JSON**: Ensure all required top-level keys are present, numbers are JSON numbers, dates are ISO strings, enums match the defined sets exactly, and `action_set` is alphabetically sorted.
