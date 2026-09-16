# API Reference

Base URL is `$API_BASE`, typically `http://task-env:9008/`.  All responses are
JSON.  Use `curl -s` with `python3 -m json.tool` for pretty-printing, or parse
with Python's `requests` / `json`.

## Endpoints

### GET /api/clients

Returns a JSON array of all client objects.

Each client object:

| Field           | Type    | Notes                                        |
|-----------------|---------|----------------------------------------------|
| client_id       | string  | Stable identifier, e.g. CLT-1001             |
| household_name  | string  | Display name                                 |
| age             | integer | Client age in planning year                  |
| marital_status  | string  | married / single                              |
| filing_status   | string  | MFJ / SINGLE / HOH                            |
| planning_year   | integer | Base year for projections (always 2026)      |
| estate_value    | number  | Total estate value in USD                    |
| liquid_assets   | number  | Available liquid assets in USD               |
| record_status   | string  | active / monitoring                           |
| advisor_team    | string  | Advisory team assignment                     |

### GET /api/clients/{client_id}

Same shape as above, but a single object instead of array.

### GET /api/source-documents

Returns a JSON array of all source documents across all clients.  Filter by
`client_id` to get documents for one client.  Each document:

| Field          | Type   | Notes                                              |
|----------------|--------|----------------------------------------------------|
| document_id    | string | Unique doc ID                                      |
| client_id      | string | Owning client                                      |
| source_type    | string | SIGNED_PROFILE, ATTORNEY_MEMO, CRM_NOTE, etc.      |
| effective_date | string | ISO date (YYYY-MM-DD)                              |
| title          | string | Human-readable label                               |
| facts          | object | Key-value fact map (fields vary by document type)  |

Common facts found in source documents:

- `annual_non_ira_income` — non-IRA annual income in USD
- `marginal_tax_rate` — decimal, e.g. 0.32
- `beneficiary_count` — integer, number of trust/ILIT beneficiaries
- `philanthropic_intent` — low / moderate / high
- `family_transfer_priority` — low / moderate / high
- `age`, `planning_year`, `filing_status`, `marital_status`
- `liquid_assets`, `estate_value`

CRM_NOTE documents are older imports and may be missing fields that
SIGNED_PROFILE or ATTORNEY_MEMO include.

### GET /api/retirement-accounts

Returns a JSON array of all retirement account records.  Filter by `client_id`.
Each account:

| Field                       | Type    | Notes                            |
|-----------------------------|---------|----------------------------------|
| account_id                  | string  | e.g. IRA-CLT-1001                |
| client_id                   | string  | Owning client                    |
| source_type                 | string  | Always CUSTODIAN_EXPORT          |
| traditional_balance         | number  | Pre-tax traditional IRA balance  |
| roth_balance                | number  | Current Roth IRA balance         |
| expected_return             | number  | Annual growth rate, decimal      |
| rmd_start_age               | integer | Age when RMDs begin (always 73)  |
| recommended_conversion_years| integer | Suggested conversion window      |

### GET /api/life-insurance

Returns a JSON array of all life-insurance policies.  Filter by `client_id`.
Each policy:

| Field                      | Type     | Notes                                    |
|----------------------------|----------|------------------------------------------|
| policy_id                  | string   | e.g. LIFE-CLT-1001                       |
| client_id                  | string   | Owning client                            |
| proposed_owner             | string   | Always ILIT in the evidence              |
| death_benefit              | number   | Face amount in USD                       |
| annual_premium             | number   | Annual premium in USD                    |
| planned_contribution_date  | string   | ISO date of planned contribution         |
| is_existing_policy_transfer| boolean  | True if policy is being transferred in   |

### GET /api/trust-candidates

Returns a JSON array of all trust candidate cases.  Filter by `client_id`.
Each trust case:

| Field                | Type    | Notes                                      |
|----------------------|---------|--------------------------------------------|
| trust_case_id        | string  | e.g. TRUST-CLT-1001                        |
| client_id            | string  | Owning client                              |
| asset_value          | number  | Value of assets to seed the trust          |
| expected_growth_rate | number  | Annual growth rate, decimal                |
| grat_term_years      | integer | GRAT term from the case                    |
| grat_annuity_rate    | number  | GRAT annuity rate (decimal)                |
| crat_term_years      | integer | CRAT term (always 20 in the evidence)      |
| crat_payout_rate     | number  | CRAT payout rate (always 0.055)            |

### GET /api/policies/tax

Returns a single global object (not an array).  Always fetch this.

| Field                     | Type   | Notes                                          |
|---------------------------|--------|------------------------------------------------|
| policy_label              | string | Description label                              |
| annual_gift_exclusion     | object | Keys: year string, value: exclusion amount     |
| estate_tax_exemption      | object | Keys: year string, value: exemption amount     |
| estate_tax_rate           | number | Decimal, always 0.4                            |
| conversion_bracket_targets| object | Keys: filing status, value: bracket target     |
| max_crat_term_years       | integer| Always 20                                      |
| charitable_deduction_rate | number | Decimal, always 0.35                           |

conversion_bracket_targets maps filing status to the top-of-bracket income
threshold used to size annual Roth conversions:

- MFJ: 394600
- SINGLE: 197300
- HOH: 263500

### GET /api/rmd-factors

Returns a single global object (not an array).  Keys are age strings (e.g.
"73"), values are the RMD life-expectancy factor for that age.

## Filtering Pattern

Every list endpoint returns all records.  Filter client-specific data:

```python
import json, urllib.request

def fetch_json(url):
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read())

base = "http://task-env:9008"
client_id = "CLT-1001"

# Client record
client = fetch_json(f"{base}/api/clients/{client_id}")

# Source documents for this client
all_docs = fetch_json(f"{base}/api/source-documents")
docs = [d for d in all_docs if d["client_id"] == client_id]

# Retirement accounts for this client
all_iras = fetch_json(f"{base}/api/retirement-accounts")
iras = [a for a in all_iras if a["client_id"] == client_id]

# Life insurance for this client
all_life = fetch_json(f"{base}/api/life-insurance")
life = [p for p in all_life if p["client_id"] == client_id]

# Trust candidates for this client
all_trusts = fetch_json(f"{base}/api/trust-candidates")
trusts = [t for t in all_trusts if t["client_id"] == client_id]

# Global tax policy (no filter needed)
tax = fetch_json(f"{base}/api/policies/tax")

# Global RMD factors (no filter needed)
rmd = fetch_json(f"{base}/api/rmd-factors")
```

Use the numeric-age key to look up an RMD factor: `rmd_factors[str(age)]`.

## Notes

- Numbers in the API are JSON numbers (float or int).  Round outputs to cents
  with `round(value, 2)`.
- For `filing_status` lookups, use the client's filing_status (from the
  controlling source document) to find the bracket target.
- The `estate_tax_exemption` object gives the per-person exemption.  For MFJ
  clients, double it.  For SINGLE and HOH, use the value as-is.
