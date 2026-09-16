# ApexCloud Retention Operations API Reference

Base URL: `<TASK_ENV_BASE_URL>` (provided in the task prompt)

All endpoints return JSON. No authentication required.

## Endpoints

### GET /api/health
Service status and row counts for all datasets.

Response fields: `status`, `service`, `seed`, `row_counts` (object with per-dataset counts).

### GET /api/accounts
List all CRM accounts (44 total).

Response: `accounts` array. Each account object:

| Field | Type | Description |
|---|---|---|
| account_id | string | Unique account identifier (e.g. `acct_northstar_finance`) |
| account_aliases | string[] | Alternative names used in AR aging, billing |
| display_name | string | Short display name |
| legal_name | string | Full legal entity name |
| billing_arr_current | number | Current ARR from billing system |
| crm_arr | number | ARR from CRM |
| contract_tenure_months | integer | Months since contract start |
| csm_owner | string | CSM name |
| lifecycle_status | string | `active` or `churned` |
| product_plan | string | `Strategic`, `Enterprise`, `Scale`, or `SMB` |
| region | string | `North America`, `EMEA`, `APAC`, `LATAM` |
| renewal_date | string | `YYYY-MM-DD` |
| segment | string | `Strategic`, `Enterprise`, `Mid-Market`, `SMB` |

### GET /api/accounts/{account_id}
Single account profile. Same shape as one element in the accounts list.

### GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM
Monthly operational metrics for the account within the period (inclusive).

Response: `account_id`, `count`, `metrics` array. Each metric:

| Field | Type | Description |
|---|---|---|
| month | string | `YYYY-MM` |
| quarter | string | `YYYY-QN` |
| recognized_revenue | number | CRM recognized revenue for the month |
| active_seats | integer | Active user seats |
| product_usage | number | Usage score (0-100) |
| nps_score | integer or null | NPS if survey completed, null if missing |
| support_ticket_count | integer | Raw ticket count (includes spam/cancelled) |
| sla_compliance | number | SLA compliance percentage (0-100) |
| survey_status | string | `completed` or `missing` |

### GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD
Support tickets for the account in the date range.

Response: `account_id`, `count`, `tickets` array. Each ticket:

| Field | Type | Description |
|---|---|---|
| ticket_id | string | e.g. `TCK-10055` |
| created_date | string | `YYYY-MM-DD` |
| status | string | `closed`, `cancelled`, `open` |
| severity | string | `P2`, `P3`, `P4` |
| product_area | string | e.g. `integrations`, `billing`, `workflow` |
| first_response_sla_met | boolean | First-response SLA met |
| resolution_sla_met | boolean | Resolution SLA met |
| is_spam | boolean | Marked as spam |
| is_duplicate | boolean | Marked as duplicate |

**Clean ticket count**: Exclude tickets where `is_spam == true` OR `status == "cancelled"`.

### GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD
NPS survey responses in the date range.

Response: `account_id`, `count`, `nps_responses` array. Each response:

| Field | Type | Description |
|---|---|---|
| response_id | string | e.g. `NPS-7015` |
| response_date | string | `YYYY-MM-DD` |
| score | integer | NPS score (0-100) |
| survey_channel | string | `email` or `csm_call` |
| retracted | boolean | Whether response was retracted |

**Latest NPS**: The most recent non-retracted response by response_date. If no completed surveys, use null or 0 depending on task instructions.

### GET /api/accounts/{account_id}/billing
**Not available.** Use `/api/billing/snapshots` instead and filter by account_id.

### GET /api/accounts/{account_id}/ar-aging
**Not available.** Use `/api/finance/ar-aging` instead and match by customer_name.

### GET /api/billing/snapshots
Quarterly billing snapshots for all accounts (176 total, 4 quarters per account).

Response: `count`, `snapshots` array. Each snapshot:

| Field | Type | Description |
|---|---|---|
| snapshot_id | string | e.g. `BILL-acct_northstar_finance-2026-Q2` |
| account_id | string | Links to accounts |
| legal_name | string | Legal name for cross-referencing |
| as_of | string | `YYYY-MM-DD` (quarter-end date) |
| billing_arr | number | Billed ARR at quarter-end |
| mrr | number | Monthly recurring revenue |
| posted | boolean | Whether snapshot is posted |
| source | string | Always `billing_snapshot` |

**Current ARR for Q2 2026**: Use snapshot where `as_of == "2026-06-30"` and account_id matches. `billing_arr` is the current_arr value.

### GET /api/finance/ar-aging
A/R aging records for all customers across quarters (196 total).

Response: `ar_aging` array. Each record:

| Field | Type | Description |
|---|---|---|
| aging_id | string | e.g. `AR-acct_globex_north-2026-Q2` |
| customer_name | string | Legal entity name (matches account legal_name or aliases) |
| as_of | string | `YYYY-MM-DD` |
| quarter | string | `YYYY-QN` |
| region | string | Region |
| current | number | Current (not past due) |
| 1_30 | number | 1-30 days past due |
| 31_60 | number | 31-60 days past due |
| 61_90 | number | 61-90 days past due |
| 90_plus | number | 90+ days past due |

**Overdue balance**: `61_90 + 90_plus`. Use the record matching the as-of date.

**Linking to accounts**: Match `customer_name` against account `legal_name` and `account_aliases`. Records that do not match any CRM account are "unlinked."

### GET /api/opportunities
CRM opportunity pipeline (114 total).

Response: `count`, `opportunities` array. Each opportunity:

| Field | Type | Description |
|---|---|---|
| opportunity_id | string | e.g. `OPP-501` |
| account_id | string | Links to accounts |
| account_legal_name | string | For cross-referencing |
| amount | number | Deal amount |
| close_date | string | `YYYY-MM-DD` |
| created_date | string | `YYYY-MM-DD` |
| stage | string | Sales stage |
| state | string | `open`, `won`, `lost` |
| product_line | string | Product line name |
| region | string | Region |

**Pipeline filtering**: Filter by close_date within the analysis period. Separate by state for won/lost/open counts.

**Expansion pipeline for an account**: Open opportunities where close_date falls within the period and state is `open`.

### GET /api/hr/summary
HR operational summary by region and quarter (16 records, 4 regions x 4 quarters).

Response: `count`, `hr_summary` array. Each record:

| Field | Type | Description |
|---|---|---|
| quarter | string | `YYYY-QN` |
| region | string | `North America`, `EMEA`, `APAC`, `LATAM` |
| headcount | integer | Total headcount |
| attendance_rate | number | Attendance percentage |
| high_absence_employees | integer | Employees with high absence |
| leave_liability_hours | number | Accrued leave hours |
| open_advances_amount | number | Outstanding salary advances |
| open_advances_count | integer | Number of advance cases |
| unpaid_claims_amount | number | Unpaid expense claims |
| unpaid_claims_count | integer | Number of unpaid claim cases |

**Aggregation**: Sum across all regions for the target quarter for headcount and unpaid_claims_total.

### GET /api/events/performance
Event performance by event_id and quarter (20 records, 5 events x 4 quarters).

Response: `count`, `event_performance` array. Each record:

| Field | Type | Description |
|---|---|---|
| event_id | string | e.g. `apex_connect`, `retention_summit` |
| quarter | string | `YYYY-QN` |
| event_orders | integer | Total orders |
| event_revenue | number | Total event revenue |
| completed_orders | integer | Completed orders |
| cancelled_orders | integer | Cancelled orders |
| pending_orders | integer | Pending orders |
| refunded_orders | integer | Refunded orders |
| product_revenue | number | Product-specific revenue |

**Filtering**: Match by event_id and quarter.

## CSV Exports

### GET /exports/churn/train.csv
Training dataset (180 rows + header). Columns: `customer_id,tenure,MonthlyCharges,TotalCharges,Contract,PaymentMethod,PaperlessBilling,Partner,Dependents,OnlineSecurity,OnlineBackup,DeviceProtection,TechSupport,StreamingTV,StreamingMovies,SupportTickets90d,NPSLast,UsageTrendPct,InvoicePastDue,ActiveSeatRatio,Churn`

### GET /exports/churn/validation.csv
Validation dataset (60 rows + header). Same columns plus `Churn` (ground truth).

### GET /exports/churn/candidates.csv
Candidate accounts for prediction (44 rows + header). Same columns as train but without `Churn` column. `customer_id` values are account_ids.

### GET /exports/account_metric_extract.csv
Full account metrics extract (528 rows). Available for cross-reference.
