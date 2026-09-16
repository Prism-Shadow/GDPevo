# ApexCloud Retention Operations API Reference

Base URL: `<TASK_ENV_BASE_URL>` or `http://task-env:9004/`
Auth: none (read-only, no credentials)

## Endpoint Catalogue

### GET /api/health

Returns service status, row counts, and seed.

```json
{
  "row_counts": { "...": 0 },
  "seed": 4004,
  "service": "ApexCloud Retention Operations",
  "status": "ok"
}
```

### GET /api/accounts

Returns all accounts. Response: `{ "accounts": [...] }`

**Account object fields:**

| Field | Type | Description |
|-------|------|-------------|
| account_id | string | Unique identifier (e.g. `acct_northstar_finance`) |
| account_aliases | string[] | Alternative names for matching |
| billing_arr_current | float | Current billing ARR |
| contract_tenure_months | int | Months since contract start |
| crm_arr | float | CRM-reported ARR |
| csm_owner | string | Customer success manager |
| display_name | string | Short display name |
| legal_name | string | Full legal entity name |
| lifecycle_status | string | `active`, `churned`, etc. |
| product_plan | string | `Strategic`, `Enterprise`, `Scale`, `Growth`, `Starter` |
| region | string | `North America`, `EMEA`, `APAC` |
| renewal_date | string | YYYY-MM-DD contract renewal date |
| segment | string | `Strategic`, `Enterprise`, `Mid-Market` |

### GET /api/accounts/{account_id}

Same shape as a single entry from `/api/accounts` but returned directly (not wrapped in `accounts` array). Fields identical.

### GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM

Returns monthly metrics for the given account and month range.

**Response shape:**

```json
{
  "account_id": "acct_...",
  "count": 3,
  "metrics": [
    {
      "account_id": "...",
      "active_seats": 95,
      "month": "2026-04",
      "nps_score": 17,
      "product_usage": 53.87,
      "quarter": "2026-Q2",
      "recognized_revenue": 118387.61,
      "sla_compliance": 85.9,
      "support_ticket_count": 5,
      "survey_status": "completed"
    }
  ]
}
```

**Fields note:** `nps_score` is the NPS captured in the metrics pipeline; it may differ from raw NPS responses. `survey_status` is `"completed"` or `"missing"`. `support_ticket_count` is the raw ticket count for that month. `recognized_revenue` is the CRM-recognized revenue (source: crm_closed_won).

Metrics are always returned sorted by month ascending.

### GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD

Returns support tickets for the date range.

**Response shape:**

```json
{
  "account_id": "acct_...",
  "count": 15,
  "tickets": [
    {
      "account_id": "...",
      "created_date": "2026-04-17",
      "first_response_sla_met": false,
      "is_duplicate": false,
      "is_spam": false,
      "product_area": "integrations",
      "resolution_sla_met": true,
      "severity": "P3",
      "status": "closed",
      "ticket_id": "TCK-10055"
    }
  ]
}
```

**Statuses:** `closed`, `cancelled`, `open`. **Severities:** `P2`, `P3`, `P4`.

### GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD

Returns NPS survey responses.

```json
{
  "account_id": "acct_...",
  "count": 2,
  "nps_responses": [
    {
      "account_id": "...",
      "response_date": "2026-04-21",
      "response_id": "NPS-7015",
      "retracted": false,
      "score": 17,
      "survey_channel": "email"
    }
  ]
}
```

**Fields:** `retracted` indicates a withdrawn response (exclude from analysis). `survey_channel` is `email`, `csm_call`, or `in_app`.

### GET /api/billing/snapshots

Returns all quarterly billing snapshots.

```json
{
  "count": 176,
  "snapshots": [
    {
      "account_id": "acct_...",
      "as_of": "2026-06-30",
      "billing_arr": 1416439.47,
      "legal_name": "Northstar Finance Group Inc.",
      "mrr": 118036.62,
      "posted": true,
      "snapshot_id": "BILL-acct_northstar_finance-2026-Q2",
      "source": "billing_snapshot"
    }
  ]
}
```

Filter by `account_id` and `as_of` to get the closest quarterly ARR. `posted: true` indicates the snapshot was finalized.

### GET /api/finance/ar-aging

Returns all A/R aging records across quarters and regions.

```json
{
  "ar_aging": [
    {
      "1_30": 8748.27,
      "31_60": 470.21,
      "61_90": 0.0,
      "90_plus": 0.0,
      "aging_id": "AR-acct_globex_north-2026-Q1",
      "as_of": "2026-03-31",
      "current": 25208.85,
      "customer_name": "Globex North Holdings LLC",
      "quarter": "2026-Q1",
      "region": "North America"
    }
  ]
}
```

Filter by `quarter` and `as_of` to get records for a specific reporting period. The `customer_name` field is used for account matching.

### GET /api/opportunities

Returns all CRM opportunities.

```json
{
  "count": 114,
  "opportunities": [
    {
      "account_id": "acct_...",
      "account_legal_name": "...",
      "amount": 144517.62,
      "close_date": "2026-12-15",
      "created_date": "2026-11-09",
      "opportunity_id": "OPP-501",
      "product_line": "Workflow Plus",
      "region": "North America",
      "stage": "Proposal",
      "state": "open"
    }
  ]
}
```

**State values:** `open`, `closed_won`, `closed_lost`. **Stage values:** `Prospecting`, `Discovery`, `Proposal`, `Negotiation`, `Closed Won`, `Closed Lost`. Filter by account_id, close_date range, and state.

### GET /api/hr/summary

Returns HR summaries by quarter and region.

```json
{
  "count": 16,
  "hr_summary": [
    {
      "attendance_rate": 98.16,
      "headcount": 61,
      "high_absence_employees": 4,
      "leave_liability_hours": 530.0,
      "open_advances_amount": 22035.75,
      "open_advances_count": 4,
      "quarter": "2026-Q1",
      "region": "North America",
      "unpaid_claims_amount": 35523.06,
      "unpaid_claims_count": 16
    }
  ]
}
```

Filter by `quarter` and optionally `region`. For all-regions summaries, sum across regions.

### GET /api/events/performance

Returns event performance by event and quarter.

```json
{
  "count": 20,
  "event_performance": [
    {
      "cancelled_orders": 32,
      "completed_orders": 450,
      "event_id": "apex_connect",
      "event_orders": 521,
      "event_revenue": 367775.66,
      "pending_orders": 31,
      "product_revenue": 145004.64,
      "quarter": "2026-Q1",
      "refunded_orders": 8
    }
  ]
}
```

Filter by `event_id` and `quarter`.

### GET /exports/churn/train.csv

Returns the churn training dataset as CSV with columns:
`customer_id,tenure,MonthlyCharges,TotalCharges,Contract,PaymentMethod,PaperlessBilling,Partner,Dependents,OnlineSecurity,OnlineBackup,DeviceProtection,TechSupport,StreamingTV,StreamingMovies,SupportTickets90d,NPSLast,UsageTrendPct,InvoicePastDue,ActiveSeatRatio,Churn`

### GET /exports/churn/validation.csv

Same schema as train.csv. Used to compute accuracy by comparing predicted vs actual Churn labels.

### GET /exports/churn/candidates.csv

Same feature columns as train/validation but without the Churn label. Used for prediction ranking. The `customer_id` column contains account_ids like `acct_northstar_finance`.

### GET /exports/account_metric_extract.csv

Returns a denormalized CSV with monthly metrics for all accounts:
`account_id,legal_name,segment,region,month,recognized_revenue,clean_ticket_count,sla_compliance,nps_score,product_usage,active_seats`
The `clean_ticket_count` in this extract is already deduplicated and spam-filtered. The `recognized_revenue` matches CRM recognized revenue.

## Filtering Conventions

- For month ranges on metrics: use `start=2026-04&end=2026-06` (inclusive)
- For date ranges on tickets/NPS: use `start=2026-04-01&end=2026-06-30` (inclusive)
- For quarterly data (billing, AR, opportunities, HR, events): filter by the `quarter` field (e.g. `2026-Q2`) or by `as_of` dates
- The `/api/accounts` and list endpoints return all records; filter client-side
- The account-scoped endpoints (metrics, tickets, NPS) already filter by account
