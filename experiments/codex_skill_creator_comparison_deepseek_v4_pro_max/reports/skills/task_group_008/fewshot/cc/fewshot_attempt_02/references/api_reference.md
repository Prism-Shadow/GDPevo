# Advisory API Reference

All requests use the base URL from `API_BASE` (set by the test harness). Every endpoint returns JSON. No auth required. No query parameters needed.

## Endpoint Details

### GET /api/clients

Returns an array of all client records. Multiple records may exist for the same `client_id` because they were imported from different source systems (a `SIGNED_PROFILE` record, a `CRM_NOTE` record, a `STALE_MARKETING_INTAKE` record, etc.).

**Response shape (each element):**
```json
{
  "client_id": "CLT-xxxx",
  "full_name": "...",
  "birth_date": "YYYY-MM-DD",
  "age": integer,
  "filing_status": "MFJ" | "SINGLE" | "HOH",
  "taxable_income": number,
  "state": "CA" | "NY" | "TX" | ...,
  "profile_source": "SIGNED_PROFILE" | "CRM_NOTE" | ...,
  "account_source": "CUSTODIAN_EXPORT" | "SIGNED_PROFILE" | ...,
  "goal_source": "SIGNED_PROFILE" | "ATTORNEY_MEMO" | ...
}
```

### GET /api/clients/{client_id}

Returns a consolidated client object for the given `client_id`. This is the resolved view -- the system may have already reconciled some fields, but cross-check with raw sources.

**Response shape:**
```json
{
  "client_id": "CLT-xxxx",
  "full_name": "...",
  "birth_date": "YYYY-MM-DD",
  "age": integer,
  "filing_status": "MFJ" | "SINGLE" | "HOH",
  "taxable_income": number,
  "state": "...",
  "profile_source": "...",
  "account_source": "...",
  "goal_source": "...",
  "policy_source": "..."
}
```

### GET /api/source-documents

Returns all source documents. Each document has a type, a system of origin, a creation date, and a client association. Use this to audit conflicts and pick the most recent record.

**Response shape (array of):**
```json
{
  "document_id": "...",
  "client_id": "CLT-xxxx",
  "document_type": "SIGNED_PROFILE" | "ATTORNEY_MEMO" | "CUSTODIAN_EXPORT" | "CRM_NOTE" | "STALE_MARKETING_INTAKE",
  "raw_system_name": "...",
  "created_date": "YYYY-MM-DD",
  "source_type": "...",
  "content": { ... varying fields ... }
}
```

### GET /api/retirement-accounts

Returns all retirement accounts across all clients. Filter by `owner_client_id` for the target client.

**Response shape (array of):**
```json
{
  "account_id": "...",
  "owner_client_id": "CLT-xxxx",
  "account_type": "TRADITIONAL_IRA" | "ROTH_IRA" | "401K" | "403B" | "ROLLOVER_IRA" | ...,
  "balance": number,
  "custodian": "...",
  "tax_deferred": boolean,
  "existing_roth_balance": number
}
```

### GET /api/life-insurance

Returns all life insurance policies. Filter by `owner_client_id` for the target client.

**Response shape (array of):**
```json
{
  "policy_id": "...",
  "owner_client_id": "CLT-xxxx",
  "policy_type": "ILIT" | "TERM" | "WHOLE_LIFE" | "UL" | "VUL" | ...,
  "death_benefit": number,
  "annual_premium": number,
  "issue_date": "YYYY-MM-DD",
  "beneficiary_count": integer,
  "policy_source": "SIGNED_PROFILE" | "ATTORNEY_MEMO" | "CUSTODIAN_EXPORT" | "CRM_NOTE"
}
```

### GET /api/trust-candidates

Returns all trust planning candidates. Each candidate represents a trust structure that could be established.

**Response shape (array of):**
```json
{
  "candidate_id": "...",
  "client_id": "CLT-xxxx",
  "trust_type": "GRAT" | "CRAT" | "ILIT" | ...,
  "assets_available": number,
  "income_beneficiaries": [...],
  "remainder_beneficiaries": [...],
  "term_years": integer,
  "applicable_federal_rate": number
}
```

### GET /api/policies/tax

Returns current tax policy constants. These are the benchmark numbers for all computations.

**Response shape:**
```json
{
  "marginal_rate_schedule": [{"bracket_floor": number, "rate": number}, ...],
  "standard_deduction": number,
  "annual_gift_exclusion": number,
  "lifetime_estate_exemption": number,
  "estate_tax_rate": number,
  "top_income_tax_rate": number,
  "long_term_capital_gains_rate": number,
  "section_7520_rate": number,
  "IRC_2035_lookback_years": integer,
  "rmd_starting_age": integer
}
```

### GET /api/rmd-factors

Returns the IRS Uniform Lifetime Table as an array of age-to-distribution-period mappings.

**Response shape (array of):**
```json
{ "age": integer, "distribution_period": number }
```

### GET /portal/client/{client_id}

Returns a web portal summary for the client. This is a read-only aggregate view. Use it to cross-check your derived numbers against the system's totals (total assets, total policies, beneficiary summary). It does not replace the detailed API calls; it is a sanity reference.

**Response shape:**
```json
{
  "client_id": "CLT-xxxx",
  "total_assets": number,
  "total_policies": integer,
  "beneficiary_summary": "...",
  "last_updated": "YYYY-MM-DD"
}
```

## Endpoint Selection by Analysis Type

| Analysis Type | Required Endpoints |
|---|---|
| `roth_conversion_rmd` | `/api/clients/{id}`, `/api/retirement-accounts`, `/api/policies/tax`, `/api/rmd-factors`, `/api/source-documents`, `/portal/client/{id}` |
| `ilit_crummey_implementation` | `/api/clients/{id}`, `/api/life-insurance`, `/api/policies/tax`, `/api/source-documents`, `/portal/client/{id}` |
| `trust_comparison` | `/api/clients/{id}`, `/api/trust-candidates`, `/api/policies/tax`, `/api/source-documents`, `/portal/client/{id}` |
| `estate_liquidity_action_plan` | `/api/clients/{id}`, `/api/life-insurance`, `/api/trust-candidates`, `/api/policies/tax`, `/api/source-documents`, `/portal/client/{id}` |

Fetch `/api/source-documents` and `/api/policies/tax` for every engagement type -- they are always needed.
