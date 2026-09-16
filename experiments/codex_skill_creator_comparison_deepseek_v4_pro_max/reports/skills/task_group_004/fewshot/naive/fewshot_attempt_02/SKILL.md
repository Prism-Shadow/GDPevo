---
name: apexcloud-retention-ops
description: Solve ApexCloud Retention Operations API tasks using the staged task environment. Covers renewal risk queues, QBR packets, receivables reviews, churn model validation, and retention action boards.
---

# ApexCloud Retention Operations Skill

This skill covers the ApexCloud Retention Operations API, a synthetic SaaS retention dataset with accounts, billing, support tickets, NPS surveys, A/R aging, opportunities pipeline, HR summaries, event performance, churn model exports, and account metric extracts.

## Base URL

The task prompt provides a base URL as the `<TASK_ENV_BASE_URL>` placeholder. Replace it with the actual URL before making any API call. All endpoints listed below are relative to that base.

## API Endpoints

See [reference/api.md](reference/api.md) for the complete endpoint reference with parameter formats, response shapes, and field descriptions.

Summary of available endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Service health and row counts |
| GET | `/api/accounts` | All CRM accounts |
| GET | `/api/accounts/{id}` | Single account details |
| GET | `/api/accounts/{id}/metrics?start=YYYY-MM&end=YYYY-MM` | Monthly metrics per account |
| GET | `/api/accounts/{id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` | Support tickets per account |
| GET | `/api/accounts/{id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` | NPS survey responses per account |
| GET | `/api/billing/snapshots` | Quarterly billing snapshots |
| GET | `/api/finance/ar-aging` | Global A/R aging by quarter |
| GET | `/api/opportunities` | All CRM opportunities |
| GET | `/api/hr/summary` | HR summaries by region and quarter |
| GET | `/api/events/performance` | Event performance by quarter |
| GET | `/exports/churn/train.csv` | Churn model training set |
| GET | `/exports/churn/validation.csv` | Churn model validation set |
| GET | `/exports/churn/candidates.csv` | Churn candidate accounts |
| GET | `/exports/account_metric_extract.csv` | Full account metric extract |

## Controlled Vocabularies

Every task uses controlled enum labels. See [reference/vocabularies.md](reference/vocabularies.md) for the complete set. Never invent or approximate these values. The vocabularies are organized by domain:

- **Risk levels**: `critical`, `high`, `medium`, `low`
- **Primary actions**: `collections_followup`, `technical_recovery`, `renewal_save`, `executive_qbr`, `nurture_monitor`, `no_action`
- **Reason codes**: `overdue_receivable`, `low_tenure_high_churn`, `sla_degradation`, `nps_drop`, `usage_decline`, `renewal_window`, `expansion_offset`, `clean_billings`
- **Metric sources**: `crm_closed_won`, `support_export`, `sla_report`, `nps_survey`, `billing_snapshot`, `ar_aging`, `pipeline_crm`, `event_dashboard`, `hr_report`
- **Ticket trends**: `improving`, `worsening`, `flat`
- **Review owners**: `solutions_engineering`, `customer_success`, `finance_ops`
- **Agenda topics**: `partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion`
- **Link status**: `linked`, `unlinked`
- **Accuracy bands**: `below_70`, `70_to_79`, `80_to_89`, `90_plus`
- **Coefficient directions**: `negative`, `positive`, `zero`, `not_assessed`
- **Outreach actions**: `renewal_save`, `technical_recovery`, `collections_followup`, `nurture_monitor`
- **Policy codes**: See vocabulary reference for all `RS-*`, `REV-*`, `SUP-*`, `ACT-*`, `RCP-*`, `CM-*`, `PW-*`, `FS-*`, `MOD-*`, `PRB-*`, `DEP-*`, `OUT-*`, `BORD-*`, `EXP-*`, `CAL-*` codes.

## Numeric Precision Rules

Apply these conventions to every output value:

| Value type | Precision | Example |
|------------|-----------|---------|
| Currency (revenue, ARR, balances, pipeline) | 2 decimal places | `1234567.89` |
| Percentages (SLA, win rate, accuracy) | 1 decimal place | `93.3` |
| Counts (tickets, accounts, headcount) | Integer | `13` |
| Risk scores | Integer | `100` |
| Churn probabilities | 3 decimal places | `0.102` |
| NPS scores | Integer | `39` |

For `null` values: use JSON `null` only when the source data is truly unavailable. Zero `0` and `0.0` are distinct from `null`.

## Data Reconciliation Rules

### Account matching across APIs

The `/api/accounts` endpoint returns CRM accounts with `account_id`, `legal_name`, and `account_aliases`. Other endpoints use `customer_name` (A/R aging) or `account_legal_name` (opportunities). To reconcile:

1. Match by exact `account_id` where available.
2. When only a `customer_name` is present (A/R aging), check it against `legal_name` fields across all accounts.
3. If no exact legal_name match, check `customer_name` against `account_aliases` arrays.
4. Mark `link_status` as `"linked"` when a CRM account match is found, `"unlinked"` otherwise.

### Ticket cleaning

When computing clean ticket counts:

1. Exclude tickets where `is_duplicate` is `true`.
2. Exclude tickets where `is_spam` is `true`.
3. Count only the remaining tickets.
4. Use the `created_date` field for period filtering.

SLA compliance for individual months: the metrics endpoint provides pre-computed `sla_compliance` values. When computing SLA from raw tickets, count tickets where `resolution_sla_met` is `true` among clean tickets in the period, and divide by total clean tickets.

### NPS handling

- The `/api/accounts/{id}/metrics` endpoint includes pre-computed `nps_score` per month.
- The `/api/accounts/{id}/nps` endpoint returns individual responses with `score` and `retracted` fields.
- Exclude retracted responses (`retracted` is `true`) when computing NPS from raw responses.
- Use the most recent non-retracted NPS score within the analysis period as `latest_nps`.

### ARR sources

Two ARR figures exist per account:

- `crm_arr` from `/api/accounts/{id}` -- CRM-sourced ARR.
- `billing_arr_current` from `/api/accounts/{id}` -- billing-sourced ARR.
- `billing_arr` from `/api/billing/snapshots` -- quarterly billing snapshot ARR.

When a task requires `current_arr` or `billing_arr_source`, use the billing snapshot matching the assessment date's quarter. The `account_metric_extract.csv` uses `recognized_revenue` from metrics, not ARR.

### Overdue balance calculation

Sum the aging buckets beyond current: `1_30 + 31_60 + 61_90 + 90_plus`. Filter A/R records by the specified as-of date. The `current` bucket represents not-yet-due amounts and is excluded from overdue totals.

### Usage trend detection

Compare `product_usage` values month-over-month from the metrics endpoint. If adjacent months show declining usage in consecutive periods, flag `usage_decline`. The `account_metric_extract.csv` provides the same data in bulk.

### Tenure risk

- Shorter `contract_tenure_months` correlates with higher churn risk.
- The churn model exports confirm this: `tenure_coefficient_direction` is `"negative"` (lower tenure = higher churn probability).
- Apply `low_tenure_high_churn` as a reason code for accounts below approximately 24 months tenure when combined with other risk signals.

## Task Pattern Reference

Each task type follows a predictable flow:

### Renewal Risk Queue

Fetch accounts, then metrics/tickets/NPS/billing/A/R for each account_id in the scoped list. Score each account using weighted signals: renewal proximity, overdue balance, NPS trajectory, SLA degradation, usage decline, tenure, and expansion offsets. Rank by descending risk_score. Use the `risk_level` vocabulary for classification thresholds.

### QBR Metrics Packet

Fetch a single account's metrics for the given month range. Also fetch tickets and NPS responses raw to confirm source attribution. Compute highlights (averages, peaks, trends) from the monthly data. Assign `metric_sources` enum values based on which endpoint supplied each metric. Select agenda topics that match the account's actual situation.

### Receivables and Pipeline Operations Review

Fetch A/R aging filtered by quarter/as-of date. For each overdue customer, attempt to match to a CRM account via legal_name/aliases. Fetch opportunities for pipeline summary (won/lost/open counts and revenue, filtered by the given date range). Fetch HR and events for ops_context. Sort overdue_followups by customer_name ascending.

### Churn Model Validation

Fetch all three CSV exports. Parse CSV with a proper parser (Python `csv` module or `csv.DictReader`). Compute validation statistics: row counts, feature count, accuracy, accuracy band. Rank candidate accounts by `predicted_churn_probability` descending. Map outreach actions based on churn probability thresholds and known risk factors. Compute cohort checks: counts of past-due and low-tenure candidates among the ranked set, average probability of top 5.

### High-Touch Retention Operations Board

Fetch accounts, billing snapshots, metrics, tickets, NPS, A/R aging, and opportunities for all scoped accounts. For each account, assess: ARR (from billing snapshot), overdue balance (from A/R), NPS trajectory, SLA health, usage trend, renewal timing, and expansion pipeline. Score and rank. Assign risk_level, primary_action, next_touch_due_date from the provided follow-up calendar, and reason_codes. Compute segment_summary (strategic vs enterprise counts, total ARR at risk, open expansion pipeline, net revenue exposure = ARR at risk minus expansion pipeline).

## CSV Parsing

When fetching CSV exports, use Python's `csv.DictReader` for reliable parsing. Parse numeric fields explicitly:

```python
import csv, io, urllib.request

def fetch_csv(url):
    with urllib.request.urlopen(url) as resp:
        text = resp.read().decode('utf-8')
    return list(csv.DictReader(io.StringIO(text)))
```

## API Calling Conventions

- Use `curl` with `-s` for silence and pipe through `python3 -m json.tool` for readable output when exploring.
- When scripting, use Python `urllib.request` with `json.loads()`.
- Always URL-encode query parameters (Python's `urllib.parse.urlencode`).
- Date formats: metrics use `YYYY-MM` (e.g., `2026-04`), tickets and NPS use `YYYY-MM-DD` (e.g., `2026-04-01`).
- The API returns JSON arrays wrapped in objects with a `count` field for list endpoints. Access the data via the named key (e.g., `data["accounts"]`, `data["metrics"]`, `data["tickets"]`).

## Output Format

- Return **valid JSON only** unless the task explicitly requests another format.
- Follow the exact JSON shape specified in the task or its payload template.
- Do not include explanatory text, markdown fences, or commentary outside the JSON structure.
- Sort ordered lists exactly as specified (by rank, by customer_name ascending, etc.).
- Include all required top-level keys; omit optional keys only when the task explicitly allows it.
