# Private Wealth Advisory — Computation & Enum Reference

This is the detailed companion to `SKILL.md`. Every formula here was reverse-engineered
from the live API and verified to the cent against the worked training gold answers.
`scripts/advisory_lib.py` implements all of it and self-tests on startup
(`python3 scripts/advisory_lib.py` must print `OK`).

## Table of contents
1. Data sources & source resolution
2. Roth conversion + RMD (`roth_conversion_rmd`)
3. ILIT / Crummey (`ilit_crummey_implementation`)
4. GRAT vs CRAT (`trust_comparison`)
5. Integrated estate-liquidity plan (`estate_liquidity_action_plan`)
6. Rounding, dates, output hygiene
7. Worked numbers you can check against

---

## 1. Data sources & source resolution

Endpoints (all GET, base = `API_BASE` env or `http://127.0.0.1:8066`):

| Endpoint | Use for |
| --- | --- |
| `/api/clients/{id}` | header only (do NOT trust for planning facts — source docs control) |
| `/api/source-documents?client_id=ID` | profile/goal/beneficiary facts (multiple, may conflict) |
| `/api/retirement-accounts?client_id=ID` | IRA balances, return, RMD age, conversion years |
| `/api/life-insurance?client_id=ID` | ILIT policy: death benefit, premium, contribution date, transfer flag |
| `/api/trust-candidates?client_id=ID` | GRAT/CRAT parameters |
| `/api/policies/tax` | ALL tax constants (never hard-code) |
| `/api/rmd-factors` | RMD divisors keyed by age (string keys) |

**Source-of-truth rules (the heart of the task):**

- **Profile / goals / beneficiary count / income / marital & filing status / estate value /
  liquid assets / philanthropic & family-transfer priority** → the **SIGNED_PROFILE**
  source document wins. It is the most recent and the only *signed* record. If more than
  one SIGNED_PROFILE ever appears, take the one with the latest `effective_date`.
  - `ATTORNEY_MEMO`, `CRM_NOTE`, and `STALE_MARKETING_INTAKE` are **distractors** that may
    disagree (older imports). They never override a signed value. In the data observed,
    only CRM_NOTE, ATTORNEY_MEMO, SIGNED_PROFILE actually occur, but the schema lists
    STALE_MARKETING_INTAKE — treat it as lowest trust if it appears.
  - Therefore `controlling_profile_source`, `controlling_beneficiary_source`,
    `controlling_goal_source`, `controlling_policy_source` are almost always
    **`SIGNED_PROFILE`**.
- **Account numbers** (traditional/roth balance, expected_return, rmd_start_age,
  recommended_conversion_years) → the **CUSTODIAN_EXPORT** record from
  `/api/retirement-accounts`. So `controlling_account_source` = **`CUSTODIAN_EXPORT`**.
- **Trust mechanics** (asset_value, growth, terms, rates) → the **trust-candidates**
  endpoint. Estate facts used alongside them (estate_value) still come from the signed
  profile. When the schema asks for `controlling_asset_source` and both ATTORNEY_MEMO and
  SIGNED_PROFILE carry the same estate value, prefer **`ATTORNEY_MEMO`** for the asset/estate
  source on the pure trust-comparison task (that is what train_003 used); for the integrated
  plan train_004 used `SIGNED_PROFILE` for `controlling_policy_source`. Rule of thumb:
  the document that actually *carries* the controlling number for that field, with
  SIGNED_PROFILE the default and ATTORNEY_MEMO acceptable when it is the dedicated
  estate/asset memo and agrees with signed.

The client header (`/api/clients/{id}`) usually matches the signed profile, but never use it
to override a signed value. Ignore `record_status` ("active"/"monitoring") for the math.

---

## 2. Roth conversion + RMD — `analysis_type: roth_conversion_rmd`

Inputs: signed profile (`annual_non_ira_income`, `marginal_tax_rate`, `age`, `planning_year`,
`filing_status`), custodian account (`traditional_balance`, `roth_balance`, `expected_return`,
`rmd_start_age`, `recommended_conversion_years`), `conversion_bracket_targets[filing_status]`
from policy, `rmd-factors`, and a horizon year (given in the request memo).

**Conversion sizing**
```
annual_conversion_amount = bracket_target[filing_status] - annual_non_ira_income
total_converted          = annual_conversion_amount * recommended_conversion_years
total_conversion_tax     = annual_conversion_amount * marginal_tax_rate * recommended_conversion_years
first_conversion_year    = planning_year
conversion_years         = recommended_conversion_years
```
- `conversion_years_positive` = `recommended_conversion_years` when `annual_conversion_amount > 0`,
  else `0`.
- If `annual_conversion_amount <= 0` (income already at/above the bracket target) there is no
  room: set conversion amounts/tax to 0, primary_action = `NO_CONVERSION`.

**Year-by-year projection (order of operations is load-bearing).** Run twice over
`year = planning_year .. horizon_year`; `age = age + (year - planning_year)`:
1. **Convert** (conversion scenario only, and only while `year < planning_year + conversion_years`,
   and only if `annual_conversion_amount > 0`): `traditional -= conv; roth += conv`.
2. **RMD** if `age >= rmd_start_age`: `dist = traditional / rmd_factor[age]`;
   `traditional -= dist`; accumulate `rmd_tax += dist * marginal_tax_rate`.
3. **Grow** both: `traditional *= (1+expected_return); roth *= (1+expected_return)`.

Run scenario A = no conversion (baseline) and scenario B = with conversion.
```
baseline_rmd_tax_through_horizon   = rmd_tax(A)
conversion_rmd_tax_through_horizon = rmd_tax(B)
rmd_tax_savings_through_horizon    = A - B
projected_roth_balance_horizon        = roth balance at end of B
projected_traditional_balance_horizon = traditional balance at end of B
first_rmd_year = planning_year + (rmd_start_age - age)
```
Growth is applied *every* year including the final horizon year (the balance reported is
post-growth). RMD divisor lookup uses the client's age *that year*; ages past 99 are not in the
table — horizons in practice stay within range.

**Enums**
- `primary_action`: `STAGED_ROTH_CONVERSION` when `annual_conversion_amount > 0` (normal);
  `NO_CONVERSION` if no headroom; `DEFER` only if the memo explicitly says to wait.
- `suitability`: `SUITABLE` when there is bracket headroom and runway before RMDs; `DEFER`
  mirrors a DEFER action; `BORDERLINE` for thin headroom.
- `risk_flag`: `TAX_BRACKET_MANAGEMENT` is the normal driver (sizing by bracket headroom).
  `RMD_NEAR_TERM` only if there is essentially no pre-RMD runway *and* the bracket logic is not
  the story; note train_005 has age 72 (one year to RMDs) yet still uses
  `TAX_BRACKET_MANAGEMENT`, so default to that. `LIQUIDITY_CONSTRAINT` if the client cannot fund
  the conversion tax from liquid assets.
- `heir_tax_profile`: by roth share of (roth+traditional) at horizon — `>=80%` →
  `MOSTLY_TAX_FREE`, `<=20%` → `MOSTLY_TAXABLE`, otherwise `MIXED_TAXABLE_AND_TAX_FREE`
  (both training cases landed MIXED at 45–61% roth).

---

## 3. ILIT / Crummey — `analysis_type: ilit_crummey_implementation`

Inputs: signed profile (`beneficiary_count`, `liquid_assets`), life policy
(`death_benefit`, `annual_premium`, `planned_contribution_date`, `is_existing_policy_transfer`),
`annual_gift_exclusion[year]` from policy.

**Gift capacity**
```
annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year]   # 2026 -> 20000
beneficiary_count                = signed profile beneficiary_count
annual_exclusion_capacity        = beneficiary_count * per_beneficiary
annual_premium                   = policy annual_premium
premium_gap                      = max(0, annual_premium - annual_exclusion_capacity)
notices_required                 = beneficiary_count   # one Crummey notice per beneficiary
```

**Crummey date arithmetic** (calendar days, from the policy's `planned_contribution_date`):
```
contribution_date            = planned_contribution_date
notice_due_date              = contribution_date + 7 days
withdrawal_window_end        = notice_due_date    + 30 days
earliest_premium_payment_date= withdrawal_window_end + 1 day
```
(So withdrawal_window_end is contribution + 37 days; premium can be paid only after the window
closes, hence +1.) `dedicated_bank_account_required` = `true` (an ILIT needs its own account to
preserve the gift/withdrawal formalities).

**Estate result**
```
death_benefit                            = policy death_benefit
projected_outside_estate_if_implemented  = policy death_benefit
tax_liquidity_support                    = signed profile liquid_assets
estate_inclusion_risk                    = risk_flag (see below)
```
Note on `tax_liquidity_support`: matched `liquid_assets` exactly in the gold (estate exposure
was 0 there, so it is not exposure-based). Use `liquid_assets`.

**Risk / recommendation enums** (driven by transfer flag and premium gap):
```
is_transfer  = is_existing_policy_transfer
shortfall    = premium_gap > 0
risk_flag = THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL if is_transfer and shortfall
          = THREE_YEAR_LOOKBACK                         if is_transfer
          = EXCLUSION_SHORTFALL                         if shortfall
          = LOW_IF_FORMALITIES_MET                      otherwise
```
- `primary_action`: `FUND_WITH_CRUMMEY_NOTICES` when capacity covers premium and no transfer;
  `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` when there is a shortfall (cover the gap with lifetime
  exemption); `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` / `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` when an
  existing policy is being transferred (3-year lookback) — pick the disclosure variant when a
  shortfall is also present.
- `suitability`: `SUITABLE_WITH_ADMINISTRATION` is the normal answer (ILITs work but require the
  notice/account formalities); `NOT_SUITABLE` only for a severe lookback+shortfall combination;
  `BORDERLINE` in between.
- `estate_inclusion_risk` mirrors `risk_flag`.

---

## 4. GRAT vs CRAT — `analysis_type: trust_comparison`

Inputs: trust candidate (`asset_value`, `expected_growth_rate`, `grat_term_years`,
`grat_annuity_rate`, `crat_term_years`, `crat_payout_rate`), signed profile for estate context &
goals, `estate_tax_rate`, `charitable_deduction_rate`, `max_crat_term_years` from policy.

**Estate context** (see §5 formula; identical):
```
exemption_used = estate_exemption(marital_status)   # married -> exemption*2
taxable_estate = max(0, estate_value - exemption_used)
estate_tax_exposure = taxable_estate * estate_tax_rate
liquid_assets_available = liquid_assets
liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)
```

**Both trusts use the SAME flat-annuity remainder engine:**
```
remainder(asset, g, term, rate) = asset*(1+g)**term - (asset*rate)*term
```
The annuity/payout is a flat dollar amount `asset*rate` each year and is NOT reinvested.

```
GRAT:
  term_years = grat_term_years
  projected_remainder_to_heirs   = remainder(asset, g, grat_term_years, grat_annuity_rate)
  estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate   # 0.40
  mortality_inclusion_risk = "TERM_SURVIVAL_REQUIRED"   # fixed enum

CRAT:
  term_years = min(crat_term_years, max_crat_term_years)   # cap at 20
  projected_charitable_remainder = remainder(asset, g, crat_term_years_capped, crat_payout_rate)
  estimated_income_tax_deduction = projected_charitable_remainder * charitable_deduction_rate  # 0.35
  family_transfer_fit = "LOW"     # a CRAT gives the remainder to charity, not the family
```

**Recommendation (goal-driven, from the signed profile):**
- `family_transfer_priority == "high"` (and not a primarily philanthropic client) →
  `preferred_strategy = GRAT`, `rationale_code = CHILDREN_TRANSFER_PRIORITY`,
  `alternate_role = SECONDARY_CHARITABLE_TOOL`.
- `philanthropic_intent == "high"` dominating → `preferred_strategy = CRAT`,
  `rationale_code = PHILANTHROPIC_PRIORITY`, `alternate_role = SECONDARY_FAMILY_TRANSFER_TOOL`.
- Resolve goals from the SIGNED profile (it carried `family_transfer_priority: high` in train_003,
  overriding the CRM's "moderate").

---

## 5. Integrated estate-liquidity plan — `analysis_type: estate_liquidity_action_plan`

Combines estate context (§4 formula), the ILIT block (§3), and a trust transfer (§4). The
trust_transfer block reports the **preferred** strategy's numbers plus the CRAT remainder for
reference:
```
estate_context: planning_year, exemption_used, taxable_estate, estate_tax_exposure,
                liquid_assets_available, liquidity_gap_before_planning   (as in §4)
ilit: annual_exclusion_capacity, premium_gap, estate_inclusion_risk,
      projected_outside_estate_if_implemented (= death_benefit)
trust_transfer:
  preferred_strategy            = GRAT or CRAT (goal-driven, §4)
  projected_remainder_to_heirs  = GRAT remainder
  estimated_estate_tax_reduction= GRAT remainder * estate_tax_rate
  projected_charitable_remainder= CRAT remainder   (always reported, even when GRAT preferred)
```

**`action_set`** — a list of enums, **sorted alphabetically** (this ordering IS scored). Include
an action only when its trigger is present:
| Enum | Include when |
| --- | --- |
| `ILIT_CRUMMEY_NOTICE_CYCLE` | a life-insurance/ILIT policy exists for the client |
| `GRAT_FOR_APPRECIATING_SHARES` | preferred trust strategy is GRAT (family transfer priority) |
| `CRAT_FOR_CHARITABLE_REMAINDER` | preferred trust strategy is CRAT (philanthropic priority) |
| `LIFETIME_EXEMPTION_ALLOCATION` | `premium_gap > 0` OR remaining estate exposure needs exemption |
| `ATTORNEY_DRAFT_REVIEW` | always (these structures need attorney drafting/coordination) |
Train_004 had ILIT + GRAT, premium_gap 0, so the set was exactly
`["ATTORNEY_DRAFT_REVIEW", "GRAT_FOR_APPRECIATING_SHARES", "ILIT_CRUMMEY_NOTICE_CYCLE"]`.

**Recommendation enums:**
- `primary_action`: `COMBINE_ILIT_AND_GRAT` when both an ILIT policy and a GRAT-preferred trust
  exist; `CRAT_WITH_LIQUIDITY_REVIEW` when the trust is CRAT-preferred; `ILIT_WITH_EXEMPTION_REVIEW`
  when only the ILIT is in play / a shortfall needs exemption.
- `sequencing`: `ILIT_FIRST_THEN_GRAT` for the combine case; `TRUST_DECISION_FIRST` when the trust
  choice gates everything; `ILIT_FIRST_THEN_ATTORNEY_REVIEW` for the ILIT-only path.
- `risk_flag`: the ILIT risk flag (§3): `LOW_IF_FORMALITIES_MET` when no transfer and no shortfall.

---

## 6. Rounding, dates, output hygiene

- Every USD field: a JSON **number** (not string) rounded to **2 decimals (cents)**. Whole-dollar
  values still serialize as e.g. `80000.0`. Round only at the end; keep full precision internally.
- Integers (`*_year`, counts) are JSON integers.
- Dates are **ISO `YYYY-MM-DD`** strings.
- Echo `task_id` exactly as the harness expects (e.g. `train_00N` / `test_00N`), `client_id` from
  the request, and the fixed `analysis_type` enum for the family.
- Output **only** the JSON object — no prose, no markdown fences. Include exactly the
  `required_top_level_keys` from the task's `answer_template.json` (key order is not scored unless
  the template says so; `action_set` element order IS scored).
- Always re-read the specific task's `answer_template.json`: field sets differ slightly between
  tasks (e.g. some include `planning_year`/`exemption_used`/`liquid_assets_available` inside
  `estate_context`, some don't). Emit exactly what that template lists.

---

## 7. Worked numbers to self-check against

Run `python3 scripts/advisory_lib.py` — it asserts these and prints `OK`:

- **CLT-1001** (MFJ, income 185000, bracket 394600): annual_conversion 209600.00,
  total_conversion_tax 469504.00, baseline_rmd_tax 1097182.33, conversion_rmd_tax 617448.59,
  savings 479733.74, roth horizon 4594320.16, trad horizon 2895040.03, first_rmd_year 2033.
- **CLT-1005** (SINGLE, bracket 197300, income 92000): annual_conversion 105300.00,
  savings 112697.88, roth horizon 1209698.68, first_rmd_year 2027.
- **CLT-1002** (4 beneficiaries, premium 78000): capacity 80000.00, premium_gap 0.00,
  contribution 2026-03-10, notice 2026-03-17, window end 2026-04-16, earliest pay 2026-04-17,
  liquidity support 1800000.00.
- **CLT-1003** GRAT (asset 8.0M, g 0.08, term 5, rate 0.04): remainder 10154624.61,
  tax reduction 4061849.85; CRAT (term 20, payout 0.055): remainder 28487657.15,
  deduction 9970680.00; exemption_used 27220000, taxable 11580000, exposure 4632000.
- **CLT-1004** GRAT (asset 9.5M, g 0.09, term 6, rate 0.045): remainder 13367451.05,
  tax reduction 5346980.42; exemption_used 13610000 (single), taxable 17590000, exposure 7036000,
  liquidity gap 4636000.
