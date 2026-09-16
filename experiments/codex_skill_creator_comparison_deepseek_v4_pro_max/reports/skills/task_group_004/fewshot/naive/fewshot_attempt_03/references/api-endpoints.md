# ApexCloud Retention Operations API

Base URL: provided via `<TASK_ENV_BASE_URL>` in the prompt. All endpoints use GET with no authentication.

## Account endpoints

- `GET /api/accounts` -- list all CRM accounts. Returns an array of account objects with `id`, `name`, `segment`, `region`, `tenure_months`, `lifecycle_stage`, and related fields.
- `GET /api/accounts/{account_id}` -- single account profile. Same shape as the list entries but may include additional detail fields.

## Metrics endpoints

- `GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM` -- monthly revenue and product-usage metrics. Returns an array of month objects with `month`, `revenue`, and usage fields. Use `start` and `end` query parameters to bound the date range (inclusive). Month values use `YYYY-MM` format.

## Support and SLA endpoints

- `GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` -- support tickets opened in the date range. Returns an array of ticket objects with `id`, `status`, `sla_breach` or similar SLA fields, and timestamps. Count only clean (non-breached) tickets by filtering on SLA status.

## NPS endpoints

- `GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` -- NPS survey responses in the date range. Returns an array of survey objects with `score` (integer) and `date` fields. Use the most recent survey score as `latest_nps`.

## Billing and ARR endpoints

- `GET /api/accounts/{account_id}/billing` -- billing records for an account including current ARR. Returns an object with `current_arr` and billing history.
- `GET /api/billing/snapshots` -- cross-account billing snapshots. Returns an array of billing snapshot objects keyed by account.

## Accounts receivable endpoints

- `GET /api/accounts/{account_id}/ar-aging` -- A/R aging for a single account. Returns an object with aging buckets and overdue balance.
- `GET /api/finance/ar-aging` -- cross-customer A/R aging. Returns an array of A/R entries with `customer_name`, `overdue_balance`, and aging bucket breakdowns.

## CRM pipeline endpoints

- `GET /api/opportunities` -- CRM pipeline opportunities. Returns an array of opportunity objects with `id`, `account_id`, `product_line`, `amount`, `stage` (e.g., `closed_won`, `closed_lost`, `open`), and `close_date`.

## HR and events endpoints

- `GET /api/hr/summary` -- HR summary data. Returns an object with `headcount`, `unpaid_claims_total`, and related fields. May support query parameters for region and period filtering.
- `GET /api/events/performance` -- event performance data. Returns an object with `orders` and `revenue` fields. May support query parameters for event name and period.

## CSV export endpoints

- `GET /exports/churn/train.csv` -- churn model training dataset in CSV format. Contains features and a `churn` label column (0 or 1) plus a `prediction` column from the model.
- `GET /exports/churn/validation.csv` -- churn model validation dataset in CSV format. Same schema as train.csv.
- `GET /exports/churn/candidates.csv` -- candidate accounts for churn prediction. Contains `customer_id` and feature columns plus a `predicted_churn_probability` column.
- `GET /exports/account_metric_extract.csv` -- bulk extract of account metrics in CSV format.

## Health check

- `GET /api/health` -- service health check. Returns status information.
