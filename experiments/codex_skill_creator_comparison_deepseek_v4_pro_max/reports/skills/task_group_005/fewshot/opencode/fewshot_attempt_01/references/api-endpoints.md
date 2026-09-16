# Finance API Endpoint Reference

The task environment runs a shared finance/ERP API. This reference catalogs the endpoints that typically appear and how to use them.

## Endpoint Discovery

Always start by calling `GET /endpoints` at the provided base URL. The response lists available routes. Endpoints may be served under plain paths or under `/api/` prefixes. Prefer the `/api/` variant when both exist.

## Endpoint Categories

### Claims and Reimbursement

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/claims` | GET | List all claims |
| `/api/claims/{claim_id}` | GET | Single claim detail |

Claim records include fields like `claim_id`, `status`, `amount`, `vendor_id`, `description`. The `status` field drives classification: `approved` claims are candidates for AP release; other statuses (draft, rejected, pending) are blockers.

### AP Bills

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/ap/bills` | GET | List all AP bills |
| `/bills` | GET | Alternative path |

Bill records link to claims via a `claim_id` field or by matching vendor context. Key fields: `bill_id`, `claim_id`, `vendor_id`, `amount`, `status`. Status values typically include `approved`, `scheduled`, `paid`, `void`. A bill in `void` status is not payable regardless of other evidence.

### AP Payments

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/ap/payments` | GET | List all AP payments |

Payment records link to bills via a `bill_id` field. Key fields: `payment_id`, `bill_id`, `amount`, `status`. Status values typically include `cleared`, `scheduled`, `none`. Only `cleared` payments reduce the AP open balance.

### AP Aging

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/ap/aging` | GET | AP aging report |

Provides aging buckets for open AP balances. Useful as cross-reference but not the primary system of record.

### Vendors

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/vendors` | GET | List all vendors |
| `/vendors` | GET | Alternative path |

Vendor records include `vendor_id`, `business_id`, `name`, `status`, `bank_last4`. The `status` field may indicate `on_hold` or `active`. A vendor on hold is a blocking condition.

### Compliance

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/compliance/objects` | GET | List all compliance records |
| `/compliance/objects` | GET | Alternative path |
| `/api/compliance/ownership/{business_id}` | GET | Beneficial ownership data |
| `/api/compliance/registry/{business_id}` | GET | Business registry data |
| `/api/compliance/screening/{business_id}` | GET | Sanctions/PEP screening results |
| `/api/compliance/bank/{business_id}` | GET | Bank account verification |

Compliance endpoints return per-business records. Key patterns:

- **Ownership**: Contains `owners` or `beneficial_owners` arrays with name and ownership percentage. Count owners at or above the reporting threshold (typically 25%) for the `reportable_ubo_counts`.
- **Registry**: Contains `license_expiry`, `tax_id`, `registration_status`. Compare `license_expiry` to the review date to determine `expired_license` flags.
- **Screening**: Contains `screening_status` (values like `clear`, `pep_found`, `sanctions_match`, `not_run`). A `screening_not_run` flag applies when status is `not_run` or the record is absent. A `confirmed_pep` flag applies on `pep_found`. A `sanctions_confirmed` flag applies on `sanctions_match`.
- **Bank**: Contains `account_status` (values like `active`, `closed`, `name_mismatch`). `bank_closed` flag on `closed`; `bank_name_mismatch` flag on `name_mismatch`.

**Missing compliance records**: When a compliance endpoint returns a 404 or an empty/absent record for a business ID, treat it as a flag condition (e.g., `screening_not_run`, `missing_required_documents`).

### Prepaid Invoices and GL

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/prepaids/invoices` | GET | List all prepaid invoices |
| `/prepaids/invoices` | GET | Alternative path |
| `/api/prepaids/gl-balances` | GET | GL account balances |
| `/gl/balances` | GET | Alternative path |

Prepaid invoice records include `prepaid_invoice_id`, `account`, `original_amount`, `term_months`, `start_date`. Compute straight-line monthly amortization as `original_amount / term_months`. The cumulative through a given month is `monthly_amortization * months_elapsed` (inclusive of the target month). The ending balance is `original_amount - cumulative_amortization_through_target`.

GL balance records include `account`, `account_name`, `ending_balance`. Match by account code.

### Close Logs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/close/logs` | GET | List close logs |
| `/close/logs` | GET | Alternative path |

Close log records include `log_id`, `claim_id`, `action`, `timestamp`. Filter logs for the claim IDs in the batch. A `close_log_required` flag is true when any log exists for a claim in the batch.

## Query Strategy

1. Call all relevant list endpoints in parallel at the start.
2. Call per-ID detail endpoints in parallel once you have the candidate IDs.
3. Filter list results in memory by the candidate IDs from the batch.
4. When a per-ID endpoint returns 404 or an unexpected structure, note the absence and treat it as a signal (not a fatal error).

## Common Data Shapes

The API returns JSON. List endpoints typically return arrays of objects or objects keyed by ID. Detail endpoints return single objects. Field names use `snake_case`. All currency amounts are in USD and represented as numbers.

When matching fields across endpoints, use these linking conventions:
- claim to bill: `claim_id` field on the bill
- bill to payment: `bill_id` field on the payment
- business to vendor: `business_id` field on the vendor
- business to compliance: the `business_id` in the endpoint path
