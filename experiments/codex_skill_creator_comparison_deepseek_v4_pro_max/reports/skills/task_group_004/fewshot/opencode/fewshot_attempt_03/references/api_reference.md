# ApexCloud Retention Operations API Reference

Base URL: `<TASK_ENV_BASE_URL>` (typically `http://task-env:9004`). No authentication. All endpoints are GET.

## /api/health

Returns service status and row counts across all datasets. Use for orientation.

```json
{
  "status": "ok",
  "service": "ApexCloud Retention Operations",
  "seed": 4004,
  "row_counts": { ... }
}
```

## /api/accounts

Full account list. Each account has:

| Field | Type | Description |
|---|---|---|
| account_id | string | Primary key, e.g. `acct_northstar_finance` |
| display_name | string | Short name |
| legal_name | string | Full legal entity name |
| account_aliases | string[] | Alternate names (used for A/R matching) |
| billing_arr_current | float | Live billing-system ARR |
| crm_arr | float | CRM-reported ARR |
| contract_tenure_months | int | Months since contract start |
| renewal_date | string | Next renewal date (YYYY-MM-DD) |
| lifecycle_status | string | `active`, `churned`, etc. |
| product_plan | string | `Strategic`, `Enterprise`, `Scale`, `Essentials`, `Growth` |
| region | string | `North America`, `EMEA`, `APAC`, `LATAM` |
| segment | string | `Strategic`, `Enterprise`, `Mid-Market` (used for segment_summary) |
| csm_owner | string | CSM name |

## /api/accounts/{account_id}

Single account. Same shape as list entry.

## /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM

Monthly metrics per account. Each metric row:

| Field | Type | Description |
|---|---|---|
| month | string | `YYYY-MM` |
| recognized_revenue | float | Monthly recognized revenue |
| support_ticket_count | int | Total tickets in month |
| sla_compliance | float | SLA compliance percentage (already percent, e.g. 85.9 means 85.9%) |
| nps_score | int or null | NPS score for the month; null when survey_status is "missing" |
| product_usage | float | Usage metric (arbitrary scale, compare across months for trend) |
| active_seats | int | Licensed seats in use |
| survey_status | string | `completed` or `missing` |
| quarter | string | `YYYY-QN` |

## /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD

Support tickets. Each ticket:

| Field | Type | Description |
|---|---|---|
| ticket_id | string | e.g. `TCK-10055` |
| created_date | string | `YYYY-MM-DD` |
| status | string | `closed`, `open`, etc. |
| severity | string | `P1` through `P4` |
| product_area | string | e.g. `billing`, `integrations`, `workflow`, `mobile` |
| is_duplicate | bool | Exclude from clean count |
| is_spam | bool | Exclude from clean count |
| first_response_sla_met | bool | First-response SLA met |
| resolution_sla_met | bool | Resolution SLA met |

**Clean ticket count**: count tickets where `is_duplicate == false AND is_spam == false`.

## /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD

NPS survey responses:

| Field | Type | Description |
|---|---|---|
| response_id | string | e.g. `NPS-7015` |
| response_date | string | `YYYY-MM-DD` |
| score | int | NPS score 0-100 |
| retracted | bool | True if respondent withdrew |
| survey_channel | string | `email`, `csm_call` |

Use the most recent non-null score. Ignore retracted responses.

## /api/billing/snapshots

Quarterly billing ARR snapshots for all accounts:

| Field | Type | Description |
|---|---|---|
| snapshot_id | string | e.g. `BILL-acct_northstar_finance-2026-Q2` |
| account_id | string | Links to accounts |
| legal_name | string | Account legal name |
| as_of | string | Quarter-end date `YYYY-MM-DD` |
| billing_arr | float | ARR at snapshot date |
| mrr | float | Monthly recurring revenue |
| posted | bool | Whether snapshot is finalized |
| source | string | Always `billing_snapshot` |

**Quarter derivation**: `2026-03-31` -> `2026-Q1`, `2026-06-30` -> `2026-Q2`, `2026-09-30` -> `2026-Q3`, `2026-12-31` -> `2026-Q4`.

## /api/finance/ar-aging

Accounts receivable aging by customer:

| Field | Type | Description |
|---|---|---|
| aging_id | string | e.g. `AR-acct_globex_north-2026-Q2` |
| customer_name | string | Legal entity name (match against account legal_name/aliases) |
| as_of | string | `YYYY-MM-DD` |
| quarter | string | `YYYY-QN` |
| region | string | Region of the customer |
| current | float | Not yet due |
| 1_30 | float | 1-30 days past due |
| 31_60 | float | 31-60 days past due |
| 61_90 | float | 61-90 days past due |
| 90_plus | float | 90+ days past due |

**Overdue balance**: `31_60 + 61_90 + 90_plus`. The `1_30` bucket is current/grace period, not overdue.

## /api/opportunities

CRM pipeline opportunities:

| Field | Type | Description |
|---|---|---|
| opportunity_id | string | e.g. `OPP-501` |
| account_id | string | Links to accounts |
| account_legal_name | string | Legal name |
| amount | float | Deal amount |
| stage | string | `Prospecting`, `Discovery`, `Proposal`, `Negotiation`, `Closed Won`, `Closed Lost` |
| state | string | `open`, `won`, `lost` |
| close_date | string | `YYYY-MM-DD` |
| created_date | string | `YYYY-MM-DD` |
| product_line | string | e.g. `AI Assist`, `Data Cloud`, `Workflow Plus`, `Core Retention` |
| region | string | Region |

**Open pipeline**: filter by `state == "open"`. **Won**: `state == "won"`. **Lost**: `state == "lost"`.

## /api/hr/summary

HR operational data by region and quarter:

| Field | Type | Description |
|---|---|---|
| quarter | string | `YYYY-QN` |
| region | string | Region |
| headcount | int | Employee headcount |
| attendance_rate | float | Attendance percentage |
| high_absence_employees | int | Employees with excessive absence |
| leave_liability_hours | float | Accrued leave hours |
| open_advances_amount | float | Outstanding salary advances |
| open_advances_count | int | Number of advance cases |
| unpaid_claims_amount | float | Unpaid expense claims |
| unpaid_claims_count | int | Number of unpaid claims |

## /api/events/performance

Event performance metrics by event and quarter:

| Field | Type | Description |
|---|---|---|
| event_id | string | e.g. `apex_connect`, `retention_summit`, `renewal_lab`, `field_roundtable` |
| quarter | string | `YYYY-QN` |
| event_orders | int | Total orders |
| event_revenue | float | Total event revenue |
| completed_orders | int | Fully delivered |
| cancelled_orders | int | Cancelled |
| pending_orders | int | Still pending |
| refunded_orders | int | Refunded |
| product_revenue | float | Revenue from products sold at event |

## /exports/churn/train.csv

Churn model training data (180 rows). CSV with headers. Key columns: `customer_id`, `tenure`, `MonthlyCharges`, `TotalCharges`, `Contract`, `Churn` (label: Yes/No), plus feature columns.

## /exports/churn/validation.csv

Churn model validation data (60 rows). Same schema as train.csv.

## /exports/churn/candidates.csv

Churn candidate predictions (44 rows). Includes `customer_id` and churn probability columns. The probability column is named predictably (likely `predicted_churn_probability` or derived from model output).

## /exports/account_metric_extract.csv

Flat CSV extract of monthly account metrics (528 rows). Columns: `account_id`, `legal_name`, `segment`, `region`, `month`, `recognized_revenue`, `clean_ticket_count`, `sla_compliance`, `nps_score`, `product_usage`, `active_seats`.
