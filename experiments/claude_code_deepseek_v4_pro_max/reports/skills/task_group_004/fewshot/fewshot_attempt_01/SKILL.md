# ApexCloud Retention Operations — Reusable Skill

## Overview

This skill covers the ApexCloud Retention Operations API for customer success workflows: renewal risk scoring, QBR metrics compilation, receivables/pipeline reviews, churn model validation, and retention action boards. Every task follows a **fetch → compute → fill-template → return-JSON** pattern. Output is always a single JSON object with no markdown wrapping.

---

## API Fundamentals

### Base URL

Use the remote URL from `environment_access.md`. Never use `localhost`, `127.0.0.1`, or URLs from task prompts unless they match the remote URL.

### Endpoint Reference

| Endpoint | Method | Key Query Params | Returns |
|---|---|---|---|
| `/api/accounts/<id>` | GET | — | Account profile: `account_id`, `legal_name`, `display_name`, `account_aliases[]`, `billing_arr_current`, `crm_arr`, `contract_tenure_months`, `csm_owner`, `lifecycle_status`, `product_plan`, `region`, `renewal_date`, `segment` |
| `/api/accounts/<id>/metrics` | GET | `start=YYYY-MM`, `end=YYYY-MM` | Monthly metrics array: `month`, `recognized_revenue`, `sla_compliance` (pct), `support_ticket_count`, `nps_score` (nullable), `product_usage`, `active_seats`, `survey_status` |
| `/api/accounts/<id>/tickets` | GET | `start=YYYY-MM-DD`, `end=YYYY-MM-DD` | Support tickets array: `ticket_id`, `created_date`, `status`, `severity`, `is_spam`, `is_duplicate`, `first_response_sla_met`, `resolution_sla_met`, `product_area` |
| `/api/accounts/<id>/nps` | GET | `start=YYYY-MM-DD`, `end=YYYY-MM-DD` | NPS responses array: `response_date`, `score`, `survey_channel`, `retracted` |
| `/api/finance/ar-aging` | GET | `as_of=YYYY-MM-DD` | A/R aging array: `customer_name`, `aging_id`, `current`, `1_30`, `31_60`, `61_90`, `90_plus`, `region`, `quarter` |
| `/api/accounts` | GET | — | List of all accounts (44 total) with same shape as single-account endpoint |
| `/api/opportunities` | GET | `quarter=YYYY-QN` | Pipeline opportunities: `account_id`, `amount`, `close_date`, `state` (open/closed), `stage`, `product_line`, `region` |
| `/api/hr/summary` | GET | `quarter=YYYY-QN` | HR summaries by region: `headcount`, `unpaid_claims_amount`, `unpaid_claims_count`, `attendance_rate`, `region` |
| `/api/events/performance` | GET | `event=<name>`, `quarter=YYYY-QN` | Event performance: `event_orders`, `event_revenue`, `product_revenue`, `completed_orders`, `cancelled_orders` |
| `/exports/churn/train.csv` | GET | — | CSV: 180 rows, 19 features + target (`Churn`) |
| `/exports/churn/validation.csv` | GET | — | CSV: 60 rows, same schema |
| `/exports/churn/candidates.csv` | GET | — | CSV: 19 features per candidate (no target), keyed by `customer_id` |

### Date Format Conventions

- **Months**: `YYYY-MM` (e.g. `2026-04`)
- **Dates**: `YYYY-MM-DD` (e.g. `2026-06-30`)
- **Quarters**: `YYYY-QN` (e.g. `2026-Q2`)
- Always use the exact date range from the task prompt; do not extend or shorten windows.

---

## Data Cleaning Rules

### Ticket Cleaning

**Clean ticket** = a ticket where ALL of the following are true:
- `is_spam` is `false`
- `is_duplicate` is `false`
- `status` is NOT `"cancelled"`

Tickets with `status: "open"` ARE included in clean counts. Tickets with `status: "closed"` ARE included. Only `"cancelled"` is excluded.

**Clean ticket count** = count of tickets passing all three filters.

### SLA Calculation

When computing SLA compliance from ticket-level data, use `first_response_sla_met` (not `resolution_sla_met`). The metrics endpoint's `sla_compliance` field is a separate, broader metric — check which one the task requires.

SLA % = (clean tickets with `first_response_sla_met: true` / total clean tickets) × 100, rounded to 1 decimal.

### NPS Scoring

- `latest_nps` = the most recent non-null `nps_score` in the analysis period. Check both the NPS endpoint (`/nps`, sorted by `response_date`) and the metrics endpoint (`nps_score` by month). If the NPS endpoint returns a score for the latest month, use it; if not, use the metrics endpoint's value. Ignore `retracted: true` responses.
- Monthly NPS for QBR = the `nps_score` from the metrics endpoint for that month (may be `null` if `survey_status: "missing"`).

### A/R Overdue Balance

`overdue_balance` = `61_90` + `90_plus` from the A/R aging record. These are the "older" aging buckets. Do NOT include `1_30` or `31_60` in the overdue balance.

### A/R-to-CRM Account Linking

Match A/R `customer_name` to CRM accounts by checking against each account's `legal_name` AND all entries in `account_aliases`. The match must be **exact** (case-sensitive, whole-string).

- **linked**: found an exact match → set `link_status: "linked"`, `account_id` = the matched `account_id`
- **unlinked**: no exact match → set `link_status: "unlinked"`, `account_id: null`

### Revenue Sources

Two ARR figures exist on the account profile:
- `billing_arr_current` — authoritative for risk/retention tasks
- `crm_arr` — CRM-reported ARR

For QBR monthly revenue, the source is `recognized_revenue` from the metrics endpoint, labeled as source `crm_closed_won`.

### Expansion Pipeline

`expansion_pipeline` for an account = sum of opportunity `amount` values where:
- `state` is `"open"` (NOT `"closed"`)
- `close_date` falls within the analysis period's date range

Closed Won and Closed Lost opportunities do NOT count toward expansion pipeline.

---

## Output Precision Rules

| Data Type | Precision | Example |
|---|---|---|
| Currency (ARR, revenue, balances, pipeline) | 2 decimal places | `1416439.47` |
| Percentages (accuracy, win rate, SLA) | 1 decimal place | `93.3` |
| NPS scores | Integer | `39` |
| Risk scores | Integer (0–100) | `100` |
| Counts (tickets, accounts, headcount) | Integer | `13` |
| Churn probabilities | 3 decimal places | `0.102` |

---

## Controlled Vocabularies (Enums)

Never invent new enum values. Use only these strings exactly as written:

### risk_level
`critical` | `high` | `medium` | `low`

### primary_action / outreach_action
`executive_qbr` | `collections_followup` | `technical_recovery` | `renewal_save` | `nurture_monitor` | `no_action`

### reason_codes
`overdue_receivable` | `low_tenure_high_churn` | `sla_degradation` | `nps_drop` | `usage_decline` | `renewal_window` | `expansion_offset` | `clean_billings`

### ticket_trend
`improving` (decreasing count) | `worsening` (increasing) | `flat` (unchanged)

### metric_sources
`crm_closed_won` | `support_export` | `sla_report` | `nps_survey` | `billing_snapshot` | `ar_aging` | `pipeline_crm` | `event_dashboard` | `hr_report`

### review_owner
`solutions_engineering` | `customer_success` | `finance_ops`

### agenda_topics
`partnership_overview` | `q2_metrics` | `performance_highlights` | `q3_initiatives` | `technical_recovery` | `commercial_expansion`

### accuracy_band
`below_70` | `70_to_79` | `80_to_89` | `90_plus`

### tenure direction enums
- `tenure_risk_direction`: `negative` (lower tenure → higher risk) | `positive` | `not_assessed`
- `tenure_coefficient_direction`: `negative` (lower tenure → higher churn) | `positive` | `zero`

### link_status
`linked` | `unlinked`

---

## Business Rules

### Risk Score Calculation

Risk score is an integer 0–100 built from additive signals. Higher = more at-risk. Key signals and their approximate weight:

- **Renewal window** (renewal_date within ~90 days of assessment date) — major contributor
- **Overdue receivables** (overdue_balance > 0) — major contributor
- **NPS drop** (latest NPS substantially below account's historical or below ~40) — moderate
- **SLA degradation** (first_response_sla_met failures on clean tickets) — moderate
- **Usage decline** (product_usage trending down across months) — moderate
- **Low tenure** (contract_tenure_months ≤ ~24, especially with other signals) — moderate
- **Expansion offset** (expansion pipeline > 0 can offset risk if the account is otherwise healthy; but can also be a risk signal if paired with other concerns) — context-dependent

Rank accounts by descending risk_score. Return exactly the requested count (typically top 5 or all accounts reviewed).

### Primary Action Mapping

| Dominant Signal | Primary Action |
|---|---|
| Overdue balance > 0 is the foremost concern | `collections_followup` |
| SLA failures + NPS drops + usage decline dominate | `technical_recovery` |
| In renewal window with moderate concerns | `renewal_save` |
| Strategic account with complex issues | `executive_qbr` |
| Low risk, clean bills, no urgent issues | `nurture_monitor` |
| Minimal risk, no active concerns | `no_action` |

When multiple signals compete, prioritize: overdue → SLA/NPS degradation → renewal timing → expansion context.

### Follow-up Due Dates

- `no_action` accounts get `next_touch_due_date: null`
- All other actions get a due date as specified in the task prompt. If not specified, derive reasonable defaults.

### Reason Codes Assembly

Assign reason codes cumulatively — an account can have many. Rules:
- `overdue_receivable` ↔ overdue_balance > 0
- `low_tenure_high_churn` ↔ contract_tenure_months ≤ 24 (or task-specific threshold) AND other risk signals present
- `sla_degradation` ↔ one or more SLA misses on clean tickets
- `nps_drop` ↔ latest NPS is low (<50) or declined from previous period
- `usage_decline` ↔ product_usage trending downward across months
- `renewal_window` ↔ renewal_date is within the upcoming ~90 days
- `expansion_offset` ↔ expansion_pipeline > 0
- `clean_billings` ↔ overdue_balance == 0 AND no billing concerns

### Portfolio / Segment Summaries

- **accounts_reviewed**: total count of accounts evaluated (not just top N)
- **critical_or_high_count**: count of accounts with risk_level `critical` or `high` among ALL reviewed accounts
- **arr_at_risk**: sum of `current_arr` for all reviewed accounts whose risk_level is NOT `low` (i.e., critical + high + medium)
- **collections_count**: count of accounts (in the returned top N) with `primary_action: "collections_followup"`
- **technical_recovery_count**: count of accounts (in the returned top N) with `primary_action: "technical_recovery"`
- **net_revenue_exposure** (when present): `arr_at_risk - open_expansion_pipeline`
- **linked_followup_count**: count of overdue_followups with `link_status: "linked"`
- **unlinked_followup_count**: count of overdue_followups with `link_status: "unlinked"`
- **strategic_accounts**: count of reviewed accounts with `segment: "Strategic"`
- **enterprise_accounts**: count of reviewed accounts with `segment: "Enterprise"`
- **open_expansion_pipeline**: sum of all `expansion_pipeline` values across reviewed accounts

### Pipeline Summary

- **won_count / won_revenue**: opportunities with `state: "closed"` AND `stage` ending in "Won"
- **lost_count**: opportunities with `state: "closed"` AND `stage` ending in "Lost"
- **open_count / open_pipeline**: opportunities with `state: "open"`
- **win_rate_pct**: `won_count / (won_count + lost_count) × 100`, to 1 decimal
- **top_open_product_line**: the `product_line` with the highest total `amount` among open opportunities

### QBR Highlights

- **average_revenue**: mean of the 3 monthly revenue values, 2 decimals
- **peak_revenue_month**: month with highest revenue
- **max_sla_month / max_sla_pct**: month with highest SLA %; on ties, pick the earliest month chronologically
- **peak_nps_month / peak_nps_score**: month with highest NPS score
- **ticket_trend**: compare total clean tickets across months — decreasing → `improving`, increasing → `worsening`, stable → `flat`

### Churn Model Validation

- **feature_count**: count the feature columns in the training CSV (exclude `customer_id` and the target column `Churn`)
- **training_rows / validation_rows**: row counts from the respective CSV files (excluding header)
- **accuracy_pct**: from the model evaluation, 1 decimal
- **accuracy_band**: map accuracy_pct to the correct band
- **tenure_coefficient_direction**: `negative` if lower tenure → higher churn probability, `positive` if higher tenure → higher churn, `zero` if no relationship
- **average_probability_top5**: mean of the top 5 predicted churn probabilities, 3 decimals
- **past_due_shortlist_count**: among top 5, count where `InvoicePastDue` = `"Yes"` in candidates.csv
- **low_tenure_shortlist_count**: among top 5, count where `tenure` ≤ 24 in candidates.csv

### Policy Codes

All tasks with `policy_codes` use the template's pipe-separated options. Select the **middle value** from each `CODE-LOW|CODE-MID|CODE-HIGH` triplet by default. The specific selection may vary based on data characteristics (e.g., which risk model version applies, which revenue source is used). Always select exactly one value per code key — never leave the pipe-separated template string.

---

## Sorting Conventions

- **Risk accounts**: descending by `risk_score`
- **Overdue followups**: ascending by `customer_name` (lexicographic, case-sensitive)
- **QBR metrics**: ascending by `month` (chronological)
- **Action board**: all reviewed accounts, descending by risk (highest risk first)

---

## JSON Output Rules

1. **Valid JSON only** — no markdown fences, no trailing commas, no comments
2. **null vs 0**: Use `null` for inapplicable/missing values (e.g., `next_touch_due_date` for `no_action`, `account_id` for unlinked A/R customers). Use `0`/`0.0` for true zero values
3. **Empty strings**: Not used in answers; use `null` or omit instead (template placeholders like `""` get filled with real values or `null`)
4. **All keys from the answer template must be present** in the output, even if some are `null` or `0`
5. **Controlled enum values only** — never invent new labels

---

## Workflow Pattern

For any task using this API:

1. **Read the answer template** (`input/payloads/answer_template.json`) to understand the exact output shape and enum options
2. **Identify the required endpoints** from the task prompt's endpoint families or data-source descriptions
3. **Fetch all data in parallel where possible** — account profiles, metrics, tickets, NPS, A/R, opportunities can all be fetched concurrently since they're independent
4. **Apply cleaning rules** to tickets (exclude spam/duplicate/cancelled)
5. **Compute derived values** (risk scores, SLA %, summaries, trends)
6. **Assemble the JSON** following the template shape, precision rules, and enum vocabularies
7. **Validate**: ensure all template keys are present, all enums are valid, precision matches rules, counts are consistent
8. **Return JSON only** — no explanatory text

---

## Common Pitfalls

- **Using wrong ARR source**: For risk/retention tasks, `current_arr` comes from billing data, not CRM. Check `uses_billing_arr_source` and `arr_source_code` in the template.
- **Including spam/duplicate/cancelled tickets in clean counts**: Always filter to clean tickets before counting or computing SLA.
- **Using resolution_sla_met instead of first_response_sla_met**: SLA compliance for QBR and risk assessment is based on first-response SLA, not resolution SLA.
- **Including 1_30 and 31_60 buckets in overdue_balance**: Only `61_90` + `90_plus` count as overdue.
- **Fuzzy A/R matching**: Account linking must be exact string match against `legal_name` and each `account_aliases` entry. "Globex North Subsidiary LLC" ≠ "Globex North Subsidiary".
- **Counting closed opportunities as pipeline**: Only `state: "open"` opportunities count toward `expansion_pipeline`.
- **Wrong precision**: Churn probabilities need 3 decimals, not 2. Currency needs exactly 2 decimals. Risk scores are integers.
- **Inventing enum values**: Use only the exact enum strings from the answer template.
- **Not returning all accounts in action boards**: When the task says "return all accounts," include every reviewed account, not just top N.
- **Using localhost URLs**: Always use the remote URL from `environment_access.md`.
