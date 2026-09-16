# Report Playbook

## Common sources
- `/api/accounts`: profile, region, segment, tenure, renewal date, lifecycle status, billing ARR, CRM ARR, owner, aliases, and legal name.
- `/api/accounts/{id}/metrics?start=YYYY-MM&end=YYYY-MM`: monthly revenue, support tickets, SLA compliance, NPS, product usage, and active seats.
- `/api/accounts/{id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`: ticket hygiene and escalation detail. Count clean tickets by excluding `is_spam=true` and `status=cancelled`.
- `/api/accounts/{id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`: raw NPS responses when the prompt needs response-level detail.
- `/api/billing/snapshots`: posted billing ARR and MRR by as-of date.
- `/api/finance/ar-aging`: customer-level A/R buckets. Use `61_90 + 90_plus` as overdue balance.
- `/api/opportunities`: pipeline rows with state, amount, close date, region, and product line.
- `/api/hr/summary`: quarterly headcount and unpaid claims by region.
- `/api/events/performance`: quarterly event metrics by `event_id`.
- `/exports/churn/train.csv`, `/exports/churn/validation.csv`, `/exports/churn/candidates.csv`: churn model inputs.

## Renewal risk queue
- Filter to the prompt's account_ids only.
- Use posted billing ARR for `current_arr` when available at the assessment date.
- Use latest monthly NPS, ticket count, SLA, usage trend, overdue balance, tenure, and lifecycle signals.
- Map the primary action to the dominant issue: `collections_followup` for overdue receivables, `technical_recovery` for support/SLA or usage degradation, `renewal_save` for renewal-window pressure, `executive_qbr` for strategic escalation, `nurture_monitor` for low-severity exposure, and `no_action` only when the prompt allows it.
- Rank by combined renewal risk and return exactly the requested top accounts.
- Set `portfolio_summary.arr_at_risk` to the sum of `current_arr` for the accounts classified as `critical` or `high`.
- Set `critical_or_high_count` to the number of `critical` and `high` rows.
- Set `collections_count` and `technical_recovery_count` from the chosen `primary_action` values.
- Set `model_checks.uses_billing_arr_source` true when posted billing drives current ARR.
- Set `tenure_risk_direction` to `negative` when shorter tenure increases risk.

## QBR metrics packet
- Build one row per month in chronological order.
- Use the monthly metrics endpoint for revenue, support tickets, SLA compliance, and NPS.
- Compute `average_revenue` as the arithmetic mean of the monthly revenue values.
- Set each `peak_*` field to the month and value with the maximum reading in the quarter.
- Set `ticket_trend` to `improving`, `worsening`, or `flat` from the quarterly ticket sequence.
- Map `metric_sources` to `crm_closed_won`, `support_export`, `sla_report`, and `nps_survey`.
- Set `review_owner` to `customer_success` for standard client-ready reviews, `solutions_engineering` when the packet is support-led, and `finance_ops` when billing is the main discussion.
- Choose four agenda topics that fit the narrative and keep them ordered from context to action.
- Set `needs_technical_signoff` true when the agenda depends on a support, SLA, or product-recovery discussion.

## Receivables and pipeline review
- Build overdue followups from A/R rows with older-bucket balances.
- Match `customer_name` to an account by legal name, display name, or alias before assigning `account_id`.
- Sort `overdue_followups` by `customer_name` ascending.
- Set `link_status` to `linked` only when the match is explicit.
- Compute `win_rate_pct` as `won_count / (won_count + lost_count) * 100`.
- Set `top_open_product_line` to the open product line with the largest total open pipeline amount.
- Set `financial_summary.overdue_total` to the sum of overdue balances and the linked/unlinked counts from the followup list.
- Sum HR headcount and unpaid claims across all regions for the requested quarter.
- Pull the matching event row for the requested event and quarter.

## Churn validation and ranking
- Treat `customer_id` and `Churn` as non-features.
- Keep preprocessing identical across train, validation, and candidates.
- Report `feature_count` as the number of source columns used after dropping `customer_id` and `Churn`.
- Validate a deterministic binary classifier, then rank only the prompted candidate accounts by predicted churn probability.
- Report the sign of the fitted tenure coefficient.
- Count shortlist members with past-due invoices and members in the low-tenure cohort from the shortlisted set only.
- Set `average_probability_top5` to the mean of the five shortlisted probabilities.

## Retention action board
- Sort by risk severity first, then current ARR descending.
- Map `next_touch_due_date` from the prompt's action calendar.
- Set `arr_at_risk` to the sum of `current_arr` for rows above `low` severity.
- Set `open_expansion_pipeline` to the sum of `expansion_pipeline`.
- Set `net_revenue_exposure` to `arr_at_risk - open_expansion_pipeline`.
- Count strategic and enterprise accounts from the account metadata.
