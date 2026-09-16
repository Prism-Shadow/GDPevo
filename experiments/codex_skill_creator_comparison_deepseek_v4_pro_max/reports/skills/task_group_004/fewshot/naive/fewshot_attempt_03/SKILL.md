---
name: apexcloud-retention-ops
description: Solve ApexCloud Retention Operations tasks by querying the task environment API, applying controlled vocabularies, deterministic precision rules, and standardized business-logic patterns for renewal risk queues, QBR packets, receivables reviews, churn model validation, and retention action boards.
---

# ApexCloud Retention Operations

## When to use this skill

Apply this skill whenever the task references the ApexCloud Retention Operations API, asks you to build retention or renewal artifacts for ApexCloud accounts, or uses any of the controlled enums and precision rules defined here. The skill covers five recurring task families: renewal risk queues, QBR metrics packets, receivables and pipeline reviews, churn model validation, and high-touch retention boards.

## Core workflow

1. Read the task prompt thoroughly and note the assessment date, analysis period, target account IDs, and the required output shape (given as a payload template or described inline).
2. Fetch data from the relevant API endpoints described in [API Endpoints](references/api-endpoints.md). Prefer parallel requests for independent calls (e.g., fetching accounts, metrics, tickets, and NPS simultaneously).
3. Transform raw API responses into derived metrics following the [Business Rules](references/business-rules.md).
4. Select policy codes using the middle-option rule from [Policy Codes](references/policy-codes.md).
5. Assemble the final JSON response using the [Controlled Vocabularies](references/vocabularies.md) and [Precision Rules](references/precision-rules.md). Return only valid JSON with no surrounding text.

## Quick reference: precision

- Currency (ARR, revenue, overdue balances, pipeline values): always 2 decimal places.
- Percentages (accuracy, SLA compliance, win rate): always 1 decimal place.
- Counts (tickets, accounts, headcount, rows): always integers.
- Risk scores: always integers.
- Churn probabilities: always 3 decimal places.

Full rules at [Precision Rules](references/precision-rules.md).

## Quick reference: controlled enums

**Risk levels:** `critical`, `high`, `medium`, `low`

**Primary actions:** `executive_qbr`, `collections_followup`, `technical_recovery`, `renewal_save`, `nurture_monitor`, `no_action`

**Reason codes:** `overdue_receivable`, `low_tenure_high_churn`, `sla_degradation`, `nps_drop`, `usage_decline`, `renewal_window`, `expansion_offset`, `clean_billings`

**Ticket trends:** `improving`, `worsening`, `flat`

**Metric sources:** `crm_closed_won`, `support_export`, `sla_report`, `nps_survey`, `billing_snapshot`, `ar_aging`, `pipeline_crm`, `event_dashboard`, `hr_report`

**Review owners:** `solutions_engineering`, `customer_success`, `finance_ops`

**Agenda topics:** `partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion`

**Link status:** `linked`, `unlinked`

**Accuracy bands:** `below_70`, `70_to_79`, `80_to_89`, `90_plus`

**Tenure coefficient direction:** `negative`, `positive`, `zero`

Full vocabularies at [Controlled Vocabularies](references/vocabularies.md).

## Quick reference: policy codes

When an answer template shows a policy code field with three pipe-separated options (e.g., `"RS-2|RS-6|RS-9"`), always select the middle option (e.g., `"RS-6"`). This rule is consistent across all task families. Full catalog at [Policy Codes](references/policy-codes.md).

## Quick reference: business rules

- **Overdue receivables** always trigger `collections_followup` as the primary action.
- **SLA degradation** and **usage decline** without overdue receivables typically map to `technical_recovery`.
- **Renewal window** combined with low tenure or NPS drops maps to `renewal_save`.
- **Clean billings** on otherwise healthy accounts maps to `nurture_monitor` or `no_action`.
- `arr_at_risk` is the sum of `current_arr` for all accounts with risk level `critical` or `high`.
- Ticket trend: compare first-month and last-month ticket counts to determine `improving`, `worsening`, or `flat`.
- CRM account linking: match A/R customer names against CRM `/api/accounts` names by normalizing case and whitespace and checking for substring or token overlap. Mark `linked` when a match is found, `unlinked` otherwise.
- For churn model validation, parse CSV exports with the pandas library (the runtime has it available). Read `train.csv` and `validation.csv` to count rows, features, and compute accuracy by comparing predictions against labels.
- Calendar due dates: when the prompt specifies per-action due dates, use those exact values. When a prompt provides only one due date for all overdue items, propagate that date. For `no_action` accounts, set `next_touch_due_date` to `null`.

Full rules at [Business Rules](references/business-rules.md).

## Task family patterns

When the prompt clearly matches one of these families, use the corresponding pattern as a starting point and adapt it to the specific parameters (accounts, periods, templates) given in the task:

- **Renewal risk queue**: Fetch account profiles, metrics, tickets, NPS, billing snapshots, and A/R aging for the specified accounts. Assign risk scores and levels based on cumulative risk factors. Return the top N ranked accounts plus a portfolio summary.
- **QBR metrics packet**: Fetch a single account's monthly metrics, tickets, NPS, and SLA data for the quarter. Compute monthly aggregates and derive highlights (averages, peaks, trends). Select metric sources and agenda topics.
- **Receivables and pipeline review**: Pull A/R aging, the full accounts list, opportunities, HR summary, and event performance. Cross-reference A/R customers with CRM accounts. Sort overdue followups by customer name ascending.
- **Churn model validation and ranking**: Fetch the three churn CSV exports. Validate training and validation row counts, feature count, and accuracy. Rank candidate accounts by predicted churn probability descending.
- **High-touch retention board**: Combine account profiles, billing, support health, NPS, receivables, usage, and expansion opportunities for the specified accounts. Return all accounts in board order with a segment summary and followup calendar.

## API endpoint quick reference

See the full endpoint catalog at [API Endpoints](references/api-endpoints.md). Key families:

- `/api/accounts` and `/api/accounts/{id}` -- account profiles and legal names
- `/api/accounts/{id}/metrics?start=YYYY-MM&end=YYYY-MM` -- monthly revenue and usage metrics
- `/api/accounts/{id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` -- support tickets with SLA data
- `/api/accounts/{id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` -- NPS survey responses
- `/api/accounts/{id}/billing` and `/api/billing/snapshots` -- billing and ARR data
- `/api/accounts/{id}/ar-aging` and `/api/finance/ar-aging` -- accounts receivable aging
- `/api/opportunities` -- CRM pipeline opportunities
- `/api/hr/summary` -- HR headcount and claims
- `/api/events/performance` -- event orders and revenue
- `/exports/churn/train.csv`, `/exports/churn/validation.csv`, `/exports/churn/candidates.csv` -- churn model exports
- `/exports/account_metric_extract.csv` -- bulk account metric extract

## Environment

The API base URL is provided through a `<TASK_ENV_BASE_URL>` placeholder in the prompt. Replace it with the actual URL before making requests. All endpoints are unauthenticated GET requests. Use standard HTTP GET with query parameters as documented.

## Output format

Return only valid JSON. Do not wrap it in markdown fences, code blocks, or explanatory text unless the task explicitly asks for a different format. Follow the output shape shown in the task's payload template exactly.
