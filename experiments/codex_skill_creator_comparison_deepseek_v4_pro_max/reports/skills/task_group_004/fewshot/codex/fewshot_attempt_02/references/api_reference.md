# ApexCloud Retention Operations API Reference

Full field schemas for every endpoint. Use as a lookup when fetching data.

## `GET /api/accounts`

Returns `.accounts[]` — a list of all account profiles.

Fields per account:
- `account_id` (str) — unique account identifier
- `display_name` (str) — short display name
- `legal_name` (str) — full legal entity name
- `account_aliases` (list[str]) — known alias names for linking
- `region` (str) — geographic region
- `segment` (str) — customer segment (Strategic, Enterprise, Mid-Market)
- `product_plan` (str) — plan tier (Strategic, Enterprise, Scale)
- `lifecycle_status` (str) — account status (active, etc.)
- `contract_tenure_months` (int) — months since contract start
- `renewal_date` (str) — next renewal date YYYY-MM-DD
- `billing_arr_current` (float) — current billing ARR
- `crm_arr` (float) — CRM-reported ARR
- `csm_owner` (str) — assigned CSM name

## `GET /api/accounts/{account_id}`

Same fields as a single element from the list above.

## `GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM`

Returns `.metrics[]` — one row per month in range. Fields:
- `account_id` (str)
- `month` (str) — YYYY-MM
- `quarter` (str) — YYYY-QN
- `recognized_revenue` (float) — CRM closed-won revenue for the month
- `support_ticket_count` (int) — raw ticket volume
- `sla_compliance` (float) — SLA compliance percentage (0–100)
- `nps_score` (int|null) — NPS score for the month (null if no survey)
- `survey_status` (str) — completed or missing
- `product_usage` (float) — usage metric (varies by product)
- `active_seats` (int) — active licensed seats

`.count` gives the number of month rows returned.

## `GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`

Returns `.tickets[]` — support tickets in date range. Fields:
- `ticket_id` (str)
- `account_id` (str)
- `created_date` (str) — YYYY-MM-DD
- `status` (str) — closed, open, etc.
- `severity` (str) — P3, P4, etc.
- `product_area` (str) — billing, integrations, workflow, identity, etc.
- `first_response_sla_met` (bool)
- `resolution_sla_met` (bool)
- `is_duplicate` (bool) — exclude when counting clean tickets
- `is_spam` (bool) — exclude when counting clean tickets

`.count` gives total tickets including duplicates/spam.

## `GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`

Returns `.nps_responses[]` — NPS surveys in date range. Fields:
- `response_id` (str)
- `account_id` (str)
- `response_date` (str) — YYYY-MM-DD
- `score` (int)
- `survey_channel` (str) — email, csm_call, etc.
- `retracted` (bool) — exclude retracted responses

`.count` gives total responses including retracted.

## `GET /api/billing/snapshots`

Returns `.snapshots[]` — quarterly billing data. Fields:
- `snapshot_id` (str)
- `account_id` (str)
- `legal_name` (str)
- `as_of` (str) — quarter-end date YYYY-MM-DD
- `billing_arr` (float) — annualized run rate from billing
- `mrr` (float) — monthly recurring revenue
- `source` (str) — billing_snapshot
- `posted` (bool)

`.count` gives total snapshots across all quarters/accounts.

Filter to the assessment date's quarter-end to get the current billing ARR for
an account.

## `GET /api/finance/ar-aging`

Returns `.ar_aging[]` — AR aging by customer and quarter. Fields:
- `aging_id` (str)
- `customer_name` (str) — legal entity name of the debtor
- `quarter` (str) — YYYY-QN
- `as_of` (str) — YYYY-MM-DD
- `region` (str)
- `current` (float) — not yet due
- `1_30` (float) — 1–30 days past due
- `31_60` (float) — 31–60 days past due
- `61_90` (float) — 61–90 days past due
- `90_plus` (float) — 90+ days past due

Overdue balance = 1_30 + 31_60 + 61_90 + 90_plus. Do not include current.

## `GET /api/opportunities`

Returns `.opportunities[]` — CRM pipeline. Fields:
- `opportunity_id` (str)
- `account_id` (str)
- `account_legal_name` (str)
- `amount` (float) — deal amount
- `stage` (str) — Discovery, Proposal, etc.
- `state` (str) — open, closed_won, closed_lost
- `close_date` (str) — YYYY-MM-DD
- `created_date` (str) — YYYY-MM-DD
- `product_line` (str) — Core Retention, AI Assist, Data Cloud, Workflow Plus, etc.
- `region` (str)

`.count` gives total opportunities.

## `GET /api/hr/summary`

Returns `.hr_summary[]` — HR/people ops by region and quarter. Fields:
- `quarter` (str)
- `region` (str)
- `headcount` (int)
- `attendance_rate` (float) — percentage
- `high_absence_employees` (int)
- `leave_liability_hours` (float)
- `open_advances_amount` (float)
- `open_advances_count` (int)
- `unpaid_claims_amount` (float)
- `unpaid_claims_count` (int)

`.count` gives total HR summary rows.

## `GET /api/events/performance`

Returns `.event_performance[]` — event operations by event and quarter. Fields:
- `event_id` (str) — retention_summit, apex_connect, field_roundtable, renewal_lab, etc.
- `quarter` (str)
- `event_orders` (int) — total orders
- `event_revenue` (float)
- `completed_orders` (int)
- `cancelled_orders` (int)
- `pending_orders` (int)
- `refunded_orders` (int)
- `product_revenue` (float)

`.count` gives total event performance records.

## `GET /exports/churn/train.csv`

CSV with 180 rows, 20 columns. Last column is Churn (Yes/No). 19 feature
columns: tenure, MonthlyCharges, TotalCharges, Contract, PaymentMethod,
PaperlessBilling, Partner, Dependents, OnlineSecurity, OnlineBackup,
DeviceProtection, TechSupport, StreamingTV, StreamingMovies, SupportTickets90d,
NPSLast, UsageTrendPct, InvoicePastDue, ActiveSeatRatio.

## `GET /exports/churn/validation.csv`

Same schema as train.csv. 60 rows. Use for accuracy validation.

## `GET /exports/churn/candidates.csv`

Same 19 feature columns as train.csv but no Churn column. Contains candidate
accounts keyed by customer_id matching ApexCloud account_id values. Use for
outreach ranking.

## `GET /exports/account_metric_extract.csv`

CSV with normalized monthly metrics: account_id, legal_name, segment, region,
month, recognized_revenue, clean_ticket_count, sla_compliance, nps_score,
product_usage, active_seats. Covers all historical months. clean_ticket_count is
already deduplicated (duplicates and spam excluded).
