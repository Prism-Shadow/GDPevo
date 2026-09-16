# ApexCloud Retention Rules

## Source precedence

- ARR: prefer `/api/billing/snapshots`; fall back to the per-account billing field only if the snapshot is unavailable.
- Revenue: use `recognized_revenue` from account metrics.
- Tickets: count only non-duplicate, non-spam, non-cancelled tickets.
- NPS: use non-retracted responses only.

## Monthly QBR packets

- Build one row per month in the requested window.
- `support_tickets`: count clean tickets created in that month.
- `sla_compliance_pct`: count clean tickets where both SLA booleans are true, divided by clean tickets in that month.
- `ticket_trend`: compare first and last monthly clean-ticket counts. Last lower than first is `improving`, higher is `worsening`, otherwise `flat`.
- `peak_*` fields: pick the maximum value in the window; break ties by earliest month.
- `metric_sources` normally map to `crm_closed_won`, `support_export`, `sla_report`, and `nps_survey`.

## Renewal and risk queues

- Treat old A/R as `61_90 + 90_plus`.
- Match A/R rows to CRM accounts by legal name or aliases.
- `clean_ticket_count` is the count of clean tickets in the period, including open tickets.
- `renewal_window` applies when renewal falls in the forward window from the as-of date.
- `overdue_receivable` applies when old A/R is greater than zero.
- `sla_degradation` applies when any clean ticket misses first-response or resolution SLA.
- `nps_drop` applies when latest NPS is materially weak, usually below 50 unless the prompt states a different threshold.
- `usage_decline` applies when the explicit usage-trend field is negative; otherwise use the start-to-end product-usage delta across the analysis window.
- `low_tenure_high_churn` applies to short-tenure accounts, especially month-to-month or recently onboarded customers.
- `expansion_offset` applies when there is open expansion pipeline in the window.
- `clean_billings` applies when old A/R is zero.
- If a prompt exposes a pipe-delimited policy enum, the correct code is usually the middle option that matches the rule described in the surrounding text.
- Keep reason-code lists short. Include only the strongest drivers needed to explain the rank, and order them by impact.

## Practical scoring

- Use a capped additive risk score.
- Typical weights: renewal window, overdue receivable, NPS weakness, SLA degradation, usage decline, and short tenure each add meaningful points.
- Escalate accounts with multiple issues into `critical` or `high`.
- Order ties by higher ARR, then by more urgent action.

## Action mapping

- `collections_followup`: overdue receivables or invoice risk.
- `technical_recovery`: support, SLA, NPS, or usage problems.
- `renewal_save`: renewal timing or churn risk without collections urgency.
- `executive_qbr`: strategic account needing leadership review.
- `nurture_monitor`: low-level watch item with no immediate intervention.
- `no_action`: only when the prompt allows it and the account is stable.

## Receivables and pipeline reviews

- Q3 receivables follow-ups: use the older aging buckets, not total current A/R.
- Sort overdue follow-ups by `customer_name`.
- Pipeline summary:
  - `won_count`: closed-won opportunities in the window.
  - `lost_count`: closed-lost opportunities in the window.
  - `open_count`: open opportunities in the window.
  - `open_pipeline`: sum open opportunity amounts.
  - `win_rate_pct`: `won_count / (won_count + lost_count) * 100`.
  - `top_open_product_line`: open product line with the largest open amount.
- HR summary: sum the requested quarter across all regions unless the prompt narrows it.
- Event summary: use the named event family and quarter from the prompt.

## Churn exports

- `feature_count` is the raw feature count in the CSV, excluding identifier and label columns.
- `training_rows` and `validation_rows` are the row counts from the exported files.
- Fit a deterministic binary classifier or equivalent probability ranker on the training export, then validate on the validation export.
- `accuracy_band` thresholds: below 70, 70 to 79, 80 to 89, 90 plus.
- `tenure_coefficient_direction` is the sign of the fitted tenure term.
- Rank candidates by predicted churn probability, descending.
- `past_due_shortlist_count`: top-5 candidates with `InvoicePastDue = Yes`.
- `low_tenure_shortlist_count`: top-5 candidates with short tenure.
- `average_probability_top5`: mean probability of the top five candidates.
- Typical outreach mapping:
  - overdue receivable -> `collections_followup`
  - short tenure / month-to-month churn -> `renewal_save`
  - SLA or product health issues -> `technical_recovery`
  - stable low-risk account -> `nurture_monitor`
