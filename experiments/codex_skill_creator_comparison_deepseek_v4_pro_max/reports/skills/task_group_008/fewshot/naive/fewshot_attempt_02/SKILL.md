---
name: private-wealth-advisory
description: Solve private wealth advisory planning tasks by querying the advisory API, resolving conflicting source documents, computing structured outputs for Roth conversions, ILIT Crummey funding, trust comparisons (GRAT/CRAT), and estate liquidity action plans, then returning a JSON object conforming to the supplied answer template.
---

# Private Wealth Advisory Skill

Use this skill when a task prompt asks you to support a private wealth advisory team and directs you to a task-group advisory API. The workflow is always: read the prompt and memo, query the API for client data, resolve source conflicts, compute the structured output, and return only a JSON object matching the supplied answer template.

## Core Workflow

1. Read the task `prompt.txt` to identify the client ID, engagement type, and API base URL.
2. Read the `request_memo.md` for the planning horizon year and other engagement-specific parameters.
3. Read the `answer_template.json` to learn exactly what output shape is required. The template's `required_top_level_keys` and field enums define the analysis type.
4. Query the advisory API (see [API Reference](#api-reference)) to collect all data for the client.
5. Resolve conflicting source documents using the rules in [Source Resolution](#source-resolution).
6. Compute every field using the methodology for the analysis type (see [Analysis Types](#analysis-types)).
7. Return **only** a JSON object conforming to the template. No prose outside the JSON.

## API Reference

All endpoints are served from the base URL supplied as `API_BASE` in the harness (typically `http://task-env:9008/`). Use `GET` for all requests. No authentication is required.

| Endpoint | Returns |
|---|---|
| `/api/clients` | List of all clients with household name, age, filing status, estate value, liquid assets, and advisor team. |
| `/api/clients/{client_id}` | Single client record. |
| `/api/source-documents` | All source documents (CRM notes, attorney memos, signed profiles) keyed by client, with `source_type`, `effective_date`, and a `facts` object. |
| `/api/retirement-accounts` | Retirement accounts keyed by client, with `source_type: CUSTODIAN_EXPORT`, traditional and Roth balances, expected return, RMD start age, and recommended conversion years. |
| `/api/life-insurance` | Life insurance policies keyed by client, with death benefit, annual premium, planned contribution date, proposed owner (ILIT), and whether the policy is an existing transfer. |
| `/api/trust-candidates` | Trust candidate cases keyed by client, with asset value, expected growth rate, GRAT term and annuity rate, CRAT term and payout rate. |
| `/api/policies/tax` | Tax constants: annual gift exclusion by year, estate tax exemption by year, estate tax rate (0.40), conversion bracket targets by filing status, max CRAT term, charitable deduction rate (0.35). |
| `/api/rmd-factors` | RMD life expectancy factors by age (starting at 73). |
| `/portal/client/{client_id}` | Human-readable client portal page (informational only). |

## Source Resolution

Every client has multiple source documents. Conflicts exist because older CRM imports disagree with newer attorney memos and signed profiles. Apply these rules to select the controlling source for each category.

### Profile fields (income, beneficiaries, intent, tax rate, age, filing status, marital status, liquid assets, estate value)

Always prefer `SIGNED_PROFILE`. It is the most recent and formally signed by the client. If a field is absent from the signed profile, fall back to `ATTORNEY_MEMO`, then `CRM_NOTE`.

### Account data (IRA balances, returns, RMD start age, conversion years)

Always use `CUSTODIAN_EXPORT`. Custodian records are authoritative for retirement account balances and parameters.

### Trust asset valuation

Use `ATTORNEY_MEMO` for controlling asset source (the attorney's valuation carries the most authority for trust funding decisions). For the donor's goals and priorities, use `SIGNED_PROFILE`.

### Life insurance policy data

Use `SIGNED_PROFILE` for controlling policy source when it exists. Life insurance records in the API carry their own policy-level data (death benefit, premium, contribution date, transfer status) which is authoritative for that policy's terms.

### Source resolution fields in output

Every analysis type's answer template includes a `source_resolution` block. Fill it with the `controlling_*_source` enums that match the selections above:

- Profile source: `SIGNED_PROFILE` (always, unless the signed profile is missing, in which case `ATTORNEY_MEMO`)
- Account source: `CUSTODIAN_EXPORT`
- Goal/beneficiary/policy source: `SIGNED_PROFILE`
- Asset source (for trusts): `ATTORNEY_MEMO`

## Analysis Types

The analysis type is determined by the `required_top_level_keys` and field enums in the answer template. Four types appear in the training evidence.

### roth_conversion_rmd (Roth Conversion and RMD Tax Summary)

**Required data:** Client record, signed profile facts, custodian retirement account, tax policy constants, RMD factors, request memo horizon year.

**Key computations:**

- `recommendation.primary_action`: `STAGED_ROTH_CONVERSION` when the client has positive bracket headroom and a positive traditional balance. `DEFER` when headroom is zero or negative. `NO_CONVERSION` only when traditional balance is zero.
- `recommendation.suitability`: `SUITABLE` with positive headroom; `BORDERLINE` with marginal headroom (less than $10,000); `DEFER` otherwise.
- `recommendation.risk_flag`: When suitability is `SUITABLE`, use `TAX_BRACKET_MANAGEMENT`. Use `LIQUIDITY_CONSTRAINT` if liquid assets are tight relative to conversion tax. Use `RMD_NEAR_TERM` when first RMD year is within 1 year of planning year.

**Conversion plan:**
  - `first_conversion_year` = the planning year (from signed profile or client record).
  - `conversion_years` = `recommended_conversion_years` from the custodian retirement account.
  - `conversion_years_positive` = same as `conversion_years`.
  - `annual_conversion_amount` = bracket target for the client's filing status (from `/api/policies/tax` `conversion_bracket_targets`) minus `annual_non_ira_income` from the signed profile. If this is zero or negative, set to 0 and change the recommendation accordingly.
  - `total_converted` = `annual_conversion_amount` multiplied by `conversion_years`, capped at the traditional IRA balance (do not convert more than exists).
  - `total_conversion_tax` = `total_converted` multiplied by marginal tax rate from the signed profile. Round to cents.

**RMD projection:**
  - `horizon_year` = from the request memo.
  - `first_rmd_year` = planning year plus (RMD start age minus client age from signed profile).
  - `baseline_rmd_tax_through_horizon`: Model the traditional IRA growing each year at `expected_return`. Starting in `first_rmd_year`, each year's RMD = prior-year-end traditional balance divided by the RMD factor for the client's attained age that year. Tax on each RMD = RMD multiplied by marginal rate. Sum taxes from `first_rmd_year` through `horizon_year`. Round to cents.
  - `conversion_rmd_tax_through_horizon`: Same model, but during the conversion years (`first_conversion_year` through `first_conversion_year + conversion_years - 1`), subtract `annual_conversion_amount` from the traditional balance at the start of each year (after growth, before RMD calculation). The converted amounts move to the Roth and grow at the same `expected_return`. RMDs are computed on the reduced traditional balance. Sum RMD taxes through horizon.
  - `rmd_tax_savings_through_horizon` = `baseline_rmd_tax_through_horizon` minus `conversion_rmd_tax_through_horizon`. Round to cents.

**Legacy projection:**
  - `projected_roth_balance_horizon`: Start with the initial Roth balance from the custodian account. During conversion years, add `annual_conversion_amount` at the start of each year. Grow the entire balance at `expected_return` through `horizon_year`.
  - `projected_traditional_balance_horizon`: The traditional balance at the end of `horizon_year` from the conversion-RMD model described above (after all conversions, after all RMDs through the horizon, including the horizon-year RMD if the horizon year is at least `first_rmd_year`).
  - `heir_tax_profile`: `MOSTLY_TAX_FREE` if the projected Roth balance is more than 2 times the traditional balance; `MOSTLY_TAXABLE` if traditional is more than 2 times Roth; otherwise `MIXED_TAXABLE_AND_TAX_FREE`.

### ilit_crummey_implementation (ILIT Crummey Funding Cycle)

**Required data:** Client record, signed profile (beneficiary count), life insurance policy, tax policy (gift exclusion, estate tax rate).

**Key computations:**

- `recommendation.primary_action`: Evaluate the policy's `is_existing_policy_transfer` flag and the premium gap.
  - If `is_existing_policy_transfer` is false and `premium_gap` is at most 0: `FUND_WITH_CRUMMEY_NOTICES`.
  - If `is_existing_policy_transfer` is false and `premium_gap` is greater than 0: `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`.
  - If `is_existing_policy_transfer` is true and `premium_gap` is at most 0: `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` (the three-year lookback applies).
  - If both flags are problematic: combine accordingly.
- `recommendation.suitability`: `SUITABLE_WITH_ADMINISTRATION` when the primary action involves Crummey notices and formalities are met. `BORDERLINE` when there is a shortfall or lookback. `NOT_SUITABLE` only for severe issues.
- `recommendation.risk_flag`:
  - `LOW_IF_FORMALITIES_MET` when `is_existing_policy_transfer` is false and `premium_gap` is at most 0.
  - `EXCLUSION_SHORTFALL` when `premium_gap` is greater than 0.
  - `THREE_YEAR_LOOKBACK` when `is_existing_policy_transfer` is true.
  - `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` when both apply.

**Gift plan:**
  - `planning_year` = from signed profile or client record.
  - `annual_exclusion_per_beneficiary` = from `/api/policies/tax`, `annual_gift_exclusion` for the planning year.
  - `beneficiary_count` = from signed profile.
  - `annual_exclusion_capacity` = `annual_exclusion_per_beneficiary` multiplied by `beneficiary_count`.
  - `annual_premium` = from life insurance policy.
  - `premium_gap` = max(0, `annual_premium` minus `annual_exclusion_capacity`). Round to cents.

**Administration (Crummey timeline):**
  - `notices_required` = `beneficiary_count`.
  - `contribution_date` = `planned_contribution_date` from the life insurance policy (ISO date string).
  - `notice_due_date` = `contribution_date` plus 7 calendar days.
  - `withdrawal_window_end` = `notice_due_date` plus 30 calendar days (standard Crummey withdrawal period).
  - `earliest_premium_payment_date` = `withdrawal_window_end` plus 1 calendar day.
  - `dedicated_bank_account_required`: Always `true` for a properly administered Crummey ILIT. The trust needs its own account to receive contributions and demonstrate present-interest gifts.

**Estate result:**
  - `death_benefit` = from life insurance policy.
  - `estate_inclusion_risk` = same as `recommendation.risk_flag` (they are identical in every training example).
  - `projected_outside_estate_if_implemented` = `death_benefit` when `estate_inclusion_risk` is `LOW_IF_FORMALITIES_MET`. If there is a lookback risk, the death benefit might be partially or fully includible; the answer should reflect the projected outside-estate amount under the recommended course of action.
  - `tax_liquidity_support` = `death_benefit` multiplied by estate tax rate (0.40) from tax policy. Round to cents.

### trust_comparison (GRAT versus CRAT Recommendation)

**Required data:** Client record, signed profile, attorney memo, trust candidate, tax policy constants, request memo.

**Key computations:**

- `recommendation.preferred_strategy`: `GRAT` when `family_transfer_priority` (from signed profile) is `"high"`. `CRAT` when `philanthropic_intent` is `"high"` and family transfer priority is `"moderate"` or lower.
- `recommendation.rationale_code`: `CHILDREN_TRANSFER_PRIORITY` with GRAT; `PHILANTHROPIC_PRIORITY` with CRAT.
- `recommendation.alternate_role`: `SECONDARY_CHARITABLE_TOOL` when GRAT is primary; `SECONDARY_FAMILY_TRANSFER_TOOL` when CRAT is primary.

**Estate context:**
  - `planning_year` = from signed profile.
  - `exemption_used` = estate tax exemption from tax policy for the planning year. For MFJ clients, multiply the exemption by 2 (portability). For SINGLE and HOH, use the exemption as-is.
  - `taxable_estate` = `estate_value` (from signed profile) minus `exemption_used`. Floor at 0.
  - `estate_tax_exposure` = `taxable_estate` multiplied by estate tax rate (0.40). Round to cents.
  - `liquid_assets_available` = `liquid_assets` from signed profile.
  - `liquidity_gap_before_planning` = max(0, `estate_tax_exposure` minus `liquid_assets_available`). Round to cents.

**GRAT computation:**
  - `term_years` = `grat_term_years` from the trust candidate.
  - `projected_remainder_to_heirs`: Model year by year. Start with `asset_value` from the trust candidate. Each year: multiply the current balance by (1 plus `expected_growth_rate`), then subtract the annual annuity (computed as `asset_value` multiplied by `grat_annuity_rate`). The final balance after `term_years` is the remainder to heirs. Round to cents.
  - `estimated_estate_tax_reduction` = `projected_remainder_to_heirs` multiplied by estate tax rate (0.40). Round to cents.
  - `mortality_inclusion_risk`: Always `TERM_SURVIVAL_REQUIRED` (the GRAT remainder is only excluded from the estate if the grantor survives the term).

**CRAT computation:**
  - `term_years` = `crat_term_years` from the trust candidate (always 20 in training data, matching `max_crat_term_years`).
  - `projected_charitable_remainder`: Model year by year. Start with `asset_value`. Each year: multiply by (1 plus `expected_growth_rate`), then subtract the annual payout (`asset_value` multiplied by `crat_payout_rate`). The balance after `term_years` goes to charity. Round to cents.
  - `estimated_income_tax_deduction` = `projected_charitable_remainder` multiplied by charitable deduction rate (0.35 from tax policy). Round to cents.
  - `family_transfer_fit`: Use `LOW` when family transfer priority is `"high"` (CRAT gives little to family). Use `HIGH` when philanthropic intent is `"high"` and family priority is `"low"`. Otherwise `MODERATE`.

### estate_liquidity_action_plan (Estate Liquidity Action Plan)

This analysis combines elements from both ILIT and trust comparison, plus an action set.

**Required data:** Client record, signed profile, life insurance policy, trust candidate, tax policy constants.

**Key computations:**

- `recommendation.primary_action`: Evaluate the combined picture.
  - When an ILIT policy exists with no transfer lookback and no premium gap, AND a trust candidate with high-growth assets is available: `COMBINE_ILIT_AND_GRAT`.
  - When philanthropic intent is `"high"`: `CRAT_WITH_LIQUIDITY_REVIEW`.
  - Otherwise: `ILIT_WITH_EXEMPTION_REVIEW`.
- `recommendation.sequencing`:
  - With `COMBINE_ILIT_AND_GRAT`: `ILIT_FIRST_THEN_GRAT` (implement the insurance structure before the wealth transfer).
  - When a lookback issue exists: `TRUST_DECISION_FIRST`.
  - Otherwise: `ILIT_FIRST_THEN_ATTORNEY_REVIEW`.
- `recommendation.risk_flag`: Same rules as the ILIT analysis.

**Estate context:** Compute identically to the trust comparison estate context.

**ILIT section:** Compute `annual_exclusion_capacity`, `premium_gap`, `estate_inclusion_risk`, and `projected_outside_estate_if_implemented` using the ILIT Crummey rules (see above, but only the sub-fields requested by the template).

**Trust transfer section:** Compute `preferred_strategy`, `projected_remainder_to_heirs`, `estimated_estate_tax_reduction`, and `projected_charitable_remainder` using the trust comparison rules (choose GRAT or CRAT based on family/philanthropic intent, then compute the relevant fields).

**Action set:** Build a sorted (alphabetically) list from the available action enums:
  - Include `ILIT_CRUMMEY_NOTICE_CYCLE` when an ILIT policy exists for the client and the risk flag allows.
  - Include `GRAT_FOR_APPRECIATING_SHARES` when a trust candidate exists and family transfer priority is `"high"`.
  - Include `CRAT_FOR_CHARITABLE_REMAINDER` when philanthropic intent is `"high"`.
  - Include `ATTORNEY_DRAFT_REVIEW` when there is a lookback risk (policy transfer) or significant complexity.
  - Include `LIFETIME_EXEMPTION_ALLOCATION` when the premium gap is greater than 0.

## Computational Notes

### Rounding
All USD amounts must be rounded to cents (two decimal places) and represented as JSON numbers, not strings. Use standard rounding (half-up).

### Date arithmetic
Use ISO 8601 dates (`YYYY-MM-DD`). When adding days, add calendar days (not business days). The date arithmetic for ILIT Crummey is:
- notice_due_date = contribution_date + 7 calendar days
- withdrawal_window_end = notice_due_date + 30 calendar days
- earliest_premium_payment_date = withdrawal_window_end + 1 calendar day

### RMD modeling
For each projection year starting from `first_rmd_year`:
1. Start with prior-year-end balance.
2. Apply growth: balance = balance * (1 + expected_return).
3. Compute RMD: rmd = balance / rmd_factor[age], where age = client_age + (year - planning_year). Use the `/api/rmd-factors` endpoint for the factor table.
4. Tax on RMD: rmd * marginal_tax_rate.
5. year-end balance = balance - rmd.

For the conversion scenario, during the conversion years:
- Before step 2: traditional_balance = traditional_balance - annual_conversion_amount.
- Roth balance for that year: roth_balance = roth_balance + annual_conversion_amount.
- Then apply growth to both balances.

### GRAT/CRAT year-by-year modeling
For each year in the term:
1. Apply growth: balance = balance * (1 + expected_growth_rate).
2. Subtract the annual payout: balance = balance - (initial_asset_value * payout_rate).
3. The final balance after the last year is the remainder.

### Bracket targets
The `conversion_bracket_targets` from `/api/policies/tax` are the top of the current marginal bracket for each filing status. The headroom for conversion is the bracket target minus `annual_non_ira_income`. This keeps the conversion within the client's current bracket.

### Estate tax exemption
For MFJ clients, the exemption is doubled (both spouses). For SINGLE and HOH, use the exemption value directly from tax policy.

### Task id
Every output must include `"task_id"` set to the task identifier found in the prompt (e.g., `"train_001"`, `"test_001"`). This is the stable task identifier string, not a path.

## Output

Return only the JSON object. No markdown fences, no explanatory prose. The JSON must match the answer template's `required_top_level_keys` and field types exactly.
