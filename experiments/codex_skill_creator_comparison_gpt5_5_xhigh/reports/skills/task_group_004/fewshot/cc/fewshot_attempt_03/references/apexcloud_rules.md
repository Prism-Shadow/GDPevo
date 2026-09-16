# ApexCloud Rules

## Table of contents

1. Endpoint map
2. Field precedence
3. Rollup rules
4. Churn fallback scoring
5. Policy-code handling

## 1. Endpoint map

- Accounts: `/api/accounts`
- Account metrics: `/api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM`
- Account tickets: `/api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`
- Account NPS: `/api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`
- Billing snapshots: `/api/billing/snapshots?as_of=YYYY-MM-DD`
- A/R aging: `/api/finance/ar-aging?as_of=YYYY-MM-DD`
- Opportunities: `/api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD`
- HR summary: `/api/hr/summary?quarter=YYYY-QN`
- Event performance: `/api/events/performance?event=<event_id>&quarter=YYYY-QN`
- Churn exports: `/exports/churn/train.csv`, `/exports/churn/validation.csv`, `/exports/churn/candidates.csv`

## 2. Field precedence

- Prefer billing snapshot ARR over account profile ARR.
- Prefer recognized revenue from account metrics for QBR revenue.
- Prefer clean ticket counts from ticket detail when monthly support counts are needed.
- Prefer latest non-retracted NPS response for a manual rollup.
- Prefer exact normalized legal name for A/R linkage.
- Treat similar names as unlinked unless they normalize to the same legal name.

## 3. Rollup rules

### Clean tickets

- Keep tickets where `is_spam` is false, `is_duplicate` is false, and `status` is not `cancelled`.
- SLA compliance for a period is the share of clean tickets with both SLA booleans true.
- Ticket trend is improving when the last month is below the first month, worsening when it is above, otherwise flat.

### A/R aging

- Overdue balance is `61_90 + 90_plus`.
- A row is overdue when that sum is greater than zero.
- For linked rows, match A/R `customer_name` to the account legal name after normalizing case and punctuation.

### Opportunities

- Split counts and revenue by `open`, `Closed Won`, and `Closed Lost` as the prompt asks.
- Open pipeline is the sum of open opportunities inside the requested window.
- Top open product line is the open product line with the largest total amount.

### HR and events

- HR summary aggregates by region; sum headcount and money fields across regions when the prompt asks for a total.
- Event performance is usually a single row for the requested event and quarter.

## 4. Churn fallback scoring

When the task asks for a churn validation or ranked candidate list and you need a lightweight deterministic fallback, use this score:

```text
score =
  2.0 * contract_risk +
  20.0 / (tenure + 1.0) +
  0.5 * invoice_past_due +
  0.5 * nps_risk +
  0.2 * usage_risk +
  0.1 * support_risk
```

Where:

- `contract_risk` = 1.0 for month-to-month, 0.5 for one year, 0.0 for two year
- `invoice_past_due` = 1.0 for yes, else 0.0
- `nps_risk` = `max(0, 50 - NPSLast) / 50`
- `usage_risk` = `max(0, -UsageTrendPct) / 20`
- `support_risk` = `SupportTickets90d / 10`

Convert the score into a small probability with a calibrated sigmoid, then floor tiny values to `0.001` so the output stays readable. Keep validation accuracy by thresholding at 0.5.

## 5. Policy-code handling

- Treat policy-code fields as metadata, not data.
- Fill them after the substantive JSON is correct.
- Choose the label that matches the rule you used, not the label that merely looks central.

