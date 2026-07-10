# ApexCloud Retention Operations — Self-Serve Analytics

## Overview

This skill covers self-serve analytics against the **ApexCloud Retention Operations API** for customer success, revenue operations, and churn analytics workflows. It applies to risk queue builds, QBR metric packets, receivables reviews, churn model validation, and retention action boards.

---

## API Conventions

### Base URL

Always use the remote base URL supplied via `environment_access.md` in the workspace. Never use `localhost`, `127.0.0.1`, or URLs from task prompts — `environment_access.md` overrides them.

### Endpoint inventory

| Family | Path | Query params |
|---|---|---|
| All accounts | `/api/accounts` | — |
| Single account | `/api/accounts/<account_id>` | — |
| Monthly metrics | `/api/accounts/<account_id>/metrics` | `start=YYYY-MM&end=YYYY-MM` |
| Support tickets | `/api/accounts/<account_id>/tickets` | `start=YYYY-MM-DD&end=YYYY-MM-DD` |
| NPS responses | `/api/accounts/<account_id>/nps` | `start=YYYY-MM-DD&end=YYYY-MM-DD` |
| A/R aging | `/api/finance/ar-aging` | `as_of=YYYY-MM-DD` |
| Opportunities | `/api/opportunities` | `quarter=YYYY-QN` (returns full dataset; filter client-side) |
| HR summary | `/api/hr/summary` | `quarter=YYYY-QN` |
| Event performance | `/api/events/performance` | `event=<name>&quarter=YYYY-QN` |
| Churn train export | `/exports/churn/train.csv` | — |
| Churn validation export | `/exports/churn/validation.csv` | — |
| Churn candidates export | `/exports/churn/candidates.csv` | — |

There is no OpenAPI spec or `/docs` endpoint. Query parameters that appear to do nothing (e.g., `quarter` on `/api/opportunities`) still must be used; the API returns a superset and you filter client-side.

---

## Data Models & Field Reference

### Account (`/api/accounts`, `/api/accounts/<id>`)

```
account_id          — stable identifier (e.g., acct_globex_north)
account_aliases     — list of alternative names used in invoices/contracts
billing_arr_current — authoritative billing-system ARR (USE THIS for risk)
crm_arr             — CRM-reported ARR; may diverge from billing
contract_tenure_months — integer months since contract start
csm_owner           — assigned CSM
display_name        — short display name
legal_name          — official legal entity name
lifecycle_status    — active | implementation | paused | renewal_risk
product_plan        — Launch | Growth | Scale | Enterprise | Strategic
region              — North America | EMEA | APAC | LATAM
renewal_date        — YYYY-MM-DD
segment             — Strategic | Enterprise | Mid-Market | SMB
```

### Monthly Metrics (`/api/accounts/<id>/metrics`)

```
month                — YYYY-MM
quarter              — YYYY-QN
recognized_revenue   — float, 2 decimal places
support_ticket_count — includes duplicates and spam (for clean counts, use tickets endpoint)
sla_compliance       — float, percentage (already 1-decimal precision)
nps_score            — integer, null when no survey completed
product_usage        — float, percentage
active_seats         — integer
survey_status        — completed | skipped
```

### Tickets (`/api/accounts/<id>/tickets`)

```
ticket_id, created_date, status, severity (P1-P4), product_area
is_duplicate     — boolean; EXCLUDE from clean counts
is_spam          — boolean; EXCLUDE from clean counts
first_response_sla_met — boolean
resolution_sla_met     — boolean
```

### NPS (`/api/accounts/<id>/nps`)

```
response_id, response_date, score (integer), survey_channel
retracted — boolean; EXCLUDE retracted responses from all calculations
```

### A/R Aging (`/api/finance/ar-aging`)

```
customer_name   — legal/invoice name (link to account via name matching)
current         — not yet due
1_30, 31_60, 61_90, 90_plus — overdue bucket amounts
quarter, region, as_of
```

**Overdue balance** = `31_60 + 61_90 + 90_plus`.  
**Escalation overdue** = `61_90 + 90_plus` (signals accounts where collections have been failing for 60+ days).

### Opportunities (`/api/opportunities`)

```
opportunity_id, account_id, account_legal_name
amount       — float, 2 decimal places
close_date   — YYYY-MM-DD
created_date — YYYY-MM-DD
product_line — AI Assist | Core Retention | Data Cloud | Workflow Plus
region, stage, state (open | closed)
```

The API ignores filter params and returns all 114 records. **Always filter client-side** by close_date range, state, and stage.

### Churn exports

20 feature columns: `tenure`, `MonthlyCharges`, `TotalCharges`, `Contract`, `PaymentMethod`, `PaperlessBilling`, `Partner`, `Dependents`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`, `SupportTickets90d`, `NPSLast`, `UsageTrendPct`, `InvoicePastDue`, `ActiveSeatRatio`.  
Target: `Churn` (Yes/No) — present in train.csv and validation.csv only.

### HR Summary (`/api/hr/summary`)

Per region: `headcount`, `unpaid_claims_amount`, `unpaid_claims_count`, `open_advances_amount`, `open_advances_count`, `leave_liability_hours`, `high_absence_employees`, `attendance_rate`.

When aggregating "all regions," **sum** headcount, unpaid claims, open advances. Do not average.

### Events (`/api/events/performance`)

Per event: `event_orders`, `event_revenue`, `product_revenue`, `completed_orders`, `cancelled_orders`, `refunded_orders`, `pending_orders`.

---

## Business Rules

### 1. Ticket hygiene — "clean" counts

**Always** exclude `is_duplicate=true` and `is_spam=true` when a task asks for "clean" ticket counts. The metrics endpoint `support_ticket_count` includes all tickets; use the individual tickets endpoint instead, then filter.

Clean ticket count = `count(tickets where is_duplicate=false AND is_spam=false)`.

### 2. NPS — use latest non-retracted

- Exclude `retracted=true` responses.
- "Latest NPS" = the most recent non-retracted score by `response_date`.
- When no valid NPS exists in the period, the value is `null` (not 0).
- NPS scores are integers.

### 3. ARR — billing is authoritative

`billing_arr_current` is the authoritative source for revenue exposure and risk. `crm_arr` is supplemental. When the two differ, `billing_arr_current` takes precedence.

`uses_billing_arr_source = true` when ARR values in the output were sourced from `billing_arr_current`. This is the default and recommended choice.

### 4. A/R aging — name-based account linkage

A/R records use `customer_name` which is a legal/invoice name. Link to CRM accounts by **case-insensitive** matching against:
1. Account `legal_name`
2. Account `display_name`  
3. Each entry in `account_aliases`

Entities with no CRM match are **unlinked** (`link_status: "unlinked"`). Unlinked entities are typically subsidiaries, affiliates, or billing-only records.

When an account has multiple A/R entries (e.g., parent + subsidiary), **sum** the overdue balances across all linked entries for the account's total overdue.

### 5. Opportunities — manual date/state filtering

The opportunities endpoint always returns all 114 records. Filter by:
- **close_date** range for the analysis period
- **state** = `open` for pipeline; `closed` for won/lost
- **stage** = `Closed Won` or `Closed Lost` for outcome counting

**Win rate** = `count(Closed Won) / (count(Closed Won) + count(Closed Lost)) * 100`, expressed to 1 decimal place.

**Open pipeline** = sum of `amount` for open opportunities with close_date in the period.

### 6. Risk ranking dimensions

Rank accounts by descending risk using these signals in priority order:

| Signal | High risk indicator | Reason code |
|---|---|---|
| Past-due renewal | Renewal date already passed | `renewal_window` |
| Overdue receivables | 61-90 or 90+ buckets non-zero | `overdue_receivable` |
| NPS drop | Latest NPS declined ≥20 pts vs prior or ≤30 absolute | `nps_drop` |
| SLA degradation | SLA compliance trending down or < 85% | `sla_degradation` |
| Usage decline | product_usage declining across months | `usage_decline` |
| Low tenure | contract_tenure_months < 18 with other risk factors | `low_tenure_high_churn` |
| Clean bill of health | No negative signals (offsetting reason) | `clean_billings` |
| Expansion offsets risk | Open expansion pipeline can offset some risk | `expansion_offset` |

### 7. Risk levels and primary actions

| Risk level | Criteria | Primary action |
|---|---|---|
| `critical` | Multiple severe signals; past-due renewal + overdue + NPS drop | `executive_qbr` for Strategic/Enterprise; `collections_followup` if primary signal is financial |
| `high` | Two or more negative signals; large overdue balance | `renewal_save` if renewal imminent; `technical_recovery` if SLA/usage signals dominate |
| `medium` | One moderate signal; small overdue only | `nurture_monitor` or `technical_recovery` depending on signal type |
| `low` | No significant negative signals | `nurture_monitor` or `no_action` |

### 8. Action follow-up calendar

Standard due dates relative to assessment date (2026-06-30 convention):

| Action | Due date offset | Default due date |
|---|---|---|
| `collections_followup` | +15 days | 2026-07-15 |
| `technical_recovery` | +18 days | 2026-07-18 |
| `renewal_save` | +22 days | 2026-07-22 |
| `executive_qbr` | +29 days | 2026-07-29 |
| `nurture_monitor` | +36 days | 2026-08-05 |

### 9. Tenure risk direction

Higher tenure generally **reduces** churn risk (coefficient is negative). This is the expected direction.

- `"negative"` = longer tenure → lower risk (standard protective effect)
- `"positive"` = longer tenure → higher risk (counterintuitive; flag for review)
- `"not_assessed"` = insufficient data to determine

### 10. Lifecycle status as risk amplifier

- `renewal_risk` — inherent elevated risk; always at least medium
- `paused` — account is not actively consuming; treat as medium-high risk
- `implementation` — onboarding phase; low renewal risk but monitor usage ramp
- `active` — normal status; risk determined by other signals

---

## Output Conventions

### Precision

| Type | Format |
|---|---|
| Currency (ARR, revenue, overdue, pipeline) | 2 decimal places (e.g., `1188000.00`) |
| Percentages (SLA, win rate, accuracy) | 1 decimal place (e.g., `95.2`) |
| Counts (tickets, accounts, headcount) | Integer |
| Churn probabilities | 3 decimal places (e.g., `0.126`) |
| Risk scores | Integer (0-100 scale) |

### Controlled vocabularies

**Risk levels**: `critical`, `high`, `medium`, `low`

**Primary actions**: `executive_qbr`, `collections_followup`, `technical_recovery`, `renewal_save`, `nurture_monitor`, `no_action`

**Reason codes**: `overdue_receivable`, `low_tenure_high_churn`, `sla_degradation`, `nps_drop`, `usage_decline`, `renewal_window`, `expansion_offset`, `clean_billings`

**Metric sources**: `crm_closed_won`, `support_export`, `sla_report`, `nps_survey`, `billing_snapshot`, `ar_aging`, `pipeline_crm`, `event_dashboard`, `hr_report`

**Review owners**: `solutions_engineering`, `customer_success`, `finance_ops`

**Agenda topics**: `partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion`

**Ticket trend**: `improving` (count decreasing), `worsening` (count increasing), `flat` (unchanged)

**Link status**: `linked`, `unlinked`

**Accuracy bands**: `below_70`, `70_to_79`, `80_to_89`, `90_plus`

**Coefficient direction**: `negative`, `positive`, `zero`

### Sorting rules

- Risk queues: by descending risk (critical → high → medium → low), then by descending overdue balance or ARR within each tier.
- Overdue followups: by `customer_name` ascending (alphabetical).
- Retention board: by risk_level descending, then by overdue_balance descending.

### Policy codes

Policy code fields accept one value from a pipe-delimited set (e.g., `"RS-2|RS-6|RS-9"` means choose RS-2, RS-6, **or** RS-9). Select the code that best matches the actual data context and methodology used. Never output the full pipe-delimited string as a value.

---

## Churn Model SOP

### Data

- `train.csv`: 180 rows, 20 features, target = `Churn` (Yes/No), ~15.6% churn rate
- `validation.csv`: 60 rows, same schema
- `candidates.csv`: 44 rows, same features minus `Churn` column

### Feature count

Count features **after one-hot encoding** categorical variables. There are 7 numeric + 12 categorical features. After one-hot encoding with `drop='first'` (reference category), the total is 28. Without dropping reference, it's 40. Use the one-hot-encoded count (typically 28) as `feature_count`.

### Model training

Train a logistic regression (or equivalent binary classifier) on the training set. Use the validation set for accuracy measurement.

### Accuracy band

- `below_70`: accuracy < 70%
- `70_to_79`: 70% ≤ accuracy < 80%
- `80_to_89`: 80% ≤ accuracy < 90%
- `90_plus`: accuracy ≥ 90%

### Tenure coefficient

Extract the coefficient for the `tenure` feature from the trained model. If logistic regression: a negative coefficient means longer tenure reduces churn probability (expected).

### Candidate ranking

Predict churn probability for each candidate. Rank descending by probability. Top 5 have highest predicted churn risk.

### Outreach action mapping

Map predicted churn probability to outreach actions:
- Combined with A/R overdue → `collections_followup`
- Combined with low tenure → `renewal_save`
- Combined with SLA/usage issues → `technical_recovery`
- Low risk → `nurture_monitor`

---

## Common Workflow Patterns

### Building a risk queue (train_001 pattern)

1. Fetch all accounts, filter to the requested account_ids
2. For each account, fetch: metrics, tickets, NPS, A/R aging (link by name)
3. Compute: clean ticket count, latest NPS (non-retracted), overdue balance, SLA trend, usage trend
4. Check renewal proximity: ≤90 days out or past-due = elevated risk
5. Assign risk_score (0-100), risk_level, primary_action, reason_codes
6. Sort by descending risk, take top 5
7. Compute portfolio_summary and model_checks

### Building QBR metrics (train_002 pattern)

1. Fetch account profile, metrics for all 3 months
2. Populate monthly arrays: revenue, support_tickets, sla_compliance_pct, nps_score
3. Compute highlights: average_revenue, peak month, ticket_trend (compare month-over-month counts)
4. Assign metric_sources enum per field based on the actual API endpoint used
5. Set review_plan with appropriate owner and signoff flag
6. Select exactly 4 agenda_topics in logical order

### Receivables + pipeline review (train_003 pattern)

1. Fetch A/R aging as of the period-end date
2. Identify overdue customers (31_60 + 61_90 + 90_plus > 0)
3. For each, attempt linkage to CRM accounts via name matching
4. Filter opportunities to the quarter's date range
5. Compute: won/lost/open counts, win rate, open pipeline, top product line
6. Sort overdue_followups by customer_name ascending
7. Aggregate HR and event context across all regions

### Churn model validation (train_004 pattern)

1. Download all three CSV exports
2. Train a classifier, evaluate on validation set
3. Report: row counts, feature count (after encoding), accuracy, accuracy_band
4. Extract tenure coefficient direction
5. Predict probabilities for the 8 specified candidates, rank top 5
6. Map outreach actions based on churn probability combined with known risk signals

### Retention action board (train_005 pattern)

1. Fetch account profiles, metrics, tickets, NPS, A/R aging, Q2 open opportunities for all 8 accounts
2. Score each account on all risk dimensions
3. Assign risk_level, primary_action, reason_codes
4. Compute expansion_pipeline from open Q2 opps
5. Set next_touch_due_date from the followup calendar based on primary_action
6. Sort into standard board order (risk descending, overdue descending)
7. Compute segment_summary and followup_calendar

---

## Pitfalls

- **Duplicate A/R entries**: Some legal entities have multiple A/R records (parent + subsidiary). Sum them for total overdue when linked to the same account. Subsidiary names (e.g., "Globex North Subsidiary LLC") do NOT match CRM account aliases and are unlinked.

- **Metrics endpoint includes spam/duplicates**: The `support_ticket_count` from the metrics endpoint is NOT a clean count. Always use the tickets endpoint with filtering when "clean" is specified.

- **NPS null vs 0**: When an account has no NPS survey in a month, the metrics endpoint returns `null`. Do not treat this as score=0. A null NPS means missing data; a score of 0 is a valid (low) NPS.

- **Opportunities API ignores filters**: The `/api/opportunities` endpoint does not actually filter by `quarter` or `state`. Always fetch the full dataset and filter client-side by close_date and state.

- **Tenure risk direction confusion**: Longer tenure is protective (negative coefficient). "negative" means the relationship is inverse (more tenure → less risk). This is the expected, healthy direction.

- **billing_arr vs crm_arr**: Not all accounts have a discrepancy. When they differ, billing_arr_current is authoritative. The discrepancy itself (billing > crm) can signal revenue recognition timing issues.

- **AR aging customer_name matching**: Match case-insensitively against legal_name, display_name, AND all account_aliases. Exact match only — no fuzzy matching.

- **renewal_date in the past**: If the renewal date has already passed relative to the assessment date, the account is in an expired/post-renewal state — this is a critical risk signal regardless of other metrics.
