# ERP Finance API Endpoint Catalog

This catalog lists all known REST endpoints exposed by the shared ERP/compliance
API at `<TASK_ENV_BASE_URL>`. Every endpoint returns JSON. Use `/endpoints` to
confirm which routes are live in the current environment before calling them.

## Core finance endpoints

| Entity | Endpoints | Filters | Notes |
|--------|-----------|---------|-------|
| Claims | `/claims`, `/api/claims`, `/api/claims/{claim_id}` | `claim_id` (exact) | A claim record has a `status` field (e.g., `approved`, `paid`, `voided`), an `amount`, and optional `bill_id` linkage. |
| AP bills | `/bills`, `/api/ap/bills` | `bill_id`, `claim_id` (exact) | An AP bill has a `status` (e.g., `scheduled`, `approved`, `paid`, `voided`), an `amount`, a `bill_id`, and an optional `claim_id` backlink. |
| Payments | `/payments`, `/api/ap/payments` | `bill_id`, `claim_id` (exact) | A payment record has a `status` (e.g., `cleared`, `none`, `scheduled`), an `amount`, and a `bill_id` or `claim_id` linkage. |
| AP aging | `/api/ap/aging` | `claim_id`, `bill_id` (exact) | Open payable balances by claim or bill. |
| GL balances | `/gl/balances`, `/api/prepaids/gl-balances` | `account`, `period` (exact) | Returns ending balance for a GL account in a given period (`YYYY-MM`). |
| Prepaid invoices | `/prepaids/invoices`, `/api/prepaids/invoices` | `prepaid_invoice_id`, `account` (exact) | Each record has `original_amount`, `monthly_amortization`, `amortization_term_months`, `start_month`, and an `account` field. |

## Vendor and compliance endpoints

| Entity | Endpoints | Use |
|--------|-----------|-----|
| Vendors | `/vendors`, `/api/vendors` | Fetch by `vendor_id` or `business_id`. Contains tax ID, license expiry, bank account, and risk score. |
| Compliance objects | `/compliance/objects`, `/api/compliance/objects` | Broad listing; prefer the sub-endpoints below. |
| Ownership / UBO | `/api/compliance/ownership/{business_id}` | Returns ultimate beneficial owners with names, percentages, and reporting-threshold flags. |
| Registry | `/api/compliance/registry/{business_id}` | Business registration status, license details, expiry dates. |
| Screening | `/api/compliance/screening/{business_id}` | PEP matches, sanctions results, adverse media, shell-company indicators. |
| Bank verification | `/api/compliance/bank/{business_id}` | Bank account status (`active`, `closed`, `name_mismatch`), last-4 institution codes. |

## Close logs

| Entity | Endpoints | Filters |
|--------|-----------|---------|
| Close logs | `/close/logs`, `/api/close/logs` | `claim_id`, `close_log_id`, `close_period` (exact) |

## API navigation patterns

- All list endpoints accept exact-match query parameters (e.g.,
  `?claim_id=CLM-YYYY-NNN`) and support `&limit=N&offset=M` pagination.
- The `/api/compliance/*` sub-endpoints use path parameters
  (`/api/compliance/ownership/BUS-YYYY-NNNN`), not query params.
- When a claim has a `bill_id`, use that `bill_id` to fetch the bill; when the
  bill has a payment linkage, use that to fetch the payment. Follow the chain.
- For vendor tasks, start with `/api/vendors` to get the base record, then call
  the four compliance sub-endpoints per business_id in parallel.
