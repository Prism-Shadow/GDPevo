# Advisory Workflow Reference

## API surface
- `API_BASE` is supplied by the harness.
- Use the endpoint that best matches the field being resolved:
  - `/api/clients/{client_id}` for client identity and household context
  - `/api/source-documents` for signed profiles, attorney memos, and other source documents
  - `/api/retirement-accounts` for balances, holdings, and account facts
  - `/api/life-insurance` for policy values, premiums, and beneficiaries
  - `/api/trust-candidates` for trust and transfer candidates
  - `/api/policies/tax` for tax policy constants and exclusions
  - `/api/rmd-factors` for RMD factors and ages
  - `/portal/client/{client_id}` for a consolidated client view when it helps
- Use only the records needed for the requested template.

## Source resolution
- Signed profile: client intent, beneficiaries, planning elections, and other affirmative client statements.
- Attorney memo: legal or planning directives, and asset or structure guidance when it clearly governs.
- Custodian export: balances, holdings, registration details, and current account status.
- CRM note / stale marketing intake: lowest-confidence context; use only if nothing better exists.
- When records conflict, choose one controlling source and reflect that choice in `source_resolution`; do not blend conflicting values.

## Template families

### `roth_conversion_rmd`
- Required top-level keys: `task_id`, `client_id`, `analysis_type`, `recommendation`, `conversion_plan`, `rmd_projection`, `legacy_projection`, `source_resolution`
- Keep all monetary fields numeric and rounded to cents.
- Use the memo's planning horizon year.
- Keep `analysis_type` set to `roth_conversion_rmd`.

### `ilit_crummey_implementation`
- Required top-level keys: `task_id`, `client_id`, `analysis_type`, `recommendation`, `gift_plan`, `administration`, `estate_result`, `source_resolution`
- Use ISO dates for all administration dates.
- Keep `dedicated_bank_account_required` boolean.
- Keep `estate_inclusion_risk` aligned with the risk flag enum.

### `trust_comparison`
- Required top-level keys: `task_id`, `client_id`, `analysis_type`, `recommendation`, `estate_context`, `grat`, `crat`, `source_resolution`
- Populate both comparison blocks even when only one strategy is preferred.
- Use the recommendation to reflect the client's dominant goal.

### `estate_liquidity_action_plan`
- Required top-level keys: `task_id`, `client_id`, `analysis_type`, `recommendation`, `estate_context`, `ilit`, `trust_transfer`, `action_set`, `source_resolution`
- `action_set` must contain only allowed enum values.
- Sort `action_set` alphabetically.

## Final check
- Match the template exactly.
- Use numbers for money and ISO strings for dates.
- Omit prose and omit any field not named in the template.
