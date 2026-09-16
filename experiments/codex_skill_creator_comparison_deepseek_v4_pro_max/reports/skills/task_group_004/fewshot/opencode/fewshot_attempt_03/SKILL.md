---
name: apexcloud-retention-ops
description: Build structured retention operations outputs from the ApexCloud Retention Operations API (task-env:9004). Use when the task involves ApexCloud, retention operations, renewal risk queues, QBR metrics packets, receivables reviews, churn model validation, action boards, customer success analytics, or any task that references `<TASK_ENV_BASE_URL>`, `http://task-env:9004`, or the environment_access.md endpoint list. Trigger even when the user describes the work in business terms (renewal risk, QBR prep, collections follow-up, churn ranking) without naming the API explicitly.
---

# ApexCloud Retention Operations Skill

Build deterministic JSON outputs from the ApexCloud Retention Operations API. The API is at `<TASK_ENV_BASE_URL>` (typically `http://task-env:9004`) with no authentication.

## Quick start

1. Read the task prompt carefully to identify the output shape required — every task has a specific JSON template in `input/payloads/answer_template.json` or described inline.
2. Fetch data from the relevant API endpoints (see [API Reference](references/api_reference.md)).
3. Compute derived fields using the rules in [Computations](references/computations.md).
4. Apply the [controlled vocabulary](references/vocabulary.md) for all enum fields.
5. Format the JSON output with deterministic precision and return only valid JSON.

## Precision rules

Every task requires these formatting rules unless the prompt says otherwise:

- **Currency values**: exactly 2 decimal places (e.g. `1250000.00`)
- **Counts**: integers
- **Percentages**: 1 decimal place (e.g. `85.0`)
- **Risk scores**: integers
- **Churn probabilities**: 3 decimal places (e.g. `0.075`)
- **Null values**: use `null` (JSON null), not `0` or `""` when data is genuinely absent. Use `0.0` or `""` only when the template shows that default.

## API usage patterns

The base URL is `<TASK_ENV_BASE_URL>`. Always resolve this from the task prompt or `environment_access.md`. All endpoints are GET and return JSON.

### Core endpoints used across tasks

| Endpoint | Typical use |
|---|---|
| `GET /api/accounts` | List all accounts; get account metadata |
| `GET /api/accounts/{id}` | Single account details (display_name, legal_name, billing_arr_current, crm_arr, contract_tenure_months, renewal_date, lifecycle_status, product_plan, region, segment, csm_owner, account_aliases) |
| `GET /api/accounts/{id}/metrics?start=YYYY-MM&end=YYYY-MM` | Monthly metrics: recognized_revenue, support_ticket_count, sla_compliance, nps_score, product_usage, active_seats, survey_status |
| `GET /api/accounts/{id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` | Support tickets: ticket_id, status, severity, product_area, is_duplicate, is_spam, first_response_sla_met, resolution_sla_met, created_date |
| `GET /api/accounts/{id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` | NPS responses: score, response_date, retracted, survey_channel |
| `GET /api/billing/snapshots` | Quarterly billing ARR snapshots by account (as_of date, billing_arr, source) |
| `GET /api/finance/ar-aging` | A/R aging: customer_name, region, quarter, 1_30, 31_60, 61_90, 90_plus, current, as_of |
| `GET /api/opportunities` | CRM pipeline: account_id, amount, stage, state (open/won/lost), close_date, product_line |
| `GET /api/hr/summary` | HR data: headcount, attendance_rate, unpaid_claims_amount, open_advances_amount, leave_liability_hours, by quarter and region |
| `GET /api/events/performance` | Event performance: event_id, event_orders, event_revenue, completed_orders, cancelled_orders, pending_orders, refunded_orders, by quarter |
| `GET /exports/churn/train.csv` | Churn model training data |
| `GET /exports/churn/validation.csv` | Churn model validation data |
| `GET /exports/churn/candidates.csv` | Churn candidate predictions (customer_id, tenure, predicted probability, plus feature columns) |
| `GET /exports/account_metric_extract.csv` | Flat CSV extract of account-level monthly metrics |

Detailed response shapes are in [API Reference](references/api_reference.md).

### Filtering and mapping patterns

- **Account-specific queries**: Always use `/api/accounts/{id}/metrics`, `/api/accounts/{id}/tickets`, `/api/accounts/{id}/nps` for per-account data. These endpoints accept `start` and `end` date parameters.
- **Global queries**: Use `/api/finance/ar-aging`, `/api/billing/snapshots`, `/api/opportunities` to get all data, then filter by account_id, customer_name, or quarter/date range.
- **Linking A/R to accounts**: The ar-aging endpoint uses `customer_name` (legal name). Match against account `legal_name` and `account_aliases` from the accounts endpoint. An A/R record is "linked" when its `customer_name` matches an account's `legal_name` or any alias. It is "unlinked" when no match exists.
- **Date/quarter filtering**: Parse `as_of`, `close_date`, `created_date`, `response_date`, and `month` fields. Most tasks specify exact date ranges — apply them strictly. Use quarter labels like `2026-Q2` to filter billing snapshots and ar-aging records.

## Controlled vocabularies

Every enum field in the output must use exactly one of the values listed. Full definitions are in [Vocabulary](references/vocabulary.md).

### Risk levels (ordered high to low)
`critical`, `high`, `medium`, `low`

### Primary actions
`executive_qbr`, `collections_followup`, `technical_recovery`, `renewal_save`, `nurture_monitor`, `no_action`

### Reason codes
`overdue_receivable`, `low_tenure_high_churn`, `sla_degradation`, `nps_drop`, `usage_decline`, `renewal_window`, `expansion_offset`, `clean_billings`

### Metric sources
`crm_closed_won`, `support_export`, `sla_report`, `nps_survey`, `billing_snapshot`, `ar_aging`, `pipeline_crm`, `event_dashboard`, `hr_report`

### Review owners
`solutions_engineering`, `customer_success`, `finance_ops`

### Agenda topics (ordered)
`partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion`

### Ticket trend
`improving`, `worsening`, `flat`

### Link status
`linked`, `unlinked`

### Accuracy bands
`below_70`, `70_to_79`, `80_to_89`, `90_plus`

### Tenure / coefficient direction
`negative`, `positive`, `zero`, `not_assessed`

### Policy codes

These vary by task and are listed in each output template. Choose exactly one from the pipe-delimited options shown in the template. Common families:

- **Risk model**: `RS-2`, `RS-6`, `RS-9`
- **ARR source**: `REV-1`, `REV-4`, `REV-8`
- **Support hygiene**: `SUP-3`, `SUP-8`, `SUP-9`
- **Action priority**: `ACT-1`, `ACT-5`, `ACT-7`
- **Receivable trigger**: `RCP-4`, `RCP-7`, `RCP-9`
- **CRM match**: `CM-2`, `CM-5`, `CM-8`
- **Pipeline window**: `PW-3`, `PW-6`, `PW-9`
- **Followup scope**: `FS-1`, `FS-4`, `FS-8`
- **Board sort**: `BORD-1`, `BORD-4`, `BORD-8`
- **Exposure formula**: `EXP-2`, `EXP-6`, `EXP-9`
- **Calendar policy**: `CAL-3`, `CAL-5`, `CAL-7`
- **Model protocol**: `MOD-2`, `MOD-7`, `MOD-9`
- **Probability scale**: `PRB-1`, `PRB-4`, `PRB-8`
- **Deployment rule**: `DEP-3`, `DEP-5`, `DEP-9`
- **Outreach mapping**: `OUT-2`, `OUT-6`, `OUT-8`

## Computing derived fields

Key computation patterns are documented in [Computations](references/computations.md). Here are the most common:

### Current ARR
When `uses_billing_arr_source` is true (most retention tasks), use the **billing snapshot** `billing_arr` for the assessment quarter, not the live account `billing_arr_current`. Match by account_id and as_of date. Fall back to account `billing_arr_current` if no snapshot exists for the quarter.

### Clean ticket count
Sum tickets where `is_duplicate == false` AND `is_spam == false` over the analysis period.

### SLA compliance (monthly)
Use `sla_compliance` directly from the metrics endpoint. This is already a percentage. To determine `sla_degradation`, check whether SLA fell below 90% in **any** month of the period. Not every month needs to be degraded — a single month below 90% signals degradation risk.

### Latest NPS
Use the most recent NPS score from the metrics or NPS endpoint within the analysis period. If the metrics endpoint provides `nps_score` per month, the latest month's non-null value is the latest NPS. Ignore months where `survey_status` is `"missing"` (those have null nps_score).

### NPS drop detection
Compare the latest NPS to the earliest NPS in the period. If the latest is **lower** than the earliest, flag `nps_drop`. Also flag if the latest NPS is below 40 (detractor range) regardless of trend.

### Overdue balance
From A/R aging: sum `31_60 + 61_90 + 90_plus` for the assessment quarter's A/R record. The `1_30` bucket is considered current, not overdue. Match to account by customer_name → account legal_name/aliases.

### Usage decline
Compare `product_usage` across months in the period. Flag `usage_decline` if the last month's usage is lower than the first month's, or if any month shows a drop exceeding a material threshold relative to the period average.

### Tenure risk
Low tenure increases churn risk. When `tenure_risk_direction` is `negative`: shorter tenure → higher risk. Flag `low_tenure_high_churn` for accounts with contract_tenure_months ≤ 18.

### Ticket trend
Compare ticket counts month-over-month. If counts are decreasing → `improving`, increasing → `worsening`, unchanged (±1) → `flat`.

### Renewal window
Flag `renewal_window` when the account's `renewal_date` falls within 90 days of the assessment date.

### Expansion offset
Flag `expansion_offset` when the account has open expansion opportunities with `close_date` within the analysis period. These opportunities may offset churn risk.

## Task-specific frameworks

Each task type follows a predictable pipeline. See [Task Patterns](references/task_patterns.md) for step-by-step workflows. Quick overview:

1. **Renewal Risk Queue** (train_001 style): Pull account list → fetch metrics, tickets, NPS, billing snapshots, A/R → compute risk factors → rank by risk_score descending → output top N.
2. **QBR Metrics Packet** (train_002 style): Fetch single-account monthly metrics → compute highlights (averages, peaks, trends) → assign sources → build agenda.
3. **Receivables & Pipeline Review** (train_003 style): Fetch global A/R → link to accounts → fetch opportunities, HR, events → filter by quarter → build follow-ups sorted by customer_name.
4. **Churn Model Validation** (train_004 style): Fetch train/validation/candidate CSVs → count rows, features → compute accuracy → rank candidates by probability descending → assign outreach actions.
5. **Retention Action Board** (train_005 style): Fetch accounts, billing, tickets, NPS, A/R, opportunities → score all accounts → sort by risk_level then ARR → build full board with follow-up calendar.

## Important edge cases

- **Null NPS**: When `survey_status` is `"missing"`, nps_score is null. Skip that month when computing latest NPS. A null doesn't count as a drop or a recovery.
- **Missing A/R**: If no A/R record exists for an account in the target quarter, overdue_balance is 0.0 and the account has `clean_billings`.
- **Empty follow-ups**: If no overdue customers exist after filtering, return an empty array, not null.
- **Duplicate customer names in A/R**: Multiple legal entities may share similar names (e.g., "Valence Payment Services LLC" vs "Valence Payment Services Canada"). Try exact legal_name match first, then fall back to alias matching. Mark unmatched as `unlinked` with `account_id: null`.
- **Account not in billing snapshots**: Use `billing_arr_current` from the account endpoint as fallback.
- **CSV parsing**: The churn CSVs have headers. Parse with Python's csv module. The `Churn` column in train.csv is the label (Yes/No). The candidates.csv has predicted probability columns.
- **Policy codes**: Each output template lists pipe-delimited options. Choose the code that best matches the methodology used — these are deterministic labels assigned after computation, never guessed.

## Output rules

- Always return **only JSON**, no markdown wrapping, no explanatory text.
- Match the exact key structure from the prompt or answer template.
- Never add extra keys not in the template.
- Sort arrays as specified: risk_accounts by rank ascending, overdue_followups by customer_name ascending, qbr_metrics by month ascending.
- When a task says "return the top 5", output exactly 5 objects unless fewer accounts exist.

## Reference files

- [API Reference](references/api_reference.md) — detailed endpoint response shapes and field meanings
- [Vocabulary](references/vocabulary.md) — full enum definitions and usage rules
- [Computations](references/computations.md) — derived field formulas with examples
- [Task Patterns](references/task_patterns.md) — step-by-step workflows per task type
