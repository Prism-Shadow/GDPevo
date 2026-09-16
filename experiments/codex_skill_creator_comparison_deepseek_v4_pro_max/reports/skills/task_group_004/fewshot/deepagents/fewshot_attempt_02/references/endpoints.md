## API Endpoint Catalog

Base URL: `<TASK_ENV_BASE_URL>` (injected by task environment)

### Account Endpoints

#### GET /api/accounts
Returns all accounts as `{"accounts": [...]}`. Each account object has:
- `account_id` (string)
- `account_aliases` (list of strings — includes legal name variants, "Ops" suffixes, "Subsidiary" forms)
- `billing_arr_current` (float — billing-system ARR, preferred ARR source)
- `contract_tenure_months` (int)
- `crm_arr` (float — CRM-reported ARR)
- `csm_owner` (string)
- `display_name` (string)
- `legal_name` (string)
- `lifecycle_status` (string — "active", "inactive", "churned")
- `product_plan` (string — e.g., "Strategic", "Enterprise", "Scale")
- `region` (string)
- `renewal_date` (string — YYYY-MM-DD)
- `segment` (string — "Strategic", "Enterprise", "Mid-Market")

#### GET /api/accounts/{account_id}
Same shape as a single account in the accounts list.

#### GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM
Returns `{"account_id": "...", "count": N, "metrics": [...]}`. Each metric:
- `month` (YYYY-MM), `quarter` (YYYY-QN)
- `recognized_revenue` (float — monthly recognized revenue)
- `support_ticket_count` (int — raw ticket count including spam/duplicates)
- `sla_compliance` (float — percentage, e.g. 85.9)
- `nps_score` (int or null — from monthly rollup; null when survey_status is "missing")
- `product_usage` (float — usage metric)
- `active_seats` (int), `survey_status` ("completed" or "missing")

#### GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD
Returns `{"account_id": "...", "count": N, "tickets": [...]}`. Each ticket:
- `ticket_id` (string), `created_date` (YYYY-MM-DD)
- `severity` (P1–P4), `product_area`, `status`
- `first_response_sla_met` (bool), `resolution_sla_met` (bool)
- `is_duplicate` (bool), `is_spam` (bool)

**Clean ticket count**: exclude tickets where `is_spam=true` or `is_duplicate=true`.

#### GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD
Returns `{"account_id": "...", "count": N, "nps_responses": [...]}`. Each response:
- `response_id`, `response_date`, `score` (int), `survey_channel`
- `retracted` (bool — exclude retracted responses)

**Latest NPS**: most recent non-retracted score. If none, use last non-null metric monthly nps_score.

### Billing and Finance Endpoints

#### GET /api/billing/snapshots
Returns `{"count": N, "snapshots": [...]}`. Each snapshot:
- `account_id`, `legal_name`, `as_of` (YYYY-MM-DD)
- `billing_arr` (float — billing system ARR as of that date, **preferred ARR source**)
- `mrr` (float), `source` ("billing_snapshot"), `posted` (bool)
- `snapshot_id` (e.g., "BILL-acct_...-2026-Q2")

#### GET /api/finance/ar-aging
Returns `{"count": N, "ar_aging": [...]}`. Each record:
- `aging_id`, `as_of` (YYYY-MM-DD), `quarter`, `region`
- `customer_name` (string — legal entity name for matching to CRM accounts)
- `current` (float), `1_30`, `31_60`, `61_90`, `90_plus` (all floats)

**Overdue balance** = `31_60 + 61_90 + 90_plus`. The `1_30` bucket is not considered overdue.

### Pipeline / Opportunities

#### GET /api/opportunities
Returns `{"count": N, "opportunities": [...]}`. Each opportunity:
- `opportunity_id`, `account_id`, `account_legal_name`
- `amount` (float), `product_line`, `stage`, `state` ("open", "won", "lost")
- `close_date`, `created_date` (YYYY-MM-DD), `region`

### HR and Event Endpoints

#### GET /api/hr/summary
Returns `{"count": N, "hr_summary": [...]}`. Grouped by quarter and region:
- `headcount`, `high_absence_employees` (int)
- `unpaid_claims_amount` (float), `unpaid_claims_count` (int)
- `open_advances_amount`, `open_advances_count`, `leave_liability_hours`, `attendance_rate`

#### GET /api/events/performance
Returns `{"count": N, "event_performance": [...]}`. Grouped by event_id and quarter:
- `event_orders` (int), `event_revenue` (float)
- `completed_orders`, `cancelled_orders`, `refunded_orders`, `pending_orders`
- `product_revenue` (float)

### Churn Model Exports

#### GET /exports/churn/train.csv
Training CSV with 19 features plus `Churn` label. Columns: customer_id, tenure, MonthlyCharges, TotalCharges, Contract, PaymentMethod, PaperlessBilling, Partner, Dependents, OnlineSecurity, OnlineBackup, DeviceProtection, TechSupport, StreamingTV, StreamingMovies, SupportTickets90d, NPSLast, UsageTrendPct, InvoicePastDue, ActiveSeatRatio, Churn (Yes/No).

#### GET /exports/churn/validation.csv
Same columns as train.csv, for accuracy evaluation.

#### GET /exports/churn/candidates.csv
Same features as train.csv but **no Churn column** — used for scoring unlabeled accounts. Use logistic regression trained on train.csv to predict churn probabilities.

#### GET /exports/account_metric_extract.csv
Flat CSV of monthly metrics across all accounts. Columns: account_id, legal_name, segment, region, month, recognized_revenue, clean_ticket_count, sla_compliance, nps_score, product_usage, active_seats.

### Cross-Entity Linking

To link A/R customers to CRM accounts, match `customer_name` from `/api/finance/ar-aging` against each account's `legal_name` or any entry in `account_aliases`. If a match is found, `link_status` is "linked" and `account_id` can be populated; otherwise "unlinked".

### Billing Snapshots as ARR Source

For tasks requiring current ARR as of a specific date, **prefer** `/api/billing/snapshots` filtered to the matching `as_of` date. Fall back to `billing_arr_current` from `/api/accounts` when a snapshot for the exact date is unavailable. When setting `uses_billing_arr_source` or `arr_source_code`, use `REV-4` when billing snapshots were the primary source.

### Health Endpoint

#### GET /api/health
Returns service status, row counts per dataset, and seed identifier.
