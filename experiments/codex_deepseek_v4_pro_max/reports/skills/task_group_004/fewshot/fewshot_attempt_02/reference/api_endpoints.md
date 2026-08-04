 # ApexCloud Retention Operations API

 Base URL: `{TASK_ENV_BASE_URL}` (resolve from the environment or `environment_access.md`)

 No authentication headers required.

 ## Account endpoints

 ### GET /api/accounts
 Returns a list of all CRM account objects. Each includes `account_id`, `company_name`, `segment` (strategic / enterprise / mid_market / smb), `tenure_months`, `renewal_date`, `lifecycle_stage` (onboarding / adopting / mature / at_risk), and `region`.

 ### GET /api/accounts/{account_id}
 Returns the full profile for a single account including `account_id`, `company_name`, `segment`, `tenure_months`, `renewal_date`, `lifecycle_stage`, `region`, `current_arr`, and `owner`.

 ### GET /api/accounts/{account_id}/metrics
 Returns time-series monthly metrics for the account.

 Query parameters:
 - `start` (YYYY-MM) — inclusive start month.
 - `end` (YYYY-MM) — inclusive end month.

 Response includes per-month `revenue`, `usage_units`, `active_users`, and `license_utilization_pct`.

 ### GET /api/accounts/{account_id}/tickets
 Returns support ticket records.

 Query parameters:
 - `start` (YYYY-MM-DD) — inclusive start date.
 - `end` (YYYY-MM-DD) — inclusive end date.

 Response includes `ticket_id`, `created_date`, `resolved_date`, `severity`, `status`, and `sla_met` (boolean).

 ### GET /api/accounts/{account_id}/nps
 Returns NPS survey responses.

 Query parameters:
 - `start` (YYYY-MM-DD) — inclusive start date.
 - `end` (YYYY-MM-DD) — inclusive end date.

 Response includes `survey_id`, `survey_date`, `score` (0-100), and `category` (promoter / passive / detractor).

 ### GET /api/accounts/{account_id}/billing
 Returns the most recent billing snapshot for the account. Response includes `current_arr`, `billing_frequency`, `last_invoice_date`, `last_invoice_amount`, and `payment_terms`.

 ### GET /api/accounts/{account_id}/ar-aging
 Returns accounts receivable aging for the account. Response includes `total_outstanding`, `current_bucket`, `30_day_bucket`, `60_day_bucket`, `90_plus_bucket`, and `overdue_balance`.

 ## Portfolio / aggregate endpoints

 ### GET /api/billing/snapshots
 Returns billing snapshots for multiple accounts. Use for cross-account ARR comparisons.

 ### GET /api/finance/ar-aging
 Returns A/R aging for all customers across the portfolio. Use for receivables-and-pipeline reviews that need to discover overdue customers, then cross-reference against `/api/accounts`. Response is a list of customer records with `customer_name`, `total_outstanding`, `current_bucket`, `30_day_bucket`, `60_day_bucket`, `90_plus_bucket`, and `overdue_balance`.

 ### GET /api/opportunities
 Returns CRM pipeline opportunities.

 Query parameters:
 - `stage` — filter by stage (won / lost / open).
 - `close_date_start` (YYYY-MM-DD) — inclusive start.
 - `close_date_end` (YYYY-MM-DD) — inclusive end.

 Response includes `opportunity_id`, `account_id`, `product_line`, `amount`, `stage`, `close_date`, and `region`.

 ## Operations context endpoints

 ### GET /api/hr/summary
 Returns headcount and financial summary. Response includes `total_headcount`, `unpaid_claims_total`, and `region_breakdown`.

 ### GET /api/events/performance
 Returns event performance data. Query: `event_name` (e.g. `apex_connect`), `period` (YYYY-QN). Response includes `total_orders`, `total_revenue`, and `attendee_count`.

 ## Export endpoints

 ### GET /exports/churn/train.csv
 Training dataset for churn prediction model. CSV with columns: `customer_id`, `tenure_months`, `monthly_charges`, `total_charges`, `contract_type`, `payment_method`, `monthly_support_tickets`, `sla_breach_count`, `latest_nps`, `overdue_balance`, `churn` (0/1), plus additional feature columns.

 ### GET /exports/churn/validation.csv
 Validation dataset with the same schema, used for computing accuracy.

 ### GET /exports/churn/candidates.csv
 Candidate accounts for churn prediction. Same feature columns, no `churn` label.

 ### GET /exports/account_metric_extract.csv
 Bulk export of account-level metrics suitable for cross-account analysis.
