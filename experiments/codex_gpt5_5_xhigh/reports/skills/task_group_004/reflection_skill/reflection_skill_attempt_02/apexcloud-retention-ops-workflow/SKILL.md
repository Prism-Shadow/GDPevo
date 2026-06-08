---
name: apexcloud-retention-ops-workflow
description: Use this skill for ApexCloud Retention Operations API tasks that ask for renewal risk queues, retention action boards, QBR metric packets, receivables and pipeline reviews, or churn validation/ranking JSON. It should trigger whenever a prompt mentions ApexCloud, account metrics, billing snapshots, A/R aging, support tickets, NPS, opportunities, churn exports, policy codes, retention risk, QBR packets, or revenue operations summaries.
---

# ApexCloud Retention Operations Workflow

Use this skill to produce deterministic JSON answers from the ApexCloud Retention Operations public API. Treat the task prompt and answer template as the contract: preserve the exact top-level keys, enum labels, ordering requirements, precision rules, and nullable fields requested there.

## Standard Procedure

1. Read only the task prompt and the answer template before solving. Do not rely on notes, evaluation scripts, prior answers, or unrelated task files.
2. Use the API base URL specified by the active instruction. If the task text mentions another port but the workflow instruction provides a shared API base, use the shared API base.
3. Fetch only the endpoint families needed for the requested date range, account list, quarter, event, or churn exports.
4. Build intermediate tables for accounts, billing snapshots, tickets, NPS, A/R rows, opportunities, HR summaries, and event summaries. Join by `account_id` where available and by exact legal/customer name only when the task explicitly starts from finance customer rows.
5. Compute values from source rows rather than copying precomputed-looking fields when the task asks for cleaned operational metrics.
6. Return JSON only. Use numbers, booleans, nulls, arrays, and enum strings exactly as the template implies.

## API Map

Common endpoints:

- `/api/accounts`
- `/api/accounts/<account_id>`
- `/api/accounts/<account_id>/metrics?start=YYYY-MM&end=YYYY-MM`
- `/api/accounts/<account_id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`
- `/api/accounts/<account_id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`
- `/api/billing/snapshots?as_of=YYYY-MM-DD`
- `/api/billing/snapshots?account_id=<account_id>&as_of=YYYY-MM-DD`
- `/api/finance/ar-aging?as_of=YYYY-MM-DD`
- `/api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD`
- `/api/hr/summary?quarter=YYYY-QN`
- `/api/events/performance?event=<event_id>&quarter=YYYY-QN`
- `/exports/churn/train.csv`
- `/exports/churn/validation.csv`
- `/exports/churn/candidates.csv`

## Field Definitions

- Current ARR: use `billing_snapshot.billing_arr` from `/api/billing/snapshots`; do not use `crm_arr` or account-level `billing_arr_current` when the billing snapshot is available. This corresponds to policy code `REV-4`.
- Monthly revenue: use `recognized_revenue` from account metrics for QBR monthly rows. For QBR source enums, classify revenue as `crm_closed_won`.
- Clean support ticket: a ticket where `is_duplicate` is false, `is_spam` is false, and `status` is not `cancelled`. Keep open tickets unless the prompt explicitly says closed/resolved only.
- Support ticket count: for QBR packets, group clean tickets by `created_date` month. For risk queues/boards, count clean tickets over the whole analysis period.
- SLA compliance percentage: compute from clean ticket rows as the percent where both `first_response_sla_met` and `resolution_sla_met` are true. Do not use the account metrics `sla_compliance` field for final QBR SLA.
- Latest NPS: use the latest non-retracted response from `/nps` in the period. Fall back to non-null monthly metric NPS only if the NPS endpoint lacks usable responses.
- A/R overdue balance: use only the older aging buckets, `61_90 + 90_plus`. Do not include `1_30` or `31_60` in output `overdue_balance`.
- Clean billings: use `clean_billings` when the older aging bucket balance is zero, even if short aging buckets have balances.
- Open expansion pipeline: sum opportunities with `state: "open"` in the requested close-date window for the relevant account set.

## Risk Queues And Boards

Build one fact row per requested account:

- Account profile: region, segment, lifecycle status, renewal date, tenure.
- Current ARR from billing snapshot.
- Clean ticket count and SLA misses from ticket rows.
- Latest NPS and NPS trend from non-retracted NPS responses.
- Product usage trend from monthly account metrics.
- Older A/R balance from `61_90 + 90_plus`.
- Open expansion pipeline from opportunities in the requested period.

Reason-code rules:

- `renewal_window`: renewal is in the task's review window or close enough to the assessment date to require save planning.
- `overdue_receivable`: older A/R balance is greater than zero.
- `nps_drop`: latest NPS is very low, or the period shows a sharp negative NPS movement.
- `sla_degradation`: clean ticket volume, SLA misses, or computed SLA compliance indicates support health risk.
- `usage_decline`: usage is low or trending down materially in the period.
- `low_tenure_high_churn`: tenure is low enough to raise churn risk, commonly around the first 12 to 18 months.
- `expansion_offset`: material open expansion pipeline should be included in exposure context.
- `clean_billings`: older A/R balance is zero.

Action priority:

- Use `collections_followup` when older A/R is present.
- Use `technical_recovery` when support, SLA, NPS, or usage issues dominate.
- Use `renewal_save` for renewal-window accounts without a stronger collections or technical driver.
- Use `executive_qbr` for high-ARR strategic leadership alignment when the prompt calls for executive handling.
- Use `nurture_monitor` or `no_action` only for low-risk accounts when the template permits them. For `no_action`, set the next touch date to `null`.

Risk summaries:

- `critical_or_high_count` counts reviewed accounts whose risk level is critical or high.
- In risk queues, `arr_at_risk` should follow the summary label; for a critical/high summary, sum current ARR for critical and high accounts only.
- In action boards, `arr_at_risk` is the actionable exposure: usually critical, high, and medium accounts, excluding low/no-action accounts.
- `open_expansion_pipeline` is the sum of open expansion across the board/account set. `net_revenue_exposure` is `arr_at_risk - open_expansion_pipeline`.
- `collections_count` and `technical_recovery_count` count returned action rows using those primary actions.

Observed stable policy codes for risk/board work:

- `risk_model_code`: `RS-6`
- `arr_source_code`: `REV-4`
- `support_hygiene_code`: `SUP-8`
- `action_priority_code`: `ACT-5`
- `board_sort_code`: `BORD-4`
- `exposure_formula_code`: `EXP-6`
- `calendar_policy_code`: `CAL-5`

## QBR Metric Packets

For each requested month:

- `revenue`: monthly `recognized_revenue` from account metrics.
- `support_tickets`: monthly clean ticket count by ticket `created_date`.
- `sla_compliance_pct`: computed clean-ticket SLA percentage, rounded to 1 decimal.
- `nps_score`: monthly NPS score from metrics or NPS response for that month.

Highlights:

- Average revenue is the arithmetic average of monthly revenue.
- Peak revenue, max SLA, and peak NPS choose the first month in chronological order if tied.
- `ticket_trend` is `improving` when final-month clean ticket count is lower than first-month count, `worsening` when higher, otherwise `flat`.
- Use source enums: `crm_closed_won`, `support_export`, `sla_report`, and `nps_survey`.
- Include `technical_recovery` as an agenda topic when support/SLA health deserves discussion, even when `needs_technical_signoff` remains false.

## Receivables And Pipeline Reviews

When a task starts from A/R customers with older overdue balances:

1. Fetch A/R aging for the as-of date and keep rows where `61_90 + 90_plus > 0`.
2. Set `overdue_balance` to that older-bucket sum.
3. Link to CRM only on exact `customer_name == account.legal_name`; similar names, subsidiaries, foundations, or claims entities remain `unlinked` with `account_id: null`.
4. Sort follow-ups by `customer_name` ascending.
5. Use `collections_followup` for every receivables follow-up unless the prompt says otherwise.

Pipeline summary:

- Use opportunities whose close dates fall in the requested quarter/window.
- `won_count`: opportunities with `stage: "Closed Won"`.
- `won_revenue`: sum of Closed Won `amount`.
- `lost_count`: opportunities with `stage: "Closed Lost"`.
- `open_count`: opportunities with `state: "open"`.
- `open_pipeline`: sum of open opportunity `amount`.
- `win_rate_pct`: `won_count / (won_count + lost_count) * 100`.
- `top_open_product_line`: product line with the largest summed open pipeline.

Operations context:

- Sum HR headcount and unpaid claims across all requested regions.
- Use event order and revenue fields directly for the requested event and quarter.

Observed stable policy codes:

- `receivable_trigger_code`: `RCP-7`
- `crm_match_code`: `CM-5`
- `pipeline_window_code`: `PW-6`
- `followup_scope_code`: `FS-4`

## Churn Validation And Candidate Ranking

Use the three churn CSV exports:

- Training rows come from `train.csv`.
- Validation rows come from `validation.csv`.
- Candidate scores come from `candidates.csv`; rank only the task's requested candidate IDs.

Modeling procedure:

1. Treat `customer_id` as an identifier and `Churn` as the label.
2. `feature_count` is the number of source feature columns excluding `customer_id` and `Churn`.
3. Encode categorical columns consistently from training data; standardize numeric columns.
4. Train a deterministic binary classifier such as logistic regression on `train.csv`.
5. Compute validation accuracy on `validation.csv`; report percentage to 1 decimal and band as `below_70`, `70_to_79`, `80_to_89`, or `90_plus`.
6. Report `tenure_coefficient_direction` from the trained tenure coefficient.
7. Predict requested candidates, sort by probability descending, and return the top 5.

Candidate outreach mapping:

- Past-due invoice: `collections_followup`, reason `overdue_receivable`.
- Low tenure/high churn signal: `renewal_save`, reason `low_tenure_high_churn`.
- Support, NPS, or usage weakness: `technical_recovery`, using the strongest matching reason code.
- Clean low-probability candidates: `nurture_monitor`, reason `clean_billings`.

Observed stable model policy codes:

- `model_protocol_code`: `MOD-7`
- `probability_scale_code`: `PRB-4`
- `deployment_rule_code`: `DEP-5`
- `outreach_mapping_code`: `OUT-2`

## Precision And Validation

- Currency: 2 decimals.
- Percentages: 1 decimal.
- Churn probabilities: 3 decimals.
- Counts and ranks: integers.
- Use null for unavailable nullable fields rather than empty strings.
- Preserve requested ordering: ranked lists by rank, receivables by customer name, QBR rows by month, and agenda topics in the requested business order.
- Validate the final JSON with a parser before returning it.

## Common Pitfalls

- Do not include short aging buckets in `overdue_balance`; older A/R means only `61_90 + 90_plus`.
- Do not fuzzy-match noisy finance customer names to CRM accounts.
- Do not use `account.crm_arr` when billing snapshots are available.
- Do not use monthly metric `support_ticket_count` or `sla_compliance` for cleaned support outputs; recompute from ticket records.
- Do not count duplicate, spam, or cancelled tickets. Open tickets still count unless a prompt asks for closed/resolved work.
- Do not treat a low-risk action board account as needing a follow-up date if the chosen primary action is `no_action`.
- Do not omit `policy_codes` when the template includes them, even if the prose list of top-level keys is shorter than the template.
