# Task Group 022 — Shared Operations Analytics API Skill

## Purpose

Execute analytical queries against a multi-tenant operations database exposed through a shared REST API backed by SQLite. This skill covers usage rollups, defect-ticket reporting, incident-exposure analysis, data-quality corrections, and backlog recomputation. Every task begins with API discovery, proceeds through exploratory SQL queries, and ends with a single JSON response matching a supplied template.

---

## 1. Environment & API Bootstrapping

### Base URL

The API root is provided via the `TASK_ENV_BASE_URL` placeholder. **Always resolve it to the value in `environment_access.md`** — currently `http://34.46.77.124:9022`. Never use localhost or any other URL unless the environment file explicitly overrides it.

### Discovery (always step 1)

```
GET {BASE_URL}/
```

The root endpoint returns live API documentation: available routes, query methods, and current database schema (table names, column names, types, and relationships). Use this response as the authoritative catalog — do not hard-code table schemas from memory. The two canonical routes are:

- **`GET /`** — API docs, schema listing, and query instructions.
- **`POST /sql`** — Execute a SQL statement (usually SQLite dialect) against the shared database. The request body is `{"sql": "<statement>"}`. The response is a JSON array of result rows, or a summary object for non-SELECT statements.

### Query workflow

1. Read the docs at `GET /` to confirm table/column names and any API-specific SQL restrictions.
2. Run exploratory `SELECT` queries to inspect columns, value distributions, and row counts.
3. Build the final analytical query as a single CTE-driven statement or a sequence of targeted `SELECT` / aggregation queries.
4. For correction tasks, construct the `UPDATE` statement last — query first to identify target rows, then write the guarded correction SQL.

---

## 2. Core Database Tables & Column Conventions

Tables share these conventions (verify against `GET /` each session):

| Table | Key columns | Notes |
|---|---|---|
| `usage_daily` | `usage_id`, `account_id`, `product_id`, `usage_date`, `compute_hours`, `api_calls`, `region`, `is_production`, `source_system`, `audit_reason`, `audit_updated_at` | One row per account-day-product. `source_system` distinguishes origin (`telemetry-v1`, `telemetry-v2`, `backfill`). |
| `accounts` | `account_id`, `account_name`, `region`, `account_type`, `is_active` | `account_type` values: `enterprise`, `internal`, `test`, `partner`. `is_active` is 0 or 1. |
| `subscriptions` | `subscription_id`, `account_id`, `product_id`, `status`, `tier`, `start_date`, `end_date` | `status`: `active`, `expired`, `canceled`, `suspended`. |
| `tickets` | `ticket_id`, `product_id`, `account_id`, `severity`, `status`, `category`, `created_at`, `resolved_at`, `closed_at`, `is_duplicate`, `duplicate_of`, `sla_deadline`, `is_customer_impact`, `audit_reason`, `audit_updated_at` | `severity`: `P1`/`P2`/`P3`/`P4`. `status`: `open`, `in_progress`, `resolved`, `closed`, `canceled`. |
| `incidents` | `incident_id`, `product_id`, `started_at`, `resolved_at`, `impacted_region`, `severity` | `impacted_region` can be `NA`, `EMEA`, `APAC`, `LATAM`, or `GLOBAL`. `severity`: `SEV1`/`SEV2`/`SEV3`. |
| `data_quality_cases` | `case_id`, `case_type`, `case_status`, `target_table`, `affected_ids`, `new_value`, `audit_reason`, `created_at` | `case_status` must be `approved` before applying. `affected_ids` is often a JSON array string. |

---

## 3. Qualification Filters — Build From Template Requirements

Each task's `answer_template.json` defines what "qualified" means. The most common filter rules across all tasks:

### Usage records (rollup tasks)

- Date range: inclusive `>= start_date AND <= end_date`.
- `is_production = 1` — exclude non-production rows.
- Exclude `source_system = 'telemetry-v1'` rows when the template asks for a telemetry-v1 overlap counter.
- Exclude `source_system = 'backfill'` rows.
- Account must be `account_type = 'enterprise'`, `is_active = 1`.
- Account must have an `active` subscription covering the usage dates (`subscriptions.status = 'active' AND usage_date BETWEEN start_date AND end_date`).
- Track every exclusion as a separate count.

### Ticket records (defect/backlog tasks)

- Creation date range: inclusive `>= start_date AND <= end_date`.
- `category` must be `defect` or match a specified defect-like value.
- `is_customer_impact = 1` — exclude non-customer-impact rows.
- Exclude `is_duplicate = 1` records.
- Exclude `status = 'canceled'`.
- Exclude internal/test accounts via JOIN to `accounts`.
- Track exclusion counts: `duplicate`, `canceled`, `internal_or_test_account`, `non_customer_impact`, `non_defect_category`.

### Follow-up tickets (incident tasks)

- Created strictly AFTER resolution time (`created_at > resolved_at`), up to exactly 7 days later (`created_at <= datetime(resolved_at, '+7 days')`).
- Only external customer accounts in the incident's impacted region.

---

## 4. Ordering Conventions — Deterministic Every Time

| Output array | Primary sort (descending) | Secondary sort (ascending) |
|---|---|---|
| `top_accounts` | `compute_hours` / `ticket_count` / `backlog_ticket_count` | `account_id` |
| `account_breakdown` | (none) | `account_id` |
| `regional_breakdown` | (none) | `region` (alphabetical: APAC, EMEA, LATAM, NA) |
| `qualified_ticket_ids` | (none) | `ticket_id` (string-lexicographic ascending) |
| `affected_accounts` | (none) | `account_id` |
| `impacted_accounts` | `compute_hours` descending (or api_calls as specified) | `account_id` |
| `accounts_with_followup_tickets` | (none) | `account_id` |
| `accounts_to_notify` | `backlog_ticket_count` descending | `highest_severity` (P1→P4), then `account_id` |

---

## 5. Rounding & Precision Rules

| Field(s) | Precision | Rounding |
|---|---|---|
| `compute_hours`, `added_compute_hours` | 2 decimal places | Standard rounding (`ROUND(value, 2)`) |
| `sla_breach_rate` | 4 decimal places | Standard rounding (`ROUND(value, 4)`) |
| `median_close_hours` | 2 decimal places | Compute median first, then round |
| `total_api_calls` | integer (no rounding) | Sum as integer |
| All counts (`qualified_*_count`, `*_rows_excluded`, etc.) | integer | No rounding |

Always apply rounding at the **final output layer**, not in intermediate CTEs. In SQLite, use `ROUND(expr, N)`.

---

## 6. Safe Data-Quality Correction SQL Patterns

When a task requires a `correction_sql` string for an approved data-quality case:

### Always include these guards

1. **Case validation**: Subquery that checks `case_status = 'approved'` in `data_quality_cases`.
2. **Idempotency guard**: The UPDATE must fail safely if already applied (check current column values before mutating).
3. **Product guard**: `AND product_id = '<correct_product>'` to prevent cross-product contamination.
4. **Explicit row list**: Use `IN (...)` with the specific `usage_id` or `ticket_id` values from the approved case.
5. **Audit fields**: Always set `audit_reason` and `audit_updated_at` from the corresponding `data_quality_cases` row.
6. **Type check**: Verify `case_type` matches (e.g., `ticket_duplicate_correction`, `product_reclassification`).

### Pattern for usage reclassification

```sql
UPDATE usage_daily
SET product_id = '<correct_product>',
    audit_reason = (SELECT audit_reason FROM data_quality_cases WHERE case_id = '<case_id>' AND case_status = 'approved'),
    audit_updated_at = (SELECT created_at FROM data_quality_cases WHERE case_id = '<case_id>' AND case_status = 'approved')
WHERE usage_id IN (<affected_ids>)
  AND product_id = '<wrong_product>'
  AND EXISTS (SELECT 1 FROM data_quality_cases WHERE case_id = '<case_id>' AND case_status = 'approved');
```

### Pattern for ticket duplicate marking

```sql
UPDATE tickets
SET is_duplicate = 1,
    duplicate_of = (SELECT new_value FROM data_quality_cases WHERE case_id = '<case_id>' AND case_status = 'approved'),
    audit_reason = (SELECT audit_reason FROM data_quality_cases WHERE case_id = '<case_id>' AND case_status = 'approved'),
    audit_updated_at = (SELECT created_at FROM data_quality_cases WHERE case_id = '<case_id>' AND case_status = 'approved')
WHERE ticket_id IN (<affected_ids>)
  AND product_id = '<product>'
  AND is_duplicate = 0
  AND duplicate_of IS NULL
  AND EXISTS (SELECT 1 FROM data_quality_cases
              WHERE case_id = '<case_id>'
                AND case_status = 'approved'
                AND case_type = 'ticket_duplicate_correction'
                AND target_table = 'tickets');
```

### After correction — recompute

Always recompute the qualified metrics after the fix is simulated/applied. The "after-fix" metrics in the response must reflect what the database would look like **after** the UPDATE runs, not before. Query the target rows that would change, compute the delta, and apply it to the pre-correction baseline.

---

## 7. Exclusion Tracking — Be Exhaustive

Every task that filters rows must report exclusion counts. Build these counts with separate queries or CTE branches, never by subtraction. Common exclusion dimensions:

### Usage exclusions

- `usage_candidate_rows` — raw rows in the date range for the product (before any filter).
- `usage_non_production_rows_excluded` — `is_production = 0`.
- `usage_backfill_rows_excluded` — `source_system = 'backfill'`.
- `usage_internal_or_inactive_account_rows_excluded` — non-enterprise account type or inactive account.
- `usage_without_active_subscription_rows_excluded` — no active subscription covering the date.
- `usage_telemetry_v1_overlap_rows_excluded` — `source_system = 'telemetry-v1'`.

### Ticket exclusions

- `duplicate` — `is_duplicate = 1`.
- `canceled` — `status = 'canceled'`.
- `internal_or_test_account` — account type is internal or test.
- `non_customer_impact` — `is_customer_impact = 0`.
- `non_defect_category` — `category != 'defect'`.

Always verify that the sum of all exclusions PLUS qualified rows equals the candidate row count.

---

## 8. Metric Computation Patterns

### SLA Breach Rate

```
sla_breach_rate = count_of_qualified_tickets_breached / count_of_qualified_tickets
```

A ticket is breached when `resolved_at > sla_deadline` or (if unresolved) `current_time > sla_deadline`. Compute for qualified non-duplicate, non-canceled tickets only. Round to 4 decimal places.

### Median Close Hours

Compute the median of `close_duration_hours = (closed_at - created_at) * 24` for closed qualified tickets only (`status = 'closed'`). In SQLite, which lacks `PERCENTILE_CONT`, use either:
- Row-number-based median: sort by duration, pick the middle value (or average of two middle values for even counts).
- Compute after fetching rows into application code and sorting.

Round to 2 decimal places after computing the median.

### Backlog

A ticket is in backlog if its `status` is `open` or `in_progress` and it is qualified (not duplicate, not canceled, customer-impacting, defect, non-internal account) within the period.

---

## 9. Incident Analysis Workflow

1. **Fetch the incident**: `SELECT * FROM incidents WHERE incident_id = '<id>'`.
2. **Set windows**:
   - Incident window: `[started_at, resolved_at]` — these are the authoritative timestamps from the database.
   - Follow-up window: `(resolved_at, resolved_at + 7 days]` — exclusive start, inclusive end.
3. **Impacted accounts**: Usage records in the incident window for the incident's product, filtered to active subscriptions and the impacted region (or all regions if `GLOBAL`).
4. **Follow-up tickets**: Tickets created in the follow-up window for external customer accounts in the impacted region.
5. **Highest-usage account**: The single impacted account with the most `compute_hours` (ties broken by ascending `account_id`).
6. **Severity mix**: Aggregate severity counts for follow-up tickets across P1-P4 (all four keys must be present, zero-valued included).

---

## 10. Common Pitfalls & Checklist

### Before submitting the answer

| Pitfall | How to avoid |
|---|---|
| **Missing `WHERE` guard on correction SQL** | Always include `AND product_id = 'X'` and idempotency conditions. |
| **Exclusion count mismatch** | Verify `candidate = qualified + sum(all_exclusions)` for every count block. |
| **Using localhost** | Always resolve `<TASK_ENV_BASE_URL>` from `environment_access.md`. |
| **Date inclusivity errors** | Use `>= start AND <= end` for inclusive ranges. Use `>` for exclusive start boundaries. |
| **Wrong ordering** | Check the template's `ordering` annotation; apply primary-desc, secondary-asc consistently. |
| **Rounding too early** | Compute sums/medians with full precision, round only at the final output layer. |
| **Missing zero-valued keys** | `backlog_by_severity` and `severity_mix` must always include all four keys (`P1`-`P4`) even when the count is 0. |
| **Ticket ID ordering** | Sort lexicographically as strings (e.g., `TKT-000025` before `TKT-000028`), not numerically. |
| **Forgotten audit fields** | Every correction UPDATE must set `audit_reason` and `audit_updated_at`. |
| **Stale API docs assumption** | Always `GET /` first — schemas may differ between task groups or sessions. |
| **`affected_ids` parsing** | `data_quality_cases.affected_ids` is often a JSON array string. Parse it to extract the row identifiers before building the IN clause. |
| **Telemetry-v1 double-counting** | When `source_system = 'telemetry-v1'` rows exist for the same account-day-product as `telemetry-v2` rows, exclude the v1 rows from qualified usage and report them in `telemetry_v1_rows_excluded`. |

---

## 11. Response Assembly Checklist

1. Read `answer_template.json` to understand every required key and its type.
2. Query `GET /` for live schema and API instructions.
3. Fetch the authoritative source records first (incident row, data-quality case row, etc.).
4. Build the qualified result set with all filters applied.
5. Compute rollups, rankings, and aggregations.
6. If a correction is required, write the guarded SQL first, then compute "after-fix" metrics by simulating the correction's effect (delta method or post-apply query).
7. Count every exclusion dimension independently.
8. Apply ordering, rounding, and precision rules at the final step.
9. Validate that every key in the template is present in the output and every type matches.
10. Return a single JSON object — no markdown wrapping, no commentary.
