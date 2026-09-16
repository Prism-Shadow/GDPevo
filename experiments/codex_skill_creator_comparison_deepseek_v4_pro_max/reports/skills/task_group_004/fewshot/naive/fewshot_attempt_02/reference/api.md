# ApexCloud Retention Operations API Reference

Base URL is provided in the task prompt as `<TASK_ENV_BASE_URL>`. All paths below are relative to that base.

---

## GET /api/health

Returns service health, row counts, and seed.

**Response shape:**

```json
{
  "row_counts": {
    "account_metric_extract.csv": 528,
    "account_metrics.json": 528,
    "accounts.json": 44,
    "ar_aging.json": 196,
    "billing_snapshots.json": 176,
    "churn_candidates.csv": 44,
    "churn_train.csv": 180,
    "churn_validation.csv": 60,
    "event_performance.json": 20,
    "hr_summary.json": 16,
    "nps_responses.json": 451,
    "opportunities.json": 114,
    "support_tickets.json": 1595
  },
  "seed": 4004,
  "service": "ApexCloud Retention Operations",
  "status": "ok"
}
```

---

## GET /api/accounts

Returns all CRM accounts.

**Response shape:**

```json
{
  "accounts": [
    {
      "account_id": "acct_globex_north",
      "account_aliases": ["Globex North", "Globex North Holdings"],
      "billing_arr_current": 1188000.00,
      "contract_tenure_months": 29,
      "crm_arr": 1057320.00,
      "csm_owner": "Maya Chen",
      "display_name": "Globex North",
      "legal_name": "Globex North Holdings LLC",
      "lifecycle_status": "active",
      "product_plan": "Scale",
      "region": "North America",
      "renewal_date": "2026-09-11",
      "segment": "Enterprise"
    }
  ]
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | string | Unique account identifier |
| `account_aliases` | string[] | Alternative names used in other systems |
| `billing_arr_current` | float | Current ARR from billing system |
| `contract_tenure_months` | int | Months since contract start |
| `crm_arr` | float | CRM-sourced ARR |
| `csm_owner` | string | Customer success manager name |
| `display_name` | string | Short display name |
| `legal_name` | string | Full legal entity name |
| `lifecycle_status` | string | Account lifecycle state |
| `product_plan` | string | Product tier |
| `region` | string | Geographic region |
| `renewal_date` | string | Contract renewal date (YYYY-MM-DD) |
| `segment` | string | Customer segment |

---

## GET /api/accounts/{account_id}

Returns a single account. Same shape as the accounts list item above.

---

## GET /api/accounts/{account_id}/metrics

Returns monthly metrics for an account.

**Query parameters:**

| Param | Format | Required | Description |
|-------|--------|----------|-------------|
| `start` | YYYY-MM | Yes | Start month inclusive |
| `end` | YYYY-MM | Yes | End month inclusive |

**Response shape:**

```json
{
  "account_id": "acct_globex_north",
  "count": 3,
  "metrics": [
    {
      "account_id": "acct_globex_north",
      "active_seats": 109,
      "month": "2026-04",
      "nps_score": 45,
      "product_usage": 76.12,
      "quarter": "2026-Q2",
      "recognized_revenue": 95756.67,
      "sla_compliance": 95.2,
      "support_ticket_count": 4,
      "survey_status": "completed"
    }
  ]
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `active_seats` | int | Active user seats |
| `month` | string | Month in YYYY-MM |
| `nps_score` | int or null | Pre-computed NPS for the month |
| `product_usage` | float | Product usage percentage |
| `quarter` | string | Quarter label |
| `recognized_revenue` | float | Revenue recognized for the month |
| `sla_compliance` | float | SLA compliance percentage |
| `support_ticket_count` | int | Raw ticket count for the month |
| `survey_status` | string | NPS survey status |

---

## GET /api/accounts/{account_id}/tickets

Returns support tickets for an account.

**Query parameters:**

| Param | Format | Required | Description |
|-------|--------|----------|-------------|
| `start` | YYYY-MM-DD | Yes | Start date inclusive |
| `end` | YYYY-MM-DD | Yes | End date inclusive |

**Response shape:**

```json
{
  "account_id": "acct_globex_north",
  "count": 11,
  "tickets": [
    {
      "account_id": "acct_globex_north",
      "created_date": "2026-04-16",
      "first_response_sla_met": true,
      "is_duplicate": false,
      "is_spam": false,
      "product_area": "billing",
      "resolution_sla_met": true,
      "severity": "P3",
      "status": "closed",
      "ticket_id": "TCK-10013"
    }
  ]
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `created_date` | string | Creation date YYYY-MM-DD |
| `first_response_sla_met` | bool | First response SLA met |
| `is_duplicate` | bool | Duplicate flag (exclude for clean counts) |
| `is_spam` | bool | Spam flag (exclude for clean counts) |
| `product_area` | string | Product area |
| `resolution_sla_met` | bool | Resolution SLA met |
| `severity` | string | P1-P4 severity |
| `status` | string | Ticket status |
| `ticket_id` | string | Unique ticket ID |

---

## GET /api/accounts/{account_id}/nps

Returns NPS survey responses for an account.

**Query parameters:**

| Param | Format | Required | Description |
|-------|--------|----------|-------------|
| `start` | YYYY-MM-DD | Yes | Start date inclusive |
| `end` | YYYY-MM-DD | Yes | End date inclusive |

**Response shape:**

```json
{
  "account_id": "acct_globex_north",
  "count": 3,
  "nps_responses": [
    {
      "account_id": "acct_globex_north",
      "response_date": "2026-04-07",
      "response_id": "NPS-7005",
      "retracted": false,
      "score": 45,
      "survey_channel": "csm_call"
    }
  ]
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `response_date` | string | Date of response YYYY-MM-DD |
| `response_id` | string | Unique response ID |
| `retracted` | bool | Whether response was retracted |
| `score` | int | NPS score (-100 to 100) |
| `survey_channel` | string | Survey delivery channel |

---

## GET /api/billing/snapshots

Returns all billing snapshots across accounts and quarters.

**Response shape:**

```json
{
  "count": 176,
  "snapshots": [
    {
      "account_id": "acct_globex_north",
      "as_of": "2026-03-31",
      "billing_arr": 1230600.05,
      "legal_name": "Globex North Holdings LLC",
      "mrr": 102550.00,
      "posted": true,
      "snapshot_id": "BILL-acct_globex_north-2026-Q1",
      "source": "billing_snapshot"
    }
  ]
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | string | Account identifier |
| `as_of` | string | Snapshot date YYYY-MM-DD |
| `billing_arr` | float | ARR in the billing system at snapshot |
| `legal_name` | string | Legal entity name |
| `mrr` | float | Monthly recurring revenue |
| `posted` | bool | Whether snapshot is posted |
| `snapshot_id` | string | Unique snapshot ID |
| `source` | string | Data source |

Filter by `as_of` date to get the snapshot matching your assessment date quarter. The snapshot `as_of` dates are quarter-end dates: `2026-03-31` (Q1), `2026-06-30` (Q2), `2026-09-30` (Q3), `2026-12-31` (Q4).

---

## GET /api/finance/ar-aging

Returns global A/R aging records across all customers and quarters.

**Response shape:**

```json
{
  "ar_aging": [
    {
      "1_30": 8748.27,
      "31_60": 470.21,
      "61_90": 0.00,
      "90_plus": 0.00,
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

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `1_30` | float | Amount 1-30 days past due |
| `31_60` | float | Amount 31-60 days past due |
| `61_90` | float | Amount 61-90 days past due |
| `90_plus` | float | Amount 90+ days past due |
| `as_of` | string | Aging date YYYY-MM-DD |
| `current` | float | Current (not past due) balance |
| `customer_name` | string | Customer legal name (match to accounts) |
| `quarter` | string | Quarter label |
| `region` | string | Geographic region |

**Overdue balance** = `1_30 + 31_60 + 61_90 + 90_plus`. The `current` bucket is not overdue.

---

## GET /api/opportunities

Returns all CRM opportunities.

**Response shape:**

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

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | string | Account identifier |
| `account_legal_name` | string | Legal name |
| `amount` | float | Opportunity amount |
| `close_date` | string | Expected close date YYYY-MM-DD |
| `created_date` | string | Creation date YYYY-MM-DD |
| `opportunity_id` | string | Unique opportunity ID |
| `product_line` | string | Product line name |
| `region` | string | Geographic region |
| `stage` | string | Sales stage |
| `state` | string | `open`, `closed_won`, or `closed_lost` |

---

## GET /api/hr/summary

Returns HR summaries by region and quarter.

**Response shape:**

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

**Fields:** `attendance_rate` (float), `headcount` (int), `high_absence_employees` (int), `leave_liability_hours` (float), `open_advances_amount` (float), `open_advances_count` (int), `quarter` (string), `region` (string), `unpaid_claims_amount` (float), `unpaid_claims_count` (int).

Filter by `quarter` and optionally by `region` to match task parameters. When aggregating across all regions, sum `headcount` and `unpaid_claims_amount` across all matching records.

---

## GET /api/events/performance

Returns event performance by quarter and event.

**Response shape:**

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

**Fields:** `cancelled_orders` (int), `completed_orders` (int), `event_id` (string), `event_orders` (int), `event_revenue` (float), `pending_orders` (int), `product_revenue` (float), `quarter` (string), `refunded_orders` (int).

Filter by `event_id` and `quarter` as specified in the task.

---

## GET /exports/churn/train.csv

Churn model training dataset (180 rows). CSV columns:

`customer_id,tenure,MonthlyCharges,TotalCharges,Contract,PaymentMethod,PaperlessBilling,Partner,Dependents,OnlineSecurity,OnlineBackup,DeviceProtection,TechSupport,StreamingTV,StreamingMovies,SupportTickets90d,NPSLast,UsageTrendPct,InvoicePastDue,ActiveSeatRatio,Churn`

The `Churn` column contains `Yes` or `No`.

---

## GET /exports/churn/validation.csv

Churn model validation dataset (60 rows). Same CSV schema as train.csv with the `Churn` label column.

---

## GET /exports/churn/candidates.csv

Churn candidate accounts (44 rows). CSV columns (no `Churn` label):

`customer_id,tenure,MonthlyCharges,TotalCharges,Contract,PaymentMethod,PaperlessBilling,Partner,Dependents,OnlineSecurity,OnlineBackup,DeviceProtection,TechSupport,StreamingTV,StreamingMovies,SupportTickets90d,NPSLast,UsageTrendPct,InvoicePastDue,ActiveSeatRatio`

---

## GET /exports/account_metric_extract.csv

Full account metric extract (528 rows). CSV columns:

`account_id,legal_name,segment,region,month,recognized_revenue,clean_ticket_count,sla_compliance,nps_score,product_usage,active_seats`

This provides pre-computed clean ticket counts, SLA compliance, NPS scores, and product usage for every account-month combination. Use it for bulk lookups instead of hitting the per-account endpoints repeatedly.
