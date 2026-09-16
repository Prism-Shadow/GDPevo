---
name: apexcloud-retention-ops
description: Use the ApexCloud Retention Operations API to build renewal risk queues, QBR metrics packets, receivables and pipeline reviews, churn model validations, and high-touch retention action boards. Trigger when the user mentions ApexCloud, retention operations, renewal risk, QBR metrics, receivables, churn models, or retention action boards — even if they do not name the API explicitly.
---

# ApexCloud Retention Operations API

A skill for querying the ApexCloud Retention Operations API and assembling structured operational reports for customer success, revenue operations, and analytics teams.

The API is a fixed-seed deterministic service (seed 4004) that models a SaaS company's retention data surface. Every endpoint returns JSON or CSV and every numeric value is stable across calls. There is no authentication, no pagination, and no write operations.

## Quick start

The task prompt will give you the base URL (typically `http://task-env:9004`). Read the prompt carefully to extract:

1. **Which task family** is being asked for (risk ranking, QBR metrics, receivables review, churn validation, or retention action board).
2. **The date scope**: quarters, months, date ranges, as-of dates.
3. **Which account IDs** to include.
4. **Any task-specific parameters** like follow-up due dates, region filters, or event filters.

Then pull data from the relevant endpoints (see [references/endpoints.md](references/endpoints.md)), apply the business-logic conventions described below and in [references/patterns.md](references/patterns.md), and return exactly the JSON shape the prompt requests.

---

## API conventions

### Base URL

The task prompt uses a placeholder like `<TASK_ENV_BASE_URL>`. Replace it with the actual URL before making requests (e.g. `http://task-env:9004`).

### Query parameters

- **Account metrics**: `start=YYYY-MM&end=YYYY-MM` (inclusive).
- **Account tickets**: `start=YYYY-MM-DD&end=YYYY-MM-DD` (inclusive).
- **Account NPS**: `start=YYYY-MM-DD&end=YYYY-MM-DD` (inclusive).
- All other endpoints accept no query parameters and return the full dataset.

### Response shapes

All endpoints return flat JSON arrays (wrapped in an envelope object) or CSV text. There is no nested pagination; the full dataset is returned in a single response. Read [references/endpoints.md](references/endpoints.md) for the exact shape of every endpoint.

---

## Core domain concepts

### ARR (Annual Recurring Revenue)

There are three ARR sources in the API. The **billing snapshot** is the authoritative source for current ARR in reports because it is point-in-time as of a specific quarter end.

| Source | Where | Meaning |
|--------|-------|---------|
| `billing_arr_current` | `/api/accounts` profile | Current billing-system ARR; may not match quarter-end snapshots |
| `crm_arr` | `/api/accounts` profile | CRM-recorded ARR; lagged or rounded |
| `billing_arr` | `/api/billing/snapshots` | Quarter-end billing snapshot; use **this** for reports that need point-in-time ARR |

When a report asks for "current ARR" as of a quarter-end date, use the matching billing snapshot from `/api/billing/snapshots`. The snapshots are keyed by `account_id` and `as_of` date. Pick the snapshot whose `as_of` matches the task's assessment date.

### Clean ticket count

Tickets come from `/api/accounts/{id}/tickets`. Compute the clean count by excluding:

- Tickets where `is_spam` is `true`
- Tickets where `is_duplicate` is `true`
- Tickets where `status` is `"cancelled"`

Everything else counts. The ticket count in the monthly metrics endpoint (`support_ticket_count`) is the raw total including spam, duplicates, and cancelled tickets. Use the `/tickets` endpoint directly for clean counts.

### NPS

NPS data exists in two places with different meanings:

| Source | What it gives you |
|--------|------------------|
| `/api/accounts/{id}/metrics` → `nps_score` | NPS score recorded for that month (may be `null` when `survey_status` is `"missing"`) |
| `/api/accounts/{id}/nps` → individual responses | Raw survey responses with dates and channels |

For reports asking for "latest NPS", use the most recent individual response from the NPS endpoint, filtering out responses where `retracted` is `true`. For reports asking for monthly NPS values, use the metrics endpoint.

### NPS trend (drop detection)

To determine whether an account has an NPS drop, compare the latest valid NPS response to the previous one within the analysis period. If the latest score is lower than the prior score, flag `nps_drop`. If there is only one response in the period, compare the latest to the previous-quarter NPS from the metrics endpoint. An account with a single NPS response of 17 after a previous-quarter score of 65 is a clear drop; one with 39 from a prior-quarter 17 is a recovery.

### SLA compliance

The metrics endpoint includes `sla_compliance` as a percentage (e.g. `85.9` means 85.9%). This is the aggregate SLA compliance for that account-month. You can also derive SLA health from the tickets endpoint by checking `first_response_sla_met` and `resolution_sla_met` fields on individual tickets.

An account has `sla_degradation` when its average SLA compliance over the analysis period is below 90% or when at least one ticket had a missed SLA (either `first_response_sla_met` is `false` or `resolution_sla_met` is `false`).

### Usage trend

The metrics endpoint includes `product_usage` as a percentage. Compare the earliest month in the analysis period to the latest month. If usage dropped across the period, flag `usage_decline`. Usage is per-account and varies month to month; a decline of more than 2 percentage points across the period is considered a decline.

### A/R aging and overdue balance

The `/api/finance/ar-aging` endpoint returns aging records keyed by **customer name** (not account ID). Each record has aging buckets: `current`, `1_30`, `31_60`, `61_90`, `90_plus`.

**Overdue balance** = `61_90` + `90_plus`. This is the aging view of receivables that are more than 60 days past due.

To connect an A/R record to an account, match the `customer_name` against the account's `legal_name` or any entry in `account_aliases` from `/api/accounts`. Not every customer name in A/R aging will match an account ID. Those are considered unlinked.

### Account lifecycle

The `lifecycle_status` field on accounts can be `active`, `implementation`, `renewal_risk`, or `paused`. Accounts in `implementation` or `paused` status may need different treatment depending on the task.

### Account tenure

`contract_tenure_months` from the account profile is the number of months the account has been active. Low-tenure accounts are higher churn risk. In the churn model, the tenure coefficient is negative, meaning lower tenure predicts higher churn probability.

### Renewal window

An account is in its renewal window when the `renewal_date` falls within 90 days after the assessment date. Accounts renewing soon are at elevated risk because the renewal decision is imminent.

### Expansion

An account has `expansion_offset` when it has open expansion opportunities whose close dates fall within the analysis period. Expansion revenue can offset churn risk; flag it as a mitigating factor.

---

## Task families

There are five recurring report types. The task prompt will describe one of them. Read [references/patterns.md](references/patterns.md) for detailed pipelines for each.

1. **Renewal risk queue** — Rank a given set of accounts by renewal risk, producing `risk_accounts` with risk scores, levels, actions, and reason codes.
2. **QBR metrics packet** — Monthly metrics for a single account plus highlights, metric sources, review plan, and agenda topics.
3. **Receivables and pipeline review** — Cross-referenced A/R aging, CRM pipeline, HR, and events data.
4. **Churn model validation** — Validate churn model exports and rank candidates by predicted probability.
5. **Retention action board** — Full-board reconciliation of account health, billing, support, NPS, receivables, usage, and expansion.

---

## Controlled vocabularies

Use only these exact string values for the corresponding fields. Do not invent new values. See [references/vocabulary.md](references/vocabulary.md) for the complete set including all policy code mappings.

### Risk levels
`critical`, `high`, `medium`, `low`

### Primary actions
`executive_qbr`, `collections_followup`, `technical_recovery`, `renewal_save`, `nurture_monitor`, `no_action`

### Reason codes
`overdue_receivable`, `low_tenure_high_churn`, `sla_degradation`, `nps_drop`, `usage_decline`, `renewal_window`, `expansion_offset`, `clean_billings`

### Metric sources
`crm_closed_won`, `support_export`, `sla_report`, `nps_survey`, `billing_snapshot`, `ar_aging`, `pipeline_crm`, `event_dashboard`, `hr_report`

### Ticket trends
`improving`, `worsening`, `flat`

### Review owners
`solutions_engineering`, `customer_success`, `finance_ops`

### Agenda topics
`partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion`

### Link status
`linked`, `unlinked`

### Tenure risk direction
`negative`, `positive`, `not_assessed`

### Accuracy bands
`below_70`, `70_to_79`, `80_to_89`, `90_plus`

---

## Output conventions

Every output must be valid JSON only. No markdown wrappers, no explanatory text.

**Precision rules:**
- Currency values: 2 decimal places (e.g. `1250000.25`)
- Percentages: 1 decimal place (e.g. `93.3`)
- Risk scores and integer counts: integers (e.g. `100`, `8`)
- Churn probabilities: 3 decimal places (e.g. `0.102`)

**Ordering:**
- Risk accounts: ordered by descending risk score (highest risk first).
- Overdue follow-ups: ordered by `customer_name` ascending (alphabetical).
- Retention board: ordered by descending risk (the task specifies the board sort order).
- QBR metrics: ordered by month ascending.

**Null handling:**
- Use `null` (JSON null, not the string `"null"`) for missing NPS scores and `null` for `account_id` in unlinked follow-ups.
- Use `0.0` for zero currency, not `0`.
- Use `null` for `next_touch_due_date` when the action is `no_action`.

**Array handling:**
- Empty arrays use `[]`, not null.
- Reason codes are arrays. Order them by significance to the account's risk profile (most impactful first).
- When `clean_billings` appears as a reason code, it always appears last in the array as a positive signal.

**Boolean fields:**
- Use JSON `true` / `false`, not strings.

---

## Working efficiently

The API returns the full dataset for most endpoints. Prefer pulling `/api/accounts` (all), `/api/billing/snapshots` (all), `/api/finance/ar-aging` (all), and `/api/opportunities` (all) once rather than making per-account calls for every piece of data. Then filter locally.

For per-account endpoints (`/metrics`, `/tickets`, `/nps`), make one call per account with the relevant date range. These calls are cheap and deterministic.

For CSV exports (`/exports/churn/*`), read the raw text and parse it with a CSV library. The exports have header rows and are standard comma-separated format.

When computing derived values (risk scores, rankings, win rates, etc.), do the computation explicitly in a Python script that reads the API responses and produces the final JSON. This is more reliable than manual arithmetic and makes it easy to verify intermediate results against the API data.

---

## Reference files

- [endpoints.md](references/endpoints.md) — Full API endpoint reference with response shapes and field descriptions.
- [vocabulary.md](references/vocabulary.md) — Complete controlled vocabulary including all policy code mappings.
- [patterns.md](references/patterns.md) — Step-by-step pipelines and business rules for each of the five task families.
