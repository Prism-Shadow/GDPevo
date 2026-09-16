## ILIT Crummey Funding Cycle

Use when `analysis_type` is `ilit_crummey_implementation`. This covers irrevocable life
insurance trust setup with Crummey withdrawal-right notices.

### Input Sources

- Client record: age, filing_status, planning_year
- Signed profile: beneficiary_count, annual_non_ira_income, marginal_tax_rate
- Life insurance: death_benefit, annual_premium, planned_contribution_date,
  is_existing_policy_transfer
- Tax policy: annual_gift_exclusion[planning_year]
- Estate context: estate_value, estate_tax_exemption, estate_tax_rate, liquid_assets

### Source Document Resolution

Same precedence as roth_conversion.md. For beneficiary_count, prefer SIGNED_PROFILE
over CRM_NOTE. For policy details, prefer SIGNED_PROFILE or ATTORNEY_MEMO over CRM_NOTE.

### Computation Model

#### Gift Plan

- **planning_year**: from client record
- **annual_exclusion_per_beneficiary**: annual_gift_exclusion for planning_year
- **beneficiary_count**: from signed profile
- **annual_exclusion_capacity**: exclusion * beneficiary_count, rounded to cents
- **annual_premium**: from life insurance record
- **premium_gap**: max(0, annual_premium - annual_exclusion_capacity), rounded to cents

#### Administration Timeline

The Crummey timeline is computed from the planned_contribution_date:

- **contribution_date**: planned_contribution_date from policy
- **notice_due_date**: contribution_date + 7 calendar days
- **withdrawal_window_end**: contribution_date + 30 calendar days
  (standard Crummey power window)
- **earliest_premium_payment_date**: withdrawal_window_end + 1 calendar day
- **notices_required**: beneficiary_count
- **dedicated_bank_account_required**: true (best practice for ILIT)

All dates are ISO YYYY-MM-DD strings.

#### Estate Result

- **death_benefit**: from policy
- **estate_inclusion_risk**: mirrors recommendation.risk_flag
- **projected_outside_estate_if_implemented**: death_benefit when properly
  administered (full Crummey formalities met)
- **tax_liquidity_support**: death_benefit * estate_tax_rate, rounded to cents

#### Recommendation Logic

- **primary_action**:
  - FUND_WITH_CRUMMEY_NOTICES: premium_gap == 0, no existing policy transfer
  - USE_LIFETIME_EXEMPTION_FOR_SHORTFALL: premium_gap > 0
  - USE_NEW_POLICY_OR_ACCEPT_LOOKBACK: is_existing_policy_transfer == true and
    gap == 0
  - DISCLOSE_LOOKBACK_AND_USE_EXEMPTION: is_existing_policy_transfer == true and
    gap > 0

- **suitability**:
  - SUITABLE_WITH_ADMINISTRATION: gap == 0, no existing transfer
  - BORDERLINE: gap > 0 or existing transfer
  - NOT_SUITABLE: beneficiary_count == 0 or death_benefit <= 0

- **risk_flag**:
  - LOW_IF_FORMALITIES_MET: gap == 0, no existing transfer
  - EXCLUSION_SHORTFALL: gap > 0, no existing transfer
  - THREE_YEAR_LOOKBACK: existing transfer, gap == 0
  - THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL: existing transfer, gap > 0

### Script

Use `scripts/crummey_timeline.py` for date arithmetic. See SKILL.md.

