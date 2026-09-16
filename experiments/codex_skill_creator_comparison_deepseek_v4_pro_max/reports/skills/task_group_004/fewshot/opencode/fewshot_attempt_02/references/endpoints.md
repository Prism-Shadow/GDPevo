# API Endpoint Reference

Base URL: the task prompt provides this (typically `http://task-env:9004`). All endpoints are GET requests with no authentication required.

---

## /api/health

Returns service metadata.

**Response shape:**
```json
{
  "status": "ok",
  "service": "ApexCloud Retention Operations",
  "seed": 4004,
  "row_counts": { ... }
}
```

---

## /api/accounts

Returns all 44 accounts. No query parameters.

**Response shape:**
```json
{
  "accounts": [
    {
      "account_id": "acct_globex_north",
      "legal_name": "Globex North Holdings LLC",
      "display_name": "Globex North",
      "account_aliases": ["Globex North", "Globex North Holdings", "GlobexNorth Ops", "Globex North Subsidiary"],
      "region": "North America",
      "segment": "Enterprise",
      "lifecycle_status": "active",
      "product_plan": "Scale",
      "contract_tenure_months": 29,
      "renewal_date": "2026-09-11",
      "billing_arr_current": 1188000.00,
      "crm_arr": 1057320.00,
      "csm_owner": "Maya Chen"
    }
  ]
}
```

Key fields:
- `account_id`: Unique identifier, always starts with `acct_`
- `account_aliases`: Array of alternative names. Used to match A/R aging customer names to accounts.
- `lifecycle_status`: `active`, `implementation`, `renewal_risk`, or `paused`
- `billing_arr_current`: Live billing system ARR (may differ from quarter-end snapshots)
- `crm_arr`: CRM-recorded ARR (may be stale or rounded)
- `renewal_date`: ISO date string (YYYY-MM-DD)

---

## /api/accounts/{account_id}

Returns the same account object as in the list, for a single account.

---

## /api/accounts/{account_id}/metrics

Monthly aggregated metrics. **Query params:** `start=YYYY-MM&end=YYYY-MM` (inclusive).

**Response shape:**
```json
{
  "account_id": "acct_globex_north",
  "count": 3,
  "metrics": [
    {
      "account_id": "acct_globex_north",
      "month": "2026-04",
      "quarter": "2026-Q2",
      "recognized_revenue": 95756.67,
      "support_ticket_count": 4,
      "sla_compliance": 95.2,
      "nps_score": 45,
      "product_usage": 76.12,
      "active_seats": 109,
      "survey_status": "completed"
    }
  ]
}
```

Key fields:
- `recognized_revenue`: Monthly recognized revenue (currency, use as-is)
- `support_ticket_count`: **Raw count** including spam, duplicates, cancelled. Do not use for clean ticket counts.
- `sla_compliance`: Percentage (e.g. 95.2 means 95.2%)
- `nps_score`: Integer or `null` (when `survey_status` is `"missing"`)
- `product_usage`: Percentage
- `active_seats`: Integer
- `survey_status`: `"completed"` or `"missing"`

---

## /api/accounts/{account_id}/tickets

Individual support tickets. **Query params:** `start=YYYY-MM-DD&end=YYYY-MM-DD` (inclusive).

**Response shape:**
```json
{
  "account_id": "acct_globex_north",
  "count": 6,
  "tickets": [
    {
      "ticket_id": "TCK-10001",
      "account_id": "acct_globex_north",
      "created_date": "2026-04-03",
      "status": "closed",
      "severity": "P3",
      "product_area": "analytics",
      "first_response_sla_met": true,
      "resolution_sla_met": true,
      "is_spam": false,
      "is_duplicate": false
    }
  ]
}
```

Key fields:
- `is_spam`, `is_duplicate`: Boolean flags for filtering
- `status`: `"closed"`, `"open"`, `"cancelled"`, `"pending"`
- `first_response_sla_met`, `resolution_sla_met`: Boolean SLA compliance per ticket
- `severity`: `"P1"`, `"P2"`, `"P3"`, `"P4"`
- `product_area`: String like `"billing"`, `"integrations"`, `"workflow"`, `"analytics"`, `"mobile"`, `"identity"`

---

## /api/accounts/{account_id}/nps

Individual NPS survey responses. **Query params:** `start=YYYY-MM-DD&end=YYYY-MM-DD` (inclusive).

**Response shape:**
```json
{
  "account_id": "acct_globex_north",
  "count": 3,
  "nps_responses": [
    {
      "response_id": "NPS-7001",
      "account_id": "acct_globex_north",
      "response_date": "2026-04-08",
      "survey_channel": "email",
      "score": 45,
      "retracted": false
    }
  ]
}
```

Key fields:
- `score`: Integer NPS score (-100 to 100, but the API only has 0-100). In this API, score can be negative (e.g. -11).
- `retracted`: Boolean. **Filter out retracted responses.** A retracted response is not a valid NPS data point.
- `survey_channel`: `"email"`, `"csm_call"`, `"in_app"`

---

## /api/billing/snapshots

All billing snapshots (176 records, 4 quarters per account). No query parameters.

**Response shape:**
```json
{
  "count": 176,
  "snapshots": [
    {
      "snapshot_id": "BILL-acct_globex_north-2026-Q2",
      "account_id": "acct_globex_north",
      "legal_name": "Globex North Holdings LLC",
      "as_of": "2026-06-30",
      "billing_arr": 1176600.70,
      "mrr": 98050.06,
      "posted": true,
      "source": "billing_snapshot"
    }
  ]
}
```

Key fields:
- `as_of`: ISO date (YYYY-MM-DD). Always a quarter-end date.
- `billing_arr`: The authoritative point-in-time ARR. Use this for report ARR values.
- `posted`: Boolean. All snapshots in the API are posted.

---

## /api/finance/ar-aging

All A/R aging records (196 records, 4 quarters per customer). No query parameters.

**Response shape:**
```json
{
  "ar_aging": [
    {
      "aging_id": "AR-acct_globex_north-2026-Q2",
      "customer_name": "Globex North Holdings LLC",
      "quarter": "2026-Q2",
      "as_of": "2026-06-30",
      "region": "North America",
      "current": 33930.72,
      "1_30": 3657.55,
      "31_60": 5405.15,
      "61_90": 14558.44,
      "90_plus": 7065.02
    }
  ]
}
```

Key fields:
- `customer_name`: The name in the billing/AR system. Match this to account `legal_name` or `account_aliases`.
- `current`, `1_30`, `31_60`, `61_90`, `90_plus`: Aging buckets in currency.
- **Overdue balance** = `61_90` + `90_plus`. This is the primary overdue metric.
- `as_of`: Quarter-end date for the aging snapshot.

Some customer names (like "Globex North Subsidiary LLC", "North Star Finance Services", "Quartz Insurance Claims Ltd.", "Riverbend Bank Foundation", "Valence Payment Services Canada") appear in A/R aging but do not directly match an existing account's `legal_name` or `account_aliases`. These are unlinked records. For example, "Globex North Subsidiary LLC" is not in `account_aliases` of `acct_globex_north` — but "Globex North Subsidiary" (without "LLC") is. Match carefully.

---

## /api/opportunities

All CRM opportunities (114 records). No query parameters.

**Response shape:**
```json
{
  "count": 114,
  "opportunities": [
    {
      "opportunity_id": "OPP-501",
      "account_id": "acct_globex_north",
      "account_legal_name": "Globex North Holdings LLC",
      "amount": 144517.62,
      "product_line": "Workflow Plus",
      "stage": "Proposal",
      "state": "open",
      "close_date": "2026-12-15",
      "created_date": "2026-11-09",
      "region": "North America"
    }
  ]
}
```

Key fields:
- `state`: `"open"` or `"closed"`
- `stage`: `"Prospecting"`, `"Discovery"`, `"Proposal"`, `"Negotiation"`, `"Closed Won"`, `"Closed Lost"`
- `close_date`: ISO date
- `amount`: Currency value
- `product_line`: Product name string

For pipeline summaries: count won/lost/open by `state` and `stage`. For expansion pipeline per account: sum `amount` for open opportunities whose `close_date` falls within the relevant period.

---

## /api/hr/summary

HR summaries by quarter and region (16 records). No query parameters.

**Response shape:**
```json
{
  "count": 16,
  "hr_summary": [
    {
      "quarter": "2026-Q1",
      "region": "North America",
      "headcount": 61,
      "attendance_rate": 98.16,
      "high_absence_employees": 4,
      "leave_liability_hours": 530.0,
      "unpaid_claims_amount": 35523.06,
      "unpaid_claims_count": 16,
      "open_advances_amount": 22035.75,
      "open_advances_count": 4
    }
  ]
}
```

Key fields for ops context:
- `headcount`: Sum across all regions for the target quarter.
- `unpaid_claims_amount`: Sum across all regions for the target quarter.

---

## /api/events/performance

Event performance by event and quarter (20 records). No query parameters.

**Response shape:**
```json
{
  "count": 20,
  "event_performance": [
    {
      "event_id": "apex_connect",
      "quarter": "2026-Q1",
      "event_orders": 521,
      "event_revenue": 367775.66,
      "completed_orders": 450,
      "pending_orders": 31,
      "cancelled_orders": 32,
      "refunded_orders": 8,
      "product_revenue": 145004.64
    }
  ]
}
```

Key fields for ops context: filter by `event_id` and `quarter`, then read `event_orders` and `event_revenue`.

---

## CSV Exports

### /exports/churn/train.csv
180 rows, 20 columns including `Churn` (target). Header row present. Standard CSV.

### /exports/churn/validation.csv
60 rows, same schema as train.csv but includes ground-truth `Churn` column. Header row present.

### /exports/churn/candidates.csv
44 rows (all accounts). Same schema as train.csv but without the `Churn` column. These are the accounts to predict on. Header row present.

**Candidate CSV columns:**
`customer_id`, `tenure`, `MonthlyCharges`, `TotalCharges`, `Contract`, `PaymentMethod`, `PaperlessBilling`, `Partner`, `Dependents`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`, `SupportTickets90d`, `NPSLast`, `UsageTrendPct`, `InvoicePastDue`, `ActiveSeatRatio`

### /exports/account_metric_extract.csv
528 rows (12 months × 44 accounts). Monthly resolved metrics. Header row present.

**Columns:** `account_id`, `legal_name`, `segment`, `region`, `month`, `recognized_revenue`, `clean_ticket_count`, `sla_compliance`, `nps_score`, `product_usage`, `active_seats`
