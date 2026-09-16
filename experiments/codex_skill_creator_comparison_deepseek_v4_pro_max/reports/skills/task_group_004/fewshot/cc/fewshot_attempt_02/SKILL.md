---
name: apexcloud-retention-ops
description: Use this skill whenever the task involves the ApexCloud Retention Operations API, customer retention analysis, renewal risk assessment, QBR metrics, churn modeling, or any customer success operations task referencing account_ids, ARR, NPS, support tickets, billing snapshots, AR aging, or retention action boards. This skill documents the API, data hygiene rules, controlled vocabularies, and deterministic output conventions. Trigger on any prompt that mentions account-level retention data, renewal queues, QBR preparation, receivables reviews, churn model validation, or retention board construction, even if the specific task type is not named.
---

# ApexCloud Retention Operations

Skill for solving ApexCloud retention operations tasks against the public
Retention Operations API. Covers the full task surface: risk queues, QBR
metrics, receivables and pipeline reviews, churn model validation, and
high-touch retention action boards.

## Quick Start

1. Read the task prompt for the **task type**, **account IDs**, **date range**,
   **assessment date**, and any **specific instructions** about scoring or
   ranking.
2. Identify the task type from the signal words (see Task Types below).
3. Consult [references/api.md](references/api.md) for exact endpoints,
   parameters, and response shapes needed.
4. Fetch all required data in parallel across accounts.
5. Apply the core data rules in this file.
6. Follow the methodology for the specific task type.
7. Produce JSON output with deterministic precision using the controlled
   vocabulary in [references/vocabulary.md](references/vocabulary.md).

## Core Data Rules

These rules apply across all task types. Follow them exactly.

### ARR Sourcing

**Always use billing snapshots for current ARR.** The account profile
`billing_arr_current` field is a forward-looking estimate and differs from the
authoritative snapshot values. The CRM `crm_arr` field is a separate sales
pipeline figure and should not be used as current ARR unless a task explicitly
requires it.

- Hit `GET /api/billing/snapshots` to get the full snapshot list.
- For each account, pick the snapshot whose `as_of` date is closest to
  (and not after) the assessment date. The `billing_arr` field is the
  authoritative current ARR.
- When aggregating multiple accounts, sum the snapshot ARR values after
  selecting the right snapshot per account.

### Ticket Hygiene

The clean ticket count represents meaningful support interactions.

- Hit `GET /api/accounts/{account_id}/tickets` with the analysis date range.
- Count tickets where **all** of these conditions hold:
  - `is_spam` is `false`
  - `is_duplicate` is `false`
  - `status` is not `cancelled`
- Include tickets regardless of severity or product area. Only exclude via
  the three filters above.

### Overdue Receivables

- Hit `GET /api/finance/ar-aging` for finance-wide aging. For per-account
  views, use `GET /api/accounts/{account_id}/ar-aging` when the account is
  a known CRM account.
- The overdue balance is the sum of aging buckets **31_60**, **61_90**, and
  **90_plus** for the quarter matching the as-of date. Do not include `1_30`
  (that bucket is current, not overdue).
- The `current` field is the total not-yet-due balance; ignore it for overdue
  calculations.

### NPS Extraction

- Hit `GET /api/accounts/{account_id}/nps` with the analysis date range.
- The NPS endpoint returns individual survey responses. Filter out responses
  where `retracted` is `true`.
- The latest NPS is the `score` from the response with the most recent
  `response_date` within the period. If no responses exist for the period,
  report `null` or 0 depending on the output shape.
- The metrics endpoint also carries an `nps_score` field, but the NPS endpoint
  is the authoritative source because it exposes retraction status.

### Account Linking

When cross-referencing A/R customers with CRM accounts:

- A/R records carry a `customer_name` field (legal entity name).
- CRM accounts have `legal_name` and `account_aliases`.
- An A/R customer is **linked** if its `customer_name` matches any CRM
  account's `legal_name` or any entry in `account_aliases`. Case-sensitive
  exact match.
- A matched record gets `link_status: "linked"` and the corresponding
  `account_id`. Unmatched records get `link_status: "unlinked"` and
  `account_id: null`.

### SLA Compliance

- Pull `sla_compliance` from the metrics endpoint per month.
- SLA degradation is indicated by a declining trend across months or by
  values consistently below 90%.

### Usage Trend

- Pull `product_usage` from the metrics endpoint per month.
- A declining trend is a risk signal. Compare the most recent month against
  the earliest month in the period.

### Tenure Risk

- Lower contract tenure correlates with higher churn risk.
- Account profile `contract_tenure_months` is the source.
- Tenure under 24 months, combined with a renewal within the analysis window,
  is the `low_tenure_high_churn` signal.
- The `tenure_risk_direction` is `"negative"` (inverse relationship).

### Renewal Window

- Pull `renewal_date` from the account profile.
- An account is "in window" when its renewal date falls within 90 days of the
  assessment date.

### Expansion Pipeline

- Hit `GET /api/opportunities` for the full opportunity list.
- Open expansion pipeline for an account is the sum of `amount` for
  opportunities where `account_id` matches, `state` is `"open"`, and the
  `close_date` falls within the relevant period (typically the analysis
  quarter).
- Expansion offsets risk: a significant open pipeline reduces the net risk
  exposure.

### Revenue (Monthly)

- For QBR and monthly views, use `recognized_revenue` from the metrics
  endpoint. This is the recognized (not billed) monthly revenue.

### Deterministic Precision

- Currency values: **2 decimal places**.
- Percentage values: **1 decimal place**.
- Counts: **integers**.
- Risk scores: **integers** (0-100 scale).
- Churn probabilities: **3 decimal places**.
- When computing averages, round the final result, not intermediate values.
- When computing percentage from integer counts, compute as
  `round(count / total * 100, 1)`.

## Task Types

Match the prompt to one of these patterns and follow the corresponding
methodology.

### Risk Queue

**Signal words:** renewal risk, risk queue, top N, ranked, risk score,
risk level, retention standup, portfolio summary.

**Methodology:**

1. Fetch account profiles, metrics (3-month range), tickets, NPS, billing
   snapshots, and A/R aging for every listed account.
2. Compute per-account:
   - `current_arr` from the billing snapshot (see ARR Sourcing).
   - `clean_ticket_count` (see Ticket Hygiene).
   - `latest_nps` (see NPS Extraction).
   - `overdue_balance` (see Overdue Receivables).
3. Score each account on these dimensions (1 point each unless noted):
   - `renewal_window`: renewal within 90 days of assessment date.
   - `overdue_receivable`: overdue balance > 0.
   - `nps_drop`: latest NPS < 50 or NPS declined from prior response.
   - `sla_degradation`: any month below 90% or declining trend.
   - `usage_decline`: product_usage declining across the period.
   - `low_tenure_high_churn`: tenure < 24 months with renewal approaching.
   - `expansion_offset`: **subtract 1** if open expansion pipeline exists
     in the period (the account is investing more, reducing churn risk).
   - `clean_billings`: no overdue balance (0 points; this is a positive
     signal, not a risk point).
4. Compute `risk_score` as `min(100, sum_of_points * 20)`. Round to nearest
   integer.
5. Map `risk_score` to `risk_level`:
   - 80-100: `"critical"`
   - 50-79: `"high"`
   - 20-49: `"medium"`
   - 0-19: `"low"`
6. Assign `primary_action`:
   - `"collections_followup"` when `overdue_receivable` is the dominant
     negative signal.
   - `"technical_recovery"` when `sla_degradation` or `usage_decline`
     dominate.
   - `"renewal_save"` when `renewal_window` or `low_tenure_high_churn`
     dominate and no overdue balance exists.
   - `"executive_qbr"` for strategic accounts with multiple critical
     signals.
   - `"nurture_monitor"` for low-risk accounts without urgent signals.
   - `"no_action"` when risk_score is very low and no signals fire.
7. List `reason_codes` as the array of signal labels (from the controlled
   vocabulary) that fired for this account. Include `clean_billings` when
   overdue_balance is 0. Include `expansion_offset` when expansion pipeline
   is present.
8. Sort by `risk_score` descending. Return top N.
9. Compute portfolio summary:
   - `accounts_reviewed`: total accounts analyzed.
   - `critical_or_high_count`: count of critical + high.
   - `arr_at_risk`: sum of current_arr for critical + high accounts.
   - `collections_count`: count with primary_action `collections_followup`.
   - `technical_recovery_count`: count with primary_action
     `technical_recovery`.

### QBR Metrics Packet

**Signal words:** QBR, quarterly business review, metrics packet, monthly
metrics, highlights, agenda.

**Methodology:**

1. Fetch account profile, metrics, tickets, and NPS for the single account
   across the specified months.
2. Build `qbr_metrics` array with one entry per month:
   - `month`: YYYY-MM.
   - `revenue`: `recognized_revenue` from metrics.
   - `support_tickets`: clean ticket count for the month.
   - `sla_compliance_pct`: `sla_compliance` from metrics, rounded to 1
     decimal.
   - `nps_score`: NPS score from the NPS endpoint (latest non-retracted
     for the month; null if none). Use the integer score.
3. Compute highlights:
   - `average_revenue`: mean of monthly revenues.
   - `peak_revenue_month` / `peak_revenue`: max revenue month and value.
   - `max_sla_month` / `max_sla_pct`: best SLA month.
   - `peak_nps_month` / `peak_nps_score`: highest NPS month.
   - `ticket_trend`: compare first month to last month. `"improving"` if
     ticket count decreased, `"worsening"` if increased, `"flat"` if
     unchanged.
4. Set `metric_sources` using the source vocabulary (see
   [references/vocabulary.md](references/vocabulary.md)):
   - revenue: `"crm_closed_won"` when pulled from metrics recognized_revenue.
   - support_tickets: `"support_export"`.
   - sla_compliance: `"sla_report"`.
   - nps: `"nps_survey"`.
5. Set `review_plan`:
   - `review_owner`: `"customer_success"` (the default). Use
     `"solutions_engineering"` if the task is tech-recovery focused, or
     `"finance_ops"` if finance/collections focused.
   - `review_due_date`: as specified in the task, or default to 3 weeks
     post quarter-end.
   - `needs_technical_signoff`: `true` if SLA degradation or usage decline
     is present, otherwise `false`.
6. Build `agenda_topics`: choose exactly four ordered topics from the agenda
   vocabulary. Default order: partnership_overview, q2_metrics (adapt to
   quarter), technical_recovery (if issues exist), q3_initiatives (adapt to
   next quarter).

### Receivables and Pipeline Review

**Signal words:** receivables, pipeline, operations review, A/R, overdue,
collections, finance, HR, events.

**Methodology:**

1. Hit `GET /api/finance/ar-aging` filtered to the as-of quarter.
2. Filter to A/R records where the overdue balance (31_60 + 61_90 + 90_plus)
   is greater than 0. These are the overdue customers.
3. Hit `GET /api/accounts` to get all CRM accounts with legal names and
   aliases.
4. Link each overdue customer to CRM accounts (see Account Linking).
5. Build `overdue_followups` array sorted by `customer_name` ascending.
6. Compute financial summary:
   - `overdue_client_count`: total overdue customers.
   - `overdue_total`: sum of all overdue balances.
   - `linked_followup_count`: count with link_status "linked".
   - `unlinked_followup_count`: count with link_status "unlinked".
7. Hit `GET /api/opportunities` and compute pipeline summary:
   - Filter opportunities by the quarter's date range (close_date within
     range).
   - Count won, lost, open by state.
   - `won_revenue`: sum of amount for won.
   - `open_pipeline`: sum of amount for open.
   - `win_rate_pct`: won_count / (won_count + lost_count) * 100.
   - `top_open_product_line`: most frequent product_line among open opps.
8. Hit `GET /api/hr/summary` and aggregate all regions for the quarter:
   - `hr_headcount`: sum of headcounts.
   - `unpaid_claims_total`: sum of unpaid_claims_amount.
9. Hit `GET /api/events/performance` for the specified event and quarter:
   - `event_orders`: the event_orders value.
   - `event_revenue`: the event_revenue value.
10. Set `primary_action` for all followups to `"collections_followup"`.
    Set `due_date` as specified in the task (default 2026-10-15 for Q3).

### Churn Model Validation and Outreach Ranking

**Signal words:** churn, model validation, churn export, train.csv,
validation.csv, candidates, churn probability, outreach.

**Methodology:**

1. Fetch the three CSV exports via `GET /exports/churn/train.csv`,
   `GET /exports/churn/validation.csv`, and
   `GET /exports/churn/candidates.csv`.
2. Parse the CSVs. The columns are: customer_id, tenure, MonthlyCharges,
   TotalCharges, Contract, PaymentMethod, PaperlessBilling, Partner,
   Dependents, OnlineSecurity, OnlineBackup, DeviceProtection, TechSupport,
   StreamingTV, StreamingMovies, SupportTickets90d, NPSLast, UsageTrendPct,
   InvoicePastDue, ActiveSeatRatio, Churn.
3. Model validation:
   - `training_rows`: row count in train.csv (excluding header).
   - `validation_rows`: row count in validation.csv (excluding header).
   - `feature_count`: count of columns excluding customer_id and Churn
     (19 features).
   - `accuracy_pct`: compute accuracy by comparing predicted to actual on
     the validation set. Train a logistic regression in Python with sklearn
     if available; otherwise use a heuristic: predict churn for rows where
     InvoicePastDue=Yes, tenure < 12, or UsageTrendPct < -15. Compute
     accuracy against actual Churn column. Round to 1 decimal.
   - `accuracy_band`: `"90_plus"` if >= 90, `"80_to_89"` if 80-89.9,
     `"70_to_79"` if 70-79.9, `"below_70"` otherwise.
   - `tenure_coefficient_direction`: `"negative"` (lower tenure -> higher
     churn probability).
4. Filter candidates.csv to the specified account IDs.
5. Sort by predicted_churn_probability descending, take top 5.
   Use the model to score each candidate and assign a probability.
6. Assign `outreach_action` per candidate:
   - `"collections_followup"` if InvoicePastDue = Yes.
   - `"renewal_save"` if tenure < 12 or UsageTrendPct < -15 and
     InvoicePastDue = No.
   - `"technical_recovery"` if SupportTickets90d > 5 and no overdue.
   - `"nurture_monitor"` for low probability with no risk signals.
7. Assign `reason_code` per candidate (single code for churn tasks, pick
   the dominant signal).
8. Compute cohort checks:
   - `past_due_shortlist_count`: candidates with InvoicePastDue = Yes.
   - `low_tenure_shortlist_count`: candidates with tenure < 12.
   - `average_probability_top5`: mean of the top 5 probabilities.
   Round to 3 decimals.

### Retention Action Board

**Signal words:** retention action board, retention board, action board,
high-touch, operating review, board order, followup calendar, segment
summary, expansion pipeline.

**Methodology:**

1. Fetch account profiles, metrics, tickets, NPS, billing snapshots, A/R
   aging, and opportunities for every listed account.
2. For each account compute risk using the Risk Queue methodology (all
   dimensions).
3. Additionally pull `expansion_pipeline` per account from opportunities
   (see Expansion Pipeline).
4. Build the action board with **all** accounts (not just top N), sorted
   by risk_score descending.
5. Set `next_touch_due_date` based on `primary_action` using the task's
   specified due dates. If the task provides a mapping, use it. For
   `no_action`, use `null`. For `nurture_monitor`, use the nurture date.
6. Compute segment summary:
   - `strategic_accounts`: count of accounts with segment "Strategic".
   - `enterprise_accounts`: count of accounts with segment "Enterprise"
     (not Strategic).
   - `arr_at_risk`: sum of current_arr for all listed accounts.
   - `open_expansion_pipeline`: sum of expansion_pipeline for all listed
     accounts.
   - `net_revenue_exposure`: `arr_at_risk - open_expansion_pipeline`.
     Round to 2 decimals.
7. Build `followup_calendar` with the task-specified due dates.

## Output Conventions

- Output **only valid JSON**. No markdown fences, no explanatory text.
- Follow the exact shape given in any provided answer template.
- Use the controlled vocabulary from
  [references/vocabulary.md](references/vocabulary.md) for all enum fields.
- Currency to 2 decimals, percentages to 1 decimal, counts as integers.
- Risk scores as integers.
- Churn probabilities to 3 decimals.
- Sort order as specified per task type.

## Policy Codes

Policy codes document the methodology variant used. Select the code that
matches the processing approach actually applied. See
[references/vocabulary.md](references/vocabulary.md) for the full enum.

**For risk queue / retention board tasks:**
- `risk_model_code`: `"RS-6"` when using standard composite model with all
  seven dimensions.
- `arr_source_code`: `"REV-4"` when using billing snapshot ARR.
- `support_hygiene_code`: `"SUP-8"` when using clean ticket count.
- `action_priority_code`: `"ACT-5"` when using composite priority.

**For receivables tasks:**
- `receivable_trigger_code`: `"RCP-7"` when filtering to older buckets
  (31+ days).
- `crm_match_code`: `"CM-5"` when matching via legal name + aliases.
- `pipeline_window_code`: `"PW-6"` when using quarter-bounded pipeline.
- `followup_scope_code`: `"FS-4"` when including all overdue customers.

**For churn tasks:**
- `model_protocol_code`: `"MOD-7"` when trained on the provided data.
- `probability_scale_code`: `"PRB-4"` when using 0-1 decimal scale.
- `deployment_rule_code`: `"DEP-5"` when filtering to a candidate list.
- `outreach_mapping_code`: `"OUT-2"` when mapping by probability.

**For retention board tasks (additional):**
- `board_sort_code`: `"BORD-4"` when risk-ranked.
- `exposure_formula_code`: `"EXP-6"` when using net exposure (ARR minus
  expansion).
- `calendar_policy_code`: `"CAL-5"` when using action-specific due dates
  from the task.

## References

- [API Reference](references/api.md) — all endpoints, parameters, and
  response shapes.
- [Controlled Vocabulary](references/vocabulary.md) — every enum value
  and its meaning.

Always read both references when the task involves endpoints or enums you
have not yet seen in the current session.
