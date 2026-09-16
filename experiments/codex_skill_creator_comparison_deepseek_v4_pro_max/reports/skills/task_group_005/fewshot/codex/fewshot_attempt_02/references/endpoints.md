# ERP Finance API Endpoint Catalog

Base URL is supplied as `<TASK_ENV_BASE_URL>`. Substitute it before issuing requests.

Most resources are reachable at two path variants. Both return the same underlying data; use whichever is referenced in the task prompt or payload.

## Claims

| Path | Notes |
|------|-------|
| `GET /claims` | List all claims. |
| `GET /api/claims` | Alternative path. |
| `GET /api/claims/{claim_id}` | Single claim by ID. |

Claim records include: `claim_id`, `status` (approved, draft, paid, void), `amount`, `vendor`, `description`, `submit_date`.

## AP Bills

| Path | Notes |
|------|-------|
| `GET /bills` | List all AP bills. |
| `GET /api/ap/bills` | Alternative path. |

Bill records include: `bill_id`, `claim_id` (link to claim), `status` (approved, scheduled, paid, void), `amount`, `vendor`, `due_date`.

## Payments

| Path | Notes |
|------|-------|
| `GET /payments` | List all payments. |
| `GET /api/ap/payments` | Alternative path. |

Payment records include: `payment_id`, `bill_id`, `claim_id` (when available), `status` (cleared, in_flight, none), `amount`, `payment_date`.

## AP Aging

| Path | Notes |
|------|-------|
| `GET /api/ap/aging` | AP aging report. |

## Vendors

| Path | Notes |
|------|-------|
| `GET /vendors` | List all vendors. |
| `GET /api/vendors` | Alternative path. |

Vendor records include: `vendor_id`, `business_id`, `name`, `status` (active, on_hold), `tax_id`, `bank_last4`.

## Compliance

| Path | Notes |
|------|-------|
| `GET /compliance/objects` | List all compliance objects. |
| `GET /api/compliance/objects` | Alternative path. |
| `GET /api/compliance/ownership/{business_id}` | Beneficial ownership data. Includes owners with name and ownership percentage. |
| `GET /api/compliance/registry/{business_id}` | Business registry data. Includes `license_expiry_date`. |
| `GET /api/compliance/screening/{business_id}` | Sanctions/PEP/adverse-media screening. Includes `pep_flag`, `sanctions_flag`, `shell_company_flag`. |
| `GET /api/compliance/bank/{business_id}` | Bank verification. Includes `account_status` (active, closed, name_mismatch). |

## Prepaid Invoices

| Path | Notes |
|------|-------|
| `GET /prepaids/invoices` | List all prepaid invoices. |
| `GET /api/prepaids/invoices` | Alternative path. |

Prepaid invoice records include: `prepaid_invoice_id`, `account` (e.g., "1250", "1251"), `original_amount`, `start_date` (YYYY-MM-DD), `term_months` (number of months), `monthly_amortization`, `amortization_schedule` (array of period objects with `period` YYYY-MM and `amount`).

## GL Balances

| Path | Notes |
|------|-------|
| `GET /gl/balances` | General ledger balances. |
| `GET /api/prepaids/gl-balances` | Alternative path. |

GL balance records include: `account`, `account_name`, `period` (YYYY-MM), `ending_balance`.

## Close Logs

| Path | Notes |
|------|-------|
| `GET /close/logs` | Close/review logs. |
| `GET /api/close/logs` | Alternative path. |

Close log records include: `close_log_id`, `period`, `claim_ids` (list of affected claims), `status`, `notes`.
