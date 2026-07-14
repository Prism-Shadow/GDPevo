# Operations Analytics API — Qualified Usage & Ticket Rollup Skill

## Overview

This skill covers querying the shared operations analytics database for qualified usage rollups, ticket/defect rollups, incident exposure summaries, and data-quality correction workflows. The API exposes a SQLite database through HTTP endpoints.

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET /health` | Service status |
| `GET /schema` | Full table/view/column catalog |
| `GET /tables` | Table and view names |
| `GET /tables/<name>?limit=100&offset=0` | Sample rows |
| `POST /query` | Read-only SQL with `{"sql": "...", "params": [...]}` |
| `POST /simulate` | Run an UPDATE on a temp copy, then run read-only queries on that copy |

Always start by reading `/schema` to confirm column names and CHECK constraints. Use `/tables/<name>` for a quick first look at data shape before writing production queries.

## Database Schema (Core Tables)

### accounts
- `account_id TEXT PK`, `account_name`, `segment` (enterprise/commercial/startup/internal), `region` (NA/EMEA/APAC/LATAM), `account_status` (active/paused/churned/test), `is_internal` (0/1)

### products
- `product_id TEXT PK` (ATLASDB, HELIOSYNC, NEXAQUEUE, LUMAFORMS), `product_name`, `product_family`, `is_active`

### subscriptions
- `subscription_id TEXT PK`, `account_id`, `product_id`, `plan_code` (enterprise/growth/standard/trial/internal), `subscription_status` (active/paused/ended/trial), `start_date`, `end_date`

### usage_daily
- `usage_id TEXT PK`, `account_id`, `product_id`, `activity_date`, `environment` (production/staging/sandbox/internal), `source_system` (telemetry_v1/telemetry_v2/import_patch), `seats_active`, `api_calls`, `compute_hours REAL`, `data_gb`, `is_backfill` (0/1), `recorded_at`, `audit_reason`, `audit_updated_at`

### tickets
- `ticket_id TEXT PK`, `account_id`, `product_id`, `created_at`, `closed_at`, `status` (open/in_progress/resolved/canceled), `severity` (P1/P2/P3/P4), `category` (bug/outage/performance/data_loss/how_to/billing/feature_request/internal_test), `customer_impact` (0/1), `is_duplicate` (0/1), `duplicate_of`, `linked_incident_id`, `sla_due_at`, `audit_reason`, `audit_updated_at`

### incidents
- `incident_id TEXT PK`, `product_id`, `started_at`, `resolved_at`, `severity` (SEV1/SEV2/SEV3), `impacted_region` (NA/EMEA/APAC/LATAM/GLOBAL), `public_status`

### data_quality_cases
- `case_id TEXT PK`, `case_type` (usage_product_correction/ticket_duplicate_correction), `case_status` (approved/draft/rejected), `target_table`, `target_ids_csv`, `field_name`, `old_value`, `new_value`, `approval_code`, `audit_reason`

### metric_notes (reference)
- Topic `usage`, `production`, `backfill`, `defect`, `duplicate tickets`, `customer impact`, `internal accounts`, `incidents`, `audit fields`, `source systems`

### Views
- `active_customer_accounts`: accounts WHERE is_internal=0 AND account_status IN ('active','paused')
- `customer_support_tickets`: tickets WHERE category <> 'internal_test'
- `production_usage_daily`: usage_daily WHERE environment='production'

## Standard Qualified Usage Definition

Apply these filters for all usage rollup queries:

```sql
WHERE u.product_id = ?
  AND u.activity_date BETWEEN ? AND ?       -- inclusive date range from task
  AND u.environment = 'production'           -- production only
  AND u.is_backfill = 0                      -- exclude late-arriving backfill
  AND u.source_system <> 'telemetry_v1'      -- exclude telemetry v1 rows entirely
  AND a.is_internal = 0                      -- external accounts only
  AND a.account_status <> 'test'             -- exclude test accounts
```

### Enterprise Account Subscription Filter

When the task specifies "enterprise customer accounts," add an EXISTS clause. Do NOT join subscriptions directly (it duplicates usage rows when an account has multiple subscriptions):

```sql
AND EXISTS (
  SELECT 1 FROM subscriptions s
  WHERE s.account_id = u.account_id
    AND s.product_id = u.product_id
    AND s.plan_code = 'enterprise'
    AND s.subscription_status = 'active'
)
```

For tasks requiring the subscription to be active *during the usage period*, also check dates:
```sql
    AND s.start_date <= <period_end_date>
    AND (s.end_date IS NULL OR s.end_date >= <period_start_date>)
```

### Account-Scope Filters

- **Region filter**: add `AND a.region = ?` when the task names a specific region
- **Segment filter**: add `AND a.segment = 'enterprise'` when specifically for enterprise accounts
- For global enterprise queries, use segment='enterprise' with no region restriction

### Telemetry v1 Exclusion Rule

**Always exclude ALL `source_system = 'telemetry_v1'` rows from qualified usage.** The `telemetry_v1_rows_excluded` field reports the count of telemetry_v1 rows that were in the candidate set (matching product, date range, production, non-backfill, account criteria, and subscription criteria where applicable) but excluded from the qualified result.

## Standard Qualified Ticket (Defect) Definition

For customer-impacting defect rollups, apply:

```sql
WHERE t.product_id = ?
  AND t.created_at BETWEEN ? AND ?           -- inclusive date range
  AND t.customer_impact = 1                  -- affected external customers
  AND t.category IN ('bug', 'outage', 'performance', 'data_loss')  -- defect categories per metric_notes
  AND t.is_duplicate = 0                     -- exclude duplicates
  AND t.status <> 'canceled'                 -- exclude canceled
  AND a.is_internal = 0                      -- external accounts only
  AND a.account_status <> 'test'             -- exclude test accounts
```

### Ticket Exclusion Counts

Compute each exclusion independently from the **full candidate set** (all tickets for the product in the date range, joined to accounts). Each exclusion category counts rows matching that criterion regardless of overlap with other categories:

| Exclusion | SQL Condition |
|-----------|--------------|
| `duplicate` | `t.is_duplicate = 1` |
| `canceled` | `t.status = 'canceled'` |
| `internal_or_test_account` | `a.is_internal = 1 OR a.account_status = 'test'` |
| `non_customer_impact` | `t.customer_impact = 0` |
| `non_defect_category` | `t.category NOT IN ('bug','outage','performance','data_loss')` |

The `excluded_duplicate_count` top-level field equals `excluded_counts.duplicate`.

## SLA Breach Calculation

A ticket breaches SLA when either:
- **Resolved tickets**: `closed_at > sla_due_at`
- **Open/In-Progress tickets**: `sla_due_at < current date` (use the task's effective "now" date — the period end date or the current date from context)

Compute the breach rate as `breached_count / total_qualified_count`, rounded to **4 decimal places**.

## Backlog Definition

Backlog = qualified tickets with `status IN ('open', 'in_progress')`. Report backlog counts by severity including zero-valued severities (always include P1, P2, P3, P4 keys).

## Median Close Hours

For qualified tickets with `closed_at IS NOT NULL`:
1. Compute `(closed_at - created_at)` in hours for each
2. Sort durations ascending
3. Median = middle value (odd count) or average of two middle values (even count)
4. Round to **2 decimal places**

## Incident Exposure Workflow

When given an incident ID:
1. Query `incidents` for the authoritative `started_at`, `resolved_at`, `impacted_region`, `severity`, and `product_id`
2. Compute the followup ticket window: `(resolved_at + 1 second)` exclusive to `(resolved_at + 7 days)` inclusive
3. For qualified production usage exposure during the incident window:
   - Apply standard qualified usage filters (production, non-backfill, non-telemetry_v1, non-internal, enterprise subscription)
   - Filter accounts to the `impacted_region` from the incident record
   - Sum `api_calls` and `compute_hours` per account
4. For post-incident support signals:
   - Query tickets in the followup window for the same product
   - Filter to accounts in the impacted region, non-internal
   - Report severity mix (P1–P4) and per-account ticket counts
5. Excluded counts for usage follow the same independent-counting pattern as ticket exclusions:
   - `usage_candidate_rows`: all usage rows for the product on the incident date(s)
   - `usage_non_production_rows_excluded`: environment <> 'production'
   - `usage_backfill_rows_excluded`: is_backfill = 1
   - `usage_internal_or_inactive_account_rows_excluded`: internal accounts or test status
   - `usage_without_active_subscription_rows_excluded`: no active enterprise subscription
   - `usage_telemetry_v1_overlap_rows_excluded`: source_system = 'telemetry_v1'
   - `ticket_candidates_in_followup_window`: all tickets in followup window for region
   - `ticket_canceled_or_duplicate_excluded`: status='canceled' OR is_duplicate=1
   - `ticket_non_customer_impact_excluded`: customer_impact = 0

## Data Quality Correction Workflow

### Usage Product Correction (case_type = 'usage_product_correction')

Read the `data_quality_cases` row and construct a safe UPDATE:
```sql
UPDATE usage_daily
SET <field_name> = '<new_value>',
    audit_reason = '<audit_reason from case>',
    audit_updated_at = datetime('now')
WHERE usage_id IN (<target_ids_csv parsed as list>)
  AND <field_name> = '<old_value>'   -- safety check
```

Key fields for the response:
- `changed_row_count`: number of rows in `target_ids_csv`
- `total_compute_hours_after_fix`: recompute qualified usage for the target product, period, and account scope, including corrected rows that meet qualification criteria
- `affected_accounts`: enterprise accounts whose corrected rows meet ALL qualification criteria (production, non-backfill, non-v1, active enterprise subscription). Include accounts that only appear after the correction. Omit accounts whose corrected rows fail qualification (e.g., commercial accounts without enterprise subscriptions). Order by `account_id` ascending.
- `top_account_after_fix`: the account with the highest `compute_hours` after the fix, breaking ties by ascending `account_id`
- `audit_reason`: exact string from the case record

### Ticket Duplicate Correction (case_type = 'ticket_duplicate_correction')

Construct a safe UPDATE that sets both `is_duplicate = 1` and `duplicate_of`:
```sql
UPDATE tickets
SET is_duplicate = 1,
    duplicate_of = '<new_value>',
    audit_reason = '<audit_reason>',
    audit_updated_at = datetime('now')
WHERE ticket_id IN (<target_ids>)
  AND is_duplicate = 0           -- safety check
  AND duplicate_of IS NULL       -- safety check
```

Then recompute qualified tickets with the standard `is_duplicate = 0` filter (the corrected tickets are now excluded). Report:
- `changed_ticket_count`: number of tickets updated
- `qualified_ticket_count_after_fix`: count after excluding the newly-marked duplicates
- `backlog_by_severity`: open/in_progress counts by P1–P4
- `sla_breach_rate_after_fix`: recomputed breach rate
- `accounts_to_notify`: accounts with backlog tickets, sorted by backlog count descending, then severity priority (P1 before P2 before P3 before P4), then account_id ascending

## Deterministic Ordering Rules

| Context | Order |
|---------|-------|
| Account breakdowns | `account_id ASC` |
| Top accounts by usage | `compute_hours DESC`, `account_id ASC` |
| Top accounts by tickets | `ticket_count DESC`, `account_id ASC` |
| Ticket IDs | `ticket_id ASC` (string sort) |
| Regional breakdown | Alphabetical by region: APAC, EMEA, LATAM, NA |
| Severity | Priority order: P1, P2, P3, P4 |
| Accounts to notify | `backlog_ticket_count DESC`, `highest_severity` priority (P1–P4), `account_id ASC` |

## Rounding & Precision Rules

| Field | Precision |
|-------|-----------|
| `compute_hours` | 2 decimal places (ROUND to 2) |
| `added_compute_hours` | 2 decimal places |
| `total_compute_hours_after_fix` | 2 decimal places |
| `sla_breach_rate` | 4 decimal places |
| `sla_breach_rate_after_fix` | 4 decimal places |
| `median_close_hours` | 2 decimal places |

## /simulate for Correction Validation

Before finalizing correction answers, use `POST /simulate` to run the UPDATE on a temporary copy and verify the result:
```json
{
  "simulate_sql": "UPDATE usage_daily SET product_id = 'ATLASDB', audit_reason = '...', audit_updated_at = datetime('now') WHERE usage_id IN (...)",
  "verify_sql": "SELECT COUNT(*) as changed FROM usage_daily WHERE audit_reason = '...'"
}
```

## Common Pitfalls

1. **Subscription join duplication**: Never JOIN subscriptions directly in aggregate queries. Use EXISTS to avoid multiplying rows when an account has multiple subscriptions for the same product.
2. **Telemetry source overlap**: The `telemetry_v1` exclusion is blanket — exclude ALL `telemetry_v1` rows, not only those overlapping with `telemetry_v2` on the same (account, date).
3. **Backfill exclusion**: Always add `is_backfill = 0`. Backfill rows are late-arriving data loaded after normal processing.
4. **Internal account detection**: Check both `is_internal = 1` AND `account_status = 'test'`. Some internal accounts may have status 'active'.
5. **Date range inclusivity**: All date filters use `BETWEEN` which is inclusive on both ends. For the followup ticket window, use `> start_exclusive AND <= end_inclusive`.
6. **SLA breach for open tickets**: Include open/in_progress tickets whose `sla_due_at` has passed. Don't only check resolved tickets.
7. **Region alignment**: For incident queries, filter impacted accounts to the incident's `impacted_region`. For general usage rollups, filter to the region(s) specified in the task.
8. **Correction safety**: Always include a WHERE clause checking the current value (`field_name = old_value` from the case) to prevent re-applying corrections.
9. **Audit fields**: Both `audit_reason` (from the case) and `audit_updated_at` (set to `datetime('now')`) must be populated in every correction UPDATE.
10. **Zero-valued severities**: In backlog and severity mix reports, always include all four severity keys (P1–P4), even when the count is zero.
11. **Account scope in corrections**: When computing `affected_accounts` for a usage correction, only include accounts whose corrected rows meet ALL qualification criteria — enterprise segment, active enterprise subscription, and the usage-level filters (production, non-backfill, non-v1).
