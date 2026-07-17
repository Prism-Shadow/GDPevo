# Private Wealth Advisory — Structured Planning Output Skill

## Overview

This skill covers producing structured JSON planning outputs for a private wealth advisory API. It supports four analysis types: Roth conversion with RMD projections, ILIT Crummey implementation, GRAT-vs-CRAT trust comparison, and estate liquidity action plans. The API provides client profiles; the skill specifies how to derive numeric projections, resolve conflicting source records, and conform to the answer templates.

## API Usage

### Client Lookup

```
GET {API_BASE}/api/clients          → list all clients
GET {API_BASE}/api/clients/{id}     → single client summary
GET {API_BASE}/api/health           → service health check
```

The client object returns these fields (all other data must be derived or assumed from standard tax/planning constants):

| Field | Type | Meaning |
|-------|------|---------|
| `client_id` | string | Stable identifier, e.g. `CLT-1001` |
| `household_name` | string | Display name |
| `age` | integer | Client age in the planning year |
| `marital_status` | string | `married` or `single` |
| `filing_status` | string | `MFJ`, `SINGLE`, or `HOH` |
| `planning_year` | integer | Current planning year (2026) |
| `estate_value` | number | Gross estate in USD |
| `liquid_assets` | number | Available liquid assets in USD |
| `record_status` | string | `active` or `monitoring` |
| `advisor_team` | string | Team assignment |

Sub-resource paths (e.g. `/api/clients/{id}/accounts`) are valid routes but may return `"client not found"` when no sub-records exist for that client. Do not assume sub-resource data is always available; derive what you can from the client summary and standard constants.

### Response Handling

- Always check for `"error"` keys in API responses.
- A `"client not found"` error on a sub-resource means the client has no records of that type — treat as zero/empty, not as a fatal error.
- Use `{API_BASE}` from the harness environment; never hardcode localhost.

## Output Format Rules (All Analysis Types)

1. **Return ONLY a JSON object.** No prose, markdown fences, or explanatory text outside the JSON.
2. **All numbers must be JSON numbers, not strings.** `1800000.00` not `"1800000.00"`.
3. **USD amounts must be rounded to two decimal places (cents).**
4. **ISO 8601 dates** (`YYYY-MM-DD`) wherever a date field is required.
5. **Integer fields** (`first_conversion_year`, `conversion_years`, `horizon_year`, `beneficiary_count`, `term_years`, `notices_required`) must be JSON integers without a decimal point.
6. **Boolean fields** (`dedicated_bank_account_required`) must be JSON `true`/`false`, not strings.
7. **`action_set` must be sorted alphabetically** (the only field with ordering constraints).
8. **Every answer must include top-level keys** `task_id`, `client_id`, and `analysis_type`.

## Analysis Type Reference

### 1. `roth_conversion_rmd` — Roth Conversion & RMD Projection

Used for tasks involving staged Roth conversions before Required Minimum Distributions begin.

**Top-level keys:** `task_id`, `client_id`, `analysis_type`, `recommendation`, `conversion_plan`, `rmd_projection`, `legacy_projection`, `source_resolution`

**Recommendation enums:**
- `primary_action`: `STAGED_ROTH_CONVERSION` | `DEFER` | `NO_CONVERSION`
  - `STAGED_ROTH_CONVERSION`: client has a conversion window before RMDs and sufficient liquid assets to pay conversion tax.
  - `DEFER`: near RMD age, insufficient conversion runway, or liquidity constrained.
  - `NO_CONVERSION`: no tax benefit from converting.
- `suitability`: `SUITABLE` | `BORDERLINE` | `DEFER`
  - `SUITABLE`: clear conversion window (≥5 years before RMD), manageable tax bracket impact.
  - `BORDERLINE`: short window (<5 years), near RMD age, or bracket risk.
  - `DEFER`: already in RMDs or conversion window closed.
- `risk_flag`: `TAX_BRACKET_MANAGEMENT` | `LIQUIDITY_CONSTRAINT` | `RMD_NEAR_TERM`
  - `TAX_BRACKET_MANAGEMENT`: primary concern is staying within a target marginal bracket.
  - `LIQUIDITY_CONSTRAINT`: liquid assets may not cover the conversion tax bill.
  - `RMD_NEAR_TERM`: RMDs begin within 1-2 years, compressing the conversion window.

**Conversion plan fields:**
- `first_conversion_year`: The calendar year of the first conversion. When recommending immediate action, set this to the planning year.
- `conversion_years`: Total number of years with a conversion (including $0 years if applicable).
- `conversion_years_positive`: Number of years with a non-zero conversion amount. Usually equals `conversion_years` unless a gap year is planned.
- `annual_conversion_amount`: The amount converted each positive year, in USD rounded to cents.
- `total_converted`: `conversion_years_positive × annual_conversion_amount`.
- `total_conversion_tax`: `total_converted × effective_tax_rate`. Use the client's estimated marginal rate (typically 24% for MFJ moderate conversions, 32-35% for SINGLE higher brackets). Document the rate assumption.

**RMD projection fields:**
- `horizon_year`: The planning horizon end year (from the request memo).
- `first_rmd_year`: The calendar year the client must take their first RMD. See RMD Age Rules below.
- `baseline_rmd_tax_through_horizon`: Total income tax on RMDs from the horizon year back to the first RMD year, assuming NO conversions.
- `conversion_rmd_tax_through_horizon`: Total income tax on RMDs assuming the recommended conversions are executed.
- `rmd_tax_savings_through_horizon`: `baseline_rmd_tax - conversion_rmd_tax` (must be positive if conversions reduce RMDs).

**Legacy projection fields:**
- `projected_roth_balance_horizon`: Projected Roth IRA balance at horizon year.
- `projected_traditional_balance_horizon`: Projected Traditional IRA balance at horizon year.
- `heir_tax_profile`: `MOSTLY_TAX_FREE` | `MIXED_TAXABLE_AND_TAX_FREE` | `MOSTLY_TAXABLE`
  - `MOSTLY_TAX_FREE`: Roth balance > 2× Traditional balance.
  - `MIXED_TAXABLE_AND_TAX_FREE`: Roughly balanced.
  - `MOSTLY_TAXABLE`: Traditional balance > 2× Roth balance.

### 2. `ilit_crummey_implementation` — ILIT with Crummey Notices

Used for life insurance trust funding through annual gift-tax exclusion with Crummey withdrawal rights.

**Top-level keys:** `task_id`, `client_id`, `analysis_type`, `recommendation`, `gift_plan`, `administration`, `estate_result`, `source_resolution`

**Recommendation enums:**
- `primary_action`: `FUND_WITH_CRUMMEY_NOTICES` | `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` | `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` | `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`
  - `FUND_WITH_CRUMMEY_NOTICES`: Premium ≤ annual exclusion capacity, standard Crummey process.
  - `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`: Premium exceeds exclusion capacity but shortfall can be covered by lifetime exemption.
  - The lookback variants apply when a policy transferred within 3 years creates estate inclusion risk.
- `suitability`: `SUITABLE_WITH_ADMINISTRATION` | `BORDERLINE` | `NOT_SUITABLE`
- `risk_flag`: `LOW_IF_FORMALITIES_MET` | `EXCLUSION_SHORTFALL` | `THREE_YEAR_LOOKBACK` | `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`

**Gift plan calculations:**
- `planning_year`: Calendar year of the premium cycle.
- `annual_exclusion_per_beneficiary`: The annual gift tax exclusion amount per donee. Use $19,000 for 2026 (inflation-adjusted from 2025's $19,000; the IRS rounds to nearest $1,000).
- `beneficiary_count`: Number of Crummey beneficiaries (trust beneficiaries with present withdrawal rights).
- `annual_exclusion_capacity`: `annual_exclusion_per_beneficiary × beneficiary_count`.
- `annual_premium`: The total annual insurance premium.
- `premium_gap`: `annual_premium - annual_exclusion_capacity`. Positive means a shortfall; zero or negative means the exclusion covers the premium.

**Administration dates (Crummey timeline):**
- `contribution_date`: Date contribution is made to the ILIT.
- `notice_due_date`: `contribution_date + 30 days` (Crummey notice must be sent promptly; 30 days is standard safe harbor).
- `withdrawal_window_end`: `notice_due_date + 30 days` (beneficiaries typically have 30 days from notice to exercise withdrawal rights).
- `earliest_premium_payment_date`: `withdrawal_window_end + 1 day` (pay premium only after withdrawal window closes).
- `notices_required`: Equal to `beneficiary_count` (one Crummey notice per beneficiary with withdrawal rights).
- `dedicated_bank_account_required`: `true` — best practice for ILITs to avoid incidents of ownership.

**Estate result:**
- `death_benefit`: Face amount of the life insurance policy.
- `estate_inclusion_risk`: Same enum as `risk_flag`; mirrors the recommendation risk flag.
- `projected_outside_estate_if_implemented`: The death benefit amount that stays outside the taxable estate when ILIT formalities are followed. Equal to `death_benefit` if no inclusion risk.
- `tax_liquidity_support`: The death benefit available to pay estate taxes, typically `death_benefit × 0.40` (approximate estate tax rate).

### 3. `trust_comparison` — GRAT versus CRAT

Used for comparing Grantor Retained Annuity Trust against Charitable Remainder Annuity Trust.

**Top-level keys:** `task_id`, `client_id`, `analysis_type`, `recommendation`, `estate_context`, `grat`, `crat`, `source_resolution`

**Recommendation enums:**
- `preferred_strategy`: `GRAT` | `CRAT`
  - `GRAT`: family/heir transfer is the dominant goal; charity is secondary.
  - `CRAT`: charitable intent is primary; family transfer is secondary.
- `rationale_code`: `CHILDREN_TRANSFER_PRIORITY` | `PHILANTHROPIC_PRIORITY`
- `alternate_role`: `SECONDARY_CHARITABLE_TOOL` | `SECONDARY_FAMILY_TRANSFER_TOOL`
  - When GRAT is preferred: the CRAT serves as `SECONDARY_CHARITABLE_TOOL`.
  - When CRAT is preferred: the GRAT serves as `SECONDARY_FAMILY_TRANSFER_TOOL`.

**Estate context:**
- `taxable_estate`: The gross estate value (from client profile `estate_value`).
- `estate_tax_exposure`: `max(0, (taxable_estate − applicable_exemption) × 0.40)`. See Estate Tax Constants.
- `liquidity_gap_before_planning`: `max(0, estate_tax_exposure − liquid_assets)`.

**GRAT fields:**
- `term_years`: Grantor Retained Annuity Trust term. Short terms (2-3 years) minimize mortality risk. Use 2 as default.
- `projected_remainder_to_heirs`: Estimated value passing to remainder beneficiaries, net of the annuity stream.
- `estimated_estate_tax_reduction`: `projected_remainder_to_heirs × 0.40`.
- `mortality_inclusion_risk`: Always `TERM_SURVIVAL_REQUIRED` — the grantor must survive the GRAT term for estate tax exclusion. If the grantor dies during the term, assets are pulled back into the estate.

**CRAT fields:**
- `term_years`: CRAT term. Can be a term of years or life. Use 1 for a short-term comparison CRAT.
- `projected_charitable_remainder`: Estimated remainder interest passing to charity.
- `estimated_income_tax_deduction`: The present value of the charitable remainder interest, usable as an income tax deduction in the year of funding (subject to AGI limits).
- `family_transfer_fit`: `LOW` | `MODERATE` | `HIGH`
  - `LOW`: most assets go to charity, minimal family benefit.
  - `MODERATE`: annuity stream provides partial family benefit.
  - `HIGH`: high annuity payout provides substantial family benefit before charitable remainder.

### 4. `estate_liquidity_action_plan` — Combined Estate Liquidity Planning

Used for complex cases combining ILIT, trust transfer, and estate liquidity analysis.

**Top-level keys:** `task_id`, `client_id`, `analysis_type`, `recommendation`, `estate_context`, `ilit`, `trust_transfer`, `action_set`, `source_resolution`

**Recommendation enums:**
- `primary_action`: `COMBINE_ILIT_AND_GRAT` | `CRAT_WITH_LIQUIDITY_REVIEW` | `ILIT_WITH_EXEMPTION_REVIEW`
- `sequencing`: `ILIT_FIRST_THEN_GRAT` | `TRUST_DECISION_FIRST` | `ILIT_FIRST_THEN_ATTORNEY_REVIEW`
- `risk_flag`: Same as ILIT risk flags.

**action_set:** A JSON array of action items, **sorted alphabetically**. Valid actions:
- `ATTORNEY_DRAFT_REVIEW`
- `CRAT_FOR_CHARITABLE_REMAINDER`
- `GRAT_FOR_APPRECIATING_SHARES`
- `ILIT_CRUMMEY_NOTICE_CYCLE`
- `LIFETIME_EXEMPTION_ALLOCATION`

## Tax & Planning Constants

### RMD Age Rules (SECURE 2.0, effective 2024+)

Determine the year a client must begin RMDs based on birth year:

| Birth Year | RMD Start Age | Rule |
|------------|---------------|------|
| Before 1951 | 72 | Pre-SECURE |
| 1951–1959 | 73 | SECURE 2.0 |
| 1960 or later | 75 | SECURE 2.0 |

**Formula:** `first_rmd_year = birth_year + rmd_start_age`
- If the resulting year is before the planning year, RMDs are already in progress — use the planning year or an already-passed year based on when the client actually turned the RMD age.

**Age-to-birth-year (for planning year 2026):**
- Age 72 → born 1954 → RMD age 73 → first RMD **2027**
- Age 66 → born 1960 → RMD age 75 → first RMD **2035**
- Age 57 → born 1969 → RMD age 75 → first RMD **2044**

### Estate Tax (2026, Post-TCJA Sunset)

The Tax Cuts and Jobs Act doubled exemption sunsets after 2025. For planning year 2026:

| Filing Status | Applicable Exemption (est.) | Top Rate |
|---------------|----------------------------|----------|
| SINGLE | $7,200,000 | 40% |
| MFJ | $14,400,000 | 40% |

**Calculation:**
```
taxable_estate = estate_value (from client profile)
estate_tax_exposure = max(0, taxable_estate − applicable_exemption) × 0.40
liquidity_gap = max(0, estate_tax_exposure − liquid_assets)
```

### Gift Tax Annual Exclusion (2026)

- **$19,000** per beneficiary (inflation-adjusted from 2025).
- Spouses can gift-split for $38,000 per beneficiary from a joint account.
- For SINGLE filers funding an ILIT, use $19,000 per beneficiary.

### Income Tax Brackets — Marginal Rates (2026 est., MFJ)

Use for estimating conversion tax:

| Bracket | MFJ Income Range | SINGLE Income Range |
|---------|-----------------|---------------------|
| 24% | $201,051–$383,900 | $100,501–$191,950 |
| 32% | $383,901–$487,450 | $191,951–$243,725 |
| 35% | $487,451–$731,200 | $243,726–$609,350 |
| 37% | $731,201+ | $609,351+ |

When a client's other income is unknown, assume they fill lower brackets and the conversion falls in the 24% bracket for MFJ or SINGLE filers with moderate income. For SINGLE filers with large estates, the 32% bracket is more conservative.

### Sec. 7520 Rate (GRAT Hurdle)

For 2026, the IRS Section 7520 rate (used as the GRAT annuity hurdle) is approximately 4.0–5.0%. The GRAT remainder (amount passing to heirs tax-free) equals the trust assets' growth in excess of this hurdle rate. Use growth assumptions of 6-8% for a diversified equity portfolio, yielding a remainder of roughly 5-15% of the funded amount per year above the hurdle.

## Source Resolution

Client records may conflict because they were imported from different systems at different times. The controlling source must be identified for each data domain. Use this reliability hierarchy (most reliable first):

### Profile / Beneficiary / Goal Sources
1. `SIGNED_PROFILE` — most recent signed advisory profile; highest authority.
2. `ATTORNEY_MEMO` — attorney correspondence or planning memo; strong but may predate the signed profile.
3. `CRM_NOTE` — advisor notes in the CRM; contemporaneous but less formal.
4. `CUSTODIAN_EXPORT` — custodian data export; reliable for account values, less so for goals.
5. `STALE_MARKETING_INTAKE` — oldest, least reliable; pre-engagement marketing data.

### Account / Policy Sources
1. `CUSTODIAN_EXPORT` — authoritative for account balances, positions, cost basis.
2. `SIGNED_PROFILE` — may list accounts but balances can be stale.
3. `CRM_NOTE` — advisor-entered values; useful if custodian data is unavailable.

### Asset Sources (Trust Funding)
1. `ATTORNEY_MEMO` — attorney asset schedule for trust funding.
2. `SIGNED_PROFILE` — corroborates attorney memo.
3. `CRM_NOTE` — supplementary.

### Default Assignment

When no conflicting records are evident, default to:
- **Profile/beneficiary/goal:** `SIGNED_PROFILE`
- **Account/balances:** `CUSTODIAN_EXPORT`
- **Policy:** `CUSTODIAN_EXPORT`
- **Asset (trust funding):** `ATTORNEY_MEMO`

## Calculation Conventions

### Rounding
- All USD amounts: round to **two decimal places** (cents).
- Intermediate calculations may use higher precision; round only at the final field value.
- Use standard rounding (half-up).

### Consistency Constraints
- `conversion_years_positive ≤ conversion_years` and `conversion_years_positive ≥ 0`.
- `total_converted = conversion_years_positive × annual_conversion_amount` (exact equality).
- `rmd_tax_savings_through_horizon = baseline_rmd_tax_through_horizon − conversion_rmd_tax_through_horizon` (exact equality).
- `premium_gap = annual_premium − annual_exclusion_capacity`. Can be negative (surplus) or positive (shortfall).
- `liquidity_gap_before_planning = estate_tax_exposure − liquid_assets`, floored at $0.
- `first_conversion_year ≥ planning_year`.
- `first_rmd_year` is derived from birth year and RMD age rules; it is not a free variable.
- `horizon_year` comes from the request memo.
- `heir_tax_profile` must be consistent with the ratio of `projected_roth_balance_horizon` to `projected_traditional_balance_horizon`.

### Date Logic (Crummey Timeline)
```
contribution_date = chosen contribution date (typically mid-January of planning year)
notice_due_date    = contribution_date + 30 days
withdrawal_window_end = notice_due_date + 30 days
earliest_premium_payment_date = withdrawal_window_end + 1 day
```
All dates are ISO format. The 30-day periods are calendar days, not business days.

## Common Pitfalls

1. **Wrong RMD age.** The most frequent error is using pre-SECURE-2.0 RMD ages (70½ or 72). Always apply the SECURE 2.0 table: born pre-1951 → 72, 1951–1959 → 73, 1960+ → 75.

2. **Pre-TCJA estate tax exemption.** Using the 2025 exemption (~$13.99M individual / ~$27.98M MFJ) for planning year 2026 after the TCJA sunset. The exemption reverts to approximately $7.2M individual / $14.4M MFJ (inflation-adjusted). This dramatically changes estate tax exposure for clients with estates in the $7M–$28M range.

3. **Gift exclusion year confusion.** Using the 2025 annual exclusion ($19,000) for 2024 or earlier years. Confirm the planning year and use the corresponding exclusion amount.

4. **String-typed numbers.** JSON numbers must not be quoted. `"total_converted": 1800000.00` is correct; `"total_converted": "1800000.00"` is wrong.

5. **Unsorted action_set.** The action_set array must be alphabetically sorted. `["ATTORNEY_DRAFT_REVIEW", "GRAT_FOR_APPRECIATING_SHARES", "ILIT_CRUMMEY_NOTICE_CYCLE"]` is correct.

6. **Missing cents in dollar amounts.** Always include `.00` for whole-dollar amounts. `1800000.00` not `1800000`.

7. **Integer fields with decimal points.** `"conversion_years": 9` is correct; `"conversion_years": 9.0` may fail validation.

8. **Wrong analysis_type enum.** Match the analysis type exactly to the task:
   - Roth conversion tasks → `roth_conversion_rmd`
   - ILIT tasks → `ilit_crummey_implementation`
   - GRAT/CRAT tasks → `trust_comparison`
   - Combined estate tasks → `estate_liquidity_action_plan`

9. **first_rmd_year vs planning year.** If the client is already past their RMD start age, the first RMD year should reflect the actual year they were required to begin (which may be before the planning year). Do not set it to the planning year simply because that is "now."

10. **Inconsistent estate_inclusion_risk.** The `estate_result.estate_inclusion_risk` must match the `recommendation.risk_flag` value — they represent the same assessment.

11. **Source resolution mismatch.** Assigning `STALE_MARKETING_INTAKE` as the controlling source when any more-recent source exists. Only use `STALE_MARKETING_INTAKE` if it is literally the only source available for that data domain.

12. **Liquidity gap floor.** `liquidity_gap_before_planning` should never be negative. If liquid assets exceed estate tax exposure, the gap is $0.00.

## Workflow for Solving a New Task

1. **Read the request memo** — extract client ID, engagement type, horizon year, and any special instructions.
2. **Fetch client profile** — `GET {API_BASE}/api/clients/{client_id}`.
3. **Identify the analysis type** — match the engagement to one of the four templates.
4. **Determine RMD age** — compute birth year from age + planning year, apply SECURE 2.0 rules.
5. **Calculate estate tax exposure** — apply post-TCJA 2026 exemption and 40% rate.
6. **Compute numeric projections** — use the formulas in this skill for conversion plans, RMD tax savings, gift plans, or trust projections.
7. **Resolve sources** — apply the source hierarchy; default to `SIGNED_PROFILE` for profile/goals and `CUSTODIAN_EXPORT` for accounts/policies.
8. **Populate the template** — fill every required field; verify consistency constraints; ensure proper JSON types.
9. **Sort action_set** — if the template includes `action_set`, sort it alphabetically before returning.
10. **Validate** — check that all numbers are JSON numbers, all dates are ISO format, all enums match allowed values, and all consistency constraints hold.
