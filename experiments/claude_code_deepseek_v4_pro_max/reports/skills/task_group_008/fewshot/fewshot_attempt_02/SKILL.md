# Private Wealth Advisory Structured Output Skill

## Environment

- API base URL: `GDPEVO_ENV_BASE_URL=http://34.46.77.124:8008` (set via harness as `API_BASE`; this file overrides any localhost references).
- Use `curl` to query the advisory API. The API serves client records, source documents, account exports, life-insurance records, trust candidates, tax policy constants, and RMD factors.
- Output format: **JSON only**, conforming to `input/payloads/answer_template.json`. No prose outside the JSON object. Return valid JSON with no trailing text.
- Numbers are JSON numbers (not strings). USD amounts are rounded to cents (2 decimal places). Dates are ISO 8601 `YYYY-MM-DD`.

---

## Step 1 — Identify the Engagement Type

Read `input/payloads/answer_template.json` to determine `analysis_type` from the `fields.analysis_type` enum. Four engagement types exist:

| analysis_type | Description |
|---|---|
| `roth_conversion_rmd` | Roth conversion and RMD tax projection |
| `ilit_crummey_implementation` | ILIT funding with Crummey notice cycle |
| `trust_comparison` | GRAT versus CRAT numerical comparison |
| `estate_liquidity_action_plan` | Combined ILIT + trust transfer with action set |

The template's `required_top_level_keys` and `fields` fully define the output schema. Build the output JSON by populating every required key from the template.

---

## Step 2 — Fetch Client Data from the Advisory API

For every engagement, query the API for:

1. **Client profile** — `GET {API_BASE}/clients/{client_id}` — returns demographics, goals, risk tolerance, signed profile data.
2. **Account/custodian records** — `GET {API_BASE}/clients/{client_id}/accounts` — returns IRA/401k balances, Roth balances, account types, custodian-exported values.
3. **Policy/insurance records** (if ILIT or estate liquidity) — `GET {API_BASE}/clients/{client_id}/policies` — death benefit, annual premium, policy ownership.
4. **Trust candidates** (if GRAT/CRAT or estate liquidity) — `GET {API_BASE}/clients/{client_id}/trusts` — GRAT/CRAT parameters, term, funding amount.
5. **Tax constants** — `GET {API_BASE}/constants` — returns estate tax rate, gift tax annual exclusion, RMD start age, income tax brackets, 7520 rate.
6. **CRM notes** — `GET {API_BASE}/clients/{client_id}/crm` — older imported records that may conflict.

Some records conflict because they were imported from different systems at different times. See Source Resolution below.

---

## Step 3 — Resolve Conflicting Sources

When multiple sources return different values for the same field, use this precedence hierarchy:

### Profile / goal / beneficiary / personal-info sources
```
SIGNED_PROFILE  >  ATTORNEY_MEMO  >  CUSTODIAN_EXPORT  >  CRM_NOTE  >  STALE_MARKETING_INTAKE
```

### Account / IRA / 401k / custodian-numeric sources
```
CUSTODIAN_EXPORT  >  SIGNED_PROFILE  >  CRM_NOTE
```

### Asset / trust-funding / basis sources
```
ATTORNEY_MEMO  >  SIGNED_PROFILE  >  CRM_NOTE
```

### Policy / insurance / death-benefit sources
```
SIGNED_PROFILE  >  ATTORNEY_MEMO  >  CUSTODIAN_EXPORT  >  CRM_NOTE
```

**Rule of thumb:** The most recently verified or legally binding source wins. `SIGNED_PROFILE` is the top authority for client-intent fields; `CUSTODIAN_EXPORT` is the top authority for actual account balances; `ATTORNEY_MEMO` is the top authority for trust/asset legal structures. `STALE_MARKETING_INTAKE` is never selected as a controlling source in any of the training examples.

---

## Step 4 — Tax Policy Constants (Hardcoded Rules)

These constants are drawn from the advisory environment's tax policy and are consistent across all training examples:

| Constant | Value | Usage |
|---|---|---|
| Federal estate tax rate | 40% (0.40) | `estate_tax_exposure`, `tax_liquidity_support`, `estimated_estate_tax_reduction` |
| Federal income tax rate (top bracket) | 32% (0.32) | `total_conversion_tax` on Roth conversions (unless client marginal rate differs) |
| Gift tax annual exclusion (2026) | $20,000 per beneficiary | `annual_exclusion_per_beneficiary`, `annual_exclusion_capacity` |
| RMD starting age | 73 | `first_rmd_year` calculation |
| Growth rate (IRA / 401k) | ~5-6% annually (compounded) | Forward balance projections |
| 7520 rate (GRAT/CRAT) | Varies by month; query API | GRAT remainder interest, CRAT deduction |

**Verify at runtime:** Always fetch `/constants` from the API; do not hardcode values that the API might override. The table above captures the consensus values observed in training examples.

---

## Step 5 — Engagement-Specific Calculation Rules

### A. roth_conversion_rmd

**RMD first year:**
- If `current_age >= 73`: `first_rmd_year = current_year`
- If `current_age < 73`: `first_rmd_year = current_year + (73 - current_age)`

**Conversion plan:**
- `first_conversion_year` = current planning year (typically 2026 in training).
- `conversion_years` = number of years from `first_conversion_year` up to (but not including) `first_rmd_year`. In the staged-conversion pattern, conversions happen every year until RMDs begin.
- `conversion_years_positive` = `conversion_years` (always equals `conversion_years`; 0 if no conversion).
- `annual_conversion_amount` = the fixed dollar amount converted each year, chosen to fill the current tax bracket without pushing into the next bracket. This is the IRA balance eligible for conversion divided by `conversion_years`, or bracket-headroom-limited.
- `total_converted` = `annual_conversion_amount` × `conversion_years`.
- `total_conversion_tax` = `total_converted` × income_tax_rate (32%).

**RMD projection:**
- `horizon_year` = planning horizon from request memo.
- `baseline_rmd_tax_through_horizon` = total income tax paid on RMDs from `first_rmd_year` through `horizon_year` assuming NO conversions.
- `conversion_rmd_tax_through_horizon` = total income tax paid on RMDs from `first_rmd_year` through `horizon_year` assuming the conversion plan is executed.
- `rmd_tax_savings_through_horizon` = `baseline_rmd_tax_through_horizon` - `conversion_rmd_tax_through_horizon`.

**Legacy projection:**
- `projected_roth_balance_horizon` = Roth balance at `horizon_year` after all conversions and growth.
- `projected_traditional_balance_horizon` = Traditional IRA balance at `horizon_year` after conversions and RMD withdrawals.
- `heir_tax_profile`: `MOSTLY_TAX_FREE` if Roth dominates, `MOSTLY_TAXABLE` if traditional dominates, `MIXED_TAXABLE_AND_TAX_FREE` otherwise.

**Recommendation logic:**
- `STAGED_ROTH_CONVERSION` + `SUITABLE` when conversions reduce lifetime tax and there is bracket headroom.
- `DEFER` when near RMD age with insufficient conversion runway.
- `NO_CONVERSION` when conversion tax exceeds RMD tax savings.
- Risk flags: `TAX_BRACKET_MANAGEMENT` (default), `LIQUIDITY_CONSTRAINT` (insufficient non-retirement cash for conversion tax), `RMD_NEAR_TERM` (first RMD within 2 years).

---

### B. ilit_crummey_implementation

**Gift plan:**
- `planning_year` = current year.
- `annual_exclusion_per_beneficiary` = current gift tax annual exclusion ($20,000 in 2026; verify via API).
- `beneficiary_count` = number of ILIT beneficiaries (equals number of Crummey withdrawal power holders).
- `annual_exclusion_capacity` = `annual_exclusion_per_beneficiary` × `beneficiary_count`.
- `annual_premium` = total annual premium from the controlling policy source.
- `premium_gap` = max(0, `annual_premium` - `annual_exclusion_capacity`). Zero means premiums are fully covered by annual exclusions.

**Administration:**
- `notices_required` = `beneficiary_count` (one Crummey notice per beneficiary).
- `contribution_date` = date contributions are made to the ILIT (from API or advisor memo).
- `notice_due_date` = `contribution_date` + 7 calendar days.
- `withdrawal_window_end` = `notice_due_date` + 30 calendar days (or `contribution_date` + 37 days).
- `earliest_premium_payment_date` = `withdrawal_window_end` + 1 day.
- `dedicated_bank_account_required` = `true` (always required for ILIT Crummey administration to avoid commingling).

**Estate result:**
- `death_benefit` = face amount from controlling policy source.
- `estate_inclusion_risk` = same value as `recommendation.risk_flag`.
- `projected_outside_estate_if_implemented` = `death_benefit` when ILIT is properly structured (full exclusion); may be less than `death_benefit` if there is a lookback period or inclusion risk.
- `tax_liquidity_support` = `death_benefit` × 0.40 (estate tax that the death benefit can cover).

**Recommendation logic:**
- `FUND_WITH_CRUMMEY_NOTICES` + `SUITABLE_WITH_ADMINISTRATION` when `premium_gap` = 0 and no lookback issue.
- `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` when `premium_gap` > 0.
- `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` when policy was recently transferred (within 3-year lookback).
- `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` when both lookback and shortfall apply.
- Risk flags: `LOW_IF_FORMALITIES_MET` (default), `EXCLUSION_SHORTFALL` (premium_gap > 0), `THREE_YEAR_LOOKBACK`, `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`.

---

### C. trust_comparison

**Estate context:**
- `taxable_estate` = gross estate - exemption used (from client records).
- `estate_tax_exposure` = `taxable_estate` × 0.40.
- `liquid_assets_available` = cash + marketable securities from account records.
- `liquidity_gap_before_planning` = max(0, `estate_tax_exposure` - `liquid_assets_available`).

**GRAT:**
- `term_years` = GRAT term from trust candidate (typically 2–5 years; shorter term favors remainder passing to heirs).
- `projected_remainder_to_heirs` = funded amount grown at hurdle rate (7520 rate) over `term_years`, minus annuity payments back to grantor; remainder passes to heirs.
- `estimated_estate_tax_reduction` = `projected_remainder_to_heirs` × 0.40 (assets removed from taxable estate).
- `mortality_inclusion_risk` = `TERM_SURVIVAL_REQUIRED` (grantor must survive the GRAT term for assets to pass outside the estate).

**CRAT:**
- `term_years` = CRAT term (typically life or 20 years).
- `projected_charitable_remainder` = funded amount grown at the CRAT rate over `term_years`, minus annuity payments; remainder to charity.
- `estimated_income_tax_deduction` = present value of the charitable remainder interest (discounted at 7520 rate).
- `family_transfer_fit`: `LOW` (CRAT primarily benefits charity, not heirs), `MODERATE`, or `HIGH`.

**Recommendation logic:**
- `preferred_strategy`: `GRAT` when `rationale_code` = `CHILDREN_TRANSFER_PRIORITY`; `CRAT` when `PHILANTHROPIC_PRIORITY`.
- `alternate_role`: `SECONDARY_CHARITABLE_TOOL` when GRAT is primary; `SECONDARY_FAMILY_TRANSFER_TOOL` when CRAT is primary.

---

### D. estate_liquidity_action_plan

This engagement combines ILIT analysis with a trust transfer comparison plus an action set.

**Estate context:** Same calculation rules as trust_comparison above.

**ILIT section:** Same calculation rules as ilit_crummey_implementation above, but only the subset fields listed in the template (`annual_exclusion_capacity`, `premium_gap`, `estate_inclusion_risk`, `projected_outside_estate_if_implemented`).

**Trust transfer section:** Same as trust_comparison above but includes BOTH `projected_remainder_to_heirs`/`estimated_estate_tax_reduction` (GRAT fields) AND `projected_charitable_remainder` (CRAT field), since both trusts are modeled for the action plan.

**Action set:** Select from these five actions, then **sort alphabetically**:
- `ATTORNEY_DRAFT_REVIEW`
- `CRAT_FOR_CHARITABLE_REMAINDER`
- `GRAT_FOR_APPRECIATING_SHARES`
- `ILIT_CRUMMEY_NOTICE_CYCLE`
- `LIFETIME_EXEMPTION_ALLOCATION`

**Recommendation logic:**
- `COMBINE_ILIT_AND_GRAT` when both ILIT is suitable and GRAT transfers significant value to heirs.
- `CRAT_WITH_LIQUIDITY_REVIEW` when charitable intent exists and liquidity gap is large.
- `ILIT_WITH_EXEMPTION_REVIEW` when ILIT is suitable but trust transfer is not.
- Sequencing: `ILIT_FIRST_THEN_GRAT` (standard ordering), `TRUST_DECISION_FIRST`, `ILIT_FIRST_THEN_ATTORNEY_REVIEW`.
- Risk flags: same set as ilit_crummey_implementation.

---

## Step 6 — Output Construction Checklist

1. Set `task_id` to the task identifier provided by the harness (e.g., `train_001`, `test_001`).
2. Set `client_id` and `analysis_type` from the request memo and template.
3. Populate every `required_top_level_key` from the template — missing keys will fail validation.
4. All enum values must match the template exactly (case-sensitive).
5. All USD amounts are JSON numbers rounded to 2 decimal places.
6. All years/integers are JSON integers (no decimal point).
7. All dates are ISO strings `YYYY-MM-DD`.
8. `action_set` lists must be sorted alphabetically.
9. `source_resolution` fields must use the exact enum values from the template.
10. Remove any computed/scratch fields not in the template (some templates include optional context fields like `planning_year`, `exemption_used`, `liquid_assets_available` in `estate_context`; include these if present in the template even if not in `required_top_level_keys`, as they appear in gold answers).

---

## Common Pitfalls

1. **Source conflicts:** Do not average conflicting values. Pick one controlling source per domain using the hierarchy above and use only that source's values.
2. **RMD age:** Use 73, not 72 or 75. Recent legislation (SECURE 2.0) moved the age; the advisory environment uses 73.
3. **Tax rate double-application:** `total_conversion_tax` is the income tax on the conversion itself, NOT the estate tax. Estate tax (40%) only applies to estate/legacy fields.
4. **Growth compounding:** Project balances forward with annual compounding. Do not use simple interest.
5. **conversion_years_positive:** Must equal `conversion_years`. If no conversion, both are 0; otherwise both are the positive integer count.
6. **premium_gap floor:** Never negative. Use `max(0, annual_premium - annual_exclusion_capacity)`.
7. **liquidity_gap_before_planning floor:** Never negative. Use `max(0, estate_tax_exposure - liquid_assets_available)`.
8. **Crummey notice timing:** `withdrawal_window_end` is 30 days after `notice_due_date`, not 30 days after `contribution_date`. The 30-day Crummey window starts when notice is given.
9. **action_set ordering:** Alphabetical sort is scored. `"GRAT_FOR_APPRECIATING_SHARES"` comes before `"ILIT_CRUMMEY_NOTICE_CYCLE"`.
10. **Never select `STALE_MARKETING_INTAKE`** as a controlling source. It represents outdated lead-gen data and should never be the final authority for any resolved field.
