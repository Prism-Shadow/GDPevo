# Roth Conversion RMD Analysis Skill

## Task Overview
Given a client profile with conflicting data sources, produce a JSON analysis recommending whether to execute a staged Roth conversion, defer, or take no conversion action. The analysis must resolve source conflicts, project RMD taxes, and estimate legacy balances.

## Input Structure
Each task contains:
- `prompt.txt` — generic instruction to read `request_memo.md` and produce deliverable
- `payloads/request_memo.md` — client profile, conflicting sources, goals, and specific questions
- `payloads/answer_template.json` — exact schema and enum values for the output

## Source Resolution Rules
The output requires `source_resolution` with two fields:
- `controlling_profile_source`: authoritative source for demographic/legal data (DOB, salary, heir info, tax profile)
- `controlling_account_source`: authoritative source for account balances

### Hierarchy
- **SIGNED_PROFILE** — highest authority for client-verified personal data (DOB, salary, filing status)
- **CUSTODIAN_EXPORT** — highest authority for actual account balances, unless the signed profile is explicitly more recent and client-acknowledged
- **ATTORNEY_MEMO** — highest authority for legal/heir matters and estate-specific guidance; overrides SIGNED_PROFILE on heir tax profiles
- **CRM_NOTE** — lowest authority; use only when no higher source exists for the datum
- **STALE_MARKETING_INTAKE** — never prefer over the above

### Principle
Prefer the source that is **most recent, most specific to the data type, and client-verified**.

## RMD Age Determination (SECURE 2.0)
Use the IRS SECURE 2.0 schedule unless the memo explicitly overrides it:
- Born before 1951 → RMD age 72
- Born 1951–1959 → RMD age 73
- Born 1960 or later → RMD age 75

**Pitfall**: If the request_memo explicitly states an RMD start year or says "RMDs already started," trust that statement even if it conflicts with the DOB-based calculation. The memo is ground truth for the client's specific situation.

## Recommendation Logic

### Suitability Assessment
1. **Current marginal rate < expected heir marginal rate** → generally **SUITABLE**
2. **Current marginal rate ≈ expected heir marginal rate** → **BORDERLINE**
3. **Current marginal rate > expected heir marginal rate** → **DEFER**
4. **RMDs already started** and current rate ≥ heir rate → strongly **DEFER**
5. **RMD within ~5 years** and balance is very large → may downgrade from SUITABLE to **BORDERLINE**

### Primary Action Mapping
- **SUITABLE** → `STAGED_ROTH_CONVERSION`
- **BORDERLINE** → `STAGED_ROTH_CONVERSION` (with conservative plan) or `DEFER`
- **DEFER** → `DEFER` (or `NO_CONVERSION` if permanently unsuitable)

### Risk Flags
- `TAX_BRACKET_MANAGEMENT` — conversion requires staying within or managing tax brackets (most common)
- `LIQUIDITY_CONSTRAINT` — client may lack outside funds to pay conversion taxes
- `RMD_NEAR_TERM` — RMDs starting within ~5 years, reducing conversion runway

## Conversion Plan Design

### If SUITABLE / BORDERLINE
1. Determine `first_conversion_year`: typically the current year or next calendar year.
2. Determine `conversion_years`: typically from current age to RMD age, or a fixed horizon (e.g., 5–15 years). If already in RMDs, use a shorter window (e.g., 3–5 years) or set to 0 if deferring.
3. Determine `total_converted`:
   - Common approach: convert enough to fill the current tax bracket without jumping brackets, or convert a set fraction of the balance over the conversion window.
   - For large balances with short runways, be conservative (e.g., 20–40% of balance).
4. `annual_conversion_amount` = `total_converted` / `conversion_years` (rounded to cents).
5. `total_conversion_tax` = `total_converted` × `current_marginal_tax_rate` (rounded to cents).
   - If conversions would span multiple brackets, use a blended rate or bracket-by-bracket calculation. A simplified flat-rate estimate is acceptable when bracket boundaries are unknown.

### If DEFER / NO_CONVERSION
- `first_conversion_year`: set to current year or next year
- `conversion_years`: 0
- `conversion_years_positive`: 0
- `annual_conversion_amount`: 0.00
- `total_converted`: 0.00
- `total_conversion_tax`: 0.00

## RMD Tax Projections

### Assumptions (use unless memo states otherwise)
- **Annual growth rate**: 6% or 7% (use 6% as a conservative standard)
- **Horizon**: age 85 or 90, or a consistent fixed year (e.g., 20 years from now). Document the chosen horizon.
- **RMD calculation**: IRS Uniform Lifetime Table (divide prior year-end balance by distribution period)
- **Tax on RMDs**: RMD amount × current marginal tax rate (simplified; can refine if bracket changes are expected)

### Baseline vs Conversion
- `baseline_rmd_tax_through_horizon`: project RMDs and taxes on the full traditional balance.
- `conversion_rmd_tax_through_horizon`: project RMDs and taxes on the balance **after** subtracting `total_converted`.
- `rmd_tax_savings_through_horizon` = baseline − conversion (must be non-negative if conversion is suitable).

**Important**: RMDs are calculated on the prior year-end balance. After each RMD, the remaining balance grows at the assumed rate. Sum taxes year-by-year through the horizon.

## Legacy Projections
- `projected_roth_balance_horizon`: `total_converted` compounded at the growth rate from `first_conversion_year` to `horizon_year`.
- `projected_traditional_balance_horizon`: initial balance minus `total_converted`, then reduced by annual RMDs and compounded by growth rate.
- `heir_tax_profile`:
  - `MOSTLY_TAX_FREE` — majority of heirs are in lower brackets or charity/spouse rollover
  - `MIXED_TAXABLE_AND_TAX_FREE` — mixed heir brackets or partial charity
  - `MOSTLY_TAXABLE` — majority of heirs are in equal or higher brackets

## Heir Tax Profile Rules
- Spousal rollover → tax-free (counts toward tax-free)
- Charity bequest → tax-free
- Heir in lower bracket than owner → tax-free perspective
- Heir in equal or higher bracket → taxable perspective
- When multiple heirs with mixed brackets → `MIXED_TAXABLE_AND_TAX_FREE` unless one side clearly dominates

## JSON Output Rules
- All monetary values must be **JSON numbers** (not strings), rounded to **two decimal places**.
- All enum values must match the template exactly (uppercase with underscores).
- `task_id` must match the task directory name (e.g., `train_001`, `test_001`).
- `client_id` should be stable (use the client's name or a slug derived from it).
- `analysis_type` is always `roth_conversion_rmd`.
- All top-level keys listed in `required_top_level_keys` must be present.
- `conversion_plan.conversion_years_positive` should equal `conversion_plan.conversion_years` when all years have conversions; set to 0 when deferring.
- Ensure internal consistency: `total_converted` ≈ `annual_conversion_amount` × `conversion_years` (within rounding).

## Common Pitfalls
1. **Using strings for numbers** — the template explicitly forbids this.
2. **Ignoring memo-overridden RMD status** — trust the memo over general IRS rules.
3. **Wrong source resolution** — account balances usually come from custodian export, but personal data comes from signed profile; legal/heir data may come from attorney memo.
4. **Inconsistent horizon** — choose a horizon and apply it consistently across baseline and conversion projections.
5. **Forgetting RMDs reduce balance** — legacy traditional balance must account for RMD withdrawals.
6. **Negative tax savings** — if conversion increases projected RMD taxes, reconsider the recommendation.
7. **Heir tax profile misclassification** — consider the *owner's current marginal rate vs heir's expected marginal rate*, not just absolute heir brackets.

## Calculation Verification Checklist
Before finalizing output, verify:
- [ ] `first_rmd_year` aligns with memo or SECURE 2.0 rules
- [ ] `horizon_year` is reasonable and consistent
- [ ] `baseline_rmd_tax_through_horizon` ≥ `conversion_rmd_tax_through_horizon`
- [ ] `rmd_tax_savings_through_horizon` = baseline − conversion
- [ ] `total_converted` = `annual_conversion_amount` × `conversion_years` (± rounding)
- [ ] `total_conversion_tax` = `total_converted` × rate (or blended rate)
- [ ] `projected_traditional_balance_horizon` < initial balance (unless very long horizon with high growth)
- [ ] `projected_roth_balance_horizon` > `total_converted` (due to growth)
- [ ] `recommendation` enums exactly match template values
- [ ] `source_resolution` enums exactly match template values
- [ ] `task_id` matches the directory/task identifier
