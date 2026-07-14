# Operations Analytics Skill — task_group_022 / self

Executable workflow guidance for the shared operations analytics API. Covers usage rollups, defect rollups, incident exposure reports, data-quality corrections, and backlog recomputation.

---

## 1. API Endpoints and Workflow

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | List all endpoints |
| GET | `/health` | Service status check |
| GET | `/schema` | Full table/view DDL with columns, types, constraints, and CHECK clauses |
| GET | `/tables` | Table and view names only |
| GET | `/tables/<name>?limit=100&offset=0` | Sample rows from one table or view |
| POST | `/query` | Read-only SQL. Body: `{"sql": "<SQL>", "params": []}` |
| POST | `/simulate` | Run an UPDATE script on a temporary DB copy, then run read-only queries. Body: `{"script": "<UPDATE SQL>", "queries": [{"sql": "...", "params": []}]}`. Returns `changed_rows` and per-query results. |

### Workflow Checklist for Every Task

1. **Read `/schema`** — understand CHECK constraints, enums, primary keys, foreign keys, and view definitions.
2. **Read `metric_notes`** — these define domain rules (defect categories, backfill meaning, telemetry overlap, audit-field conventions, etc.).
3. **Discover filter values** — query `SELECT DISTINCT` on categorical columns to learn the actual domain values.
4. **Query in stages** — start broad, add filters incrementally, verify intermediate row counts.
5. **For corrections** — query the `data_quality_cases` table; only apply rows with `case_status = 'approved'`.

---

## 2. Database Schema Reference

### Core Tables

**accounts** — `account_id` (PK), `account_name`, `segment` (enterprise | commercial | startup | internal), `region` (NA | EMEA | APAC | LATAM), `account_status` (active | paused | churned | test), `is_internal` (0 | 1), `owner_team`, `created_at`

**products** — `product_id` (PK: ATLASDB | HELIOSYNC | NEXAQUEUE | LUMAFORMS), `product_name`, `product_family`, `is_active`

**subscriptions** — `subscription_id` (PK), `account_id` (FK→accounts), `product_id` (FK→products), `plan_code` (enterprise | growth | standard | trial | internal), `subscription_status` (active | paused | ended | trial), `start_date`, `end_date` (nullable)

**usage_daily** — `usage_id` (PK), `account_id`, `product_id`, `activity_date`, `environment` (production | staging | sandbox | internal), `source_system` (telemetry_v1 | telemetry_v2 | import_patch), `seats_active`, `api_calls`, `compute_hours` (REAL), `data_gb`, `is_backfill` (0 | 1), `recorded_at`, `audit_reason` (nullable), `audit_updated_at` (nullable)

**tickets** — `ticket_id` (PK), `account_id`, `product_id`, `created_at`, `closed_at` (nullable), `status` (open | in_progress | resolved | canceled), `severity` (P1 | P2 | P3 | P4), `category` (bug | outage | performance | data_loss | how_to | billing | feature_request | internal_test), `customer_impact` (0 | 1), `is_duplicate` (0 | 1), `duplicate_of` (nullable FK→tickets), `linked_incident_id` (nullable FK→incidents), `sla_due_at`, `audit_reason` (nullable), `audit_updated_at` (nullable)

**incidents** — `incident_id` (PK), `product_id`, `started_at`, `resolved_at`, `severity` (SEV1 | SEV2 | SEV3), `impacted_region` (NA | EMEA | APAC | LATAM | GLOBAL), `public_status` (resolved | monitoring | closed)

**data_quality_cases** — `case_id` (PK), `case_type` (usage_product_correction | ticket_duplicate_correction), `case_status` (approved | draft | rejected), `target_table`, `target_ids_csv`, `field_name`, `old_value` (nullable), `new_value`, `approval_code`, `audit_reason`, `created_at`

**metric_notes** — `note_id` (PK), `topic`, `note_text`, `updated_at`. Read these FIRST — they encode domain rules not visible in schema.

### Views

**active_customer_accounts** — `accounts WHERE is_internal = 0 AND account_status IN ('active', 'paused')`. Excludes churned and test accounts.

**customer_support_tickets** — `tickets WHERE category <> 'internal_test'`. Does NOT filter is_duplicate, canceled, or non-defect categories.

**production_usage_daily** — `usage_daily WHERE environment = 'production'`. Does NOT filter backfill or telemetry_v1.

---

## 3. Qualified Usage Filters (Universal)

When a task asks for "qualified usage," apply ALL of these unless the task explicitly overrides one:

```
1. product_id = <target product>
2. activity_date BETWEEN '<start>' AND '<end>'        -- inclusive on both ends
3. environment = 'production'
4. is_backfill = 0
5. source_system != 'telemetry_v1'                     -- exclude v1 overlap
6. Account is_internal = 0                             -- no internal/test accounts
7. Account segment filter (e.g., segment = 'enterprise' if task says "enterprise accounts")
8. Account region filter (e.g., region = 'EMEA' if task says "EMEA")
9. Active subscription for the product during the period (if task says "with active subscriptions"):
   - subscription_status = 'active'
   - plan_code filter if specified (e.g., plan_code = 'enterprise')
   - Subscription window covers the usage date (start_date <= activity_date AND (end_date IS NULL OR end_date >= activity_date))
```

### Telemetry v1 Exclusion Rule

Metric note NOTE-010: "Telemetry v1, telemetry v2, and import patch records may overlap during migration periods." Always exclude `source_system = 'telemetry_v1'` rows from qualified metrics. Count them separately when the answer template asks for `telemetry_v1_rows_excluded` — count all telemetry_v1 rows in the candidate scope (same product/date/region/segment filters, but BEFORE the subscription filter).

### Backfill Exclusion Rule

Metric note NOTE-003: "Backfill rows are late-arriving records loaded after normal telemetry processing." Always exclude `is_backfill = 1` from qualified metrics.

---

## 4. Qualified Ticket / Defect Filters (Universal)

When a task asks for "customer-impacting defect" tickets, apply ALL of these:

```
1. product_id = <target product>
2. created_at BETWEEN '<start>' AND '<end>'              -- inclusive
3. category IN ('bug', 'outage', 'performance', 'data_loss')  -- defect categories per NOTE-004
4. customer_impact = 1
5. is_duplicate = 0
6. status != 'canceled'
7. Account is_internal = 0                                -- no internal/test accounts
```

### Exclusion Categories (for exclusion breakdowns)

When the answer template asks for `excluded_counts`, count independently (a ticket can match multiple exclusion reasons):

| Exclusion Key | Condition |
|--------------|-----------|
| `duplicate` | `is_duplicate = 1` |
| `canceled` | `status = 'canceled'` |
| `internal_or_test_account` | Account `is_internal = 1` OR `account_status = 'test'` |
| `non_customer_impact` | `customer_impact = 0` (among defect-category tickets only) |
| `non_defect_category` | `category NOT IN ('bug','outage','performance','data_loss')` |

**Important**: For qualification, these are AND-ed (all must pass). For exclusion counting, count each independently from the candidate pool — overlapping exclusions are expected and normal.

### Backlog Definition

"Backlog" tickets are qualified (customer-impacting defect) tickets whose `status IN ('open', 'in_progress')`. Backlog excludes resolved and canceled tickets.

---

## 5. Data Quality Correction Patterns

### General Rules

1. Only apply cases where `case_status = 'approved'`. Ignore `draft` and `rejected`.
2. Use the `/simulate` endpoint to test the UPDATE on a copy before finalizing.
3. Always populate BOTH `audit_reason` and `audit_updated_at` in the UPDATE.
4. The `changed_row_count` is the number of rows actually modified (as returned by `/simulate`).
5. Recomputed metrics after correction use the SAME qualification filters as the original task, applied to the corrected data.

### Usage Product Correction SQL Template

```sql
UPDATE usage_daily
SET product_id = '<new_value>',
    audit_reason = '<case.audit_reason>',
    audit_updated_at = datetime('now')
WHERE usage_id IN (<comma-separated target_ids from target_ids_csv>)
```

Parse `target_ids_csv` from the DQ case row and use each ID as a quoted string in the IN clause. Do NOT use subqueries or dynamic splitting — hardcode the IDs.

### Ticket Duplicate Correction SQL Template

```sql
UPDATE tickets
SET is_duplicate = 1,
    duplicate_of = '<new_value>',
    audit_reason = '<case.audit_reason>',
    audit_updated_at = datetime('now')
WHERE ticket_id IN (<comma-separated target_ids from target_ids_csv>)
```

The `new_value` from the DQ case is the master ticket ID. All target tickets become duplicates of that master.

### After Correction: Recomputing Metrics

1. Run the UPDATE via `/simulate`.
2. In the same `/simulate` call, include read queries to recompute:
   - Qualified row counts (with all standard filters applied)
   - Aggregated compute hours (ROUND to 2 decimals)
   - Affected account breakdowns (only accounts whose corrected rows now pass qualification)
   - Top account rankings (DESC compute_hours, ASC account_id for ties)

---

## 6. Output-Field Conventions

### Ordering Rules

| Output Section | Sort Order |
|---------------|------------|
| `top_accounts` | DESC by primary metric (compute_hours or ticket_count), then ASC `account_id` for ties |
| `regional_breakdown` | Alphabetical by region: APAC, EMEA, LATAM, NA |
| `account_breakdown` | ASC `account_id` |
| `qualified_ticket_ids` | ASC string sort (`ticket_id`) |
| `affected_accounts` | ASC `account_id` |
| `accounts_with_followup_tickets` | ASC `account_id` |
| `accounts_to_notify` | DESC `backlog_ticket_count`, then ASC severity priority (P1→P2→P3→P4), then ASC `account_id` |
| `backlog_by_severity` | Keys: P1, P2, P3, P4 (always all four, with zeros for unused severities) |
| `severity_mix` | Keys: P1, P2, P3, P4 (always all four, with zeros) |

### Rounding Rules

| Field | Precision | SQL |
|-------|-----------|-----|
| `compute_hours` | 2 decimal places | `ROUND(SUM(compute_hours), 2)` |
| `added_compute_hours` | 2 decimal places | `ROUND(SUM(compute_hours), 2)` |
| `sla_breach_rate` | 4 decimal places | `ROUND(breached::REAL / total, 4)` |
| `median_close_hours` | 2 decimal places | Compute median in application code, `ROUND(result, 2)` |

### Always-Include / Never-Skip Rules

- **Regional breakdown**: Always include all 4 regions (APAC, EMEA, LATAM, NA) even if some have 0 counts/rows/hours.
- **Severity keys**: Always include P1, P2, P3, P4 even if some counts are 0.
- **Zero-valued accounts**: Accounts with 0 qualified usage rows or 0 qualified tickets should NOT appear in account-level breakdowns.
- **Top-N lists**: Only include accounts that actually have data. If fewer than N accounts qualify, return all of them.

---

## 7. Incident Exposure Patterns

### Incident Window

Query the `incidents` table for the specified `incident_id`. Use the DB row as the authoritative source for:
- `started_at` / `resolved_at` timestamps
- `impacted_region`
- `severity`

### Qualified Production Usage During Incident

Filter usage to:
1. `product_id = incident.product_id`
2. `activity_date` between `DATE(started_at)` and `DATE(resolved_at)` inclusive
3. `environment = 'production'`
4. Accounts in the `impacted_region` (or all regions if GLOBAL)
5. Accounts with `is_internal = 0`
6. Accounts with an **active** subscription for the product during the incident (subscription_status = 'active', and subscription window covers the incident date)
7. `is_backfill = 0`
8. `source_system != 'telemetry_v1'`

### Post-Incident Follow-Up Ticket Window

- **start_exclusive**: `incident.resolved_at` (tickets created AFTER resolution)
- **end_inclusive**: `incident.resolved_at + 7 days` (tickets created on or before this)

Filter follow-up tickets to:
1. `product_id = incident.product_id`
2. `created_at > resolved_at AND created_at <= resolved_at_plus_7d`
3. Accounts in the `impacted_region`
4. Accounts with `is_internal = 0` (external customer accounts only)
5. Exclude tickets with `status = 'canceled'` OR `is_duplicate = 1`

### Exclusion Counts for Incident Reports

Count independently from the candidate pool (before applying all qualification filters):

| Key | What It Counts |
|-----|---------------|
| `usage_candidate_rows` | All usage rows matching product + date range + region (before ANY filter) |
| `usage_non_production_rows_excluded` | `environment != 'production'` |
| `usage_backfill_rows_excluded` | `is_backfill = 1` |
| `usage_internal_or_inactive_account_rows_excluded` | Account `is_internal = 1` OR `account_status = 'test'` |
| `usage_without_active_subscription_rows_excluded` | No active subscription covering the date |
| `usage_telemetry_v1_overlap_rows_excluded` | `source_system = 'telemetry_v1'` (production rows only) |
| `ticket_candidates_in_followup_window` | All tickets in the follow-up date range for product + region |
| `ticket_canceled_or_duplicate_excluded` | `status = 'canceled'` OR `is_duplicate = 1` |
| `ticket_non_customer_impact_excluded` | `customer_impact = 0` in the follow-up window |

---

## 8. SLA Breach and Median Close Calculations

### SLA Breach Rate

An SLA breach occurs when a qualified ticket's resolution/closure exceeds its SLA deadline:
- For resolved tickets: `closed_at > sla_due_at`
- For open/in_progress tickets: treat current timestamp as the close time (or determine from task context)
- `sla_breach_rate = breached_count / total_qualified_count`
- Always round to 4 decimal places

### Median Close Hours

1. Consider only **closed** qualified tickets (status = 'resolved').
2. Compute close duration in hours: `(julianday(closed_at) - julianday(created_at)) * 24`
3. Take the **median** of these durations (not average).
4. Round to 2 decimal places.

For SQLite, compute close hours per ticket with a subquery, order them, and pick the middle value(s):
```sql
WITH close_hours AS (
  SELECT (julianday(closed_at) - julianday(created_at)) * 24 AS hours
  FROM tickets ...
  WHERE status = 'resolved' ...
  ORDER BY hours
)
SELECT AVG(hours) FROM (
  SELECT hours FROM close_hours
  LIMIT 2 - (SELECT COUNT(*) FROM close_hours) % 2
  OFFSET (SELECT (COUNT(*) - 1) / 2 FROM close_hours)
)
```

---

## 9. Correction Habits and Simulation Flow

### Correction Workflow (Step by Step)

1. **Read the DQ case**: `SELECT * FROM data_quality_cases WHERE case_id = '<id>'`
2. **Verify**: `case_status = 'approved'` — abort if not.
3. **Construct the UPDATE**: Follow the templates in Section 5. Hardcode target IDs from `target_ids_csv`. Use the `audit_reason` from the case.
4. **Plan the recompute queries**: What metrics need recalculation after the fix? Prepare read queries.
5. **Call `/simulate`**: Send the UPDATE script and all recompute queries in one call.
6. **Read results**: `changed_rows` gives the correction count. Query results give recomputed metrics.
7. **Assemble the response**: Combine correction metadata + recomputed metrics.

### Safety Rules for Correction SQL

- Always include `WHERE usage_id IN (...)` or `WHERE ticket_id IN (...)` — never a broad UPDATE.
- Only update the specific field from the DQ case (`field_name`).
- Always set both `audit_reason` and `audit_updated_at`.
- Do NOT update rows that already have the correct value (if applicable — though the `old_value` in the case may be NULL or empty, check before adding a redundant guard).
- Use literal IDs in the IN clause; do not use subqueries, JOINs in UPDATE, or dynamic SQL.

---

## 10. Common Pitfalls and Remedies

### Pitfall 1: Confusing "Enterprise" Meanings
"Enterprise" can mean `accounts.segment = 'enterprise'` OR `subscriptions.plan_code = 'enterprise'`. Most tasks that say "enterprise accounts" mean BOTH: the account must have segment = 'enterprise' AND an active enterprise-plan subscription for the product. Always JOIN accounts + subscriptions and filter both.

### Pitfall 2: Forgetting the Telemetry v1 Exclusion
Every "qualified usage" query MUST exclude `source_system = 'telemetry_v1'`. This is the single most common omission. Count these rows separately when asked.

### Pitfall 3: Including Backfill Rows
Late-arriving backfill rows (`is_backfill = 1`) inflate metrics. Always exclude them from qualified usage.

### Pitfall 4: Using Views Without Understanding Their Filters
`production_usage_daily` only filters by environment. It does NOT filter backfill, telemetry_v1, or account quality. `customer_support_tickets` only filters internal_test category. Never assume a view applies all needed filters — always layer additional WHERE clauses.

### Pitfall 5: Wrong Date Boundaries
All date ranges are **inclusive** on both ends (`BETWEEN`), UNLESS:
- Incident follow-up window: `start_exclusive` = after resolution (`>`), `end_inclusive` = resolution + 7 days (`<=`)
- The task explicitly says "exclusive" for a boundary.

### Pitfall 6: Including Canceled or Duplicate Tickets in Defect Metrics
Canceled tickets and duplicate tickets (`is_duplicate = 1`) are NOT qualified defects even if they have defect categories and customer_impact = 1. Always filter them out.

### Pitfall 7: Missing Churned Accounts
The `active_customer_accounts` view excludes churned accounts (`account_status NOT IN ('active', 'paused')`). If a task uses this view explicitly, churned accounts are excluded. If a task says "customer accounts" without referencing the view, churned accounts may still count. CHECK the task wording.

### Pitfall 8: Overlapping Exclusion Counts
When computing `excluded_counts`, count each exclusion condition independently from the full candidate pool. Do NOT pipeline them (mutually exclusive) unless the answer template implies a sequential pipeline. The sum of exclusion counts will typically exceed the total row count due to overlap — this is expected.

### Pitfall 9: Using Wrong Timestamp Formats
- `activity_date`: DATE only (`YYYY-MM-DD`), no time component.
- `created_at`, `closed_at`, `started_at`, `resolved_at`: DATETIME (`YYYY-MM-DD HH:MM:SS`).
- When joining on dates between usage and incidents, use `DATE(incident_timestamp)` to match `activity_date`.

### Pitfall 10: Subscription Window Gaps
A subscription with `start_date = '2026-01-01'` and `end_date = '2026-02-01'` does NOT cover usage on 2026-03-15. When filtering by active subscriptions for a date range, ensure the subscription window overlaps the usage date: `start_date <= activity_date AND (end_date IS NULL OR end_date >= activity_date)`.

### Pitfall 11: Forgetting the "zero rows" Rule for Severity/Region Outputs
`backlog_by_severity`, `severity_mix`, and `regional_breakdown` must always include all keys/regions, even with zero counts. Do not omit P4 just because no P4 tickets exist.

### Pitfall 12: Incorrect Top-N Tiebreaking
When two accounts have the same compute_hours in a top-N ranking, the tiebreaker is ASC `account_id`. When sorting `accounts_to_notify`, the cascade is: DESC backlog_ticket_count → ASC severity priority (P1 first, P4 last) → ASC account_id.

### Pitfall 13: Rounding Before Aggregation
Always ROUND the final aggregated value, not intermediate values. Compute `ROUND(SUM(compute_hours), 2)`, not `SUM(ROUND(compute_hours, 2))`.

### Pitfall 14: Not Reading metric_notes First
The `metric_notes` table encodes domain definitions not expressed in schema constraints. Always read it before starting any task. Key topics: "defect", "duplicate tickets", "customer impact", "internal accounts", "backfill", "source systems".

---

## 11. Task-Type Quick Reference

### Usage Rollup (train_001 pattern)
**Filters**: Product + date range + segment + region + production + not backfill + not telemetry_v1 + active enterprise subscription.
**Outputs**: Qualified account count, total compute hours, top accounts ranked, regional breakdown (all 4 regions), account breakdown, telemetry_v1 excluded count.

### Defect Rollup (train_002 pattern)
**Filters**: Product + date range + defect categories + customer_impact=1 + not duplicate + not canceled + not internal account.
**Outputs**: Qualified ticket count, ticket IDs sorted, P1/P2 open count, SLA breach rate (4dp), top 5 accounts, exclusion breakdown, median close hours (2dp).

### Usage Correction (train_003 pattern)
**Workflow**: Read DQ case → verify approved → build UPDATE SQL → call /simulate with recompute queries → assemble response.
**Outputs**: correction_sql string, changed_row_count, recomputed total (2dp), affected accounts (enterprise only, ASC account_id), top account after fix, audit_reason.

### Incident Exposure (train_004 pattern)
**Workflow**: Read incident row → determine window → find qualified usage in window → find follow-up tickets in post-resolution window.
**Outputs**: Incident metadata, usage exposure counts, impacted accounts list, follow-up ticket accounts, highest-usage account, severity mix, detailed exclusion counts.

### Backlog Correction (train_005 pattern)
**Workflow**: Read DQ case → build UPDATE for tickets → call /simulate → recompute backlog metrics.
**Outputs**: correction_sql, changed_ticket_count, qualified count after fix, backlog_by_severity (all P1-P4), SLA breach rate after fix (4dp), accounts_to_notify (sorted by DESC backlog count → ASC severity priority → ASC account_id).

---

## 12. /simulate Endpoint Reference

### Request Shape
```json
{
  "script": "<SQL UPDATE statement(s)>",
  "queries": [
    {"sql": "<SELECT query 1>", "params": []},
    {"sql": "<SELECT query 2>", "params": []}
  ]
}
```

### Response Shape
```json
{
  "changed_rows": <integer>,
  "results": {
    "query_1": { "columns": [...], "row_count": <n>, "rows": [...] },
    "query_2": { "columns": [...], "row_count": <n>, "rows": [...] }
  }
}
```

- `changed_rows` counts rows modified by the script.
- Queries run AFTER the script on the modified copy.
- The original database is never affected.
- All recompute queries needed for the answer should be included in the same `/simulate` call.
