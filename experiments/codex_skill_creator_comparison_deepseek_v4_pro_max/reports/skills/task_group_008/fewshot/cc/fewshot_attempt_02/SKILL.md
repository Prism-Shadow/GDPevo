---
name: wealth-advisory-planner
description: Produce structured private-wealth planning JSON reports (Roth conversion RMD analysis, ILIT Crummey funding, GRAT vs CRAT comparisons, estate liquidity action plans) by querying a REST advisory API, reconciling conflicting multi-source client records, and computing domain-specific projections. Use this skill whenever the user asks for wealth advisory planning output, financial planning reports, estate tax projections, retirement distribution analysis, ILIT or trust planning, Roth conversion comparisons, or any client-specific structured planning deliverable for a private wealth team.
---

# Wealth Advisory Planner

You are supporting a private wealth advisory team. Produce structured JSON planning reports by querying a REST API that models a multi-source advisory environment, reconciling conflicts between records, and performing domain-specific calculations.

## Workflow

Follow this sequence for every engagement:

1. **Read the request memo** -- it names the client ID, engagement type, and any special parameters (e.g. planning horizon year). These become your north star.
2. **Read the answer template** -- note every required key, enum, type, and constraint. Your output must match this exactly.
3. **Fetch all relevant API data** -- call every endpoint needed for the analysis type. See [references/api_reference.md](references/api_reference.md) for endpoint details.
4. **Reconcile sources** -- compare records from different endpoints and resolve conflicts. See **Source Resolution** below.
5. **Compute domain numbers** -- apply the formulas for the analysis type. See [references/calculations.md](references/calculations.md).
6. **Emit exactly the JSON object** -- no prose outside it, no wrapping, no markdown fences. Numbers must be JSON numbers (not strings), USD amounts rounded to cents, dates in ISO YYYY-MM-DD.

## API Strategy

The advisory API is available at the environment variable `API_BASE` set by the harness. All endpoints are read-only GETs. No authentication header is needed.

**Always fetch these in parallel when applicable.** The API reference lists which endpoints to use for each analysis type.

**Endpoint summary** (full details in [references/api_reference.md](references/api_reference.md)):

- `GET /api/clients` -- list of all client records (multiple may exist for the same client_id from different source systems)
- `GET /api/clients/{client_id}` -- single client's consolidated profile
- `GET /api/source-documents` -- all source documents with timestamps, types, and metadata
- `GET /api/retirement-accounts` -- all retirement account records
- `GET /api/life-insurance` -- all life insurance policy records
- `GET /api/trust-candidates` -- trust planning candidates
- `GET /api/policies/tax` -- current tax policy constants (rates, brackets, exemptions)
- `GET /api/rmd-factors` -- IRS RMD distribution period factors by age
- `GET /portal/client/{client_id}` -- web portal summary (for cross-checking)

**Key data points from each endpoint** (see the reference file for full response shapes):

- **Clients**: age/birth_date, filing_status, taxable_income, state, profile_source, account_source, goal_source, policy_source
- **Source documents**: source_type, created_date, client_id, document_type, raw_system_name, content fields
- **Retirement accounts**: account_type, balance, owner_client_id, custodian, tax_deferred flag, existing_roth_balance
- **Life insurance**: policy_type, death_benefit, annual_premium, owner_client_id, issue_date, beneficiary_count, policy_source
- **Trust candidates**: trust_type, assets_available, income_beneficiaries, remainder_beneficiaries, term_years, applicable_federal_rate
- **Tax policies**: marginal_rate_schedule, standard_deduction, annual_gift_exclusion, lifetime_estate_exemption, estate_tax_rate, top_income_tax_rate, long_term_capital_gains_rate, section_7520_rate, IRC_2035_lookback_years
- **RMD factors**: age-to-distribution-period mapping
- **Portal**: cross-check summary of total assets, policies, and beneficiaries

## Source Resolution

Client records may conflict because they were imported from different advisory systems at different times. When a piece of data appears in multiple sources with different values, choose the controlling source by authority and recency.

**General hierarchy** (most to least authoritative):

1. `SIGNED_PROFILE` -- the client's signed financial profile, most authoritative for goals, beneficiaries, and household facts
2. `ATTORNEY_MEMO` -- attorney-prepared memo, most authoritative for asset titling and trust structures
3. `CUSTODIAN_EXPORT` -- direct custodian data feed, most authoritative for account balances and holdings
4. `CRM_NOTE` -- advisor notes from the CRM system
5. `STALE_MARKETING_INTAKE` -- old marketing intake form, least authoritative

**Domain-specific rules:**

- **Account balances**: CUSTODIAN_EXPORT beats SIGNED_PROFILE beats CRM_NOTE. The custodian has the actual settlement data.
- **Client demographics (age, filing status)**: SIGNED_PROFILE beats everything. This is the client's confirmed self-report.
- **Beneficiary counts and identities**: SIGNED_PROFILE beats ATTORNEY_MEMO beats CUSTODIAN_EXPORT.
- **Policy details (death benefit, premium)**: SIGNED_PROFILE beats ATTORNEY_MEMO beats CUSTODIAN_EXPORT. The signed policy application or in-force illustration controls.
- **Client goals and priorities**: SIGNED_PROFILE beats ATTORNEY_MEMO beats CRM_NOTE beats STALE_MARKETING_INTAKE.
- **Asset titling and ownership**: ATTORNEY_MEMO beats SIGNED_PROFILE beats CRM_NOTE. The attorney's title review controls.

**How to resolve a conflict:**
1. Find all records for the client across the raw API responses.
2. Group by domain (profile, accounts, goals, policies).
3. Within each domain, pick the source with the highest authority in the hierarchy above.
4. If two sources have equal authority, pick the one with the most recent `created_date` in source-documents.
5. Record the chosen source in `source_resolution` fields.

## Analysis Types

The skill handles four engagement types. Each expects a specific JSON template.

### roth_conversion_rmd

Staged Roth conversion analysis with RMD tax projections and legacy balance projections.

**Relevant endpoints**: `/api/clients/{id}`, `/api/retirement-accounts`, `/api/policies/tax`, `/api/rmd-factors`, `/api/source-documents`, `/portal/client/{id}`

**Template keys**: `recommendation`, `conversion_plan`, `rmd_projection`, `legacy_projection`, `source_resolution` (profile + account)

### ilit_crummey_implementation

ILIT funding verification with Crummey notice timing, gift-tax exclusion math, and estate inclusion risk assessment.

**Relevant endpoints**: `/api/clients/{id}`, `/api/life-insurance`, `/api/policies/tax`, `/api/source-documents`, `/portal/client/{id}`

**Template keys**: `recommendation`, `gift_plan`, `administration`, `estate_result`, `source_resolution` (beneficiary + policy)

### trust_comparison

Side-by-side GRAT versus CRAT comparison with estate tax and legacy projections.

**Relevant endpoints**: `/api/clients/{id}`, `/api/trust-candidates`, `/api/policies/tax`, `/api/source-documents`, `/portal/client/{id}`

**Template keys**: `recommendation`, `estate_context`, `grat`, `crat`, `source_resolution` (goal + asset)

### estate_liquidity_action_plan

Combined ILIT and trust transfer with action sequencing and liquidity gap analysis.

**Relevant endpoints**: `/api/clients/{id}`, `/api/life-insurance`, `/api/trust-candidates`, `/api/policies/tax`, `/api/source-documents`, `/portal/client/{id}`

**Template keys**: `recommendation`, `estate_context`, `ilit`, `trust_transfer`, `action_set`, `source_resolution` (goal + policy)

## Output Rules

- Return exactly one JSON object. No surrounding text, no markdown fences, no trailing commas.
- Every number is a JSON number (not a string).
- USD amounts: round to cents (two decimal places).
- Dates: ISO 8601 YYYY-MM-DD format.
- Enums: use the exact string values listed in the template. Do not invent new values.
- `action_set`: sort the array alphabetically.
- `task_id`: copy from the request memo or prompt (e.g. `"task_001"`, the test harness supplies it).
- Required keys must all be present, even if some values are zero or empty.

## Calculation Notes

See [references/calculations.md](references/calculations.md) for the detailed formulas and step-by-step guidance for each analysis type. Do not guess at formulas -- consult that reference.

Key principles:
- Roth conversions are staged over multiple years up to a tax-bracket ceiling.
- RMD projections use the IRS Uniform Lifetime Table factors from `/api/rmd-factors`.
- GRAT remainder uses the IRC 7520 rate (from `/api/policies/tax`) with mortality/survival assumptions.
- CRAT charitable remainder is computed from the trust's payment stream and term.
- Gift tax exclusion capacity is `annual_exclusion_per_beneficiary * beneficiary_count`.
- Estate tax exposure = `max(0, taxable_estate - remaining_exemption) * estate_tax_rate`.
- For `conversion_years_positive`, it must equal `conversion_years` (same value).
- The `first_rmd_year` is the year the client turns the RMD starting age (from `rmd_starting_age` in tax policies).

## Cross-Checking

After computing the output:
- Verify that `total_converted = conversion_years * annual_conversion_amount`.
- Verify that `conversion_years_positive = conversion_years`.
- Verify that `rmd_tax_savings = baseline_rmd_tax - conversion_rmd_tax` (non-negative).
- Verify `premium_gap = max(0, annual_premium - annual_exclusion_capacity)`.
- Verify `estate_tax_exposure` is consistent with `taxable_estate`, exemption, and rate.
- For the ILIT, verify `notices_required = beneficiary_count`.
- For `action_set`, verify the array is sorted alphabetically.
