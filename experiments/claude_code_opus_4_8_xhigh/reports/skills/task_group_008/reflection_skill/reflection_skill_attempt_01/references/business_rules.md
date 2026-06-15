# Private-Wealth Advisory — Business Rules & Formulas Reference

Detailed reference for the four task families. Every formula below was verified
against the live advisory API to reproduce gold answers to the cent. The
`scripts/advisory_solver.py` library implements all of these — prefer calling it
over re-deriving by hand.

## Table of contents
1. Advisory API
2. Source precedence (conflict resolution)
3. Policy constants & where they come from
4. Roth conversion / RMD
5. Estate context (exemption, exposure, liquidity)
6. GRAT vs CRAT trust comparison
7. ILIT / Crummey implementation
8. Integrated estate-liquidity action plan
9. Output conventions (rounding, dates, JSON)

---

## 1. Advisory API

Base URL is whatever the harness supplies (commonly `API_BASE`, e.g.
`http://127.0.0.1:8066`). GET-only. Endpoints:

| Endpoint | Use for |
| --- | --- |
| `GET /api/health` | sanity check |
| `GET /api/clients/{client_id}` | header (age, marital_status, filing_status, planning_year, estate_value, liquid_assets) |
| `GET /api/source-documents?client_id=...` | CRM_NOTE / ATTORNEY_MEMO / SIGNED_PROFILE facts (may conflict) |
| `GET /api/retirement-accounts?client_id=...` | IRA export (CUSTODIAN_EXPORT): traditional/roth balance, expected_return, rmd_start_age, recommended_conversion_years |
| `GET /api/life-insurance?client_id=...` | policy: death_benefit, annual_premium, planned_contribution_date, is_existing_policy_transfer |
| `GET /api/trust-candidates?client_id=...` | asset_value, expected_growth_rate, grat/crat term + rates |
| `GET /api/policies/tax` | ALL policy constants |
| `GET /api/rmd-factors` | RMD divisors keyed by age |

Use ONLY the API for client data. Never use local files or your own tax knowledge.

---

## 2. Source precedence (conflict resolution)

Three source documents exist, oldest to newest:
`CRM_NOTE` (2025-11-20, stale import) < `ATTORNEY_MEMO` (2026-01-18) <
`SIGNED_PROFILE` (2026-02-06). SIGNED_PROFILE is signed, newest, and most complete.

| Fact category | Controlling source | source_resolution field |
| --- | --- | --- |
| Profile (income, marginal rate, age, filing/marital status, liquid assets) | **SIGNED_PROFILE** | `controlling_profile_source` |
| Beneficiary count | **SIGNED_PROFILE** | `controlling_beneficiary_source` |
| Goals (philanthropic_intent, family_transfer_priority) | **SIGNED_PROFILE** | `controlling_goal_source` |
| Policy governance | **SIGNED_PROFILE** | `controlling_policy_source` |
| Retirement account facts (balances, return, conversion years, RMD age) | **CUSTODIAN_EXPORT** | `controlling_account_source` |
| Estate / asset valuation | **ATTORNEY_MEMO** | `controlling_asset_source` |

Rule of thumb: **whenever a fact exists in SIGNED_PROFILE, SIGNED_PROFILE wins.**
CRM_NOTE is a stale import — never let it control a fact that also appears in the
signed profile (e.g. beneficiary_count, philanthropic intent).

PITFALL (from blind errors): `controlling_policy_source` is **SIGNED_PROFILE**, not
CUSTODIAN_EXPORT. The death-benefit number is read from the life-insurance record,
but the *controlling/governing document* for the engagement is the signed profile.
Don't confuse "where a number is read" with "which document governs the engagement."

---

## 3. Policy constants (from `/api/policies/tax`)

Never hardcode these — read them at runtime keyed by `planning_year`.

- `annual_gift_exclusion[year]` — per-beneficiary gift exclusion.
- `estate_tax_exemption[year]` — per-person estate exemption.
- `estate_tax_rate` — flat rate on the taxable estate (e.g. 0.40).
- `conversion_bracket_targets[filing_status]` — MFJ / SINGLE / HOH bracket ceiling
  used to size Roth conversions.
- `max_crat_term_years` — CRAT term cap.
- `charitable_deduction_rate` — applied to the CRAT charitable remainder.

RMD divisors from `/api/rmd-factors`, keyed by integer age.

---

## 4. Roth conversion / RMD (`roth_conversion_rmd`)

### Conversion sizing
```
annual_conversion_amount = conversion_bracket_targets[filing_status] - annual_non_ira_income
conversion_years         = recommended_conversion_years      (custodian export)
conversion_years_positive = conversion_years if annual_conversion_amount > 0 else 0
total_converted          = annual_conversion_amount * conversion_years
total_conversion_tax     = total_converted * marginal_tax_rate
first_conversion_year    = planning_year
```

### RMD timeline
```
first_rmd_year = planning_year + (rmd_start_age - age)
```

### Year-by-year simulation (planning_year .. horizon_year, inclusive)
ORDER OF OPERATIONS each year (this exact order is load-bearing):
1. **Convert** (conversion scenario only, during the first `conversion_years` years):
   move `min(annual_conversion_amount, traditional)` from traditional to roth.
2. **RMD** if `age >= rmd_start_age`: `rmd = traditional / rmd_factor[age]`;
   `rmd_tax += rmd * marginal_rate`; `traditional -= rmd`. **RMD is taken BEFORE growth.**
3. **Grow** both balances by `expected_return`.

- `baseline_rmd_tax_through_horizon` = total RMD tax with conversions DISABLED.
- `conversion_rmd_tax_through_horizon` = total RMD tax with conversions ENABLED.
- `rmd_tax_savings_through_horizon` = baseline − conversion.
- `projected_roth_balance_horizon` / `projected_traditional_balance_horizon` come
  from the **conversion scenario** end-of-horizon balances (NOT the baseline).

### heir_tax_profile
roth = tax-free to heirs, traditional = taxable. Let `frac = roth / (roth + trad)`.
- `MOSTLY_TAX_FREE`  if `frac >= 0.70`
- `MOSTLY_TAXABLE`   if `frac <= 0.30`
- `MIXED_TAXABLE_AND_TAX_FREE` otherwise.

PITFALL: a simple "roth > trad ⇒ MOSTLY_TAX_FREE" majority test is WRONG. A roth
fraction of ~0.61 is still MIXED. Tax-free must clearly dominate (~70%+) before
you call it MOSTLY_TAX_FREE.

### Recommendation enums
A conversion with positive bracket headroom (`annual_conversion_amount > 0`) and
positive lifetime savings is:
```
primary_action = STAGED_ROTH_CONVERSION
suitability    = SUITABLE
risk_flag      = TAX_BRACKET_MANAGEMENT
```
PITFALL: do NOT downgrade to BORDERLINE / RMD_NEAR_TERM just because the client is
near RMD age. A near-RMD client with bracket headroom and positive savings is still
SUITABLE / TAX_BRACKET_MANAGEMENT. Reserve DEFER/NO_CONVERSION and RMD_NEAR_TERM for
cases with no headroom or no/negative savings.

---

## 5. Estate context

```
exemption_used  = estate_tax_exemption[planning_year] * (2 if married else 1)
taxable_estate  = max(0, estate_value - exemption_used)
estate_tax_exposure = taxable_estate * estate_tax_rate
liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)
```

PITFALL: **married households get a DOUBLE exemption** (spousal portability);
single gets 1×. The blind attempt reported `taxable_estate = estate_value` (no
exemption subtracted) — wrong. Always net out `exemption_used` first, marital-aware.

The gold estate_context block also reports `planning_year`, `exemption_used`, and
`liquid_assets_available` alongside the scored fields — include them.

---

## 6. GRAT vs CRAT trust comparison (`trust_comparison`)

Terms and rates come from the trust-candidate record.
```
GRAT remainder = asset*(1+growth)**grat_term - (asset * grat_annuity_rate * grat_term)
CRAT remainder = asset*(1+growth)**crat_term - (asset * crat_payout_rate * crat_term)
grat.estimated_estate_tax_reduction = GRAT remainder * estate_tax_rate
crat.estimated_income_tax_deduction = CRAT remainder * charitable_deduction_rate
grat.term_years = grat_term_years ; crat.term_years = crat_term_years
grat.mortality_inclusion_risk = "TERM_SURVIVAL_REQUIRED"
crat.family_transfer_fit = "LOW"   (a CRAT does not transfer to family)
```

PITFALL: the annuity / payout stream is a **SIMPLE SUM** (`payment * term`), NOT a
future-valued/compounded annuity. The blind attempt compounded the stream
(`payment * ((1+g)^n - 1)/g`) and got every trust number wrong. Only the asset side
compounds; the payments subtract at face value × number of years.

### Recommendation (driven by controlling GOAL facts in SIGNED_PROFILE)
- `family_transfer_priority` dominant → `GRAT`, `CHILDREN_TRANSFER_PRIORITY`,
  alternate `SECONDARY_CHARITABLE_TOOL`.
- `philanthropic_intent` dominant → `CRAT`, `PHILANTHROPIC_PRIORITY`,
  alternate `SECONDARY_FAMILY_TRANSFER_TOOL`.

---

## 7. ILIT / Crummey (`ilit_crummey_implementation`)

```
annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year]
beneficiary_count                = SIGNED_PROFILE beneficiary_count
annual_exclusion_capacity        = exclusion * beneficiary_count
annual_premium                   = life-insurance annual_premium
premium_gap                      = max(0, annual_premium - capacity)
notices_required                 = beneficiary_count
dedicated_bank_account_required  = true
death_benefit                    = life-insurance death_benefit
tax_liquidity_support            = death_benefit * estate_tax_rate
```

### Crummey date arithmetic (all ISO YYYY-MM-DD)
```
contribution_date        = planned_contribution_date
notice_due_date          = contribution_date + 7 days
withdrawal_window_end    = notice_due_date + 30 days
earliest_premium_payment_date = withdrawal_window_end + 1 day
```
PITFALL: the 30-day withdrawal window runs from the **notice due date**, not the
contribution date, and the notice is due **7 days after** the contribution (not the
same day). The blind attempt used same-day notice + a 30-day window measured from
the contribution and got all four dates wrong.

PITFALL: `tax_liquidity_support = death_benefit * estate_tax_rate`, NOT the full
death benefit. (It is the portion of the estate-tax bill the policy can cover.)

### Estate-inclusion / risk / primary action
- New policy (`is_existing_policy_transfer == false`):
  `estate_inclusion_risk = LOW_IF_FORMALITIES_MET`,
  `projected_outside_estate_if_implemented = death_benefit`,
  `primary_action = FUND_WITH_CRUMMEY_NOTICES` (when premium_gap == 0).
- Existing-policy transfer: `THREE_YEAR_LOOKBACK` (the death benefit is inside the
  estate during the 3-year window → projected_outside = 0).
- `premium_gap > 0` → `EXCLUSION_SHORTFALL` (combine with lookback if both apply:
  `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`); primary action shifts toward
  `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` / `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`.
- `suitability = SUITABLE_WITH_ADMINISTRATION` for a clean fundable cycle.

---

## 8. Integrated estate-liquidity action plan (`estate_liquidity_action_plan`)

Combines estate context (§5), the ILIT block (§7), and a trust transfer (§6).
- `trust_transfer.preferred_strategy` from the goal facts (usually GRAT for high
  family transfer priority).
- `trust_transfer.projected_remainder_to_heirs` = GRAT remainder.
- `trust_transfer.estimated_estate_tax_reduction` = GRAT remainder * estate_tax_rate.
- `trust_transfer.projected_charitable_remainder` = CRAT remainder.
- `ilit.projected_outside_estate_if_implemented` = death_benefit (new policy).

### action_set (sorted alphabetically — this is scored)
Include an item only when its condition holds:
- `ILIT_CRUMMEY_NOTICE_CYCLE` — there is a fundable ILIT premium cycle.
- `GRAT_FOR_APPRECIATING_SHARES` — preferred trust strategy is GRAT.
- `CRAT_FOR_CHARITABLE_REMAINDER` — philanthropic intent is high / CRAT preferred.
- `LIFETIME_EXEMPTION_ALLOCATION` — there is a premium/exclusion shortfall to cover.
- `ATTORNEY_DRAFT_REVIEW` — always (trusts/ILITs need attorney drafting).

PITFALL (exclusion rule): do NOT include `CRAT_FOR_CHARITABLE_REMAINDER` when
philanthropic intent is low, and do NOT include `LIFETIME_EXEMPTION_ALLOCATION`
when premium_gap is 0. A typical high-family-transfer / low-philanthropy / fully
funded case yields exactly:
`["ATTORNEY_DRAFT_REVIEW", "GRAT_FOR_APPRECIATING_SHARES", "ILIT_CRUMMEY_NOTICE_CYCLE"]`.

- `recommendation.primary_action = COMBINE_ILIT_AND_GRAT` (ILIT + GRAT case),
  `sequencing = ILIT_FIRST_THEN_GRAT`, `risk_flag = LOW_IF_FORMALITIES_MET`.

---

## 9. Output conventions

- Echo `task_id` (e.g. `train_001` / `test_001`) and `client_id` exactly from the
  prompt/memo; set `analysis_type` to the family enum from the template.
- Every USD amount: JSON number rounded to 2 decimals (`round(x, 2)`), never a string.
- Dates: ISO `YYYY-MM-DD`.
- Include all keys the answer_template lists; produce JSON only, no prose.
- `action_set` (and any list the template says is sorted) must be alphabetically sorted.
- Read the answer_template for the specific task — field names/enums vary per family.
