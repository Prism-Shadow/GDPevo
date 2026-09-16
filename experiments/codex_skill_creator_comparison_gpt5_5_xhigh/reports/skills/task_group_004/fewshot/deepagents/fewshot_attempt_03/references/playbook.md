# ApexCloud Retention Reporting Playbook

## Shared rules

- Use only the task environment base URL from the prompt.
- Match the template exactly. Return JSON only.
- Use exact controlled labels. Do not invent new enum values.
- Currency values use 2 decimals. Percentages use 1 decimal unless the prompt says otherwise. Counts are integers.
- Prefer exact legal-name matching for account links. Mark a customer unlinked unless the match is unambiguous.
- For ARR, use billing snapshots posted at the requested as-of date, not CRM ARR.
- For overdue balance, use the severe delinquency buckets (`61_90` + `90_plus`) unless the prompt states a different aging scope.
- For latest NPS, use the latest non-retracted score in the requested window. Keep nulls when a month has no survey.

## Template: `risk_accounts` / `portfolio_summary`

- Source account profile data from `/api/accounts`.
- Pull `current_arr` from `/api/billing/snapshots` for the requested as-of date.
- Pull `overdue_balance` from `/api/finance/ar-aging` for the same as-of date.
- Pull monthly metrics, tickets, and NPS when you need usage, SLA, and sentiment signals.
- Rank by renewal risk. Use this order of pressure signals:
  - overdue receivables
  - renewal window
  - SLA degradation
  - NPS drop
  - usage decline
  - low tenure
- Choose `collections_followup` for severe overdue, `technical_recovery` for health or usage issues, `renewal_save` for renewal pressure, `nurture_monitor` for low-risk rows.
- `clean_ticket_count` should count closed tickets that are not spam and not duplicates.
- `critical_or_high_count` should count rows labeled `critical` or `high`.
- `collections_count` and `technical_recovery_count` should count rows with those actions.
- `arr_at_risk` should sum the `current_arr` values for the rows included in the at-risk queue.
- `model_checks.uses_billing_arr_source` should be `true` when ARR comes from billing snapshots.
- `model_checks.tenure_risk_direction` should be `negative` when shorter tenure increases risk.

## Template: `action_board` / `segment_summary` / `followup_calendar`

- Use the same account, billing, AR, tickets, NPS, and opportunity sources as the renewal-risk queue.
- Set `current_arr` from the posted billing snapshot as of the review date.
- Set `expansion_pipeline` from open opportunities in the requested window.
- Set `next_touch_due_date` from the follow-up calendar for the chosen action, or `null` for low/no-action rows.
- Sort by the board's risk order, not alphabetically.
- `segment_summary.strategic_accounts` and `enterprise_accounts` should count the returned rows in those segments.
- `arr_at_risk` should sum the rows that require action.
- `open_expansion_pipeline` should sum `expansion_pipeline`.
- `net_revenue_exposure` should equal `arr_at_risk - open_expansion_pipeline`.

## Template: `qbr_metrics` / `highlights`

- Use `/api/accounts/{id}/metrics?start=YYYY-MM&end=YYYY-MM`.
- Map fields directly:
  - `revenue` -> `recognized_revenue`
  - `support_tickets` -> `support_ticket_count`
  - `sla_compliance_pct` -> `sla_compliance`
  - `nps_score` -> `nps_score`
- Set `ticket_trend` by comparing monthly support ticket counts. Decreasing is `improving`, increasing is `worsening`, otherwise `flat`.
- Set `metric_sources` by data origin, not by endpoint name:
  - revenue -> `crm_closed_won`
  - support_tickets -> `support_export`
  - sla_compliance -> `sla_report`
  - nps -> `nps_survey`
- Choose `review_owner` by the dominant need:
  - `customer_success` for standard account reviews
  - `solutions_engineering` when technical recovery dominates
  - `finance_ops` when billing or collections dominates
- Choose four ordered `agenda_topics` that match the story in the data, usually a mix of `partnership_overview`, `q2_metrics`, `technical_recovery`, `commercial_expansion`, and `q3_initiatives`.

## Template: `financial_summary` / `pipeline_summary` / `overdue_followups` / `ops_context`

- Build overdue follow-ups from `/api/finance/ar-aging` at the requested as-of date.
- Keep only rows with overdue balances. Sort by `customer_name` ascending.
- Set `link_status` to `linked` only when the customer resolves cleanly to a known account. Use `account_id` from `/api/accounts` when linked; otherwise set `account_id` to `null`.
- Set `overdue_total` to the sum of the overdue balances in the follow-up list.
- Filter `/api/opportunities` to the requested quarter.
- Count `stage == "Closed Won"` as won and `stage == "Closed Lost"` as lost.
- Count `state == "open"` as open.
- Compute `win_rate_pct` as `won / (won + lost) * 100`.
- Set `top_open_product_line` to the open product line with the largest summed amount.
- For `ops_context`, sum the requested HR-quarter rows and the requested event-quarter rows.

## Template: `model_validation` / `risk_ranking` / `cohort_checks`

- Read the train, validation, and candidate CSVs with the same header.
- `training_rows` and `validation_rows` are row counts.
- `feature_count` is all columns except `customer_id` and `Churn`.
- `accuracy_band` should be one of `below_70`, `70_to_79`, `80_to_89`, or `90_plus` based on validation accuracy.
- Rank only the requested candidates, descending by predicted churn probability.
- Compute `average_probability_top5` from the top five candidate probabilities.
- Set `outreach_action` from the dominant driver:
  - `collections_followup` for past due
  - `renewal_save` for low tenure or renewal pressure
  - `technical_recovery` for health or usage issues
  - `nurture_monitor` for low-risk cases
- Use the controlled `reason_code` that best matches the dominant driver.

## Policy codes

- When the template includes policy codes, fill each one with the single option that matches your method.
- Do not invent new codes or omit the field.
