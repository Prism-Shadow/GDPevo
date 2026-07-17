# Skill: Private Wealth Advisory Structured Planning Output

## Condition
Self-contained financial planning tasks that require querying a remote advisory API, resolving conflicting client sources, performing tax/estate calculations, and emitting a strict JSON object conforming to a task-specific answer template.

## 0. Pre-Flight Checklist

1. **Read `environment_access.md`** to get the exact remote API base URL. Do not start local env services, run `env/setup.sh`, or use `localhost`/`127.0.0.1`.
2. **Read `input/prompt.txt`** to identify the client, engagement type, and task ID.
3. **Read `input/payloads/request_memo.md`** to extract: planning horizon year, household specifics, and advisor priorities.
4. **Read `input/payloads/answer_template.json`** to memorize the required top-level keys, field types, enums, and ordering rules for this exact analysis type.
5. **Query the API** (`GET /api/health`, then `GET /api/clients/{client_id}`) to fetch the flat client profile.

## 1. API Usage Habits

### Discovery & Health
- `GET {BASE_URL}/api/health` → verify service. Expected: `{"ok": true, "service": "private-wealth-advisory"}`.
- `GET {BASE_URL}/api/clients` → flat list of all client profiles.
- `GET {BASE_URL}/api/clients/{client_id}` → single flat profile.

### Flat Profile Schema
The API returns **only** flat objects with these fields:
- `client_id`, `household_name`, `age` (int), `marital_status` (`"married"`|`"single"`), `filing_status` (`"MFJ"`|`"SINGLE"`|`"HOH"`), `planning_year` (int, usually 2026), `estate_value` (int USD), `liquid_assets` (int USD), `record_status`, `advisor_team`.

### Sub-Resource Caveat
Endpoints like `/api/clients/{id}/records`, `/accounts`, `/policies`, `/documents` currently return `"client not found"` even for valid clients. **Do not rely on them.** Derive missing detail (account balances, policy values, beneficiary counts, RMD factors, tax constants) from:
- The request memo context,
- Standard tax/estate planning assumptions,
- The template field definitions themselves (they imply what values are expected).

## 2. Source Resolution Rules

When the prompt or template mentions conflicting records imported from different systems, apply this hierarchy (highest first) to choose the **controlling source**:

1. `SIGNED_PROFILE` — highest authority for profile/goal data.
2. `ATTORNEY_MEMO` — high authority, especially for trust/legal structures.
3. `CUSTODIAN_EXPORT` — authoritative for account balances and policy values.
4. `CRM_NOTE` — secondary, use only if higher sources absent.
5. `STALE_MARKETING_INTAKE` — lowest authority; treat as fallback only.

**Rule:** If the task context implies only one source exists for a category, use that source. Never default to `CRM_NOTE` just because it is mentioned in passing.

## 3. Analysis-Type SOPs

Each task uses exactly one `analysis_type`. Match the template to the section below and follow the calculation SOP.

### A. Roth Conversion & RMD (`analysis_type: roth_conversion_rmd`)

**Required top-level keys:** `task_id`, `client_id`, `analysis_type`, `recommendation`, `conversion_plan`, `rmd_projection`, `legacy_projection`, `source_resolution`

**Source resolution fields:** `controlling_profile_source`, `controlling_account_source`

**Calculation SOP:**
1. **RMD Age** (SECURE 2.0):
   - Born before 1951 → 70.5
   - Born 1951–1959 → 73
   - Born 1960+ → 75
2. **First RMD year** = birth year + RMD age.
3. **Conversion window** = years from `planning_year` up to (but not including) first RMD year.
4. **conversion_years** = count of years in the window.
5. **conversion_years_positive** = same integer as `conversion_years` (≥ 0).
6. **annual_conversion_amount** = estimated traditional balance ÷ `conversion_years` (if staged conversion is viable).
7. **total_converted** = `annual_conversion_amount` × `conversion_years`.
8. **total_conversion_tax** = `total_converted` × effective marginal tax rate (bracket-aware; e.g. 24%–35% for HNW).
9. **baseline_rmd_tax_through_horizon** = projected tax on RMDs with no conversion, through the memo's horizon year.
10. **conversion_rmd_tax_through_horizon** = projected tax on RMDs after conversion, through horizon.
11. **rmd_tax_savings_through_horizon** = baseline − conversion.
12. **Projected balances at horizon:**
    - Roth = starting Roth + total_converted + growth.
    - Traditional = starting traditional − total_converted − RMDs + growth.
13. **heir_tax_profile:**
    - `MOSTLY_TAX_FREE` if projected Roth >> projected traditional
    - `MIXED_TAXABLE_AND_TAX_FREE` if roughly balanced
    - `MOSTLY_TAXABLE` if projected traditional dominates

**Recommendation enums:**
- `primary_action`: `STAGED_ROTH_CONVERSION`, `DEFER`, `NO_CONVERSION`
- `suitability`: `SUITABLE`, `BORDERLINE`, `DEFER`
- `risk_flag`: `TAX_BRACKET_MANAGEMENT`, `LIQUIDITY_CONSTRAINT`, `RMD_NEAR_TERM`

---

### B. ILIT Crummey Implementation (`analysis_type: ilit_crummey_implementation`)

**Required top-level keys:** `task_id`, `client_id`, `analysis_type`, `recommendation`, `gift_plan`, `administration`, `estate_result`, `source_resolution`

**Source resolution fields:** `controlling_beneficiary_source`, `controlling_policy_source`

**Calculation SOP:**
1. **Annual exclusion per beneficiary (2026):** $18,000 per donor.
   - MFJ households have two donors → $36,000 per beneficiary total.
2. **annual_exclusion_capacity** = per_beneficiary × beneficiary_count.
3. **annual_premium** = policy annual premium (from memo/context).
4. **premium_gap** = max(0, annual_premium − annual_exclusion_capacity).
5. **notices_required** = beneficiary_count (one Crummey notice per beneficiary per contribution).
6. **contribution_date** = date premium is paid (ISO `YYYY-MM-DD`).
7. **notice_due_date** = contribution_date + 30 days.
8. **withdrawal_window_end** = contribution_date + 30 days (standard Crummey window).
9. **earliest_premium_payment_date** = first day of planning year or policy anniversary.
10. **dedicated_bank_account_required** = `true` (ILIT best practice).
11. **death_benefit** = policy face amount.
12. **projected_outside_estate_if_implemented** = death benefit (assuming formalities met).
13. **tax_liquidity_support** = estate_tax_exposure − liquid_assets.
14. **estate_inclusion_risk** = same enum value as `recommendation.risk_flag`.

**Recommendation enums:**
- `primary_action`: `FUND_WITH_CRUMMEY_NOTICES`, `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`, `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`, `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`
- `suitability`: `SUITABLE_WITH_ADMINISTRATION`, `BORDERLINE`, `NOT_SUITABLE`
- `risk_flag`: `LOW_IF_FORMALITIES_MET`, `EXCLUSION_SHORTFALL`, `THREE_YEAR_LOOKBACK`, `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`

---

### C. GRAT vs CRAT Comparison (`analysis_type: trust_comparison`)

**Required top-level keys:** `task_id`, `client_id`, `analysis_type`, `recommendation`, `estate_context`, `grat`, `crat`, `source_resolution`

**Source resolution fields:** `controlling_goal_source`, `controlling_asset_source`

**Calculation SOP:**
1. **Taxable estate** = `estate_value` − applicable estate tax exemption.
   - 2026 exemption: ~$13.99M per person ($27.98M MFJ).
   - Floor at 0.
2. **Estate tax exposure** = taxable_estate × 0.40.
3. **Liquidity gap before planning** = estate_tax_exposure − liquid_assets.
4. **GRAT:**
   - `term_years`: typically 2–5.
   - `projected_remainder_to_heirs`: asset value minus annuity payments (7520-rate PV discount).
   - `estimated_estate_tax_reduction`: ≈ remainder value removed from estate.
   - `mortality_inclusion_risk`: `TERM_SURVIVAL_REQUIRED`.
5. **CRAT:**
   - `term_years`: lifetime or 20 years.
   - `projected_charitable_remainder`: PV of remainder interest (charitable deduction).
   - `estimated_income_tax_deduction`: PV of charitable remainder.
   - `family_transfer_fit`:
     - `LOW` if client prioritizes family transfer
     - `MODERATE` if balanced
     - `HIGH` if charitable priority
6. **Recommendation** must pick one primary tool based on memo goals:
   - `preferred_strategy`: `GRAT` | `CRAT`
   - `rationale_code`: `CHILDREN_TRANSFER_PRIORITY` | `PHILANTHROPIC_PRIORITY`
   - `alternate_role`: `SECONDARY_CHARITABLE_TOOL` | `SECONDARY_FAMILY_TRANSFER_TOOL`

---

### D. Estate Liquidity Action Plan (`analysis_type: estate_liquidity_action_plan`)

**Required top-level keys:** `task_id`, `client_id`, `analysis_type`, `recommendation`, `estate_context`, `ilit`, `trust_transfer`, `action_set`, `source_resolution`

**Source resolution fields:** `controlling_goal_source`, `controlling_policy_source`

**Calculation SOP:**
1. Compute `estate_context` exactly as in GRAT/CRAT section.
2. Compute `ilit` sub-object using ILIT rules (annual_exclusion_capacity, premium_gap, estate_inclusion_risk, projected_outside_estate_if_implemented).
3. Compute `trust_transfer`:
   - `preferred_strategy`: `GRAT` | `CRAT`
   - `projected_remainder_to_heirs`, `estimated_estate_tax_reduction`, `projected_charitable_remainder`.
4. **action_set** = alphabetically sorted list of applicable actions chosen from:
   - `ATTORNEY_DRAFT_REVIEW`
   - `CRAT_FOR_CHARITABLE_REMAINDER`
   - `GRAT_FOR_APPRECIATING_SHARES`
   - `ILIT_CRUMMEY_NOTICE_CYCLE`
   - `LIFETIME_EXEMPTION_ALLOCATION`

**Recommendation enums:**
- `primary_action`: `COMBINE_ILIT_AND_GRAT`, `CRAT_WITH_LIQUIDITY_REVIEW`, `ILIT_WITH_EXEMPTION_REVIEW`
- `sequencing`: `ILIT_FIRST_THEN_GRAT`, `TRUST_DECISION_FIRST`, `ILIT_FIRST_THEN_ATTORNEY_REVIEW`
- `risk_flag`: same ILIT risk flags (`LOW_IF_FORMALITIES_MET`, etc.)

## 4. Output Field Conventions

### Universal Rules
- Return **only** the final JSON object. No markdown code fences, no prose before or after.
- Include **all** `required_top_level_keys` from the template.
- `task_id` = the prompt's task identifier (e.g. `train_001`, `test_001`).
- `client_id` = the stable identifier (e.g. `CLT-1001`).
- `analysis_type` = exact enum string from the template.

### Numeric Formatting
- All USD amounts must be JSON **numbers** (not strings), rounded to **two decimal places** (cents).
  - Correct: `18400000.00`
  - Wrong: `"18400000.00"`, `18400000` (if the evaluator expects cents)
- Years, counts, and other integers can be bare JSON integers.

### Date Formatting
- All dates must be ISO 8601: `YYYY-MM-DD`.
- Example: `2026-01-15`.

### Enum Strictness
- Use **only** the enum values explicitly listed in the template. Any deviation causes validation failure.
- Watch for compound enums like `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`.

### Ordering
- `action_set` (in `estate_liquidity_action_plan`) must be sorted **alphabetically**.
- No ordering constraints for object keys unless the template explicitly states one.

## 5. Pitfalls & Verification Checklist

- [ ] **Sub-resources missing:** Do not assume `/api/clients/{id}/records`, `/accounts`, `/policies` return data. They return `"client not found"` even for valid clients. Derive values from the flat profile + memo context.
- [ ] **String vs Number:** Never quote numeric fields. The evaluator checks types strictly.
- [ ] **RMD Age Errors:** SECURE 2.0 changed RMD ages. Verify birth year before computing first RMD year.
- [ ] **Estate Exemption:** Use current-year figures (~$13.99M per person in 2026). Do not use outdated $11.7M or $5M values.
- [ ] **Source Resolution Defaulting:** Do not lazily default to `CRM_NOTE`. Apply the hierarchy explicitly.
- [ ] **Action Set Sorting:** For `estate_liquidity_action_plan`, forgetting to alphabetize `action_set` is a common scoring failure.
- [ ] **Horizon Year Mismatch:** Use the planning horizon year from the request memo. If the memo says 2046, all horizon projections must target 2046.
- [ ] **Missing task_id:** Every template requires `task_id`. Omitting it causes immediate validation failure.
- [ ] **ISO Date Precision:** Crummey windows are 30 days. Compute `withdrawal_window_end` as contribution_date + 30 days, not +31 or +29.
- [ ] **MFJ Exclusion Doubling:** For ILIT tasks with MFJ clients, both spouses can gift, so per-beneficiary capacity doubles.
