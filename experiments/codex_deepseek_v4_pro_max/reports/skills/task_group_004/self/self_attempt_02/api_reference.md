## Allowed GET Endpoints

Base URL: `$GDPEVO_ENV_BASE_URL`

### Accounts

- `GET /api/accounts` — List of all CRM accounts (account_id, name, segment, tenure_months, industry, region)
- `GET /api/accounts/{account_id}` — Single account profile
- `GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM` — Monthly revenue, sla_compliance_pct, usage_trend
- `GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` — Support tickets with SLA status
- `GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` — NPS survey scores by month
- `GET /api/accounts/{account_id}/billing` — Billing snapshot: current_arr, renewal_date, contract_end
- `GET /api/accounts/{account_id}/ar-aging` — A/R aging: current, 1-30, 31-60, 61-90, 90+ day buckets

### Finance and Pipeline

- `GET /api/billing/snapshots` — All accounts billing snapshots with current ARR
- `GET /api/finance/ar-aging` — All customers with overdue balances across aging buckets
- `GET /api/opportunities` — CRM pipeline: deal stage, amount, product_line, close_date

### Operations

- `GET /api/hr/summary` — Headcount and unpaid claims totals per region/quarter
- `GET /api/events/performance` — Event performance: orders, revenue by event and quarter

### Exports

- `GET /exports/churn/train.csv` — Churn model training dataset
- `GET /exports/churn/validation.csv` — Churn model validation dataset
- `GET /exports/churn/candidates.csv` — Candidate accounts with churn probability predictions
- `GET /exports/account_metric_extract.csv` — Bulk account metric extract

### Query Parameters

- `start` / `end`: scope metrics, tickets, and NPS to a date or month range
- Month-granularity: `start=YYYY-MM&end=YYYY-MM`
- Date-granularity: `start=YYYY-MM-DD&end=YYYY-MM-DD`
