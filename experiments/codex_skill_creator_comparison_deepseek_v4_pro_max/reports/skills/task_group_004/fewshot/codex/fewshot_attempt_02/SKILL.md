---
name: apexcloud-retention-ops
description: ApexCloud Retention Operations API client for customer success and revenue operations workflows. Use when the task involves pulling data from the ApexCloud Retention Ops API (account profiles, metrics, support tickets, NPS, billing snapshots, AR aging, opportunities, HR summary, event performance, churn exports, or account metric extracts) to build structured deliverables such as renewal risk queues, QBR metrics packets, AR and pipeline operations reviews, churn model validation and outreach rankings, or high-touch retention action boards.
---

# ApexCloud Retention Operations

API-driven skill for the ApexCloud Retention Operations service. Use this when
the task requires calling the API to pull account, financial, and operational
data and assembling a structured JSON response with controlled labels,
deterministic precision, and policy codes.

## Base URL

The task prompt always provides the base URL as `<TASK_ENV_BASE_URL>`. Replace
that token with the actual URL from the task before making any requests. All
endpoints are `GET` only and require no authentication.

## Endpoint Catalog

| Endpoint | Key shape | Notes |
|---|---|---|
| `GET /api/accounts` | `.accounts[]` — list of all account profiles | Full-account list for cross-portfolio work |
| `GET /api/accounts/{id}` | Single account object | Profile detail for one account |
| `GET /api/accounts/{id}/metrics?start=YYYY-MM&end=YYYY-MM` | `.metrics[]` — monthly metric rows | Revenue, SLA, NPS, usage, seats per month |
| `GET /api/accounts/{id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` | `.tickets[]` — support ticket records | SLA fields, severity, status, is_duplicate, is_spam |
| `GET /api/accounts/{id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` | `.nps_responses[]` — NPS survey records | score, retracted flag, survey_channel |
| `GET /api/billing/snapshots` | `.snapshots[]` — quarterly billing snapshots | billing_arr, mrr, as_of date |
| `GET /api/finance/ar-aging` | `.ar_aging[]` — AR aging by quarter | current, 1_30, 31_60, 61_90, 90_plus buckets |
| `GET /api/opportunities` | `.opportunities[]` — CRM pipeline | stage, state, amount, close_date, product_line |
| `GET /api/hr/summary` | `.hr_summary[]` — HR ops by region/quarter | headcount, unpaid_claims, open_advances |
| `GET /api/events/performance` | `.event_performance[]` — event ops by event/quarter | event_revenue, event_orders, product_revenue |
| `GET /exports/churn/train.csv` | CSV — churn training data | 19 features + Churn label |
| `GET /exports/churn/validation.csv` | CSV — churn validation data | Same schema as train.csv |
| `GET /exports/churn/candidates.csv` | CSV — candidate accounts for scoring | Same features, no Churn label |
| `GET /exports/account_metric_extract.csv` | CSV — normalized metric time series | account-level monthly metrics across all periods |

Full field schemas for every endpoint are in
[references/api_reference.md](references/api_reference.md).

## Precision Rules

Follow these output conventions exactly unless the task prompt overrides a
specific format:

- **Currency** (ARR, revenue, overdue balance, pipeline amounts): 2 decimal
  places, e.g. `1416439.47`
- **Percentages** (SLA compliance, win rate, accuracy): 1 decimal place,
  e.g. `93.3`
- **Churn probabilities**: 3 decimal places, e.g. `0.102`
- **Counts** (tickets, accounts, headcount, orders): integers
- **Risk scores**: integers
- **NPS scores**: integers (null when no survey response exists)
- **Months**: `YYYY-MM` format (e.g. `2026-04`)
- **Dates**: `YYYY-MM-DD` format (e.g. `2026-07-22`)

## Controlled Vocabulary

Every task requires picking values from a fixed controlled vocabulary. The
complete catalog with all enum labels is in
[references/controlled_vocabulary.md](references/controlled_vocabulary.md). Load
it at the start of every task so you never invent a label.

Key categories:

- **risk_level**: `critical`, `high`, `medium`, `low`
- **primary_action**: `executive_qbr`, `collections_followup`,
  `technical_recovery`, `renewal_save`, `nurture_monitor`, `no_action`
- **reason_codes**: `overdue_receivable`, `low_tenure_high_churn`,
  `sla_degradation`, `nps_drop`, `usage_decline`, `renewal_window`,
  `expansion_offset`, `clean_billings`
- **policy_codes**: multi-code groups — pick exactly one code per group after
  assessing the data shape (see controlled vocabulary reference for the full
  list and matching guidance)

## Task Type Patterns

The API supports five core task patterns. See
[references/workflows.md](references/workflows.md) for step-by-step recipes for
each one:

1. **Renewal Risk Queue** — Cross-account ranking by composite retention risk
2. **QBR Metrics Packet** — Single-account quarterly business review data
3. **Receivables & Pipeline Operations Review** — AR aging to CRM linking to
   pipeline summary to HR/event context
4. **Churn Model Validation & Outreach Ranking** — Validate model exports, rank
   candidate accounts by churn probability
5. **High-Touch Retention Action Board** — Full-portfolio retention board with
   segment summaries and follow-up calendar

## General Workflow

1. Read the task prompt to identify which task type, which accounts, which
   period, and which output shape is required.
2. Read [references/controlled_vocabulary.md](references/controlled_vocabulary.md)
   to load the full controlled-label catalog.
3. Read [references/workflows.md](references/workflows.md) and follow the
   recipe for the identified task type.
4. Fetch only the endpoints needed for the specific task — never pull
   unnecessary data.
5. Compute derived values from API responses using the formulas in the workflow
   recipe (e.g., clean ticket count = tickets minus duplicates and spam;
   overdue balance = sum of aging buckets beyond current).
6. Assemble the response JSON following the exact shape and enum constraints
   from the task template.
7. Apply deterministic precision rules from the **Precision Rules** section
   unless the task overrides a specific rule.

## Policy Codes

Every task includes a `policy_codes` object. Pick one code per key by matching
the data characteristics to the code descriptions in
[references/controlled_vocabulary.md](references/controlled_vocabulary.md). Do
not guess — each code maps to a specific observable condition in the API
responses.

## Important Constraints

- Never invent enum values or policy codes not listed in the controlled
  vocabulary.
- Return only valid JSON — no markdown wrappers, no commentary outside the JSON
  structure.
- When a task provides an answer template in
  `input/payloads/answer_template.json`, match its structure exactly, filling
  every required field.
- The `/api/accounts/{id}/billing` and `/api/accounts/{id}/ar-aging` endpoints
  do not exist — use `/api/billing/snapshots` and `/api/finance/ar-aging`
  instead and filter by account/quarter.
- When counting "clean tickets", exclude tickets where `is_duplicate` or
  `is_spam` is true.
- NPS `latest_nps` means the most recent non-null, non-retracted score in the
  period. If none exists, use null or 0 as specified by the task template.
- Overdue balance for AR aging = `1_30 + 31_60 + 61_90 + 90_plus` (sum of all
  non-current buckets). Do not include the `current` bucket.
- The `billing_arr_current` field on the account profile is the current billing
  ARR. The CRM `crm_arr` field is the CRM-reported ARR. When a task asks for
  `current_arr`, prefer `billing_arr` from the latest billing snapshot matching
  the assessment date unless the task specifies otherwise.
- When linking AR customers to CRM accounts, match `customer_name` from AR aging
  against `legal_name` or `account_aliases` from the accounts list. If no match
  is found, set `link_status` to `"unlinked"` and `account_id` to `null`.
