# Finance ERP API Reference
 
 All endpoints return JSON with the structure `{"count": N, "data": [...], "endpoint": "...", "limit": N, "offset": N, "total": N}`. Filter with exact-match query parameters by field name. Use `limit` and `offset` for pagination.
 
 Base URL is provided at runtime as `<TASK_ENV_BASE_URL>`. All endpoints below are relative to that base.
 
 ## Claims
 
 `/api/claims` — Filter by `claim_id`, `status`, `vendor_id`, `department`, `category`.
 
 ```json
 {
   "claim_id": "CLM-2025-0001",
   "amount": 566.84,
   "currency": "USD",
   "status": "approved",
   "submitted_date": "2025-01-20",
   "approved_date": "2025-01-31",
   "department": "Operations",
   "category": "Travel",
   "employee_name": "Riley Morgan",
   "vendor_id": null,
   "receipt_status": "attached",
   "policy_flags": [],
   "notes": ""
 }
 ```
 
 **Status values:** `submitted`, `needs_receipt`, `approved`, `rejected`, `paid`.
 
 **Single-claim lookup:** `GET /api/claims?claim_id=CLM-2025-0001`
 
 ## AP Bills
 
 `/api/ap/bills` — Filter by `bill_id`, `claim_id`, `status`, `vendor_id`.
 
 ```json
 {
   "bill_id": "AP-2025-0001",
   "claim_id": null,
   "vendor_id": "VEN-0019",
   "amount": 21771.50,
   "currency": "USD",
   "status": "paid",
   "account": "6200",
   "bill_date": "2025-01-04",
   "due_date": "2025-02-03",
   "invoice_number": "INV-79957",
   "memo": ""
 }
 ```
 
 **Status values:** `draft`, `approved`, `scheduled`, `paid`, `void`.
 
 **Claim-linked bills:** Filter with `claim_id` to find the AP bill(s) for a given claim. A claim may have zero, one, or multiple bills. Use the bill whose status is active (not `void`) as the primary record.
 
 ## AP Payments
 
 `/api/ap/payments` — Filter by `bill_id`, `payment_id`, `status`, `vendor_id`.
 
 ```json
 {
   "payment_id": "PAY-2025-0001",
   "bill_id": "AP-2025-0063",
   "vendor_id": "VEN-0024",
   "amount": 8021.70,
   "status": "processing",
   "method": "ACH",
   "bank_reference": "BNK4330664",
   "payment_date": "2025-06-07"
 }
 ```
 
 **Status values:** `scheduled`, `processing`, `cleared`, `failed`. Only `cleared` payments are settled.
 
 ## AP Aging
 
 `/api/ap/aging` — Filter by `bill_id`, `claim_id`, `status`, `vendor_id`.
 
 ```json
 {
   "bill_id": "AP-2025-0001",
   "claim_id": null,
   "vendor_id": "VEN-0019",
   "amount": 21771.50,
   "paid_amount": 21771.50,
   "balance": 0.00,
   "status": "paid",
   "bill_date": "2025-01-04",
   "due_date": "2025-02-03",
   "as_of": ""
 }
 ```
 
 **Key fields:** `balance` is the open amount (bill amount minus cleared payments). `paid_amount` is the total of cleared payments applied. Use this for open-balance decisions — it is more reliable than deriving it from bills and payments separately.
 
 ## Vendors
 
 `/api/vendors` — Filter by `vendor_id`, `status`, `industry`, `tax_id`.
 
 ```json
 {
   "vendor_id": "VEN-0001",
   "vendor_name": "Summit Services",
   "legal_name": "Summit Services, Inc.",
   "status": "active",
   "industry": "Payroll",
   "tax_id": "TIN608869",
   "default_account": "6200",
   "payment_terms": "Net 45",
   "bank_account_last4": "5554",
   "updated_at": "2025-01-23"
 }
 ```
 
 **Status values:** `active`, `inactive`, `on_hold`.
 
 ## Compliance Objects (aggregate view)
 
 `/api/compliance/objects` — Filter by `business_id`, `vendor_id`, `review_status`, `jurisdiction`, `sanctions_check_status`.
 
 ```json
 {
   "business_id": "BUS-2025-0001",
   "business_name": "Lattice Works",
   "vendor_id": "VEN-0008",
   "jurisdiction": "New York",
   "registration_number": "REG-760307",
   "tax_id": "TIN527199",
   "license_expiry": "2025-07-01",
   "review_status": "escalated",
   "risk_score": 84,
   "pep_status": "none",
   "sanctions_check_status": "clear",
   "shell_company_suspected": false,
   "bank_account_status": "verified",
   "ownership_layer_count": 4,
   "missing_fields": [],
   "ubo_list": [
     {"name": "Samir Bell", "ownership_pct": 25},
     {"name": "Samir Bell", "ownership_pct": 10}
   ]
 }
 ```
 
 **Key review fields:**
 - `pep_status`: `none`, `confirmed_pep`
 - `sanctions_check_status`: `not_run`, `clear`, `matched`, `confirmed`
 - `bank_account_status`: `verified`, `name_mismatch`, `closed`, `not_verified`
 - `license_expiry`: YYYY-MM-DD date
 - `review_status`: `not_started`, `in_review`, `escalated`, `completed`
 - `missing_fields`: list of missing items like `["license", "website", "bank_statement"]`
 
 This endpoint returns all compliance data in one record. Use it as the primary compliance source.
 
 ## Compliance Detail Endpoints
 
 All use `GET /api/compliance/{endpoint}/{business_id}`.
 
 **Ownership** — `/api/compliance/ownership/{business_id}`
 ```json
 {
   "business_id": "BUS-2025-0009",
   "ownership_layer_count": 4,
   "shell_company_suspected": false,
   "ubo_list": [{"name": "Alex Stone", "ownership_pct": 45}]
 }
 ```
 
 **Registry** — `/api/compliance/registry/{business_id}`
 ```json
 {
   "business_id": "BUS-2025-0009",
   "jurisdiction": "Delaware",
   "license_expiry": "2025-02-12",
   "registration_number": "REG-836527",
   "tax_id": "TIN999999"
 }
 ```
 
 **Screening** — `/api/compliance/screening/{business_id}`
 ```json
 {
   "business_id": "BUS-2025-0009",
   "pep_status": "confirmed_pep",
   "sanctions_check_status": "clear"
 }
 ```
 
 **Bank** — `/api/compliance/bank/{business_id}`
 ```json
 {
   "business_id": "BUS-2025-0009",
   "bank_account_status": "verified"
 }
 ```
 
 The detail endpoints are useful when the aggregate `/api/compliance/objects` result needs cross-verification, or when a specific sub-record is missing from the aggregate.
 
 **Reporting threshold for UBO:** Count unique names where `ownership_pct >= 25`. Combine all `ubo_list` entries from both aggregate and detail endpoints. A name appearing multiple times (different layers or entities) counts once.
 
 ## Prepaid Invoices
 
 `/api/prepaids/invoices` — Filter by `prepaid_invoice_id`, `account`, `vendor_id`.
 
 ```json
 {
   "prepaid_invoice_id": "PPD-2025-0001",
   "account": "1250",
   "vendor_id": "VEN-0042",
   "description": "Maintenance contract",
   "invoice_number": "PP-7678",
   "invoice_date": "2025-03-01",
   "original_amount": 7637.68,
   "monthly_amortization": 848.63,
   "recognition_method": "straight_line",
   "service_start": "2025-03-01",
   "service_end": "2025-11-30",
   "source_document": "Renewal notice",
   "data_quality_flags": ["rounded_amount"]
 }
 ```
 
 **Straight-line amortization:** `monthly_amortization` is the per-month expense. For any month in the service period, use the `monthly_amortization` value directly from the invoice record — it already reflects any mid-month proration. The cumulative amortization through a target month is `monthly_amortization * months_from_service_start_to_end_of_target_month`. `ending_balance = original_amount - cumulative_amortization_through_month`, clamped to zero when negative.
 
 **Data quality flags:** `rounded_amount` (amounts may have precision issues), `missing_contract_dates` (default or missing term), `missing_source_document`.
 
 ## Prepaid GL Balances
 
 `/api/prepaids/gl-balances` — Filter by `account`, `period`, `entity`.
 
 ```json
 {
   "account": "1250",
   "account_name": "Prepaid Expenses",
   "entity": "Aurisic US",
   "period": "2025-03",
   "ending_balance": 473655.55,
   "source": "close ledger export",
   "loaded_at": "2025-05-03T09:30:00Z"
 }
 ```
 
 Look up the target period's `ending_balance` for each account in scope. Compare to the schedule-derived ending balance to detect variances.
 
 ## Close Logs
 
 `/api/close/logs` — Filter by `log_id`, `period`, `area`, `related_account`, `status`.
 
 ```json
 {
   "log_id": "CLOSE-2025-04-009",
   "period": "2025-04",
   "area": "Expense",
   "owner": "Leo Martin",
   "message": "Reviewer cleared variance",
   "related_account": null,
   "status": "closed",
   "created_at": "2025-04-17T18:15:00Z"
 }
 ```
 
 **Areas:** `Compliance`, `Expense`, `Prepaids`, `AP`. Filter by area when checking for recent close activity relevant to a batch.
 **Status values:** `open`, `closed`.
 
 ## Reimbursement-specific bill IDs
 
 Reimbursement AP bills use the format `AP-2025-REIM-NNN`. Claim-to-bill linkage is established via `claim_id` on the bill record.
