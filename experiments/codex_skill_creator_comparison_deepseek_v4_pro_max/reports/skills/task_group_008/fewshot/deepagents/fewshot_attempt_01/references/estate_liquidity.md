## Estate Liquidity Action Plan

Use when `analysis_type` is `estate_liquidity_action_plan`. This combines ILIT Crummey
assessment with trust transfer (GRAT vs CRAT) for comprehensive estate planning.

### Input Sources

All sources from ilit_crummey.md and trust_comparison.md apply. The key difference is
that this analysis integrates both and produces an ordered action set.

### Computation Model

#### Estate Context

Same as trust_comparison.md:

```
taxable_estate = max(0, estate_value - estate_tax_exemption)
estate_tax_exposure = taxable_estate * estate_tax_rate
liquidity_gap = max(0, estate_tax_exposure - liquid_assets)
```

Include `exemption_used` (the estate_tax_exemption for planning_year) and
`liquid_assets_available` (liquid_assets from client record) as additional
fields in the estate_context output.

#### ILIT Assessment

Same model as ilit_crummey.md:

- annual_exclusion_capacity: exclusion * beneficiary_count
- premium_gap: max(0, annual_premium - annual_exclusion_capacity)
- estate_inclusion_risk: risk flag from ilit model
- projected_outside_estate_if_implemented: death_benefit (assuming proper administration)

#### Trust Transfer Assessment

Same model as trust_comparison.md for both GRAT and CRAT:

- preferred_strategy: GRAT or CRAT based on goals
- projected_remainder_to_heirs: GRAT remainder
- estimated_estate_tax_reduction: GRAT remainder * estate_tax_rate
- projected_charitable_remainder: CRAT remainder

Compute both GRAT and CRAT projections even though only one is preferred.

#### Action Set Construction

Build a list of actions relevant to the client from these candidates:

- ATTORNEY_DRAFT_REVIEW: always included (attorney must review all plans)
- GRAT_FOR_APPRECIATING_SHARES: included when GRAT is the preferred trust strategy
- ILIT_CRUMMEY_NOTICE_CYCLE: included when a life insurance policy exists
- LIFETIME_EXEMPTION_ALLOCATION: included when premium_gap > 0
- CRAT_FOR_CHARITABLE_REMAINDER: included when CRAT is the preferred strategy and
  client has meaningful philanthropic intent

Filter to actions that are genuinely needed. Sort the final list alphabetically.

#### Recommendation Logic

- **primary_action**:
  - COMBINE_ILIT_AND_GRAT: policy exists, preferred_strategy is GRAT
  - CRAT_WITH_LIQUIDITY_REVIEW: preferred_strategy is CRAT, liquidity gap > 0
  - ILIT_WITH_EXEMPTION_REVIEW: policy exists but premium_gap > 0

- **sequencing**:
  - ILIT_FIRST_THEN_GRAT: ILIT + GRAT, no existing policy transfer
  - TRUST_DECISION_FIRST: when trust strategy is unclear or needs priority
  - ILIT_FIRST_THEN_ATTORNEY_REVIEW: existing policy transfer scenario

- **risk_flag**: same enum as ilit model

### Script

Use `scripts/roth_projection.py` and `scripts/grat_crat.py` for deterministic
computations. See SKILL.md.

