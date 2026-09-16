# API Endpoints Reference

Base URL: `<TASK_ENV_BASE_URL>` (provided in each task prompt).

## Health

```
GET /api/health
```

Returns service status, seed, and row counts for all datasets.

```json
{
  "service": "ApexCloud Retention Operations",
  "status": "ok",
  "seed": 4004,
  "row_counts": { }
}
```

---

## Accounts

### List All Accounts

```
GET /api/accounts
```

Returns all 44 accounts.

Key fields for analysis:
- `account_id` — unique identifier
- `billing_arr_current` — authoritative ARR from billing system (use for `current_arr`)
- `crm_arr` — ARR from CRM (use for revenue source tracking, not as primary ARR)
- `contract_tenure_months` — tenure in months (lower = higher churn risk)
- `renewal_date` — upcoming renewal date (proximity drives risk)
- `lifecycle_status` — active | implementation | renewal_risk | paused
- `segment` — Strategic | Enterprise | Mid-Market | SMB
- `product_plan` — Strategic | Enterprise | Scale | Growth | Launch
- `account_aliases` — used for customer name matching against A/R aging
- `legal_name` — used for customer name matching against A/R aging

### Single Account

```
GET /api/accounts/{account_id}
```

Returns the same shape as above for a single account.

---

## Account Metrics

```
GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM
```

Returns monthly metrics for the given month range (inclusive).

Key fields:
- `recognized_revenue` — monthly recognized revenue (use for QBR metrics)
- `support_ticket_count` — raw ticket count including spam/duplicates (do NOT use; fetch tickets endpoint for clean count)
- `sla_compliance` — SLA compliance percentage (already 1 decimal)
- `nps_score` — NPS score for the month; may be null if survey missing
- `product_usage` — usage metric (declining = usage_decline risk)
- `active_seats` — number of active seats
- `survey_status` — completed | missing

---

## Support Tickets

```
GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD
```

Returns individual tickets for the date range.

**Clean ticket count:** Filter `is_duplicate == false AND is_spam == false`. Count remaining tickets.

**SLA from tickets (alternative):** Count `first_response_sla_met == true` divided by clean ticket count. This is a secondary approach; prefer the `sla_compliance` field from metrics endpoint when available.

---

## NPS Responses

```
GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD
```

Returns individual NPS survey responses.

**Latest NPS:** Take the most recent non-null `score` (by `response_date`) where `retracted == false`. This is the `latest_nps` for risk ranking.

---

## Billing Snapshots

```
GET /api/billing/snapshots
```

Returns quarterly billing snapshots for all accounts.

Filter by `account_id` and `as_of` to get the billing ARR for a specific quarter-end date.

---

## A/R Aging

```
GET /api/finance/ar-aging
```

Returns A/R aging entries for all customers across quarters.

**Overdue balance:** `31_60 + 61_90 + 90_plus`. Do NOT include `current` or `1_30`.

**Customer name matching:** Match `customer_name` against account `account_aliases` and `legal_name` to link A/R entries to CRM accounts. If no match, the customer is `unlinked`.

---

## Opportunities (Pipeline)

```
GET /api/opportunities
```

Returns CRM pipeline opportunities.

**Pipeline summary:**
- `won_count` / `won_revenue`: count and sum `amount` where `state == "won"` and close_date within period
- `lost_count`: count where `state == "lost"` and close_date within period
- `open_count` / `open_pipeline`: count and sum `amount` where `state == "open"` and close_date within period
- `win_rate_pct`: `won_count / (won_count + lost_count) * 100`, format to 1 decimal
- `top_open_product_line`: most frequent `product_line` among open opportunities in period; break ties alphabetically

**Expansion pipeline per account:** Sum `amount` where `state == "open"`, `close_date` within analysis period, for the specific `account_id`.

---

## HR Summary

```
GET /api/hr/summary
```

Returns quarterly HR summary by region.

For ops context, sum `headcount` across all regions for the specified quarter. Sum `unpaid_claims_amount` across all regions.

---

## Event Performance

```
GET /api/events/performance
```

Returns quarterly event performance data.

Filter by `event_id` and `quarter`. Use `event_orders` and `event_revenue` for ops context.

---

## Churn Model Exports

### Training Data

```
GET /exports/churn/train.csv
```

CSV with 20 columns: `customer_id,tenure,MonthlyCharges,TotalCharges,Contract,PaymentMethod,PaperlessBilling,Partner,Dependents,OnlineSecurity,OnlineBackup,DeviceProtection,TechSupport,StreamingTV,StreamingMovies,SupportTickets90d,NPSLast,UsageTrendPct,InvoicePastDue,ActiveSeatRatio,Churn`

`feature_count` excludes `customer_id` and `Churn` (the label), so **19 features**.

Row count (`training_rows`): count all data rows (excluding header).

### Validation Data

```
GET /exports/churn/validation.csv
```

Same schema. `validation_rows`: count all data rows.

**Accuracy:** Compute from the validation csv. The `Churn` column is the ground-truth label. For deterministic output use the validation row count and a computed accuracy percentage.

**tenure_coefficient_direction:** If tenure is negatively correlated with churn in the training data, use `"negative"`. In practice, lower tenure = higher churn, so this is typically `"negative"`.

### Candidate Data

```
GET /exports/churn/candidates.csv
```

Same schema minus the `Churn` column (19 features). Contains 44 candidate records. Filter by the specified `account_id` list (match on `customer_id` field).

---

## Account Metric Extract (CSV)

```
GET /exports/account_metric_extract.csv
```

Flat CSV with columns: `account_id,legal_name,segment,region,month,recognized_revenue,clean_ticket_count,sla_compliance,nps_score,product_usage,active_seats`

This is a denormalized extract that can serve as an alternative data source for account-month metrics. The `clean_ticket_count` field here already excludes spam/duplicates, so it is a convenient shortcut.
