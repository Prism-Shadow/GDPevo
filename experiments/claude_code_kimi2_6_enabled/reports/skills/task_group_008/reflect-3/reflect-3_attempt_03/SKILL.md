# Roth Conversion and RMD Analysis Skill

## Task Overview
Analyze a client's retirement accounts to determine whether a systematic Roth conversion is advisable, calculate the optimal conversion plan, project RMD tax impacts, and resolve authoritative data sources. Output must follow a strict JSON template with exact numeric precision.

## Categorical Decision Rules (Critical — Wrong Values = Zero Score)

### Recommendation Block
- **primary_action**: 
  - `STAGED_ROTH_CONVERSION` when the client can convert without liquidity issues and bracket constraints can be managed.
  - `DEFER` when conversion is theoretically beneficial but constrained by age, bracket, or timing.
  - `NO_CONVERSION` when liquidity concerns explicitly prevent conversion or the client is well past the conversion window with no viable path.
- **suitability**:
  - `SUITABLE` for straightforward conversion cases (no liquidity issues, bracket accommodates meaningful conversion, client preference aligns).
  - `BORDERLINE` for constrained cases (small conversion due to low bracket headroom, near-term RMDs, or high existing bracket).
  - `DEFER` when the analysis suggests waiting for better tax circumstances.
- **risk_flag**:
  - `TAX_BRACKET_MANAGEMENT` when the $200k systematic amount would push the client into a higher marginal bracket (most common).
  - `LIQUIDITY_CONSTRAINT` when the taxable account must be drawn for living expenses and cannot cover conversion taxes.
  - `RMD_NEAR_TERM` when RMDs start within ~2–3 years and conversion window is extremely short.

### Legacy Projection
- **heir_tax_profile**: Compare projected Roth vs Traditional balance at horizon.
  - `MOSTLY_TAX_FREE` when Roth balance > 1.5× Traditional balance.
  - `MOSTLY_TAXABLE` when Traditional balance > 1.5× Roth balance.
  - `MIXED_TAXABLE_AND_TAX_FREE` otherwise.
  - If no Roth exists and no conversion occurs, this is `MOSTLY_TAXABLE`.

### Source Resolution
- **controlling_profile_source**: `SIGNED_PROFILE` is the default authoritative source for tax profile data (filing status, marginal rate) unless it is materially stale and superseded by a more recent CRM note. In cases of conflict or significant age gap, the most recent documented source with tax profile data controls.
- **controlling_account_source**: Always `CUSTODIAN_EXPORT` — it holds the actual account balances and is the most recent account-level source in every task.

## Numeric Calculation Rules

### Conversion Plan
1. **first_conversion_year**: Always the analysis year (2026 in the training tasks).
2. **conversion_window**: Convert "until age 70 or first RMD year, whichever comes first."
   - Count years from first_conversion_year up to (but not including) the earlier of: (a) the year the client turns 70, or (b) first_rmd_year.
   - For clients already past age 70, use first_rmd_year as the limit.
   - For clients already past first RMD year, conversion_years = 0.
3. **conversion_years_positive**: Equals conversion_years when all years have positive conversions. If the traditional IRA depletes mid-window, count only full years (partial final years may still count as positive if any amount converts).
4. **annual_conversion_amount**: Default is $200,000. **Reduce** if $200k + client income (after standard deduction) would exceed the top of the current marginal bracket.
   - Use the **standard deduction** for the client's filing status when computing taxable income room.
   - Use **2025 tax brackets** as the reference (the data spans 2025–2026, and 2026 brackets are not finalized in the task context).
   - For married filing jointly: 22% tops at $206,700; 24% tops at $394,600; 32% tops at $501,050.
   - For single: 22% tops at $103,350; 24% tops at $197,300; 32% tops at $250,500.
   - Standard deduction 2025: MFJ $29,900; Single $14,950.
5. **total_converted**: Sum of actual annual conversions over the conversion window, accounting for 6% annual growth of the remaining traditional balance between conversions.
6. **total_conversion_tax**: total_converted × client's marginal tax rate.

### RMD Projection
1. **horizon_year**: The year the client reaches age 85. Compute as birth_year + 85.
2. **first_rmd_year**: Determined by SECURE 2.0 rules:
   - Born before 1951: RMD at age 72.
   - Born 1951–1959: RMD at age 73.
   - Born 1960 or later: RMD at age 75.
3. **baseline_rmd_tax_through_horizon**: 
   - **Critical**: Include the **pre-RMD growth phase**. The traditional IRA balance grows at 6% annually for ALL years from the analysis year up to (but not including) first_rmd_year.
   - Once RMDs begin, each year: RMD = current_balance / Uniform Lifetime Table factor; subtract RMD; apply 6% growth to remainder; accumulate tax at marginal_rate.
   - Use the **post-2022 Uniform Lifetime Table** (SECURE 2.0 updated table):
     - Age 73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9, 78: 22.0, 79: 21.1, 80: 20.2, 81: 19.4, 82: 18.5, 83: 17.7, 84: 16.8, 85: 16.0.
4. **conversion_rmd_tax_through_horizon**: Same RMD methodology, but starting from the reduced traditional balance after conversions. For clients with no conversion, this equals baseline.
5. **rmd_tax_savings_through_horizon**: baseline_rmd_tax − conversion_rmd_tax. Can be small or even negative if conversion tax outweighs RMD savings, but usually positive for meaningful conversions.

### Legacy Projection
1. **projected_roth_balance_horizon**: Current Roth balance grown at 6% annually through horizon, PLUS all converted amounts (which also grow at 6% from their conversion year onward). Roth assets do not have RMDs for the original owner.
2. **projected_traditional_balance_horizon**: The remaining traditional balance after all RMDs through horizon, computed under the conversion scenario.
3. Round all dollar amounts to **two decimal places (cents)** using standard rounding. Use exact arithmetic where possible to avoid floating-point drift.

## Common Pitfalls
- **Forgetting pre-RMD growth**: The baseline traditional balance grows untouched for years before RMDs begin. This is the single largest source of numeric error.
- **Wrong conversion window**: Do not convert past age 70 or past first RMD year, whichever comes first. Converting up to the first RMD year is the hard stop.
- **Ignoring bracket limits**: Always check whether $200k pushes the client out of their stated marginal bracket. Apply standard deduction.
- **Source resolution errors**: Do not default to the newest date for profile source. The signed profile is authoritative unless clearly superseded. Custodian export always controls account balances.
- **Heir tax profile threshold**: Use the 1.5× rule, not simple majority.
- **RMD table**: Use the post-2022 table for all RMDs; do not revert to pre-2022 factors.

## Output Template Checklist
Ensure the JSON contains exactly these top-level keys:
- `task_id`, `client_id`, `analysis_type`
- `recommendation` with `primary_action`, `suitability`, `risk_flag`
- `conversion_plan` with `first_conversion_year`, `conversion_years`, `conversion_years_positive`, `annual_conversion_amount`, `total_converted`, `total_conversion_tax`
- `rmd_projection` with `horizon_year`, `first_rmd_year`, `baseline_rmd_tax_through_horizon`, `conversion_rmd_tax_through_horizon`, `rmd_tax_savings_through_horizon`
- `legacy_projection` with `projected_roth_balance_horizon`, `projected_traditional_balance_horizon`, `heir_tax_profile`
- `source_resolution` with `controlling_profile_source`, `controlling_account_source`

All numbers must be JSON numbers (not strings). No ordering constraints on object keys.
