# Advisory API Reference

All endpoints are GET requests. The base URL is supplied as `API_BASE` in the task environment. See `environment_access.md` for the configured base.

## Clients

**`GET /api/clients`** — List all clients in the advisory environment.

Response: Array of objects with fields:
- `client_id` (string) — Stable client identifier
- `household_name` (string) — Display name
- `age` (integer) — Primary client age
- `marital_status` (string) — "married" or "single"
- `filing_status` (string) — "MFJ", "SINGLE", or "HOH"
- `planning_year` (integer) — Planning year (usually 2026)
- `estate_value` (number) — Total estate value in USD
- `liquid_assets` (number) — Liquid assets in USD
- `record_status` (string) — "active" or "monitoring"
- `advisor_team` (string) — Assigned team name

**`GET /api/clients/{client_id}`** — Single client by ID. Same field structure.

## Source Documents

**`GET /api/source-documents`** — All source documents across all clients. Filter by `client_id`.

Response: Array of objects with fields:
- `document_id` (string) — Unique document identifier
- `client_id` (string) — Which client this document belongs to
- `source_type` (string) — One of: `SIGNED_PROFILE`, `ATTORNEY_MEMO`, `CUSTODIAN_EXPORT`, `CRM_NOTE`, `STALE_MARKETING_INTAKE`
- `effective_date` (string) — ISO date of the document
- `title` (string) — Human-readable title
- `facts` (object) — Key-value facts from the document:
  - `annual_non_ira_income` (number) — Non-IRA annual income
  - `marginal_tax_rate` (number) — Decimal marginal rate (e.g., 0.32)
  - `beneficiary_count` (integer) — Number of beneficiaries
  - `philanthropic_intent` (string) — "low", "moderate", or "high"
  - `family_transfer_priority` (string) — "low", "moderate", or "high"
  - `age`, `planning_year`, `filing_status`, `marital_status` may also appear
  - `liquid_assets`, `estate_value` may appear in signed profiles and attorney memos

Not all documents contain all fact fields. CRM notes typically contain only income, beneficiary count, and philanthropic intent.

## Retirement Accounts

**`GET /api/retirement-accounts`** — All retirement accounts. Filter by `client_id`.

Response: Array of objects with fields:
- `account_id` (string) — Account identifier (e.g., "IRA-CLT-1001")
- `client_id` (string)
- `source_type` (string) — Typically `CUSTODIAN_EXPORT`
- `traditional_balance` (number) — Current traditional IRA balance
- `roth_balance` (number) — Current Roth IRA balance
- `expected_return` (number) — Annual expected return as decimal (e.g., 0.065)
- `rmd_start_age` (integer) — Age at which RMDs begin (typically 73)
- `recommended_conversion_years` (integer) — Recommended number of years for staged conversions

## Life Insurance

**`GET /api/life-insurance`** — All life insurance policies. Filter by `client_id`.

Response: Array of objects with fields:
- `policy_id` (string) — Policy identifier
- `client_id` (string)
- `proposed_owner` (string) — Typically "ILIT"
- `death_benefit` (number) — Policy death benefit in USD
- `annual_premium` (number) — Annual premium in USD
- `planned_contribution_date` (string) — ISO date for planned contribution
- `is_existing_policy_transfer` (boolean) — Whether this is a transfer of an existing policy (triggers three-year lookback)

## Trust Candidates

**`GET /api/trust-candidates`** — All trust transfer candidates. Filter by `client_id`.

Response: Array of objects with fields:
- `trust_case_id` (string) — Trust case identifier
- `client_id` (string)
- `asset_value` (number) — Value of assets to seed the trust
- `expected_growth_rate` (number) — Annual growth rate as decimal
- `grat_term_years` (integer) — Recommended GRAT term
- `grat_annuity_rate` (number) — GRAT annuity rate as decimal of principal
- `crat_term_years` (integer) — CRAT term (typically 20)
- `crat_payout_rate` (number) — CRAT payout rate as decimal of principal

## Tax Policies

**`GET /api/policies/tax`** — Static tax constants for the planning year.

Response: Object with fields:
- `policy_label` (string) — Description
- `annual_gift_exclusion` (object) — Per-year gift exclusion amounts: `{"2025": 19000, "2026": 20000}`
- `estate_tax_exemption` (object) — Per-year estate tax exemption amounts: `{"2025": 13990000, "2026": 13610000}`
- `estate_tax_rate` (number) — Estate tax rate as decimal (0.4)
- `conversion_bracket_targets` (object) — Income bracket targets for Roth conversions: `{"MFJ": 394600, "SINGLE": 197300, "HOH": 263500}`
- `max_crat_term_years` (integer) — Maximum CRAT term (20)
- `charitable_deduction_rate` (number) — Charitable deduction rate as decimal (0.35)

## RMD Factors

**`GET /api/rmd-factors`** — RMD divisors by age.

Response: Object mapping age (string key) to divisor (number). Age range: 73 through 99.

Example: `{"73": 26.5, "74": 25.5, ...}`
