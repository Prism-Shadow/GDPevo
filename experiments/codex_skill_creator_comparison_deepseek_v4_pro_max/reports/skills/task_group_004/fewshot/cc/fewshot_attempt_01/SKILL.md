---
name: apexcloud-retention-ops
description: Build structured customer retention analytics from the ApexCloud Retention Operations API. Use when the user asks about ApexCloud account risk, renewal queues, QBR metrics packets, churn model validation, receivables/pipeline reviews, retention action boards, or any operational analytics that reference ApexCloud accounts, billing, support, NPS, AR aging, or churn exports. Also use for any task involving `<TASK_ENV_BASE_URL>` with ApexCloud endpoints.
---

# ApexCloud Retention Operations

Build structured JSON analytics from the ApexCloud Retention Operations API.
The API serves account profiles, monthly metrics, support tickets, NPS surveys,
billing snapshots, A/R aging, CRM opportunities, HR summaries, event
performance, churn model exports, and an account-metric CSV extract.

## Quick-start workflow

1. Read the prompt for the task type and list of account_ids.
2. Read the answer template from `input/payloads/answer_template.json`, which
   defines the exact output shape, controlled enum values, and precision rules.
3. Fetch account profiles for every account_id mentioned.
4. Fetch relevant time-series data (metrics, tickets, NPS) for the stated
   period and months. Fetch snapshots as-of the stated assessment date.
5. Compute derived indicators — see [references/rules.md](references/rules.md).
6. Select policy codes — see [references/rules.md](references/rules.md).
7. Assemble the output JSON using the controlled vocabularies in
   [references/enums.md](references/enums.md) and the precision rules below.

## Task-type decision tree

The shape of the output and which endpoints matter most depend on the task:

- **Renewal risk queue** — prompt mentions risk ranking, renewal standup,
  "risk accounts." Output top-N ranked with risk_score, risk_level,
  primary_action, reason_codes. Every listed account must be fetched.
- **QBR metrics packet** — prompt mentions QBR, quarterly business review,
  single account, monthly breakouts. Output qbr_metrics array, highlights,
  metric_sources, agenda_topics.
- **Receivables & pipeline review** — prompt mentions A/R, overdue, pipeline,
  finance, "followup." Cross-reference `/api/finance/ar-aging` customer_name
  with account `legal_name`/`account_aliases`. Link status is `linked` when a
  matching account_id exists, `unlinked` otherwise.
- **Churn model validation** — prompt mentions churn, model,
  `train.csv`/`validation.csv`/`candidates.csv`. Count rows, features. Rank
  candidates by predicted churn probability extracted from the candidates CSV.
- **Retention action board** — prompt mentions "board," multiple accounts, many
  data sources, follow-up calendar. Output all listed accounts in the standard
  retention board order with full action-board shape.

## Common processing rules

The detailed rules for data sourcing, derived metrics, and policy code
selection live in [references/rules.md](references/rules.md). At a high level:

- **ARR source**: For snapshot-based tasks use the billing snapshot as-of the
  assessment date. For current-value tasks use `billing_arr_current` from the
  account profile.
- **Clean tickets**: Fetch all tickets in the period via
  `/api/accounts/{id}/tickets`, then exclude `is_duplicate=true` and
  `is_spam=true`. The `clean_ticket_count` is the count of remaining tickets.
- **NPS**: Fetch NPS responses via `/api/accounts/{id}/nps`, exclude
  `retracted=true`. `latest_nps` is the score from the most recent remaining
  response. When the prompt asks for monthly NPS, use `nps_score` from the
  metrics endpoint (which may be null for months with no survey).
- **Overdue balance**: From `/api/finance/ar-aging`, filter to the as-of date,
  match `customer_name` to account `legal_name` or `account_aliases`.
  Overdue = `1_30 + 31_60 + 61_90 + 90_plus`.
- **SLA compliance**: From the metrics endpoint `sla_compliance` field.
- **Usage trend**: From the metrics endpoint `product_usage` field; compute
  month-over-month change. If declining over the period, flag `usage_decline`.
- **NPS trend**: If latest NPS dropped relative to prior months in the period
  or is below 50, flag `nps_drop`.
- **Renewal window**: Account is in the renewal window when its `renewal_date`
  falls within ~90 days after the assessment date.
- **Tenure risk**: `contract_tenure_months` ≤ 24 may indicate higher churn
  risk (flag `low_tenure_high_churn`). Longer tenure is protective.
- **Expansion offset**: When the account has open Q2 (or current-quarter)
  expansion opportunities with close dates in the analysis period, flag
  `expansion_offset`.
- **Cross-referencing A/R**: A/R records use `customer_name` (legal entity),
  not `account_id`. Match against `legal_name` and `account_aliases` from the
  accounts endpoint.
- **Churn candidate matching**: Candidates CSV uses `customer_id`; some rows
  use `acct_*` identifiers, others do not. Match `acct_*` values directly.

## Output conventions

Every output must be valid JSON matching the answer template shape exactly.

- **Precision**: currency values to 2 decimal places, percentages to 1 decimal
  place, churn probabilities to 3 decimal places, counts as integers, risk
  scores as integers.
- **Enum values**: use exactly the strings listed in the template's pipe-
  delimited sets or in [references/enums.md](references/enums.md). Never invent
  new enum values.
- **Ordering**: risk_accounts and action_board arrays are sorted by rank
  ascending (rank 1 first). overdue_followups are sorted by customer_name
  ascending.
- **Null handling**: When an NPS score is missing for a month, use `null` (JSON
  null, not a string). When an account has no overdue balance, use `0.0`.
- **Dates**: Use YYYY-MM-DD format.

## Reference files

Read these as needed during execution:

- [references/api-schema.md](references/api-schema.md) — complete field-level
  schema for every API endpoint.
- [references/enums.md](references/enums.md) — every controlled vocabulary
  value, its meaning, and when to use it.
- [references/rules.md](references/rules.md) — derived-metric formulas,
  risk-scoring heuristics, policy-code selection, cross-referencing rules.

When the prompt includes an answer template, that template is authoritative for
the output shape and takes precedence over any conflicting defaults described
here.
