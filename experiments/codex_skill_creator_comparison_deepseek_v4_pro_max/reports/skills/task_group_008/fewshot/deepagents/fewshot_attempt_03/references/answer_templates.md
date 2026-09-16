## Answer Template Reference

Always read the answer_template.json in the task payloads directory to get the exact required_top_level_keys and field enums. The sections below summarize common patterns across analysis types.

### Common Keys Shared Across Templates

- `task_id`: From the prompt context (e.g. train_001, test_001). The prompt text or directory name indicates this.
- `client_id`: From the request_memo.md.
- `analysis_type`: From the answer_template.json `fields.analysis_type` enum.
- `source_resolution`: Always present; see [source_resolution.md](source_resolution.md) for rules.

### roth_conversion_rmd Template

Top-level keys: `task_id, client_id, analysis_type, recommendation, conversion_plan, rmd_projection, legacy_projection, source_resolution`

recommendation fields: `primary_action`, `suitability`, `risk_flag`

conversion_plan fields: `first_conversion_year`, `conversion_years`, `conversion_years_positive`, `annual_conversion_amount`, `total_converted`, `total_conversion_tax`

rmd_projection fields: `horizon_year`, `first_rmd_year`, `baseline_rmd_tax_through_horizon`, `conversion_rmd_tax_through_horizon`, `rmd_tax_savings_through_horizon`

legacy_projection fields: `projected_roth_balance_horizon`, `projected_traditional_balance_horizon`, `heir_tax_profile`

### ilit_crummey_implementation Template

Top-level keys: `task_id, client_id, analysis_type, recommendation, gift_plan, administration, estate_result, source_resolution`

gift_plan fields: `planning_year`, `annual_exclusion_per_beneficiary`, `beneficiary_count`, `annual_exclusion_capacity`, `annual_premium`, `premium_gap`

administration fields: `notices_required`, `contribution_date`, `notice_due_date`, `withdrawal_window_end`, `earliest_premium_payment_date`, `dedicated_bank_account_required`

estate_result fields: `death_benefit`, `estate_inclusion_risk`, `projected_outside_estate_if_implemented`, `tax_liquidity_support`

### trust_comparison Template

Top-level keys: `task_id, client_id, analysis_type, recommendation, estate_context, grat, crat, source_resolution`

estate_context fields: `planning_year`, `exemption_used`, `taxable_estate`, `estate_tax_exposure`, `liquid_assets_available`, `liquidity_gap_before_planning`

grat fields: `term_years`, `projected_remainder_to_heirs`, `estimated_estate_tax_reduction`, `mortality_inclusion_risk`

crat fields: `term_years`, `projected_charitable_remainder`, `estimated_income_tax_deduction`, `family_transfer_fit`

### estate_liquidity_action_plan Template

Top-level keys: `task_id, client_id, analysis_type, recommendation, estate_context, ilit, trust_transfer, action_set, source_resolution`

action_set must be sorted alphabetically.

### Enum Reference

**primary_action (roth)**: STAGED_ROTH_CONVERSION, DEFER, NO_CONVERSION

**suitability (roth)**: SUITABLE, BORDERLINE, DEFER

**risk_flag (roth)**: TAX_BRACKET_MANAGEMENT, LIQUIDITY_CONSTRAINT, RMD_NEAR_TERM

**primary_action (ilit)**: FUND_WITH_CRUMMEY_NOTICES, USE_LIFETIME_EXEMPTION_FOR_SHORTFALL, USE_NEW_POLICY_OR_ACCEPT_LOOKBACK, DISCLOSE_LOOKBACK_AND_USE_EXEMPTION

**suitability (ilit)**: SUITABLE_WITH_ADMINISTRATION, BORDERLINE, NOT_SUITABLE

**risk_flag (ilit)**: LOW_IF_FORMALITIES_MET, EXCLUSION_SHORTFALL, THREE_YEAR_LOOKBACK, THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL

**preferred_strategy**: GRAT, CRAT

**rationale_code**: CHILDREN_TRANSFER_PRIORITY, PHILANTHROPIC_PRIORITY

**alternate_role**: SECONDARY_CHARITABLE_TOOL, SECONDARY_FAMILY_TRANSFER_TOOL

**family_transfer_fit**: LOW, MODERATE, HIGH

**mortality_inclusion_risk**: TERM_SURVIVAL_REQUIRED

**primary_action (estate)**: COMBINE_ILIT_AND_GRAT, CRAT_WITH_LIQUIDITY_REVIEW, ILIT_WITH_EXEMPTION_REVIEW

**sequencing**: ILIT_FIRST_THEN_GRAT, TRUST_DECISION_FIRST, ILIT_FIRST_THEN_ATTORNEY_REVIEW

**action_set members**: ATTORNEY_DRAFT_REVIEW, CRAT_FOR_CHARITABLE_REMAINDER, GRAT_FOR_APPRECIATING_SHARES, ILIT_CRUMMEY_NOTICE_CYCLE, LIFETIME_EXEMPTION_ALLOCATION

**heir_tax_profile**: MOSTLY_TAX_FREE, MIXED_TAXABLE_AND_TAX_FREE, MOSTLY_TAXABLE

**source_type enums**: SIGNED_PROFILE, ATTORNEY_MEMO, CUSTODIAN_EXPORT, CRM_NOTE, STALE_MARKETING_INTAKE

### Field Type Notes

- Numbers must be JSON numbers, not strings
- USD amounts always rounded to 2 decimal places
- Dates ISO YYYY-MM-DD
- Years as integers
- Booleans as JSON true/false
- Enums as exact strings matching the template
