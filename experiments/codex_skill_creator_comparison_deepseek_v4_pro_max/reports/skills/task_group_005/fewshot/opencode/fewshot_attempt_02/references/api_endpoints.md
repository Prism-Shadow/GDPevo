# API Endpoints Reference

All endpoints live at the base URL provided as `<TASK_ENV_BASE_URL>`.
Every endpoint supports exact-match query parameter filtering by field name,
plus `limit` and `offset` pagination.

## Endpoint table

| Path | Returns | Key filter fields |
|------|---------|-------------------|
| `/claims` or `/api/claims` | List of expense claims | `claim_id`, `status`, `vendor_id`, `department` |
| `/api/claims/{claim_id}` | Single claim | -- |
| `/bills` or `/api/ap/bills` | List of AP bills | `claim_id`, `status`, `bill_id`, `vendor_id` |
| `/payments` or `/api/ap/payments` | List of payments | `bill_id`, `status`, `payment_id`, `vendor_id` |
| `/api/ap/aging` | AP aging with balance/payment info | `bill_id`, `claim_id`, `status` |
| `/vendors` or `/api/vendors` | List of vendors | `vendor_id` |
| `/compliance/objects` or `/api/compliance/objects` | List of compliance records | `business_id` |
| `/api/compliance/ownership/{id}` | UBO ownership detail | -- |
| `/api/compliance/screening/{id}` | PEP and sanctions status | -- |
| `/api/compliance/bank/{id}` | Bank account verification | -- |
| `/api/compliance/registry/{id}` | License, tax, registration | -- |
| `/prepaids/invoices` or `/api/prepaids/invoices` | Prepaid invoice schedules | `prepaid_invoice_id`, `account`, `vendor_id` |
| `/gl/balances` or `/api/prepaids/gl-balances` | GL ending balances | `account`, `period` |
| `/close/logs` or `/api/close/logs` | Period close log entries | `period`, `area`, `status` |
| `/endpoints` | Endpoint listing and filtering help | -- |

## Claim record fields

```
claim_id:      string, e.g. "CLM-2025-OPS-017"
amount:        number, USD
status:        enum: approved | paid | submitted | rejected | needs_receipt
approved_date: string or null, YYYY-MM-DD
submitted_date: string, YYYY-MM-DD
employee_name: string
department:    string
category:      string (Travel, Software, Meals, Office supplies, etc.)
currency:      string, always "USD"
receipt_status: enum: attached | partial
policy_flags:  list of strings (may include: weekend_spend, late_receipt,
               manual_rate, over_limit, duplicate_amount)
vendor_id:     string or null, e.g. "VEN-0007"
notes:         string
```

## AP bill record fields

```
bill_id:        string, e.g. "AP-2025-REIM-017"
claim_id:       string or null (links to a claim when present)
amount:         number, USD
status:         enum: draft | approved | scheduled | paid | void
bill_date:      string, YYYY-MM-DD
due_date:       string, YYYY-MM-DD
invoice_number: string
account:        string, account code e.g. "1250", "6200", "2100"
vendor_id:      string
memo:           string (flags: "Duplicate check required", "Accrual review",
               "Imported from AP inbox", etc.)
currency:       string, always "USD"
```

## Payment record fields

```
payment_id:    string, e.g. "PAY-2025-0037"
bill_id:       string (links to an AP bill)
amount:        number, USD
status:        enum: scheduled | processing | cleared
payment_date:  string, YYYY-MM-DD
method:        enum: ACH | Check | Wire | Virtual card
bank_reference: string
vendor_id:     string
```

## AP aging record fields

```
bill_id:      string
claim_id:     string or null
amount:       number, original bill amount
paid_amount:  number, sum of cleared payments
balance:      number, amount - paid_amount
status:       string
bill_date:    string
due_date:     string
vendor_id:    string
```

## Vendor record fields

```
vendor_id:          string, e.g. "VEN-0007"
vendor_name:        string
legal_name:         string
status:             enum: active | inactive
industry:           string
payment_terms:      string
default_account:    string
bank_account_last4: string, 4 digits
tax_id:             string
updated_at:         string, YYYY-MM-DD
```

## Compliance object fields

```
business_id:              string, e.g. "BUS-2025-0009"
business_name:            string
vendor_id:                string (links to vendor)
registration_number:      string
jurisdiction:             string
license_expiry:           string, YYYY-MM-DD
tax_id:                   string, e.g. "TIN527199"
bank_account_status:      enum: verified | name_mismatch | closed
pep_status:               enum: none | confirmed_pep | possible_pep | not_run
sanctions_check_status:   enum: clear | confirmed_match | possible_match | not_run
shell_company_suspected:  boolean
risk_score:               integer
missing_fields:           list of strings (license, website, bank_statement,
                         beneficial_owner_id)
ownership_layer_count:    integer
review_status:            enum: not_started | in_review | awaiting_information |
                          escalated | approved
ubo_list:                 list of {name: string, ownership_pct: number}
```

## Prepaid invoice record fields

```
prepaid_invoice_id:    string, e.g. "PPD-2025-0001"
account:               string, account code
original_amount:       number, USD
monthly_amortization:  number, USD per month
recognition_method:    string, always "straight_line"
service_start:         string, YYYY-MM-DD
service_end:           string, YYYY-MM-DD
invoice_number:        string
invoice_date:          string, YYYY-MM-DD
description:           string
source_document:       string
vendor_id:             string
data_quality_flags:    list of strings (missing_contract_dates, rounded_amount)
```

## GL balance record fields

```
period:         string, YYYY-MM
entity:         string
account:        string
account_name:   string
ending_balance: number, USD
source:         string
loaded_at:      string, ISO timestamp
```

## Close log record fields

```
log_id:          string, e.g. "CLOSE-2025-04-009"
period:          string, YYYY-MM
area:            string (AP, Expense, Prepaids, Treasury, Compliance)
message:         string
owner:           string
status:          enum: open | ready_for_review | closed
related_account: string or null
created_at:      string, ISO timestamp
```

## Pagination pattern

Every list endpoint wraps results in:

```json
{
  "count": <number of records in this page>,
  "total": <total records matching query>,
  "limit": <requested limit>,
  "offset": <requested offset>,
  "data": [ ... ]
}
```

When `count` equals `limit`, there may be more pages. Increment `offset` by
`limit` and fetch again until `count` falls below `limit`.

## Exact-match filtering

Filter with query parameters matching field names:

- `/api/claims?status=approved` returns only approved claims
- `/api/ap/bills?claim_id=CLM-2025-0090` returns bills linked to that claim
- `/api/compliance/objects?business_id=BUS-2025-0009` returns that business
- `/api/prepaids/gl-balances?period=2025-03&account=1250` returns GL balance
  for that period and account
