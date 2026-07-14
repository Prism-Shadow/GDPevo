# Ops Analytics API Skill — task_group_022 (self)

## Overview

Skill for querying a shared operations analytics SQLite database through a REST API (`{BASE_URL}`). Covers usage rollups, defect ticket rollups, incident exposure summaries, and data-quality correction simulations. Every response must match an exact JSON template with precise field types, ordering, and rounding.

---

## 1. API Workflow Rules

### 1.1 Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/schema` | Full table/view/column catalog — always call first |
| GET | `/tables` | Table and view names only |
| GET | `/tables/<name>?limit=N&offset=M` | Sample rows from one table/view |
| POST | `/query` | Read-only SQL. Body: `{"sql": "...", "params": []}` |
| POST | `/simulate` | Run an UPDATE/DELETE script on a temp copy, then run read-only queries. Body: `{"script": "UPDATE ...", "queries": [{"sql": "SELECT ..."}]}` |

### 1.2 Workflow Order

1. **GET `/schema`** — understand columns, constraints, views.
2. **GET `/tables/<name>`** — sample data to verify assumptions.
3. **POST `/query`** — execute read-only analysis queries.
4. **POST `/simulate`** — for corrections: run the update script, then recompute metrics with queries.

### 1.3 Simulate Endpoint Detail

```json
{
  "script": "UPDATE usage_daily SET product_id = 'ATLASDB', audit_reason = '...', audit_updated_at = datetime('now') WHERE usage_id IN (...) AND product_id = 'HELIOSYNC'",
  "queries": [
    {"sql": "SELECT COUNT(*) as changed FROM usage_daily WHERE audit_reason = '...'"},
    {"sql": "SELECT ROUND(SUM(compute_hours), 2) as total_ch FROM ..."}
  ]
}
```

Response: `{"changed_rows": N, "results": {"query_1": {...}, "query_2": {...}}}`

`changed_rows` is the number of rows the script modified. Use it directly as `changed_row_count` / `changed_ticket_count`.

---

## 2. Database Schema Reference

### Tables
- **accounts**: account_id (PK), account_name, segment, region, account_status, is_internal (0/1), owner_team, created_at
- **products**: product_id (PK: ATLASDB, HELIOSYNC, LUMAFORMS, NEXAQUEUE), product_name, product_family, is_active (0/1)
- **usage_daily**: usage_id (PK), account_id (FK), product_id (FK), activity_date, environment, source_system, seats_active, api_calls, compute_hours, data_gb, is_backfill (0/1), recorded_at, audit_reason, audit_updated_at
- **tickets**: ticket_id (PK), account_id (FK), product_id (FK), created_at, closed_at, status, severity, category, customer_impact (0/1), is_duplicate (0/1), duplicate_of (FK self), linked_incident_id (FK), sla_due_at, audit_reason, audit_updated_at
- **subscriptions**: subscription_id (PK), account_id (FK), product_id (FK), plan_code, subscription_status, start_date, end_date
- **incidents**: incident_id (PK), product_id (FK), started_at, resolved_at, severity (SEV1/SEV2/SEV3), impacted_region, public_status
- **data_quality_cases**: case_id (PK), case_type, case_status, target_table, target_ids_csv, field_name, old_value, new_value, approval_code, audit_reason, created_at
- **metric_notes**: note_id, topic, note_text, updated_at

### Views
- **active_customer_accounts**: accounts WHERE is_internal=0 AND account_status IN ('active','paused')
- **customer_support_tickets**: tickets WHERE category <> 'internal_test'
- **production_usage_daily**: usage_daily WHERE environment = 'production'

### Enums
- **segment**: enterprise, commercial, startup, internal
- **region**: NA, EMEA, APAC, LATAM
- **account_status**: active, paused, churned, test
- **environment**: production, staging, sandbox, internal
- **source_system**: telemetry_v1, telemetry_v2, import_patch
- **ticket status**: open, in_progress, resolved, canceled
- **ticket severity**: P1, P2, P3, P4
- **ticket category**: bug, outage, performance, data_loss, how_to, billing, feature_request, internal_test
- **subscription plan_code**: enterprise, growth, standard, trial, internal
- **subscription_status**: active, paused, ended, trial
- **incident severity**: SEV1, SEV2, SEV3
- **incident impacted_region**: NA, EMEA, APAC, LATAM, GLOBAL
- **DQ case_type**: usage_product_correction, ticket_duplicate_correction
- **DQ case_status**: approved, draft, rejected

---

## 3. Usage Qualification Rules

Every usage query must apply these filters to be "qualified":

### 3.1 Core Usage Filters

```sql
WHERE environment = 'production'
  AND is_backfill = 0
  AND source_system != 'telemetry_v1'
```

**Rationale** (from metric_notes and schema views):
- Only `production` environment counts (NOTE-002: "customer-facing workload observations")
- Backfill rows excluded (NOTE-003: "late-arriving records loaded after normal telemetry processing")
- Telemetry v1 excluded to avoid overlap with v2 during migration (NOTE-010)

### 3.2 Account Filters

```sql
AND account_id IN (
  SELECT account_id FROM accounts
  WHERE is_internal = 0
    AND account_status IN ('active', 'paused')
)
```

Or equivalently, join against `active_customer_accounts` view.

### 3.3 Product/Date Scoping

Always scope to the correct product and inclusive date range:
```sql
AND product_id = '<PRODUCT_ID>'
AND activity_date >= '<START_DATE>'
AND activity_date <= '<END_DATE>'
```

### 3.4 Enterprise-Specific

When the task specifies "enterprise accounts":
```sql
AND segment = 'enterprise'
```

### 3.5 Regional Scoping

When region is specified:
```sql
AND region = '<REGION>'
```

### 3.6 Telemetry v1 Exclusion Counting

`telemetry_v1_rows_excluded` counts rows that match ALL other qualification criteria (product, dates, account, region, segment, production, non-backfill) but have `source_system = 'telemetry_v1'`. Count from the pre-filtered pool — NOT from the full table.

---

## 4. Ticket Qualification Rules

### 4.1 Customer-Impacting Defect Tickets

```sql
WHERE product_id = '<PRODUCT_ID>'
  AND created_at >= '<START_DATE>'
  AND created_at <= '<END_DATE>'
  AND customer_impact = 1
  AND category IN ('bug', 'outage', 'performance', 'data_loss')
  AND is_duplicate = 0
  AND status != 'canceled'
  AND account_id IN (
    SELECT account_id FROM accounts
    WHERE is_internal = 0 AND account_status != 'test'
  )
```

**Defect categories** (per NOTE-004): bug, outage, performance, data_loss.

**Non-defect categories** to exclude: how_to, billing, feature_request, internal_test.

### 4.2 SLA Breach

A ticket breaches SLA if it was not resolved before its SLA deadline:

```sql
-- Breached if: still open/in_progress past sla_due_at, OR resolved after sla_due_at
CASE WHEN (status IN ('open', 'in_progress'))
      OR (closed_at > sla_due_at)
     THEN 1 ELSE 0 END AS sla_breach
```

SLA breach rate = `breach_count / qualified_ticket_count`, rounded to **4 decimal places**.

### 4.3 Median Close Hours

Compute for **closed** (resolved) qualified tickets only. Use the median of `(julianday(closed_at) - julianday(created_at)) * 24`. Round to **2 decimal places**.

### 4.4 Excluded Counts (for defect rollup)

Count from the full candidate pool matching product + date range + account (customer, non-test, non-internal), then break down exclusions:

| Exclusion | Filter |
|-----------|--------|
| duplicate | `is_duplicate = 1` |
| canceled | `status = 'canceled'` |
| internal_or_test_account | account `is_internal = 1` or `account_status = 'test'` |
| non_customer_impact | `customer_impact = 0` |
| non_defect_category | `category NOT IN ('bug','outage','performance','data_loss')` |

These are **non-overlapping** — apply them in sequence, each counting rows excluded at that step. The qualified pool is what remains after ALL exclusions.

### 4.5 P1/P2 Open Count

Among qualified tickets, count those where `severity IN ('P1','P2')` AND `status IN ('open','in_progress')`.

---

## 5. Correction SQL Patterns

### 5.1 Reading the DQ Case

Always query `data_quality_cases` first to get the authoritative correction parameters:
```sql
SELECT * FROM data_quality_cases
WHERE case_id = '<CASE_ID>' AND case_status = 'approved'
```

Key fields:
- `target_table`: which table to update
- `target_ids_csv`: comma-separated list of primary keys
- `field_name`: which column to change
- `old_value`: expected current value (use in WHERE guard)
- `new_value`: value to set
- `audit_reason`: exact string to write into audit_reason column
- `approval_code`: verification code

### 5.2 Safe UPDATE Pattern

Always include an **old-value guard** in the WHERE clause:

```sql
UPDATE <target_table>
SET <field_name> = '<new_value>',
    audit_reason = '<audit_reason>',
    audit_updated_at = datetime('now')
WHERE <pk_column> IN (<comma-separated-ids>)
  AND <field_name> = '<old_value>'
```

**For usage_product_correction** — updating `product_id`:
```sql
UPDATE usage_daily
SET product_id = '<new_value>',
    audit_reason = '<audit_reason>',
    audit_updated_at = datetime('now')
WHERE usage_id IN ('ID1','ID2',...)
  AND product_id = '<old_value>'
```

**For ticket_duplicate_correction** — setting `duplicate_of`:
When `field_name = 'duplicate_of'`, the correction marks tickets as duplicates. Set both `is_duplicate = 1` AND `duplicate_of = '<new_value>'`:
```sql
UPDATE tickets
SET is_duplicate = 1,
    duplicate_of = '<new_value>',
    audit_reason = '<audit_reason>',
    audit_updated_at = datetime('now')
WHERE ticket_id IN ('ID1','ID2',...)
  AND is_duplicate = 0
  AND duplicate_of IS NULL
```

### 5.3 Run via /simulate

Submit the UPDATE as `script` and all recomputed metric queries as `queries`:
```json
{
  "script": "UPDATE ...",
  "queries": [
    {"sql": "SELECT COUNT(*) as cnt FROM <table> WHERE audit_reason = '<case_id>'"},
    {"sql": "SELECT ROUND(SUM(compute_hours), 2) FROM ... WHERE ..."},
    ...
  ]
}
```

### 5.4 Recompute Metrics After Correction

After applying the correction, recompute metrics with the **same qualification rules** as the original task. The correction only changes specific rows; all filters (production, non-backfill, non-telemetry_v1, account status, segment, etc.) are reapplied.

### 5.5 Affected Accounts

For `usage_product_correction`: group corrected rows by account, count corrected rows and their added compute_hours. Filter to accounts matching the task's segment/status scope (e.g., "enterprise accounts" → only enterprise rows in affected_accounts).

For `ticket_duplicate_correction`: recompute the backlog, then build accounts_to_notify from the post-correction qualified pool.

---

## 6. Incident Exposure Patterns

### 6.1 Read Incident First

Always read the incident record as the **authoritative source** for:
- `started_at` / `resolved_at`: incident window boundaries (timestamp format `YYYY-MM-DD HH:MM:SS`)
- `impacted_region`: which region's accounts are affected
- `severity`: SEV1/SEV2/SEV3

### 6.2 Active Subscription Check

An account has an active subscription during the incident window if:
```sql
SELECT DISTINCT s.account_id
FROM subscriptions s
JOIN accounts a ON s.account_id = a.account_id
WHERE s.product_id = '<INCIDENT_PRODUCT>'
  AND s.subscription_status = 'active'
  AND s.start_date <= '<WINDOW_END_DATE>'
  AND (s.end_date IS NULL OR s.end_date >= '<WINDOW_START_DATE>')
  AND a.is_internal = 0
  AND a.account_status IN ('active', 'paused')
```

### 6.3 Usage Exposure During Incident

Qualified production usage for impacted accounts during the incident window dates:
```sql
WHERE u.product_id = '<PRODUCT>'
  AND u.activity_date >= date('<STARTED_AT>')
  AND u.activity_date <= date('<RESOLVED_AT>')
  AND u.environment = 'production'
  AND u.is_backfill = 0
  AND u.source_system != 'telemetry_v1'
  AND u.account_id IN (<impacted-account-subquery>)
```

### 6.4 Follow-Up Ticket Window

Seven calendar days after resolution, **exclusive** of the resolution timestamp:
- `start_exclusive` = `resolved_at` — same timestamp string
- `end_inclusive` = `resolved_at + 7 days` — add 7 to the day, keep same time

```sql
WHERE t.created_at > '<RESOLVED_AT>'
  AND t.created_at <= datetime('<RESOLVED_AT>', '+7 days')
```

Filter tickets to: external customer accounts in the impacted region, non-canceled, non-duplicate, customer-impacting.

### 6.5 Excluded Counts for Incidents

| Key | Meaning |
|-----|---------|
| usage_candidate_rows | Total usage rows matching product + date range + account scope |
| usage_non_production_rows_excluded | environment != 'production' |
| usage_backfill_rows_excluded | is_backfill = 1 |
| usage_internal_or_inactive_account_rows_excluded | is_internal=1 or account_status not active/paused |
| usage_without_active_subscription_rows_excluded | No active subscription during incident window |
| usage_telemetry_v1_overlap_rows_excluded | source_system = 'telemetry_v1' |
| ticket_candidates_in_followup_window | Total ticket candidates in followup window |
| ticket_canceled_or_duplicate_excluded | status='canceled' or is_duplicate=1 |
| ticket_non_customer_impact_excluded | customer_impact=0 |

Apply exclusions sequentially, each counting from the remaining pool after prior exclusions.

---

## 7. Output Conventions

### 7.1 Rounding

| Metric | Precision | SQL |
|--------|-----------|-----|
| compute_hours | 2 decimal places | `ROUND(value, 2)` |
| sla_breach_rate | 4 decimal places | `ROUND(value, 4)` |
| median_close_hours | 2 decimal places | `ROUND(value, 2)` |
| All counts | integer | `CAST(... AS INTEGER)` |

### 7.2 Deterministic Ordering

| Context | Order |
|---------|-------|
| top_accounts (usage) | `compute_hours DESC, account_id ASC` |
| top_accounts (tickets) | `ticket_count DESC, account_id ASC` |
| regional_breakdown | Alphabetical by region: `APAC, EMEA, LATAM, NA` |
| account_breakdown | `account_id ASC` |
| affected_accounts (correction) | `account_id ASC` |
| accounts_to_notify | `backlog_ticket_count DESC, highest_severity ASC` (P1→P2→P3→P4), `account_id ASC` |
| qualified_ticket_ids | `ticket_id ASC` (string sort) |
| impacted_accounts | `account_id ASC` |
| accounts_with_followup_tickets | `account_id ASC` |

### 7.3 Date Formats

- **Date-only fields**: `YYYY-MM-DD` (e.g., `"2026-01-01"`)
- **Timestamp fields**: `YYYY-MM-DD HH:MM:SS` (e.g., `"2026-05-20 10:57:13"`)
- Always use **inclusive** date ranges (BETWEEN or `>=` / `<=`)

### 7.4 String Values

- Region values: exactly `"NA"`, `"EMEA"`, `"APAC"`, `"LATAM"`, `"GLOBAL"`
- Severity: `"P1"`, `"P2"`, `"P3"`, `"P4"` for tickets; `"SEV1"`, `"SEV2"`, `"SEV3"` for incidents
- Product IDs: exactly as stored (e.g., `"ATLASDB"`, `"HELIOSYNC"`)
- `audit_reason`: exact value from `data_quality_cases.audit_reason`

### 7.5 Zero-Handling

- Include **all severity buckets** (P1–P4) even when count is 0
- Include **all regions** (NA, EMEA, APAC, LATAM) in regional_breakdown even with 0 qualified accounts
- Accounts with 0 qualified rows: omit from account_breakdown unless the task explicitly requires all accounts
- `qualified_account_count` counts only accounts with ≥1 qualified row

---

## 8. Common Pitfalls

1. **Forgetting telemetry_v1 exclusion**: `source_system != 'telemetry_v1'` must be explicitly in WHERE; the `production_usage_daily` view does NOT filter source_system.

2. **Including backfill rows**: Even in `production_usage_daily` view, `is_backfill = 1` rows exist. Always add `AND is_backfill = 0`.

3. **Account status for "active"**: Use `account_status IN ('active', 'paused')` — "paused" accounts are still customers. Exclude "churned" and "test".

4. **Internal accounts**: Check `is_internal = 0`, not `segment != 'internal'` — the `is_internal` flag is the authoritative field.

5. **Subscription overlap math**: Active during window means `start_date <= window_end AND (end_date IS NULL OR end_date >= window_start)`.

6. **Date vs datetime**: `activity_date` is a date string; `created_at`/`closed_at`/`resolved_at`/`started_at` are datetime strings. Use `date()` function to extract date portions from datetimes when comparing against date-only fields.

7. **Duplicate correction scope**: Marking a ticket as duplicate requires setting BOTH `is_duplicate = 1` AND `duplicate_of = '<master_id>'`.

8. **Simulate changed_rows**: The `/simulate` endpoint returns `changed_rows` — this is your authoritative count. Do not recompute it from queries.

9. **Exclusion counts are non-overlapping**: Each exclusion bucket counts rows remaining after prior exclusions. Do not double-count. The base pool is all rows matching product + dates + customer accounts; then apply each filter in order.

10. **SLA breach for open tickets**: Tickets still `open` or `in_progress` past their `sla_due_at` ARE breached — not just resolved-late tickets.

11. **Account ordering tiebreaks**: When ordering by a count/metric descending, ties break on `account_id ASC` (not account_name).

12. **Correction SQL must be idempotent**: Include the old-value guard so re-running doesn't double-apply. Use `datetime('now')` for audit_updated_at rather than a hardcoded timestamp.

13. **Incident followup window is exclusive of resolved_at**: `created_at > resolved_at` (strict greater-than), but `created_at <= resolved_at + 7 days` (inclusive upper bound).
