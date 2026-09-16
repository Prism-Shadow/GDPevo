## Account Endpoints

Base: `<TASK_ENV_BASE_URL>` (the task prompt supplies the actual value)

### GET /api/accounts

List all 44 accounts.

```json
{
  "accounts": [
    {
      "account_id": "acct_northstar_finance",
      "account_aliases": ["Northstar Finance", "Northstar Finance Group", "NorthstarFinance Ops", "Northstar Finance Subsidiary"],
      "billing_arr_current": 1425000.0,
      "contract_tenure_months": 12,
      "crm_arr": 1268250.0,
      "csm_owner": "Owen Patel",
      "display_name": "Northstar Finance",
      "legal_name": "Northstar Finance Group Inc.",
      "lifecycle_status": "active",
      "product_plan": "Strategic",
      "region": "North America",
      "renewal_date": "2026-08-27",
      "segment": "Strategic"
    }
  ]
}
```

`lifecycle_status`: `active|renewal_risk|implementation|paused`
`segment`: `Strategic|Enterprise|Mid-Market|SMB`
`product_plan`: `Strategic|Enterprise|Scale|Growth|Launch`
`region`: `North America|EMEA|APAC|LATAM`

### GET /api/accounts/{account_id}

Single account object, same shape as list item above.

### GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM

Monthly metrics per account. Supports range queries.

```json
{
  "account_id": "acct_northstar_finance",
  "count": 3,
  "metrics": [
    {
      "account_id": "acct_northstar_finance",
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

`nps_score` may be `null` when `survey_status` is `"missing"`.
`survey_status`: `completed|missing`

### GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD

Support tickets for a date range.

```json
{
  "account_id": "acct_northstar_finance",
  "count": 15,
  "tickets": [
    {
      "account_id": "acct_northstar_finance",
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

`severity`: P1–P4. `status`: `closed|open|cancelled`.

### GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD

NPS survey responses for a date range.

```json
{
  "account_id": "acct_northstar_finance",
  "count": 2,
  "nps_responses": [
    {
      "account_id": "acct_northstar_finance",
      "response_date": "2026-04-21",
      "response_id": "NPS-7015",
      "retracted": false,
      "score": 17,
      "survey_channel": "email"
    }
  ]
}
```

`survey_channel`: `email|csm_call|in_app|phone`.
Filter out `retracted: true` responses before computing latest NPS.

## Finance and Billing Endpoints

### GET /api/billing/snapshots

Quarterly billing snapshots for each account. 176 total across all accounts and quarters.

```json
{
  "count": 176,
  "snapshots": [
    {
      "account_id": "acct_globex_north",
      "as_of": "2026-06-30",
      "billing_arr": 1176600.7,
      "legal_name": "Globex North Holdings LLC",
      "mrr": 98050.06,
      "posted": true,
      "snapshot_id": "BILL-acct_globex_north-2026-Q2",
      "source": "billing_snapshot"
    }
  ]
}
```

`billing_arr` is the authoritative ARR for the as-of date. Filter by account_id and as_of date to get the correct period snapshot.

### GET /api/finance/ar-aging

A/R aging records for all customers (196 records across quarters). Some customers are CRM accounts, some are not ("unlinked" entries).

```json
{
  "ar_aging": [
    {
      "1_30": 3416.05,
      "31_60": 1476.95,
      "61_90": 0.0,
      "90_plus": 0.0,
      "aging_id": "AR-acct_northstar_finance-2026-Q1",
      "as_of": "2026-03-31",
      "current": 31837.31,
      "customer_name": "Northstar Finance Group Inc.",
      "quarter": "2026-Q1",
      "region": "North America"
    }
  ]
}
```

`overdue_balance` for a single record = `31_60` + `61_90` + `90_plus`.
Filter by `as_of` date and optionally by `region` to isolate the target period.

## Pipeline and Opportunities

### GET /api/opportunities

114 opportunities across all accounts.

```json
{
  "count": 114,
  "opportunities": [
    {
      "account_id": "acct_globex_north",
      "account_legal_name": "Globex North Holdings LLC",
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

`stage`: `Prospecting|Discovery|Proposal|Negotiation|Closed Won|Closed Lost`
`state`: `open|closed`
`product_line`: `Core Retention|Workflow Plus|AI Assist|Data Cloud`

## HR and Events

### GET /api/hr/summary

16 records, one per region per quarter.

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

Sum `headcount` and `unpaid_claims_amount` across all matching regions for the target quarter.

### GET /api/events/performance

20 records, 5 events per quarter.

```json
{
  "count": 20,
  "event_performance": [
    {
      "cancelled_orders": 8,
      "completed_orders": 120,
      "event_id": "retention_summit",
      "event_orders": 134,
      "event_revenue": 108256.2,
      "pending_orders": 5,
      "product_revenue": 28116.07,
      "quarter": "2026-Q1",
      "refunded_orders": 1
    }
  ]
}
```

## Churn Exports (CSV)

### GET /exports/churn/train.csv

180 rows, 21 columns: `customer_id`, `tenure`, `MonthlyCharges`, `TotalCharges`, `Contract`, `PaymentMethod`, `PaperlessBilling`, `Partner`, `Dependents`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`, `SupportTickets90d`, `NPSLast`, `UsageTrendPct`, `InvoicePastDue`, `ActiveSeatRatio`, `Churn`.

Last column is the target label (`Yes`/`No`). 28 churners, 152 non-churners.

### GET /exports/churn/validation.csv

60 rows, same schema. 4 churners, 56 non-churners.

### GET /exports/churn/candidates.csv

44 rows, 20 columns (no Churn label). Same prefix columns as train/validation. Used for churn prediction ranking.

## Consolidated Metric Extract

### GET /exports/account_metric_extract.csv

528 rows, one per account per month. Columns: `account_id`, `legal_name`, `segment`, `region`, `month`, `recognized_revenue`, `clean_ticket_count`, `sla_compliance`, `nps_score`, `product_usage`, `active_seats`.

`clean_ticket_count` is pre-computed (deduplicated), `nps_score` is empty when unavailable.
