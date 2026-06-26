# Private Wealth Advisory JSON Skill

Use this skill for private-wealth advisory tasks that ask for a structured JSON
planning answer using the staged prompt/memo/template plus the advisory API.
Return only the JSON object that conforms to `input/payloads/answer_template.json`.

## Operating Procedure

1. Read only the task prompt, request memo, and answer template. Extract the
   `client_id`, requested `analysis_type`, any planning horizon year, and every
   enum or required field from the template.
2. Query only the advisory API endpoints listed in `environment_access.md`:
   `/api/clients/<client_id>`, `/api/source-documents?client_id=...`,
   `/api/retirement-accounts?client_id=...`, `/api/life-insurance?client_id=...`,
   `/api/trust-candidates?client_id=...`, `/api/policies/tax`, and
   `/api/rmd-factors`.
3. Resolve conflicting facts before calculating. Prefer current signed/profile
   facts over stale CRM facts; use domain-specific API records for account,
   policy, and trust terms.
4. Calculate with full precision, then round currency outputs to two decimals.
   Emit JSON numbers, booleans, arrays, and ISO dates; do not stringify numbers.

## Source Resolution

- Profile facts: use `SIGNED_PROFILE` when present for age, planning year, filing
  status, marital status, annual non-IRA income, marginal tax rate, beneficiaries,
  estate value, liquid assets, philanthropic intent, and family-transfer priority.
  Fall back to `ATTORNEY_MEMO`, then `CRM_NOTE`; treat stale marketing/intake
  material as lowest priority.
- Retirement facts: use `CUSTODIAN_EXPORT` for traditional IRA balance, Roth
  balance, expected return, RMD start age, and recommended conversion years.
- Life-insurance facts: use `/api/life-insurance` for death benefit, premium,
  contribution date, ownership, and existing-policy-transfer status. If the
  template requires a `controlling_policy_source` but does not allow an insurance
  source enum, report `ATTORNEY_MEMO` for legal/ILIT policy implementation unless
  an allowed explicit source is present.
- Trust-candidate facts: use `/api/trust-candidates` for asset value, growth,
  GRAT term/rate, and CRAT term/payout. If the template requires
  `controlling_asset_source`, use `ATTORNEY_MEMO` unless an allowed explicit asset
  source is present.
- Goal source fields usually resolve to `SIGNED_PROFILE` when signed goals are
  present; otherwise use the attorney memo before CRM.

## Shared Tax Formulas

Use `/api/policies/tax` for the planning-year annual gift exclusion, estate tax
exemption, estate tax rate, conversion bracket target by filing status, maximum
CRAT term, and charitable deduction rate.

- `taxable_estate = max(0, estate_value - estate_tax_exemption[planning_year])`.
- `estate_tax_exposure = taxable_estate * estate_tax_rate`.
- `liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)`.
- Unless a task explicitly says otherwise, apply one household exemption/exclusion
  schedule; do not double just because the client is married.

## Roth Conversion and RMD

Inputs: signed profile, custodian retirement account, tax policy, RMD factors, and
memo horizon year.

- `first_rmd_year = planning_year + max(0, rmd_start_age - age)`.
- `years_until_rmd = max(0, first_rmd_year - planning_year)`.
- `conversion_years = min(recommended_conversion_years, years_until_rmd)`.
- `conversion_years_positive = max(0, conversion_years)`, but set it to `0` if
  bracket room is zero.
- `bracket_room = max(0, conversion_bracket_targets[filing_status] - annual_non_ira_income)`.
- `annual_conversion_amount = min(traditional_balance / conversion_years_positive, bracket_room)`;
  use `0` when `conversion_years_positive` is zero.
- `total_converted = annual_conversion_amount * conversion_years_positive`.
- `total_conversion_tax = total_converted * marginal_tax_rate`.

Projection convention:

- For the baseline, start with current traditional/Roth balances. For each year
  through the horizon, use attained age `age + (year - planning_year)`. Beginning
  with `first_rmd_year`, compute `rmd = traditional_balance / rmd_factor[age]`,
  subtract it from traditional balance, and add `rmd * marginal_tax_rate` to RMD
  tax. Grow remaining traditional and Roth balances annually at `expected_return`.
- For the conversion case, make the annual conversion at the start of each
  positive conversion year before RMD/growth. Move the converted amount from
  traditional to Roth, then run the same RMD and growth loop.
- `rmd_tax_savings_through_horizon = baseline_rmd_tax_through_horizon -
  conversion_rmd_tax_through_horizon`.
- Use the conversion-case ending balances for legacy projection. Set heir tax
  profile by Roth share of total ending retirement assets: `MOSTLY_TAX_FREE` if
  Roth share is at least 80%, `MIXED_TAXABLE_AND_TAX_FREE` if at least 20%, else
  `MOSTLY_TAXABLE`.

Recommendation mapping:

- Use `LIQUIDITY_CONSTRAINT` if liquid assets cannot comfortably cover conversion
  tax; otherwise `RMD_NEAR_TERM` when there are two or fewer years until RMD;
  otherwise `TAX_BRACKET_MANAGEMENT`.
- Use `STAGED_ROTH_CONVERSION`/`SUITABLE` when there are positive conversion
  years, positive bracket room, no liquidity issue, and RMD tax savings are
  positive. Use `DEFER`/`BORDERLINE` for near-term RMD or liquidity concerns with
  some benefit. Use `NO_CONVERSION` or `DEFER` when bracket room, conversion years,
  or projected benefit are zero.

## ILIT and Crummey Funding

Inputs: signed profile beneficiaries, life-insurance record, estate context, and
tax policy.

- `annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year]`.
- `annual_exclusion_capacity = annual_exclusion_per_beneficiary * beneficiary_count`.
- `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`.
- `notices_required = beneficiary_count`.
- `contribution_date = planned_contribution_date`.
- Date convention when no task-specific rule overrides it:
  `notice_due_date = contribution_date + 5 calendar days`;
  `withdrawal_window_end = notice_due_date + 30 calendar days`;
  `earliest_premium_payment_date = withdrawal_window_end + 1 calendar day`.
- `dedicated_bank_account_required = true`.
- `projected_outside_estate_if_implemented = death_benefit`.
- `tax_liquidity_support = min(death_benefit, liquidity_gap_before_planning)`.

Risk and action mapping:

- No existing policy transfer and no premium gap: `LOW_IF_FORMALITIES_MET`,
  `FUND_WITH_CRUMMEY_NOTICES`, `SUITABLE_WITH_ADMINISTRATION`.
- Premium gap only: `EXCLUSION_SHORTFALL`,
  `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`, usually `BORDERLINE`.
- Existing policy transfer only: `THREE_YEAR_LOOKBACK`,
  `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`, usually `BORDERLINE`.
- Both issues: `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`,
  `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`, usually `BORDERLINE` or
  `NOT_SUITABLE` if the gap/lookback dominates the plan.

## GRAT, CRAT, and Trust Comparison

Inputs: signed/attorney goals, trust-candidate record, estate context, and tax
policy.

- `grat.projected_remainder_to_heirs =
  max(0, asset_value * ((1 + expected_growth_rate)^grat_term_years -
  (1 + grat_annuity_rate)^grat_term_years))`.
- `grat.estimated_estate_tax_reduction =
  grat.projected_remainder_to_heirs * estate_tax_rate`.
- `crat.term_years = min(crat_term_years, max_crat_term_years)`.
- `crat.projected_charitable_remainder =
  asset_value * (1 + expected_growth_rate - crat_payout_rate)^crat.term_years`.
- `crat.estimated_income_tax_deduction =
  asset_value * charitable_deduction_rate`.
- Use `TERM_SURVIVAL_REQUIRED` for GRAT mortality inclusion risk.

Recommendation mapping:

- Prefer `GRAT` when family-transfer priority is stronger than philanthropic
  intent; rationale `CHILDREN_TRANSFER_PRIORITY`; alternate role
  `SECONDARY_CHARITABLE_TOOL`.
- Prefer `CRAT` when philanthropic intent is stronger; rationale
  `PHILANTHROPIC_PRIORITY`; alternate role `SECONDARY_FAMILY_TRANSFER_TOOL`.
- CRAT `family_transfer_fit` is `LOW` when family transfer is the dominant goal,
  `MODERATE` when goals are mixed, and `HIGH` only when philanthropy clearly
  dominates and family transfer is not central.

## Estate Liquidity Action Plan

Combine the estate context, ILIT, and trust-transfer calculations.

- Prefer `COMBINE_ILIT_AND_GRAT` with sequencing `ILIT_FIRST_THEN_GRAT` when the
  client has low ILIT implementation risk and the trust comparison favors GRAT.
- Prefer `CRAT_WITH_LIQUIDITY_REVIEW` with sequencing `TRUST_DECISION_FIRST` when
  philanthropy dominates and the CRAT is the preferred trust strategy.
- Use `ILIT_WITH_EXEMPTION_REVIEW` with sequencing
  `ILIT_FIRST_THEN_ATTORNEY_REVIEW` when ILIT funding has an exclusion shortfall,
  an existing-policy transfer/lookback issue, or both.
- Build `action_set` from the actual recommendations, then sort alphabetically.
  Common actions are `ILIT_CRUMMEY_NOTICE_CYCLE`, `GRAT_FOR_APPRECIATING_SHARES`,
  `CRAT_FOR_CHARITABLE_REMAINDER`, `LIFETIME_EXEMPTION_ALLOCATION`, and
  `ATTORNEY_DRAFT_REVIEW`.

## Output Checks

- Include every required top-level key and nested field in the answer template.
- Use exactly the enum spellings from the template.
- Sort only fields the template says to sort, especially `action_set`.
- Return the final JSON object only, with no explanatory prose.
