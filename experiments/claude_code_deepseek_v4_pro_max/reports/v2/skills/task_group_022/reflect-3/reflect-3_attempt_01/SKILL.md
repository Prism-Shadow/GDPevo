# Operations Analytics Skill — task_group_022 (reflect-3)

## Overview

This skill covers querying the shared operations analytics database through its HTTP API to produce usage rollups, defect ticket reports, incident exposure summaries, and data-quality correction workflows. The database is SQLite-backed with tables for accounts, products, subscriptions, usage, tickets, incidents, and data-quality cases. Three convenience views are also available.

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET /health` | Service status |
| `GET /schema` | Full table/view/column catalog |
| `GET /tables` | Table and view names |
| `GET /tables/<name>?limit=100&offset=0` | Sample rows |
| `POST /query` | Read-only SQL: `{"sql": "...", "params": []}` |
| `POST /simulate` | Run an UPDATE script on a temp copy, then run read-only queries. Body: `{"script": "<SQL>", "queries": [{"sql": "...", "params": []}]}`. Returns `changed_rows` and `results`. |

Always start with `GET /schema` to confirm column names, types, and constraints before writing queries.

---

## Database Schema

### Tables

**accounts** — `account_id` (PK), `account_name`, `segment` (enterprise|commercial|startup|internal), `region` (NA|EMEA|APAC|LATAM), `account_status` (active|paused|churned|test), `owner_team`, `is_internal` (0|1), `created_at`

**products** — `product_id` (PK; values: ATLASDB, HELIOSYNC, NEXAQUEUE, LUMAFORMS), `product_name`, `product_family`, `is_active`

**subscriptions** — `subscription_id` (PK), `account_id` (FK→accounts), `product_id` (FK→products), `plan_code` (enterprise|growth|standard|trial|internal), `subscription_status` (active|paused|ended|trial), `start_date`, `end_date` (nullable). Constraint: `end_date IS NULL OR end_date >= start_date`.

**usage_daily** — `usage_id` (PK), `account_id` (FK), `product_id` (FK), `activity_date`, `environment` (production|staging|sandbox|internal), `source_system` (telemetry_v1|telemetry_v2|import_patch), `seats_active`, `api_calls`, `compute_hours` (REAL), `data_gb` (REAL), `is_backfill` (0|1), `recorded_at`, `audit_reason`, `audit_updated_at`

**tickets** — `ticket_id` (PK), `account_id` (FK), `product_id` (FK), `created_at`, `closed_at` (nullable), `status` (open|in_progress|resolved|canceled), `severity` (P1|P2|P3|P4), `category` (bug|outage|performance|data_loss|how_to|billing|feature_request|internal_test), `customer_impact` (0|1), `is_duplicate` (0|1), `duplicate_of` (FK→tickets, nullable), `linked_incident_id` (FK→incidents, nullable), `sla_due_at`, `audit_reason`, `audit_updated_at`

**incidents** — `incident_id` (PK), `product_id` (FK), `started_at`, `resolved_at`, `severity` (SEV1|SEV2|SEV3), `impacted_region` (NA|EMEA|APAC|LATAM|GLOBAL), `public_status` (resolved|monitoring|closed). Constraint: `resolved_at >= started_at`.

**data_quality_cases** — `case_id` (PK), `case_type` (usage_product_correction|ticket_duplicate_correction), `case_status` (approved|draft|rejected), `target_table`, `target_ids_csv`, `field_name`, `old_value`, `new_value`, `approval_code`, `audit_reason`, `created_at`

**metric_notes** — `note_id` (PK), `topic`, `note_text`, `updated_at`. Provides semantic guidance for common analysis patterns. Always query this table first in any new task domain.

### Views

- **active_customer_accounts** — `SELECT … FROM accounts WHERE is_internal = 0 AND account_status IN ('active', 'paused')`
- **customer_support_tickets** — `SELECT … FROM tickets WHERE category <> 'internal_test'`
- **production_usage_daily** — `SELECT … FROM usage_daily WHERE environment = 'production'`

---

## Qualification Rules

### Qualified Usage (compute-hours rollups)

1. `environment = 'production'`
2. `is_backfill = 0`
3. **Telemetry overlap rule**: When both `telemetry_v1` and `telemetry_v2` rows exist for the same `(account_id, activity_date)`, **exclude all `telemetry_v1` rows** for that date and keep `telemetry_v2`. Count excluded v1 rows as `telemetry_v1_rows_excluded`. This rule applies to all usage-based metrics.
4. Account is enterprise segment (`segment = 'enterprise'`), not internal (`is_internal = 0`), and not test (`account_status != 'test'`). Do **not** exclude churned or paused accounts from usage qualification.
5. Active enterprise subscription: `plan_code = 'enterprise'`, `subscription_status = 'active'`, and the subscription window covers the usage date (`start_date <= activity_date AND (end_date IS NULL OR end_date >= activity_date)`).

**Critical**: Use `EXISTS (SELECT 1 FROM subscriptions s WHERE …)` for subscription checks. Never use a plain `JOIN subscriptions` — a single account can have multiple subscriptions for the same product, which multiplies usage rows.

### Qualified Tickets (customer-impacting defect)

1. `product_id` matches the target product.
2. `created_at` within the reporting period (inclusive).
3. `customer_impact = 1`.
4. `category IN ('bug', 'outage', 'performance', 'data_loss')` — these are the four defect categories per metric note NOTE-004.
5. Account is not internal and not test (`is_internal = 0 AND account_status != 'test'`). Do **not** exclude churned accounts.
6. `is_duplicate = 0` — duplicate tickets are excluded from qualified counts.
7. `status != 'canceled'` — canceled tickets are excluded.

### Incident Exposure

- Incident window and impacted region come from the `incidents` table — treat the database record as authoritative.
- Usage exposure: apply the standard usage qualification rules during the incident-window dates.
- Follow-up ticket window: `start_exclusive = resolved_at`, `end_inclusive = resolved_at + 7 days`. Filter tickets created in this window for **external customer accounts in the impacted region** (`is_internal = 0`, `account_status != 'test'`, region matches `impacted_region`).
- Qualified follow-up tickets: apply the ticket qualification rules (customer-impacting defect) on top of the window + region filter.

---

## SLA Breach Rules

- **Closed tickets**: breached if `closed_at > sla_due_at`.
- **Open / in_progress tickets**: breached if the reporting reference date (typically the day after the period end, e.g. `2026-04-01` for a March 2026 report) is later than `sla_due_at`.
- **SLA breach rate** = `(breached_closed + breached_open) / total_qualified`. Round to **4 decimal places**.

---

## Data Quality Corrections

### Correction SQL Pattern

Write **safe, idempotent UPDATE statements**:

```sql
UPDATE <target_table>
SET <field_name> = '<new_value>',
    audit_reason = '<audit_reason from DQ case>',
    audit_updated_at = '<created_at from DQ case>'
WHERE <id_column> IN (<target_ids_csv>)
  AND <field_name> = '<old_value>'
  AND audit_reason IS NULL
```

- Always include the old-value guard and the `audit_reason IS NULL` guard so the statement is safe to re-run.
- For `ticket_duplicate_correction` cases: set `is_duplicate = 1` and `duplicate_of = '<new_value>'` (the master ticket ID) in addition to the field-specific change.
- For `usage_product_correction` cases: set `product_id = '<new_value>'` (the correct product).
- `changed_row_count` is the number of rows the UPDATE targets (the count of IDs in `target_ids_csv`).
- After correction, recompute all metrics with the standard qualification rules applied to the corrected database state.

### Using the Simulate Endpoint

`POST /simulate` applies the correction script to a temporary copy, then runs your queries against the copy. Use it to verify both the correction and the recomputed metrics before finalizing:

```json
{
  "script": "UPDATE usage_daily SET product_id = 'ATLASDB', … WHERE …",
  "queries": [
    {"sql": "SELECT …", "params": []},
    {"sql": "SELECT …", "params": []}
  ]
}
```

The response includes `changed_rows` and `results` with one key per query (`query_1`, `query_2`, …).

---

## Ordering Conventions

| Context | Sort |
|---------|------|
| Regional breakdown | Alphabetical by region (APAC, EMEA, LATAM, NA) |
| Account breakdown | Ascending `account_id` |
| Top accounts by compute hours | Descending `compute_hours`, then ascending `account_id` for ties |
| Top accounts by ticket count | Descending `ticket_count`, then ascending `account_id` for ties |
| Severity priority | P1 (highest) → P2 → P3 → P4 (lowest). Use `ORDER BY CASE severity WHEN 'P1' THEN 0 WHEN 'P2' THEN 1 WHEN 'P3' THEN 2 WHEN 'P4' THEN 3 END` |
| Accounts to notify (defect backlog) | 1. Descending `backlog_ticket_count`, 2. Ascending severity priority (P1 first), 3. Ascending `account_id` |
| Impacted accounts (incident) | Ascending `account_id` |
| Follow-up ticket accounts | Ascending `account_id` |

---

## Rounding and Precision

| Field | Precision |
|-------|-----------|
| `compute_hours` | 2 decimal places (`ROUND(…, 2)`) |
| `sla_breach_rate` | 4 decimal places |
| `median_close_hours` | 2 decimal places |
| `added_compute_hours` | 2 decimal places |

---

## Median Calculation

When computing `median_close_hours` for closed qualified tickets:
1. Compute `(closed_at - created_at)` in hours for each closed qualified ticket.
2. Sort the values ascending.
3. If odd count N: median = value at index `(N-1)/2` (0-indexed).
4. If even count N: median = average of values at indices `N/2 - 1` and `N/2`.
5. Round to 2 decimal places.

Only closed tickets contribute. Open/in_progress tickets are excluded from the median.

---

## Excluded Counts Pattern

When reporting exclusion breakdowns, use **independent (overlapping) counts** — count each exclusion criterion against the full candidate pool separately. Do not use cascading/sequential counts where earlier exclusions shrink the pool for later criteria.

For usage exclusions:
- `usage_non_production_rows_excluded`: `environment != 'production'`
- `usage_backfill_rows_excluded`: `is_backfill = 1`
- `usage_internal_or_inactive_account_rows_excluded`: `is_internal = 1 OR account_status = 'test'`
- `usage_without_active_subscription_rows_excluded`: among production, non-backfill, non-internal rows — those without an active enterprise subscription
- `usage_telemetry_v1_overlap_rows_excluded`: `telemetry_v1` rows where a `telemetry_v2` row exists for the same account and date

For ticket exclusions:
- `duplicate`: `is_duplicate = 1`
- `canceled`: `status = 'canceled'`
- `internal_or_test_account`: `is_internal = 1 OR account_status = 'test'`
- `non_customer_impact`: `customer_impact = 0`
- `non_defect_category`: `category NOT IN ('bug', 'outage', 'performance', 'data_loss')`

---

## Common Pitfalls

1. **JOIN subscriptions directly**: Using `JOIN subscriptions` with `GROUP BY` multiplies rows when an account has multiple active subscriptions for the same product. Always use `EXISTS (SELECT 1 FROM subscriptions s WHERE s.account_id = … AND …)`.

2. **Forgetting telemetry overlap**: Usage metrics must always exclude `telemetry_v1` rows when `telemetry_v2` exists for the same account and date. Compute this per-account per-date before summing.

3. **Excluding churned accounts from tickets**: Churned accounts (`account_status = 'churned'`) are still external customers. Only exclude `is_internal = 1` and `account_status = 'test'` accounts.

4. **Including non-defect categories**: Only `bug`, `outage`, `performance`, and `data_loss` are defect categories. `how_to`, `billing`, `feature_request`, and `internal_test` are not defects.

5. **Subscript start-date filtering**: An account only qualifies for usage metrics on dates when its enterprise subscription is active. A subscription starting mid-period means only later dates qualify.

6. **Incorrect SLA reference for open tickets**: Open/in_progress tickets should be checked against the reporting reference date (period end + 1 day), not `closed_at`.

7. **Cascading exclusion counts**: Use independent (overlapping) counts, not sequential/cascading ones.

8. **Correction SQL without safety guards**: Always include `AND field_name = 'old_value' AND audit_reason IS NULL` in the WHERE clause.

9. **/simulate query format**: Queries in simulate must be objects `{"sql": "…", "params": []}`, not plain strings.

10. **Answer template fields**: Some template fields like `top_accounts_ordering` are documentation, not actual answer keys. Only include the data fields shown in the template structure.

---

## Workflow Summary

1. **Read `/schema` and `metric_notes`** to understand the data model and domain conventions.
2. **Identify the product**, period, region scope, and metric type from the task description.
3. **Query the DQ case** (if applicable) from `data_quality_cases` to get target IDs, field, old/new values, and audit reason.
4. **Apply qualification filters** in order: product → period → environment → backfill → account status → subscription → overlap (for usage) or product → period → customer impact → defect category → account status → duplicate/canceled (for tickets).
5. **Handle telemetry overlap** for all usage queries: group by account + date, check for both v1 and v2, exclude v1 when v2 present.
6. **Use EXISTS for subscription joins** to avoid row multiplication.
7. **For corrections**: simulate first, verify changed rows and recomputed metrics, then write the final answer with the safe SQL.
8. **Apply correct ordering** for each output section.
9. **Round all numeric outputs** to the specified precision.
10. **Include zero-valued severity buckets** (P1–P4) even when empty.
