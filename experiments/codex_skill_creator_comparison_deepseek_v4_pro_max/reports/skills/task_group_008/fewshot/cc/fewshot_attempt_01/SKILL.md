---
name: private-wealth-advisory
description: Build structured JSON planning outputs for private wealth advisory engagements using a task-group advisory API. Use this skill whenever the task mentions private wealth, advisory API, estate planning, Roth conversions, RMD projections, ILIT Crummey funding, trust comparisons (GRAT/CRAT), estate liquidity action plans, or structured planning output for client IDs like CLT-XXXX. The skill covers data gathering from a REST API, source conflict resolution, tax-aware projections, and filling template-driven JSON outputs.
---

# Private Wealth Advisory Planning Engine

This skill guides you through assembling structured JSON planning outputs for private
wealth advisory engagements using deterministic computations against a REST API. You will
fetch data, resolve conflicts between competing source documents, run tax-aware financial
projections, and populate a template into a clean JSON answer.

## The task environment

The harness provides the advisory API base URL through an environment variable (commonly
`API_BASE`). If that variable is not set, fall back to `http://task-env:9008`. All
endpoints return JSON arrays or objects with no authentication required.

### Available endpoints

| Endpoint | Returns |
|----------|---------|
| `GET /api/clients` | All client records |
| `GET /api/clients/{client_id}` | Single client record |
| `GET /api/source-documents` | All source documents (CRM notes, attorney memos, signed profiles) |
| `GET /api/retirement-accounts` | All retirement account custodian exports |
| `GET /api/life-insurance` | All life insurance policy records |
| `GET /api/trust-candidates` | All trust candidate records for GRAT/CRAT modeling |
| `GET /api/policies/tax` | Tax policy constants (gift exclusion, estate exemption, rates, bracket targets) |
| `GET /api/rmd-factors` | RMD divisor table keyed by age |

### Client portal

`GET /portal/client/{client_id}` returns an HTML page (informational only). The JSON
endpoints above carry all structured data you need.

## Input files to read first

Every task provides these files relative to the task directory:

- `input/prompt.txt` — the system prompt establishing context
- `input/payloads/request_memo.md` — the advisor request memo with client ID, engagement
  type, and any planning horizon
- `input/payloads/answer_template.json` — the JSON schema your output must satisfy

Read all three before touching the API. The request memo identifies which client to work
on and what analysis type is needed. The answer template tells you the exact top-level
keys, field types, enums, and ordering constraints.

## Step 1: Gather all data for the client

Fetch every relevant endpoint and filter to the target client ID. Use a scripting
language (Python recommended) to issue HTTP requests and process JSON.

```
GET $API_BASE/api/clients/{client_id}
GET $API_BASE/api/source-documents   (filter by client_id)
GET $API_BASE/api/retirement-accounts (filter by client_id)
GET $API_BASE/api/life-insurance     (filter by client_id)
GET $API_BASE/api/trust-candidates    (filter by client_id)
GET $API_BASE/api/policies/tax
GET $API_BASE/api/rmd-factors
```

The `policies/tax` and `rmd-factors` endpoints are global; fetch them once per task.
All endpoints return JSON with `Content-Type: application/json`.

## Step 2: Resolve source conflicts

Clients often have multiple source documents with conflicting facts (CRM import from an
older system, attorney planning notes, and the most recent signed household profile).
Apply these precedence rules:

### Profile facts (income, filing status, beneficiary count, priorities, liquid assets, estate value, marginal tax rate)

1. **SIGNED_PROFILE** — the most recent signed document; always authoritative if present
2. **ATTORNEY_MEMO** — fallback when no signed profile exists
3. **CRM_NOTE** — last resort

In practice, take the document with `source_type == "SIGNED_PROFILE"` and the latest
`effective_date` for all profile-driven facts.

### Account facts (IRA balances, expected return, RMD start age, conversion years)

1. **CUSTODIAN_EXPORT** — the authoritative source for retirement account data
2. **SIGNED_PROFILE** — fallback only if no custodian export exists
3. **CRM_NOTE** — last resort

The `retirement-accounts` endpoint already carries `source_type: "CUSTODIAN_EXPORT"`.
Use it directly.

### Policy facts (death benefit, annual premium, contribution date, existing-policy flag)

Use the `life-insurance` endpoint record for the client. It carries all policy fields
directly.

### Trust asset facts (asset value, growth rate, GRAT/CRAT parameters)

Use the `trust-candidates` endpoint record for the client. It carries all trust modeling
parameters directly.

### Source resolution fields in the output

The output template always includes a `source_resolution` block. Populate its
`controlling_*_source` fields with the enum values corresponding to the source you
actually relied on:

- **controlling_profile_source**: `SIGNED_PROFILE` (when the signed profile is available
  and used for client profile facts)
- **controlling_account_source**: `CUSTODIAN_EXPORT`
- **controlling_beneficiary_source**: `SIGNED_PROFILE`
- **controlling_policy_source**: `SIGNED_PROFILE`
- **controlling_goal_source**: `SIGNED_PROFILE`
- **controlling_asset_source**: `ATTORNEY_MEMO` for trust-asset decisions (the attorney
  memo provides the most specific valuation and funding guidance for trust planning)

## Step 3: Set the common planning constants

From `policies/tax`:
- `annual_gift_exclusion["2026"]` = 20000 (current planning year)
- `estate_tax_exemption["2026"]` = 13610000 (per individual; double for MFJ)
- `estate_tax_rate` = 0.4
- `conversion_bracket_targets[FILING_STATUS]` — the top of the marginal bracket to fill
- `charitable_deduction_rate` = 0.35
- `max_crat_term_years` = 20

From `rmd-factors`: a mapping of age to divisor (e.g., 73 -> 26.5, 74 -> 25.5, ...).
The client's RMD start age comes from the retirement account record.

## Step 4: Run the analysis by type

Match the `analysis_type` from the template against these sections. Work through the
fields in the same order as the answer template's `required_top_level_keys`.

---

### Analysis: roth_conversion_rmd

Relevant for templates where `analysis_type` is `"roth_conversion_rmd"`.

**Recommendation**

- `primary_action`: `"STAGED_ROTH_CONVERSION"` when the client has bracket headroom
  (annual_non_ira_income < bracket_target). Use `"DEFER"` when RMDs have already started
  and headroom is insufficient. Use `"NO_CONVERSION"` only when there is no
  traditional balance at all.
- `suitability`: `"SUITABLE"` when bracket headroom is positive and conversion can begin
  before or early in RMD years. `"BORDERLINE"` when headroom is small (under $10,000).
  `"DEFER"` when RMDs are already underway with zero headroom.
- `risk_flag`: `"TAX_BRACKET_MANAGEMENT"` for clients whose conversion strategy hinges
  on staying within a bracket. `"RMD_NEAR_TERM"` when the client is at or past RMD start
  age and has limited conversion years. `"LIQUIDITY_CONSTRAINT"` when liquid assets may
  not cover the conversion tax comfortably.

**Conversion plan**

Compute the annual conversion amount as the bracket headroom:

```
annual_headroom = conversion_bracket_target - annual_non_ira_income
```

- `first_conversion_year`: the planning year (2026)
- `conversion_years`: `recommended_conversion_years` from the retirement account record
- `conversion_years_positive`: same as `conversion_years` (must be a positive integer)
- `annual_conversion_amount`: the `annual_headroom` above, rounded to cents
- `total_converted`: `annual_conversion_amount * conversion_years`
- `total_conversion_tax`: `total_converted * marginal_tax_rate`

**RMD projection**

Compute two trajectories over the horizon (planning year through horizon_year):
one baseline (no conversions) and one with the staged conversion plan.

The model is:

For each year, in order:
1. (Conversion case only) Subtract `annual_conversion_amount` from traditional balance
   and add same amount to Roth balance. Accumulate conversion tax at marginal rate.
2. If the client's current age >= RMD start age: compute RMD as
   `traditional_balance / rmd_factor[age]`. Accumulate RMD tax at marginal rate.
3. Subtract RMD from traditional balance (if applicable).
4. Grow both traditional and Roth balances by `(1 + expected_return)`.

Important: the RMD divisor is applied to the beginning-of-year balance (after
conversion but before growth). Then the remaining balance grows.

The baseline trajectory omits step 1. The conversion trajectory includes step 1 in each
of the `conversion_years` starting from `first_conversion_year`.

- `horizon_year`: from the request memo
- `first_rmd_year`: `planning_year + (rmd_start_age - client_age)`
- `baseline_rmd_tax_through_horizon`: total RMD tax over all horizon years, baseline
- `conversion_rmd_tax_through_horizon`: total RMD tax over all horizon years, with
  conversion
- `rmd_tax_savings_through_horizon`: `baseline - conversion`

**Legacy projection**

Ending balances from the conversion trajectory at the horizon year:

- `projected_roth_balance_horizon`: Roth balance after final year's growth
- `projected_traditional_balance_horizon`: traditional balance after final year's growth
- `heir_tax_profile`:
  - `"MOSTLY_TAX_FREE"` if projected Roth > 2x projected traditional
  - `"MIXED_TAXABLE_AND_TAX_FREE"` if projected Roth is between 0.5x and 2x projected
    traditional (inclusive)
  - `"MOSTLY_TAXABLE"` if projected Roth < 0.5x projected traditional

---

### Analysis: ilit_crummey_implementation

Relevant for templates where `analysis_type` is `"ilit_crummey_implementation"`.

**Recommendation**

Decide based on the premium gap and whether the policy is an existing-policy transfer:

- `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`
- If `premium_gap == 0` and `is_existing_policy_transfer == false`:
  - `primary_action`: `"FUND_WITH_CRUMMEY_NOTICES"`
  - `suitability`: `"SUITABLE_WITH_ADMINISTRATION"`
  - `risk_flag`: `"LOW_IF_FORMALITIES_MET"`
- If `premium_gap > 0` and `is_existing_policy_transfer == false`:
  - `primary_action`: `"USE_LIFETIME_EXEMPTION_FOR_SHORTFALL"`
  - `suitability`: `"BORDERLINE"`
  - `risk_flag`: `"EXCLUSION_SHORTFALL"`
- If `is_existing_policy_transfer == true` and `premium_gap == 0`:
  - `primary_action`: `"USE_NEW_POLICY_OR_ACCEPT_LOOKBACK"`
  - `suitability`: `"BORDERLINE"`
  - `risk_flag`: `"THREE_YEAR_LOOKBACK"`
- If `is_existing_policy_transfer == true` and `premium_gap > 0`:
  - `primary_action`: `"DISCLOSE_LOOKBACK_AND_USE_EXEMPTION"`
  - `suitability`: `"NOT_SUITABLE"`
  - `risk_flag`: `"THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL"`

**Gift plan**

- `planning_year`: the current planning year (2026)
- `annual_exclusion_per_beneficiary`: the gift exclusion for the planning year (20000)
- `beneficiary_count`: from the controlling profile source (SIGNED_PROFILE)
- `annual_exclusion_capacity`: `annual_exclusion_per_beneficiary * beneficiary_count`
- `annual_premium`: from the life insurance record
- `premium_gap`: `max(0, annual_premium - annual_exclusion_capacity)`

**Administration**

- `notices_required`: `beneficiary_count` (one Crummey notice per beneficiary)
- `contribution_date`: `planned_contribution_date` from the life insurance record
- `notice_due_date`: `contribution_date + 7 calendar days`
- `withdrawal_window_end`: `contribution_date + 37 calendar days` (30-day withdrawal
  window starting after the 7-day notice period ends)
- `earliest_premium_payment_date`: `withdrawal_window_end + 1 day`
- `dedicated_bank_account_required`: always `true` for ILIT Crummey administration

All dates are ISO 8601 (`YYYY-MM-DD`). Use Python's `datetime` and `timedelta` to
compute date arithmetic.

**Estate result**

- `death_benefit`: from the life insurance record
- `estate_inclusion_risk`: same value as `recommendation.risk_flag`
- `projected_outside_estate_if_implemented`: `death_benefit` (the full death benefit is
  outside the estate if properly implemented through the ILIT)
- `tax_liquidity_support`: `death_benefit * estate_tax_rate` (0.4)

---

### Analysis: trust_comparison

Relevant for templates where `analysis_type` is `"trust_comparison"`.

**Recommendation**

- `preferred_strategy`: `"GRAT"` when `family_transfer_priority == "high"`. `"CRAT"`
  when `philanthropic_intent == "high"` and `family_transfer_priority` is not `"high"`.
- `rationale_code`: `"CHILDREN_TRANSFER_PRIORITY"` when GRAT is preferred;
  `"PHILANTHROPIC_PRIORITY"` when CRAT is preferred.
- `alternate_role`: `"SECONDARY_CHARITABLE_TOOL"` when GRAT is primary;
  `"SECONDARY_FAMILY_TRANSFER_TOOL"` when CRAT is primary.

**Estate context**

- `planning_year`: 2026
- `exemption_used`: `estate_tax_exemption` (multiply by 2 if `filing_status` is `"MFJ"`)
- `taxable_estate`: `estate_value - exemption_used` (floor at 0)
- `estate_tax_exposure`: `taxable_estate * estate_tax_rate` (0.4)
- `liquid_assets_available`: `liquid_assets` from the signed profile
- `liquidity_gap_before_planning`: `max(0, estate_tax_exposure - liquid_assets)`

**GRAT**

- `term_years`: `grat_term_years` from the trust candidate record
- `projected_remainder_to_heirs` computed as:
  ```
  future_value = asset_value * (1 + expected_growth_rate)^term_years
  total_annuity_paid = asset_value * grat_annuity_rate * term_years
  remainder = future_value - total_annuity_paid
  ```
- `estimated_estate_tax_reduction`: `projected_remainder_to_heirs * estate_tax_rate` (0.4)
- `mortality_inclusion_risk`: `"TERM_SURVIVAL_REQUIRED"` (GRAT assets are included in
  the estate if the grantor dies during the term)

**CRAT**

- `term_years`: `crat_term_years` from the trust candidate record
- `projected_charitable_remainder`:
  ```
  future_value = asset_value * (1 + expected_growth_rate)^crat_term_years
  total_payout = asset_value * crat_payout_rate * crat_term_years
  charitable_remainder = future_value - total_payout
  ```
- `estimated_income_tax_deduction`:
  `projected_charitable_remainder * charitable_deduction_rate` (0.35)
- `family_transfer_fit`: `"LOW"` when GRAT is the preferred strategy (CRAT does not
  transfer to family in this scenario). `"MODERATE"` when priorities are mixed.
  `"HIGH"` when philanthropic intent is high and family transfer priority is low.

---

### Analysis: estate_liquidity_action_plan

Relevant for templates where `analysis_type` is `"estate_liquidity_action_plan"`.
This combines ILIT and trust-transfer analysis into one output.

**Recommendation**

- `primary_action`:
  - `"COMBINE_ILIT_AND_GRAT"` when ILIT is feasible (premium_gap == 0) and GRAT is the
    preferred trust strategy AND `family_transfer_priority == "high"`
  - `"ILIT_WITH_EXEMPTION_REVIEW"` when ILIT has a premium gap but GRAT is still
    preferred
  - `"CRAT_WITH_LIQUIDITY_REVIEW"` when CRAT is preferred
- `sequencing`: `"ILIT_FIRST_THEN_GRAT"` when both ILIT and GRAT are part of the plan;
  `"TRUST_DECISION_FIRST"` when only a trust decision is needed;
  `"ILIT_FIRST_THEN_ATTORNEY_REVIEW"` when attorney review is the main coordination need
- `risk_flag`: same value as the ILIT risk assessment (see ilit_crummey_implementation)

**Estate context**

Same computation as in trust_comparison (exemption, taxable estate, tax exposure,
liquid assets, liquidity gap).

**ILIT**

Apply the same ILIT computations from ilit_crummey_implementation:

- `annual_exclusion_capacity`: from gift plan (`annual_exclusion_per_beneficiary * beneficiary_count`)
- `premium_gap`: from gift plan (`max(0, annual_premium - annual_exclusion_capacity)`)
- `estate_inclusion_risk`: same as `recommendation.risk_flag`
- `projected_outside_estate_if_implemented`: `death_benefit` from the life insurance
  record

**Trust transfer**

- `preferred_strategy`: same logic as trust_comparison recommendation
- `projected_remainder_to_heirs`: GRAT remainder if GRAT preferred (same formula as
  trust_comparison GRAT section)
- `estimated_estate_tax_reduction`: `projected_remainder_to_heirs * 0.4`
- `projected_charitable_remainder`: CRAT remainder computed using the same formula as
  trust_comparison CRAT section, regardless of which strategy is preferred (the template
  always expects this field)

**Action set**

Build a sorted list (alphabetically) from these candidate action enums:

- Include `"ATTORNEY_DRAFT_REVIEW"` when any ILIT or trust action is part of the plan
- Include `"GRAT_FOR_APPRECIATING_SHARES"` when GRAT is the preferred trust strategy
- Include `"ILIT_CRUMMEY_NOTICE_CYCLE"` when ILIT is feasible (premium_gap == 0) and
  risk_flag is `LOW_IF_FORMALITIES_MET`
- Include `"CRAT_FOR_CHARITABLE_REMAINDER"` when CRAT is the preferred strategy
- Include `"LIFETIME_EXEMPTION_ALLOCATION"` when `premium_gap > 0` and the ILIT needs
  exemption allocation to cover the gap

Sort the final list alphabetically before writing it to the output.

---

## Step 5: Format and validate the output

### General rules for all outputs

- Return only the JSON object. No markdown fences, no prose, no trailing text.
- `task_id`: use the exact task identifier from the request memo or prompt (e.g.,
  `"train_001"`). For general test tasks, use whatever identifier the harness supplies.
- `client_id`: exactly as given in the request memo.
- USD amounts: JSON numbers rounded to two decimal places (cents).
- Dates: ISO 8601 strings (`YYYY-MM-DD`).
- Enums: use the exact uppercase strings from the template's enum lists.
- Lists: follow any ordering constraint noted in the template (e.g., `action_set` must
  be sorted alphabetically).
- Object keys: no ordering constraint beyond what the template specifies.

### Numeric precision

Use floating-point arithmetic for intermediate computation, rounding to two decimal
places only at the final output. To avoid floating-point noise, compute in a consistent
order and apply `round(value, 2)` just before JSON serialization.

### Validation checklist before returning

1. Every key in `required_top_level_keys` is present in the output
2. Every nested field matches its specified type and enum
3. `task_id` and `client_id` are set correctly
4. All dollar amounts are JSON numbers (not strings), rounded to cents
5. All dates are ISO strings
6. Lists are sorted as required
7. No extra prose or markdown outside the JSON object

## Example workflow

For a concrete illustration, here is the full sequence for a Roth conversion analysis:

1. Read `input/prompt.txt`, `input/payloads/request_memo.md`, and
   `input/payloads/answer_template.json` from the task directory.
2. Identify `client_id`, `analysis_type`, and any horizon from the memo.
3. Fetch client, source documents, retirement accounts, tax policies, and RMD factors
   from the API using Python's `requests` or equivalent.
4. Extract the controlling profile facts from the SIGNED_PROFILE source document
   (filtering by client_id and source_type).
5. Extract retirement account data from the CUSTODIAN_EXPORT record
   (filtering by client_id from the retirement-accounts endpoint).
6. Compute bracket headroom, conversion plan, RMD projections (baseline and conversion),
   and legacy balances using the formulas above.
7. If the template includes life insurance or trust fields, fetch those endpoints too
   and apply the relevant analysis section.
8. Assemble the JSON object matching the template, using the formulas and decision
   tables above.
9. Round all dollar amounts to cents.
10. Output only the JSON with no surrounding text or code fences.
