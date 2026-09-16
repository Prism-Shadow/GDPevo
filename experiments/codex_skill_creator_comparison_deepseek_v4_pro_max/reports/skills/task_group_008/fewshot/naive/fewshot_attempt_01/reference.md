## Private Wealth Advisory — Computation Reference

This file captures the exact formulas verified against the five training answers.

### RMD Divisors

From `/api/rmd-factors`. Key ages:

| Age | Divisor |
|-----|---------|
| 73  | 26.5    |
| 74  | 25.5    |
| 75  | 24.6    |
| 76  | 23.7    |
| 77  | 22.9    |
| 78  | 22.0    |
| 79  | 21.1    |
| 80  | 20.2    |
| ... | ...     |

Full table of 27 values from 73 through 99. Always fetch live from the API; the table above is for reference only.

### Tax Constants (2026 Planning Year)

| Constant | Value |
|---|---|
| Annual gift exclusion | 20000 |
| Estate tax exemption | 13610000 (per individual; MFJ uses 2×) |
| Estate tax rate | 0.4 |
| Charitable deduction rate | 0.35 |
| Conversion bracket target MFJ | 394600 |
| Conversion bracket target SINGLE | 197300 |
| Conversion bracket target HOH | 263500 |
| Max CRAT term | 20 years |

### Source Priority

1. SIGNED_PROFILE (most recent effective date among all SIGNED_PROFILE docs for the client)
2. ATTORNEY_MEMO
3. CUSTODIAN_EXPORT
4. CRM_NOTE
5. STALE_MARKETING_INTAKE

When a fact appears in multiple sources, use the highest-ranked source.

### Roth Conversion Formulas

```
annual_conversion_amount = bracket_target[filing_status] − annual_non_ira_income
  (Never negative; floor at 0. Rounded to cents.)

total_converted = min(annual_conversion_amount × conversion_years, traditional_balance)
total_conversion_tax = total_converted × marginal_tax_rate

conversion_years = recommended_conversion_years (from account)
conversion_years_positive = conversion_years
first_conversion_year = planning_year
```

### RMD Simulation (year‑by‑year)

For each year Y from `planning_year` to `horizon_year`:

```
age = client_age + (Y − planning_year)

1. If in conversion window: balance_trad −= annual_conversion_amount (and balance_roth += annual_conversion_amount)
2. If age ≥ rmd_start_age: rmd = balance_trad / rmd_factor[age]; balance_trad −= rmd; tax += rmd × marginal_rate
3. balance_trad *= (1 + expected_return)
4. balance_roth *= (1 + expected_return)
```

Run twice: once without step 1 (baseline), once with (conversion scenario).

### Legacy Balances at Horizon

After the simulation loop through `horizon_year`, report `balance_roth` and `balance_trad` rounded to cents. The `heir_tax_profile` is `MIXED_TAXABLE_AND_TAX_FREE` when both balances are nonzero.

### GRAT Formulas

```
annuity = asset_value × grat_annuity_rate
fv = asset_value × (1 + expected_growth_rate) ^ grat_term_years
remainder = fv − (grat_term_years × annuity)
estate_tax_reduction = remainder × estate_tax_rate
```

Grat_term_years, grat_annuity_rate, asset_value, and expected_growth_rate come from the trust-candidates record for the client.

### CRAT Formulas

```
annuity = asset_value × crat_payout_rate
fv = asset_value × (1 + expected_growth_rate) ^ crat_term_years
charitable_remainder = fv − (crat_term_years × annuity)
income_tax_deduction = charitable_remainder × charitable_deduction_rate
```

Crat_term_years is always 20. crat_payout_rate is 0.055. Both come from the trust-candidates record.

### Estate Context Formulas

```
exemption_used = estate_tax_exemption[planning_year]
  Multiply by 2 for MFJ, use as-is for SINGLE and HOH.

taxable_estate = estate_value − exemption_used
estate_tax_exposure = taxable_estate × estate_tax_rate
liquidity_gap_before_planning = max(0, estate_tax_exposure − liquid_assets)
liquid_assets_available = liquid_assets (from signed profile)
```

### ILIT Crummey Dates

All computed from `planned_contribution_date` (ISO string from the policy record):

```
contribution_date = planned_contribution_date
notice_due_date = contribution_date + 7 days
withdrawal_window_end = notice_due_date + 30 days
earliest_premium_payment_date = withdrawal_window_end + 1 day
```

Use Python `datetime.date.fromisoformat()` + `timedelta(days=n)` + `.isoformat()`.

### ILIT Risk Determination

```
premium_gap = max(0, annual_premium − annual_exclusion_capacity)

If is_existing_policy_transfer == false:
  premium_gap == 0 → LOW_IF_FORMALITIES_MET
  premium_gap > 0  → EXCLUSION_SHORTFALL

If is_existing_policy_transfer == true:
  premium_gap == 0 → THREE_YEAR_LOOKBACK
  premium_gap > 0  → THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL
```

### Trust Recommendation Logic

| Profile Signal | Preferred | Rationale | Alternate Role |
|---|---|---|---|
| family_transfer_priority = high | GRAT | CHILDREN_TRANSFER_PRIORITY | SECONDARY_CHARITABLE_TOOL |
| philanthropic_intent = high | CRAT | PHILANTHROPIC_PRIORITY | SECONDARY_FAMILY_TRANSFER_TOOL |
| Both moderate, family >= moderate | GRAT | CHILDREN_TRANSFER_PRIORITY | SECONDARY_CHARITABLE_TOOL |

### Estate Liquidity Action Set

Valid enum values (sorted alphabetically in output):
- ATTORNEY_DRAFT_REVIEW
- CRAT_FOR_CHARITABLE_REMAINDER
- GRAT_FOR_APPRECIATING_SHARES
- ILIT_CRUMMEY_NOTICE_CYCLE
- LIFETIME_EXEMPTION_ALLOCATION

When combining ILIT and GRAT (the most common pattern), include ATTORNEY_DRAFT_REVIEW, GRAT_FOR_APPRECIATING_SHARES, and ILIT_CRUMMEY_NOTICE_CYCLE.
