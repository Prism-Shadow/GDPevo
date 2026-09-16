---
name: apexcloud-retention-ops
description: Solve ApexCloud Retention Operations API tasks that require customer success, billing, receivables, pipeline, event, HR, or churn-export analysis and JSON-only business outputs.
---

# ApexCloud Retention Ops

Use this skill when a task asks for an ApexCloud Retention Operations API analysis and a structured JSON answer. Treat the prompt and `input/payloads/answer_template.json` as the contract. Compute from the live API at the supplied `<TASK_ENV_BASE_URL>`; never reuse staged example answers or hard-code account-specific results.

## One-Pass Solver Flow

1. Read the prompt, extract the requested account IDs, dates, months, quarter, region/event filters, due dates, ranking size, enum vocabularies, and required top-level JSON shape.
2. Query only the public GET endpoints named in the task or needed for the requested fields. Prefer a small local script using standard-library `urllib`, `json`, `csv`, `datetime`, and `decimal` so calculations are repeatable.
3. Build normalized records first, then fill the answer template exactly. Omit any template-only keys that the prompt excludes, but include required policy/model code blocks when present in the template.
4. Return JSON only. Use numbers, booleans, and nulls as JSON values, not strings.

## Endpoint Guide

Use these endpoint families by data need:

- Account profile: `/api/accounts`, `/api/accounts/{account_id}`.
- Monthly account metrics: `/api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM`.
- Support tickets: `/api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`.
- NPS: `/api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`.
- Billing ARR snapshots: `/api/billing/snapshots`; filter client-side by `account_id` and `as_of`.
- A/R aging: `/api/finance/ar-aging?as_of=YYYY-MM-DD`; filter client-side by customer/account.
- Opportunities: `/api/opportunities`; filter client-side by `close_date`, `state`, `stage`, account, and region. Query parameters may not narrow this collection.
- HR: `/api/hr/summary?quarter=YYYY-QN`, then filter or aggregate region as requested.
- Events: `/api/events/performance?event=<event_id>&quarter=YYYY-QN`.
- Churn exports: `/exports/churn/train.csv`, `/exports/churn/validation.csv`, `/exports/churn/candidates.csv`.
- Account metric extract: `/exports/account_metric_extract.csv` when a prompt asks for export-style monthly account metrics.

Prefer collection billing and A/R endpoints over account-scoped billing/A/R endpoints; in this environment the collection endpoints are the reliable source.

## Source Rules

- `current_arr`: use the posted billing snapshot `billing_arr` at the assessment or A/R as-of date. If there is no exact match, use the latest posted snapshot on or before that date; only then fall back to account profile ARR. Set `uses_billing_arr_source` to `true` when billing snapshots drive ARR.
- `overdue_balance`: for risk, follow-up, and collections work, use only older A/R buckets: `61_90 + 90_plus`. Do not include `current`, `1_30`, or `31_60`.
- CRM receivables linking: link an A/R customer to an account only on exact `customer_name == account.legal_name`. Treat subsidiaries, foundations, claims entities, alternate spellings, and aliases as unlinked unless the prompt explicitly authorizes fuzzy matching.
- Clean support tickets: exclude tickets where `is_duplicate` or `is_spam` is true. `clean_ticket_count` is this filtered count.
- SLA compliance from tickets: percentage of clean tickets where both `first_response_sla_met` and `resolution_sla_met` are true. Do not use summary metric `sla_compliance` when ticket-level records are available.
- NPS: ignore retracted responses. For `latest_nps`, use the newest non-retracted response in the date range. For monthly packets, group non-retracted responses by response month and use the month’s response score; if multiple exist, use the latest in that month unless the prompt asks for an average.
- Monthly revenue: use `recognized_revenue` from account metrics unless the prompt explicitly asks for billing ARR/MRR.
- Expansion pipeline: sum opportunity `amount` for `state == "open"` opportunities whose `close_date` is inside the prompt’s date range. Use the same close-date window for pipeline summaries.

## Retention Risk Queues And Boards

Build one feature row per requested account:

- Profile: segment, lifecycle status, tenure, renewal date.
- Current ARR from billing snapshot.
- Older A/R overdue balance.
- Clean ticket count and clean-ticket SLA percentage.
- Latest NPS and period NPS high.
- Latest product usage and usage trend from monthly metrics.
- Open expansion pipeline in the prompt’s close-date window when expansion is in scope.

Use this reusable additive risk model unless the prompt supplies another model:

| Factor | Trigger | Points |
| --- | --- | ---: |
| `renewal_window` | renewal date is on/after the as-of date and within the next 90 days | 25 |
| `overdue_receivable` | older A/R buckets total is greater than 0 | 20 |
| `nps_drop` | latest NPS is below 40, or period high minus latest is at least 10 and latest is below 50 | 15 |
| `sla_degradation` | clean-ticket SLA percentage is below 90.0 | 15 |
| `usage_decline` | latest product usage is below 65, or an export-only usage trend is materially negative | 10 |
| `low_tenure_high_churn` | contract tenure is 18 months or less | 10 |
| lifecycle uplift | `lifecycle_status` is `renewal_risk` | 5 |
| high revenue exposure uplift | billing ARR is at least 1,000,000 | 5 |

Cap `risk_score` at 100. Map levels as: `critical` for scores >= 70, `high` for 50-69, `medium` for 25-49, and `low` for below 25.

Reason codes should be controlled enum values and ordered by business priority:

`renewal_window`, `overdue_receivable`, `nps_drop`, `sla_degradation`, `usage_decline`, `low_tenure_high_churn`, `expansion_offset`, `clean_billings`.

Include `expansion_offset` when the output explicitly includes expansion pipeline or net exposure and the account has open expansion pipeline. In simpler rank-only queues, include it only when it is salient context; do not let it change the risk score. Include `clean_billings` for accounts with no older-bucket overdue balance when the template expects billing hygiene context.

Sort boards and risk queues by descending `risk_score`, then descending current ARR, then `account_id`. For top-N queues, return exactly the requested count. For standard action boards, return every requested account in this order.

Primary action policy:

- `collections_followup` if `overdue_receivable` is present.
- `technical_recovery` if technical health dominates: `nps_drop`, severe SLA degradation, or low/latest usage is present.
- `renewal_save` if renewal timing is the main risk and collections does not apply.
- `executive_qbr` for critical high-ARR accounts when executive alignment is more central than collections or technical recovery.
- `nurture_monitor` for low-risk watchlist accounts.
- `no_action` only when the prompt/template permits it, usually for low-risk full-board rows.

Portfolio/segment summaries:

- `accounts_reviewed`: count requested accounts reviewed.
- `critical_or_high_count`: count accounts with risk level critical or high.
- `arr_at_risk`: sum current ARR for critical/high accounts in queues; for full action boards, sum current ARR for non-low accounts.
- `collections_count`, `technical_recovery_count`: count rows whose primary action matches.
- Segment counts come from account profile `segment`.
- `open_expansion_pipeline`: sum open expansion pipeline for all included board accounts.
- `net_revenue_exposure`: `arr_at_risk - open_expansion_pipeline`.
- Follow-up calendars use the due dates specified in the prompt by action.

## QBR Metrics Packets

For each requested month:

- `revenue`: account metric `recognized_revenue`.
- `support_tickets`: clean ticket count in that month.
- `sla_compliance_pct`: clean-ticket SLA percentage for that month.
- `nps_score`: non-retracted NPS score for that month, or `null` if none.

Highlights:

- `average_revenue`: arithmetic mean of monthly revenue.
- Peak revenue, max SLA, and peak NPS use the earliest month as the tie-breaker.
- `ticket_trend`: compare first and last monthly clean ticket counts: last lower is `improving`, higher is `worsening`, equal is `flat`.
- Metric source enums normally map to `crm_closed_won` for revenue, `support_export` for support tickets, `sla_report` for SLA, and `nps_survey` for NPS.
- `review_owner` is usually `customer_success` for QBR packets. Use `solutions_engineering` only when the packet is primarily a technical recovery handoff, and `finance_ops` only when finance/billing owns the review.
- Agenda topics should stay in deck order: relationship overview, period metrics, the most important risk/opportunity topic, then next-period initiatives.

## Receivables, Pipeline, HR, And Event Ops Reviews

For receivables follow-ups:

- Start from A/R rows whose `61_90 + 90_plus > 0`.
- `overdue_client_count` is the number of those rows.
- `overdue_total` is the sum of those older buckets.
- Link using exact legal-name matching only.
- Sort `overdue_followups` by `customer_name` ascending.
- `primary_action` is `collections_followup`; due date comes from the prompt.

For pipeline summaries:

- Filter opportunities by `close_date` inside the prompt date range, and by region if requested.
- `won_count` and `won_revenue`: `stage == "Closed Won"`.
- `lost_count`: `stage == "Closed Lost"`.
- `open_count` and `open_pipeline`: `state == "open"`.
- `win_rate_pct`: `won_count / (won_count + lost_count) * 100`; use 0.0 if there are no closed won/lost opportunities.
- `top_open_product_line`: product line with the largest summed open amount, tie-breaking alphabetically.

For ops context, aggregate the requested quarter and region scope:

- HR headcount: sum `headcount`.
- Unpaid claims: sum `unpaid_claims_amount`.
- Event orders/revenue: use the matching event-quarter record’s `event_orders` and `event_revenue`.

## Churn Export Validation And Outreach Ranking

Use the three churn CSV exports as a self-contained modeling dataset:

1. `training_rows` and `validation_rows` are CSV row counts.
2. `feature_count` is the number of original predictor columns, excluding `customer_id` and label `Churn`.
3. Train a deterministic binary classifier on `train.csv`, validate against `validation.csv`, and rank only the candidate IDs requested in the prompt. A portable default is L2-regularized logistic regression with standardized numeric predictors and deterministic encoding of categoricals from training-set categories. Use no class weighting unless the prompt asks for it.
4. Compute validation accuracy at threshold 0.5 and map bands: below 70, 70-79, 80-89, 90+.
5. Churn probabilities are fractions from 0 to 1, not percentages. Round to 3 decimals and sort descending, tie-breaking by candidate ID.
6. `tenure_coefficient_direction` should be `negative` when increasing tenure reduces churn risk.

Outreach mapping for ranked candidates:

- If the candidate has `InvoicePastDue == "Yes"` or other past-due evidence, use `collections_followup` with `overdue_receivable`.
- Else if tenure is 18 months or less and probability is elevated, use `renewal_save` with `low_tenure_high_churn`.
- Else if support tickets are high or SLA/support health is poor, use `technical_recovery` with `sla_degradation`.
- Else if NPS is low or falling, use `technical_recovery` with `nps_drop`.
- Else if usage trend is negative, use `technical_recovery` with `usage_decline`.
- Otherwise use `nurture_monitor` with `clean_billings`.

Cohort checks are computed on the returned top five unless the prompt says otherwise: count past-due rows, count tenure <= 18 rows, and average returned probabilities.

## Policy Code Selection

When templates ask for policy/model codes and the prompt does not define alternatives, use the code matching the rules applied:

- Risk model: `RS-6` for the additive renewal-risk model above.
- ARR source: `REV-4` for billing snapshot ARR.
- Support hygiene: `SUP-8` for duplicate/spam-excluded clean tickets and ticket-level SLA.
- Action priority: `ACT-5` for collections first, then technical recovery, then renewal/nurture.
- Receivable trigger: `RCP-7` for older A/R buckets only.
- CRM match: `CM-5` for exact legal-name matching.
- Pipeline window: `PW-6` for close-date window filtering.
- Follow-up scope: `FS-4` for every older-bucket overdue customer.
- Board sort: `BORD-4` for risk score then ARR.
- Exposure formula: `EXP-6` for ARR at risk minus open expansion pipeline.
- Calendar policy: `CAL-5` for prompt-specified action due dates.
- Churn protocol: `MOD-7` for train/validate CSV modeling.
- Probability scale: `PRB-4` for 0-1 probabilities rounded to 3 decimals.
- Deployment rule: `DEP-5` for ranking only requested candidates.
- Outreach mapping: `OUT-2` for the outreach action rules above.

## Precision And JSON Hygiene

- Currency: round to 2 decimals.
- Percentages: round to 1 decimal.
- Risk scores and counts: integers.
- Churn probabilities: round to 3 decimals.
- Preserve account IDs, customer names, enum labels, dates, and key order from the requested template.
- Use `null` only where the template or missing data calls for it; otherwise use zero values of the correct type.
- Before final output, assert list lengths, sort order, required keys, enum membership, and rounding.
