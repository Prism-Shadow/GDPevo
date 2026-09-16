# Enum Decision Logic

Every enum value in the output must exactly match one of the allowed values from the answer template. These rules determine which value to select based on the data.

## Roth Conversion Enums

### recommendation.primary_action
- `STAGED_ROTH_CONVERSION` — Use when the client has a positive conversion amount and the horizon is beyond RMD start. This is the default when the numbers support conversion.
- `DEFER` — Use when conversion provides minimal tax savings (e.g., very small bracket headroom or near-zero conversion amount).
- `NO_CONVERSION` — Use when conversion is not recommended (e.g., client already past RMD age with no room).

From train evidence: both train_001 and train_005 used `STAGED_ROTH_CONVERSION` when bracket_headroom > 0.

### recommendation.suitability
- `SUITABLE` — Conversion plan has meaningful tax savings (rmd_tax_savings > 0 and total_converted is substantial relative to traditional balance).
- `BORDERLINE` — Savings exist but are modest.
- `DEFER` — Not suitable at this time.

From train evidence: both suits used `SUITABLE`.

### recommendation.risk_flag
- `TAX_BRACKET_MANAGEMENT` — Primary concern is staying within bracket targets during conversion years.
- `LIQUIDITY_CONSTRAINT` — Client may not have liquid assets to pay conversion taxes.
- `RMD_NEAR_TERM` — RMDs start within 1-2 years, limiting conversion runway.

From train evidence: `TAX_BRACKET_MANAGEMENT` was used when bracket_target - income determined the annual conversion amount.

### legacy_projection.heir_tax_profile
- `MOSTLY_TAX_FREE` — Roth balance >> traditional balance at horizon.
- `MIXED_TAXABLE_AND_TAX_FREE` — Roth and traditional balances are in the same order of magnitude at horizon.
- `MOSTLY_TAXABLE` — Traditional balance >> Roth balance at horizon.

From train evidence: `MIXED_TAXABLE_AND_TAX_FREE` was used in both train_001 and train_005 where balances were within ~50% of each other.

### source_resolution.controlling_profile_source
Priority order: `SIGNED_PROFILE` > `ATTORNEY_MEMO` > `CRM_NOTE` > `STALE_MARKETING_INTAKE`.
Select the highest-priority source that provides the profile facts used in calculations.

### source_resolution.controlling_account_source
Priority order: `CUSTODIAN_EXPORT` > `SIGNED_PROFILE` > `CRM_NOTE`.

## ILIT Crummey Enums

### recommendation.primary_action
- `FUND_WITH_CRUMMEY_NOTICES` — Premium fits within annual exclusion capacity and no existing-policy-transfer issues.
- `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` — Premium exceeds exclusion capacity but other factors are clean.
- `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` — Existing policy transfer (three-year lookback) with no exclusion shortfall.
- `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` — Both three-year lookback and exclusion shortfall.

Decision logic:
1. If `premium_gap > 0` AND `is_existing_policy_transfer = true` → `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`
2. If `is_existing_policy_transfer = true` (but gap = 0) → `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`
3. If `premium_gap > 0` (but no transfer) → `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`
4. Otherwise → `FUND_WITH_CRUMMEY_NOTICES`

### recommendation.suitability
- `SUITABLE_WITH_ADMINISTRATION` — Plan works with proper Crummey notice administration.
- `BORDERLINE` — Plan has complications but may still work.
- `NOT_SUITABLE` — Plan cannot be implemented cleanly.

### recommendation.risk_flag / estate_result.estate_inclusion_risk
Same values:
- `LOW_IF_FORMALITIES_MET` — No existing-policy-transfer and no exclusion shortfall.
- `EXCLUSION_SHORTFALL` — Premium exceeds annual exclusion capacity.
- `THREE_YEAR_LOOKBACK` — Existing policy transfer (lookback risk) without exclusion shortfall.
- `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` — Both risks present.

### source_resolution.controlling_beneficiary_source
Priority: `SIGNED_PROFILE` > `ATTORNEY_MEMO` > `CUSTODIAN_EXPORT` > `CRM_NOTE` > `STALE_MARKETING_INTAKE`

### source_resolution.controlling_policy_source
Priority: `SIGNED_PROFILE` > `ATTORNEY_MEMO` > `CUSTODIAN_EXPORT` > `CRM_NOTE`

## Trust Comparison Enums

### recommendation.preferred_strategy
- `GRAT` — Family transfer priority is "high" and philanthropic intent is "low" or "moderate". The GRAT remainder goes to heirs.
- `CRAT` — Philanthropic intent is "high" and family transfer priority is "moderate" or "low".
Rule: family_transfer_priority = "high" → `GRAT`; philanthropic_intent = "high" → `CRAT`.
When both are "high", family_transfer_priority wins → `GRAT`.
When both are "moderate", default to `GRAT`.

### recommendation.rationale_code
- `CHILDREN_TRANSFER_PRIORITY` — When GRAT is preferred.
- `PHILANTHROPIC_PRIORITY` — When CRAT is preferred.

### recommendation.alternate_role
- `SECONDARY_CHARITABLE_TOOL` — When GRAT is primary (CRAT can serve charitable goals secondarily).
- `SECONDARY_FAMILY_TRANSFER_TOOL` — When CRAT is primary (GRAT can serve family transfer goals secondarily).

### crat.family_transfer_fit
- `LOW` — CRAT does not transfer wealth to family.
- `MODERATE` — CRAT has some family benefit through reduced estate.
- `HIGH` — CRAT aligns well with family goals.

From train evidence: `LOW` when family_transfer_priority = "high" (CRAT doesn't transfer wealth to heirs).

### grat.mortality_inclusion_risk
Always `TERM_SURVIVAL_REQUIRED` — GRAT remainder depends on the grantor surviving the term.

### source_resolution.controlling_goal_source
Priority: `SIGNED_PROFILE` > `ATTORNEY_MEMO` > `CUSTODIAN_EXPORT` > `CRM_NOTE` > `STALE_MARKETING_INTAKE`

### source_resolution.controlling_asset_source
Priority: `ATTORNEY_MEMO` > `SIGNED_PROFILE` > `CRM_NOTE`

## Estate Liquidity Enums

### recommendation.primary_action
- `COMBINE_ILIT_AND_GRAT` — Both ILIT and GRAT strategies apply (estate tax exposure + ILIT policy exists).
- `CRAT_WITH_LIQUIDITY_REVIEW` — CRAT preferred with liquidity focus.
- `ILIT_WITH_EXEMPTION_REVIEW` — ILIT with lifetime exemption review.

Decision logic: Check whether ILIT policy exists for client. Check trust candidates. If both exist: `COMBINE_ILIT_AND_GRAT`.

### recommendation.sequencing
- `ILIT_FIRST_THEN_GRAT` — Implement ILIT Crummey cycle first, then fund the GRAT.
- `TRUST_DECISION_FIRST` — Choose trust strategy first.
- `ILIT_FIRST_THEN_ATTORNEY_REVIEW` — ILIT first, then attorney review.

### recommendation.risk_flag
Same options as ILIT risk_flag.

### trust_transfer.preferred_strategy
Same logic as trust comparison: `GRAT` or `CRAT`.

### action_set
Allowed values (from template):
- `ATTORNEY_DRAFT_REVIEW`
- `CRAT_FOR_CHARITABLE_REMAINDER`
- `GRAT_FOR_APPRECIATING_SHARES`
- `ILIT_CRUMMEY_NOTICE_CYCLE`
- `LIFETIME_EXEMPTION_ALLOCATION`

Select the subset of actions needed and sort alphabetically. From train_004: when ILIT exists and GRAT is preferred → `ATTORNEY_DRAFT_REVIEW`, `GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`.

## Source Resolution Enums (shared)

All source resolution fields use the same priority hierarchy but with different candidate source types per field. See [source-resolution.md](source-resolution.md) for the full rules.
