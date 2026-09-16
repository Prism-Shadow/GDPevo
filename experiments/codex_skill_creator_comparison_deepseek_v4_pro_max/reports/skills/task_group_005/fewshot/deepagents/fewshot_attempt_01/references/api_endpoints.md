
# API Endpoints Reference

This document describes the ERP finance API endpoints available in the shared task environment. The API uses dual-path routing: short paths (`/claims`) and `/api/*` paths (`/api/claims`) serve the same data with identical schemas. Prefer the `/api/*` path.

## Base URL

The runner provides `<TASK_ENV_BASE_URL>`. Always verify with `GET /api/endpoints` before relying on specific paths.

## Endpoint Inventory

### Claims

- **Path**: `GET /claims`, `GET /api/claims`, `GET /api/claims/{claim_id}`
- **Key fields**: `claim_id`, `status`, `amount`, `claimant`, `description`
- **Relationship**: Links to bills via `claim_id`

### AP Bills

- **Path**: `GET /bills`, `GET /api/ap/bills`
- **Key fields**: `bill_id`, `claim_id`, `status`, `amount`, `vendor_id`
- **Status values**: `approved`, `paid`, `scheduled`, `void`, `pending`
- **Relationship**: Links to claims via `claim_id`, to payments via `bill_id`

### Payments

- **Path**: `GET /payments`, `GET /api/ap/payments`
- **Key fields**: `payment_id`, `bill_id`, `status`, `amount`
- **Status values**: `cleared`, `scheduled`, `none`
- **Relationship**: Links to bills via `bill_id`; zero or more payments per bill

### AP Aging

- **Path**: `GET /api/ap/aging`
- **Key fields**: aging buckets and balances per vendor or bill

### Vendors

- **Path**: `GET /vendors`, `GET /api/vendors`
- **Key fields**: `vendor_id`, `business_id`, `vendor_name`, `status`

### Compliance

All compliance endpoints use `business_id` as the join key:

- **Path**: `GET /compliance/objects`, `GET /api/compliance/objects`
- **Path**: `GET /api/compliance/ownership/{business_id}` — beneficial ownership records; key fields: `ubo_name`, `ownership_percentage`
- **Path**: `GET /api/compliance/registry/{business_id}` — business registration details; key fields: `license_status`, `license_expiry`, `tax_id_status`
- **Path**: `GET /api/compliance/screening/{business_id}` — sanctions/PEP/adverse-media screening; key fields: `screening_status`, `screening_date`, `pep_status`, `sanctions_status`
- **Path**: `GET /api/compliance/bank/{business_id}` — bank account verification; key fields: `bank_account_status`, `bank_last4`, `bank_name`

### Prepaid Invoices

- **Path**: `GET /prepaids/invoices`, `GET /api/prepaids/invoices`
- **Key fields**: `prepaid_invoice_id`, `account`, `original_amount`, `amortization_term_months`, `amortization_start_date`, `monthly_amortization`, `cumulative_amortization`, `ending_balance`, `default_missing_term_flag`

### GL Balances

- **Path**: `GET /gl/balances`, `GET /api/prepaids/gl-balances`
- **Key fields**: `account`, `account_name`, `period`, `ending_balance`

### Close Logs

- **Path**: `GET /close/logs`, `GET /api/close/logs`
- **Key fields**: `close_log_id`, `claim_id` or `batch_id`, `status`, `notes`

## Cross-Reference Patterns

### Claims → Bills → Payments

```
claim_id ──────► claim_id in bills ──────► bill_id in payments
```

### Business → Compliance

```
business_id ──────► ownership/business_id
                  ► registry/business_id
                  ► screening/business_id
                  ► bank/business_id
```

### Prepaid → GL

```
invoice.account ──────► gl_balances.account (for a given period)
```

### Stale Snapshot → Current API

Compare snapshot `claim_id` to current claims, bills, payments. Flag divergences:

- Snapshot `approved` claim → API `void` bill: `ignore_void_bill`
- Snapshot `scheduled` payment → API `cleared` payment: `mark_in_flight_payment`
- Snapshot bill not matching API bill: `replace_with_matched_paid_bill`
- API claim not `approved`: `block_unapproved_claim`
- Bill amount mismatch: `exclude_amount_or_vendor_mismatch`

## Query Strategy

When endpoints do not support filtering by ID list, fetch the full list and filter client-side. When per-ID endpoints exist (e.g., `/api/claims/{claim_id}`), iterate over the candidate IDs to retrieve each record individually. Parallelize fetches across independent endpoints to minimize round trips.
