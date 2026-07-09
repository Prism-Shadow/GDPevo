# ApexCloud Retention Operations — Skill Guide

## Overview

This skill covers the ApexCloud Retention Operations API: account profiling, metrics, support-ticket hygiene, NPS, A/R aging, billing, CRM pipeline, HR context, event operations, and churn-model exports. Use it to build renewal risk queues, QBR packets, receivables reviews, churn-model readouts, and retention action boards.

---

## API Conventions

### Base URL

Use the remote environment base URL. Do **not** use `localhost`, `127.0.0.1`, or any `env/setup.sh` reference.

### Endpoint Families

| Family | Pattern | Notes |
|---|---|---|
| Accounts list | `GET /api/accounts` | Returns all accounts |
| Account detail | `GET /api/accounts/{account_id}` | Profile, billing, CRM ARR, tenure, lifecycle, segment, renewal |
| Monthly metrics | `GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM` | Revenue, NPS, SLA, usage, ticket count per month |
| Support tickets | `GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` | Individual ticket records with SLA flags |
| NPS responses | `GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` | Individual survey responses with retraction flag |
| A/R aging | `GET /api/finance/ar-aging?as_of=YYYY-MM-DD` | Aging buckets by customer legal name |
| Opportunities | `GET /api/opportunities` | CRM pipeline with stage, state, amount, close date |
| HR summary | `GET /api/hr/summary` | Headcount, unpaid claims by region and quarter |
| Event performance | `GET /api/events/performance` | Event orders and revenue by event ID and quarter |
| Churn exports | `GET /exports/churn/{train,validation,candidates}.csv` | CSV files for churn model work |

### Query Parameter Formats

- **Month ranges**: `start=2026-04&end=2026-06` (YYYY-MM format)
- **Date ranges**: `start=2026-04-01&end=2026-06-30` (YYYY-MM-DD format)
- **Point-in-time**: `as_of=2026-06-30` (YYYY-MM-DD format)

---

## Data Extraction Rules

### Account Profile

- `billing_arr_current` is the authoritative ARR for risk calculations and board outputs. CRM ARR (`crm_arr`) is a secondary source.
- `lifecycle_status` values: `active`, `renewal_risk`, `paused`, `implementation`.
- `segment` values: `Strategic`, `Enterprise`, `Mid-Market`, `SMB`.
- `renewal_date` is a date string (YYYY-MM-DD). Compare against the assessment date to flag past-due or approaching renewals.

### Monthly Metrics

- Use raw API values **without rounding**. The API already returns values at appropriate precision.
- `recognized_revenue` is the monthly revenue figure.
- `sla_compliance` is a percentage (e.g., `95.2` means 95.2%).
- `nps_score` in the metrics endpoint is a point-in-time monthly value that may be `null` when no survey was completed.
- `support_ticket_count` in the metrics endpoint is a raw total; for "clean" counts prefer the tickets endpoint with filtering applied.
- `survey_status`: `completed`, `missing`, or `retracted`. A `retracted` NPS score must be excluded from analysis.

### Support Tickets

- **Clean ticket**: A ticket where `is_spam` is `false` AND `is_duplicate` is `false`. This is the definition of "clean" for counting purposes.
- SLA health is assessed from the tickets endpoint using `first_response_sla_met` and `resolution_sla_met` fields.
- Ticket status values: `closed`, `open`, `cancelled`.

### NPS Responses

- Use the NPS endpoint (`/api/accounts/{id}/nps`) for individual scores.
- **Exclude retracted responses** (`retracted: true`).
- The **latest NPS** is the most recent non-retracted score by `response_date`.

### A/R Aging

- **Overdue balance** = `31_60` + `61_90` + `90_plus`. Do **not** include `current` or `1_30`.
- "Older aging buckets" refers to `61_90` and `90_plus` specifically.
- Match AR `customer_name` to account `legal_name` for CRM linking. Entries whose customer name does not match any CRM account legal name are **unlinked**.

### CRM Pipeline (Opportunities)

- Use the **`stage` field** (not `state`) to classify opportunities:
  - `Closed Won` → won
  - `Closed Lost` → lost
  - Everything else (`Prospecting`, `Discovery`, `Proposal`, `Negotiation`) → open pipeline
- **All open stages count as pipeline**, including Prospecting and Discovery. Do not exclude early-stage opportunities from pipeline counts.
- Filter by `close_date` within the analysis period for period-specific pipeline summaries.
- **Win rate** = `won_count / (won_count + lost_count) * 100` (count-based, not revenue-based). When denominator is zero, win rate is `0.0`.

### Churn Model Exports

- CSV exports at `/exports/churn/` contain telco-style churn features: tenure, MonthlyCharges, TotalCharges, Contract, PaymentMethod, and service flags.
- The target column is `Churn` (Yes/No) in train and validation sets; absent in candidates.
- **Feature count** in model validation refers to the number of raw feature columns (excluding `customer_id` and the target), not the count after one-hot encoding.
- Tenure coefficient direction: `negative` means longer tenure reduces churn probability (standard expectation).
- Accuracy band thresholds: `below_70`, `70_to_79`, `80_to_89`, `90_plus`.
- Predict churn probability on the candidate set, then filter and rank the specified accounts.
- `predicted_churn_probability` uses 3 decimal places.

---

## Output Field Conventions

### Precision

| Type | Decimal Places | Example |
|---|---|---|
| Currency (ARR, revenue, overdue, pipeline amounts) | 2 | `1425000.00` |
| Percentages (SLA, win rate, accuracy) | 1 | `95.2` |
| Counts (tickets, accounts, headcount) | 0 (integer) | `14` |
| Churn probabilities | 3 | `0.129` |
| Risk scores | 0 (integer) | `85` |

### Controlled Enums

**Risk levels**: `critical`, `high`, `medium`, `low`

**Primary actions**: `executive_qbr`, `collections_followup`, `technical_recovery`, `renewal_save`, `nurture_monitor`, `no_action`

**Reason codes**: `overdue_receivable`, `low_tenure_high_churn`, `sla_degradation`, `nps_drop`, `usage_decline`, `renewal_window`, `expansion_offset`, `clean_billings`

**Link status**: `linked` (customer name matches a CRM account legal name), `unlinked` (no match)

**Metric sources** (for QBR packets): `billing_snapshot`, `support_export`, `sla_report`, `nps_survey`, `crm_closed_won`, `ar_aging`, `pipeline_crm`, `event_dashboard`, `hr_report`

**Ticket trend** (for QBR): `improving` (ticket count decreasing), `worsening` (increasing), `flat` (no meaningful change)

**Review owner** (for QBR): `customer_success`, `solutions_engineering`, `finance_ops`

**Agenda topics** (for QBR, choose exactly 4 from): `partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion`

**Accuracy bands** (for churn model): `below_70`, `70_to_79`, `80_to_89`, `90_plus`

**Tenure risk direction**: `negative` (longer tenure → lower risk), `positive`, `not_assessed`

**Outreach actions** (for churn model): `renewal_save`, `technical_recovery`, `collections_followup`, `nurture_monitor`

**Churn reason codes** (single code per candidate): same as risk reason codes above.

---

## Business-Policy Rules

### Risk Ranking Factors

When ranking accounts by renewal risk, consider these factors in combination:

1. **Lifecycle status** — `renewal_risk` and `paused` are explicit risk signals. `renewal_risk` carries the highest weight.
2. **Renewal timing** — Past-due renewals (date before assessment date) are high-risk. Approaching renewals (within 90 days) are elevated risk.
3. **Revenue exposure** — Higher ARR amplifies the impact of other risk factors. Strategic-segment accounts get heightened attention.
4. **Customer sentiment (NPS)** — Low absolute scores (<30) and significant score drops (>15 points across the period) are risk signals.
5. **SLA health** — Declining SLA compliance, especially below 90%, indicates service degradation.
6. **Usage trend** — Declining product usage (>5 percentage points) signals disengagement.
7. **Overdue receivables** — Balances over $5,000 in 31+ day buckets increase risk. The older the bucket, the higher the concern.
8. **Tenure** — Accounts with fewer than 24 months of tenure have elevated churn risk.
9. **Expansion pipeline** — Open expansion opportunities partially offset risk (they indicate ongoing commercial engagement).

### Action Assignment

- `executive_qbr` — Critical-risk accounts, especially strategic/enterprise with multiple risk factors. Requires executive-level intervention.
- `collections_followup` — Accounts with significant overdue receivables (>$5,000) as a primary concern.
- `technical_recovery` — Accounts where SLA degradation or support-ticket issues are the dominant risk driver.
- `renewal_save` — Accounts with approaching or past-due renewals where the primary goal is retention.
- `nurture_monitor` — Medium/low-risk accounts that need regular attention but no immediate escalation.
- `no_action` — Accounts with no material risk signals.

### Reason Code Assignment

Assign the most specific, data-supported reason codes (up to 5). Prefer concrete, measurable signals over generic labels. When multiple codes apply, order by severity (most impactful first). Use `clean_billings` only when no other negative signal is present.

### Board Sorting

For retention action boards, the standard order is by risk severity group, then by ARR (descending) within each group, then by account ID for ties.

### Follow-Up Due Dates

When the task specifies follow-up due dates by action type, use those exact dates for the `next_touch_due_date` field:

| Action | Typical Due Date Offset |
|---|---|
| `collections_followup` | ~15 days after period end |
| `technical_recovery` | ~18 days after period end |
| `renewal_save` | ~22 days after period end |
| `executive_qbr` | ~29 days after period end |
| `nurture_monitor` | ~36 days after period end |

---

## Exclusion Rules & Pitfalls

### Data Quality

- **Exclude spam and duplicate tickets** from all "clean" ticket counts. Check `is_spam` and `is_duplicate` flags.
- **Exclude retracted NPS responses**. Check both the `retracted` field in the NPS endpoint and `survey_status: "retracted"` in the metrics endpoint.
- **Do not round raw API values** before using them in output. The API values are already at the required precision. Rounding intermediate values introduces errors.
- **A/R entries without CRM matches are unlinked**, not errors. Subsidiaries, foundations, and alternative legal names that don't match any account's `legal_name` should be flagged as `unlinked` with `account_id: null`.

### Pipeline

- **Use `stage` not `state`** to classify won/lost/open. The `state` field may only contain `open`/`closed` while `stage` contains the granular classification (`Closed Won`, `Closed Lost`, `Proposal`, etc.).
- **Include all non-closed stages in pipeline counts**, including Prospecting and Discovery. These are valid pipeline stages.
- **Win rate denominator excludes open opportunities.** Use `won / (won + lost)`.

### ARR Sources

- **Prefer `billing_arr_current`** from the account profile as the source of truth for current ARR. This is the billing-system ARR.
- CRM ARR (`crm_arr`) may differ from billing ARR. When the task asks whether billing ARR is used, answer based on which source was actually used.

### Risk Model

- **Risk is multi-dimensional.** No single factor (not even `renewal_risk` lifecycle) determines risk alone. Combine signals.
- **Past-due renewal alone is not sufficient** for critical risk if all other indicators are healthy.
- **Expansion pipeline offsets risk** — an account with significant expansion activity may be engaged even if other signals are mixed.

### General

- **Read the answer template carefully.** Every field in the template must be populated with the correct type (object, array, string, number, boolean, null).
- **Sort orders matter.** When the task specifies a sort order (e.g., `customer_name ascending`), apply it exactly.
- **Response must be JSON only.** No explanatory text, markdown fences, or commentary.
- **Deterministic precision is required.** Currency to 2 decimals, percentages to 1 decimal, counts as integers.
