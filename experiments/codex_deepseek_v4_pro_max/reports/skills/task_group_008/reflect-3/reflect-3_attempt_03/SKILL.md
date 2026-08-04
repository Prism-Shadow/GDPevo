## Private Wealth Advisory — Structured Planning Output

Generate a JSON object for a private-wealth advisory task by querying an advisory API,
applying deterministic financial-planning formulas, and resolving conflicting source
records according to a fixed hierarchy. Return only the JSON; no surrounding prose.

### Data Retrieval

Collect every relevant record before computing:

- `GET /api/clients` — all client profiles indexed by `client_id`
- `GET /api/clients/{client_id}` — single-client summary
- `GET /api/source-documents` — conflict-resolution documents (SIGNED_PROFILE, ATTORNEY_MEMO, CRM_NOTE, STALE_MARKETING_INTAKE)
- `GET /api/retirement-accounts` — IRA balances and parameters
- `GET /api/life-insurance` — ILIT policy details
- `GET /api/trust-candidates` — GRAT / CRAT parameters
- `GET /api/policies/tax` — annual gift exclusion, estate exemption, bracket targets, rates
- `GET /api/rmd-factors` — age-keyed divisor table

### Source-Resolution Hierarchy (all tasks)

When records disagree:

1. **SIGNED_PROFILE** — most recent, signed by client; always the controlling profile source unless
   the field is account-level data
2. **ATTORNEY_MEMO** — second in authority; may contain priorities not in the signed profile
3. **CUSTODIAN_EXPORT** — controlling for account balances, expected return, conversion years,
   and RMD start age
4. **CRM_NOTE** — typically stale; do not use when a newer SIGNED_PROFILE or ATTORNEY_MEMO exists
5. **STALE_MARKETING_INTAKE** — never controlling when any other source is present

For `source_resolution` fields:
- `controlling_profile_source` / `controlling_goal_source` / `controlling_beneficiary_source`:
  SIGNED_PROFILE when it contains the relevant facts, with a later effective date than CRM.
- `controlling_account_source`: always CUSTODIAN_EXPORT.
- `controlling_policy_source`: SIGNED_PROFILE when no policy-specific conflict exists.
- `controlling_asset_source`: use SIGNED_PROFILE unless the attorney memo explicitly governs assets.

### Roth Conversion & RMD Tasks (`analysis_type: roth_conversion_rmd`)

**Conversion Plan**

- `first_conversion_year` = client planning year (always the current year from the client record).
- `conversion_years` = `recommended_conversion_years` from the custodian retirement-account export.
- `conversion_years_positive` = `conversion_years` (every year in the plan has a positive conversion).
- `annual_conversion_amount` = bracket-constrained slice:
  ```
  bracket_room = conversion_bracket_targets[filing_status] - annual_non_ira_income
  annual_conversion_amount = min(traditional_balance / conversion_years, bracket_room)
  ```
  Use `annual_non_ira_income` and `filing_status` from the SIGNED_PROFILE; use
  `conversion_bracket_targets` from `/api/policies/tax`.
- `total_converted` = `annual_conversion_amount * conversion_years`.
- `total_conversion_tax` = `total_converted * marginal_tax_rate` (rate from SIGNED_PROFILE).

**RMD Projection** — always use *RMD-first* ordering:
1. Take RMD = `balance / rmd_factors[current_age]` (if `current_age >= rmd_start_age`).
2. Subtract RMD from balance.
3. Apply growth: `balance = balance * (1 + expected_return)`.

Compute both baseline (no conversions) and conversion scenarios over the planning horizon.
RMD tax = `rmd_amount * marginal_tax_rate`.  `rmd_tax_savings` = baseline – conversion.

- `horizon_year` = the year given in the request memo.
- `first_rmd_year` = `planning_year + (rmd_start_age - client_age)`.

**Legacy Projection**

Apply the same RMD-first / conversion ordering (without applying taxes to RMD withdrawals
for the balance calculation itself). Compute both Roth and traditional balances at the
horizon year.

- `heir_tax_profile`:
  - `MOSTLY_TAX_FREE` when projected Roth balance > 2× traditional balance.
  - `MIXED_TAXABLE_AND_TAX_FREE` when the ratio is between 0.5× and 2×.
  - `MOSTLY_TAXABLE` when traditional dominates.

**Recommendation**

- `primary_action`: always `STAGED_ROTH_CONVERSION` when a conversion plan is computed.
- `suitability`: `SUITABLE` when there are at least 2 full conversion years before RMD start;
  `BORDERLINE` when 0–1 years remain.
- `risk_flag`: `TAX_BRACKET_MANAGEMENT` when the bracket constraint binds (conversion capped
  below the equal-split amount); `RMD_NEAR_TERM` when `first_rmd_year - first_conversion_year ≤ 1`;
  `LIQUIDITY_CONSTRAINT` otherwise.

### ILIT Crummey Tasks (`analysis_type: ilit_crummey_implementation`)

**Gift Plan**

- `planning_year` = client planning year.
- `annual_exclusion_per_beneficiary` = `annual_gift_exclusion` for the planning year.
- `beneficiary_count` from SIGNED_PROFILE.
- `annual_exclusion_capacity` = exclusion × beneficiary_count.
- `annual_premium` from the life-insurance policy.
- `premium_gap` = `max(0, annual_premium - annual_exclusion_capacity)` (zero when capacity covers premium).

**Administration**

- `notices_required` = `beneficiary_count`.
- `contribution_date` = `planned_contribution_date` from the policy.
- `notice_due_date` = same as `contribution_date` (notices go out upon funding).
- `withdrawal_window_end` = `contribution_date + 30 days`.
- `earliest_premium_payment_date` = `withdrawal_window_end + 1 day`.
- `dedicated_bank_account_required` = `true`.

**Estate Result**

- `death_benefit` from the policy.
- `estate_inclusion_risk`: `LOW_IF_FORMALITIES_MET` for new policies (`is_existing_policy_transfer` = false);
  `THREE_YEAR_LOOKBACK` for transferred policies.
- `projected_outside_estate_if_implemented` = `death_benefit` (if formalities met).
- `tax_liquidity_support` = `death_benefit * estate_tax_rate` (capped at `death_benefit`).

**Recommendation**

- `primary_action`: `FUND_WITH_CRUMMEY_NOTICES` when exclusion capacity ≥ premium.
- `suitability`: `SUITABLE_WITH_ADMINISTRATION` when gap is zero.
- `risk_flag`: `LOW_IF_FORMALITIES_MET` for new policies with zero premium gap.

### Trust Comparison Tasks (`analysis_type: trust_comparison`)

**Estate Context**

- `taxable_estate` = `estate_value` from the client record.
- `estate_tax_exposure` = `max(0, (taxable_estate - estate_tax_exemption)) * estate_tax_rate`.
- `liquidity_gap_before_planning` = `liquid_assets - estate_tax_exposure`.

**GRAT Projection**

- `term_years` = `grat_term_years` from the trust candidate.
- Use the Section 7520 rate (`grat_annuity_rate`) as the hurdle: compute the annuity as the
  level payment whose present value (discounted at the annuity rate over the term) equals the
  contributed asset value.
- Project the asset forward at `expected_growth_rate`, subtract the annuity each year, for
  `term_years` years. The remainder after the last annuity is `projected_remainder_to_heirs`.
- `estimated_estate_tax_reduction` = `projected_remainder_to_heirs * estate_tax_rate`.
- `mortality_inclusion_risk` = `TERM_SURVIVAL_REQUIRED`.

**CRAT Projection**

- `term_years` = `crat_term_years`.
- Annual payout = `asset_value * crat_payout_rate`.
- Project the asset forward at `expected_growth_rate`, subtract the payout each year, for
  `term_years` years. The remainder is `projected_charitable_remainder`.
- `estimated_income_tax_deduction` = `projected_charitable_remainder * charitable_deduction_rate`.
- `family_transfer_fit`: `MODERATE` unless the family-transfer priority strongly favors one tool.

**Recommendation**

- `preferred_strategy` and `rationale_code`: prefer `GRAT` / `CHILDREN_TRANSFER_PRIORITY`
  when `family_transfer_priority = "high"` and `philanthropic_intent ≠ "high"`.
- `alternate_role`: the non-preferred tool's complementary role.

### Estate Liquidity Action Plan Tasks (`analysis_type: estate_liquidity_action_plan`)

**Estate Context** — same formulas as Trust Comparison above.

**ILIT Section** — same formulas as ILIT Crummey tasks, omitting dates/notices.

**Trust Transfer**

- Compute GRAT and CRAT as in Trust Comparison.
- `preferred_strategy`: `GRAT` when family-transfer priority is high and philanthropic intent is
  low or moderate; `CRAT` when philanthropic intent is high.
- Include `projected_charitable_remainder` from the CRAT calculation even when GRAT is preferred.

**Action Set**

Sort alphabetically. Include only actions that apply:
- `ATTORNEY_DRAFT_REVIEW` — always include (trust documents require attorney).
- `GRAT_FOR_APPRECIATING_SHARES` — include when GRAT is preferred or under consideration.
- `ILIT_CRUMMEY_NOTICE_CYCLE` — include when an ILIT is being implemented.
- `LIFETIME_EXEMPTION_ALLOCATION` — include when estate tax exposure exceeds liquid assets.
- `CRAT_FOR_CHARITABLE_REMAINDER` — include only when philanthropic intent is "high".

**Recommendation**

- `primary_action`: `COMBINE_ILIT_AND_GRAT` when both ILIT and GRAT are part of the plan.
- `sequencing`: `ILIT_FIRST_THEN_GRAT` (ILIT funding is time-sensitive due to contribution dates).
- `risk_flag`: `LOW_IF_FORMALITIES_MET` for new policies with zero premium gap.

### Numerical Conventions (all tasks)

- All USD amounts rounded to **two decimal places** (cents).
- Years and counts are **integers**, never strings.
- ISO dates are `YYYY-MM-DD` strings.
- Boolean fields are JSON `true` / `false`.
- Enum strings must match the template exactly (case, underscores).
- `action_set` arrays must be **sorted alphabetically**.
- Top-level keys must match the required list from the answer template.

### Year / Age Mapping

Use `planning_year` as year zero:
- `current_age = client_age + (calendar_year - planning_year)`.
- `first_rmd_year = planning_year + (rmd_start_age - client_age)`.
- `conversion_years` = `recommended_conversion_years` from the account record.

### Tax Constants

Read annually from `/api/policies/tax`. For 2026 planning:
- `annual_gift_exclusion` = 20,000
- `estate_tax_exemption` = 13,610,000
- `estate_tax_rate` = 0.40
- `charitable_deduction_rate` = 0.35
- `conversion_bracket_targets` varies by filing status
- `max_crat_term_years` = 20

### RMD Factors

Read from `/api/rmd-factors`. Keys are integer ages; values are floating-point divisors.
Always apply the RMD to the *beginning-of-year* balance before growth:
1. RMD = balance / factor
2. balance = balance - RMD
3. balance = balance * (1 + expected_return)
