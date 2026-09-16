# Advisory API Reference

Base URL: `http://task-env:9008` (or `API_BASE` if set by the harness). All endpoints return JSON.

---

## GET /api/clients

Returns an array of all client summary records.

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

Filter by client_id programmatically after fetching the array. A singular GET `/api/clients/{client_id}` also works for one record.

**Key fields:** `age`, `marital_status`, `filing_status`, `estate_value`, `liquid_assets`. The `filing_status` is one of `MFJ`, `SINGLE`, or `HOH`.

---

## GET /api/source-documents

Returns an array of all source documents across all clients. Query parameter `?client_id=CLT-1001` filters to one client.

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

**Source types** (in authority order):
- `SIGNED_PROFILE` -- the authoritative client document (most recent)
- `ATTORNEY_MEMO` -- attorney planning notes (second priority, high legal weight)
- `CUSTODIAN_EXPORT` -- factual account export (not a profile source; accounts come from the retirement-accounts endpoint)
- `CRM_NOTE` -- older CRM import, superseded by newer sources
- `STALE_MARKETING_INTAKE` -- oldest, least reliable

**Conflict resolution:** See the main SKILL.md for resolution rules. In short: prefer `SIGNED_PROFILE` for profile facts; prefer `ATTORNEY_MEMO` for trust-asset decisions when it is the more specific document; use `CUSTODIAN_EXPORT` for account-level data.

**Facts fields vary by source type.** `SIGNED_PROFILE` documents carry the richest facts: `annual_non_ira_income`, `marginal_tax_rate`, `beneficiary_count`, `philanthropic_intent`, `family_transfer_priority`, `age`, `filing_status`, `marital_status`, `liquid_assets`, `estate_value`. `CRM_NOTE` and `ATTORNEY_MEMO` may carry fewer fields.

---

## GET /api/retirement-accounts

Returns an array of all retirement account records. Filter by `client_id` after fetching.

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

**Key fields:**
- `traditional_balance` -- current pre-tax traditional IRA balance (USD)
- `roth_balance` -- current Roth IRA balance (USD, may be zero)
- `expected_return` -- annualized return assumption (decimal, e.g., 0.065 = 6.5%)
- `rmd_start_age` -- age at which RMDs begin (typically 73)
- `recommended_conversion_years` -- number of years over which to stage conversions

These are custodian-exported values. There is only one record per client. The `source_type` is always `CUSTODIAN_EXPORT`.

---

## GET /api/life-insurance

Returns an array of all life insurance policy records. Filter by `client_id`.

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

**Key fields:**
- `proposed_owner` -- typically `"ILIT"` (irrevocable life insurance trust)
- `death_benefit` -- face value of the policy (USD)
- `annual_premium` -- annual premium amount (USD)
- `planned_contribution_date` -- target contribution date for the first premium cycle (ISO date)
- `is_existing_policy_transfer` -- `true` if this is a transfer of an existing policy into the ILIT (triggers three-year lookback risk); `false` if a new policy

---

## GET /api/trust-candidates

Returns an array of all trust candidate cases. Filter by `client_id`.

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

**Key fields:**
- `asset_value` -- value of assets to place in trust (USD)
- `expected_growth_rate` -- annualized return assumption (decimal)
- `grat_term_years` -- recommended GRAT term in years
- `grat_annuity_rate` -- annuity payout rate for the GRAT (decimal)
- `crat_term_years` -- recommended CRAT term in years (typically 20)
- `crat_payout_rate` -- payout rate for the CRAT (decimal, typically 0.055)

---

## GET /api/policies/tax

Returns a single tax policy object (shared across all clients).

```json
{
  "policy_label": "Advisory internal 2026 planning constants",
  "annual_gift_exclusion": { "2025": 19000, "2026": 20000 },
  "estate_tax_exemption": { "2025": 13990000, "2026": 13610000 },
  "estate_tax_rate": 0.4,
  "conversion_bracket_targets": { "MFJ": 394600, "SINGLE": 197300, "HOH": 263500 },
  "max_crat_term_years": 20,
  "charitable_deduction_rate": 0.35
}
```

**Key constants used in computations:**

| Field | Meaning | Use |
|---|---|---|
| `annual_gift_exclusion` | Annual gift-tax exclusion per beneficiary (by year) | ILIT: compute annual exclusion capacity |
| `estate_tax_exemption` | Lifetime estate-tax exemption (by year) | Estate context: compute taxable estate and tax exposure |
| `estate_tax_rate` | Flat estate tax rate (0.40) | Estate context: tax exposure = taxable_estate * rate |
| `conversion_bracket_targets` | Target AGI ceiling per filing status for Roth conversions | Roth: annual_conversion_amount = target - income |
| `max_crat_term_years` | Maximum CRAT term (20) | CRAT: use as fixed term |
| `charitable_deduction_rate` | Income tax deduction rate for charitable remainder (0.35) | CRAT: income tax deduction |

---

## GET /api/rmd-factors

Returns a JSON object mapping ages (as string keys) to RMD divisor factors.

```json
{ "73": 26.5, "74": 25.5, ..., "99": 6.8 }
```

Ages 73 through 99 are present. The RMD for a given year is `traditional_balance / divisor`. The `traditional_balance` used is the year-end balance before the RMD is taken.

---

## GET /portal/client/{client_id}

Returns an HTML client portal page. Not used for structured data extraction; use the API endpoints instead.
