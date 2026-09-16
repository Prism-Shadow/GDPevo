# ApexCloud Retention Ops Reference

## Source Rules

- Replace `<TASK_ENV_BASE_URL>` with the task base URL and use GET requests only.
- Account profile data comes from `/api/accounts` or `/api/accounts/{account_id}`.
- Monthly account metrics come from `/api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM`.
- Support health comes from `/api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`.
- NPS comes from `/api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`.
- Current ARR for dated analyses comes from `/api/billing/snapshots?as_of=YYYY-MM-DD`, not account `crm_arr` or profile ARR.
- Receivables come from `/api/finance/ar-aging?as_of=YYYY-MM-DD`; older overdue balance is `61_90 + 90_plus`.
- Pipeline comes from `/api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD`, filtered by close date by the API.
- HR and event context come from `/api/hr/summary?quarter=YYYY-QN` and `/api/events/performance?event=EVENT&quarter=YYYY-QN`.
- Churn work uses `/exports/churn/train.csv`, `/exports/churn/validation.csv`, and `/exports/churn/candidates.csv`.

## Cleaning And Precision

- A clean support ticket has `is_duplicate == false` and `is_spam == false`.
- For emitted `clean_ticket_count` totals, prefer `/exports/account_metric_extract.csv` `clean_ticket_count` by account/month when available; use ticket records as a fallback.
- Ticket-derived SLA compliance is the share of clean tickets where both `first_response_sla_met` and `resolution_sla_met` are true.
- Ignore retracted NPS responses. For a latest NPS field, use the most recent non-retracted response in the requested date range.
- Sort tied monthly maxima by first month encountered unless the prompt says otherwise.
- Round only final emitted values: currency to 2 decimals, percentages to 1 decimal, churn probabilities to 3 decimals.

## QBR Metrics Packets

For each requested month:

- `revenue`: `recognized_revenue` from account metrics.
- `support_tickets`: count clean support tickets created in that month.
- `sla_compliance_pct`: ticket-derived clean SLA percentage for that month.
- `nps_score`: non-retracted NPS score in that month, falling back to the monthly metric only when no response row exists.

Highlights:

- `average_revenue`: average monthly revenue.
- `peak_revenue_month` and `peak_revenue`: max monthly revenue.
- `max_sla_month` and `max_sla_pct`: max ticket-derived monthly SLA.
- `peak_nps_month` and `peak_nps_score`: max monthly NPS.
- `ticket_trend`: `improving` if last month clean tickets are lower than first month, `worsening` if higher, else `flat`.

Common source labels:

- revenue: `crm_closed_won`
- support tickets: `support_export`
- SLA compliance: `sla_report`
- NPS: `nps_survey`

Use `customer_success` as the default review owner. Set technical signoff only when current-period technical health is persistently poor or the prompt explicitly asks for it. Agenda topics usually start with `partnership_overview` and `q2_metrics`; include `technical_recovery` when SLA or NPS needs discussion, otherwise use `performance_highlights`, then close with the next-quarter initiative topic.

## Receivables And Pipeline Reviews

- Select A/R rows whose older overdue balance `61_90 + 90_plus` is greater than zero.
- Link an overdue customer to CRM only when `customer_name` exactly equals an account `legal_name`. Do not link by aliases, subsidiaries, or fuzzy names.
- Sort followups by `customer_name` ascending.
- `overdue_client_count`: count selected A/R rows.
- `overdue_total`: sum older overdue balance.
- `linked_followup_count` and `unlinked_followup_count`: counts by exact legal-name linkage.
- Pipeline `won_count`, `lost_count`, and `open_count` come from opportunity stage/state in the requested close-date window.
- `won_revenue` sums Closed Won amounts; `open_pipeline` sums open opportunity amounts.
- `win_rate_pct` is `won_count / (won_count + lost_count) * 100`.
- `top_open_product_line` is the product line with the largest open-pipeline amount; break ties by product-line name.
- HR context sums selected HR rows. For "all regions", sum all rows in the quarter.
- Event context uses the event row for the requested event and quarter.

Receivables policy codes:

- `receivable_trigger_code`: `RCP-7`
- `crm_match_code`: `CM-5`
- `pipeline_window_code`: `PW-6`
- `followup_scope_code`: `FS-4`

## Renewal Risk Queues And Retention Boards

Build one account fact row per requested account:

- Account profile: segment, region, lifecycle status, renewal date, contract tenure.
- ARR: billing snapshot `billing_arr` at the A/R or assessment as-of date.
- Support: clean ticket count and ticket-derived SLA percentage for the activity window.
- NPS: latest non-retracted score and prior non-retracted score in the window.
- Usage: first, last, and average product usage over the requested months.
- Receivables: older overdue balance `61_90 + 90_plus`.
- Expansion: sum open opportunity amounts in the requested opportunity window when the prompt asks for expansion or board exposure.

Reason-code rules:

- `renewal_window`: renewal date is on or after assessment date and within the next 90 days.
- `overdue_receivable`: older overdue balance is greater than zero.
- `low_tenure_high_churn`: contract tenure is less than 18 months.
- `sla_degradation`: ticket-derived clean SLA is below 90%.
- `nps_drop`: latest NPS is 40 or lower, or latest NPS is 50 or lower and has dropped at least 10 points from prior in-window sentiment.
- `usage_decline`: latest product usage is below 65 and below the first requested month, or latest product usage is below 65 and the current-period average is at least 3 points below the immediately prior period average.
- `expansion_offset`: open expansion pipeline exists and the prompt asks for pipeline/exposure context.
- `clean_billings`: no older overdue receivable exists.

Useful risk-score weights:

- renewal window: 25
- older overdue receivable: 20
- NPS drop: 15
- SLA degradation: 15
- usage decline: 10
- low tenure: 10
- lifecycle status `renewal_risk`: 5
- current ARR of at least 1,000,000: 5

Cap scores at 100. Risk levels: `critical` for 75+, `high` for 50-74, `medium` for 30-49, and `low` below 30.

Action priority:

- Use `collections_followup` when older overdue receivables exist and the account is not low/no-action scope.
- Use `technical_recovery` when SLA, NPS, or usage is the main problem and receivables are clean.
- Use `renewal_save` when renewal timing is the main problem and technical health is not the dominant issue.
- For paused lifecycle accounts in a renewal window with only mild SLA degradation, prefer `renewal_save` over `technical_recovery`.
- Use `executive_qbr` for strategic/high-ARR executive alignment when the prompt asks for QBR action.
- Use `nurture_monitor` for low active watchlist accounts.
- Use `no_action` for low-risk retention board rows when the template allows it.

Ranking:

- Risk queues: sort by risk score descending, then current ARR descending, then account ID.
- Retention boards: sort by risk level severity (`critical`, `high`, `medium`, `low`), then current ARR descending, then account ID.
- Board `arr_at_risk`: sum current ARR for rows whose primary action is not `no_action`.
- Board `open_expansion_pipeline`: sum open expansion pipeline for all included board rows.
- Board `net_revenue_exposure`: `arr_at_risk - open_expansion_pipeline`.

Risk and board policy codes:

- `risk_model_code`: `RS-6`
- `arr_source_code`: `REV-4`
- `support_hygiene_code`: `SUP-8`
- `action_priority_code`: `ACT-5`
- `board_sort_code`: `BORD-4`
- `exposure_formula_code`: `EXP-6`
- `calendar_policy_code`: `CAL-5`

## Churn Validation And Outreach

- `training_rows` and `validation_rows`: row counts from the CSV exports.
- `feature_count`: count raw feature columns excluding `customer_id` and `Churn`.
- `accuracy_pct`: use validation accuracy at a 0.5 cutoff. A conservative all-no baseline is acceptable when all model probabilities are below 0.5; compute it as validation non-churn rows divided by validation rows.
- `accuracy_band`: `below_70`, `70_to_79`, `80_to_89`, or `90_plus`.
- `tenure_coefficient_direction`: report `negative` when churned training rows have lower average tenure than retained rows or the fitted tenure coefficient is below zero.

For outreach ranking, restrict to the candidate IDs named in the prompt and sort by predicted churn probability descending. A portable heuristic should increase probability for low tenure, month-to-month contract, electronic check, missing tech support, high support tickets, low NPS, negative usage trend, low active-seat ratio, and invoice past due, while reducing probability for long tenure and two-year contracts.

Compute `past_due_shortlist_count`, `low_tenure_shortlist_count`, and average probability over the emitted top-ranked cohort unless the prompt says to count the full candidate list.

Outreach mapping:

- If the top reason is invoice past due, use `collections_followup` and `overdue_receivable`.
- Else if tenure is below 18 months, use `renewal_save` and `low_tenure_high_churn`.
- Else if support/SLA indicators dominate, use `technical_recovery` and `sla_degradation`.
- Else use `nurture_monitor` and `clean_billings`.

Churn policy codes:

- `model_protocol_code`: `MOD-7`
- `probability_scale_code`: `PRB-4`
- `deployment_rule_code`: `DEP-5`
- `outreach_mapping_code`: `OUT-2`
