# Private Wealth Advisory Structured Output Skill

## Overview

This skill covers generating structured JSON planning outputs for private wealth advisory engagements. Tasks span Roth conversion and RMD analysis, ILIT Crummey funding, GRAT/CRAT trust comparisons, and estate liquidity action plans.

## Environment Setup

The advisory API provides client records at a base URL supplied by the harness. Use that base URL for all HTTP requests.

### API Endpoints

Only two endpoints are available:

```
GET {API_BASE}/api/clients          — list all clients
GET {API_BASE}/api/clients/{id}     — single client detail
```

No other endpoints exist for accounts, documents, policies, trusts, profiles, sources, RMD factors, or tax constants. All required data must be derived from the client record plus standard tax and estate-planning rules.

### Client Record Schema

Each client object contains:

| Field | Type | Description |
|-------|------|-------------|
| client_id | string | Stable identifier (e.g. CLT-1001) |
| household_name | string | Display name |
| age | integer | Client age in planning_year |
| marital_status | string | married / single |
| filing_status | string | MFJ / SINGLE / HOH |
| planning_year | integer | Current planning year (e.g. 2026) |
| estate_value | number | Total gross estate in USD |
| liquid_assets | number | Liquid assets available in USD |
| record_status | string | active / monitoring |
| advisor_team | string | Advisory team assignment |

## Task Input Structure

Each task directory contains:

```
input/
  prompt.txt                  — engagement description and client ID
  payloads/
    request_memo.md           — advisor request memo with specific context
    answer_template.json      — required output schema and enum definitions
```

### Workflow Steps

1. **Read the answer template first.** It defines all required top-level keys, field types, and allowed enum values.
2. **Read the request memo** for the client ID, engagement type, and planning horizon.
3. **Fetch client data** from `GET {API_BASE}/api/clients/{client_id}`.
4. **Fetch all clients** from `GET {API_BASE}/api/clients` if you need cross-client context or to verify data.
5. **Construct the answer JSON** conforming exactly to the template.
6. **Return only the JSON object** — no prose outside the JSON.

## Output Construction Rules

### General JSON Rules

- Return **only** a JSON object that conforms to `answer_template.json`.
- Do not include prose, markdown fences, or commentary outside the JSON.
- Numbers must be **JSON numbers**, not strings.
- USD amounts must be **rounded to cents** (two decimal places).
- Dates must be **ISO 8601 format** (YYYY-MM-DD).
- Object key order is not scored except where noted.
- Every `required_top_level_key` from the template **must be present**.

### Task ID and Client ID

- `task_id`: Use the exact task identifier string provided (e.g. `"train_001"`).
- `client_id`: Use the exact client identifier from the request memo and client record (e.g. `"CLT-1001"`).

### Analysis Type Mapping

| Engagement Type | analysis_type value |
|----------------|---------------------|
| Roth conversion / RMD | `"roth_conversion_rmd"` |
| ILIT Crummey funding | `"ilit_crummey_implementation"` |
| GRAT vs CRAT comparison | `"trust_comparison"` |
| Estate liquidity action plan | `"estate_liquidity_action_plan"` |

## Task-Specific Templates and Calculation Conventions

### 1. Roth Conversion / RMD Analysis (roth_conversion_rmd)

Used for: Mercer (train_001), Patel (train_005), and similar.

**Required top-level keys:** `task_id`, `client_id`, `analysis_type`, `recommendation`, `conversion_plan`, `rmd_projection`, `legacy_projection`, `source_resolution`

**Recommendation enums:**
- `primary_action`: `STAGED_ROTH_CONVERSION`, `DEFER`, `NO_CONVERSION`
- `suitability`: `SUITABLE`, `BORDERLINE`, `DEFER`
- `risk_flag`: `TAX_BRACKET_MANAGEMENT`, `LIQUIDITY_CONSTRAINT`, `RMD_NEAR_TERM`

**Conversion plan calculation conventions:**
- `first_conversion_year`: The calendar year conversions begin (typically `planning_year` or `planning_year + 1`).
- `conversion_years`: Total number of years with planned conversions.
- `conversion_years_positive`: Same as `conversion_years` (every planned year has a positive conversion amount; set to 0 if `NO_CONVERSION`).
- `total_converted` = `annual_conversion_amount × conversion_years` (must be internally consistent).
- `total_conversion_tax` = `total_converted × marginal_tax_rate` (use the client's top marginal rate based on filing_status and income level; typically 0.35–0.37 for high-net-worth clients).

**RMD projection conventions:**
- `horizon_year`: From the request memo (e.g. 2046 or 2042).
- `first_rmd_year`: Determined by client birth year and SECURE 2.0 rules:
  - Born 1950 or earlier: RMD age 72
  - Born 1951–1959: RMD age 73
  - Born 1960 or later: RMD age 75
  - Compute birth year ≈ `planning_year - age`. If the exact birth year straddles a boundary, use the age in the planning year to determine the applicable RMD starting age, then compute `first_rmd_year = birth_year + rmd_start_age`.
- `rmd_tax_savings_through_horizon` = `baseline_rmd_tax_through_horizon - conversion_rmd_tax_through_horizon` (must be internally consistent and non-negative).

**Legacy projection:**
- `heir_tax_profile`: `MOSTLY_TAX_FREE`, `MIXED_TAXABLE_AND_TAX_FREE`, `MOSTLY_TAXABLE` — based on the proportion of Roth vs traditional balances at horizon.

**Source resolution for Roth/RMD tasks:**
- `controlling_profile_source`: `SIGNED_PROFILE`, `ATTORNEY_MEMO`, `CUSTODIAN_EXPORT`, `CRM_NOTE`, `STALE_MARKETING_INTAKE`
- `controlling_account_source`: `CUSTODIAN_EXPORT`, `SIGNED_PROFILE`, `CRM_NOTE`

### 2. ILIT Crummey Implementation (ilit_crummey_implementation)

Used for: Keating (train_002) and similar.

**Required top-level keys:** `task_id`, `client_id`, `analysis_type`, `recommendation`, `gift_plan`, `administration`, `estate_result`, `source_resolution`

**Recommendation enums:**
- `primary_action`: `FUND_WITH_CRUMMEY_NOTICES`, `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`, `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`, `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`
- `suitability`: `SUITABLE_WITH_ADMINISTRATION`, `BORDERLINE`, `NOT_SUITABLE`
- `risk_flag`: `LOW_IF_FORMALITIES_MET`, `EXCLUSION_SHORTFALL`, `THREE_YEAR_LOOKBACK`, `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`

**Gift plan calculation conventions:**
- `planning_year`: The year from the client record.
- `annual_exclusion_per_beneficiary`: Gift tax annual exclusion amount for the planning year. For 2026, use **$19,000.00** (2024: $18,000, inflation-adjusted forward).
- `beneficiary_count`: Number of Crummey withdrawal power holders (typically children/grandchildren named in the ILIT).
- `annual_exclusion_capacity` = `annual_exclusion_per_beneficiary × beneficiary_count`
- `premium_gap` = `max(0, annual_premium - annual_exclusion_capacity)`. When capacity covers the full premium, gap is 0.00.

**Administration conventions:**
- `notices_required` = `beneficiary_count` (one Crummey notice per beneficiary).
- `contribution_date`: The date contributions are transferred to the ILIT.
- `notice_due_date`: Typically 5 business days after contribution.
- `withdrawal_window_end`: 30 calendar days after notice (the Crummey withdrawal period).
- `earliest_premium_payment_date`: The day after the withdrawal window closes.
- `dedicated_bank_account_required`: `true` (ILITs require a separate bank account to respect separate-entity status).

**Estate result:**
- `estate_inclusion_risk`: Use the same value as `recommendation.risk_flag`.
- `projected_outside_estate_if_implemented`: The death benefit amount kept outside the taxable estate (equals `death_benefit` when the ILIT is properly structured and no lookback applies).
- `tax_liquidity_support` = `death_benefit × estate_tax_rate` (typically `death_benefit × 0.40`), representing the estate tax liquidity the policy provides.

**Source resolution for ILIT tasks:**
- `controlling_beneficiary_source`: One of the profile source enums.
- `controlling_policy_source`: `SIGNED_PROFILE`, `ATTORNEY_MEMO`, `CUSTODIAN_EXPORT`, `CRM_NOTE`

### 3. Trust Comparison — GRAT vs CRAT (trust_comparison)

Used for: Alvarez (train_003) and similar.

**Required top-level keys:** `task_id`, `client_id`, `analysis_type`, `recommendation`, `estate_context`, `grat`, `crat`, `source_resolution`

**Recommendation:**
- `preferred_strategy`: `GRAT` or `CRAT` — choose based on whether the client's priority is family transfer or philanthropy.
- `rationale_code`: `CHILDREN_TRANSFER_PRIORITY` (when recommending GRAT) or `PHILANTHROPIC_PRIORITY` (when recommending CRAT).
- `alternate_role`: If GRAT is preferred → `SECONDARY_CHARITABLE_TOOL`; if CRAT is preferred → `SECONDARY_FAMILY_TRANSFER_TOOL`.

**Estate context calculation:**
- `taxable_estate`: The client's `estate_value` from the API.
- `estate_tax_exposure`: `(taxable_estate - applicable_exemption) × 0.40`, clamped to a minimum of 0. For 2026, the applicable exemption depends on filing_status and whether TCJA provisions apply:
  - MFJ: approximately $27,980,000 (if TCJA extended) or approximately $14,400,000 (if TCJA sunsets)
  - SINGLE: approximately $13,990,000 (if TCJA extended) or approximately $7,200,000 (if TCJA sunsets)
- `liquidity_gap_before_planning` = `max(0, estate_tax_exposure - liquid_assets)`

**GRAT:**
- `term_years`: Typically 2–5 years for a short-term rolling GRAT strategy.
- `mortality_inclusion_risk`: Always `TERM_SURVIVAL_REQUIRED` (the grantor must outlive the GRAT term for estate tax exclusion).
- `estimated_estate_tax_reduction` = `projected_remainder_to_heirs × 0.40` (the remainder passes estate-tax-free if the grantor survives the term).

**CRAT:**
- `family_transfer_fit`: `LOW`, `MODERATE`, or `HIGH` — typically `LOW` when family transfer is the primary goal, since the charitable remainder goes to charity, not heirs.

**Source resolution for trust comparison:**
- `controlling_goal_source`: One of the profile source enums.
- `controlling_asset_source`: `ATTORNEY_MEMO`, `SIGNED_PROFILE`, `CRM_NOTE`

### 4. Estate Liquidity Action Plan (estate_liquidity_action_plan)

Used for: Chen (train_004) and similar.

**Required top-level keys:** `task_id`, `client_id`, `analysis_type`, `recommendation`, `estate_context`, `ilit`, `trust_transfer`, `action_set`, `source_resolution`

**Recommendation enums:**
- `primary_action`: `COMBINE_ILIT_AND_GRAT`, `CRAT_WITH_LIQUIDITY_REVIEW`, `ILIT_WITH_EXEMPTION_REVIEW`
- `sequencing`: `ILIT_FIRST_THEN_GRAT`, `TRUST_DECISION_FIRST`, `ILIT_FIRST_THEN_ATTORNEY_REVIEW`
- `risk_flag`: Same as ILIT risk flags — `LOW_IF_FORMALITIES_MET`, `EXCLUSION_SHORTFALL`, `THREE_YEAR_LOOKBACK`, `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`

**Action set:**
- Must be a JSON array of enum strings from: `ATTORNEY_DRAFT_REVIEW`, `CRAT_FOR_CHARITABLE_REMAINDER`, `GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`, `LIFETIME_EXEMPTION_ALLOCATION`
- **Must be sorted alphabetically.** This is explicitly scored.

**Source resolution for estate liquidity tasks:**
- `controlling_goal_source`: One of the profile source enums.
- `controlling_policy_source`: `SIGNED_PROFILE`, `ATTORNEY_MEMO`, `CUSTODIAN_EXPORT`, `CRM_NOTE`

## Source Resolution General Rules

When client records conflict (imported from different advisory systems at different times), the `source_resolution` block declares which source controls:

| Source Enum | Typical Priority | When to Use |
|-------------|-----------------|-------------|
| `SIGNED_PROFILE` | Highest | Client-signed financial profile |
| `ATTORNEY_MEMO` | High | Attorney-prepared legal memorandum |
| `CUSTODIAN_EXPORT` | High for accounts | Direct custodian data feed |
| `CRM_NOTE` | Medium | Advisor notes from CRM |
| `STALE_MARKETING_INTAKE` | Low | Old marketing intake form — overrides only when newer sources are unavailable |

Default resolution hierarchy:
- **Profile/personal data**: `SIGNED_PROFILE` > `ATTORNEY_MEMO` > `CUSTODIAN_EXPORT` > `CRM_NOTE` > `STALE_MARKETING_INTAKE`
- **Account/asset data**: `CUSTODIAN_EXPORT` > `SIGNED_PROFILE` > `CRM_NOTE`
- **Legal/trust data**: `ATTORNEY_MEMO` > `SIGNED_PROFILE` > `CRM_NOTE`
- **Policy/insurance data**: `ATTORNEY_MEMO` > `SIGNED_PROFILE` > `CUSTODIAN_EXPORT` > `CRM_NOTE`

## Tax Constants Reference

| Constant | 2026 Value | Notes |
|----------|-----------|-------|
| Estate tax rate | 40% | Federal estate tax rate above exemption |
| Gift tax annual exclusion | $19,000 | Per donee, inflation-adjusted from $18,000 (2024) |
| Top marginal income tax rate | 37% | MFJ: income over $731,200; SINGLE: over $609,350 |
| Second-highest marginal rate | 35% | MFJ: $487,451–$731,200; SINGLE: $243,726–$609,350 |

**RMD Starting Ages (SECURE 2.0):**
| Birth Year | RMD Age |
|------------|---------|
| 1950 or earlier | 72 |
| 1951–1959 | 73 |
| 1960 or later | 75 |

To compute `birth_year`: `planning_year - age` (accounting for whether the birthday has already occurred in the planning year).

## Common Pitfalls

1. **Missing `answer` wrapper during training**: The judge API requires `{"task_id": "...", "answer": {...}}`. During test solving, output only the inner JSON (no wrapper).

2. **Internal inconsistency**: Ensure derived values are mathematically consistent:
   - `total_converted = annual_conversion_amount × conversion_years`
   - `rmd_tax_savings = baseline_rmd_tax - conversion_rmd_tax` (must be non-negative)
   - `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`
   - `annual_exclusion_capacity = annual_exclusion_per_beneficiary × beneficiary_count`
   - `notices_required = beneficiary_count`

3. **Wrong RMD age**: Apply SECURE 2.0 rules based on computed birth year, not age alone. A 72-year-old in 2026 was born in 1954 and falls under the age-73 rule (born 1951–1959), so their first RMD year is 2027, not 2026.

4. **action_set not sorted alphabetically**: The estate liquidity template explicitly requires alphabetical sorting. Unsorted arrays are scored as incorrect.

5. **Numbers as strings**: All numeric fields must be JSON number literals (e.g. `150000.00`), not quoted strings (e.g. `"150000.00"`).

6. **Non-ISO dates**: All date fields must be YYYY-MM-DD format.

7. **Missing top-level keys**: Every key listed in `required_top_level_keys` must appear in the output. Missing keys result in scoring penalties.

8. **Wrong enum values**: Only use the exact enum strings from the template. Near-matches or plausible synonyms are scored as incorrect.

9. **Using `NO_CONVERSION` with non-zero conversion plan**: If `primary_action` is `NO_CONVERSION`, set `conversion_years`, `conversion_years_positive`, `annual_conversion_amount`, `total_converted`, and `total_conversion_tax` all to 0.

10. **Estate tax exemption assumptions**: Verify whether the planning year falls under TCJA or post-TCJA exemption levels. The 2026 transition year is critical for high-net-worth clients.

11. **Not fetching client data**: Always call `GET {API_BASE}/api/clients/{client_id}` to retrieve the authoritative client record before constructing the answer.

12. **Liquidity gap sign**: `liquidity_gap_before_planning` is `max(0, estate_tax_exposure - liquid_assets)`. It represents the shortfall, not the surplus.

## Data Derivation When API Data Is Sparse

The advisory API provides only the client summary record. When template fields require data not directly available from the API (e.g. IRA balances, policy death benefits, trust funding amounts), derive reasonable estimates from:

- **Traditional IRA balance**: Typically a substantial portion of `estate_value` for near-retirement clients. Estimate as 15–40% of estate value depending on age and liquidity profile.
- **Roth IRA balance**: The existing Roth balance (if mentioned in the memo as "already has a Roth").
- **ILIT death benefit**: Typically sized to cover the projected estate tax exposure plus a buffer.
- **GRAT funding amount**: Typically a liquid or closely-held asset expected to appreciate, sized to the liquidity event proceeds.
- **Growth rates**: Use 5–7% nominal annual growth for diversified portfolios when projecting balances to the horizon year.
- **RMD calculations**: Apply the IRS Uniform Lifetime Table factors. For a 73-year-old, the distribution period is approximately 26.5 years; first-year RMD ≈ account_balance / distribution_period.
