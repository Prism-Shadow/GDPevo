# ApexCloud Retention Operations API

All endpoints are GET-only. The base URL is provided in the prompt as `TASK_ENV_BASE_URL`
(typically `http://task-env:9004/`). Append the path shown below.

---

## /api/health

Returns row counts for every dataset and the service status. Use for debugging
but not for filling template fields.

```json
{
  "row_counts": { "...": 528 },
  "seed": 4004,
  "service": "ApexCloud Retention Operations",
  "status": "ok"
}
```

---

## /api/accounts

Lists all accounts.

```
GET /api/accounts
```

Response shape:

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

Fields used in retention tasks:
- `account_id` — primary key used in all per-account endpoints
- `billing_arr_current` — current billing ARR (convenience field; prefer billing snapshots for quarter-close)
- `crm_arr` — CRM-reported ARR
- `contract_tenure_months` — used for tenure risk assessment
- `legal_name` — used for matching A/R customer names to accounts
- `account_aliases` — list of name variants; also used for A/R matching
- `renewal_date` — next renewal date; used for renewal-window risk flagging
- `region` — geographic region
- `segment` — Strategic, Enterprise, Mid-Market, or Scale
- `product_plan` — plan tier

---

## /api/accounts/{account_id}

Single-account profile. Same shape as an element in the `/api/accounts` list.

---

## /api/accounts/{account_id}/metrics

Monthly account metrics.

```
GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM
```

Response shape:

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

Key fields:
- `recognized_revenue` — monthly recognized revenue (use for QBR revenue columns)
- `sla_compliance` — percentage (0–100); use for SLA columns
- `nps_score` — aggregated NPS for the month; `null` when no survey completed
- `product_usage` — percentage (may exceed 100)
- `support_ticket_count` — raw count of tickets in the month
- `active_seats` — seat count
- `survey_status` — `"completed"` or `"missing"`

---

## /api/accounts/{account_id}/tickets

Support ticket history.

```
GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD
```

Response shape:

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

Key fields:
- `is_spam` — exclude these from clean ticket counts
- `is_duplicate` — exclude these from clean ticket counts
- `first_response_sla_met` / `resolution_sla_met` — SLA breach indicators
- `severity` — P1 through P4
- `product_area` — billing, integrations, mobile, workflow, etc.
- `status` — open, closed, pending

**Clean ticket count**: count of tickets where `is_spam` is `false` AND `is_duplicate` is `false`.

**SLA degradation signal**: when multiple tickets have `first_response_sla_met: false` or
`resolution_sla_met: false` within the period, flag `sla_degradation` as a reason code.

---

## /api/accounts/{account_id}/nps

Individual NPS survey responses.

```
GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD
```

Response shape:

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

For `latest_nps`: take the `score` from the most recent `response_date` where `retracted` is `false`.
If no unretracted responses exist, use the most recent `nps_score` from the metrics endpoint.

For `nps_drop` risk flagging: compare the latest score to the previous score (same source). A drop
of 20+ points or a score below 35 signals risk.

---

## /api/billing/snapshots

Quarterly billing ARR snapshots.

```
GET /api/billing/snapshots?start=YYYY-MM&end=YYYY-MM
```

Query parameters filter by `as_of` date range. The response includes all snapshots
in that range.

```json
{
  "count": 176,
  "snapshots": [
    {
      "account_id": "acct_northstar_finance",
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

Use `billing_arr` for `current_arr` when the task asks for ARR and includes
`model_checks.uses_billing_arr_source`. Match the snapshot whose `as_of` date
equals the assessment date.

---

## /api/finance/ar-aging

Accounts-receivable aging.

```
GET /api/finance/ar-aging?as_of=YYYY-MM-DD
```

```json
{
  "ar_aging": [
    {
      "1_30": 3657.55,
      "31_60": 5405.15,
      "61_90": 14558.44,
      "90_plus": 7065.02,
      "aging_id": "AR-acct_globex_north-2026-Q2",
      "as_of": "2026-06-30",
      "current": 33930.72,
      "customer_name": "Globex North Holdings LLC",
      "quarter": "2026-Q2",
      "region": "North America"
    }
  ]
}
```

**`overdue_balance`** = `61_90` + `90_plus`. These are the older aging buckets
that represent genuinely overdue receivables.

**Region filtering**: the A/R endpoint returns all regions. Filter to the
region(s) the prompt specifies.

**Account matching**: the A/R record has a `customer_name` (legal name), not
an `account_id`. Match to accounts by comparing `customer_name` against:
1. `legal_name` in the account profile (exact match)
2. `account_aliases` in the account profile (case-insensitive substring or exact match)

When a match is found the follow-up is `linked`; otherwise `unlinked` with
`account_id: null`.

---

## /api/opportunities

CRM pipeline opportunities.

```
GET /api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD
```

Filters by `close_date`. Returns opportunities whose close date falls in the
range.

```json
{
  "count": 32,
  "opportunities": [
    {
      "account_id": "acct_northstar_finance",
      "account_legal_name": "Northstar Finance Group Inc.",
      "amount": 501980.99,
      "close_date": "2026-05-25",
      "created_date": "2026-02-07",
      "opportunity_id": "OPP-503",
      "product_line": "AI Assist",
      "region": "North America",
      "stage": "Discovery",
      "state": "open"
    }
  ]
}
```

Key fields:
- `state`: `"open"` or `"closed"`
- `stage`: for closed opps — `"Closed Won"` or `"Closed Lost"`
- `amount`: deal amount in currency
- `product_line`: AI Assist, Core Retention, Data Cloud, etc.
- `close_date`: date the opportunity is expected to close or did close

**Pipeline summary**: sum `amount` for open opps (`open_pipeline`). Count
`Closed Won` and `Closed Lost` opps for win rate. `top_open_product_line` is the
product line with the highest total `amount` among open opps.

**Expansion pipeline per account**: sum `amount` for open opps belonging to
that `account_id` whose close dates fall within the analysis period.

---

## /api/hr/summary

HR operations data by quarter and region.

```
GET /api/hr/summary
```

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

For `hr_headcount`: sum `headcount` across all regions for the specified quarter.
For `unpaid_claims_total`: sum `unpaid_claims_amount` across all regions for the
specified quarter.

---

## /api/events/performance

Event performance data.

```
GET /api/events/performance?event=EVENT_ID&quarter=YYYY-QN
```

```json
{
  "count": 1,
  "event_performance": [
    {
      "cancelled_orders": 32,
      "completed_orders": 394,
      "event_id": "apex_connect",
      "event_orders": 445,
      "event_revenue": 309724.17,
      "pending_orders": 9,
      "product_revenue": 85017.07,
      "quarter": "2026-Q3",
      "refunded_orders": 10
    }
  ]
}
```

For `event_orders` and `event_revenue`: use the values from the matching event/quarter record.

---

## /exports/churn/train.csv, validation.csv, candidates.csv

CSV exports for churn model validation.

```
GET /exports/churn/train.csv
GET /exports/churn/validation.csv
GET /exports/churn/candidates.csv
```

Train and validation CSVs share this schema:

| Column | Description |
|---|---|
| `customer_id` | Row identifier (exclude from feature count) |
| `tenure` | Months with ApexCloud |
| `MonthlyCharges` | Monthly charge amount |
| `TotalCharges` | Lifetime charges |
| `Contract` | Contract type (Month-to-month, One year, Two year) |
| `PaymentMethod` | Payment method |
| `PaperlessBilling` | Yes/No |
| `Partner` | Yes/No |
| `Dependents` | Yes/No |
| `OnlineSecurity` | Yes/No/No internet service |
| `OnlineBackup` | Yes/No/No internet service |
| `DeviceProtection` | Yes/No/No internet service |
| `TechSupport` | Yes/No/No internet service |
| `StreamingTV` | Yes/No/No internet service |
| `StreamingMovies` | Yes/No/No internet service |
| `SupportTickets90d` | Ticket count in last 90 days |
| `NPSLast` | Most recent NPS score |
| `UsageTrendPct` | Usage trend percentage |
| `InvoicePastDue` | Yes/No |
| `ActiveSeatRatio` | Active seat ratio |
| `Churn` | Target: Yes/No |

**Candidates CSV** has the same columns minus `Churn`.

**Feature count**: total columns minus `customer_id` and `Churn` (the target).

**Training/validation row counts**: number of data rows (excluding header).

**Accuracy**: computed from comparing model predictions against validation
labels.

**tenure_coefficient_direction**: negative means longer tenure correlates with
lower churn (the standard pattern). Check by comparing average tenure for churners
vs non-churners.

For the ranking, filter `candidates.csv` to only the account IDs listed in the
prompt, then sort descending by churn probability and take the top 5.
