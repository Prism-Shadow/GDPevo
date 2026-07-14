# Task Group 022 — Shared Operations Analytics API (Few-Shot)

## Overview

This skill covers querying a shared operations analytics API backed by a SQLite database to produce structured JSON reports. The API base URL is provided via the task prompt as `<TASK_ENV_BASE_URL>`. Always resolve this to the value in environment_access.md before making any requests. The task types are:

- **Usage rollups** — qualified compute-hour aggregations by product, region, and account for a date range.
- **Defect ticket rollups** — customer-impacting defect tickets with SLA breach rates, severity breakdowns, and exclusion tallies.
- **Data corrections** — apply an approved data-quality case (usage reclassification or ticket duplicate correction) via safe SQL, then recompute the affected metrics.
- **Incident exposure summaries** — production usage during an incident window plus post-resolution followup tickets.

---

## API Interaction Rules

1. **First call: GET the API root.** The root endpoint returns query instructions and available endpoints. Do not assume endpoints — read them from the root response.
2. **Query the database through the API.** The API exposes a `/query` or `/sql` endpoint (discover the exact path from the root). POST plain SQL as the request body or as a `{"sql": "..."}` JSON object — follow the format the root endpoint describes.
3. **Use read-only queries for data extraction.** Only use INSERT/UPDATE/DELETE for correction tasks where the prompt explicitly asks for a safe correction SQL to be executed. Even then, verify the data-quality case is `approved` before writing.
4. **SQLite dialect.** The backend is SQLite. Use SQLite-compatible date functions (`date()`, `datetime()`, `strftime()`), string concatenation (`||`), and no window functions unless you have confirmed they work. Prefer subqueries and JOINs over CTEs if either would work.
5. **No local databases.** Always query through the API. Never create local SQLite files.

---

## Output Field Conventions

### Dates and Timestamps
| Field type | Format | Example |
|---|---|---|
| Date-only | `YYYY-MM-DD` | `"2026-01-01"` |
| Datetime | `YYYY-MM-DD HH:MM:SS` | `"2026-05-20 10:57:13"` |
| Period start/end dates | `YYYY-MM-DD` | Inclusive on both ends |

### Numeric Precision
| Metric | Decimal places | Example |
|---|---|---|
| Compute hours | **2** | `17063.68` |
| SLA breach rate | **4** | `0.7273` |
| Median close hours | **2** | `115.71` |
| Added compute hours (corrections) | **2** | `193.99` |
| API call counts, row counts, ticket counts | **0 (integer)** | `41960` |

### ID and Enum Formats
| Field | Format / Pattern |
|---|---|
| `account_id` | `ACCT-NNNN` (4-digit zero-padded) |
| `ticket_id` | `TKT-NNNNNN` (6-digit zero-padded) |
| `usage_id` | Alphanumeric, e.g. `USG-DQ-APR-NNN` |
| `region` | One of `NA`, `EMEA`, `APAC`, `LATAM` |
| `incident_severity` | `SEV1`, `SEV2`, `SEV3` |
| Ticket severity | `P1`, `P2`, `P3`, `P4` |
| `product_id` | Uppercase short code, e.g. `ATLASDB`, `HELIOSYNC` |

---

## Data Filters (Qualification Rules)

Apply these filters **in order** when computing qualified metrics. Track exclusion counts at each step for transparency.

### Usage Record Qualification
1. **Date range:** `usage_date BETWEEN start AND end` (inclusive).
2. **Product:** `product_id = '<TARGET>'`.
3. **Account tier:** Enterprise accounts only — join to `accounts` and filter `account_tier = 'enterprise'` or equivalent. Exclude `internal` and `test` accounts.
4. **Production only:** Exclude rows where `environment`/`usage_type` indicates non-production (e.g., `'sandbox'`, `'dev'`, `'test'`).
5. **Active subscription:** The account must have an `active` subscription covering the usage date. Join to `subscriptions` (or equivalent) and check `status = 'active'` with `start_date <= usage_date AND end_date >= usage_date`.
6. **Exclude backfill:** Filter out `is_backfill = 1` or rows with a `backfill` flag.
7. **Exclude telemetry_v1 overlaps:** When the task asks for `telemetry_v1_rows_excluded`, count and exclude rows where `source` or `telemetry_source` indicates telemetry v1 ingestion.

### Ticket Record Qualification
1. **Date range:** `created_at BETWEEN start AND end` (inclusive).
2. **Product:** `product_id = '<TARGET>'`.
3. **Customer-impacting:** `customer_impact = 1` or `impact_level = 'customer'`.
4. **Defect category:** The ticket category/type must be `'defect'` or `'bug'`.
5. **Not cancelled:** `status != 'cancelled'`.
6. **Not a duplicate:** `is_duplicate = 0` or `duplicate_of IS NULL`.
7. **External accounts only:** Exclude internal/test accounts (join `accounts` and filter).

### Incident Usage Qualification
1. **Incident window:** Query the `incidents` table for the incident record. Use its `started_at`/`resolved_at` and `impacted_region` as the authoritative window.
2. **Production usage** during the window for accounts in the impacted region (or all regions if `GLOBAL`).
3. **Active AtlasDB subscriptions** during the incident dates.
4. **Exclude:** non-production rows, backfill rows, internal/inactive accounts, telemetry_v1 overlaps.

### Followup Ticket Window (Post-Incident)
- Window: `(resolved_at, resolved_at + 7 days]` — start is **exclusive**, end is **inclusive**.
- Tickets `created_at` in that window for **external** customer accounts in the **impacted region**.
- Exclude cancelled and duplicate tickets.
- Exclude non-customer-impact tickets.

---

## Deterministic Ordering

| Array | Sort key | Direction |
|---|---|---|
| `top_accounts` (usage) | `compute_hours` DESC, then `account_id` ASC | — |
| `top_accounts` (tickets) | `ticket_count` DESC, then `account_id` ASC | — |
| `regional_breakdown` | `region` alphabetically | ASC |
| `account_breakdown` | `account_id` | ASC |
| `qualified_ticket_ids` | Ticket ID string | ASC |
| `impacted_accounts` | `account_id` | ASC |
| `accounts_with_followup_tickets` | `account_id` | ASC |
| `accounts_to_notify` | `backlog_ticket_count` DESC, `highest_severity` priority (P1 first), `account_id` ASC | — |
| `affected_accounts` (corrections) | `account_id` | ASC |
| `severity_counts` / `severity_mix` / `backlog_by_severity` | Always include all four keys `P1`, `P2`, `P3`, `P4` with zero for absent severities | — |

---

## Correction SQL Habits

When the task asks for a `correction_sql` string, follow these rules:

### Structure
- Write a **single safe UPDATE** statement (or a script of guarded UPDATEs if multiple targets).
- Always include guard conditions that verify the **pre-correction state** before mutating.
- Use `IN (...)` for the specific IDs to change — never use broad predicates that could sweep in unintended rows.

### Audit Trail
Every correction must write these audit columns:
- `audit_reason` — the approved case ID string, e.g. `'approved correction DQ-USG-2026-04-A'`
- `audit_updated_at` — a fixed timestamp from the data-quality case's `created_at`, e.g. `'2026-04-23 10:15:00'`

### Guard Pattern for Usage Reclassification
```sql
UPDATE usage_daily
SET product_id = '<CORRECT_PRODUCT>',
    audit_reason = '<CASE_ID>',
    audit_updated_at = '<CASE_CREATED_AT>'
WHERE usage_id IN ('<id1>', '<id2>', ...)
  AND product_id = '<WRONG_PRODUCT>';
```
- The `AND product_id = '<WRONG_PRODUCT>'` guard ensures you only change rows that still have the wrong classification.
- The `IN` list must include every row the approved case covers — derive this from querying `data_quality_cases` joined to the relevant detail table, or from the case's own payload.

### Guard Pattern for Ticket Duplicate Correction
```sql
UPDATE tickets
SET is_duplicate = 1,
    duplicate_of = (SELECT new_value FROM data_quality_cases WHERE case_id = '<CASE_ID>' AND case_status = 'approved'),
    audit_reason = (SELECT audit_reason FROM data_quality_cases WHERE case_id = '<CASE_ID>' AND case_status = 'approved'),
    audit_updated_at = (SELECT created_at FROM data_quality_cases WHERE case_id = '<CASE_ID>' AND case_status = 'approved')
WHERE ticket_id IN ('<id1>', '<id2>', ...)
  AND product_id = '<PRODUCT>'
  AND is_duplicate = 0
  AND duplicate_of IS NULL
  AND EXISTS (
    SELECT 1 FROM data_quality_cases
    WHERE case_id = '<CASE_ID>'
      AND case_status = 'approved'
      AND case_type = 'ticket_duplicate_correction'
      AND target_table = 'tickets'
  );
```
Key guards:
- `is_duplicate = 0` — don't double-mark.
- `duplicate_of IS NULL` — don't overwrite an existing link.
- `product_id` matches — don't touch wrong-product tickets.
- `EXISTS` subquery verifies the case is still approved with the right type.

### After Correction
- Report `changed_row_count` / `changed_ticket_count` — the number of rows the UPDATE actually matched (not the IN-list length).
- Recompute all qualified metrics **as if the correction had already been applied**. This means: exclude the corrected rows from pre-correction qualification, include them under their corrected classification, and recompute aggregates, top accounts, and breakdowns.

---

## SLA Breach Rate

```
sla_breach_rate = count(qualified tickets WHERE sla_breach = 1) / count(all qualified tickets)
```
- Round to **4 decimal places**.
- If there are zero qualified tickets, the rate is `0.0` (not undefined).

---

## Median Close Hours

- Only consider **closed** qualified tickets (status `'closed'` or `'resolved'`).
- Compute `close_hours = (resolved_at - created_at)` in hours as a decimal.
- Take the **median** of the per-ticket close-hour values:
  - If odd count N: the value at position `(N+1)/2` after sorting ascending.
  - If even count N: the average of the two middle values at positions `N/2` and `N/2 + 1`.
- Round to **2 decimal places**.

---

## Top Accounts Logic

- **Usage tasks:** Top accounts = all qualified accounts (not just top-N), ordered by `compute_hours` DESC then `account_id` ASC. Include every account that has at least one qualified usage row.
- **Ticket tasks:** Top 5 accounts by `ticket_count` DESC then `account_id` ASC. If fewer than 5 accounts qualify, include all of them.
- **Top account after fix (corrections):** The single highest-compute qualified account after the correction. Break ties with `account_id` ASC.

---

## Exclusion Counts Pattern

For every task type, report an `excluded_counts` object that transparently tracks what was filtered out at each qualification step. Use the exact key names from the answer template. Common exclusion buckets:

| Key | Meaning |
|---|---|
| `duplicate` | Tickets marked `is_duplicate = 1` |
| `canceled` | Tickets with `status = 'cancelled'` |
| `internal_or_test_account` | Rows/tickets from non-external accounts |
| `non_customer_impact` | Tickets where `customer_impact = 0` |
| `non_defect_category` | Tickets not in the defect/bug category |
| `usage_non_production_rows_excluded` | Non-production usage rows filtered out |
| `usage_backfill_rows_excluded` | Backfill rows filtered out |
| `usage_internal_or_inactive_account_rows_excluded` | Internal/inactive account rows filtered |
| `usage_without_active_subscription_rows_excluded` | Rows without an active subscription |
| `usage_telemetry_v1_overlap_rows_excluded` | Telemetry v1 rows excluded |
| `ticket_candidates_in_followup_window` | Total tickets in followup window before filtering |
| `ticket_canceled_or_duplicate_excluded` | Cancelled/duplicate tickets excluded from followup |
| `ticket_non_customer_impact_excluded` | Non-customer-impact tickets excluded from followup |

**Counting rule:** Exclusion counts are computed against the **pre-correction** state for correction tasks — they describe what was filtered, not what changed. For non-correction tasks, they describe the full qualification pipeline.

---

## Rounding Rules

- **Two decimal places:** `ROUND(value, 2)` — applies to compute hours, median close hours, added compute hours.
- **Four decimal places:** `ROUND(value, 4)` — applies to SLA breach rate.
- **Integers:** All counts, row numbers, and API call totals are integers — no rounding needed.
- **SQLite caveat:** SQLite's `ROUND()` uses banker's rounding for exact `.5` ties. If precision is critical, compute in the application layer instead. For the metrics in these tasks, SQLite `ROUND()` is acceptable.

---

## Common Pitfalls

1. **Inclusive date ranges.** Both `start_date` and `end_date` are inclusive (`BETWEEN` or `>= AND <=`). For the incident followup window, the start is **exclusive** (`> resolved_at`), end is **inclusive** (`<= resolved_at + 7 days`).

2. **Region casing.** Regions are always uppercase: `NA`, `EMEA`, `APAC`, `LATAM`. Never lowercase or mixed case.

3. **Missing zero-severity entries.** When reporting `severity_counts`, `severity_mix`, or `backlog_by_severity`, always include `P1`, `P2`, `P3`, `P4` keys even if their value is `0`. The answer template requires all four.

4. **Telemetry overlap double-counting.** When excluding telemetry v1 rows, exclude them from both the qualified set AND the compute-hour totals. Report the excluded count separately.

5. **Correction applied before recomputation.** After a correction, recompute metrics from the database as if the UPDATE already ran. Do not arithmetically adjust the pre-correction numbers.

6. **Account name consistency.** Account names follow the pattern `{Brand} {Type} {Region} {NNN}` and must be sourced from the database, not invented. Always `SELECT account_name FROM accounts WHERE account_id = ...`.

7. **qualified_ticket_ids sorting.** Sort as strings (lexicographic), not numerically extracted. `TKT-000025` comes before `TKT-000028`.

8. **SLA breach rate with zero denominator.** If no tickets qualify, return `0.0`, not `NULL` or division-by-zero error.

9. **Correction SQL safety.** Never write an UPDATE without a WHERE clause. Never use a WHERE clause that could match rows outside the approved case. Always guard with product_id, current state, and case-approval EXISTS checks.

10. **Root API discovery.** Do not hardcode endpoint paths. Always GET the root URL first to discover the current API structure.

---

## Workflow Summary

For any task in this group, follow this sequence:

1. **GET the API root** — discover endpoints and query format.
2. **Explore the schema** — query `sqlite_master` or use an `/info` or `/tables` endpoint to understand table structures, column names, and relationships.
3. **For correction tasks:** Query `data_quality_cases` to find the approved case, its target rows, and audit metadata. Build and execute the safe correction SQL. Verify `changed_row_count`.
4. **Query qualified records** — apply filters in the documented order, tracking exclusion counts at each step.
5. **Compute aggregates** — totals, breakdowns, rankings using the deterministic ordering rules.
6. **Assemble the JSON response** — match the answer template's shape exactly. Include all required keys. Use the correct numeric precision and date formats.
7. **Validate** — check ordering, rounding, zero-valued entries, and that exclusion counts sum correctly.
