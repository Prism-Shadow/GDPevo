---
name: apexcloud-retention-ops
description: Solve ApexCloud Retention Operations API tasks that ask for customer success, renewal risk, QBR metrics, receivables, pipeline, event/HR context, or churn-ranking JSON outputs. Use when a prompt references the ApexCloud Retention Operations API, account metrics, tickets, NPS, billing snapshots, A/R aging, opportunities, HR summaries, event performance, churn CSV exports, or controlled retention policy/action codes.
---

# ApexCloud Retention Ops

Use this skill to produce deterministic JSON answers from the ApexCloud Retention Operations API.

## Operating Rules

1. Read the task prompt and `input/payloads/answer_template.json` first. The template is authoritative for keys, enum vocabulary, nullability, and top-level objects.
2. Replace `<TASK_ENV_BASE_URL>` with the base URL supplied by the task environment. Use only public GET endpoints mentioned by the prompt or environment access file. Never call judge or POST endpoints.
3. Fetch source data, then filter client-side. Some documented per-account endpoint families may be exposed as global collection endpoints instead; tolerate `not_found` and use the collection endpoint.
4. Return JSON only. Preserve the template shape exactly, omit no required keys, and use controlled enum strings exactly as shown.
5. Round only at output boundaries: currency to 2 decimals, percentages to 1 decimal, risk scores/counts as integers, and churn probabilities to 3 decimals.

## Source Mapping

- Accounts: `/api/accounts` and `/api/accounts/{account_id}` for legal names, segment, region, lifecycle, tenure, and renewal date.
- Monthly metrics: `/api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM` for recognized revenue, usage, seats, and metric context.
- Tickets: `/api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`.
- NPS: `/api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`.
- Billing ARR: `/api/billing/snapshots?as_of=YYYY-MM-DD`; filter posted snapshots by account and as-of date.
- Receivables: `/api/finance/ar-aging?as_of=YYYY-MM-DD`.
- Opportunities: `/api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD`; filter by close date, state, account, region, or product line as requested.
- HR: `/api/hr/summary?quarter=YYYY-QN`; sum regions unless the prompt narrows scope.
- Events: `/api/events/performance?event=<event_id>&quarter=YYYY-QN`.
- Churn exports: `/exports/churn/train.csv`, `/exports/churn/validation.csv`, `/exports/churn/candidates.csv`.
- Monthly extract: `/exports/account_metric_extract.csv` can cross-check cleaned monthly counts, but prefer live API records when prompt requests reconciliation.

## Common Definitions

- Clean ticket: exclude tickets where `is_duplicate` or `is_spam` is true, and exclude `status == "cancelled"`. Include open and closed tickets.
- Clean ticket count: count clean tickets in the requested date range. For monthly packets, bucket by `created_date` month.
- SLA compliance percent: among clean tickets, percentage where both `first_response_sla_met` and `resolution_sla_met` are true. If no clean tickets exist, use `100.0` unless the template or prompt implies null/zero.
- SLA degradation reason: any clean ticket in the analysis period missed first response or resolution SLA.
- NPS score: exclude retracted responses. Use the latest response by `response_date` for latest-NPS fields; for monthly packets, use that month's latest non-retracted response or `null`.
- NPS drop reason: latest NPS is below 40, or the first-to-latest non-retracted score drop is at least 10 points.
- Current ARR: use the posted billing snapshot on the requested as-of date. This is the REV-4 billing ARR source; do not use account `crm_arr` or account-level current ARR when a billing snapshot exists.
- Overdue balance: `61_90 + 90_plus` from A/R aging. Use only these older aging buckets for overdue triggers and receivables followups.
- Clean billings reason: overdue balance is exactly zero.
- Renewal window reason: renewal date is on or after the assessment/as-of date and no more than 90 days later.
- Usage decline reason: latest analysis-period product usage is below 65.0. If a prompt explicitly asks for trend rather than risk reasons, compare first and last period values.
- Low tenure high churn reason: account tenure is 18 months or less, or churn CSV tenure is 18 or less.
- Expansion pipeline: sum open opportunities whose close dates fall inside the requested period. Expansion is an offset/context reason, not a receivables trigger.

## Risk Queues

For renewal risk queues or retention boards, compute reason flags first, then score:

- `renewal_window`: +20
- `overdue_receivable`: +25
- `nps_drop`: +15
- `sla_degradation`: +15
- `usage_decline`: +10
- `low_tenure_high_churn`: +10
- Add +5 for `segment == "Strategic"`.
- Add +5 for `lifecycle_status == "renewal_risk"`.
- Cap `risk_score` at 100.

Risk levels:

- `critical`: score >= 70
- `high`: score >= 50
- `medium`: score >= 30
- `low`: score < 30

Reason code ordering:

`renewal_window`, `overdue_receivable`, `nps_drop`, `sla_degradation`, `usage_decline`, `low_tenure_high_churn`, `expansion_offset`, `clean_billings`.

Use `expansion_offset` when open expansion pipeline exists and the output asks for expansion context or the account has meaningful open expansion against its ARR. Use `clean_billings` when overdue balance is zero and the template includes reason codes.

Primary action priority:

1. `collections_followup` when `overdue_receivable` is present.
2. `renewal_save` when low tenure or renewal timing is the dominant non-collections risk.
3. `technical_recovery` when SLA, NPS, or usage health is the dominant risk.
4. `nurture_monitor` for low-risk monitoring when the enum supports it.
5. `no_action` for low-risk board rows when the enum supports it and the prompt asks for an action board.

Queue ordering:

- For "top N ranked accounts", sort by `risk_score` descending, then current ARR descending, then `account_id`.
- For a standard retention action board, sort by risk level severity, then current ARR descending within each level. Include all requested accounts unless the prompt asks for a top N subset.

Portfolio/segment summaries:

- `critical_or_high_count`: count rows with risk level `critical` or `high`.
- Risk queue `arr_at_risk`: sum current ARR for `critical` and `high` rows.
- Action board `arr_at_risk`: sum current ARR for all non-low rows.
- `collections_count`: count rows whose primary action is `collections_followup`.
- `technical_recovery_count`: count rows whose primary action is `technical_recovery`.
- `open_expansion_pipeline`: sum open expansion pipeline for all included board accounts.
- `net_revenue_exposure`: `arr_at_risk - open_expansion_pipeline`.

Risk policy codes:

- `risk_model_code`: `RS-6`
- `arr_source_code`: `REV-4`
- `support_hygiene_code`: `SUP-8`
- `action_priority_code`: `ACT-5`
- Board-specific: `board_sort_code` = `BORD-4`, `exposure_formula_code` = `EXP-6`, `calendar_policy_code` = `CAL-5`

## QBR Metric Packets

For each requested month:

- `revenue`: monthly `recognized_revenue` from account metrics.
- `support_tickets`: clean tickets created in that month.
- `sla_compliance_pct`: clean-ticket SLA compliance for that month.
- `nps_score`: latest non-retracted NPS response in that month, or `null`.

Highlights:

- Average revenue is the arithmetic mean of monthly revenue.
- Peak revenue/NPS/SLA months use the earliest month on ties.
- `ticket_trend` is `improving` if final-month clean ticket count is lower than first-month count, `worsening` if higher, else `flat`.

Metric source enums:

- revenue: `crm_closed_won`
- support_tickets: `support_export`
- sla_compliance: `sla_report`
- nps: `nps_survey`

Review plan and agenda:

- Default `review_owner` to `customer_success`.
- Set `needs_technical_signoff` true only when sustained technical health is poor, such as average SLA below 90.0 or repeated severe SLA misses.
- Use four agenda topics. A reliable order is `partnership_overview`, metrics topic for the period, one focus topic (`technical_recovery` if ticket/SLA health needs discussion, `commercial_expansion` if expansion dominates, otherwise `performance_highlights`), then next-period initiatives.

## Receivables And Pipeline Reviews

Receivable trigger:

- Include A/R rows whose `61_90 + 90_plus` is greater than zero.
- `overdue_total` is the sum of those older buckets only.
- Match A/R customer names to CRM accounts by exact `legal_name`; do not link aliases, subsidiaries, similarly named noise records, or fuzzy matches.
- `link_status` is `linked` only on exact legal-name match; otherwise `unlinked` and `account_id: null`.
- Sort `overdue_followups` by `customer_name` ascending.
- Use `collections_followup` for receivables followup actions.

Pipeline summary:

- Filter opportunities by requested close-date window and requested region scope.
- `won_count`/`won_revenue`: closed opportunities with `stage == "Closed Won"`.
- `lost_count`: closed opportunities with `stage == "Closed Lost"`.
- `open_count`/`open_pipeline`: opportunities with `state == "open"`.
- `win_rate_pct`: `won_count / (won_count + lost_count) * 100`.
- `top_open_product_line`: product line with the largest summed open amount; break ties alphabetically.

Ops context:

- Sum HR `headcount` and `unpaid_claims_amount` across requested regions.
- Use event `event_orders` and `event_revenue` directly for the requested event/quarter.

Receivables policy codes:

- `receivable_trigger_code`: `RCP-7`
- `crm_match_code`: `CM-5`
- `pipeline_window_code`: `PW-6`
- `followup_scope_code`: `FS-4`

## Churn Validation And Candidate Ranking

Use the churn CSV exports as a modeling task, not as account operational metrics.

Validation fields:

- `training_rows`: count rows in `train.csv`.
- `validation_rows`: count rows in `validation.csv`.
- `feature_count`: count input columns excluding `customer_id` and `Churn`.
- `accuracy_pct`: train a binary churn classifier on `train.csv`, predict `validation.csv`, and compute accuracy at threshold 0.5.
- `accuracy_band`: `below_70`, `70_to_79`, `80_to_89`, or `90_plus`.
- `tenure_coefficient_direction`: direction of the fitted tenure coefficient.

Modeling procedure:

1. Treat `Churn == "Yes"` as 1 and `"No"` as 0.
2. Use all 19 features. Standardize numeric features and one-hot encode categoricals.
3. Prefer deterministic logistic regression with L2 regularization and a fixed solver. If no ML library exists, implement ridge logistic regression with Newton or batch gradient descent in standard Python.
4. Rank only the candidate IDs requested in the prompt by unrounded predicted probability, then output the top N requested by the template/prompt.
5. Round displayed `predicted_churn_probability` to 3 decimals after sorting.

Churn cohort checks:

- `past_due_shortlist_count`: top-ranked output rows whose candidate CSV `InvoicePastDue` is `Yes`.
- `low_tenure_shortlist_count`: top-ranked output rows whose tenure is 18 or less.
- `average_probability_top5`: arithmetic mean of displayed or equivalently rounded top-5 probabilities, to 3 decimals.

Outreach mapping:

- Invoice past due or operational overdue evidence: `collections_followup`, reason `overdue_receivable`.
- Tenure <= 18 or month-to-month high-risk profile: `renewal_save`, reason `low_tenure_high_churn`.
- SLA/support/usage technical weakness: `technical_recovery`, reason `sla_degradation`, `nps_drop`, or `usage_decline`, whichever is strongest.
- Otherwise: `nurture_monitor`, reason `clean_billings`.

Churn policy codes:

- `model_protocol_code`: `MOD-7`
- `probability_scale_code`: `PRB-4`
- `deployment_rule_code`: `DEP-5`
- `outreach_mapping_code`: `OUT-2`
