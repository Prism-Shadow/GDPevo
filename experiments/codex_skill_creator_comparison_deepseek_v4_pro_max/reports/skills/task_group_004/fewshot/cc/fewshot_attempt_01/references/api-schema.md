## API Endpoints

Base URL: provided in the task prompt (e.g. `<TASK_ENV_BASE_URL>`).

### GET /api/health

Returns service status and row counts for all datasets.

```json
{
  "service": "ApexCloud Retention Operations",
  "status": "ok",
  "seed": 4004,
  "row_counts": {
    "accounts.json": 44,
    "account_metrics.json": 528,
    "support_tickets.json": 1595,
    "nps_responses.json": 451,
    "billing_snapshots.json": 176,
    "ar_aging.json": 196,
    "opportunities.json": 114,
    "hr_summary.json": 16,
    "event_performance.json": 20,
    "churn_train.csv": 180,
    "churn_validation.csv": 60,
    "churn_candidates.csv": 44,
    "account_metric_extract.csv": 528
  }
}
```

### GET /api/accounts

Returns all 44 accounts. Each account object:

| Field | Type | Description |
|-------|------|-------------|
| account_id | string | e.g. `acct_northstar_finance` |
| legal_name | string | Full legal entity name |
| display_name | string | Short display name |
| account_aliases | string[] | All known name variants |
| region | string | North America, EMEA, APAC, LATAM |
| segment | string | Strategic, Enterprise, Mid-Market |
| lifecycle_status | string | active, implementation, at-risk, churned |
| product_plan | string | Strategic, Enterprise, Scale, Core |
| crm_arr | number | CRM-sourced ARR |
| billing_arr_current | number | Current billing-system ARR |
| contract_tenure_months | integer | Months since contract start |
| renewal_date | string | YYYY-MM-DD |
| csm_owner | string | CSM full name |

### GET /api/accounts/{account_id}

Same shape as a single element from /api/accounts. Includes the full account
profile for one account.

### GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM

Returns monthly metrics for one account within the range.

| Field | Type | Description |
|-------|------|-------------|
| month | string | YYYY-MM |
| quarter | string | YYYY-QN |
| recognized_revenue | number | Monthly recognized revenue |
| support_ticket_count | integer | Raw ticket count (includes dupes/spam) |
| sla_compliance | number | Percentage 0-100 |
| nps_score | integer or null | Survey score when present; null when `survey_status` is "missing" |
| product_usage | number | Usage metric |
| active_seats | integer | Seat count |
| survey_status | string | "completed" or "missing" |

### GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD

Returns support tickets for one account. Each ticket:

| Field | Type | Description |
|-------|------|-------------|
| ticket_id | string | e.g. `TCK-10055` |
| created_date | string | YYYY-MM-DD |
| status | string | closed, open, etc. |
| severity | string | P1-P4 |
| product_area | string | integrations, billing, workflow, mobile, etc. |
| first_response_sla_met | boolean | |
| resolution_sla_met | boolean | |
| is_duplicate | boolean | Exclude when true |
| is_spam | boolean | Exclude when true |

### GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD

NPS responses for one account. Each response:

| Field | Type | Description |
|-------|------|-------------|
| response_id | string | e.g. `NPS-7015` |
| response_date | string | YYYY-MM-DD |
| score | integer | 0-100 |
| survey_channel | string | email, csm_call |
| retracted | boolean | Exclude when true |

### GET /api/billing/snapshots

Returns all 176 quarterly billing snapshots. Filter by `account_id` and `as_of`.
Each snapshot:

| Field | Type | Description |
|-------|------|-------------|
| snapshot_id | string | e.g. `BILL-acct_globex_north-2026-Q2` |
| account_id | string | |
| legal_name | string | |
| as_of | string | YYYY-MM-DD (quarter end) |
| billing_arr | number | ARR at snapshot date |
| mrr | number | MRR at snapshot date |
| posted | boolean | |
| source | string | "billing_snapshot" |

### GET /api/finance/ar-aging

Returns all 196 A/R aging records. Each record:

| Field | Type | Description |
|-------|------|-------------|
| aging_id | string | e.g. `AR-acct_globex_north-2026-Q2` |
| customer_name | string | Legal entity name — not an account_id |
| as_of | string | YYYY-MM-DD (quarter end) |
| quarter | string | YYYY-QN |
| region | string | |
| current | number | Not yet due |
| 1_30 | number | 1-30 days overdue |
| 31_60 | number | 31-60 days overdue |
| 61_90 | number | 61-90 days overdue |
| 90_plus | number | 90+ days overdue |

To cross-reference with accounts, match `customer_name` against `legal_name` or
`account_aliases` from the accounts endpoint. Overdue balance = `1_30 + 31_60 +
61_90 + 90_plus`.

### GET /api/opportunities

Returns all 114 opportunities. Each opportunity:

| Field | Type | Description |
|-------|------|-------------|
| opportunity_id | string | e.g. `OPP-501` |
| account_id | string | |
| account_legal_name | string | |
| amount | number | Deal amount |
| product_line | string | AI Assist, Data Cloud, Workflow Plus, Core Retention |
| stage | string | Prospecting, Discovery, Proposal, etc. |
| state | string | "open", "closed_won", "closed_lost" |
| close_date | string | YYYY-MM-DD |
| created_date | string | YYYY-MM-DD |
| region | string | |

### GET /api/hr/summary

Returns 16 quarterly HR records by region. Each record:

| Field | Type | Description |
|-------|------|-------------|
| quarter | string | YYYY-QN |
| region | string | |
| headcount | integer | |
| attendance_rate | number | Percentage |
| unpaid_claims_amount | number | |
| unpaid_claims_count | integer | |
| open_advances_amount | number | |
| open_advances_count | integer | |
| high_absence_employees | integer | |
| leave_liability_hours | number | |

### GET /api/events/performance

Returns 20 quarterly event performance records. Each record:

| Field | Type | Description |
|-------|------|-------------|
| event_id | string | apex_connect, retention_summit, etc. |
| quarter | string | YYYY-QN |
| event_orders | integer | Total orders |
| event_revenue | number | Total revenue |
| completed_orders | integer | |
| cancelled_orders | integer | |
| pending_orders | integer | |
| refunded_orders | integer | |
| product_revenue | number | |

### GET /exports/churn/train.csv

180-row CSV with `customer_id` (not account_id), 19 feature columns, and a
`Churn` label column (Yes/No). Features: `tenure`, `MonthlyCharges`,
`TotalCharges`, `Contract`, `PaymentMethod`, `PaperlessBilling`, `Partner`,
`Dependents`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`,
`TechSupport`, `StreamingTV`, `StreamingMovies`, `SupportTickets90d`,
`NPSLast`, `UsageTrendPct`, `InvoicePastDue` (Yes/No), `ActiveSeatRatio`.

### GET /exports/churn/validation.csv

Same schema as train.csv; 60 rows with `Churn` labels.

### GET /exports/churn/candidates.csv

Same schema as train.csv but WITHOUT the `Churn` column. 44 rows with
`customer_id` values that may be `acct_*` identifiers or other formats.

### GET /exports/account_metric_extract.csv

528-row CSV with account-level monthly metrics:
`account_id`, `legal_name`, `segment`, `region`, `month`,
`recognized_revenue`, `clean_ticket_count`, `sla_compliance`, `nps_score`,
`product_usage`, `active_seats`.

`clean_ticket_count` is pre-deduplicated (no spam/dupes).
