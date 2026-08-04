# ERP / Compliance API Reference

Base URL: supplied by the runner as `<TASK_ENV_BASE_URL>`.
Authentication: none required.
All endpoints are read-only GET. No POST endpoints are available.

## Collection Endpoints

Collection endpoints support optional exact-match query parameters by field name, plus optional `limit` and `offset` query parameters (both integers) for pagination.

| Endpoint | Description |
|----------|-------------|
| `GET /claims` or `GET /api/claims` | List all expense/reimbursement claims. Filter by claim status or other claim fields. |
| `GET /bills` or `GET /api/ap/bills` | List all AP bills. Filter by bill status, claim reference, vendor, or amount. |
| `GET /payments` or `GET /api/ap/payments` | List all AP payments. Filter by payment status, bill reference, or amount. |
| `GET /api/ap/aging` | List AP aging buckets and open balances. |
| `GET /vendors` or `GET /api/vendors` | List all vendors. Filter by vendor status, business ID, or other vendor fields. |
| `GET /compliance/objects` or `GET /api/compliance/objects` | List all compliance objects across businesses. |
| `GET /prepaids/invoices` or `GET /api/prepaids/invoices` | List all prepaid invoices with schedules. Filter by account, invoice ID, or entity. |
| `GET /gl/balances` or `GET /api/prepaids/gl-balances` | List GL account balances. Filter by account, entity, or period. |
| `GET /close/logs` or `GET /api/close/logs` | List close-period logs. Filter by period, entity, or status. |

## Detail Endpoints

Replace path placeholders such as `{claim_id}` or `{business_id}` with the identifier string.

| Endpoint | Description |
|----------|-------------|
| `GET /api/claims/{claim_id}` | Get a single claim by ID. Returns claim status, amount, approval state, and linked references. |
| `GET /api/compliance/ownership/{business_id}` | Get beneficial ownership structure for a business. Returns UBO names, ownership percentages, and reporting-threshold flags. |
| `GET /api/compliance/registry/{business_id}` | Get business registry information including license status, expiration dates, and legal entity details. |
| `GET /api/compliance/screening/{business_id}` | Get sanctions, PEP, and adverse-media screening results for a business and its owners. |
| `GET /api/compliance/bank/{business_id}` | Get bank account verification status including name-match results and account status. |

## Query Mechanics

- **Exact-match filtering**: Append `?field_name=value` to filter a collection by an exact field match. Multiple filters can be combined with `&`.
- **Pagination**: Append `?limit=N&offset=M` to retrieve a page of N results starting at offset M. Use when collections may be large.
- **Path parameters**: Replace `{placeholder}` in the URL path with the literal identifier value (no braces).

## Example Requests

```
GET <TASK_ENV_BASE_URL>/api/claims/{claim_id}
GET <TASK_ENV_BASE_URL>/api/ap/bills?claim_id={claim_id}
GET <TASK_ENV_BASE_URL>/api/compliance/ownership/{business_id}
GET <TASK_ENV_BASE_URL>/api/compliance/bank/{business_id}
GET <TASK_ENV_BASE_URL>/api/prepaids/invoices?account={account_code}&limit=50
GET <TASK_ENV_BASE_URL>/api/prepaids/gl-balances?account={account_code}&period={period}
GET <TASK_ENV_BASE_URL>/api/close/logs?period={period}&entity={entity_name}
```
