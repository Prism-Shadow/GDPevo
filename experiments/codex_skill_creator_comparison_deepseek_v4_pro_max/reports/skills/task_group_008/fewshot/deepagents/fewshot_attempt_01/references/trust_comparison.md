## GRAT vs CRAT Trust Comparison

Use when `analysis_type` is `trust_comparison`. Compares a Grantor Retained Annuity
Trust (GRAT) against a Charitable Remainder Annuity Trust (CRAT) for a client with
a specific trust candidate.

### Input Sources

- Client record: age, estate_value, liquid_assets, filing_status
- Signed profile: annual_non_ira_income, marginal_tax_rate, philanthropic_intent,
  family_transfer_priority
- Trust candidate: asset_value, expected_growth_rate, grat_term_years,
  grat_annuity_rate, crat_term_years, crat_payout_rate
- Tax policy: estate_tax_exemption[planning_year], estate_tax_rate,
  charitable_deduction_rate, max_crat_term_years

### Source Document Resolution

Same precedence order. For client goals (philanthropic_intent,
family_transfer_priority), prefer SIGNED_PROFILE over CRM_NOTE. For asset values
and trust parameters, prefer ATTORNEY_MEMO or SIGNED_PROFILE.

### Computation Model

#### Estate Context

```
taxable_estate = max(0, estate_value - estate_tax_exemption)
estate_tax_exposure = taxable_estate * estate_tax_rate
liquidity_gap = max(0, estate_tax_exposure - liquid_assets)
```

All values rounded to cents.

#### GRAT Projection

```
annuity = asset_value * grat_annuity_rate
projected_remainder = asset_value * (1 + expected_growth_rate)^grat_term_years
                    - annuity * grat_term_years
estimated_estate_tax_reduction = projected_remainder * estate_tax_rate
```

- **term_years**: grat_term_years
- **mortality_inclusion_risk**: always "TERM_SURVIVAL_REQUIRED" (grantor must
  survive the term for remainder to pass estate-tax-free)
- Values rounded to cents.

#### CRAT Projection

```
annuity = asset_value * crat_payout_rate
projected_charitable_remainder = asset_value * (1 + expected_growth_rate)^crat_term_years
                                - annuity * crat_term_years
estimated_income_tax_deduction = projected_charitable_remainder * charitable_deduction_rate
```

- **term_years**: min(crat_term_years, max_crat_term_years)
- **family_transfer_fit**: determined by comparing CRAT remainder transfer to
  family vs GRAT remainder. If philanthropic_intent is high and the CRAT
  charitable remainder is large, family_transfer_fit is LOW.
  - HIGH: CRAT leaves meaningful family remainder
  - MODERATE: CRAT balances charitable and family
  - LOW: CRAT primarily benefits charity, limited family transfer
- All values rounded to cents.

#### Recommendation Logic

- **preferred_strategy**:
  - GRAT: when family_transfer_priority == "high" and philanthropic_intent != "high"
  - CRAT: when philanthropic_intent == "high" and family_transfer_priority != "high"

- **rationale_code**:
  - CHILDREN_TRANSFER_PRIORITY: when GRAT preferred
  - PHILANTHROPIC_PRIORITY: when CRAT preferred

- **alternate_role**:
  - SECONDARY_CHARITABLE_TOOL: when GRAT preferred (CRAT can still serve
    charitable goals)
  - SECONDARY_FAMILY_TRANSFER_TOOL: when CRAT preferred (GRAT can still serve
    family transfer goals)

### Script

Use `scripts/grat_crat.py` for deterministic computation. See SKILL.md.

