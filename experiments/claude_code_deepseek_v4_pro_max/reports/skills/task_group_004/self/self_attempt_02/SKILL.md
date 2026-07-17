# ApexCloud Retention Operations — Self-Service Analytics Skill

## Overview

This skill covers the ApexCloud Retention Operations API and the standard workflows for building retention risk queues, QBR metric packets, receivables reviews, churn model validations, and high-touch retention action boards. All tasks share the same API surface, controlled vocabularies, and output conventions described below.

**Base URL:** Use the remote API URL provided in `environment_access.md`. Never use localhost unless the remote URL itself redirects there.

---

## API Endpoint Reference

### Accounts

| Endpoint | Method | Key Parameters | Returns |
|---|---|---|---|
| `/api/accounts` | GET | — | Array of all account objects |
| `/api/accounts/<account_id>` | GET | — | Single account detail |
| `/api/accounts/<account_id>/metrics` | GET | `start=YYYY-MM`, `end=YYYY-MM` | Monthly aggregated metrics |
| `/api/accounts/<account_id>/tickets` | GET | `start=YYYY-MM-DD`, `end=YYYY-MM-DD` | Support ticket list |
| `/api/accounts/<account_id>/nps` | GET | `start=YYYY-MM-DD`, `end=YYYY-MM-DD` | NPS survey responses |

### Finance & Pipeline

| Endpoint | Method | Key Parameters | Returns |
|---|---|---|---|
| `/api/finance/ar-aging` | GET | `as_of=YYYY-MM-DD` | AR aging buckets by customer |
| `/api/opportunities` | GET | `quarter=YYYY-QN` | Sales opportunities (filter by close_date yourself) |

### HR & Events

| Endpoint | Method | Key Parameters | Returns |
|---|---|---|---|
| `/api/hr/summary` | GET | `quarter=YYYY-QN` | HR headcount/claims by region |
| `/api/events/performance` | GET | `event=<id>`, `quarter=YYYY-QN` | Event orders/revenue |

### Churn Exports

| Endpoint | Method | Returns |
|---|---|---|
| `/exports/churn/train.csv` | GET | Training dataset (CSV) |
| `/exports/churn/validation.csv` | GET | Validation dataset (CSV) |
| `/exports/churn/candidates.csv` | GET | Candidate accounts for scoring (CSV) |

---

## Data Retrieval Patterns

### Parallel fetching

When a task lists explicit account_ids, fetch all account-level data in parallel:

```
For each account_id, simultaneously:
  GET /api/accounts/<id>
  GET /api/accounts/<id>/metrics?start=...&end=...
  GET /api/accounts/<id>/tickets?start=...&end=...
  GET /api/accounts/<id>/nps?start=...&end=...
Then:
  GET /api/finance/ar-aging?as_of=...
  GET /api/opportunities?quarter=...   (filter locally by close_date)
```

### The AS_OF pattern

AR aging uses the `as_of` query parameter (not `start`/`end`). Always pass it in `YYYY-MM-DD` format, typically the last day of the assessment period.

### The quarter parameter on opportunities

The `/api/opportunities?quarter=YYYY-QN` parameter does NOT reliably filter to only that quarter's opportunities. **Always filter by `close_date` locally** for pipeline window calculations. The pipeline window for a given quarter is `close_date` between the quarter's first and last day.

---

## Controlled Vocabularies

Use these enums exactly as written. Do not invent new values.

### Risk Levels
`critical`, `high`, `medium`, `low`

### Primary Actions
| Value | When to Use |
|---|---|
| `executive_qbr` | Strategic/enterprise accounts needing executive intervention; high ARR + renewal risk + relationship issues |
| `collections_followup` | Overdue receivables present (any aging bucket beyond current) |
| `technical_recovery` | SLA breaches, repeated SLA misses, or service degradation |
| `renewal_save` | Approaching renewal with elevated risk but no single dominant issue |
| `nurture_monitor` | Low/medium risk, stable accounts — routine watch |
| `no_action` | Healthy accounts with no risk indicators |

### Reason Codes
| Value | Trigger |
|---|---|
| `overdue_receivable` | Any overdue balance in AR aging (1-30, 31-60, 61-90, 90+) |
| `low_tenure_high_churn` | Contract tenure ≤ 24 months combined with other risk signals |
| `sla_degradation` | Declining SLA compliance over the period, or SLA misses on current tickets |
| `nps_drop` | Latest NPS below 30 OR downward trend over the period |
| `usage_decline` | Product usage trending down across the period |
| `renewal_window` | Renewal date within the current or next quarter |
| `expansion_offset` | Open expansion opportunity exists that could offset risk |
| `clean_billings` | No overdue balance; billing in good standing |

### Metric Source Enums
| Field | Source Enum | Derived From |
|---|---|---|
| Revenue | `billing_snapshot` | `recognized_revenue` in `/accounts/<id>/metrics` |
| Revenue | `crm_closed_won` | CRM opportunity amounts (closed-won) |
| Support tickets | `support_export` | `/accounts/<id>/tickets` endpoint |
| SLA compliance | `sla_report` | `sla_compliance` field in metrics |
| NPS | `nps_survey` | `/accounts/<id>/nps` endpoint or `nps_score` in metrics |

Full source enum vocabulary: `crm_closed_won`, `support_export`, `sla_report`, `nps_survey`, `billing_snapshot`, `ar_aging`, `pipeline_crm`, `event_dashboard`, `hr_report`

### Ticket Trend
`improving` (ticket count decreasing), `worsening` (increasing), `flat` (stable or mixed pattern with ≤1 change)

### Review Owner
`customer_success`, `solutions_engineering`, `finance_ops`

### Agenda Topics (ordered set of exactly 4)
`partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion`

### Accuracy Band
`below_70`, `70_to_79`, `80_to_89`, `90_plus`

### Link Status
`linked` (customer_name matches an account legal_name or alias), `unlinked` (no match found)

### Lifecycle Statuses
`active`, `renewal_risk`, `implementation`, `paused`

### Account Segments (ARR-based tiers)
`Strategic`, `Enterprise`, `Mid-Market`, `SMB`

### Product Plans
`Strategic`, `Enterprise`, `Scale`, `Growth`, `Launch`

### Regions
`North America`, `EMEA`, `APAC`, `LATAM`

### Contract Types (in churn CSVs)
`Month-to-month`, `One year`, `Two year`

---

## Business Rules

### Ticket Hygiene (Clean Ticket Count)

1. Start with all tickets from `/api/accounts/<id>/tickets`
2. **Exclude** tickets where `is_spam == true`
3. **Exclude** tickets where `is_duplicate == true`
4. The remaining count is the **clean ticket count**
5. For SLA health assessment, check within clean tickets: count where `first_response_sla_met == false` OR `resolution_sla_met == false`

### NPS Conventions

1. Fetch NPS responses from `/api/accounts/<id>/nps`
2. **Exclude** responses where `retracted == true`
3. The **latest NPS** is the score from the response with the most recent `response_date`
4. If no non-retracted responses exist, `latest_nps` is `null` (or 0 depending on task)
5. The `nps_score` in the metrics endpoint may differ from the raw NPS endpoint — prefer the raw endpoint for precise latest-score lookups; use the metrics endpoint for monthly trend data

### ARR Source Convention

Accounts have two ARR fields:
- `billing_arr_current` — from the billing system (the `/api/accounts/<id>` endpoint)
- `crm_arr` — from the CRM system

When a task asks `uses_billing_arr_source`:
- `true` means prefer `billing_arr_current` as the primary ARR figure
- `false` means prefer `crm_arr`

The billing ARR is generally authoritative for revenue recognition; CRM ARR may differ due to pipeline adjustments or discount structures. When both are available, note which one drives your calculations.

### AR Aging to Account Linking

The `/api/finance/ar-aging` endpoint returns records keyed by `customer_name`. To link an AR record to an account:

1. Match `customer_name` against `legal_name` (exact match)
2. If no exact match, check against all entries in `account_aliases` (case-insensitive substring or fuzzy match)
3. The AR name may differ subtly from the account name (e.g., "North Star Finance Services" vs "Northstar Finance Group Inc.", "Globex North Subsidiary LLC" vs alias "Globex North Subsidiary")
4. Only accounts where `customer_name` can be linked are "linked" (`link_status: "linked"`); otherwise `"unlinked"`
5. When multiple AR records could match one account (e.g., subsidiary names), aggregate the overdue totals

### Overdue Balance Calculation

Total overdue = `1_30 + 31_60 + 61_90 + 90_plus` from the AR aging record. Do NOT include `current` in overdue totals.

"Older aging buckets" refers to `61_90` and `90_plus` specifically.

### Tenure Risk Direction

- `negative`: Lower tenure → higher churn risk (newer customers more volatile). This is the typical direction.
- `positive`: Higher tenure → higher risk (long-tenured customers with stale relationships)
- `not_assessed`: Tenure not used as a risk factor in this analysis

In churn model CSVs, the `tenure` coefficient direction determines this: if the model shows negative correlation between tenure and churn probability, direction is `negative`.

### Risk Scoring Framework

Score each account on these dimensions; higher score = higher risk:

| Dimension | Signal | Weight Driver |
|---|---|---|
| Renewal proximity | Closer renewal date → higher risk | Renewal within 90 days from assessment date |
| Revenue exposure | Higher ARR → higher risk (more to lose) | Absolute billing ARR |
| NPS sentiment | Lower NPS → higher risk | Latest non-retracted NPS score |
| SLA health | More SLA misses → higher risk | Count of clean tickets with SLA failures |
| Usage trend | Declining → higher risk | Month-over-month usage percentage change |
| Overdue receivables | Any overdue → higher risk | Total overdue from AR aging |
| Tenure (if negative direction) | Lower tenure → higher risk | Months under contract |
| Lifecycle status | `renewal_risk` or `paused` → additional risk | Status field |

Rank accounts from highest to lowest risk score. For top-N outputs, take the first N.

### Pipeline Calculations

For pipeline summaries:
- **Won**: opportunities with `state == "closed"` and `stage` containing "Won" (e.g., "Closed Won"), with `close_date` in the period
- **Lost**: opportunities with `state == "closed"` and `stage` containing "Lost" (e.g., "Closed Lost"), with `close_date` in the period
- **Open**: opportunities with `state == "open"` and `close_date` in the period
- **Win rate**: `won_count / (won_count + lost_count) * 100` (to 1 decimal)
- **Top open product line**: most frequent `product_line` among open opps (ties broken by first alphabetically)

### Churn Model Validation

From the train/validation CSV exports:
- `training_rows`: row count of train.csv minus header
- `validation_rows`: row count of validation.csv minus header
- `feature_count`: number of predictor columns (exclude `customer_id` and `Churn`)
- `accuracy_pct`: correct predictions / total validation rows × 100 (to 1 decimal)
- `accuracy_band`: bucket as `below_70`, `70_to_79`, `80_to_89`, `90_plus`
- `tenure_coefficient_direction`: `negative` if higher tenure → lower churn probability in the training data; `positive` if the reverse; `zero` if no correlation

### Expansion Pipeline for Retention Board

For each account on a retention board, sum the `amount` of open opportunities (`state == "open"`) whose `close_date` falls within the analysis period. This is the `expansion_pipeline` per account.

### Net Revenue Exposure

`net_revenue_exposure = arr_at_risk - open_expansion_pipeline` (expansion offsets risk). This can be positive (net risk) or negative (expansion covers risk).

---

## Output Format Conventions

### Precision Rules (deterministic, every task)

| Type | Precision | Example |
|---|---|---|
| Currency (ARR, revenue, overdue) | 2 decimal places | `1425000.00` |
| Percentages (SLA, win rate, accuracy) | 1 decimal place | `87.3` |
| Counts (tickets, accounts, headcount) | Integer | `15` |
| Risk scores | Integer | `78` |
| Churn probabilities | 3 decimal places | `0.342` |
| NPS scores | Integer | `45` |

### JSON Output Rules
- Output **only valid JSON** — no markdown fences, no explanatory text
- All enum values must match the controlled vocabulary exactly (case-sensitive)
- `null` for missing numeric values (e.g., missing NPS), never omit the key
- Empty strings for missing string values in templates
- Sort arrays as specified (e.g., overdue_followups by `customer_name` ascending)

### Policy Codes

Task templates include a `policy_codes` object with code families. Each family has a deterministic code based on the task's parameters (assessment date, period, model version, region filter). Code families observed:

| Family | Applies To |
|---|---|
| `risk_model_code` (RS-N) | Risk scoring model version |
| `arr_source_code` (REV-N) | Which ARR source was used |
| `support_hygiene_code` (SUP-N) | Ticket filtering rules applied |
| `action_priority_code` (ACT-N) | Action-to-risk-level mapping |
| `receivable_trigger_code` (RCP-N) | Overdue threshold for inclusion |
| `crm_match_code` (CM-N) | Linking strategy for AR→CRM |
| `pipeline_window_code` (PW-N) | Date range used for pipeline |
| `followup_scope_code` (FS-N) | Which follow-ups are included |
| `model_protocol_code` (MOD-N) | Churn model protocol |
| `probability_scale_code` (PRB-N) | Probability calibration |
| `deployment_rule_code` (DEP-N) | Model deployment rules |
| `outreach_mapping_code` (OUT-N) | Outreach action mapping |
| `board_sort_code` (BORD-N) | Retention board sort order |
| `exposure_formula_code` (EXP-N) | Net exposure calculation |
| `calendar_policy_code` (CAL-N) | Follow-up calendar rules |

### Follow-up Due Dates

When tasks specify follow-up due dates by action type, use them exactly:

| Action | Typical Due Date Offset |
|---|---|
| `collections_followup` | 15 days after assessment |
| `technical_recovery` | 18 days after assessment |
| `renewal_save` | 22 days after assessment |
| `executive_qbr` | 29 days after assessment |
| `nurture_monitor` | ~36 days after assessment |

---

## Common Pitfalls

1. **Don't trust the quarter filter on `/api/opportunities`.** Always filter by `close_date` locally for pipeline window calculations.

2. **AR aging customer_name ≠ account legal_name.** Always attempt alias matching. Some AR names are subsidiary/alternate forms that appear in `account_aliases` or are close variants.

3. **NPS from metrics ≠ NPS from the NPS endpoint.** The metrics endpoint may average or aggregate NPS differently. Use the raw NPS endpoint (`/api/accounts/<id>/nps`) for the latest individual score; use the metrics endpoint for month-level trend data.

4. **The metrics endpoint's `nps_score` can be `null`** when `survey_status == "missing"`. Handle nulls — don't treat them as 0.

5. **Billing ARR and CRM ARR can differ.** Check the task's `uses_billing_arr_source` directive and use the appropriate field. Never average or blend them unless explicitly instructed.

6. **Ticket SLA checks must use clean tickets only.** Filter out spam and duplicates before counting SLA misses.

7. **Not all accounts in AR aging appear in the accounts list.** Some AR customer_names may be pure billing entities without CRM accounts. Mark these as `"unlinked"`.

8. **Q2 vs Q3 pipeline windows differ.** Q2 = 2026-04-01 to 2026-06-30, Q3 = 2026-07-01 to 2026-09-30. Use the exact date range from the task prompt, not the quarter label alone.

9. **The churn candidates CSV uses `customer_id` values that match `account_id` values.** Link candidates back to the accounts API for additional context when needed.

10. **Always sort retention boards by risk score descending.** The highest-risk account gets rank 1.

---

## Workflow Checklist

When approaching any retention operations task:

1. **Read the task prompt completely.** Note assessment date, analysis period, months, and account_ids or filters.
2. **Fetch all accounts** via `GET /api/accounts` to get the full population. Filter by region, segment, or explicit account_ids as the task requires.
3. **Fetch per-account data in parallel:** metrics, tickets, NPS for each account in scope.
4. **Fetch cross-cutting data:** AR aging (as_of date), opportunities (all quarters, filter locally), HR, events.
5. **Link AR records to accounts** using legal_name + alias matching.
6. **Compute clean ticket counts** (exclude spam + duplicates).
7. **Extract latest NPS** from raw NPS endpoint (latest non-retracted response_date).
8. **Score and rank** according to the risk framework, using only the dimensions the task requires.
9. **Populate the answer template** with precise values, using controlled enums exactly as written.
10. **Validate precision:** currencies to 2 decimals, percentages to 1 decimal, counts as integers.
