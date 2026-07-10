# Private Wealth Advisory — Structured Planning Output Generator

## Overview

This skill produces structured JSON planning outputs for a private wealth advisory API. The advisory environment exposes client records, retirement accounts, life insurance policies, trust candidates, source documents with conflicting data, and IRS RMD life-expectancy factors. The task is to reconcile conflicting sources, compute tax-aware projections, and emit a JSON object that conforms to a supplied answer template.

## API Usage

### Base URL
Use the harness-supplied `API_BASE` (typically `http://<host>:8008`). Do **not** construct localhost URLs.

### Endpoints

| Method | Path | Query params | Returns |
|--------|------|-------------|---------|
| GET | `/api/health` | — | `{"ok":true,"service":"private-wealth-advisory"}` |
| GET | `/api/clients` | — | Array of all client records |
| GET | `/api/clients/{client_id}` | — | Single client record |
| GET | `/api/retirement-accounts` | `?client_id=CLT-XXXX` | Retirement account(s) for client |
| GET | `/api/life-insurance` | `?client_id=CLT-XXXX` | Life insurance policy for client |
| GET | `/api/trust-candidates` | `?client_id=CLT-XXXX` | Trust candidate (GRAT/CRAT inputs) for client |
| GET | `/api/source-documents` | `?client_id=CLT-XXXX` | All source documents for client |
| GET | `/api/rmd-factors` | — | Map of age (string) → RMD divisor (float), ages 73–99 |

**Pattern**: Always use the query-parameter form `?client_id=CLT-XXXX` when fetching per-client resources rather than filtering client-side. Every data endpoint supports it. The sub-path form `/api/clients/{id}/accounts` etc. is **not reliable** — use the query-parameter form on the dedicated resource endpoint instead.

### HTTP client
Use `curl -s` with the base URL. Responses are JSON. The server runs Python `BaseHTTP/0.6`; only GET is supported (POST/OPTIONS/HEAD return errors).

---

## Data Model Reference

### Client Record (`/api/clients` and `/api/clients/{id}`)
```
client_id       : string   "CLT-XXXX" (always uppercase CLT, dash, digits)
household_name  : string
age             : integer  (primary client age as of planning_year)
marital_status  : "married" | "single"
filing_status   : "MFJ" | "SINGLE" | "HOH"
planning_year   : integer  (2026 for the current train/test cohort)
estate_value    : number   gross taxable estate in USD
liquid_assets   : number   cash + marketable securities in USD
record_status   : "active" | "monitoring"
advisor_team    : string
```
The numeric `client_id` suffix always matches the task's client (e.g., task for CLT-1004 → client_id 1004).

### Retirement Account (`/api/retirement-accounts`)
```
account_id                 : string
client_id                  : string
source_type                : "CUSTODIAN_EXPORT" (the authoritative account source)
traditional_balance        : number   pre-tax IRA/401(k) balance in USD
roth_balance               : number   Roth IRA balance in USD
expected_return            : number   annual rate of return (decimal, e.g. 0.065)
rmd_start_age              : integer  age when RMDs begin (73 per SECURE 2.0)
recommended_conversion_years : integer  suggested number of staged conversion years
```
- One record per client; all seen records are `CUSTODIAN_EXPORT`.
- `rmd_start_age` is 73 for all observed clients (consistent with SECURE 2.0 Act).
- When the SIGNED_PROFILE or CRM mentions account data, **CUSTODIAN_EXPORT still controls** account balances — it is the direct custodian feed.

### Life Insurance (`/api/life-insurance`)
```
policy_id                  : string   "LIFE-CLT-XXXX"
client_id                  : string
proposed_owner             : "ILIT" (all observed policies)
death_benefit              : number   face amount in USD
annual_premium             : number   annual premium in USD
planned_contribution_date  : ISO date "YYYY-MM-DD"
is_existing_policy_transfer: boolean  true → three-year lookback risk applies
```
- When `is_existing_policy_transfer` is `false`, this is a **new policy** — no lookback concern, standard Crummey administration applies.
- When `true`, the policy was transferred from the insured within the last three years → `THREE_YEAR_LOOKBACK` risk flag; estate inclusion risk is elevated.

### Trust Candidate (`/api/trust-candidates`)
```
trust_case_id        : string   "TRUST-CLT-XXXX"
client_id            : string
asset_value          : number   value of assets to place in trust, USD
expected_growth_rate : number   annual appreciation rate (decimal)
grat_term_years      : integer  GRAT term (2–10 years range in practice)
grat_annuity_rate    : number   IRS §7520 rate proxy for the GRAT annuity
crat_term_years      : integer  CRAT term (always 20 in observed data)
crat_payout_rate     : number   CRAT annual payout rate (always 0.055 = 5.5%)
```
- GRAT remainder ≈ `asset_value × (1 + growth)^years − annuity_stream`, where the annuity is calculated as a level-payment amortization using the `grat_annuity_rate` (the §7520 hurdle). The GRAT only delivers a remainder to heirs if growth exceeds the hurdle rate.
- CRAT charitable remainder = present value of the remainder interest after the term, computed from `crat_payout_rate` and `crat_term_years`. CRAT provides an upfront income-tax deduction based on the charitable remainder interest.
- `grat.mortality_inclusion_risk` is always `"TERM_SURVIVAL_REQUIRED"` — if the grantor dies during the GRAT term, assets are pulled back into the estate.

### Source Documents (`/api/source-documents`)
```
document_id   : string   "DOC-CLT-XXXX-{SRCTYPE}"
client_id     : string
source_type   : "SIGNED_PROFILE" | "ATTORNEY_MEMO" | "CRM_NOTE" | "CUSTODIAN_EXPORT" | "STALE_MARKETING_INTAKE"
effective_date: ISO date "YYYY-MM-DD"
title         : string
facts         : object   (keys vary by source_type; see below)
```

**Fact keys observed across documents:**
- `age`, `planning_year`, `filing_status`, `marital_status`
- `estate_value`, `liquid_assets`
- `annual_non_ira_income` — total household income excluding IRA distributions
- `marginal_tax_rate` — federal marginal rate (decimal: 0.32, 0.35, 0.37)
- `beneficiary_count` — number of ILIT/gift beneficiaries
- `philanthropic_intent` — `"low"` | `"moderate"` | `"high"`
- `family_transfer_priority` — `"low"` | `"moderate"` | `"high"`

**Typical document effective dates (observed pattern):**
- `CRM_NOTE`: 2025-11-20 (oldest, imported from prior CRM — frequently stale)
- `ATTORNEY_MEMO`: 2026-01-18 (intermediate)
- `SIGNED_PROFILE`: 2026-02-06 (newest, client-signed — most authoritative)

---

## Source Resolution Rules

### Authority Hierarchy (most → least authoritative)
```
SIGNED_PROFILE > ATTORNEY_MEMO > CUSTODIAN_EXPORT > CRM_NOTE > STALE_MARKETING_INTAKE
```

### Field-by-field controlling source selection

| Field category | Controlling source | Rationale |
|---|---|---|
| Demographics (age, filing_status, marital_status) | `SIGNED_PROFILE` | Most recent client-confirmed data |
| Income (annual_non_ira_income) | `SIGNED_PROFILE` | Client-confirmed; CRM values are stale |
| marginal_tax_rate | `SIGNED_PROFILE` | Only present in SIGNED_PROFILE |
| beneficiary_count | `SIGNED_PROFILE` | Attorney memo and CRM may have different counts |
| estate_value, liquid_assets | `SIGNED_PROFILE` | Matches client record on `/api/clients` |
| family_transfer_priority | `ATTORNEY_MEMO` or `SIGNED_PROFILE` | Use the more recent if they conflict; both usually agree on `"high"` |
| philanthropic_intent | `SIGNED_PROFILE` | CRM often says `"moderate"` but signed profile is authoritative |
| Account balances (traditional_balance, roth_balance) | `CUSTODIAN_EXPORT` | Direct custodian feed; only source for account data |
| Policy data (death_benefit, annual_premium) | `/api/life-insurance` endpoint | Single source of truth |
| Trust parameters (asset_value, growth, terms) | `/api/trust-candidates` endpoint | Single source of truth |

### source_resolution output fields
- `controlling_profile_source`: nearly always `SIGNED_PROFILE` (most recent, client-signed)
- `controlling_account_source`: always `CUSTODIAN_EXPORT` (direct feed, no other source)
- `controlling_goal_source`: `SIGNED_PROFILE` for philanthropic/family-transfer intent
- `controlling_beneficiary_source`: `SIGNED_PROFILE` for beneficiary_count
- `controlling_policy_source`: `SIGNED_PROFILE` if available, else `ATTORNEY_MEMO`
- `controlling_asset_source`: `ATTORNEY_MEMO` or `SIGNED_PROFILE` (estate/asset context)

### When sources conflict
1. Always prefer the source with the **most recent effective_date**.
2. If `CRM_NOTE` is the only source for a fact not present elsewhere, use it but flag as lower confidence.
3. `STALE_MARKETING_INTAKE` should **never** be selected as controlling — it is a pre-engagement marketing artifact.
4. When `SIGNED_PROFILE` and `ATTORNEY_MEMO` agree on a value, that value is doubly confirmed.

---

## Calculation Conventions

### General
- All USD amounts: JSON **numbers** (not strings), rounded to **2 decimal places** (cents).
- All dates: ISO 8601 **strings** `"YYYY-MM-DD"`.
- Years: JSON integers.
- Enum values: exactly as specified in the answer template (uppercase with underscores).
- `task_id`: set to the task identifier string (e.g., `"train_001"`, `"test_001"`).
- `client_id`: the stable `"CLT-XXXX"` identifier from the request memo.
- `analysis_type`: exactly matches the template's `required_top_level_keys` value.

### Roth Conversion & RMD (`analysis_type: roth_conversion_rmd`)

**Conversion plan:**
- `first_conversion_year` = `planning_year` (2026).
- `conversion_years` = `recommended_conversion_years` from the retirement account record.
- `conversion_years_positive` = `max(1, conversion_years)`. Always an integer ≥ 1.
- `annual_conversion_amount` = `traditional_balance / conversion_years`, rounded to cents.
- `total_converted` = `annual_conversion_amount × conversion_years` (should equal `traditional_balance` if evenly divided).
- `total_conversion_tax` = `total_converted × marginal_tax_rate` (simplified: all conversions taxed at the client's current marginal rate). Round to cents.

**RMD projection:**
- `horizon_year` = the planning horizon year from the request memo (e.g., 2046 for CLT-1001, 2042 for CLT-1005).
- `first_rmd_year` = year when client reaches `rmd_start_age` (age 73). Compute as: `planning_year + (rmd_start_age − age)`.
- **Baseline RMD tax** (`baseline_rmd_tax_through_horizon`): Project the traditional IRA balance forward each year without conversions, compute RMDs from `first_rmd_year` through `horizon_year`, sum the taxes on those RMDs at the client's marginal rate.
  - Growth: `balance_next = balance_current × (1 + expected_return) − rmd`
  - RMD for age A: `rmd = balance / rmd_factor[A]`
  - RMD tax for year Y: `rmd × marginal_tax_rate`
- **Conversion RMD tax** (`conversion_rmd_tax_through_horizon`): Same projection but the traditional balance is reduced by the annual conversion amount each year during the conversion window, then grows and faces RMDs on the smaller remaining balance.
  - During conversion years (1 through `conversion_years`): `balance_next = (balance_current − annual_conversion_amount) × (1 + expected_return)`
  - After conversion years: same growth as baseline but from the reduced base.
  - Roth grows tax-free: `roth_next = (roth_current + annual_conversion_amount) × (1 + expected_return)` during conversion years.
- `rmd_tax_savings_through_horizon` = `baseline_rmd_tax_through_horizon − conversion_rmd_tax_through_horizon`. This must be ≥ 0.

**Legacy projection:**
- `projected_roth_balance_horizon` = Roth balance at `horizon_year` (including converted amounts + growth).
- `projected_traditional_balance_horizon` = Traditional IRA balance at `horizon_year` after all conversions, growth, and RMDs.
- `heir_tax_profile`:
  - `"MOSTLY_TAX_FREE"` — if Roth balance > 70% of total retirement assets at horizon
  - `"MOSTLY_TAXABLE"` — if Traditional balance > 70%
  - `"MIXED_TAXABLE_AND_TAX_FREE"` — otherwise

**Recommendation logic:**
- `STAGED_ROTH_CONVERSION` — when `rmd_tax_savings_through_horizon > 0` and `conversion_years ≥ 1`.
- `DEFER` — when the client is very close to RMD age (age ≥ 71) AND the savings are marginal, or when liquidity would be strained by conversion taxes.
- `NO_CONVERSION` — when conversion produces no net benefit or negative savings.
- `suitability`:
  - `SUITABLE` — clear tax savings, reasonable conversion horizon.
  - `BORDERLINE` — small savings or near-RMD-age client.
  - `DEFER` — near-RMD where waiting may be better; liquidity constraint.
- `risk_flag`:
  - `TAX_BRACKET_MANAGEMENT` — large conversions could push into higher bracket.
  - `LIQUIDITY_CONSTRAINT` — conversion tax exceeds liquid_assets comfortably.
  - `RMD_NEAR_TERM` — client age ≥ 70 and first RMD within 3 years.

### ILIT Crummey (`analysis_type: ilit_crummey_implementation`)

**Gift plan:**
- `planning_year` = 2026.
- `annual_exclusion_per_beneficiary` = $19,000 (2026 IRS annual gift tax exclusion; verify against current-year IRS figure — use $19,000 for 2026 unless the environment provides a different value).
- `beneficiary_count` = from SIGNED_PROFILE facts.
- `annual_exclusion_capacity` = `annual_exclusion_per_beneficiary × beneficiary_count`. Round to cents.
- `annual_premium` = from `/api/life-insurance`.
- `premium_gap` = `annual_premium − annual_exclusion_capacity`. If negative or zero, Crummey withdrawals fully cover the premium (gap = 0.00). If positive, there is a shortfall.

**Administration dates:**
- `contribution_date` = `planned_contribution_date` from the life insurance record.
- `notice_due_date` = `contribution_date + 30 days`. Crummey notices must be sent within 30 days of contribution.
- `withdrawal_window_end` = `notice_due_date + 30 days`. Standard Crummey withdrawal right period.
- `earliest_premium_payment_date` = `withdrawal_window_end + 1 day`. Premium can only be paid after the withdrawal window closes.
- `notices_required` = `beneficiary_count`. One Crummey notice per beneficiary.
- `dedicated_bank_account_required` = `true` (ILITs need a separate trust checking account to respect formalities; always true for new ILIT implementations).

**Estate result:**
- `death_benefit` = from life insurance record.
- `estate_inclusion_risk`:
  - `LOW_IF_FORMALITIES_MET` — new policy, properly administered.
  - `EXCLUSION_SHORTFALL` — `premium_gap > 0` but no lookback.
  - `THREE_YEAR_LOOKBACK` — `is_existing_policy_transfer = true` but premium fully covered by exclusions.
  - `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` — both lookback AND shortfall.
- `projected_outside_estate_if_implemented` = `death_benefit` (ILIT removes the death benefit from the taxable estate if formalities are met). If there is lookback risk, this may be reduced or zero.
- `tax_liquidity_support` = `death_benefit` (the insurance proceeds provide estate tax liquidity).

**Recommendation logic:**
- `FUND_WITH_CRUMMEY_NOTICES` — new policy, premium fully covered by exclusion capacity.
- `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` — new policy but `premium_gap > 0`; use part of the lifetime gift/estate tax exemption to cover the gap.
- `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` — existing transfer outside the three-year window.
- `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` — existing transfer within three-year window; disclose risk and use exemption for any shortfall.
- `suitability`:
  - `SUITABLE_WITH_ADMINISTRATION` — new policy, formalities can be met.
  - `BORDERLINE` — minor gaps or documentation concerns.
  - `NOT_SUITABLE` — three-year lookback makes the ILIT largely ineffective for estate tax purposes.
- `risk_flag`: same enum as `estate_inclusion_risk`.

### GRAT vs CRAT (`analysis_type: trust_comparison`)

**Estate context:**
- `taxable_estate` = `estate_value` from the client record / SIGNED_PROFILE.
- Federal estate tax exemption (2026): $13,990,000 per individual; $27,980,000 for MFJ. (Use the 2026 inflation-adjusted unified credit amount.)
- Estate tax rate: 40% on amounts above the exemption.
- `estate_tax_exposure` = `max(0, taxable_estate − exemption) × 0.40`. For MFJ, use the MFJ exemption; for SINGLE/HOH, use the individual exemption.
- `liquidity_gap_before_planning` = `estate_tax_exposure − liquid_assets`. If negative (enough liquidity), set to 0.00.

**GRAT calculation:**
- `term_years` = `grat_term_years` from trust candidate.
- Annual annuity payment = `asset_value × grat_annuity_rate` (simplified level-payment model; the §7520 rate sets the hurdle).
- Projected asset value at end of term = `asset_value × (1 + expected_growth_rate)^term_years`.
- `projected_remainder_to_heirs` = `max(0, projected_terminal_value − sum_of_annuity_payments)`. This is the amount passing to heirs free of gift tax.
- `estimated_estate_tax_reduction` = `projected_remainder_to_heirs × 0.40` (assets removed from estate, assuming grantor survives the term).
- `mortality_inclusion_risk` = always `"TERM_SURVIVAL_REQUIRED"`.

**CRAT calculation:**
- `term_years` = `crat_term_years` from trust candidate.
- `projected_charitable_remainder` = present value of remainder after the payout term. Compute as: `asset_value / (1 + crat_payout_rate)^term_years` (simplified) or use the actuarial remainder factor implied by the payout rate and term.
  - Alternative: charitable remainder ≈ `asset_value × (1 − crat_payout_rate × term_years_adjusted)`. The IRS charitable remainder factor depends on the §7520 rate. For the 5.5% CRAT payout observed, compute the remainder interest accordingly.
- `estimated_income_tax_deduction` = `projected_charitable_remainder` (limited to 30% or 50% of AGI depending on the charity type, but for planning purposes report the full amount).
- `family_transfer_fit`: `"LOW"` | `"MODERATE"` | `"HIGH"` — based on how much value reaches family vs charity.
  - `"LOW"` — CRAT designed primarily for charity; family gets mainly the income stream.
  - `"MODERATE"` — balanced.
  - `"HIGH"` — the income stream provides meaningful family benefit while remainder goes to charity (wealth replacement trust scenario).

**Recommendation logic:**
- `preferred_strategy`:
  - `GRAT` — when `family_transfer_priority = "high"` AND `philanthropic_intent ∈ {"low", "moderate"}`.
  - `CRAT` — when `philanthropic_intent = "high"` OR when the client needs the upfront income-tax deduction.
- `rationale_code`:
  - `CHILDREN_TRANSFER_PRIORITY` — GRAT chosen because family transfer is the primary goal.
  - `PHILANTHROPIC_PRIORITY` — CRAT chosen because charitable intent is dominant.
- `alternate_role`:
  - `SECONDARY_CHARITABLE_TOOL` — when GRAT is primary, the CRAT can serve a secondary charitable purpose.
  - `SECONDARY_FAMILY_TRANSFER_TOOL` — when CRAT is primary, the GRAT can serve a secondary family transfer purpose.

### Estate Liquidity Action Plan (`analysis_type: estate_liquidity_action_plan`)

This combines ILIT analysis + trust transfer recommendation + an ordered action set.

- Use the same estate tax exposure and liquidity gap calculations as the trust comparison template.
- Use the same ILIT analysis as the Crummey template.
- `action_set`: A sorted (alphabetical) array of action enum strings. Select from:
  - `ATTORNEY_DRAFT_REVIEW` — always include; attorney must review all documents.
  - `CRAT_FOR_CHARITABLE_REMAINDER` — include if CRAT is a relevant strategy.
  - `GRAT_FOR_APPRECIATING_SHARES` — include if GRAT is a relevant strategy.
  - `ILIT_CRUMMEY_NOTICE_CYCLE` — include if ILIT is being implemented.
  - `LIFETIME_EXEMPTION_ALLOCATION` — include if premium_gap > 0 or estate tax exposure is significant.
- Sort alphabetically before output.

---

## Common Pitfalls

1. **CRM data is stale**: `CRM_NOTE` dates to 2025-11-20. Its `beneficiary_count` and `annual_non_ira_income` frequently differ from the `SIGNED_PROFILE`. Never use CRM values when a more recent source exists.

2. **Account source cannot be overridden**: Retirement account balances come from `CUSTODIAN_EXPORT` only. Even if a source document mentions different balances, the custodian feed controls.

3. **`conversion_years_positive` vs `conversion_years`**: These are separate fields. `conversion_years_positive` must be ≥ 1 even if `conversion_years` is 0. In observed data, `conversion_years` is always ≥ 1, so they typically have the same value.

4. **RMD factor lookup by age as string**: The `/api/rmd-factors` endpoint returns string keys (`"73"`, `"74"`, etc.), not integers. Use string coercion when looking up divisors.

5. **Beneficiary count is from SIGNED_PROFILE, not CRM**: CRM often has a different (stale) beneficiary_count. SIGNED_PROFILE controls.

6. **Estate tax exemption depends on filing status**: MFJ clients get the combined exemption (~$27.98M for 2026); SINGLE/HOH clients get the individual exemption (~$13.99M). Use current-year IRS inflation-adjusted figures.

7. **Premium gap can be zero or negative**: When `annual_exclusion_capacity ≥ annual_premium`, `premium_gap` = 0.00 (not negative). The Crummey exclusions fully cover the premium.

8. **`action_set` must be sorted alphabetically**: The template explicitly requires this. Java/ASCII sort order: `ATTORNEY_DRAFT_REVIEW` < `CRAT_FOR_CHARITABLE_REMAINDER` < `GRAT_FOR_APPRECIATING_SHARES` < `ILIT_CRUMMEY_NOTICE_CYCLE` < `LIFETIME_EXEMPTION_ALLOCATION`.

9. **Dates are ISO strings, numbers are JSON numbers**: Do not quote numbers. Do not use epoch or other date formats.

10. **`total_conversion_tax` is the tax ON the conversions, not the total tax bill**: It equals `total_converted × marginal_tax_rate` (simplified single-bracket model).

11. **Projection calculations must use the correct growth rate**: RMD projections use `expected_return` from the retirement account. GRAT projections use `expected_growth_rate` from the trust candidate. These are different rates.

12. **RMD projections for conversion scenario**: Remember to grow the Roth balance during conversion years and the traditional balance net of conversions. The converted amount is removed from traditional and added to Roth; both sides then compound.

13. **First RMD year**: For a client age A in planning_year P, with RMD start age S: `first_rmd_year = P + (S − A)`. The first RMD is taken in that calendar year based on the prior year-end balance.

14. **`projected_outside_estate_if_implemented` with lookback**: When `is_existing_policy_transfer = true`, the death benefit may be includible in the estate for three years from transfer. If within the three-year window, this field should be 0.00 (or a reduced amount reflecting partial inclusion risk).

15. **No tax constants endpoint**: Tax rates (marginal_tax_rate), estate exemptions, and gift tax exclusions are not served by a dedicated `/api/tax-constants` endpoint. The marginal_tax_rate comes from SIGNED_PROFILE facts. Estate tax exemption and gift exclusion amounts must use current-year IRS figures (2026 values).

---

## Workflow

1. **Read the request memo** (`input/payloads/request_memo.md`) to identify: `client_id`, engagement type, and any horizon year.
2. **Read the answer template** (`input/payloads/answer_template.json`) to identify: `required_top_level_keys`, field definitions, enum constraints, and ordering rules.
3. **Fetch all API data** for the client: client record, retirement account, life insurance, trust candidate, source documents.
4. **Resolve source conflicts**: Compare source documents by effective_date and source_type authority. Select controlling sources for each field category.
5. **Compute projections** according to the analysis_type, using the formulas above.
6. **Determine recommendation** based on the computed values and client priorities.
7. **Emit JSON**: A single JSON object, no prose outside it. Match the template exactly.

---

## 2026 IRS Reference Values

These are the current-law values for the 2026 planning year. Use unless the environment provides different constants:

| Parameter | Value | Notes |
|-----------|-------|-------|
| Federal estate tax rate | 40% | Flat rate above exemption |
| Individual estate tax exemption | $13,990,000 | 2026 inflation-adjusted |
| MFJ estate tax exemption | $27,980,000 | 2× individual |
| Annual gift tax exclusion (per donee) | $19,000 | 2026 inflation-adjusted |
| Top marginal income tax rate | 37% | For income over ~$626K (SINGLE) / ~$751K (MFJ) in 2026 |
| RMD start age | 73 | SECURE 2.0 Act (for those born 1951–1959) |
| §7520 rate (GRAT hurdle) | varies | Use `grat_annuity_rate` from trust candidate (observed range: 0.040–0.045) |
| Crummey withdrawal period | 30 days | Standard; notice_due_date = contribution + 30 days |
| Three-year lookback (IRC §2035) | 3 years | Policy transfers within 3 years of death are includible |
