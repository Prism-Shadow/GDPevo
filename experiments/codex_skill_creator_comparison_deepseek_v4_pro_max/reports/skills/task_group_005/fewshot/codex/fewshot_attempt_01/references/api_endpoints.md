# Finance API Endpoints

All endpoints are GET and return JSON. The API is available under both bare paths
(e.g., `/claims`) and `/api/`-prefixed paths (e.g., `/api/claims`); both forms are
equivalent. Use `/api/` prefix by default.

## Claims

| Endpoint | Description |
|----------|-------------|
| `GET /api/claims` | List all claims |
| `GET /api/claims/{claim_id}` | Single claim detail |

### Claim record fields

- `claim_id` — Canonical claim identifier (e.g., `CLM-2025-OPS-017`)
- `status` — Claim lifecycle status: `approved`, `pending`, `rejected`, `draft`, `void`
- `amount` — Claimed amount in USD (string, parse as float with two-decimal precision)
- `vendor_id` — Associated vendor identifier
- `business_id` — Business entity associated with the claim
- `description` — Free-text claim description
- `submitted_date`, `approved_date` — ISO-8601 timestamps

## AP Bills

| Endpoint | Description |
|----------|-------------|
| `GET /api/ap/bills` | List all AP bills |
| `GET /bills` | List all AP bills (bare path) |

### Bill record fields

- `bill_id` — Bill identifier (e.g., `AP-2025-REIM-017`)
- `claim_id` — Linked claim, when applicable
- `vendor_id` — Vendor on the bill
- `status` — `scheduled`, `approved`, `paid`, `void`, `pending`
- `amount` — Bill amount in USD (string)
- `paid_amount` — Cleared payment total against this bill
- `description` — Bill description or memo

## Payments

| Endpoint | Description |
|----------|-------------|
| `GET /api/ap/payments` | List all payments |
| `GET /payments` | List all payments (bare path) |

### Payment record fields

- `payment_id` — Payment identifier
- `bill_id` — Linked bill
- `claim_id` — Linked claim, when applicable
- `status` — `cleared`, `scheduled`, `void`, `pending`
- `amount` — Payment amount in USD (string)

## AP Aging

| Endpoint | Description |
|----------|-------------|
| `GET /api/ap/aging` | AP aging report |

## Vendors

| Endpoint | Description |
|----------|-------------|
| `GET /api/vendors` | List all vendors |
| `GET /vendors` | List all vendors (bare path) |

### Vendor record fields

- `vendor_id` — Vendor identifier (e.g., `VEN-0047`)
- `business_id` — Linked business entity
- `name` — Vendor display name
- `tax_id` — Tax identification number
- `status` — `active`, `on_hold`, `inactive`
- `risk_score` — Numeric risk score (0-100)
- `bank_last4` — Last four digits of bank account on file

## Compliance

### Ownership

`GET /api/compliance/ownership/{business_id}`

Returns beneficial ownership records for the business. Key fields:

- `owners` — Array of owner entries, each with `name`, `ownership_percentage`, `role`
- UBOs are owners meeting the reporting threshold (typically >= 25% ownership).
  Count unique owner names at or above the threshold.

### Registry

`GET /api/compliance/registry/{business_id}`

Returns business registration records. Key fields:

- `license_status` — `active`, `expired`, `pending`, `suspended`
- `license_expiry_date` — ISO-8601 date
- `tax_id` — Registered tax identifier
- `tax_id_status` — `valid`, `invalid`, `unverified`

### Screening

`GET /api/compliance/screening/{business_id}`

Returns watchlist and adverse-media screening results. Key fields:

- `screening_status` — `clear`, `not_run`, `flagged`
- `pep_flag` — Boolean, politically exposed person match
- `sanctions_flag` — Boolean, sanctions-list match
- `adverse_media_flag` — Boolean, negative-news match
- `shell_company_risk` — `none`, `low`, `suspected`

### Bank

`GET /api/compliance/bank/{business_id}`

Returns bank account verification status. Key fields:

- `bank_account_status` — `verified`, `name_mismatch`, `closed`, `unverified`
- `bank_name` — Name on the bank account
- `business_name` — Expected business name for matching

## Prepaid Invoices

| Endpoint | Description |
|----------|-------------|
| `GET /api/prepaids/invoices` | List all prepaid invoices |
| `GET /prepaids/invoices` | List all prepaid invoices (bare path) |

### Prepaid invoice record fields

- `prepaid_invoice_id` — Invoice identifier (e.g., `PPD-2025-0001`)
- `account` — GL account code (string, e.g., `"1250"`)
- `entity` — Legal entity name
- `original_amount` — Total invoice amount in USD (string)
- `start_date` — Amortization start date (ISO-8601)
- `term_months` — Amortization term in months (integer; may be 0 or missing)
- `monthly_amortization` — Straight-line monthly amount in USD (string)
- `months_amortized` — Count of months already amortized
- `cumulative_amortization` — Total amortized-to-date in USD (string)
- `schedule` — Optional array of monthly amortization entries, each with `period` (YYYY-MM) and `amount`

## GL Balances

| Endpoint | Description |
|----------|-------------|
| `GET /api/prepaids/gl-balances` | GL balance records for prepaid accounts |
| `GET /gl/balances` | GL balance records (bare path) |

### GL balance record fields

- `account` — GL account code (string, e.g., `"1250"`)
- `account_name` — Human-readable account name
- `period` — Period in YYYY-MM format
- `ending_balance` — Period-end balance in USD (string)
- `entity` — Legal entity name

## Close Logs

| Endpoint | Description |
|----------|-------------|
| `GET /api/close/logs` | List all close logs |
| `GET /close/logs` | List all close logs (bare path) |

### Close log record fields

- `log_id` — Close log identifier (e.g., `CLOSE-2025-04-009`)
- `period` — Close period (YYYY-MM)
- `status` — `open`, `closed`, `pending_review`
- `entity` — Legal entity
- `notes` — Free-text notes referencing claims or issues

## Endpoint Discovery

The full endpoint catalog is available at `GET /api/endpoints` or `GET /endpoints`.
Use it to confirm available paths when the task references an unfamiliar endpoint.
All endpoints listed above are read-only GET operations.
