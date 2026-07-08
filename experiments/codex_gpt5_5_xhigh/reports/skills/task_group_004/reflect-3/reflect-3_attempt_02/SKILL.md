---
name: apexcloud-retention-ops
description: Use this skill for ApexCloud Retention Operations tasks that ask for renewal-risk queues, QBR metric packets, receivables and pipeline operations reviews, churn validation, or high-touch retention action boards. Trigger whenever the prompt references ApexCloud customer success, retention operations, support/NPS/billing/A/R reconciliation, churn exports, or structured JSON outputs with controlled enum labels.
---

# ApexCloud Retention Operations

Use this workflow to build structured JSON answers from the ApexCloud Retention Operations API. The task usually combines CRM accounts, monthly account metrics, support tickets, NPS, billing snapshots, A/R aging, opportunities, HR context, event performance, and churn exports.

## Core Workflow

1. Read the prompt and the answer template before touching data.
2. Copy the required top-level structure, nested field names, enum vocabulary, and output cardinality from the template.
3. Fetch only the endpoint families named or implied by the prompt.
4. Filter locally by account IDs, dates, months, quarter, region, and event IDs from the prompt.
5. Reconcile accounts by `account_id` first, then exact legal name or listed aliases. Avoid fuzzy matching unless the prompt explicitly asks for it.
6. Apply exclusions before counting or scoring: duplicate/spam tickets, retracted NPS, out-of-window opportunities, non-posted billing snapshots, and A/R records from the wrong `as_of` date.
7. Round only at the final output step: currency to 2 decimals, percentages to 1 decimal, integer counts and ranks, churn probabilities to 3 decimals when requested.
8. Return JSON only. Do not include explanatory text, markdown, comments, or trailing notes.

## API Habits

Use the task-provided ApexCloud environment entrypoint. When the prompt shows a local host that is not directly reachable, use the environment access information supplied with the task to reach the same service. Do not inspect local environment source or data files.

Reliable endpoint patterns:

- `/api/accounts` for the account roster.
- `/api/accounts/<account_id>` for one account profile.
- `/api/accounts/<account_id>/metrics?start=YYYY-MM&end=YYYY-MM` for monthly revenue, usage, SLA, support count, and NPS fields.
- `/api/accounts/<account_id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` for ticket-level support hygiene.
- `/api/accounts/<account_id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` for survey responses.
- `/api/billing/snapshots` for posted ARR/MRR snapshots. Filter by `account_id` and quarter-ending `as_of`.
- `/api/finance/ar-aging?as_of=YYYY-MM-DD` for A/R aging.
- `/api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD` for close-date-windowed opportunity work.
- `/api/hr/summary?quarter=YYYY-QN` for regional HR context.
- `/api/events/performance?event=<event_id>&quarter=YYYY-QN` for event context.
- `/exports/churn/train.csv`, `/exports/churn/validation.csv`, and `/exports/churn/candidates.csv` for churn tasks.

If a filter parameter is ignored by an endpoint, fetch the broad payload and filter the returned records yourself.

## Field Conventions

Prefer template fields over prose if they conflict, but do not invent extra top-level sections when the prompt explicitly lists allowed top-level keys.

For account revenue exposure:

- Use `billing_arr` from the posted billing snapshot at the requested as-of date when the task asks for current ARR or says to use billing as the revenue source.
- Use `recognized_revenue` from monthly metrics for monthly QBR revenue rows unless the task specifically asks for MRR or ARR.
- Use `crm_arr` only when the prompt asks for CRM-sourced revenue or pipeline CRM.

For support:

- `clean_ticket_count` excludes `is_duplicate` and `is_spam`.
- Support ticket counts in health or risk outputs should usually use clean tickets.
- SLA degradation should be based on clean tickets with missed first-response or resolution SLA, or on monthly `sla_compliance` when the prompt asks for a metrics packet.

For NPS:

- Ignore retracted responses.
- Latest NPS means the latest valid response in the requested date range.
- `nps_drop` means worsening sentiment over the requested monthly window, not merely a low absolute score.

For receivables:

- Overdue balance is normally `1_30 + 31_60 + 61_90 + 90_plus`.
- When a prompt says "older aging buckets," scope the trigger and follow-up amount to `61_90 + 90_plus`.
- Sort receivables follow-ups by `customer_name` ascending when requested.
- Use `linked` only for exact CRM account matches by legal name or explicit alias; otherwise use `unlinked` and `account_id: null`.

For opportunities:

- Treat `start` and `end` as the close-date window unless the prompt says otherwise.
- Q2/Q3 pipeline summaries should separate `Closed Won`, `Closed Lost`, and open opportunities.
- `win_rate_pct` is won divided by won plus lost closed opportunities.
- `top_open_product_line` is the product line with the largest open opportunity amount, not the largest count.

For HR/event context:

- If the prompt says all regions, sum regional HR rows for the quarter.
- Event context should be filtered by both event ID and quarter.

## Risk and Action Labels

Use controlled labels exactly as the template lists them. Common mappings:

- `collections_followup`: older receivables or materially overdue A/R is the dominant issue.
- `technical_recovery`: SLA misses, high clean-ticket volume, or support-driven customer health decline dominates.
- `renewal_save`: renewal is inside or already past the assessment window and commercial retention is the primary concern.
- `executive_qbr`: strategic or enterprise account needs senior engagement but lacks a more urgent collections or technical trigger.
- `nurture_monitor`: low-risk account with clean billing and no urgent recovery trigger.

Reason codes should be evidence-backed:

- `overdue_receivable`: nonzero overdue A/R, especially older buckets.
- `low_tenure_high_churn`: short tenure combined with churn-risk signals; do not use for long-tenure accounts.
- `sla_degradation`: clean-ticket SLA misses or declining SLA metrics.
- `nps_drop`: NPS worsens across the period or latest valid NPS is clearly weak in context.
- `usage_decline`: product usage declines across the requested months.
- `renewal_window`: renewal date is close to, inside, or just past the assessment window.
- `expansion_offset`: meaningful open expansion pipeline offsets gross ARR exposure.
- `clean_billings`: no meaningful overdue receivables.

## Churn Validation

For churn export tasks:

1. Load train, validation, and candidate CSVs from the API exports.
2. Treat `Churn` as the binary target.
3. Use the same feature columns for train, validation, and candidates, excluding `customer_id` and `Churn`.
4. One-hot encode categorical columns and keep numeric columns numeric; report whether feature count means raw columns or transformed columns based on the template/prompt wording.
5. Validate on the validation export before ranking candidates.
6. Rank only the candidate IDs requested in the prompt.
7. Report probabilities on a 0-1 scale, rounded to 3 decimals.
8. Map outreach actions from the dominant risk signal, not just from probability rank.

Be careful with arbitrary model choices: a high validation accuracy alone does not guarantee the expected ranking. Prefer a simple, reproducible model and document its implied tenure direction in the requested field.

## Common Pitfalls

- Do not use local source files, hidden outputs, evaluator files, or notes as data sources.
- Do not call environment setup scripts if the remote service is already available.
- Do not count duplicate or spam tickets in clean support metrics.
- Do not include retracted NPS responses.
- Do not use Q4/current account `billing_arr_current` when the prompt asks for Q2 or Q3 as-of ARR; use the matching billing snapshot.
- Do not fuzzy-link A/R customer names unless explicitly instructed; subsidiaries, foundations, and country variants may be separate receivable customers.
- Do not let expansion pipeline erase ARR exposure unless the output specifically asks for net exposure.
- Do not sort boards alphabetically unless requested; sort by the prompt's stated ranking, action priority, or risk order.
- Do not omit policy-code fields when they appear in the answer template, unless the prompt explicitly forbids extra top-level keys.
- Do not change enum spelling, casing, or date formats.

## Final JSON Checklist

Before returning:

- Every required list has the exact requested length.
- Ranks are consecutive integers starting at 1.
- Dates match `YYYY-MM-DD`; months match `YYYY-MM`.
- Currency fields have two decimals.
- Percent fields have one decimal.
- Counts and risk scores are integers.
- Null account IDs are actual JSON `null`, not the string `"null"`.
- Enum fields exactly match the template vocabulary.
- Top-level keys match the prompt/template contract.
