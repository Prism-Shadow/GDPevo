---
name: apexcloud-retention-ops
description: Use this skill for ApexCloud Retention Operations API tasks that ask for renewal risk queues, QBR metric packets, receivables and pipeline reviews, churn validation/ranking, or high-touch retention action boards. It gives the endpoint habits, filtering rules, source priorities, controlled enum conventions, precision rules, and common pitfalls needed to produce JSON-only answers from the public ApexCloud environment.
---

# ApexCloud Retention Operations

Use this skill when a task references the ApexCloud Retention Operations API and asks for a structured operations, customer success, finance, or churn-risk JSON output.

## First Moves

1. Read the prompt and the supplied `input/payloads/answer_template.json` before calculating anything. The prompt sometimes omits fields that the template requires, especially `policy_codes`.
2. Use the remote API entrypoint given by the task environment. If the prompt says `http://127.0.0.1:8074` but the evaluation workspace provides a remote base URL, replace only the host/base with the provided remote base and keep the same paths.
3. Query only public API/export endpoints. Do not inspect local environment source or data files.
4. Build a small local table keyed by `account_id`, then join finance, billing, support, NPS, opportunity, HR, event, or churn data into it as the prompt requires.
5. Return only valid JSON. Do not include prose, markdown fences, comments, or explanatory text.

Useful health/schema probe:

```text
GET /api/health
```

The root path and OpenAPI-style paths may return `not_found`; that is normal.

## Endpoint Habits

Core account data:

```text
GET /api/accounts
GET /api/accounts/<account_id>
```

Account fields include `account_id`, `display_name`, `legal_name`, `account_aliases`, `region`, `segment`, `lifecycle_status`, `renewal_date`, `contract_tenure_months`, `billing_arr_current`, `crm_arr`, and `csm_owner`.

Monthly metrics:

```text
GET /api/accounts/<account_id>/metrics?start=YYYY-MM&end=YYYY-MM
```

Metrics rows include `month`, `quarter`, `recognized_revenue`, `product_usage`, `active_seats`, `support_ticket_count`, `sla_compliance`, `nps_score`, and `survey_status`.

Support tickets:

```text
GET /api/accounts/<account_id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD
```

Tickets include `created_date`, `status`, `severity`, `product_area`, `first_response_sla_met`, `resolution_sla_met`, `is_duplicate`, and `is_spam`.

NPS:

```text
GET /api/accounts/<account_id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD
```

NPS rows include `response_date`, `score`, `survey_channel`, and `retracted`.

Billing snapshots:

```text
GET /api/billing/snapshots?as_of=YYYY-MM-DD
```

This is not nested under accounts. Snapshot rows include `account_id`, `as_of`, `billing_arr`, `mrr`, `posted`, `legal_name`, and `source`.

A/R aging:

```text
GET /api/finance/ar-aging?as_of=YYYY-MM-DD
```

Aging rows include `customer_name`, `region`, `quarter`, `current`, `1_30`, `31_60`, `61_90`, and `90_plus`.

Opportunities:

```text
GET /api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD
```

Opportunity rows include `account_id`, `amount`, `close_date`, `created_date`, `product_line`, `stage`, `state`, and `region`.

HR and event operations context:

```text
GET /api/hr/summary?quarter=YYYY-QN
GET /api/events/performance?event=apex_connect&quarter=YYYY-QN
```

Churn exports:

```text
GET /exports/churn/train.csv
GET /exports/churn/validation.csv
GET /exports/churn/candidates.csv
```

## Source Priority Rules

Use the source that matches the business meaning, not just the first similar-looking field.

- Current ARR and ARR-at-risk: use posted `/api/billing/snapshots` for the requested `as_of` date when available. This supports `uses_billing_arr_source: true` and `metric_sources.revenue: "billing_snapshot"` only when the field is actually current ARR. Use account `billing_arr_current` only as a fallback, and `crm_arr` only when the prompt explicitly asks for CRM ARR.
- Monthly QBR revenue: use `recognized_revenue` from account metrics, not current ARR. The source enum for monthly revenue is usually `billing_snapshot` only if the prompt defines revenue as billing snapshot; otherwise choose the enum that best represents the requested source from the template vocabulary.
- Support ticket counts and clean ticket counts: use the support tickets endpoint. Exclude rows where `is_duplicate` or `is_spam` is true for "clean" counts and support-health analysis.
- SLA compliance: use monthly `sla_compliance` from metrics when the output asks for a monthly SLA percentage from the SLA report. Use tickets only when the prompt asks you to recompute from ticket outcomes.
- Latest NPS: use NPS responses, exclude `retracted: true`, sort by `response_date`, and take the latest valid score. Use `null` only when the answer template permits null and no valid response exists.
- Product usage trend: use monthly `product_usage` from metrics across the requested period.
- A/R overdue balance: normally sum `1_30 + 31_60 + 61_90 + 90_plus`. When the prompt says "older aging buckets" for eligibility, include only customers with `61_90 + 90_plus > 0`, but still report total overdue balance unless the prompt says otherwise.
- Pipeline totals: filter opportunities by `close_date` within the requested window. `state: "open"` contributes to open pipeline, `stage: "Closed Won"` or closed won state contributes to won revenue, and `stage: "Closed Lost"` contributes to lost count.
- HR "all regions": sum numeric fields across all returned region rows for the requested quarter.
- Event context: use the exact event ID and quarter from the prompt, then copy/sum the requested event fields.

## Matching And Exclusions

- Review only the `account_id`s listed in the prompt when a shortlist is provided. Do not add high-risk accounts from outside the requested list.
- For A/R followups, build a case-insensitive, punctuation-insensitive match map from `legal_name`, `display_name`, and every `account_aliases` value. The `aging_id` often contains the account id, but do not rely on it as the only match. If no CRM account matches, set `link_status: "unlinked"` and `account_id: null`.
- Ignore `current` A/R for overdue and follow-up calculations.
- Exclude duplicate/spam support tickets before counting "clean" tickets, determining ticket product-area pressure, or using ticket-level SLA.
- Exclude retracted NPS responses.
- Do not include closed opportunities in `open_expansion_pipeline`; do include closed won/lost in pipeline summaries when those fields are requested.
- Respect lifecycle context: paused, implementation, renewal_risk, upcoming renewal, low tenure, overdue receivables, poor NPS, SLA degradation, usage decline, and expansion offsets all affect risk/action choice.

## Risk And Action Conventions

Risk tasks are deterministic business triage, not hidden-model tasks unless the prompt specifically references churn exports.

Use these factors in roughly this order:

1. Severe/older overdue receivables and large overdue balances.
2. Renewal date near or inside the assessment window.
3. Current revenue exposure from billing snapshots.
4. Negative customer sentiment: low latest NPS or NPS decline.
5. Support/SLA problems: low SLA, P1/P2 load, open severe issues, or many clean tickets.
6. Usage decline across the requested months.
7. Low tenure combined with churn signals.
8. Lifecycle context such as `renewal_risk`, `paused`, or `implementation`.
9. Open expansion pipeline as an offset, not as a reason to ignore severe risk.

Primary action mapping:

- `collections_followup`: overdue receivables dominate, especially older buckets.
- `technical_recovery`: SLA/support/product usage problems dominate.
- `renewal_save`: renewal timing and churn risk dominate.
- `executive_qbr`: strategic/enterprise relationship needs leadership attention but not urgent collections/technical recovery.
- `nurture_monitor`: lower-risk account needing monitoring.
- `no_action`: only when the template allows it and no material issue exists.

Common reason codes:

- `overdue_receivable`: any meaningful overdue balance, especially older buckets.
- `low_tenure_high_churn`: low tenure plus other churn indicators.
- `sla_degradation`: poor SLA, rising support pressure, or severe ticket issues.
- `nps_drop`: low latest NPS or deterioration over the period.
- `usage_decline`: product usage declines over the requested months.
- `renewal_window`: renewal is near the assessment period.
- `expansion_offset`: open expansion pipeline reduces net risk/exposure.
- `clean_billings`: billing/receivables are clean and should be called out when relevant.

For board-style outputs, sort by the requested board order if explicitly specified. Otherwise use risk severity first (`critical`, `high`, `medium`, `low`), then action urgency (`collections_followup`, `technical_recovery`, `renewal_save`, `executive_qbr`, `nurture_monitor`, `no_action`), then descending ARR or net exposure, with `account_id` as a stable final tie-breaker.

## Churn Export Workflow

For `/exports/churn/*` tasks:

1. Load `train.csv`, `validation.csv`, and `candidates.csv`.
2. Treat `Churn` as the label in train/validation; candidates have no label.
3. One-hot encode categorical fields consistently across all three datasets. Keep numeric fields numeric.
4. Train a deterministic, regularized classifier such as logistic regression with a fixed random seed and enough iterations to converge. A simple interpretable model is preferred over a hand-made score.
5. Compute validation accuracy from predicted classes and report it as a percentage to 1 decimal.
6. `feature_count` is the number of model input columns after encoding, not the raw CSV column count and not including `customer_id` or `Churn`.
7. Determine `tenure_coefficient_direction` from the fitted coefficient for the raw `tenure` feature: negative, positive, or zero.
8. Score only the candidate accounts requested in the prompt, rank descending by predicted churn probability, return exactly the requested top N, and round probabilities to 3 decimals.
9. For shortlist counts, count within the requested candidate shortlist unless the prompt says to use the full candidate export.

Reason/action mapping for churn ranking should mirror the risk conventions: invoice past due maps to `overdue_receivable` and often `collections_followup`; high support/SLA-like pressure maps to `sla_degradation` or `technical_recovery`; low NPS maps to `nps_drop`; declining usage maps to `usage_decline`; low tenure maps to `low_tenure_high_churn`; upcoming renewal maps to `renewal_window`.

## Output Field Conventions

- Preserve the exact top-level keys and nested field names from the answer template.
- Include policy-code fields when present in the template, even if the prompt summary did not mention them.
- Currency: numbers rounded to 2 decimals.
- Percentages: numbers rounded to 1 decimal.
- Churn probabilities: numbers rounded to 3 decimals.
- Counts, ranks, and risk scores: integers.
- Dates: `YYYY-MM-DD`; months: `YYYY-MM`; quarters: `YYYY-QN`.
- Use JSON numbers, booleans, arrays, and nulls naturally. Do not stringify numeric values.
- Ordered lists should be deterministic: use the prompt's sort order when provided; otherwise sort by the requested ranking metric, then stable tie-breakers.
- For "exactly N" outputs, return exactly N objects even if more accounts qualify.
- For agenda topics, controlled labels, source enums, risk levels, actions, and reason codes, use only labels listed in the prompt/template.

## Controlled Enum Sets Seen In This API Family

Risk levels:

```text
critical, high, medium, low
```

Primary actions:

```text
executive_qbr, collections_followup, technical_recovery, renewal_save, nurture_monitor, no_action
```

Reason codes:

```text
overdue_receivable, low_tenure_high_churn, sla_degradation, nps_drop, usage_decline, renewal_window, expansion_offset, clean_billings
```

Metric source enums:

```text
crm_closed_won, support_export, sla_report, nps_survey, billing_snapshot, ar_aging, pipeline_crm, event_dashboard, hr_report
```

Review owners:

```text
solutions_engineering, customer_success, finance_ops
```

Agenda topics:

```text
partnership_overview, q2_metrics, performance_highlights, q3_initiatives, technical_recovery, commercial_expansion
```

Link status:

```text
linked, unlinked
```

Accuracy bands:

```text
below_70, 70_to_79, 80_to_89, 90_plus
```

Tenure direction fields:

```text
negative, positive, zero, not_assessed
```

Policy-code fields are controlled strings. Choose the code that corresponds to the method actually used, and never invent a new code outside the alternatives shown in the template. If the code semantics are not documented, keep the selection consistent across related tasks:

- Risk model code: use the risk-scoring option when ranking from multiple retention factors.
- ARR source code: use the billing-snapshot option when ARR comes from posted billing snapshots.
- Support hygiene code: use the clean-support option when duplicate/spam tickets are excluded.
- Action priority code: use the option matching the action-priority mapping above.
- Receivable trigger code: use the older-aging-bucket option when `61_90` or `90_plus` drives inclusion.
- CRM match code: use the alias/legal-name matching option when linking A/R customers to accounts.
- Pipeline window code: use the close-date-in-window option.
- Followup scope code: use the prompt's stated follow-up eligibility scope.

## Task-Specific Recipes

Renewal risk queue:

- Pull accounts, billing snapshot as of the prompt date, metrics for the requested months, tickets/NPS for the requested date range, and A/R aging as of date.
- Calculate latest NPS, clean ticket count, overdue balance, usage trend, SLA health, renewal proximity, tenure, lifecycle, and current ARR.
- Rank only the prompted accounts; return the requested top N.
- `arr_at_risk` usually sums current ARR for critical/high accounts in the returned or reviewed set as implied by the template; be consistent with the summary wording.

QBR metrics packet:

- For each requested month, report monthly revenue, clean support tickets, SLA percentage, and NPS score.
- Use averages/peaks from the monthly rows after rounding rules are clear. `ticket_trend` is `improving` when monthly counts decline, `worsening` when they rise, and `flat` when essentially unchanged.
- `needs_technical_signoff` should be true when support/SLA/technical-recovery agenda items are material.
- Choose exactly the number of agenda topics requested and keep them ordered for a deck: overview, metrics, highlights, forward-looking initiatives/recovery/expansion as appropriate.

Receivables and pipeline operations review:

- Start from A/R customers with older overdue balances (`61_90 + 90_plus > 0`) unless the prompt sets another trigger.
- Link to CRM accounts by names/aliases. Sort overdue followups by `customer_name` when instructed.
- Summarize Q3 or requested-window opportunities by won/lost/open state and product line.
- Sum HR and event context across all requested regions/events.

High-touch retention action board:

- Return all prompted accounts, not just the high-risk ones.
- Use billing snapshots for `current_arr`, open opportunities in the requested close-date window for `expansion_pipeline`, and A/R overdue for `overdue_balance`.
- `net_revenue_exposure` is current ARR at risk minus open expansion pipeline when the template asks for exposure offset behavior.
- Use the due-date calendar supplied in the prompt and set each row's `next_touch_due_date` from its `primary_action`.

## Pitfalls

- Do not use localhost if only a remote base URL is available in the evaluation environment.
- Do not start or inspect the local task environment when the prompt/environment says to use the remote public endpoint.
- Do not use account `crm_arr` for current ARR when billing snapshots are available.
- Do not count duplicate/spam tickets as clean tickets.
- Do not include retracted NPS responses.
- Do not treat A/R `current` as overdue.
- Do not rank or summarize accounts outside the prompt shortlist unless the prompt asks for all regions/all accounts.
- Do not ignore answer-template fields such as policy codes just because they are not repeated in the natural-language prompt.
- Do not output extra explanation around JSON.
