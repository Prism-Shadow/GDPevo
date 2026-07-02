# SKILL: Private Wealth Advisory Structured Output

Personal financial advisory planning over a remote advisory API. Each task asks for a
strict JSON object (per an answer template) summarizing one of four analysis types:
roth_conversion_rmd, ilit_crummey_implementation, trust_comparison, or
estate_liquidity_action_plan. The advisory environment holds CONFLICTING source records
imported from different systems; the core skill is resolving which source controls each
fact, then computing precisely (USD to cents, ISO dates, sorted lists, exact formulas).

## 1. Remote API Workflow (endpoint order)

Base URL is supplied by the harness (`API_BASE`). All endpoints are GET; data is JSON.

1. `GET /api/health` -> confirm `{"ok": true}`.
2. `GET /api/policies/tax` -> planning constants (read once, cache):
   - `annual_gift_exclusion` (by year; 2026 = 20000)
   - `estate_tax_exemption` (by year; 2026 = 13610000)
   - `estate_tax_rate` (0.4)
   - `conversion_bracket_targets` by filing status (MFJ=394600, SINGLE=197300, HOH=263500)
   - `max_crat_term_years` (20)
   - `charitable_deduction_rate` (0.35)
3. `GET /api/rmd-factors` -> age -> RMD divisor table (keys are ages 73..99 as strings).
4. `GET /api/clients/<client_id>` -> base record (household, age, marital/filing status,
   planning_year, estate_value, liquid_assets).
5. `GET /api/source-documents?client_id=<id>` -> the conflicting sources (CRM_NOTE,
   ATTORNEY_MEMO, SIGNED_PROFILE, sometimes STALE_MARKETING_INTAKE), each with an
   `effective_date` and a `facts` map. ALWAYS fetch this before deciding any contested fact.
6. `GET /api/retirement-accounts?client_id=<id>` -> traditional/Roth balances, expected
   return, rmd_start_age, recommended_conversion_years (source_type = CUSTODIAN_EXPORT).
7. `GET /api/life-insurance?client_id=<id>` -> ILIT policy: death_benefit, annual_premium,
   planned_contribution_date, is_existing_policy_transfer, proposed_owner.
8. `GET /api/trust-candidates?client_id=<id>` -> asset_value, expected_growth_rate,
   grat_term_years, grat_annuity_rate, crat_term_years, crat_payout_rate.

Fetch 2+3 once; fetch 4-8 per client. The local `request_memo.md` gives the engagement
type and the planning HORIZON YEAR (when relevant) — read it first.

## 2. Source-Resolution Precedence (the central skill)

Source records disagree after an older CRM import. Resolve by this precedence (later,
signed, system-of-record sources win over stale/marketing ones):

- **SIGNED_PROFILE controls client-stated facts** (it is the most recent, client-signed
  record). Use it for: `annual_non_ira_income`, `marginal_tax_rate`, `beneficiary_count`,
  `age`, `planning_year`, `filing_status`, `marital_status`, `liquid_assets`,
  `estate_value`, AND client goals (`family_transfer_priority`, `philanthropic_intent`),
  AND life-insurance policy determinations. So `controlling_profile_source`,
  `controlling_beneficiary_source`, `controlling_policy_source`, and
  `controlling_goal_source` are all `SIGNED_PROFILE`.
- **CUSTODIAN_EXPORT controls account balances** — traditional_balance, roth_balance,
  expected_return, rmd_start_age, recommended_conversion_years.
  `controlling_account_source` = `CUSTODIAN_EXPORT`.
- **ATTORNEY_MEMO controls trust / estate-asset facts** — the trust funding asset_value
  and estate-asset determinations. `controlling_asset_source` = `ATTORNEY_MEMO`.
- **CRM_NOTE and STALE_MARKETING_INTAKE never control** — they are the stale import;
  ignore their numbers (e.g., older income, older beneficiary_count) when a signed/
  custodian/attorney record exists for the same fact.

Default the `source_resolution` output fields accordingly. When SIGNED_PROFILE and
ATTORNEY_MEMO agree on a goal, the controlling source is still SIGNED_PROFILE (client
goals), NOT the attorney memo. Policy source is SIGNED_PROFILE, not ATTORNEY_MEMO.

## 3. Analysis Type: roth_conversion_rmd

Source values: income/marginal_rate/age/beneficiary from SIGNED_PROFILE; balances and
recommended_conversion_years from CUSTODIAN_EXPORT; horizon_year from the request memo.

Formulas:
- `bracket_room = conversion_bracket_targets[filing_status] - annual_non_ira_income`.
  (Uses SIGNED_PROFILE income; do not subtract RMD or any other income.)
- `annual_conversion_amount = min(bracket_room, traditional_balance / recommended_conversion_years)`.
- `first_conversion_year = planning_year`; `conversion_years = recommended_conversion_years`;
  `conversion_years_positive` = count of years with positive conversion (all of them when
  the balance outlasts the plan — the usual case).
- `total_converted = annual_conversion_amount * conversion_years`.
- `total_conversion_tax = total_converted * marginal_tax_rate`.
- `first_rmd_year = planning_year + (rmd_start_age - age)`.
  (rmd_start_age is 73 in this environment.)
- `horizon_year` = the year stated in the request memo.

Year-by-year projection (planning_year .. horizon_year INCLUSIVE). Maintain a traditional
balance (start = traditional_balance) and a Roth balance (start = roth_balance, which may
already be > 0). For each year Y in that range, age = age0 + (Y - planning_year):
  1. If Y is a conversion year (planning_year .. planning_year+conversion_years-1):
     `traditional -= annual_conversion_amount; roth += annual_conversion_amount`.
     (Conversions can overlap RMD years — apply the conversion first.)
  2. If age >= rmd_start_age and Y >= first_rmd_year and age is in the factor table:
     `rmd = traditional / rmd_factor[age]; rmd_tax += rmd * marginal_tax_rate;
     traditional -= rmd`.
  3. Grow: `traditional *= (1 + expected_return); roth *= (1 + expected_return)`.
     Apply growth AFTER the year's transactions, in every year including the horizon year.
- `baseline_rmd_tax_through_horizon` = rmd_tax from the simulation with NO conversions
  (balance just grows, RMDs from 73..horizon).
- `conversion_rmd_tax_through_horizon` = rmd_tax from the simulation WITH conversions.
- `rmd_tax_savings_through_horizon = baseline - conversion`.
- `projected_roth_balance_horizon` = Roth balance at horizon (conversion case; includes any
  pre-existing roth_balance grown plus conversions grown).
- `projected_traditional_balance_horizon` = traditional balance at horizon (conversion case).
- `heir_tax_profile`: compare the two horizon balances. If Roth is clearly larger than
  Traditional (roughly >1.5x) -> `MOSTLY_TAX_FREE`. If Traditional is clearly larger than
  Roth -> `MOSTLY_TAXABLE`. If they are close/balanced (e.g., ~55/45 split) ->
  `MIXED_TAXABLE_AND_TAX_FREE`.

Recommendation:
- `primary_action` = `STAGED_ROTH_CONVERSION` when a conversion plan is being run.
- `suitability` = `SUITABLE` whenever conversions are viable (bracket room > 0 and balance
  > 0) — including near-RMD cases. Keep SUITABLE; do NOT downgrade to BORDERLINE just
  because RMDs are close.
- `risk_flag`: `TAX_BRACKET_MANAGEMENT` when RMDs are far off (multiple years before
  rmd_start_age); `RMD_NEAR_TERM` when the client is at/within ~1 year of rmd_start_age.
  The near-RMD signal lives in `risk_flag`, NOT in `suitability`.

Round every USD field to cents. Use JSON numbers, never strings.

## 4. Analysis Type: ilit_crummey_implementation

Source values: beneficiary_count from SIGNED_PROFILE; annual_premium, death_benefit,
planned_contribution_date, is_existing_policy_transfer from life-insurance; gift
exclusion from tax policy for the planning year.

Formulas:
- `planning_year` = SIGNED_PROFILE planning_year.
- `annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year]`.
- `beneficiary_count` = SIGNED_PROFILE value.
- `annual_exclusion_capacity = annual_exclusion_per_beneficiary * beneficiary_count`.
- `annual_premium` = policy annual_premium.
- `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`.
  CLAMP to 0 — when the premium is below exclusion capacity there is no shortfall, so the
  gap is 0 (do NOT report a raw negative number).
- `notices_required = beneficiary_count` (one Crummey notice per beneficiary).
- Administration dates — all offsets from `planned_contribution_date` (the contribution_date):
  - `contribution_date` = planned_contribution_date (ISO).
  - `notice_due_date` = contribution_date + 7 days.
  - `withdrawal_window_end` = contribution_date + 30 days.
  - `earliest_premium_payment_date` = contribution_date + 1 day.
  Compute with real calendar arithmetic; the +7/+30/+1 are all measured from the
  contribution_date (do NOT chain them).
- `dedicated_bank_account_required = true`.

estate_result:
- `death_benefit` = policy death_benefit.
- `estate_inclusion_risk`: `LOW_IF_FORMALITIES_MET` if the policy is new
  (is_existing_policy_transfer = false) AND premium <= capacity; else `EXCLUSION_SHORTFALL`
  if premium > capacity; `THREE_YEAR_LOOKBACK` if it is an existing-policy transfer;
  `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` if both.
- `projected_outside_estate_if_implemented = death_benefit` (the ILIT death benefit passes
  outside the gross estate when formalities are met).
- `tax_liquidity_support = death_benefit` (the liquidity the ILIT provides). Do NOT replace
  this with the computed estate-tax liability.

Recommendation:
- `primary_action`: `FUND_WITH_CRUMMEY_NOTICES` when premium <= capacity and new policy;
  `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` when premium > capacity; lookback variants when
  is_existing_policy_transfer.
- `suitability` = `SUITABLE_WITH_ADMINISTRATION`.
- `risk_flag` = `LOW_IF_FORMALITIES_MET` for the clean new-policy case.

source_resolution: `controlling_beneficiary_source = SIGNED_PROFILE`,
`controlling_policy_source = SIGNED_PROFILE`.

## 5. Analysis Type: trust_comparison (GRAT vs CRAT)

Source values: asset_value, growth rate, GRAT/CRAT terms and rates from trust-candidates;
family_transfer_priority / philanthropic_intent (goals) from SIGNED_PROFILE; estate_value
and liquid_assets from SIGNED_PROFILE (matches attorney memo); death_benefit from
life-insurance.

estate_context (this model applies wherever estate_context appears):
- `taxable_estate = estate_value` (the GROSS estate_value; do NOT subtract the exemption here).
- `estate_tax_exposure = (estate_value - estate_tax_exemption[planning_year]) * estate_tax_rate`.
  (Exemption is applied in THIS step.)
- `liquidity_gap_before_planning = estate_tax_exposure - liquid_assets - death_benefit`.
  INCLUDE the life-insurance death benefit as available liquidity, and report the RAW
  result (it may be negative — do not clamp to 0).

GRAT:
- `term_years` = grat_term_years.
- `projected_remainder_to_heirs = asset_value * (1 + expected_growth_rate)^grat_term_years
  - asset_value * grat_annuity_rate * grat_term_years`.
  Use this SIMPLE formula (projected growth minus nominal flat payouts). Do NOT use a
  year-by-year corpus-reducing annuity model — that over-withdraws and loses score.
- `estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate`.
- `mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED`.

CRAT:
- `term_years` = crat_term_years (clamp to max_crat_term_years if needed; here it is 20).
- `projected_charitable_remainder = asset_value * (1 + expected_growth_rate)^crat_term_years
  - asset_value * crat_payout_rate * crat_term_years` (same simple formula).
- `estimated_income_tax_deduction = asset_value * charitable_deduction_rate`.
- `family_transfer_fit = LOW` (a CRAT sends the remainder to charity; principal does not
  transfer to family).

Recommendation:
- `preferred_strategy`: `GRAT` when family_transfer_priority is high (family transfer wins);
  `CRAT` when philanthropic_intent is high.
- `rationale_code`: `CHILDREN_TRANSFER_PRIORITY` (GRAT) or `PHILANTHROPIC_PRIORITY` (CRAT).
- `alternate_role`: the non-preferred strategy's role —
  `SECONDARY_CHARITABLE_TOOL` when GRAT is preferred (CRAT serves as secondary charitable);
  `SECONDARY_FAMILY_TRANSFER_TOOL` when CRAT is preferred.

source_resolution: `controlling_goal_source = SIGNED_PROFILE`,
`controlling_asset_source = ATTORNEY_MEMO`.

## 6. Analysis Type: estate_liquidity_action_plan

Combines estate_context, an ILIT block, a trust_transfer block, and an action_set.

- estate_context: same model as section 5 (taxable_estate = gross; estate_tax_exposure =
  (gross - exemption)*rate; liquidity_gap = estate_tax_exposure - liquid - death_benefit, raw).
- ilit: `annual_exclusion_capacity`, `premium_gap = max(0, premium - capacity)`,
  `estate_inclusion_risk` (as in section 4), `projected_outside_estate_if_implemented = death_benefit`.
- trust_transfer: `preferred_strategy` (GRAT if family_transfer_priority=high), with the
  SIMPLE-formula `projected_remainder_to_heirs` and `projected_charitable_remainder`
  (CRAT), and `estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate`.
- `action_set`: a JSON array of action enums, SORTED ALPHABETICALLY. Available enums:
  `ATTORNEY_DRAFT_REVIEW`, `CRAT_FOR_CHARITABLE_REMAINDER`, `GRAT_FOR_APPRECIATING_SHARES`,
  `ILIT_CRUMMEY_NOTICE_CYCLE`, `LIFETIME_EXEMPTION_ALLOCATION`.
  For a `COMBINE_ILIT_AND_GRAT` recommendation (family transfer priority high, ILIT
  premium within exclusion capacity), the set is exactly:
  `["ATTORNEY_DRAFT_REVIEW", "GRAT_FOR_APPRECIATING_SHARES", "ILIT_CRUMMEY_NOTICE_CYCLE"]`.
  Do NOT add `LIFETIME_EXEMPTION_ALLOCATION` when the ILIT premium is already covered by
  annual exclusion (no shortfall). Do NOT add `CRAT_FOR_CHARITABLE_REMAINDER` when the
  chosen trust strategy is GRAT (philanthropic intent is low).
- Recommendation: `primary_action = COMBINE_ILIT_AND_GRAT`;
  `sequencing = ILIT_FIRST_THEN_GRAT`; `risk_flag = LOW_IF_FORMALITIES_MET`
  (clean new-policy ILIT, premium within capacity).
- source_resolution: `controlling_goal_source = SIGNED_PROFILE`,
  `controlling_policy_source = SIGNED_PROFILE`.

## 7. Precision and formatting rules (apply to every analysis type)

- Every USD field is a JSON number rounded to CENTS (2 decimals). No string numbers.
- Dates are ISO `YYYY-MM-DD` strings; compute with real calendar-day arithmetic.
- `action_set` must be sorted alphabetically (lexicographic).
- Enum values must match the answer template exactly (case and underscores).
- `task_id` mirrors the task identifier; `client_id` is the stable client id; `analysis_type`
  is the per-task enum.
- top-level required keys must all be present.

## 8. Common mistakes to avoid

- Reporting `premium_gap` as a raw negative when premium < capacity: clamp to 0.
- Setting `tax_liquidity_support` to the estate-tax liability: it is the death_benefit.
- Using a year-by-year corpus-reducing annuity model for GRAT/CRAT remainders: use the
  simple `projected - nominal_payouts` formula.
- Setting `earliest_premium_payment_date` to `withdrawal_window_end + 1`: it is
  `contribution_date + 1` (all Crummey offsets +7/+30/+1 are from the contribution_date).
- Subtracting the estate-tax exemption from `taxable_estate`: `taxable_estate` is the gross
  estate_value; the exemption is applied only in `estate_tax_exposure`.
- Forgetting the life-insurance death_benefit in `liquidity_gap_before_planning`, or
  clamping a negative gap to 0: include the death benefit and report the raw value.
- Adding `LIFETIME_EXEMPTION_ALLOCATION` to `action_set` when the ILIT premium is within
  annual exclusion capacity.
- Downgrading `suitability` to `BORDERLINE` for near-RMD conversions: keep `SUITABLE` and
  signal the near-term RMD via `risk_flag = RMD_NEAR_TERM`.
- Using `ATTORNEY_MEMO` for policy or goal sources: policy and goals are controlled by
  `SIGNED_PROFILE`. `ATTORNEY_MEMO` controls trust/estate ASSET facts only
  (`controlling_asset_source`).
- Trusting stale CRM/marketing numbers (income, beneficiary_count, goals) over the
  signed/custodian/attorney records.

## 9. Numbered SOP per task

1. Read the local `request_memo.md` and `prompt.txt` to get the client id, engagement
   (analysis_type), and planning horizon_year.
2. Read `answer_template.json` to learn the exact required keys and enum values.
3. Fetch tax policy and RMD factors (cache).
4. Fetch client base record, source-documents, retirement-accounts, life-insurance,
   trust-candidates for the client.
5. Resolve every contested fact by the section-2 precedence; set the `source_resolution`
   fields.
6. Run the formulas for the analysis_type (sections 3-6). Compute with calendar-day
   arithmetic for dates and full floating-point for money, then round to cents.
7. Assemble the JSON object with all required top-level keys and enums matching the template.
8. Output ONLY the final JSON object — no prose, no trailing text.
