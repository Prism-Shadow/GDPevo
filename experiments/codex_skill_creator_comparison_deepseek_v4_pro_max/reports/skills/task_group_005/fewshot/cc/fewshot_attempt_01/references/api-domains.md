# API Domains and Data Models

This reference catalogs the endpoints available in the shared ERP/compliance
API and describes the data models you can expect from each. The API is the
system of record for all finance close-review tasks.

## Base URL

The API base URL is provided by the runner as `<TASK_ENV_BASE_URL>`. All
endpoints are relative to this base. Append the path directly, e.g.:
`<TASK_ENV_BASE_URL>/claims` or `<TASK_ENV_BASE_URL>/api/claims`.

Two path conventions exist (`/claims` and `/api/claims`) and are equivalent.
Choose whichever the task context or prior examples suggest, but verify that
the endpoint returns data.

## Endpoint Catalog

### Claims

| Endpoint | Returns |
|----------|---------|
| `/claims` or `/api/claims` | Array of all claim objects |
| `/api/claims/{claim_id}` | Single claim object |

Each claim object typically has:
- `id`: The claim identifier (e.g. `CLM-2025-OPS-017`).
- `status`: The claim status (e.g. `approved`, `pending`, `rejected`).
- `amount`: The claim total in USD.
- Possibly a `bill_id` or other linking field connecting it to an AP bill.

Use the list endpoint to find all claims, then filter to the candidate
IDs from the batch. The single-claim endpoint is useful for spot-checking
or when the batch is small.

### AP Bills

| Endpoint | Returns |
|----------|---------|
| `/bills` or `/api/ap/bills` | Array of all AP bill objects |

Each bill object typically has:
- `id`: The bill identifier (e.g. `AP-2025-REIM-017`).
- `claim_id`: The claim this bill reimburses (or a similar linking field).
- `status`: `scheduled`, `approved`, `paid`, `voided`, etc.
- `amount`: The bill amount in USD.
- `payment_id`: Reference to a linked payment, if any.

**Cross-reference rule**: Match bills to claims by the linking field. A
claim may have zero, one, or multiple bills. When multiple bills exist,
use the most recent or non-voided one.

### Payments

| Endpoint | Returns |
|----------|---------|
| `/payments` or `/api/ap/payments` | Array of all payment objects |
| `/api/ap/aging` | AP aging summary (less commonly needed) |

Each payment object typically has:
- `id`: The payment identifier.
- `bill_id`: The bill this payment settles.
- `status`: `none`, `scheduled`, `cleared`, etc.
- `amount`: The payment amount in USD.

**Cross-reference rule**: Match payments to bills by `bill_id`. A `cleared`
payment for the full bill amount means the bill is settled.

### Close Logs

| Endpoint | Returns |
|----------|---------|
| `/close/logs` or `/api/close/logs` | Array of close-log entry objects |

Close-log entries track prior close-review activity. Use them when a task
asks whether a close-log entry is required or when stale-snapshot context
needs to be reconciled against logged close events.

### Prepaid Invoices

| Endpoint | Returns |
|----------|---------|
| `/prepaids/invoices` or `/api/prepaids/invoices` | Array of all prepaid invoice objects |

Each invoice object typically has:
- `prepaid_invoice_id`: The invoice identifier.
- `account`: The GL account number (e.g. `1250`, `1251`).
- `account_name`: Human-readable account name.
- `original_amount`: The total prepaid amount in USD.
- `amortization_schedule`: Monthly amortization entries with period and
  amount. The schedule data drives straight-line computations.
- `term_months`: The contract-specified amortization term. A default or
  missing value is a data-quality concern.
- Possibly a `start_period` or `start_date` field.

**Amortization computation**: Sum monthly entries through the target period
for cumulative amortization. Ending balance = original_amount - cumulative.
When the schedule uses straight-line, the monthly amount is constant (verify
this from the data rather than assuming).

### GL Balances

| Endpoint | Returns |
|----------|---------|
| `/gl/balances` or `/api/prepaids/gl-balances` | GL balance data by account and period |

Returns account-level ending balances. Filter to the target account numbers
and the target period. The GL ending balance is the independent check
against the prepaid schedule's computed ending balance.

### Vendors

| Endpoint | Returns |
|----------|---------|
| `/vendors` or `/api/vendors` | Array of vendor objects |

Each vendor object typically has:
- `vendor_id`: The vendor identifier.
- `business_id`: The business entity linked to this vendor.
- `status`: Active, on-hold, etc.
- Possibly tax, risk-score, and other compliance-related fields.

### Compliance

| Endpoint | Returns |
|----------|---------|
| `/compliance/objects` or `/api/compliance/objects` | Array of compliance summary objects |
| `/api/compliance/ownership/{business_id}` | Ownership records for one business |
| `/api/compliance/registry/{business_id}` | Registry/registration records |
| `/api/compliance/screening/{business_id}` | Screening results (sanctions, PEP, etc.) |
| `/api/compliance/bank/{business_id}` | Bank account verification status |

**Compliance objects**: A convenience endpoint that may bundle multiple
compliance dimensions. Use it for a broad view, then drill into
per-business endpoints when you need specific evidence for a decision.

**Ownership**: Returns beneficial owner records. Count unique UBO names
whose ownership percentage meets the reporting threshold. The threshold
is typically 25% but verify from the task context.

**Registry**: Returns registration status, license validity dates, and
document completeness flags. Check license expiry against the task's
as-of date.

**Screening**: Returns sanctions-list, PEP, and adverse-media screening
results. Look for `confirmed` matches vs `potential` or `clear` statuses.

**Bank**: Returns bank account status and last-4 digits. Compare the
`bank_account_status` field (e.g. `active`, `closed`, `name_mismatch`)
and the `bank_last4` against any requested account-change values.

## Discovery Endpoint

| Endpoint | Returns |
|----------|---------|
| `/endpoints` | List of all available endpoints |

Use this at the start of a task when you are unsure which endpoints the
current environment exposes. This is the authoritative endpoint index.

## Data Model Notes

**Do not hardcode field names.** The actual API response is the authority.
The field patterns above are common across the finance domain but the API
may use slightly different naming. Always inspect the first response to
learn the real schema.

**Linking fields may vary.** Claims link to bills, bills link to payments,
vendors link to businesses, and compliance endpoints use `business_id`.
The linking field name may be `claim_id`, `bill_id`, `business_id`, or a
similar suffix. Trace the connections by reading the data.

**Status values are task-specific.** The API may return statuses like
`approved`, `scheduled`, `paid`, `cleared`, `voided`, `none`, `active`,
`closed`, `on_hold`. Map these to the decision logic described in
[SKILL.md](../SKILL.md), but always use the exact status strings from the
API response when reasoning.

**Currency amounts are in USD.** The API returns numeric amounts. Treat
them as-is and format to two decimal places in output.
