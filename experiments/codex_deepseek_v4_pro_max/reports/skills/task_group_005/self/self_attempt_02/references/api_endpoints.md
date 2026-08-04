# API Endpoint Reference

Base URL: `<TASK_ENV_BASE_URL>`
Authentication: none
Method: GET only (no POST)

## Collection endpoints (accept query params, limit, offset)

| Path | Alternate | Resource |
|------|-----------|----------|
| `/claims` | `/api/claims` | Expense claims |
| `/bills` | `/api/ap/bills` | AP bills |
| `/payments` | `/api/ap/payments` | Payment records |
| `/api/ap/aging` | — | AP aging |
| `/vendors` | `/api/vendors` | Vendor master |
| `/compliance/objects` | `/api/compliance/objects` | Compliance records |
| `/prepaids/invoices` | `/api/prepaids/invoices` | Prepaid invoices |
| `/gl/balances` | `/api/prepaids/gl-balances` | GL balances |
| `/close/logs` | `/api/close/logs` | Close logs |

## Detail endpoints (use path placeholder)

| Path | Purpose |
|------|---------|
| `/api/claims/{claim_id}` | Single claim |
| `/api/compliance/ownership/{business_id}` | UBO ownership |
| `/api/compliance/registry/{business_id}` | Business registry |
| `/api/compliance/screening/{business_id}` | Sanctions screening |
| `/api/compliance/bank/{business_id}` | Bank validation |

## Query examples

```
<BASE>/claims?status=approved&limit=50&offset=0
<BASE>/api/claims/CLM-2025-OPS-017
<BASE>/api/compliance/bank/BUS-2025-0009
<BASE>/bills?claim_id=CLM-2025-FIN-042
<BASE>/payments?bill_id=AP-2025-0079
```
