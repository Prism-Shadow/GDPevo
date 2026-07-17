# Private Wealth Advisory — Structured Planning Skill

## Environment

Base URL: use the `GDPEVO_ENV_BASE_URL` supplied by the harness (HTTP). All endpoints are under `/api/` and use kebab-case naming. The API is a plain JSON REST service over HTTP; no authentication is required within the staging environment. Use `curl` or equivalent. Responses are JSON arrays or objects.

### Endpoint Reference

| Endpoint | Returns | Use |
|---|---|---|
| `GET /api/clients` | Array of client objects | Look up client by `client_id` |
| `GET /api/clients/{client_id}` | Single client object | Verify or pull a specific client |
| `GET /api/retirement-accounts` | Array of IRA account objects | Get traditional/Roth balances, expected return, RMD start age, recommended conversion years |
| `GET /api/rmd-factors` | Object mapping age→factor | IRS Uniform Lifetime Table; divisor for RMD = balance / factor |
| `GET /api/life-insurance` | Array of policy objects | Death benefit, annual premium, proposed owner, contribution date, existing-policy-transfer flag |
| `GET /api/trust-candidates` | Array of trust objects | Asset value, growth rate, GRAT term/annuity rate, CRAT term/payout rate |
| `GET /api/source-documents` | Array of document objects | CRM_NOTE, ATTORNEY_MEMO, SIGNED_PROFILE with `facts` payloads |
| `GET /api/policies/tax` | Tax constants object | Gift exclusion, estate exemption, estate rate, conversion bracket targets, CRAT max term, charitable deduction rate |

No other endpoints exist. Query parameters are not supported. Client sub-resource paths return `"error":"client not found"` — always list the full collection and filter on `client_id` client-side.

---

## Source Document Resolution (Critical for Every Task)

Every client has up to three source documents keyed by `source_type`:

| Source | Typical Date | Authority |
|---|---|---|
| `SIGNED_PROFILE` | 2026-02-06 | **Highest** — most recent, signed by client |
| `ATTORNEY_MEMO` | 2026-01-18 | Middle — attorney notes, may reflect stated intent |
| `CRM_NOTE` | 2025-11-20 | **Lowest** — stale CRM import, often conflicts |

**Rule**: When facts conflict across sources, the SIGNED_PROFILE always controls. Use the ATTORNEY_MEMO only when SIGNED_PROFILE omits a field. Never prefer CRM_NOTE values over SIGNED_PROFILE or ATTORNEY_MEMO values.

Key conflicts to expect:
- `beneficiary_count` — CRM_NOTE often shows a different number than SIGNED_PROFILE
- `annual_non_ira_income` — CRM_NOTE vs SIGNED_PROFILE can differ by $20K–$50K
- `philanthropic_intent` and `family_transfer_priority` — CRM_NOTE often shows "moderate" while SIGNED_PROFILE shows "high" / "low" pairings
- `marginal_tax_rate` — only present in SIGNED_PROFILE
- `estate_value` — ATTORNEY_MEMO and SIGNED_PROFILE should agree; CRM_NOTE lacks this field

For `source_resolution` fields:
- The **controlling profile source** is `SIGNED_PROFILE` whenever it provides the deciding fact values.
- The **controlling account source** is always `CUSTODIAN_EXPORT` (retirement account data).
- The **controlling beneficiary source** is `SIGNED_PROFILE` (it has the beneficiary_count).
- The **controlling policy source** is `SIGNED_PROFILE` by default (life insurance keyed by client, not from documents).
- The **controlling goal source** is `SIGNED_PROFILE` (has philanthropic_intent and family_transfer_priority).
- The **controlling asset source** is `ATTORNEY_MEMO` (estate_value used for trust asset sizing).

Note: The enum `STALE_MARKETING_INTAKE` is defined but CRM_NOTE is almost never the controlling source.

---

## Tax Policy Constants (`GET /api/policies/tax`)

These are the advisory-internal 2026 planning constants:

```
annual_gift_exclusion.2026       = $20,000
estate_tax_exemption.2026        = $13,610,000
estate_tax_rate                  = 0.40
conversion_bracket_targets.MFJ   = $394,600
conversion_bracket_targets.SINGLE = $197,300
conversion_bracket_targets.HOH   = $263,500
max_crat_term_years              = 20
charitable_deduction_rate        = 0.35
```

### How to Use Each Constant

- **Annual gift exclusion**: Multiply by beneficiary count to get `annual_exclusion_capacity`. Compare with `annual_premium` to compute `premium_gap`.
- **Estate tax exemption**: Subtract from `estate_value` to get taxable estate; multiply by 40% for `estate_tax_exposure`.
- **Conversion bracket targets**: These are the **top-line ceiling** (gross income before deduction) used to determine how much Roth conversion fits within the client's current marginal bracket. Convert up to this ceiling, not beyond it.
- **Max CRAT term**: CRATs are capped at 20 years. Use the `crat_term_years` from trust-candidates if ≤ 20, otherwise cap at 20.
- **Charitable deduction rate**: Used for CRAT income-tax deduction estimate: `crat.projected_charitable_remainder × charitable_deduction_rate`.

### Income Tax Brackets (Standard 2026)

The API provides bracket **ceiling** targets, but full 2026 marginal brackets are standardized:

| Rate | MFJ | SINGLE |
|---|---|---|
| 10% | $0–$23,200 | $0–$11,600 |
| 12% | $23,201–$94,300 | $11,601–$47,150 |
| 22% | $94,301–$201,050 | $47,151–$100,525 |
| 24% | $201,051–$394,600 | $100,526–$197,300 |
| 32% | $394,601–$501,050 | $197,301–$250,525 |
| 35% | $501,051–$751,600 | $250,526–$626,350 |
| 37% | $751,601+ | $626,351+ |

The `conversion_bracket_targets` values correspond to the **top of 24%** bracket. Use the client's `marginal_tax_rate` from SIGNED_PROFILE as the rate applied to conversion amounts.

---

## Analysis Type 1: Roth Conversion + RMD (`roth_conversion_rmd`)

Tasks: Mercer (train_001), Patel (train_005). Horizon is provided in the request memo.

### Key Data Sources
- Client record: `age`, `filing_status`, `liquid_assets`
- Retirement account: `traditional_balance`, `roth_balance`, `expected_return`, `rmd_start_age`, `recommended_conversion_years`
- RMD factors: mapping age→divisor
- SIGNED_PROFILE: `annual_non_ira_income`, `marginal_tax_rate`, `beneficiary_count`
- Tax policy: `conversion_bracket_targets` for the filing status

### Conversion Plan Calculation

1. **`first_conversion_year`** = `planning_year` (2026) — conversions begin immediately.
2. **`conversion_years`** = `recommended_conversion_years` from the retirement account (integer from the CUSTODIAN_EXPORT). This is the number of years to stage the conversion.
3. **`conversion_years_positive`** = same as `conversion_years` — it is the positive (non-zero) count of conversion years. Set it equal to `conversion_years`.
4. **`annual_conversion_amount`** = fill-up-to-ceiling logic:

   Determine remaining room in the target bracket:
   ```
   room = conversion_bracket_target - annual_non_ira_income
   annual_conversion_amount = min(traditional_balance / conversion_years, room)
   ```
   Cap at zero if no room (income already above target).

   For near-RMD clients (age ≥ 72): if `traditional_balance` can be fully converted within the bracket room over the available years before RMDs start, use that amount. Otherwise, convert up to the bracket ceiling each year.

5. **`total_converted`** = `annual_conversion_amount × conversion_years` (capped at `traditional_balance`).
6. **`total_conversion_tax`** = `total_converted × marginal_tax_rate`.

### RMD Projection

1. **`first_rmd_year`** = `planning_year + (rmd_start_age - age)`. RMD start age is always 73 in this environment.
2. **`horizon_year`** = from memo (e.g., 2046, 2042).

Baseline (no conversion):
- Grow `traditional_balance` at `expected_return` each year.
- From `first_rmd_year` through `horizon_year`: RMD = balance / rmd_factor_for_age, taxed at `marginal_tax_rate`.
- `baseline_rmd_tax_through_horizon` = sum of all RMD taxes over the RMD window.

Conversion scenario:
- Subtract converted amounts during conversion years. Grow remaining traditional balance.
- Grow Roth balance (starting + converted) at `expected_return`.
- From `first_rmd_year` through `horizon_year`: RMD on remaining traditional only.
- `conversion_rmd_tax_through_horizon` = sum of reduced RMD taxes.
- `rmd_tax_savings_through_horizon` = baseline − conversion (always non-negative if conversion makes sense).

3. **`rmd_tax_savings_through_horizon`** = `baseline_rmd_tax_through_horizon - conversion_rmd_tax_through_horizon`.

### Legacy Projection

- `projected_roth_balance_horizon` = Roth balance at horizon after growing at `expected_return` for horizon−planning_year years.
- `projected_traditional_balance_horizon` = Remaining traditional balance at horizon after conversions and RMDs.
- `heir_tax_profile`:
  - `MOSTLY_TAX_FREE` if projected Roth > 67% of total IRA assets
  - `MOSTLY_TAXABLE` if projected traditional > 67%
  - `MIXED_TAXABLE_AND_TAX_FREE` otherwise

### Recommendation Logic

- **`primary_action`**: `STAGED_ROTH_CONVERSION` if `rmd_tax_savings_through_horizon > 0` and `annual_conversion_amount > 0`. `DEFER` if RMDs start within 2 years and bracket room is minimal. `NO_CONVERSION` if age already past RMD start or no tax savings.
- **`suitability`**: `SUITABLE` when clear savings and adequate liquid assets. `BORDERLINE` when RMD near-term or small savings. `DEFER` when no meaningful benefit.
- **`risk_flag`**: `TAX_BRACKET_MANAGEMENT` (standard cases), `RMD_NEAR_TERM` (age ≥ 71), `LIQUIDITY_CONSTRAINT` (conversion tax > liquid_assets).

---

## Analysis Type 2: ILIT Crummey (`ilit_crummey_implementation`)

Task: Keating (train_002).

### Key Data Sources
- Client: age, filing_status, liquid_assets, estate_value
- Life insurance: death_benefit, annual_premium, planned_contribution_date, is_existing_policy_transfer
- SIGNED_PROFILE: beneficiary_count, marginal_tax_rate
- Tax policy: annual_gift_exclusion.2026

### Gift Plan Calculations

1. **`planning_year`** = 2026 (from client record).
2. **`annual_exclusion_per_beneficiary`** = `annual_gift_exclusion.2026` = $20,000.
3. **`beneficiary_count`** = from SIGNED_PROFILE (not CRM_NOTE).
4. **`annual_exclusion_capacity`** = `beneficiary_count × annual_exclusion_per_beneficiary`.
5. **`annual_premium`** = from life insurance policy.
6. **`premium_gap`** = `annual_premium - annual_exclusion_capacity`. If positive, the premium exceeds the exclusion capacity.

### Administration Dates

All derived from `planned_contribution_date`:
- **`contribution_date`** = `planned_contribution_date` (from life insurance record).
- **`notice_due_date`** = `contribution_date + 30 days` (Crummey notice must be sent within 30 days of contribution).
- **`withdrawal_window_end`** = `notice_due_date + 30 days` (beneficiaries have 30 days from notice to exercise withdrawal rights).
- **`earliest_premium_payment_date`** = `withdrawal_window_end + 1 day` (premium can be paid only after withdrawal window closes).
- **`notices_required`** = `beneficiary_count` (one Crummey notice per beneficiary).
- **`dedicated_bank_account_required`** = `true` (best practice for ILIT administration).

### Estate Result

- **`death_benefit`** = from life insurance policy.
- **`estate_inclusion_risk`**:
  - `LOW_IF_FORMALITIES_MET` when `premium_gap ≤ 0` and `is_existing_policy_transfer = false`
  - `EXCLUSION_SHORTFALL` when `premium_gap > 0`
  - `THREE_YEAR_LOOKBACK` when `is_existing_policy_transfer = true`
  - `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` when both conditions hold
- **`projected_outside_estate_if_implemented`** = `death_benefit` (if properly structured, ILIT keeps death benefit outside taxable estate).
- **`tax_liquidity_support`** = `death_benefit - (estate_value - estate_tax_exemption.2026) × estate_tax_rate`. Represents how much of the death benefit would cover estate tax. Floor at 0.

### Recommendation Logic

- `FUND_WITH_CRUMMEY_NOTICES` when `premium_gap ≤ 0` and no lookback — standard Crummey path.
- `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` when `premium_gap > 0` — gap exceeds exclusion capacity.
- `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` when `is_existing_policy_transfer = true` — three-year lookback issue.
- `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` when both lookback AND shortfall.

---

## Analysis Type 3: GRAT vs CRAT (`trust_comparison`)

Task: Alvarez (train_003).

### Key Data Sources
- Client: estate_value, liquid_assets, filing_status
- Trust candidate: asset_value, expected_growth_rate, grat_term_years, grat_annuity_rate, crat_term_years, crat_payout_rate
- SIGNED_PROFILE: philanthropic_intent, family_transfer_priority, marginal_tax_rate
- Tax policy: estate_tax_exemption, estate_tax_rate, charitable_deduction_rate, max_crat_term_years

### Estate Context

1. **`taxable_estate`** = `estate_value` (total gross estate for this analysis).
2. **`estate_tax_exposure`** = `max(0, (estate_value - estate_tax_exemption.2026) × estate_tax_rate)`.
3. **`liquidity_gap_before_planning`** = `max(0, estate_tax_exposure - liquid_assets)`.

### GRAT Analysis

- **`term_years`** = `grat_term_years` from trust candidate.
- **`projected_remainder_to_heirs`**: GRAT remainder calculation:
  - The grantor receives annuity payments = `asset_value × grat_annuity_rate` for `grat_term_years`.
  - Assets grow at `expected_growth_rate` inside the GRAT.
  - Remainder = final asset value after annuity payments minus the "hurdle" (return of the §7520-rate-adjusted present value). In the simplified model: `asset_value × (1 + expected_growth_rate)^grat_term_years - (annuity_payments accumulated at the hurdle rate)`.
  
  Simplified approximation: `asset_value × ((1 + expected_growth_rate)^grat_term_years - 1) × (expected_growth_rate - grat_annuity_rate) / expected_growth_rate`. When `expected_growth_rate > grat_annuity_rate`, there is a positive remainder.
  
  A more direct model: growth exceeds annuity rate → remainder exists. Compute as:
  ```
  future_value = asset_value × (1 + expected_growth_rate)^grat_term_years
  total_annuity = asset_value × grat_annuity_rate × grat_term_years
  remainder = max(0, future_value - total_annuity)
  ```
- **`estimated_estate_tax_reduction`** = `remainder × estate_tax_rate` (the portion of the remainder that would have been taxed at 40%).
- **`mortality_inclusion_risk`** = `TERM_SURVIVAL_REQUIRED` (always; GRAT requires grantor survival through term for tax benefit).

### CRAT Analysis

- **`term_years`** = `min(crat_term_years, max_crat_term_years)` — cap at 20 years.
- **`projected_charitable_remainder`**: 
  ```
  future_value = asset_value × (1 + expected_growth_rate)^crat_term_years
  annual_payout = asset_value × crat_payout_rate
  total_payouts = annual_payout × crat_term_years
  charitable_remainder = max(0, future_value - total_payouts)
  ```
- **`estimated_income_tax_deduction`** = `projected_charitable_remainder × charitable_deduction_rate`. This is the present value of the charitable remainder interest deduction.
- **`family_transfer_fit`**: `LOW` by default (CRAT primarily benefits charity). `MODERATE` if `philanthropic_intent = "high"`. `HIGH` only if both charitable and family priorities are strong.

### Recommendation Logic

- **`preferred_strategy`**: `GRAT` when `family_transfer_priority = "high"`. `CRAT` when `philanthropic_intent = "high"` AND `family_transfer_priority ≠ "high"`.
- **`rationale_code`**: `CHILDREN_TRANSFER_PRIORITY` when GRAT chosen. `PHILANTHROPIC_PRIORITY` when CRAT chosen.
- **`alternate_role`**: `SECONDARY_CHARITABLE_TOOL` (when GRAT preferred — CRAT as backup for charity). `SECONDARY_FAMILY_TRANSFER_TOOL` (when CRAT preferred — GRAT as backup for family).

---

## Analysis Type 4: Estate Liquidity Action Plan (`estate_liquidity_action_plan`)

Task: Chen (train_004). Combines ILIT analysis + trust comparison into an integrated plan.

### Key Data Sources
- Client: estate_value, liquid_assets, filing_status, age
- Life insurance: death_benefit, annual_premium, planned_contribution_date, is_existing_policy_transfer
- Trust candidate: asset_value, expected_growth_rate, grat_term_years, grat_annuity_rate
- SIGNED_PROFILE: beneficiary_count, philanthropic_intent, family_transfer_priority, annual_non_ira_income

### Estate Context (same as trust_comparison)

1. `taxable_estate` = estate_value
2. `estate_tax_exposure` = max(0, (estate_value − estate_tax_exemption.2026) × 0.40)
3. `liquidity_gap_before_planning` = max(0, estate_tax_exposure − liquid_assets)

### ILIT Section (same as ilit_crummey_implementation)

Same calculations. Note that `annual_exclusion_capacity` uses beneficiary_count from SIGNED_PROFILE.

### Trust Transfer Section

- `preferred_strategy`: `GRAT` when `family_transfer_priority = "high"`. `CRAT` otherwise.
- `projected_remainder_to_heirs`: GRAT remainder calculation (same as trust_comparison).
- `estimated_estate_tax_reduction`: `projected_remainder_to_heirs × 0.40`.
- `projected_charitable_remainder`: CRAT charitable remainder (same as trust_comparison). If GRAT preferred, this is the fallback scenario value.

### Action Set

Choose from: `ATTORNEY_DRAFT_REVIEW`, `CRAT_FOR_CHARITABLE_REMAINDER`, `GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`, `LIFETIME_EXEMPTION_ALLOCATION`.

- `ILIT_CRUMMEY_NOTICE_CYCLE` — always included when there's a life insurance policy.
- `GRAT_FOR_APPRECIATING_SHARES` — included when GRAT is preferred strategy.
- `CRAT_FOR_CHARITABLE_REMAINDER` — included when CRAT is preferred strategy OR as secondary tool.
- `LIFETIME_EXEMPTION_ALLOCATION` — included when premium_gap > 0.
- `ATTORNEY_DRAFT_REVIEW` — always included (drafting required for any trust strategy).

**Must be sorted alphabetically** in the output array.

### Recommendation

- `primary_action`: `COMBINE_ILIT_AND_GRAT` when both ILIT and GRAT applicable; `CRAT_WITH_LIQUIDITY_REVIEW` when CRAT preferred; `ILIT_WITH_EXEMPTION_REVIEW` when premium gap necessitates exemption.
- `sequencing`: `ILIT_FIRST_THEN_GRAT` (standard order — ILIT first for estate tax liquidity, then GRAT for wealth transfer). `TRUST_DECISION_FIRST` when CRAT is preferred. `ILIT_FIRST_THEN_ATTORNEY_REVIEW` when only ILIT applies.
- `risk_flag`: same logic as ILIT Crummey task.

---

## General Conventions

### Monetary Values
- All USD amounts must be JSON numbers (not strings), rounded to cents (2 decimal places).
- Use 2 decimal places consistently even for whole-dollar amounts (e.g., `20000.00` not `20000`).

### Dates
- All dates must be ISO 8601 `YYYY-MM-DD` format as strings.
- Planning year is always 2026.

### Enums
- Use exact enum values as specified in each answer template. Do not invent new values.
- Multiple-choice fields: copy the enum string exactly, including underscores and capitalization.

### Task ID
- Set `task_id` to the exact task identifier (e.g., `train_001`, `test_001`).
- Set `client_id` to the client ID from the engagement memo (e.g., `CLT-1001`).

### Output Format
- Return **only** a JSON object. No markdown fences, no prose.
- The JSON must include all `required_top_level_keys` from the answer template.
- Nested keys use dot-notation in the template (e.g., `recommendation.primary_action` means `{"recommendation": {"primary_action": "..."}}`).

### Data Filtering Pattern
- Always fetch the full collection endpoint, then filter client-side by `client_id`.
- Do NOT try nested paths like `/api/clients/{id}/accounts` — they return errors.
- When filtering, match `client_id` exactly (case-sensitive, e.g., `CLT-1001`).

### Common Pitfalls
1. **Using CRM_NOTE values over SIGNED_PROFILE**: Always prefer SIGNED_PROFILE. CRM_NOTE is stale.
2. **Wrong beneficiary count**: CRM_NOTE often disagrees with SIGNED_PROFILE. Use SIGNED_PROFILE.
3. **Forgetting to cap conversion amount at bracket ceiling**: Converting above the ceiling pushes income into a higher bracket, eroding tax savings.
4. **RMD factor lookup**: Use the client's age at each projection year, not current age. RMD = balance at end of prior year / factor for age in distribution year.
5. **Estate tax exposure floor at zero**: `max(0, ...)` — negative exposure means no estate tax.
6. **CRAT term cap**: Always cap CRAT term at 20 years regardless of trust-candidate data.
7. **action_set ordering**: Must be alphabetically sorted for `estate_liquidity_action_plan`.
8. **`conversion_years_positive` vs `conversion_years`**: They are typically the same value — both equal to `recommended_conversion_years`. Do not set one to zero.
9. **Premium gap sign**: Positive means shortfall (premium > exclusion capacity). This drives ILIT risk flags.
10. **Date arithmetic**: Crummey dates cascade: contribution → +30d notice → +30d withdrawal → +1d premium payment.
