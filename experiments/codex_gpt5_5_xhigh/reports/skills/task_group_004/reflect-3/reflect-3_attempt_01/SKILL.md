---
name: apexcloud-retention-ops-json
description: Use this skill for ApexCloud Retention Operations tasks that ask for structured JSON from account, metrics, support, NPS, billing, A/R aging, opportunities, HR, events, or churn export data. Trigger it whenever the prompt asks for renewal risk queues, retention action boards, QBR metrics packets, receivables and pipeline operations reviews, churn validation, or any controlled-enum customer-success operations output.
---

# ApexCloud Retention Operations JSON

## Core Workflow

Start from the prompt and the answer template. The template is the contract: preserve every top-level key, nested key, list shape, enum vocabulary, date string, and null-vs-number convention unless the prompt explicitly says otherwise. Return JSON only.

Use the API base URL supplied in the prompt. If the prompt names endpoint families, prefer those exact paths over guessing from dataset filenames. The service often exposes richer account-scoped endpoints than top-level file-style routes.

Work in this order:

1. Read the prompt parameters: account IDs, region, quarter/date range, months, A/R as-of date, event ID, due dates, and controlled enum lists.
2. Fetch only the relevant endpoint families and date ranges.
3. Build a local reconciliation table keyed by `account_id`, plus legal/display/alias names for A/R customer matching.
4. Apply exclusions and filters before aggregating.
5. Populate the template with deterministic rounding and controlled labels.
6. Recheck sort order, list length, enum spelling, and integer/currency/percentage precision.

## Endpoint Habits

Use account-scoped routes when the task is about specific customers:

- Account profile: `/api/accounts/<account_id>`
- Monthly account metrics: `/api/accounts/<account_id>/metrics?start=YYYY-MM&end=YYYY-MM`
- Support tickets: `/api/accounts/<account_id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`
- NPS responses: `/api/accounts/<account_id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`

Use portfolio routes for cross-account operations work:

- Accounts: `/api/accounts`
- Opportunities: `/api/opportunities`
- A/R aging: `/api/finance/ar-aging?as_of=YYYY-MM-DD`
- HR context: `/api/hr/summary`
- Event context: `/api/events/performance`

Use export routes for churn tasks:

- `/exports/churn/train.csv`
- `/exports/churn/validation.csv`
- `/exports/churn/candidates.csv`

Query parameters on broad collection endpoints may not filter server-side. Fetch and filter locally when in doubt.

## Field Conventions

Use `billing_arr_current` as current ARR when the prompt asks for revenue exposure or asks to confirm the billing ARR source. Do not substitute `crm_arr` unless the task explicitly asks for CRM revenue.

For monthly QBR metrics, account metrics provide recognized revenue and monthly health fields. Support ticket endpoints are useful for validating ticket counts and SLA health; if the task emphasizes operational support health, calculate SLA from actual ticket records.

For A/R aging:

- `current` is not overdue.
- Aged receivables usually mean `1_30 + 31_60 + 61_90 + 90_plus`.
- "Older aging buckets" usually means `61_90 + 90_plus`.
- Match A/R `customer_name` to account `legal_name`, `display_name`, and aliases; mark unmatched customers as unlinked.

For opportunities:

- Filter by `close_date` for the requested period.
- Treat `state == "open"` as open pipeline.
- Treat `stage == "Closed Won"` as won and `stage == "Closed Lost"` as lost when calculating win rate.
- Top open product line should normally be by open pipeline amount, not count, unless the prompt says count.

For churn exports:

- Exclude `customer_id` and `Churn` from model features.
- Preserve the requested candidate shortlist; do not rank accounts outside it.
- Use a reproducible logistic-style model when the prompt asks for coefficient direction.
- Report probabilities on a 0-1 scale rounded to three decimals, and percentages rounded to one decimal.

## Exclusion Rules

Apply these before counts, rates, and rankings:

- Support hygiene: exclude tickets where `is_duplicate` or `is_spam` is true when the field says clean tickets.
- NPS hygiene: exclude retracted responses when selecting latest or peak NPS.
- Account scope: include only the listed account IDs, even if other accounts look riskier.
- Date scope: use the exact months, quarter, close-date range, response-date range, and A/R as-of date in the prompt.
- Receivables scope: do not include A/R rows with zero balance in the requested overdue bucket definition.
- Churn scope: train on train export, validate on validation export, then score only the named candidates.

## Risk And Action Labels

Use controlled enum values exactly. A reasonable retention risk model should consider renewal window, ARR exposure, NPS, support/SLA health, usage trend, overdue receivables, tenure, lifecycle context, and expansion offset.

Map primary action by the dominant operational problem:

- `collections_followup`: meaningful overdue receivables, especially older buckets.
- `technical_recovery`: SLA degradation, high clean ticket volume, or usage decline.
- `renewal_save`: near-term renewal risk without a stronger collections or technical driver.
- `executive_qbr`: strategic/high-ARR account needing leadership alignment or sentiment recovery.
- `nurture_monitor`: low or offset risk, expansion offset, or watchlist follow-up.
- `no_action`: only when the template allows it and no material risk is present.

Common reason code mapping:

- `overdue_receivable`: aged receivables are present.
- `low_tenure_high_churn`: short tenure contributes to churn risk.
- `sla_degradation`: SLA compliance is weak or clean ticket load is high.
- `nps_drop`: low or declining sentiment.
- `usage_decline`: product usage falls over the analysis period.
- `renewal_window`: renewal date is near or recently passed as of the assessment date.
- `expansion_offset`: open expansion pipeline offsets some risk.
- `clean_billings`: no meaningful overdue receivables.

## Output Precision

Follow the prompt's precision rules exactly:

- Currency: two decimals.
- Percentages: one decimal.
- Churn probabilities: three decimals.
- Counts, ranks, and risk scores: integers.
- Dates: ISO `YYYY-MM-DD`.
- Months: `YYYY-MM`.
- Booleans: real JSON booleans, not strings.
- Missing values: use `null` only when the template permits it.

Sort lists as instructed. If no custom order is given, use the operational order implied by the task: risk lists by descending risk then exposure; receivables follow-ups by `customer_name` ascending; monthly packets by month ascending.

## Pitfalls

Do not build a broad analytics object when the task provides a template. Extra keys and wrong nesting can erase otherwise correct calculations.

Do not assume filenames are API paths. Route families are often nested and account-scoped.

Do not mix periods: Q2 activity, Q3 opportunities, A/R as-of dates, and follow-up due dates each have separate meanings.

Do not count all support tickets when the field asks for clean tickets.

Do not include `current` A/R in overdue balances.

Do not use CRM ARR for ARR-at-risk when the task asks for billing/current revenue exposure.

Do not rank every account in the environment when the prompt gives a shortlist.

Do not invent enum strings. Choose from the template or prompt vocabulary, even when a more natural phrase would read better.
