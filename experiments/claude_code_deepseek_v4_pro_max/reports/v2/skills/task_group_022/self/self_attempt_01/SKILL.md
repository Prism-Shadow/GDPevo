# Shared Operations Analytics API — Reusable Skill

## Overview

This skill covers querying and correcting data through the shared operations analytics API
(`GDPEVO_ENV_BASE_URL`). The API provides HTTP access to a SQLite database containing
accounts, products, subscriptions, usage, tickets, incidents, data-quality cases, and
metric notes. Every task follows a common read → filter → aggregate → format pipeline,
optionally applying corrections through the `/simulate` endpoint.

---

## 1. API Endpoints and Their Purposes

| Method | Endpoint | Purpose | When to Use |
|--------|----------|---------|-------------|
| GET | `/` | API documentation and endpoint listing | First contact; discover available endpoints |
| GET | `/health` | Service status | Verify the API is reachable |
| GET | `/schema` | Full DDL for all tables and views | Understand column types, constraints, CHECK clauses |
| GET | `/tables` | List of table and view names | Quick inventory |
| GET | `/tables/<name>?limit=N&offset=M` | Sample rows from one table or view | Inspect data distribution before writing queries |
| POST | `/query` | Read-only SQL: `{"sql": "...", "params": []}` | All SELECT-based analysis |
| POST | `/simulate` | Run UPDATE on temp copy, then run read-only queries | Test corrections and compute recomputed metrics |

### Simulate Request Format

```json
{
  "script": "UPDATE target_table SET col = 'new_val', audit_reason = '...', audit_updated_at = datetime('now') WHERE ... AND old_col = 'expected' AND audit_reason IS NULL",
  "queries": [
    {"name": "name_for_results", "sql": "SELECT ..."}
  ]
}
```

Response: `{"changed_rows": N, "results": {"name_for_results": {...}}}`

---

## 2. Database Views — Always Prefer These Over Raw Tables

| View | Filters Applied | Use For |
|------|----------------|---------|
| `production_usage_daily` | `environment = 'production'` | Usage queries; note this view does NOT expose `environment` column |
| `active_customer_accounts` | `is_internal = 0 AND account_status IN ('active','paused')` | Account join for customer-facing reports |
| `customer_support_tickets` | `category <> 'internal_test'` | Ticket queries; use instead of bare `tickets` table |

**Rule:** Always join `production_usage_daily` + `active_customer_accounts` for usage queries.
Always use `customer_support_tickets` for ticket queries, then add further filters.

---

## 3. Qualified Usage Rules (Compute-Hour Reports)

When a task asks for "qualified" usage, apply ALL of these filters:

```
production_usage_daily pud
JOIN active_customer_accounts aca ON pud.account_id = aca.account_id
WHERE pud.product_id = '<TARGET_PRODUCT>'
  AND pud.activity_date >= '<START>' AND pud.activity_date <= '<END>'
  AND pud.source_system = 'telemetry_v2'   -- exclude telemetry_v1 overlap
  AND pud.is_backfill = 0                  -- exclude late-arriving records
  AND aca.segment = '<SEGMENT>'            -- if task specifies (e.g., 'enterprise')
  AND aca.region = '<REGION>'              -- if task specifies (e.g., 'EMEA')
```

**Key rule:** Always exclude `source_system = 'telemetry_v1'` to avoid double-counting during
migration overlap periods. Metric note NOTE-010 confirms telemetry v1 and v2 may overlap.

**When joining subscriptions** (e.g., for "active subscription during period" checks):
Use `EXISTS (SELECT 1 FROM subscriptions s WHERE ...)` instead of a JOIN, because an account
may have multiple active subscriptions for the same product, which would double-count rows.

---

## 4. Qualified Ticket Rules (Defect Reports)

A "customer-impacting defect" ticket must pass ALL of these sequential filters:

1. **Base universe:** `customer_support_tickets` view (already excludes `internal_test` category)
2. **Product:** `product_id = '<TARGET>'`
3. **Date:** `created_at` within the report period (inclusive)
4. **Defect category:** `category IN ('bug', 'outage', 'performance', 'data_loss')`
   — Confirmed by NOTE-004: "Support defect analysis commonly includes bug, outage, performance, and data loss categories."
5. **Customer impact:** `customer_impact = 1`
6. **Not duplicate:** `is_duplicate = 0`
7. **Not canceled:** `status != 'canceled'`
8. **External account:** account `is_internal = 0` AND `account_status NOT IN ('test')`

### Exclusion Pipeline (Sequential)

Count exclusions in order — each step removes from what remains after the previous step:

1. `duplicate` — `is_duplicate = 1`
2. `canceled` — `status = 'canceled'` and not already excluded as duplicate
3. `internal_or_test_account` — account `is_internal = 1` OR `account_status = 'test'`
4. `non_customer_impact` — `customer_impact = 0`
5. `non_defect_category` — `category NOT IN ('bug','outage','performance','data_loss')`

**The sum of all sequential exclusions must equal (total_candidates - qualified_count).**

---

## 5. SLA Breach Definition

A ticket is breached when:
```sql
(closed_at IS NOT NULL AND closed_at > sla_due_at)
OR
(closed_at IS NULL AND sla_due_at < datetime('now'))
```

Open tickets past their SLA due date count as breached. The breach rate is:
```
ROUND(breached_count / qualified_count, 4)
```
Always rounded to **4 decimal places**.

### Median Close Hours

For closed qualified tickets only (`closed_at IS NOT NULL`):
1. Compute `(julianday(closed_at) - julianday(created_at)) * 24` for each
2. Take the median value (middle value when sorted; for even count, average the two middle)
3. Round to **2 decimal places**

---

## 6. Data Correction Patterns (DQ Cases)

### Reading a Correction Case

```sql
SELECT * FROM data_quality_cases WHERE case_id = '<CASE_ID>'
```

Key fields:
- `case_type`: `'usage_product_correction'` or `'ticket_duplicate_correction'`
- `case_status`: must be `'approved'`
- `target_table`: which table to update
- `target_ids_csv`: comma-separated list of IDs
- `field_name`: which column to change
- `old_value`: expected current value (empty string means NULL)
- `new_value`: value to set
- `audit_reason`: the exact string to write into audit fields
- `approval_code`: do NOT embed this in the SQL (it validates the case, not the data)

### Writing Safe Correction SQL

**Always include safety guards:**
```sql
UPDATE <target_table>
SET <field_name> = '<new_value>',
    audit_reason = '<audit_reason>',
    audit_updated_at = datetime('now')
WHERE <id_column> IN (<target_ids>)
  AND <field_name> = '<old_value>'   -- guard: ensure row still has expected old value
  AND audit_reason IS NULL           -- guard: prevent overwriting a prior correction
```

**For ticket duplicate corrections (`duplicate_of`):**
Also set `is_duplicate = 1` alongside setting `duplicate_of`. The qualification filter
uses `is_duplicate = 0`, so this ensures corrected tickets are excluded from qualified
counts.

**Always test with `/simulate` before returning final numbers.**

### Computing Recomputed Metrics

After simulating the correction, recompute the qualified metrics using the SAME filter
rules as the original report. The simulate queries should mirror the original qualification
logic exactly.

---

## 7. Incident Exposure Reports

### Incident Details

Read authoritative incident data from the `incidents` table:
```sql
SELECT * FROM incidents WHERE incident_id = '<INCIDENT_ID>'
```

### Incident Window

- `started_at`: inclusive start of the incident
- `resolved_at`: inclusive end of the incident
- The usage exposure window covers `activity_date` between `date(started_at)` and `date(resolved_at)` inclusive

### Followup Ticket Window

- `start_exclusive` = `resolved_at` (the exact timestamp; tickets created AT this moment are excluded)
- `end_inclusive` = `resolved_at + 7 days` (the exact timestamp + 7 days)
- Filter: `t.created_at > '<resolved_at>' AND t.created_at <= '<resolved_at + 7 days>'`

### Impacted Accounts

Accounts with:
1. Active subscription covering the incident date (`EXISTS (SELECT 1 FROM subscriptions s WHERE ...)`)
2. Qualified production usage on the incident date(s)
3. External customer accounts (`is_internal = 0`, `account_status IN ('active','paused')`)

### Followup Tickets

From the followup window, further restrict to:
- Accounts in the `impacted_region` from the incident record
- External accounts only
- Non-duplicate, non-canceled tickets

### Usage Exclusion Pipeline for Incidents

1. `usage_candidate_rows` — all rows in `usage_daily` for the product on the incident date
2. `usage_non_production_rows_excluded` — `environment != 'production'`
3. `usage_backfill_rows_excluded` — `is_backfill = 1`
4. `usage_internal_or_inactive_account_rows_excluded` — account `is_internal = 1` OR `account_status NOT IN ('active','paused')`
5. `usage_without_active_subscription_rows_excluded` — no active subscription for that date
6. `usage_telemetry_v1_overlap_rows_excluded` — `source_system = 'telemetry_v1'`

### Ticket Exclusion Pipeline for Incidents

1. `ticket_candidates_in_followup_window` — all tickets in the followup window for the product (excluding `internal_test` category)
2. `ticket_canceled_or_duplicate_excluded` — `is_duplicate = 1` OR `status = 'canceled'`
3. `ticket_non_customer_impact_excluded` — `customer_impact = 0`

---

## 8. Deterministic Ordering Conventions

Always apply these sort orders unless the answer template explicitly overrides:

| Output Section | Primary Sort | Secondary Sort | Tertiary Sort |
|---------------|-------------|----------------|---------------|
| `top_accounts` | `compute_hours` DESC (or `ticket_count` DESC) | `account_id` ASC | — |
| `regional_breakdown` | `region` ASC (alphabetical) | — | — |
| `account_breakdown` | `account_id` ASC | — | — |
| `affected_accounts` | `account_id` ASC | — | — |
| `accounts_to_notify` | `backlog_ticket_count` DESC | `highest_severity` priority (P1 before P2 before P3 before P4) | `account_id` ASC |
| `qualified_ticket_ids` | `ticket_id` ASC | — | — |
| `accounts_with_followup_tickets` | `account_id` ASC | — | — |
| `impacted_accounts` | `compute_hours` DESC | `account_id` ASC | — |

---

## 9. Rounding and Numeric Precision

| Field | Precision | Rule |
|-------|-----------|------|
| `compute_hours` | 2 decimal places | `ROUND(SUM(compute_hours), 2)` |
| `total_compute_hours` | 2 decimal places | Same as above |
| `added_compute_hours` | 2 decimal places | `ROUND(SUM(compute_hours), 2)` |
| `sla_breach_rate` | 4 decimal places | `ROUND(breached / total, 4)` — returns a decimal ratio, not a percentage |
| `median_close_hours` | 2 decimal places | Compute median, then `ROUND(..., 2)` |
| `api_calls` | integer | `SUM(api_calls)` — no rounding needed |

---

## 10. Output Field Conventions

### Period Objects
```json
{
  "period": {
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD"
  }
}
```
Dates are always formatted `YYYY-MM-DD` (date-only, no time component) for period fields.

### Datetime Fields
Incident windows and followup windows use `YYYY-MM-DD HH:MM:SS` format (24-hour clock).

### Severity Values
Always use normalized severity codes: `P1`, `P2`, `P3`, `P4`, `SEV1`, `SEV2`, `SEV3`.

When a severity bucket has zero tickets, still include it with value `0`.

### Region Values
Valid regions: `NA`, `EMEA`, `APAC`, `LATAM`. For incident impact: also `GLOBAL`.

### Audit Reason
Always use the exact string from the DQ case's `audit_reason` column. Do not invent or modify it.

---

## 11. Common Pitfalls and Their Fixes

### Pitfall 1: Subscription JOIN Doubles Rows
**Symptom:** SUMs are too high by a factor matching the number of subscriptions per account.
**Fix:** Use `EXISTS (SELECT 1 FROM subscriptions s WHERE s.account_id = ud.account_id AND ...)` instead of `JOIN subscriptions`. An account can have multiple active subscriptions for the same product.

### Pitfall 2: Using Column Not in View
**Symptom:** "no such column" error.
**Fix:** `production_usage_daily` does not expose `environment`. Don't filter on `environment` when using this view — it's already filtered to production.

### Pitfall 3: Forgetting Telemetry v1 Exclusion
**Symptom:** Usage counts are higher than expected.
**Fix:** Always add `source_system = 'telemetry_v2'` to usage queries. Telemetry v1 and v2 overlap during migrations (NOTE-010).

### Pitfall 4: Including Backfill Rows
**Symptom:** Usage totals are inflated.
**Fix:** Always add `is_backfill = 0` to usage queries. Backfill rows are late-arriving records (NOTE-003).

### Pitfall 5: Not Setting is_duplicate in Ticket Corrections
**Symptom:** Corrected tickets still appear in qualified counts after applying a duplicate correction.
**Fix:** When updating `duplicate_of`, also set `is_duplicate = 1`. The qualification filter uses `is_duplicate = 0`.

### Pitfall 6: Non-Sequential Exclusion Counting
**Symptom:** Exclusion counts don't sum correctly (exceed total excluded).
**Fix:** Apply exclusion filters sequentially. Each exclusion counts only from what remains after prior exclusions. The sum of all sequential exclusion counts must equal `(total_candidates - qualified_count)`.

### Pitfall 7: Using customer_support_tickets for Account Filtering
**Symptom:** Missing the account-level internal/test filter.
**Fix:** `customer_support_tickets` only filters on `category <> 'internal_test'` (ticket-level). You still need to join `accounts` and filter on `is_internal = 0` and `account_status NOT IN ('test')` for account-level filtering.

### Pitfall 8: Wrong SLA Breach Logic for Open Tickets
**Symptom:** Open tickets past their SLA are not counted as breaches.
**Fix:** Always use: `(closed_at IS NOT NULL AND closed_at > sla_due_at) OR (closed_at IS NULL AND sla_due_at < datetime('now'))`. Open tickets past SLA are breached too.

### Pitfall 9: Using JOIN for Severity-Max Per Account
**Symptom:** Incorrect `highest_severity` values in accounts_to_notify.
**Fix:** Use `MIN(CASE severity WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 WHEN 'P3' THEN 3 WHEN 'P4' THEN 4 END)` to find the highest-priority severity per account, then map back to the severity label. Sort accounts by this numeric rank ascending.

### Pitfall 10: Wrong Followup Window Boundaries
**Symptom:** Tickets at the resolution boundary are miscounted.
**Fix:** The followup window uses `start_exclusive > resolved_at` (strict greater-than) and `end_inclusive <= resolved_at + 7 days`. A ticket created exactly at `resolved_at` is NOT in the followup window.

---

## 12. Task-Type Quick Reference

### Usage Rollup
1. Parse product, segment, region, date range from prompt
2. Query qualified usage with all filters (Section 3)
3. Compute per-account totals, regional breakdown, telemetry_v1 excluded count
4. Order accounts by compute_hours DESC, account_id ASC
5. Include ALL regions in regional_breakdown (not just the filtered one)

### Defect Rollup / Backlog
1. Parse product, date range from prompt
2. Count sequential exclusions (Section 4)
3. Filter to qualified tickets
4. Compute SLA breach rate (Section 5)
5. Compute median close hours for closed tickets
6. Top 5 accounts by ticket_count DESC, account_id ASC

### Data Correction (Usage)
1. Read the DQ case
2. Write safe UPDATE with guards (Section 6)
3. Simulate the correction
4. Compute recomputed metrics: total hours, affected enterprise accounts, top account

### Data Correction (Tickets)
1. Read the DQ case
2. Write safe UPDATE setting both `duplicate_of` and `is_duplicate = 1`
3. Simulate the correction
4. Compute recomputed metrics: qualified count, backlog by severity, SLA breach rate, accounts to notify

### Incident Exposure
1. Read the incident record
2. Compute followup window (Section 7)
3. Find impacted accounts (qualified usage + active subscription)
4. Find followup tickets (impacted region + followup window)
5. Compute all exclusion counts
6. Determine highest-usage account and severity mix
