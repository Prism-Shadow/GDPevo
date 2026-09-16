# ApexCloud Data And Scoring Rules

This reference captures reusable conventions for ApexCloud Retention Operations JSON tasks. It intentionally avoids account-specific final answer records.

## Endpoint Use

- `/api/accounts` is the canonical account list. Per-account `/api/accounts/{account_id}` is useful for profiles.
- Per-account `/metrics`, `/tickets`, and `/nps` endpoints accept period filters and should still be filtered locally by month/date.
- Use aggregate `/api/billing/snapshots`, `/api/finance/ar-aging`, and `/api/opportunities`; filter locally by account, exact date/window, and state/stage.
- Use `/api/hr/summary` and `/api/events/performance` for operations context.
- Use `/exports/churn/train.csv`, `/exports/churn/validation.csv`, and `/exports/churn/candidates.csv` for churn tasks.

## Core Measures

- `current_arr`: posted billing snapshot `billing_arr` at the task as-of date; fallback to latest posted snapshot on/before as-of, then account profile `billing_arr_current`.
- `clean_ticket_count`: tickets where `is_duplicate` and `is_spam` are false and `status` is `open` or `closed`.
- SLA percent: clean tickets with both `first_response_sla_met` and `resolution_sla_met`, divided by clean tickets. Use `100.0` for display when a requested month has no clean tickets.
- Latest NPS: newest non-retracted response by `response_date`; monthly NPS is the newest non-retracted response within the month.
- `overdue_balance`: A/R older buckets only, `61_90 + 90_plus`.
- A/R CRM link: exact `customer_name == account.legal_name`; aliases and near-matches remain `unlinked`.
- Expansion pipeline: sum open opportunity `amount` for close dates inside the requested window.

## Risk Reasons

Add reason codes in this order when conditions apply:

1. `renewal_window`: renewal date is from the assessment date through the next 90 days.
2. `overdue_receivable`: older A/R overdue balance is greater than zero.
3. `nps_drop`: latest NPS is below 40, or the latest response dropped by at least 15 points from the first response in the period.
4. `sla_degradation`: clean-ticket SLA percent for the period is below 90.
5. `usage_decline`: average or latest product usage for the requested months is below 65.
6. `low_tenure_high_churn`: contract tenure is 18 months or less.
7. `expansion_offset`: include when the task asks for expansion pipeline and the account has open expansion, or in risk queues when open expansion is material.
8. `clean_billings`: include in risk queues for accounts without older overdue A/R.

## Risk Score And Level

Use this risk score for renewal queues and as the underlying severity for action boards:

- Renewal window: 20
- Older overdue A/R: 25
- NPS drop/low NPS: 10
- SLA degradation: 15
- Low usage: 10
- Low tenure: 15
- Lifecycle status `renewal_risk`: 5
- Revenue exposure: 5 when current ARR is at least 1,000,000 or the segment is Strategic

Cap scores at 100. Risk levels:

- `critical`: score >= 65
- `high`: score >= 45
- `medium`: score >= 30
- `low`: score < 30

Renewal risk queues sort by score descending, then current ARR descending. Retention boards sort by risk level severity, then current ARR descending.

## Actions

Primary action precedence:

1. `collections_followup` when older overdue A/R is present.
2. For renewal-risk queues, use `technical_recovery` for NPS, low-usage, or SLA problems, and `renewal_save` for renewal-window accounts with only mild technical symptoms.
3. For retention boards, use lifecycle status as the tie-breaker: `paused` medium-risk accounts usually get `renewal_save`, active medium-risk accounts with renewal/SLA friction get `technical_recovery`, and low-risk rows get `no_action`.
4. `executive_qbr` for healthy high-touch accounts when the template requires an action and no recovery/collections action fits.
5. `nurture_monitor` for low-risk monitoring when that enum is available.
6. `no_action` for board rows that allow no action and have only low residual risk.

Use prompt-specified due dates for board actions. `no_action` rows use `null` for next-touch due date.

## Portfolio Summaries

- Renewal queue `arr_at_risk`: sum current ARR for critical/high accounts in the reviewed set or returned queue, matching the prompt scope.
- Board `arr_at_risk`: sum current ARR for rows with critical, high, or medium risk.
- Board `open_expansion_pipeline`: sum all open expansion pipeline in the included board rows.
- Board `net_revenue_exposure`: `arr_at_risk - open_expansion_pipeline`.
- Strategic/Enterprise counts come from account `segment`; do not count Strategic rows as Enterprise.

## QBR Metrics

- Revenue comes from monthly metrics `recognized_revenue`.
- Support tickets and SLA come from the cleaned ticket convention, grouped by created month.
- NPS comes from non-retracted NPS responses.
- `ticket_trend` is `improving` when the final month has fewer clean tickets than the first month, `worsening` when it has more, otherwise `flat`.
- Source enums: revenue `crm_closed_won`, support `support_export`, SLA `sla_report`, NPS `nps_survey`.
- Default agenda order: `partnership_overview`, `q2_metrics`, then `technical_recovery` if any month has SLA below 90 or high support friction, otherwise `performance_highlights`, then `q3_initiatives`.

## Receivables And Pipeline

- Include A/R follow-ups only for rows with `61_90 + 90_plus > 0`.
- Sort follow-ups by `customer_name` ascending.
- Pipeline summaries use opportunity close date inside the requested range:
  - won: `stage == "Closed Won"`
  - lost: `stage == "Closed Lost"`
  - open: `state == "open"`
- Win rate is won count divided by won plus lost count.
- Top open product line is the product line with the largest summed open amount.

## Churn Export Tasks

- Report raw row counts for train and validation exports.
- Feature count is the number of predictor columns: all columns except `customer_id` and `Churn`.
- Validation accuracy is computed from thresholded deployed probabilities against the validation labels.
- Tenure coefficient direction is `negative`: lower tenure increases churn risk.
- Deployment probabilities use ApexCloud's calibrated raw-feature heuristic and are rounded to three decimals.
- Outreach action/reason mapping:
  - Past-due invoice: `collections_followup` / `overdue_receivable`
  - Tenure <= 18 or month-to-month churn risk: `renewal_save` / `low_tenure_high_churn`
  - Support/NPS/usage technical friction: `technical_recovery` / the strongest technical reason
  - Otherwise: `nurture_monitor` / `clean_billings`
