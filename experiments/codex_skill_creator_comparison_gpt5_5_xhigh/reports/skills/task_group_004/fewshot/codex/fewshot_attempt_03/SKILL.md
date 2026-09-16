---
name: apexcloud-retention-ops
description: Solve ApexCloud Retention Operations API tasks that require JSON-only customer success, renewal risk, QBR, receivables, pipeline, operations, or churn-export outputs. Use when prompts mention the ApexCloud Retention Operations API, billing snapshots, A/R aging, account metrics, support tickets, NPS, opportunities, HR/event operations context, or churn CSV exports.
---

# ApexCloud Retention Operations

## Core Workflow

Read the prompt and any answer template provided with the task first. Produce only the JSON object requested by the prompt or template; keep key order and controlled enum values from the template.

Resolve `<TASK_ENV_BASE_URL>` from the task environment instructions. Do not hard-code a training URL. Fetch data with the public API/exports named in the prompt, then filter locally when an endpoint returns a portfolio collection.

Prefer these endpoint families:

- Accounts: `/api/accounts`, `/api/accounts/{account_id}`
- Metrics: `/api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM`
- Tickets: `/api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`
- NPS: `/api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`
- Billing ARR: `/api/billing/snapshots`, filtered by `as_of`
- A/R aging: `/api/finance/ar-aging`, filtered by `as_of`
- Pipeline: `/api/opportunities`, filtered by `close_date`
- HR/event context: `/api/hr/summary`, `/api/events/performance`
- Churn: `/exports/churn/train.csv`, `/exports/churn/validation.csv`, `/exports/churn/candidates.csv`

If account-level billing or A/R endpoints are unavailable, use the portfolio billing snapshot and finance A/R endpoints above. Billing snapshots are the authoritative ARR source when present.

## Normalization Rules

Use posted billing snapshots at the requested `as_of` date for `current_arr`; fall back to account `billing_arr_current` only when no matching snapshot exists. Set `uses_billing_arr_source` to true when snapshots drive ARR.

For A/R risk and receivables follow-up, compute older overdue balance as:

```text
overdue_balance = 61_90 + 90_plus
```

Do not include `current`, `1_30`, or `31_60` in overdue balances unless the prompt explicitly asks for total receivables.

Clean tickets exclude duplicates, spam, and cancelled tickets. Count all remaining tickets, including open tickets. SLA compliance is the percentage of clean tickets where both `first_response_sla_met` and `resolution_sla_met` are true. If there are no clean tickets, treat SLA as fully compliant for risk purposes.

Use the most recent non-retracted NPS response in the requested date range as latest NPS. For monthly QBR rows, group non-retracted NPS responses by response month; use `null` when a month has no usable response.

For product usage, use the latest month in the requested period. Treat usage below 65 as a usage risk. If usage is missing, use a first-to-last decline of 5 points or more as the fallback usage risk.

For opportunities, filter by `close_date` within the requested period. Open expansion pipeline is the sum of `amount` where `state` is `open`. Closed-won/lost summaries use `stage` values `Closed Won` and `Closed Lost`.

For finance-to-CRM matching, link an A/R customer to an account only on exact account legal name, exact display name, or exact alias after light case/space normalization. Do not link subsidiaries, foundations, or similarly named customers by partial/fuzzy matching.

## Risk Reasons

Use reason codes in this order when present:

```text
renewal_window
overdue_receivable
nps_drop
sla_degradation
usage_decline
low_tenure_high_churn
expansion_offset
clean_billings
```

Derive them as follows:

- `renewal_window`: renewal date is after the assessment date and within 90 days inclusive.
- `overdue_receivable`: older overdue balance is greater than zero.
- `nps_drop`: latest NPS is below 40, or the first-to-latest usable NPS decline is at least 15 points.
- `sla_degradation`: clean-ticket SLA compliance is below 90%.
- `usage_decline`: latest product usage is below 65, or fallback usage decline applies.
- `low_tenure_high_churn`: contract tenure is 18 months or less.
- `expansion_offset`: open expansion pipeline exists and the output explicitly reports expansion, or expansion is material context for a high-risk account.
- `clean_billings`: older overdue balance is zero; use mainly in risk queues or churn outreach explanations, not in action boards unless requested.

## Risk Scoring

When a prompt asks for numeric renewal risk, use this deterministic score and cap at 100:

```text
20 renewal_window
20 overdue_receivable
10 nps_drop
10 usage_decline
10 low_tenure_high_churn
15 sla_degradation
 5 additional SLA points when at least two clean tickets missed either SLA
10 ARR exposure bonus when billing ARR exceeds 1000000
```

The ARR exposure bonus affects score and ordering but is not a reason code.

Map scores to levels:

```text
critical: score >= 70
high:     score >= 50
medium:   score >= 30
low:      score < 30
```

For ranked risk queues, sort by score descending, then billing ARR descending, then account id. Return the requested top N.

For standard retention action boards, return every requested account and sort by risk level severity first, then billing ARR descending within each level. Use `no_action` and `null` next-touch date for low-risk board rows unless the prompt explicitly asks for an action on every row.

Primary action priority:

1. `collections_followup` for any older overdue balance.
2. `technical_recovery` for high/critical technical health risk, recurring SLA misses, low usage, or severe sentiment/usage deterioration.
3. `renewal_save` for renewal-window risk without stronger collections or technical recovery.
4. `executive_qbr` for strategic relationship risk when the prompt expects executive action and no stronger action applies.
5. `nurture_monitor` for low-probability outreach candidates with clean billing.
6. `no_action` for low-risk action-board rows.

When the prompt supplies due dates by action, copy the date for the chosen primary action. Use `null` when the chosen action is `no_action`.

## QBR Metrics Packets

For monthly QBR rows:

- `revenue`: account metrics `recognized_revenue`.
- `support_tickets`: clean ticket count in that month.
- `sla_compliance_pct`: clean-ticket SLA percentage in that month.
- `nps_score`: non-retracted NPS response score for that month, or `null`.

Highlights:

- Average revenue is the arithmetic mean of requested months.
- Peak revenue, max SLA, and peak NPS use the earliest month on ties.
- `ticket_trend` is `improving` when the last month has fewer clean tickets than the first, `worsening` when greater, otherwise `flat`.

Metric source enums:

```text
revenue: crm_closed_won
support_tickets: support_export
sla_compliance: sla_report
nps: nps_survey
```

Use `customer_success` as the default review owner. Set technical signoff only for materially degraded technical health, such as sustained SLA below 75%, recurring severe support misses, or a prompt that explicitly asks for engineering approval. Agenda topics should start with partnership/context, include the requested metrics, include technical recovery when SLA or usage is degraded, and end with next-period initiatives.

## Receivables, Pipeline, HR, And Events

For receivables follow-ups, include customers with older overdue balance greater than zero, sort by `customer_name` ascending, and set `primary_action` to `collections_followup`. Count linked and unlinked rows after conservative CRM matching.

For pipeline summaries over a quarter or date range:

- `won_count` and `won_revenue`: `stage == "Closed Won"`.
- `lost_count`: `stage == "Closed Lost"`.
- `open_count` and `open_pipeline`: `state == "open"`.
- `win_rate_pct`: won divided by won plus lost, as a percentage.
- `top_open_product_line`: product line with the largest open pipeline sum; break ties alphabetically.

For HR summaries across all regions, sum `headcount` and `unpaid_claims_amount`. For event context, use the matching event/quarter row and copy `event_orders` and `event_revenue`.

## Churn Export Validation

Parse churn exports with the standard CSV reader. Feature count is the number of input columns excluding `customer_id` and `Churn`; do not count one-hot-expanded columns in the reported feature count.

Use a conservative deployment threshold of 0.5 for validation accuracy. These exports can be highly imbalanced; if all calibrated probabilities fall below 0.5, validation accuracy equals the validation share of non-churn rows. Report the corresponding band:

```text
below_70, 70_to_79, 80_to_89, 90_plus
```

Tenure coefficient direction is `negative` when lower tenure increases churn risk, `positive` when higher tenure increases churn risk, and `zero` only when tenure has no effect in the fitted or heuristic model.

Rank only the candidate IDs named in the prompt. Churn probability should be monotonic with these risk signals: past-due invoice, low tenure, month-to-month contract, electronic check payment, low NPS, declining usage, high support tickets, and low active-seat ratio. Keep probabilities on a calibrated low scale unless the model strongly supports churn; round to 3 decimals and sort descending.

Outreach mapping:

- Past-due invoice driving the rank: `collections_followup`, reason `overdue_receivable`.
- Low tenure or month-to-month risk without past due: `renewal_save`, reason `low_tenure_high_churn`.
- Support or usage deterioration driving the rank: `technical_recovery`, reason `sla_degradation` or `usage_decline`.
- Otherwise: `nurture_monitor`, reason `clean_billings`.

Cohort checks count the returned top cohort only. Average probability is the arithmetic mean of returned probabilities after using full precision, rounded to the requested precision.

## Policy Codes

When a template contains policy-code fields and the prompt provides no separate policy definitions, use the middle policy option implied by the reusable rules:

```text
risk_model_code: RS-6
arr_source_code: REV-4
support_hygiene_code: SUP-8
action_priority_code: ACT-5
board_sort_code: BORD-4
exposure_formula_code: EXP-6
calendar_policy_code: CAL-5
receivable_trigger_code: RCP-7
crm_match_code: CM-5
pipeline_window_code: PW-6
followup_scope_code: FS-4
model_protocol_code: MOD-7
probability_scale_code: PRB-4
deployment_rule_code: DEP-5
outreach_mapping_code: OUT-2
```

## Final Checks

Return valid JSON only, with no prose or code fences. Use numbers, not formatted strings. Round currency to 2 decimals, percentages to 1 decimal, churn probabilities to 3 decimals, risk scores and counts to integers. Preserve `null` where the template uses `null`; do not replace it with an empty string or zero.
