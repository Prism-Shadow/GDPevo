# Analysis Types

## Shared rules

- Use only the fields in the provided answer template.
- JSON numbers must stay numeric.
- Round USD amounts to cents.
- Use ISO `YYYY-MM-DD` dates.
- Record provenance in `source_resolution` instead of hiding conflicts.
- Prefer signed profile for client intent, attorney memo for legal assumptions, custodian export for account facts, and CRM or stale intake only as fallback.

## `roth_conversion_rmd`

Required top-level keys:
`task_id`, `client_id`, `analysis_type`, `recommendation`, `conversion_plan`, `rmd_projection`, `legacy_projection`, `source_resolution`

Decision focus:

- Choose `STAGED_ROTH_CONVERSION` when multi-year conversions before RMD still improve the tax result without breaking bracket or liquidity constraints.
- Choose `DEFER` or `NO_CONVERSION` when near-term RMDs, liquidity pressure, or bracket risk makes staged conversion unattractive.
- Use `TAX_BRACKET_MANAGEMENT` unless RMD timing or liquidity is the main issue.
- Keep `conversion_years_positive` equal to `conversion_years`.
- Use the memo horizon in `rmd_projection.horizon_year` and the controlled source data for `first_rmd_year`.
- Report both horizon balances in `legacy_projection` and choose the heir tax profile from the facts, not from a preset pattern.
- Record profile provenance from `SIGNED_PROFILE` and account provenance from `CUSTODIAN_EXPORT` when those are the controlling sources.

## `ilit_crummey_implementation`

Required top-level keys:
`task_id`, `client_id`, `analysis_type`, `recommendation`, `gift_plan`, `administration`, `estate_result`, `source_resolution`

Decision focus:

- Choose `FUND_WITH_CRUMMEY_NOTICES` when annual exclusion capacity covers the premium.
- Use the shortfall or lookback actions only when the exclusion math or policy facts require them.
- Keep contribution, notice, withdrawal-window, and first premium dates internally consistent.
- Keep the estate inclusion risk aligned with the recommendation risk family.
- Record beneficiary and policy provenance from `SIGNED_PROFILE` unless a more authoritative memo overrides it.

## `trust_comparison`

Required top-level keys:
`task_id`, `client_id`, `analysis_type`, `recommendation`, `estate_context`, `grat`, `crat`, `source_resolution`

Decision focus:

- Choose `GRAT` when the client priority is family transfer or estate-tax reduction.
- Choose `CRAT` when charitable remainder or charitable deduction priority dominates.
- Set `rationale_code` to the priority that actually drove the recommendation.
- Use `alternate_role` for the other trust's secondary function.
- Fill both `grat` and `crat` numerically even when one is the weaker option.
- Record goal provenance from `SIGNED_PROFILE` and asset assumptions from `ATTORNEY_MEMO` when that memo controls.

## `estate_liquidity_action_plan`

Required top-level keys:
`task_id`, `client_id`, `analysis_type`, `recommendation`, `estate_context`, `ilit`, `trust_transfer`, `action_set`, `source_resolution`

Decision focus:

- Choose `COMBINE_ILIT_AND_GRAT` when the memo supports using both liquidity and transfer levers.
- Make sequencing reflect the operational order the case needs, often ILIT first when liquidity is the bottleneck.
- Keep `action_set` sorted alphabetically by the exact enum strings.
- Populate both the ILIT and trust-transfer sections even when one lever is secondary.
- Record goal provenance from `SIGNED_PROFILE` and policy provenance from the controlling policy source.

## Sanity check

If two sources conflict, select the one with higher authority and state that choice in `source_resolution`. Do not invent new enums, new keys, or explanatory prose outside the JSON object.
