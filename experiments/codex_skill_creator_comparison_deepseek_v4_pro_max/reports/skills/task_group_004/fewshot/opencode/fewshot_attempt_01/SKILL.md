---
name: apexcloud-retention-ops
description: Use the ApexCloud Retention Operations API to build renewal risk queues, QBR metrics packets, receivables and pipeline reviews, churn model validation readouts, and high-touch retention action boards. Use this skill whenever the task mentions ApexCloud, retention operations, renewal risk, customer success QBR, A/R aging, churn predictions, NPS analysis, support health, billing snapshots, expansion pipeline, or a task-environment base URL pointing to a retention operations API — even if the user does not name ApexCloud explicitly. Also use it when you see enumerated answer template fields like risk_level, primary_action, reason_codes, policy_codes, or controlled source enums typical of CS ops tooling.
---

# ApexCloud Retention Operations

This skill covers the end-to-end workflow for building structured retention and
revenue-operations reports from the ApexCloud Retention Operations API. The
tasks are JSON-in/JSON-out: you read an answer template, fetch across several
REST endpoints, compute derived fields with deterministic precision, and return
exactly the completed template.

## Quickstart

1. **Read the answer template** — it lives at `input/payloads/answer_template.json`
   or wherever the prompt points you. Every slot that is `null`, `0`, `0.0`, `""`,
   `[]`, or `false` is unfilled and needs your computed value.

2. **Identify the data you need.** Walk the template keys and map each one to the
   endpoints in [references/api.md](references/api.md). The prompt usually tells
   you which account IDs, date ranges, months, and quarters to use.

3. **Fetch all API data.** Parallelize fetches for independent resources (account
   profiles, metrics, tickets, NPS, billing snapshots, A/R aging, opportunities,
   HR summaries, events, churn exports). Use the base URL given in the prompt
   (often `<TASK_ENV_BASE_URL>` — substitute it before calling).

4. **Compute derived fields.** Follow the rules in
   [references/conventions.md](references/conventions.md) for ARR sourcing,
   overdue-balance aging-bucket sums, ticket counting, NPS resolution, trend
   classification, risk scoring, and link-status matching.

5. **Select controlled vocabulary values.** Every enum string the template
   requires is defined in [references/enums.md](references/enums.md). Policy
   codes are also listed there; choose the code that reflects the data sources
   and approach you actually used.

6. **Output only the completed JSON object.** No markdown fences, no commentary —
   just the raw JSON document.

## Workflow Pattern

Every ApexCloud task follows the same rhythm:

### Phase 1 — Parse the template

Do not skip this. The answer template tells you exactly what the task expects.
For each field, note its type and what endpoint(s) will supply its value. Build a
mental (or scratch) table: field → endpoint → computation. Ambiguous fields
(e.g. `current_arr` vs `revenue` vs `recognized_revenue`) are disambiguated by
reading `references/conventions.md`.

### Phase 2 — Gather all data

Fetch everything you will need before you start computing. The API is read-only
and idempotent; there is no reason to sequence calls that do not depend on each
other.

Common endpoint families (full shape catalog in `references/api.md`):

| Endpoint | Provides |
|---|---|
| `/api/accounts` | All accounts with ARR, tenure, segment, region, renewal date, CSM, aliases |
| `/api/accounts/{id}` | Single account profile |
| `/api/accounts/{id}/metrics` | Monthly recognized revenue, SLA%, NPS, usage %, seat count |
| `/api/accounts/{id}/tickets` | Support tickets with SLA flags, spam/duplicate markers |
| `/api/accounts/{id}/nps` | Individual NPS survey responses |
| `/api/billing/snapshots` | Quarterly billing ARR snapshots |
| `/api/finance/ar-aging` | A/R aging buckets (1-30, 31-60, 61-90, 90+ days) |
| `/api/opportunities` | CRM pipeline (open/closed, product lines) |
| `/api/hr/summary` | Headcount, unpaid claims by quarter and region |
| `/api/events/performance` | Event orders and revenue |
| `/exports/churn/train.csv` | Churn-model training rows |
| `/exports/churn/validation.csv` | Churn-model validation rows |
| `/exports/churn/candidates.csv` | Candidate accounts for churn ranking |

### Phase 3 — Compute and fill

Work field by field. Use the conventions reference for every derived value
(ARR source, overdue balance, ticket hygiene, NPS, trends, risk scoring,
account matching). Select controlled enums deliberately — do not guess.

For **risk scoring** (risk_score, risk_level): build a composite from the
available signals rather than using a single axis. The conventions reference
provides a scoring rubric derived from the train evidence.

For **ranking / ordering**: the prompt will tell you whether to return a
top-N (e.g. top 5 risk accounts) or all accounts in board order.

### Phase 4 — Validate and emit

Before returning:
- Currency values are to 2 decimal places.
- Percentage values are to 1 decimal place (except churn probabilities, which
  are to 3 decimal places).
- Counts are integers.
- Every enum value is one of the allowed strings in `references/enums.md`.
- Policy codes are selected from the set the template provides; default to the
  middle option unless a specific data source or approach warrants a different
  code.
- No extra keys exist beyond what the template defines.

## When outputs differ from per-account API values

Some API endpoints return data at a different grain than the template expects:

- **Account-profile ARR vs billing-snapshot ARR**: For retention tasks,
  prefer the billing snapshot that matches the assessment date. The account
  profile's `billing_arr_current` is a convenience field; the snapshots are
  the authoritative quarter-close source. When the task includes
  `model_checks.uses_billing_arr_source`, set it to `true`.

- **Metrics NPS vs NPS-endpoint NPS**: The metrics endpoint returns a single
  `nps_score` per month (the survey-aggregated value for that month, or `null`
  when no survey completed). The per-account NPS endpoint returns individual
  survey responses. For monthly QBR-style reporting, use the metrics endpoint.
  For "latest NPS," use the most recent non-null value from the NPS endpoint
  unless the task explicitly calls for metrics-endpoint values.

- **Tickets**: `clean_ticket_count` means non-spam, non-duplicate tickets.
  Always filter out `is_spam: true` and `is_duplicate: true` before counting.

## Reference files

- [references/api.md](references/api.md) — Full endpoint catalog with field shapes.
- [references/enums.md](references/enums.md) — Every controlled string value organized by category.
- [references/conventions.md](references/conventions.md) — Precision rules, computation recipes, risk-scoring rubric, and matching logic.
