# Finance Audit API Reference

All endpoints are served from the task-environment base URL (`<TASK_ENV_BASE_URL>`).
No authentication is required. All responses are JSON.

## Available endpoints

### Claims

| Endpoint | Method | Description |
|---|---|---|
| `/api/claims` | GET | Returns array of all claim objects |
| `/api/claims/{claim_id}` | GET | Returns a single claim object |
| `/claims` | GET | Same as `/api/claims` (non-prefixed variant) |

Expected claim fields: `claim_id`, `status` (approved, denied, pending, etc.),
`amount`, `vendor_id`, `description`, `claim_date`.

### AP Bills

| Endpoint | Method | Description |
|---|---|---|
| `/api/ap/bills` | GET | Returns array of all AP bill objects |
| `/bills` | GET | Same as `/api/ap/bills` (non-prefixed variant) |

Expected bill fields: `bill_id`, `claim_id` (or cross-reference key),
`status` (scheduled, approved, paid, void), `amount`, `vendor_id`.

### AP Payments

| Endpoint | Method | Description |
|---|---|---|
| `/api/ap/payments` | GET | Returns array of all AP payment objects |
| `/payments` | GET | Same as `/api/ap/payments` (non-prefixed variant) |

Expected payment fields: `payment_id`, `bill_id` (or cross-reference key),
`status` (scheduled, cleared, none), `amount`.

### AP Aging

| Endpoint | Method | Description |
|---|---|---|
| `/api/ap/aging` | GET | Returns AP aging summary data |

### Vendors

| Endpoint | Method | Description |
|---|---|---|
| `/api/vendors` | GET | Returns array of all vendor objects |
| `/vendors` | GET | Same as `/api/vendors` (non-prefixed variant) |

Expected vendor fields: `vendor_id`, `business_id`, `name`, `status`,
`bank_account_last4`, `tax_id`, `license_expiry`, `risk_score`.

### Compliance objects

| Endpoint | Method | Description |
|---|---|---|
| `/api/compliance/objects` | GET | Returns array of all compliance objects |
| `/compliance/objects` | GET | Same (non-prefixed variant) |

Expected fields: `business_id`, `vendor_id`, various compliance flags.

### Compliance per-business endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/compliance/ownership/{business_id}` | GET | Ownership/UBO data for a business |
| `/api/compliance/registry/{business_id}` | GET | Registry/license data for a business |
| `/api/compliance/screening/{business_id}` | GET | Sanctions/PEP screening results |
| `/api/compliance/bank/{business_id}` | GET | Bank account verification status |

Expected ownership fields: beneficial owners with names and ownership percentages.
Expected registry fields: license status, expiry date, registration status.
Expected screening fields: sanctions flags, PEP flags, screening run status.
Expected bank fields: `bank_account_status` (active, closed, name_mismatch),
bank name, account last4.

### Prepaid invoices

| Endpoint | Method | Description |
|---|---|---|
| `/api/prepaids/invoices` | GET | Returns array of all prepaid invoice objects |
| `/prepaids/invoices` | GET | Same (non-prefixed variant) |

Expected invoice fields: `prepaid_invoice_id`, `account` (account code),
`original_amount`, `start_date`, `term_months` (or null if default/missing),
`monthly_amortization`, amortization schedule data.

### GL Balances

| Endpoint | Method | Description |
|---|---|---|
| `/api/prepaids/gl-balances` | GET | Returns GL balance data per account |
| `/gl/balances` | GET | Same (non-prefixed variant) |

Expected fields: `account`, `account_name`, `ending_balance` for each period.

### Close logs

| Endpoint | Method | Description |
|---|---|---|
| `/api/close/logs` | GET | Returns array of close log entries |
| `/close/logs` | GET | Same (non-prefixed variant) |

Expected fields: `close_log_id`, `period`, `status`, `claim_ids` or
related entity references.

### Discovery

| Endpoint | Method | Description |
|---|---|---|
| `/endpoints` | GET | Returns a list of all available endpoints |

Use this if the API surface differs from what is documented here.

## Cross-reference keys

The exact join keys between resources depend on the API's data model.
Common patterns observed:

- **claim to bill**: `claim_id` field on bill, or matching `vendor_id` and
  `amount` when direct claim_id is absent.
- **bill to payment**: `bill_id` field on payment.
- **vendor to compliance**: `business_id` or `vendor_id`.
- **invoice to account**: `account` field on invoice.

When the join key is ambiguous, examine the actual API response fields and
use the most specific match available.

## Filtering strategy

The list endpoints do not reliably support query-string filtering. Fetch the
full collection, then filter in your code by the candidate IDs. For compliance
per-business endpoints, call each endpoint once per candidate business ID.

## Parallel fetching

All list endpoints are independent and can be fetched in parallel. All
per-business compliance endpoints for all business IDs are also independent
and can be fetched in parallel. Wait for the initial data fetch to complete
before starting the cross-reference and classification steps.
