---
name: reflection-skill-attempt-03
description: Use this skill for ApexCloud Retention Operations API evaluation tasks that ask for renewal risk queues, QBR packets, receivables/pipeline reviews, churn validation, outreach rankings, or high-touch retention boards. This skill should trigger whenever a prompt references the ApexCloud Retention Operations API, retention risk, support/SLA/NPS/billing/A/R reconciliation, churn CSV exports, controlled enum answer templates, or reflection-skill evaluation work.
---

# ApexCloud Retention Operations Workflow

Use this skill to produce deterministic JSON answers from the ApexCloud Retention Operations API. It captures transferable SOPs and business rules learned from blind training attempts; do not treat any task-specific training output as reusable content.

## First Moves

1. Read the task prompt and any input-side answer template.
2. Use the shared API base URL `http://127.0.0.1:8066`, even if a prompt mentions another local port.
3. Pull only the endpoint families the task asks for; save or inspect raw pulls when doing evaluation work.
4. Build the response from the answer template shape. Include `policy_codes` objects when the input template contains them, even if the prompt summary lists only the business-facing objects.
5. Return JSON only. Use 2 decimals for currency, 1 decimal for percentages, integer counts/scores, and 3 decimals for churn probabilities.

## API Map

Use these public endpoints:

- Accounts: `/api/accounts`, `/api/accounts/<account_id>`
- Monthly metrics: `/api/accounts/<account_id>/metrics?start=YYYY-MM&end=YYYY-MM`
- Tickets: `/api/accounts/<account_id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`
- NPS: `/api/accounts/<account_id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`
- Billing ARR snapshots: `/api/billing/snapshots?account_id=<account_id>&as_of=YYYY-MM-DD`
- A/R aging: `/api/finance/ar-aging?as_of=YYYY-MM-DD`
- Opportunities: `/api/opportunities`
- HR summary: `/api/hr/summary?quarter=YYYY-QN`
- Event performance: `/api/events/performance?event=<event_id>&quarter=YYYY-QN`
- Churn exports: `/exports/churn/train.csv`, `/exports/churn/validation.csv`, `/exports/churn/candidates.csv`

The billing snapshot route is easy to miss. For `current_arr`, use `snapshots[0].billing_arr`; do not use the account catalog's `billing_arr_current`.

## Core Field Rules

`current_arr`: Billing snapshot `billing_arr` for the requested as-of date.

`latest_nps`: Latest non-retracted NPS response in the analysis period. Ignore missing monthly metric values.

`clean_ticket_count`: Count ticket detail rows where `is_duplicate == false`, `is_spam == false`, and `status != "cancelled"`. Open tickets can still be clean.

`sla_compliance_pct`: Compute from clean ticket detail, not the aggregate metric field: clean tickets with both `first_response_sla_met` and `resolution_sla_met` divided by clean tickets for that month or period. If a month has no clean tickets, treat it as fully compliant unless the prompt says otherwise.

`overdue_balance`: For retention risk and receivables follow-ups, use only older A/R buckets: `61_90 + 90_plus`. Younger `1_30` and `31_60` buckets are not the actionable overdue balance.

`link_status`: Link A/R rows to CRM accounts by exact `legal_name` or explicit account alias. Similar-looking noise customers remain `unlinked` with `account_id: null`.

`expansion_pipeline`: Sum open opportunities whose `close_date` is inside the requested period. Use `state == "open"` rather than stage text.

`net_revenue_exposure`: For retention boards, `arr_at_risk - open_expansion_pipeline`.

## Risk Signals

Use controlled reason codes only when their evidence is present:

- `overdue_receivable`: older A/R balance `61_90 + 90_plus` is greater than zero.
- `clean_billings`: older A/R balance is zero.
- `renewal_window`: `renewal_date` is on or after the assessment date and within the stated renewal window, usually 90 days. Do not mark already-past renewals solely for this reason.
- `sla_degradation`: any clean support ticket missed first-response or resolution SLA, or ticket-derived compliance is below 100%.
- `nps_drop`: latest sentiment is weak, or latest NPS has materially fallen from the earliest valid response in the period. As a practical threshold, latest NPS below 40 or a drop of about 15+ points is enough.
- `usage_decline`: latest product usage is in a low pressure band, roughly below 65, or there is a clear sustained usage decline.
- `low_tenure_high_churn`: contract tenure is below 18 months.
- `expansion_offset`: there is open expansion pipeline in the requested period.

Good default risk scoring is additive and capped at 100:

- older receivable: 25
- renewal window: 15
- NPS risk: 15
- SLA degradation: 15
- usage decline: 10
- low tenure: 10
- ARR exposure: +10 for ARR >= 1,000,000; +5 for ARR >= 500,000

Use bands as a starting point: `critical` around 70+, `high` 50-69, `medium` 35-49, `low` below 35. Use the template's expected integer scores; keep the rank ordering consistent with the score and ARR exposure.

## Actions And Ordering

Primary action mapping:

- `collections_followup`: older A/R exists and the account is not otherwise a low/no-action board item.
- `technical_recovery`: SLA degradation is the dominant actionable issue.
- `renewal_save`: renewal window, low tenure, usage, or sentiment risk is dominant without collections or stronger technical recovery.
- `executive_qbr`: high-ARR strategic/enterprise accounts needing leadership alignment but no acute collections or technical recovery.
- `nurture_monitor`: low-risk active monitoring.
- `no_action`: allowed on high-touch boards for low-risk accounts with no urgent intervention; set `next_touch_due_date` to `null`.

Risk queues: rank by risk score descending, then ARR descending. Return the requested top N only.

Retention boards: include all requested accounts. The standard board order is risk severity first (`critical`, `high`, `medium`, `low`), then `current_arr` descending within the same severity. Do not sort the board primarily by action type.

Portfolio summaries:

- Queue `critical_or_high_count`: count returned accounts with level `critical` or `high`.
- Queue `arr_at_risk`: sum current ARR for returned accounts with level `critical` or `high`.
- Board `arr_at_risk`: sum current ARR for all non-low accounts on the board.
- Collections and technical counts use each returned account's `primary_action`.

Follow-up calendars use the exact due-date map from the prompt. If an account has `no_action`, do not invent a due date.

## QBR Packets

For monthly QBR rows:

- `revenue`: monthly `recognized_revenue` from account metrics.
- `support_tickets`: clean ticket count by created month.
- `sla_compliance_pct`: ticket-derived clean SLA percent by created month.
- `nps_score`: monthly NPS score from metrics or latest response in that month.

Highlights:

- `average_revenue`: arithmetic average of the monthly revenue rows.
- Peak revenue/SLA/NPS months: choose the earliest month when tied.
- `ticket_trend`: compare first and last monthly clean ticket counts; fewer is `improving`, more is `worsening`, equal is `flat`.
- Metric source labels: revenue often uses `crm_closed_won`; support tickets `support_export`; SLA `sla_report`; NPS `nps_survey`.
- If any ticket-derived SLA month is poor, include `technical_recovery` as an agenda topic before forward-looking initiatives.

## Receivables And Pipeline Reviews

Start from A/R rows with older balances (`61_90 + 90_plus > 0`), including unlinked noise customers. Sort `overdue_followups` by `customer_name` ascending. `overdue_total` is the sum of older balances for those rows.

Pipeline summaries use opportunities whose `close_date` falls inside the requested period:

- `won_count` and `won_revenue`: stage `Closed Won`.
- `lost_count`: stage `Closed Lost`.
- `open_count` and `open_pipeline`: `state == "open"`.
- `win_rate_pct`: `won_count / (won_count + lost_count) * 100`.
- `top_open_product_line`: product line with the largest summed open pipeline.

For all-region ops context, sum HR rows across regions and use the single requested event performance row.

## Churn Validation

For churn export tasks:

1. Load train, validation, and candidate CSVs from the API.
2. Treat `Churn == "Yes"` as the positive class.
3. Use all raw feature columns except `customer_id` and `Churn`. Report `feature_count` as this raw count, not the one-hot-expanded model matrix.
4. Train a deterministic classifier on the train export, validate on the validation export, and rank only the candidate IDs named in the prompt by predicted churn probability.
5. A regularized logistic classifier with scaled numeric features and encoded categoricals is a good default. Set a fixed random seed if the model uses randomness.
6. Report `accuracy_pct` on the validation set and map it to `below_70`, `70_to_79`, `80_to_89`, or `90_plus`.
7. `tenure_coefficient_direction` should usually be `negative` for a sane churn model: longer tenure lowers churn risk.

Outreach mapping for ranked candidates:

- `collections_followup` / `overdue_receivable`: invoice is past due and the probability is among the top ranked risks.
- `renewal_save` / `low_tenure_high_churn`: tenure below 18 months without a stronger collections reason.
- `technical_recovery` / `sla_degradation`: high recent support tickets or support-health risk dominates.
- `renewal_save` / `usage_decline`: usage trend is clearly negative without collections.
- `nurture_monitor` / `clean_billings`: no stronger risk reason.

`cohort_checks` counts are computed over the returned top-ranked cohort, not all selected candidates.

## Policy Codes

When policy-code objects are requested, use these stable choices:

- Retention risk model: `risk_model_code: "RS-6"`, `arr_source_code: "REV-4"`, `support_hygiene_code: "SUP-8"`, `action_priority_code: "ACT-5"`.
- Board extras: `board_sort_code: "BORD-4"`, `exposure_formula_code: "EXP-6"`, `calendar_policy_code: "CAL-5"`.
- Receivables/pipeline: `receivable_trigger_code: "RCP-7"`, `crm_match_code: "CM-5"`, `pipeline_window_code: "PW-6"`, `followup_scope_code: "FS-4"`.
- Churn model: `model_protocol_code: "MOD-7"`, `probability_scale_code: "PRB-4"`, `deployment_rule_code: "DEP-5"`, `outreach_mapping_code: "OUT-2"`.

## Common Pitfalls

- Do not use the task-local setup script or environment directory when the shared API is available.
- Do not use catalog ARR for output `current_arr`; billing snapshots are the source of truth.
- Do not sum all A/R buckets for actionable overdue balance.
- Do not fuzzy-match noisy A/R customer names into CRM accounts.
- Do not use aggregate monthly SLA fields when ticket detail is available.
- Do not count duplicate, spam, or cancelled tickets as clean support volume.
- Do not mark past renewal dates as `renewal_window`.
- Do not report one-hot-expanded dimensions as churn `feature_count`.
- Do not dump training answers into the skill or final responses; encode only transferable rules and controlled vocabularies.
