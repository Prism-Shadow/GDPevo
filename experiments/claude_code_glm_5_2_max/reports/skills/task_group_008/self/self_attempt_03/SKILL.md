# Private Wealth Advisory Structured Output Skill

SOP for producing the JSON planning object for an unseen advisory client.
Base API URL is in the staged `environment_access.md` (hereafter `API_BASE`).
All amounts are USD rounded to cents (2 decimals). All dates are ISO `YYYY-MM-DD`.
Return ONLY the JSON object; no prose.

## 0. Determine analysis type from the engagement text
Map the memo "Engagement:" line (or prompt title) to `analysis_type`:
- contains "Roth conversion" / "RMD" / "near-RMD Roth" -> `roth_conversion_rmd`
- contains "ILIT" / "Crummey" -> `ilit_crummey_implementation`
- contains "GRAT" and "CRAT" / "GRAT versus CRAT" -> `trust_comparison`
- contains "estate liquidity action plan" -> `estate_liquidity_action_plan`
Set `task_id` = `"test_NNN"` where NNN is the zero-padded task folder number.
Set `client_id` = the `CLT-XXXX` from the memo.

## 1. Remote API workflow (endpoint order)
1. `GET {API_BASE}/api/health` — confirm `{"ok": true}`.
2. `GET {API_BASE}/api/policies/tax` — cache the planning constants (gift exclusion by year, estate exemption by year, estate_tax_rate, conversion_bracket_targets by filing status, max_crat_term_years, charitable_deduction_rate).
3. `GET {API_BASE}/api/rmd-factors` — cache the age->divisor map (keys 73..99).
4. `GET {API_BASE}/api/clients/{client_id}` — base record (age, filing_status, planning_year, estate_value, liquid_assets).
5. `GET {API_BASE}/api/source-documents?client_id={client_id}` — the CONFLICTING sources (CRM_NOTE, ATTORNEY_MEMO, SIGNED_PROFILE, possibly CUSTODIAN_EXPORT / STALE_MARKETING_INTAKE). Each carries `source_type`, `effective_date`, `facts{}`.
6. Optionally fetch the data endpoints the analysis needs:
   - roth: `GET /api/retirement-accounts?client_id=`
   - ilit / estate-liquidity: `GET /api/life-insurance?client_id=`
   - trust-comparison / estate-liquidity: `GET /api/trust-candidates?client_id=`
7. Read the local `request_memo.md` for the planning horizon year and engagement framing.
8. Read `answer_template.json` for the required keys / enums for THIS task.

## 2. Source-resolution precedence (infer the controlling source)
Each source has an `effective_date` and `source_type`. Resolve every fact from the
conflicting sources using this precedence (highest first):

1. **SIGNED_PROFILE** — most recent, client-signed. Controls PROFILE facts:
   `annual_non_ira_income`, `marginal_tax_rate`, `beneficiary_count`, `age`,
   `filing_status`, `marital_status`, `planning_year`, `liquid_assets`,
   `estate_value`, and GOAL facts (`philanthropic_intent`, `family_transfer_priority`).
2. **ATTORNEY_MEMO** — controls ASSET identification for trust transfers (which
   appreciating asset funds the GRAT/CRAT). Also confirms `estate_value`.
3. **CUSTODIAN_EXPORT** — controls ACCOUNT balances (traditional_balance,
   roth_balance, expected_return on retirement accounts). Always wins for
   account balances even if a profile states a different number.
4. **CRM_NOTE** — older import; superseded by any of the above.
5. **STALE_MARKETING_INTAKE** — lowest; never controls any scored fact.

Resulting `source_resolution` output fields by analysis type:
- roth_conversion_rmd: `controlling_profile_source` = SIGNED_PROFILE;
  `controlling_account_source` = CUSTODIAN_EXPORT.
- ilit_crummey_implementation: `controlling_beneficiary_source` = SIGNED_PROFILE;
  `controlling_policy_source` = SIGNED_PROFILE (the signed plan documents the policy).
- trust_comparison: `controlling_goal_source` = SIGNED_PROFILE;
  `controlling_asset_source` = ATTORNEY_MEMO.
- estate_liquidity_action_plan: `controlling_goal_source` = SIGNED_PROFILE;
  `controlling_policy_source` = SIGNED_PROFILE.

When SIGNED_PROFILE and ATTORNEY_MEMO agree on a goal fact, emit SIGNED_PROFILE.
Only emit a different enum when the signed profile is genuinely absent for that
fact category.

## 3. Reading the planning horizon from the memo
- For `roth_conversion_rmd`: the memo states `Planning horizon year: YYYY`.
  Use that year for `rmd_projection.horizon_year` and project balances to that year.
- For the other three analysis types there is NO horizon field; the trust term is
  read from `trust-candidates` (grat_term_years / crat_term_years) and the ILIT
  dates from `life-insurance.planned_contribution_date`.

## 4. Type A — `roth_conversion_rmd` (tasks 1, 5 template)

Fetch retirement-accounts; you get `traditional_balance`, `roth_balance`,
`expected_return`, `rmd_start_age` (=73), `recommended_conversion_years`.
From SIGNED_PROFILE read `annual_non_ira_income`, `marginal_tax_rate`,
`filing_status`, `age`, `planning_year`. From tax policy read
`conversion_bracket_targets[filing_status]`.

### 4a. conversion_plan
- `first_conversion_year` = `planning_year`.
- `conversion_years` = `recommended_conversion_years`.
- `first_rmd_year` = `planning_year + (rmd_start_age - age)` (year owner turns 73).
- `annual_conversion_amount` = `conversion_bracket_targets[filing_status]` MINUS
  `annual_non_ira_income`. (Fill the bracket: non-IRA income fills first, conversion
  fills the rest to the bracket ceiling.) Round to cents.
- `total_converted` = `annual_conversion_amount * conversion_years` (cents).
- `total_conversion_tax` = `total_converted * marginal_tax_rate` (cents).
- `conversion_years_positive` = number of conversion years that fall STRICTLY BEFORE
  `first_rmd_year` = `max(0, min(conversion_years, first_rmd_year - first_conversion_year))`.

### 4b. rmd_projection
- `horizon_year` = memo planning-horizon year.
- `first_rmd_year` = as above.

Baseline model (no conversion):
```
B = traditional_balance
for Y in [planning_year .. horizon_year]:
    ageY = age + (Y - planning_year)
    rmd = B / rmd_factors[ageY]          if Y >= first_rmd_year else 0
    tax = rmd * marginal_tax_rate         if Y >= first_rmd_year else 0
    B = (B - rmd) * (1 + expected_return)   # withdraw RMD, then grow remainder
baseline_rmd_tax_through_horizon = sum(tax over Y)
```

Conversion model (with conversion):
```
Bc = traditional_balance
Rc = roth_balance
for Y in [planning_year .. horizon_year]:
    ageY = age + (Y - planning_year)
    rmd = Bc / rmd_factors[ageY]          if Y >= first_rmd_year else 0
    conv = annual_conversion_amount       if Y is a conversion year else 0
    tax = rmd * marginal_tax_rate         if Y >= first_rmd_year else 0
    Bc = (Bc - rmd - conv) * (1 + expected_return)
    Rc = (Rc + conv) * (1 + expected_return)
conversion_rmd_tax_through_horizon = sum(tax over Y)
```
- `rmd_tax_savings_through_horizon` = `baseline_rmd_tax_through_horizon` MINUS
  `conversion_rmd_tax_through_horizon` (positive = savings; cents).

### 4c. legacy_projection
- `projected_traditional_balance_horizon` = `Bc` at horizon (conversion model).
- `projected_roth_balance_horizon` = `Rc` at horizon (conversion model).
- `heir_tax_profile`: ratio = `Rc / (Rc + Bc)`.
  - ratio >= 0.60 -> `MOSTLY_TAX_FREE`
  - ratio <= 0.30 -> `MOSTLY_TAXABLE`
  - else -> `MIXED_TAXABLE_AND_TAX_FREE`

### 4d. recommendation
- If `conversion_years_positive` <= 1 (RMD imminent): `primary_action`=`DEFER`,
  `suitability`=`DEFER`, `risk_flag`=`RMD_NEAR_TERM`.
- Else if `liquid_assets < total_conversion_tax`: `risk_flag`=`LIQUIDITY_CONSTRAINT`,
  `suitability`=`BORDERLINE`, `primary_action`=`DEFER`.
- Else: `primary_action`=`STAGED_ROTH_CONVERSION`, `suitability`=`SUITABLE`,
  `risk_flag`=`TAX_BRACKET_MANAGEMENT`.

## 5. Type B — `ilit_crummey_implementation` (task 2 template)

Fetch life-insurance; you get `death_benefit`, `annual_premium`,
`planned_contribution_date`, `is_existing_policy_transfer`. From SIGNED_PROFILE
read `beneficiary_count`; from the client record read `planning_year`.

### 5a. gift_plan
- `planning_year` = client planning_year (2026 for train data).
- `annual_exclusion_per_beneficiary` = `annual_gift_exclusion[planning_year]`.
- `beneficiary_count` = from SIGNED_PROFILE (resolves CRM conflict).
- `annual_exclusion_capacity` = `beneficiary_count * annual_exclusion_per_beneficiary`.
- `annual_premium` = from life-insurance record.
- `premium_gap` = `max(0, annual_premium - annual_exclusion_capacity)` (cents).

### 5b. administration
- `notices_required` = `beneficiary_count`.
- `contribution_date` = `planned_contribution_date` (ISO).
- `notice_due_date` = `contribution_date` (Crummey notice served on contribution).
- `withdrawal_window_end` = `contribution_date + 30 days` (ISO).
- `earliest_premium_payment_date` = `withdrawal_window_end + 1 day` (trustee pays
  premium only after the 30-day withdrawal right closes).
- `dedicated_bank_account_required` = `true`.

Date arithmetic: add 30 calendar days to the ISO date; `+ 1 day` after.
E.g. 2026-03-10 -> window end 2026-04-09 -> earliest premium 2026-04-10.

### 5c. estate_result
- `death_benefit` = from life-insurance record.
- `estate_inclusion_risk` = same value as `recommendation.risk_flag` (see 5d).
- `projected_outside_estate_if_implemented` = `death_benefit` (ILIT-owned policy
  passes outside the taxable estate when formalities are met).
- `tax_liquidity_support` = `death_benefit` (liquidity the ILIT supplies).

### 5d. recommendation (matrix on two axes)
Axes: `is_existing_policy_transfer` (T/F) and `premium_gap > 0` (T/F).
- F / F: `FUND_WITH_CRUMMEY_NOTICES`, `SUITABLE_WITH_ADMINISTRATION`, `LOW_IF_FORMALITIES_MET`.
- F / T: `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`, `BORDERLINE`, `EXCLUSION_SHORTFALL`.
- T / F: `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`, `BORDERLINE`, `THREE_YEAR_LOOKBACK`.
- T / T: `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`, `NOT_SUITABLE`, `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`.
`estate_result.estate_inclusion_risk` takes the same risk_flag value.

## 6. Type C — `trust_comparison` (task 3 template)

Fetch trust-candidates; you get `asset_value`, `expected_growth_rate`,
`grat_term_years`, `grat_annuity_rate`, `crat_term_years`, `crat_payout_rate`.
From SIGNED_PROFILE read `estate_value`, `liquid_assets`, `filing_status`,
`planning_year`, and goals (`family_transfer_priority`, `philanthropic_intent`).

### 6a. estate_context (shared formula for types C and D)
- `taxable_estate` = `estate_value` from SIGNED_PROFILE.
- `estate_tax_exposure` = `max(0, taxable_estate - estate_tax_exemption[planning_year]) * estate_tax_rate`.
- `liquidity_gap_before_planning` = `max(0, estate_tax_exposure - liquid_assets)`.

### 6b. grat
- `term_years` = `grat_term_years`.
- annuity_payment = `asset_value * grat_annuity_rate` (fixed each year).
- `projected_remainder_to_heirs` =
  `asset_value * (1+growth)^term - annuity_payment * (((1+growth)^term - 1) / growth)` (cents).
  (Grow the asset each year, pay the fixed annuity at year-end; remainder passes to heirs.)
- `estimated_estate_tax_reduction` = `projected_remainder_to_heirs * estate_tax_rate` (cents).
- `mortality_inclusion_risk` = `TERM_SURVIVAL_REQUIRED` (always; grantor must survive the term).

### 6c. crat
- `term_years` = `min(crat_term_years, max_crat_term_years)`.
- annuity_payment = `asset_value * crat_payout_rate` (fixed each year).
- `projected_charitable_remainder` =
  `asset_value * (1+growth)^term - annuity_payment * (((1+growth)^term - 1) / growth)` (cents).
- `estimated_income_tax_deduction` = `asset_value * charitable_deduction_rate` (cents).
- `family_transfer_fit` based on `family_transfer_priority`:
  high -> `LOW`; moderate -> `MODERATE`; low -> `HIGH`.

### 6d. recommendation
- `preferred_strategy`: `GRAT` if `family_transfer_priority == "high"` and
  `philanthropic_intent != "high"`; else `CRAT` if `philanthropic_intent == "high"`;
  else default `GRAT`.
- `rationale_code`: GRAT -> `CHILDREN_TRANSFER_PRIORITY`; CRAT -> `PHILANTHROPIC_PRIORITY`.
- `alternate_role`: GRAT preferred -> `SECONDARY_CHARITABLE_TOOL`;
  CRAT preferred -> `SECONDARY_FAMILY_TRANSFER_TOOL`.

## 7. Type D — `estate_liquidity_action_plan` (task 4 template)

Combines estate_context + ILIT + trust transfer. Fetch life-insurance AND
trust-candidates. Use SIGNED_PROFILE for estate/liquid goals, beneficiary_count.

### 7a. estate_context — same formula as 6a.

### 7b. ilit
- `annual_exclusion_capacity` = `beneficiary_count * annual_gift_exclusion[planning_year]`.
- `premium_gap` = `max(0, annual_premium - annual_exclusion_capacity)`.
- `estate_inclusion_risk` = risk_flag from the 5d matrix.
- `projected_outside_estate_if_implemented` = `death_benefit`.

### 7c. trust_transfer
- `preferred_strategy`: GRAT/CRAT using the same goal rule as 6d.
- `projected_remainder_to_heirs` = GRAT remainder (formula 6b).
- `estimated_estate_tax_reduction` = `projected_remainder_to_heirs * estate_tax_rate`.
- `projected_charitable_remainder` = CRAT remainder (formula 6c, computed regardless
  of which strategy is preferred).

### 7d. recommendation
- `primary_action`:
  - GRAT preferred + ILIT funding (no shortfall) -> `COMBINE_ILIT_AND_GRAT`.
  - CRAT preferred (philanthropic_intent high) -> `CRAT_WITH_LIQUIDITY_REVIEW`.
  - ILIT has `premium_gap > 0` -> `ILIT_WITH_EXEMPTION_REVIEW`.
- `sequencing`:
  - `COMBINE_ILIT_AND_GRAT` -> `ILIT_FIRST_THEN_GRAT`.
  - `CRAT_WITH_LIQUIDITY_REVIEW` -> `TRUST_DECISION_FIRST`.
  - `ILIT_WITH_EXEMPTION_REVIEW` -> `ILIT_FIRST_THEN_ATTORNEY_REVIEW`.
- `risk_flag` = the ILIT risk from the 5d matrix.

### 7e. action_set (sorted alphabetically, subset of the 5 enum values)
Always include: `ATTORNEY_DRAFT_REVIEW`.
Include `GRAT_FOR_APPRECIATING_SHARES` when GRAT is preferred.
Include `CRAT_FOR_CHARITABLE_REMAINDER` when CRAT is preferred.
Include `ILIT_CRUMMEY_NOTICE_CYCLE` when the ILIT is being funded.
Include `LIFETIME_EXEMPTION_ALLOCATION` when `taxable_estate > estate_tax_exemption`
  (always true for these high-net-worth clients) OR when `premium_gap > 0`.
Sort the resulting list alphabetically and output as a JSON array of strings.

## 8. Pitfalls
- Do NOT use CRM_NOTE values for income, beneficiary_count, or goals when a
  SIGNED_PROFILE exists — the CRM is the stale import that disagrees.
- Do NOT use the signed-profile stated balance for retirement accounts; use the
  CUSTODIAN_EXPORT balance from `/api/retirement-accounts`.
- `conversion_years` is the RECOMMENDED count from the account record, NOT a value
  you derive.
- `annual_conversion_amount` is the bracket fill (target MINUS non-IRA income), not
  the balance divided by years.
- `first_rmd_year` = year the owner turns 73 = `planning_year + (73 - age)`.
  Patel (age 72) starts RMD the very next year.
- RMD factor for year Y uses the age IN that year (`age + (Y - planning_year)`),
  not the current age. Guard against age > 99 (no factor) by clamping.
- `premium_gap` is `max(0, ...)`, never negative.
- GRAT/CRAT annuity payment = `asset_value * rate` EACH YEAR (fixed), and the
  remainder formula grows the starting asset and subtracts the FV of the annuity
  stream at `expected_growth_rate`.
- `estimated_income_tax_deduction` for CRAT = `asset_value * charitable_deduction_rate`
  (a flat fraction of the contribution), NOT the future charitable remainder.
- All numeric outputs must be JSON numbers (not strings) rounded to 2 decimals.
- All date outputs must be ISO `YYYY-MM-DD` strings.
- `action_set` MUST be sorted alphabetically.
- Use the `estate_tax_exemption` and `annual_gift_exclusion` for the client's
  `planning_year` (2026 -> exemption 13,610,000; gift exclusion 20,000), not 2025.
- `task_id` must be the literal `test_NNN` for the current test task, not a train id.
