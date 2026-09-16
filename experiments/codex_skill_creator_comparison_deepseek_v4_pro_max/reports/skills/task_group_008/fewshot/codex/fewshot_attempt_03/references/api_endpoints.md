# Advisory API Endpoints

Base URL: `{API_BASE}` (supplied by the harness, usually `http://task-env:9008/`).
No authentication required. All endpoints return JSON arrays or objects.

## Endpoints

### GET /api/clients

Returns an array of client objects. Filter by `client_id` locally.

```json
{
  "client_id": "CLT-1001",
  "household_name": "Mercer Household",
  "age": 66,
  "marital_status": "married",
  "filing_status": "MFJ",
  "planning_year": 2026,
  "estate_value": 18400000,
  "liquid_assets": 2100000,
  "record_status": "active",
  "advisor_team": "Private Wealth Tax and Estate Desk"
}
```

### GET /api/clients/{client_id}

Returns a single client object, same shape as above.

### GET /api/source-documents

Returns an array of source documents for all clients. Each document has a
`source_type` and `effective_date`. The same client may have multiple documents
from different sources with conflicting facts.

```json
{
  "document_id": "DOC-CLT-1001-SIGNED",
  "client_id": "CLT-1001",
  "source_type": "SIGNED_PROFILE",
  "effective_date": "2026-02-06",
  "title": "Signed household planning profile",
  "facts": {
    "annual_non_ira_income": 185000,
    "marginal_tax_rate": 0.32,
    "beneficiary_count": 3,
    "philanthropic_intent": "low",
    "family_transfer_priority": "high",
    "age": 66,
    "planning_year": 2026,
    "filing_status": "MFJ",
    "marital_status": "married",
    "liquid_assets": 2100000,
    "estate_value": 18400000
  }
}
```

Source types in priority order:

- **SIGNED_PROFILE**: Most authoritative client facts.
- **ATTORNEY_MEMO**: Contains estate_value, family_transfer_priority,
  philanthropic_intent. Does not always contain income or beneficiary count.
- **CUSTODIAN_EXPORT**: Always controls retirement-account facts. May appear
  in source-documents but actual account data lives under
  `/api/retirement-accounts`.
- **CRM_NOTE**: Stale imports, typically dated 2025-11-20. Overridden by any
  newer source.
- **STALE_MARKETING_INTAKE**: Very stale, never controlling.

### GET /api/retirement-accounts

Returns an array of retirement account records. Always use this endpoint for
account balances; the custodian export controls.

```json
{
  "account_id": "IRA-CLT-1001",
  "client_id": "CLT-1001",
  "source_type": "CUSTODIAN_EXPORT",
  "traditional_balance": 2800000,
  "roth_balance": 0,
  "expected_return": 0.065,
  "rmd_start_age": 73,
  "recommended_conversion_years": 7
}
```

### GET /api/life-insurance

Returns an array of life-insurance policy records.

```json
{
  "policy_id": "LIFE-CLT-1002",
  "client_id": "CLT-1002",
  "proposed_owner": "ILIT",
  "death_benefit": 4500000,
  "annual_premium": 78000,
  "planned_contribution_date": "2026-03-10",
  "is_existing_policy_transfer": false
}
```

When `is_existing_policy_transfer` is true, the policy faces a three-year
lookback risk for estate inclusion.

### GET /api/trust-candidates

Returns an array of trust candidate records with GRAT and CRAT parameters.

```json
{
  "trust_case_id": "TRUST-CLT-1003",
  "client_id": "CLT-1003",
  "asset_value": 8000000,
  "expected_growth_rate": 0.08,
  "grat_term_years": 5,
  "grat_annuity_rate": 0.04,
  "crat_term_years": 20,
  "crat_payout_rate": 0.055
}
```

### GET /api/policies/tax

Returns a single object with current-year tax policy constants.

```json
{
  "policy_label": "Advisory internal 2026 planning constants",
  "annual_gift_exclusion": { "2025": 19000, "2026": 20000 },
  "estate_tax_exemption": { "2025": 13990000, "2026": 13610000 },
  "estate_tax_rate": 0.4,
  "conversion_bracket_targets": {
    "MFJ": 394600,
    "SINGLE": 197300,
    "HOH": 263500
  },
  "max_crat_term_years": 20,
  "charitable_deduction_rate": 0.35
}
```

### GET /api/rmd-factors

Returns a flat object mapping age to the IRS life-expectancy divisor for RMD
calculations.

```json
{
  "73": 26.5, "74": 25.5, "75": 24.6, "76": 23.7, "77": 22.9,
  "78": 22.0, "79": 21.1, "80": 20.2, "81": 19.4, "82": 18.5,
  "83": 17.7, "84": 16.8, "85": 16.0, "86": 15.2, "87": 14.4,
  "88": 13.7, "89": 12.9, "90": 12.2, "91": 11.5, "92": 10.8,
  "93": 10.1, "94": 9.5, "95": 8.9, "96": 8.4, "97": 7.8,
  "98": 7.3, "99": 6.8
}
```

### GET /portal/client/{client_id}

Rich client portal page. Not needed for structured planning output; the API
endpoints above supply all required data.

## Fetch Strategy

For every engagement:

1. Fetch `/api/clients` and filter by `client_id`.
2. Fetch `/api/source-documents` and filter by `client_id`.
3. Fetch `/api/retirement-accounts` and filter by `client_id`.
4. Fetch `/api/life-insurance` and filter by `client_id`.
5. Fetch `/api/trust-candidates` and filter by `client_id`.
6. Fetch `/api/policies/tax` (singleton, no filter needed).
7. Fetch `/api/rmd-factors` (singleton, no filter needed).
