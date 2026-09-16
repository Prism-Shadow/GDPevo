# Advisory API Endpoint Catalog

Base URL: `API_BASE` (supplied by harness, e.g. `http://task-env:9008`)

All endpoints are read-only GET. No authentication required. All responses are JSON arrays or objects.

---

## GET /api/clients

Returns the full list of all client records.

Each record:

| Field | Type | Meaning |
|-------|------|---------|
| `client_id` | string | Stable identifier, e.g. `"CLT-1001"` |
| `household_name` | string | Display name |
| `age` | integer | Client age in planning year |
| `marital_status` | string | `"married"` or `"single"` |
| `filing_status` | string | `"MFJ"`, `"SINGLE"`, or `"HOH"` |
| `planning_year` | integer | Current planning year (2026) |
| `estate_value` | number | Gross estate value in USD |
| `liquid_assets` | number | Liquid assets available in USD |
| `record_status` | string | `"active"` or `"monitoring"` |
| `advisor_team` | string | Advisory team assignment |

## GET /api/clients/{client_id}

Same shape as above but returns a single client object (not an array). Use this for the target client.

---

## GET /api/source-documents

Returns a flat array of all source documents across all clients. Filter by `client_id` in memory.

Each document:

| Field | Type | Meaning |
|-------|------|---------|
| `document_id` | string | e.g. `"DOC-CLT-1001-SIGNED"` |
| `client_id` | string | Owning client |
| `source_type` | string | One of the source-type enums (see source-resolution.md) |
| `effective_date` | string | ISO date when recorded/imported |
| `title` | string | Human-readable label |
| `facts` | object | Key-value pairs the document asserts |

The `facts` object varies by document. Common fields: `annual_non_ira_income`, `marginal_tax_rate`, `beneficiary_count`, `philanthropic_intent`, `family_transfer_priority`, `age`, `planning_year`, `filing_status`, `marital_status`, `liquid_assets`, `estate_value`.

Not every document carries every field. Only the `SIGNED_PROFILE` type carries the full set. `CRM_NOTE` and `ATTORNEY_MEMO` carry subsets.

---

## GET /api/retirement-accounts

Returns a flat array of all retirement account records. Filter by `client_id`.

Each record:

| Field | Type | Meaning |
|-------|------|---------|
| `account_id` | string | e.g. `"IRA-CLT-1001"` |
| `client_id` | string | Owning client |
| `source_type` | string | Always `"CUSTODIAN_EXPORT"` |
| `traditional_balance` | number | Current pre-tax IRA balance in USD |
| `roth_balance` | number | Current Roth IRA balance in USD |
| `expected_return` | number | Annual expected return as a decimal (e.g. 0.065 = 6.5%) |
| `rmd_start_age` | integer | Age at which RMDs begin (always 73) |
| `recommended_conversion_years` | integer | Model-recommended number of conversion years |

Accounts are always `source_type: "CUSTODIAN_EXPORT"`. They are the authoritative source for account balances and expected returns.

---

## GET /api/life-insurance

Returns a flat array of all life insurance policy records. Filter by `client_id`.

Each record:

| Field | Type | Meaning |
|-------|------|---------|
| `policy_id` | string | e.g. `"LIFE-CLT-1001"` |
| `client_id` | string | Owning client |
| `proposed_owner` | string | Always `"ILIT"` |
| `death_benefit` | number | Face value of the policy in USD |
| `annual_premium` | number | Annual premium in USD |
| `planned_contribution_date` | string | ISO date for planned contribution |
| `is_existing_policy_transfer` | boolean | Whether this is a transfer of an existing policy (true) or a new policy (false) |

---

## GET /api/trust-candidates

Returns a flat array of all trust candidate records. Filter by `client_id`.

Each record:

| Field | Type | Meaning |
|-------|------|---------|
| `trust_case_id` | string | e.g. `"TRUST-CLT-1001"` |
| `client_id` | string | Owning client |
| `asset_value` | number | Value of assets to place in the trust in USD |
| `expected_growth_rate` | number | Annual growth rate as decimal |
| `grat_term_years` | integer | Recommended GRAT term |
| `grat_annuity_rate` | number | GRAT annuity rate as decimal (7520 rate) |
| `crat_term_years` | integer | CRAT term (always 20 for this data) |
| `crat_payout_rate` | number | CRAT payout rate as decimal |

---

## GET /api/policies/tax

Returns a single global policy object.

| Field | Type | Meaning |
|-------|------|---------|
| `policy_label` | string | Label ("Advisory internal 2026 planning constants") |
| `annual_gift_exclusion` | object | Map year (string) → per-donee exclusion in USD |
| `estate_tax_exemption` | object | Map year (string) → exemption amount in USD |
| `estate_tax_rate` | number | Federal estate tax rate as decimal (0.4 = 40%) |
| `conversion_bracket_targets` | object | Map filing status → taxable-income target for conversion |
| `max_crat_term_years` | integer | Maximum CRAT term (20) |
| `charitable_deduction_rate` | number | Charitable deduction rate as decimal (0.35) |

`conversion_bracket_targets` maps `filing_status` to the upper bound of the target bracket in dollars:
- `"MFJ"`: 394600
- `"SINGLE"`: 197300
- `"HOH"`: 263500

---

## GET /api/rmd-factors

Returns a single object mapping integer age (as string keys) to the RMD divisor for that age.

Example: `{"73": 26.5, "74": 25.5, ...}`

Ages range from 73 through 99. The divisor declines with age. Use the divisor corresponding to the client's age at the start of each RMD year.
