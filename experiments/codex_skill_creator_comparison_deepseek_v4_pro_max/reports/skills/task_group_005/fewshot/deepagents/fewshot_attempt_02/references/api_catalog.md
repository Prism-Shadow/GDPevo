# Shared ERP Finance API — Endpoint Catalog

The task environment exposes a read-only ERP/compliance API. All endpoints return
paginated JSON with `count`, `data`, `offset`, `limit`, and `total` fields.

Base URL: `<TASK_ENV_BASE_URL>` (supplied by the runner; substitute into every request).

Filtering: use exact-match query parameters by field name, plus `limit` and
`offset` for pagination. Example: `?claim_id=CLM-2025-0001&limit=5`.

When you need all records matching a filter, page until `offset + count >= total`.

## Table of Contents

- Claims
- AP Bills
- AP Payments
- AP Aging
- Vendors
- Compliance Objects
- Prepaid Invoices
- GL Balances (Prepaids)
- Close Logs

## Claims

**Endpoint:** `/api/claims` (aliases: `/claims`)

| Field | Type | Notes |
|---|---|---|
| claim_id | string | Primary key. Format varies: CLM-YYYY-DEPT-NNN or CLM-YYYY-NNNN |
| amount | number | Claim amount in USD |
| currency | string | Always "USD" |
| status | string | `approved`, `paid`, `rejected`, `pending`, `partially_paid`, `under_review`, `voided`, `pending_approval` |
| category | string | e.g. Travel, Office supplies, Client event, Meals, Conference |
| department | string | e.g. Operations, Engineering, Finance, People |
| employee_name | string | |
| vendor_id | string\|null | Links to `/api/vendors` |
| submitted_date | string | YYYY-MM-DD |
| approved_date | string | YYYY-MM-DD (null if not approved) |
| receipt_status | string | `attached`, `missing`, `partial` |
| policy_flags | list[string] | e.g. `weekend_spend`, `late_receipt`, `missing_receipt`, `over_limit` |
| notes | string | |

**Key query params:** `claim_id`, `status`, `vendor_id`

## AP Bills

**Endpoint:** `/api/ap/bills` (aliases: `/bills`)

| Field | Type | Notes |
|---|---|---|
| bill_id | string | Primary key. Format: AP-YYYY-NNNN or AP-YYYY-REIM-NNN |
| claim_id | string\|null | Links to claims. Null for non-claim bills |
| vendor_id | string | Links to `/api/vendors` |
| amount | number | Bill amount in USD |
| currency | string | Always "USD" |
| status | string | `approved`, `scheduled`, `paid`, `void`, `pending`, `rejected`, `in_review`, `partially_paid` |
| account | string | GL account code |
| bill_date | string | YYYY-MM-DD |
| due_date | string | YYYY-MM-DD |
| invoice_number | string | Vendor invoice number |
| memo | string | Free-text memo |

**Key query params:** `claim_id`, `bill_id`, `status`, `vendor_id`

## AP Payments

**Endpoint:** `/api/ap/payments` (aliases: `/payments`)

| Field | Type | Notes |
|---|---|---|
| payment_id | string | Primary key. Format: PAY-YYYY-NNNN |
| bill_id | string | Links to `/api/ap/bills` |
| vendor_id | string | Links to `/api/vendors` |
| amount | number | Payment amount in USD |
| status | string | `cleared`, `processing`, `scheduled`, `failed`, `pending`, `void` |
| method | string | `ACH`, `Check`, `Virtual card`, `Wire` |
| payment_date | string | YYYY-MM-DD |
| bank_reference | string | Bank reference number |

**Key query params:** `bill_id`, `payment_id`, `status`, `vendor_id`

## AP Aging

**Endpoint:** `/api/ap/aging`

Returns the same shape as `/api/ap/bills` with additional `balance` (open amount)
and `paid_amount` fields. Each record is an AP bill with accumulated payment
information.

| Extra Field | Type | Notes |
|---|---|---|
| balance | number | Remaining open amount on the bill |
| paid_amount | number | Total paid toward the bill |
| as_of | string | Aging date |

**Key query params:** `bill_id`, `claim_id`, `status`, `vendor_id`

## Vendors

**Endpoint:** `/api/vendors` (aliases: `/api/vendors`)

| Field | Type | Notes |
|---|---|---|
| vendor_id | string | Primary key. Format: VEN-NNNN |
| vendor_name | string | Display name |
| legal_name | string | Full legal entity name |
| status | string | `active`, `on_hold`, `inactive`, `under_review` |
| industry | string | e.g. Payroll, Travel, Legal, Technology |
| payment_terms | string | e.g. Net 30, Net 45 |
| default_account | string | Default GL account |
| bank_account_last4 | string | Last 4 digits of bank account |
| tax_id | string | Tax identifier |
| updated_at | string | YYYY-MM-DD |

**Key query params:** `vendor_id`, `status`, `tax_id`

## Compliance Objects

**Endpoint:** `/api/compliance/objects` (aliases: `/compliance/objects`)

Also reachable as sub-resources (note: the task may refer to these but the
`/objects` list endpoint returns all fields):
- `/api/compliance/ownership/{business_id}`
- `/api/compliance/registry/{business_id}`
- `/api/compliance/screening/{business_id}`
- `/api/compliance/bank/{business_id}`

| Field | Type | Notes |
|---|---|---|
| business_id | string | Primary key. Format: BUS-YYYY-NNNN |
| business_name | string | |
| vendor_id | string | Links to `/api/vendors` |
| jurisdiction | string | e.g. Delaware, New York, United Kingdom |
| registration_number | string | |
| tax_id | string | Tax identifier |
| review_status | string | `not_started`, `in_review`, `cleared`, `escalated`, `approved` |
| risk_score | integer | 0-100 scale |
| pep_status | string | `none`, `confirmed`, `potential` |
| sanctions_check_status | string | `clear`, `flagged`, `confirmed`, `not_run` |
| bank_account_status | string | `verified`, `name_mismatch`, `closed`, `unverified` |
| license_expiry | string | YYYY-MM-DD |
| missing_fields | list[string] | e.g. `license`, `website`, `bank_statement` |
| shell_company_suspected | boolean | |
| ownership_layer_count | integer | |
| ubo_list | list[object] | Objects with `name` (string) and `ownership_pct` (number) |

**Key query params:** `business_id`, `vendor_id`, `review_status`

### Hard-Stop Flag Derivation

When reviewing a vendor/business for release readiness, derive hard-stop flags
from compliance fields:

| Flag | Condition |
|---|---|
| bank_closed | `bank_account_status == "closed"` |
| bank_name_mismatch | `bank_account_status == "name_mismatch"` |
| confirmed_pep | `pep_status == "confirmed"` |
| expired_license | `license_expiry < as_of_date` |
| missing_required_documents | `missing_fields` is non-empty |
| sanctions_confirmed | `sanctions_check_status == "confirmed"` |
| screening_not_run | `sanctions_check_status == "not_run"` |
| shell_company_suspected | `shell_company_suspected == true` |
| vendor_on_hold | Vendor `status == "on_hold"` (requires cross-referencing vendor endpoint) |

### UBO Counting

Count unique `name` values in `ubo_list`. Sum ownership percentages per unique
name. A UBO is "reportable" at or above 25% total ownership.

## Prepaid Invoices

**Endpoint:** `/api/prepaids/invoices` (aliases: `/prepaids/invoices`)

| Field | Type | Notes |
|---|---|---|
| prepaid_invoice_id | string | Primary key. Format: PPD-YYYY-NNNN or PPD-ENTITY-ACCT-CODE-NNN |
| account | string | GL account code (e.g. "1250", "1251") |
| description | string | |
| vendor_id | string | Links to `/api/vendors` |
| invoice_number | string | Vendor invoice ref |
| invoice_date | string | YYYY-MM-DD |
| original_amount | number | Total invoice amount in USD |
| monthly_amortization | number | Straight-line monthly amount |
| recognition_method | string | Always "straight_line" |
| service_start | string | YYYY-MM-DD |
| service_end | string | YYYY-MM-DD |
| source_document | string | |
| data_quality_flags | list[string] | e.g. `missing_contract_dates`, `rounded_amount` |

**Key query params:** `prepaid_invoice_id`, `account`, `vendor_id`

### Straight-Line Amortization Rules

For a given target period (YYYY-MM):
1. `months_elapsed` = months from `service_start` through the target period inclusive. If target month is before service_start, months_elapsed = 0.
2. `cumulative_amortization` = `monthly_amortization` * `months_elapsed`
3. `ending_balance` = max(`original_amount` - `cumulative_amortization`, 0.00)
4. `target_month_amortization` = `monthly_amortization` (or 0 if service hasn't started or has fully amortized)
5. **Default/missing term flag**: true when `data_quality_flags` includes `missing_contract_dates` OR `service_start` is null/missing
6. **Exception flag**: true when any data quality flag is present OR `ending_balance` does not round to a clean value within standard tolerance

## GL Balances (Prepaids)

**Endpoint:** `/api/prepaids/gl-balances` (aliases: `/gl/balances`)

| Field | Type | Notes |
|---|---|---|
| account | string | GL account code |
| account_name | string | e.g. "Prepaid Expenses", "Prepaid Insurance" |
| period | string | YYYY-MM |
| ending_balance | number | GL ending balance for the period in USD |
| entity | string | e.g. "Northwind US" |
| source | string | "close ledger export" |
| loaded_at | string | ISO timestamp |

**Key query params:** `account`, `period`, `entity`

### Reconciliation Logic

1. Compute schedule ending balance for all selected invoices in the account
2. Compare to `gl_ending_balance` for matching (account, period, entity)
3. `variance_amount` = `schedule_ending_balance` - `gl_ending_balance`
4. `variance_flag` = true when `abs(variance_amount) > variance_threshold_abs`
5. Account status:
   - `reconciled`: variance within threshold, no default/missing term invoices
   - `variance_review`: variance within threshold but has default/missing term invoice(s)
   - `requires_reconciliation`: variance exceeds threshold

## Close Logs

**Endpoint:** `/api/close/logs` (aliases: `/close/logs`)

| Field | Type | Notes |
|---|---|---|
| log_id | string | Primary key. Format: CLOSE-YYYY-MM-NNN |
| period | string | YYYY-MM |
| area | string | e.g. Compliance, Prepaids, Expense, AP |
| message | string | Free-text description |
| status | string | `open`, `closed`, `in_review` |
| owner | string | Reviewer name |
| related_account | string\|null | |
| created_at | string | ISO timestamp |

**Key query params:** `period`, `area`, `status`, `log_id`

Close logs with `status == "open"` signal that a prior close cycle has
unresolved items; these typically require attention before a batch can be
finalized.
