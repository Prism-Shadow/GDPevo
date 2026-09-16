# ApexCloud Retention Operations API Reference

Base URL: `<TASK_ENV_BASE_URL>` (provided in the task prompt)

No authentication required. All endpoints are public GET.

All endpoints return JSON unless noted.

## Health

```
GET /api/health
```

Returns service status. Use to verify connectivity before starting work.

## Account Repository

### List all accounts

```
GET /api/accounts
```

Returns `{"accounts": [...], "count": N}`. Each account object:

| Field | Type | Description |
|-------|------|-------------|
| account_id | string | Primary key, e.g. `acct_northstar_finance` |
| account_aliases | string[] | Alternative names for the account |
| billing_arr_current | number | Forward-looking billing ARR estimate (not authoritative for current ARR) |
| contract_tenure_months | integer | Months since contract start |
| crm_arr | number | CRM-reported ARR (sales pipeline figure) |
| csm_owner | string | Customer success manager name |
| display_name | string | Short display name |
| legal_name | string | Legal entity name |
| lifecycle_status | string | `active`, `implementation`, `renewal_risk`, `paused` |
| product_plan | string | `Launch`, `Growth`, `Scale`, `Enterprise`, `Strategic` |
| region | string | `North America`, `EMEA`, `APAC`, `LATAM` |
| renewal_date | string | YYYY-MM-DD |
| segment | string | `SMB`, `Mid-Market`, `Enterprise`, `Strategic` |

### Get single account

```
GET /api/accounts/{account_id}
```

Returns the account object directly (not wrapped in an array).

## Metrics

```
GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM
```

Returns `{"account_id": "...", "count": N, "metrics": [...]}`. Each entry:

| Field | Type | Description |
|-------|------|-------------|
| month | string | YYYY-MM |
| quarter | string | YYYY-QN |
| active_seats | integer | Active user seats |
| nps_score | integer or null | NPS from the survey (may be null if survey missing) |
| product_usage | number | Usage percentage (0-100+) |
| recognized_revenue | number | Recognized monthly revenue |
| sla_compliance | number | SLA adherence percentage (0-100) |
| support_ticket_count | integer | Raw ticket count (includes spam/dupes/cancelled) |
| survey_status | string | `completed` or `missing` |

The `support_ticket_count` in metrics is a raw count. For clean counts, use
the tickets endpoint and apply hygiene rules.

### Bulk metric extract (CSV)

```
GET /exports/account_metric_extract.csv
```

Returns a CSV with columns: account_id, legal_name, segment, region, month,
recognized_revenue, clean_ticket_count, sla_compliance, nps_score,
product_usage, active_seats.

This CSV spans all accounts and all months. Useful for cross-account
comparisons or when the metrics endpoint responses are slow to fetch
individually.

## Support Tickets

```
GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD
```

Returns `{"account_id": "...", "count": N, "tickets": [...]}`. Each ticket:

| Field | Type | Description |
|-------|------|-------------|
| ticket_id | string | e.g. `TCK-10055` |
| created_date | string | YYYY-MM-DD |
| severity | string | `P2`, `P3`, `P4` |
| product_area | string | e.g. `integrations`, `billing`, `workflow`, `mobile`, `analytics`, `identity` |
| status | string | `closed`, `cancelled` |
| is_spam | boolean | Marked as spam |
| is_duplicate | boolean | Marked as duplicate |
| first_response_sla_met | boolean | First response within SLA |
| resolution_sla_met | boolean | Resolution within SLA |

## NPS (Net Promoter Score)

```
GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD
```

Returns `{"account_id": "...", "count": N, "nps_responses": [...]}`. Each:

| Field | Type | Description |
|-------|------|-------------|
| response_id | string | e.g. `NPS-7015` |
| response_date | string | YYYY-MM-DD |
| score | integer | 0-100 |
| survey_channel | string | `email`, `csm_call` |
| retracted | boolean | True if the response was retracted (exclude from analysis) |

**Important:** Use this endpoint (not the metrics endpoint) for NPS scoring
because it exposes retraction status. The metrics endpoint's `nps_score` is
the survey result but does not indicate whether it was retracted.

## Billing Snapshots

```
GET /api/billing/snapshots
```

Returns `{"count": 176, "snapshots": [...]}`. Each snapshot:

| Field | Type | Description |
|-------|------|-------------|
| snapshot_id | string | e.g. `BILL-acct_globex_north-2026-Q2` |
| account_id | string | |
| legal_name | string | |
| as_of | string | YYYY-MM-DD (quarter-end date) |
| billing_arr | number | **Authoritative current ARR** |
| mrr | number | Monthly recurring revenue |
| source | string | Always `billing_snapshot` |
| posted | boolean | Whether the snapshot is posted |

**This is the authoritative ARR source.** Always prefer `billing_arr` from
the most recent posted snapshot relative to the assessment date over the
account profile's `billing_arr_current` or `crm_arr`.

## A/R Aging

### Finance-wide

```
GET /api/finance/ar-aging
```

Returns `{"ar_aging": [...]}`. Each record:

| Field | Type | Description |
|-------|------|-------------|
| aging_id | string | e.g. `AR-acct_globex_north-2026-Q2` |
| customer_name | string | Legal name of the A/R customer |
| as_of | string | YYYY-MM-DD |
| quarter | string | YYYY-QN |
| region | string | |
| current | number | Not-yet-due balance |
| 1_30 | number | 1-30 days overdue |
| 31_60 | number | 31-60 days overdue |
| 61_90 | number | 61-90 days overdue |
| 90_plus | number | 90+ days overdue |

Overdue balance = `31_60 + 61_90 + 90_plus`. The `1_30` bucket is
current-period, not overdue. The `current` field is the not-yet-due balance.

### Per-account

```
GET /api/accounts/{account_id}/ar-aging
```

When the account is a CRM account, returns its A/R aging records. This
endpoint only works for accounts that have A/R records.

## Opportunities (CRM Pipeline)

```
GET /api/opportunities
```

Returns `{"count": 114, "opportunities": [...]}`. Each opportunity:

| Field | Type | Description |
|-------|------|-------------|
| opportunity_id | string | e.g. `OPP-501` |
| account_id | string | |
| account_legal_name | string | |
| amount | number | Deal amount |
| product_line | string | e.g. `Workflow Plus`, `Core Retention`, `AI Assist`, `Data Cloud` |
| stage | string | e.g. `Proposal`, `Discovery` |
| state | string | `open`, `closed_won`, `closed_lost` |
| created_date | string | YYYY-MM-DD |
| close_date | string | YYYY-MM-DD |
| region | string | |

For expansion pipeline: filter to `state = "open"` and sum `amount` per
account_id. For quarterly pipeline: filter by close_date within the quarter
range.

## HR Summary

```
GET /api/hr/summary
```

Returns `{"count": 16, "hr_summary": [...]}`. Each record per quarter per region:

| Field | Type | Description |
|-------|------|-------------|
| quarter | string | YYYY-QN |
| region | string | |
| headcount | integer | Employee count |
| attendance_rate | number | Percentage |
| high_absence_employees | integer | |
| leave_liability_hours | number | |
| open_advances_amount | number | |
| open_advances_count | integer | |
| unpaid_claims_amount | number | |
| unpaid_claims_count | integer | |

## Event Performance

```
GET /api/events/performance
```

Returns `{"count": 20, "event_performance": [...]}`. Each record per event
per quarter:

| Field | Type | Description |
|-------|------|-------------|
| event_id | string | `retention_summit`, `apex_connect`, `field_roundtable`, `renewal_lab`, `customer_ops_day` |
| quarter | string | YYYY-QN |
| event_orders | integer | Total orders placed |
| event_revenue | number | Total event revenue |
| completed_orders | integer | |
| cancelled_orders | integer | |
| pending_orders | integer | |
| refunded_orders | integer | |
| product_revenue | number | |

## Churn Exports

All three exports return CSV with the same column schema.

```
GET /exports/churn/train.csv
GET /exports/churn/validation.csv
GET /exports/churn/candidates.csv
```

Columns: customer_id, tenure, MonthlyCharges, TotalCharges, Contract,
PaymentMethod, PaperlessBilling, Partner, Dependents, OnlineSecurity,
OnlineBackup, DeviceProtection, TechSupport, StreamingTV, StreamingMovies,
SupportTickets90d, NPSLast, UsageTrendPct, InvoicePastDue, ActiveSeatRatio,
Churn.

- `train.csv` and `validation.csv` include the `Churn` column (Yes/No).
- `candidates.csv` does not include `Churn`; it is unlabeled.
- `InvoicePastDue` is Yes/No.
- `tenure` is in months.
- `SupportTickets90d`, `NPSLast` are integers.
- `UsageTrendPct` is a signed numeric percentage.
- `ActiveSeatRatio` is a float.

The `customer_id` in churn exports (e.g. `train_0001`) is a different
namespace from account IDs (e.g. `acct_northstar_finance`). When churn
candidates are filtered for specific account_ids, the candidates.csv uses
the account_id namespace.

## Fetching Strategy

When a task lists multiple accounts, fetch in parallel across all accounts
to minimize latency. Common fetch pattern for most task types:

1. Get all billing snapshots (single call).
2. Get all A/R aging (single call).
3. Get all opportunities (single call).
4. For each listed account in parallel: profile, metrics, tickets, NPS.
5. For finance/HR/events tasks: also fetch HR and events endpoints.

Always verify the response before processing. The API returns `{"error":
"not_found", "message": "..."}` for unknown endpoints.
