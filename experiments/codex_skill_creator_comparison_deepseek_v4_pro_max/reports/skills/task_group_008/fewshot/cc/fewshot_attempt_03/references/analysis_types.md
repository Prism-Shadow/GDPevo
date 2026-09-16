# Per-Analysis-Type Step-by-Step Guides

Each section below walks through the computation for one `analysis_type` value.
All formulas are detailed in `tax_formulas.md`. Source resolution rules are in
`source_resolution.md`.

---

## roth_conversion_rmd

Used for Roth conversion RMD analysis engagements.

### Step 1: Fetch and resolve

1. `GET /api/clients/{client_id}` — get `age`, `filing_status`, `planning_year`.
2. `GET /api/source-documents` — filter to `client_id`. Extract
   `annual_non_ira_income`, `marginal_tax_rate`, `beneficiary_count` from the
   controlling source (signed profile, then attorney memo, then CRM).
3. `GET /api/retirement-accounts` — filter to `client_id`. Get
   `traditional_balance`, `roth_balance`, `expected_return`, `rmd_start_age`,
   `recommended_conversion_years`.
4. `GET /api/policies/tax` — get `conversion_bracket_targets[filing_status]`
   and `estate_tax_rate`.
5. `GET /api/rmd-factors` — full table.

6. Determine `horizon_year` from the request memo. If absent, default to
   `planning_year + 20`.

### Step 2: Compute conversion plan

- `annual_conversion_amount` = bracket target - income.
- `total_converted` = annual * conversion_years.
- `total_conversion_tax` = total_converted * marginal_rate.

### Step 3: Compute RMD projections

Run the baseline projection (no conversions) and the conversion projection
(as described in `tax_formulas.md`). When `first_rmd_year` falls within the
conversion window, conversion and RMD both apply in overlapping years —
subtract the conversion first, then the RMD, then grow. Get
`rmd_tax_savings_through_horizon`.

### Step 4: Compute legacy balances

Run the Roth and Traditional growth projections to horizon.

### Step 5: Select enums

- `primary_action`: `STAGED_ROTH_CONVERSION` if conversion_years >= 1 and
  savings > 0. `DEFER` if first RMD year <= planning_year + 2 (near-term).
  `NO_CONVERSION` if income already exceeds bracket target.
- `suitability`: `SUITABLE` when savings are meaningful and the plan
  executes. `BORDERLINE` when near RMD (1-2 years out). `DEFER` when savings
  are negligible.
- `risk_flag`: `TAX_BRACKET_MANAGEMENT` for normal cases. `LIQUIDITY_CONSTRAINT`
  when `liquid_assets` < 2 * `total_conversion_tax`. `RMD_NEAR_TERM` when
  `first_rmd_year` <= `planning_year + 2`.

### Step 6: Source resolution

- `controlling_profile_source`: highest-priority profile document present.
- `controlling_account_source`: highest-priority account document present.

---

## ilit_crummey_implementation

Used for ILIT Crummey funding engagements and the ILIT block of estate
liquidity plans.

### Step 1: Fetch and resolve

1. `GET /api/clients/{client_id}`.
2. `GET /api/source-documents` — filter, resolve `beneficiary_count`.
3. `GET /api/life-insurance` — filter to `client_id`. Get `death_benefit`,
   `annual_premium`, `planned_contribution_date`, `is_existing_policy_transfer`.
4. `GET /api/policies/tax` — get `annual_gift_exclusion[planning_year]`.

### Step 2: Gift plan

Capacity = exclusion * beneficiaries. Gap = max(0, premium - capacity).

### Step 3: Administration

Compute dates from `planned_contribution_date` using day arithmetic.
`notices_required` = `beneficiary_count`.

### Step 4: Estate result

`death_benefit` and `tax_liquidity_support` = `death_benefit` * `estate_tax_rate`.

### Step 5: Select enums

- `primary_action`: see the dispatch table in `SKILL.md` based on gap and
  existing-policy flag.
- `suitability`: `SUITABLE_WITH_ADMINISTRATION` (gap=0, not existing).
  `BORDERLINE` (gap > 0 or existing). `NOT_SUITABLE` (gap > 0 AND
  existing).
- `risk_flag` and `estate_inclusion_risk`: `LOW_IF_FORMALITIES_MET` (clean),
  `EXCLUSION_SHORTFALL` (gap>0), `THREE_YEAR_LOOKBACK` (existing),
  `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` when both apply.

### Step 6: Source resolution

- `controlling_beneficiary_source`: highest-priority source giving
  beneficiary_count.
- `controlling_policy_source`: highest-priority source for policy facts.

---

## trust_comparison

Used for GRAT vs CRAT comparison engagements and the trust block of estate
liquidity plans.

### Step 1: Fetch and resolve

1. `GET /api/clients/{client_id}`.
2. `GET /api/source-documents` — resolve `family_transfer_priority`,
   `philanthropic_intent`, `estate_value`, `liquid_assets`.
3. `GET /api/trust-candidates` — filter to `client_id`. Get all fields.
4. `GET /api/policies/tax` — get `estate_tax_rate`,
   `estate_tax_exemption[planning_year]`, `charitable_deduction_rate`.

### Step 2: Estate context

`taxable_estate` = max(0, estate_value - exemption).
`estate_tax_exposure` = taxable * rate.
`liquidity_gap` = max(0, exposure - liquid_assets).
Add `planning_year`, `exemption_used`, and `liquid_assets_available` when the
template requires them.

### Step 3: GRAT and CRAT

Compute remainder, tax reduction/deduction using formulas in `tax_formulas.md`.

### Step 4: Select enums

- `preferred_strategy`: `GRAT` when `family_transfer_priority` is at least
  as high as `philanthropic_intent`. `CRAT` when philanthropy clearly
  dominates.
- `rationale_code`: `CHILDREN_TRANSFER_PRIORITY` for GRAT;
  `PHILANTHROPIC_PRIORITY` for CRAT.
- `alternate_role`: `SECONDARY_CHARITABLE_TOOL` (GRAT primary);
  `SECONDARY_FAMILY_TRANSFER_TOOL` (CRAT primary).
- `family_transfer_fit`: `LOW` for CRAT when philanthropy is high; `MODERATE`
  when mixed; `HIGH` when CRAT still carries family benefit.

### Step 5: Source resolution

- `controlling_goal_source`: for philanthropy/intent facts.
- `controlling_asset_source`: for trust asset value.

---

## estate_liquidity_action_plan

Used for combined ILIT + trust recommendation engagements.

### Step 1: Fetch everything

Combine the fetches from ILIT and trust comparison sections. Fetch clients,
source documents, life insurance, trust candidates, tax policies, and RMD
factors. The estate context needs `estate_value`, `liquid_assets`, and tax
constants. The ILIT block needs policy data. The trust block needs trust
candidate data.

### Step 2: Estate context

Same as trust comparison.

### Step 3: ILIT block

Same computations as `ilit_crummey_implementation` for gift capacity, premium
gap, inclusion risk, and projected outside-estate value.

### Step 4: Trust transfer block

Same computations as `trust_comparison` for preferred strategy, remainder,
and estate tax reduction.

### Step 5: Action set

Build the sorted list. The standard actions for a combined ILIT + GRAT plan are:
`ATTORNEY_DRAFT_REVIEW`, `GRAT_FOR_APPRECIATING_SHARES`,
`ILIT_CRUMMEY_NOTICE_CYCLE`. Add `LIFETIME_EXEMPTION_ALLOCATION` when any gap
needs exemption coverage. Add `CRAT_FOR_CHARITABLE_REMAINDER` when CRAT is the
preferred strategy instead of GRAT.

### Step 6: Select enums

- `primary_action`: `COMBINE_ILIT_AND_GRAT` when both paths are active.
  `CRAT_WITH_LIQUIDITY_REVIEW` when CRAT is preferred and gap is significant.
  `ILIT_WITH_EXEMPTION_REVIEW` when only the ILIT side is relevant.
- `sequencing`: `ILIT_FIRST_THEN_GRAT` (default for combined),
  `TRUST_DECISION_FIRST` (when trust choice dominates),
  `ILIT_FIRST_THEN_ATTORNEY_REVIEW` (when attorney formalities need review).
- `risk_flag`: same logic as ILIT section.

### Step 7: Source resolution

- `controlling_goal_source` and `controlling_policy_source` as resolved.
