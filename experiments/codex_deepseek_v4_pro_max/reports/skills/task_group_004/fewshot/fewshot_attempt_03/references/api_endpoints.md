## ApexCloud Retention Operations API Reference

Base URL: read from `environment_access.md` in the task workspace (key `GDPEVO_ENV_BASE_URL`). The file declares allowed endpoints and any required headers.

### Account Profile & Hierarchy
- `GET /api/accounts` — list all CRM accounts (includes account_id, name, segment, tenure, status)
- `GET /api/accounts/{account_id}` — single account detail (includes legal_name, segment, arr, renewal_date, status)

### Time-Series & Health
- `GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM` — monthly metrics (revenue, usage index)
- `GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` — support tickets (includes sla_compliance boolean)
- `GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` — NPS survey responses

### Billing & Receivables
- `GET /api/accounts/{account_id}/billing` — current billing snapshot (arr, renewal_date, status)
- `GET /api/accounts/{account_id}/ar-aging` — A/R aging for a single account
- `GET /api/billing/snapshots` — billing snapshots for all accounts
- `GET /api/finance/ar-aging` — consolidated A/R aging across all customers (includes customer_name, overdue amounts by bucket, and a boolean or field indicating CRM-link status)

### Pipeline & Opportunities
- `GET /api/opportunities` — CRM pipeline (includes account_id, product_line, stage, amount, close_date, status)

### Operations Context
- `GET /api/hr/summary` — headcount, unpaid claims (supports region and period filters)
- `GET /api/events/performance` — event orders and revenue (supports event name and period filters)

### Exports (CSV)
- `GET /exports/churn/train.csv` — churn training dataset (features + churn label)
- `GET /exports/churn/validation.csv` — churn validation dataset
- `GET /exports/churn/candidates.csv` — candidate accounts for churn prediction
- `GET /exports/account_metric_extract.csv` — bulk account metric extract

### Query Parameter Conventions
- Date range filters use `?start=YYYY-MM-DD&end=YYYY-MM-DD` for daily endpoints
- Month range filters use `?start=YYYY-MM&end=YYYY-MM` for monthly endpoints
- CSV exports are returned as text/csv; parse with csv-aware tooling

### Key Data Relationships
- AR aging `customer_name` maps to CRM account `legal_name` or `name` for linking
- A linked AR record has a non-null `account_id`; unlinked records have `null` account_id
- Opportunities reference `account_id` and have a `close_date` for period filtering
- Billing snapshot `arr` is the canonical current-ARR source when `uses_billing_arr_source` is relevant
- SLA compliance is computed as (tickets with sla_met=true) / (total tickets) × 100 for a given period
