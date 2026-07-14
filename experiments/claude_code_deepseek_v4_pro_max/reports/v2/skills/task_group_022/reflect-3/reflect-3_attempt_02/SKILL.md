# Shared Operations Analytics — Qualified Usage, Defect, and Correction Workflows

## Overview

This skill covers querying the shared operations analytics database for usage rollups, defect rollups, incident exposure summaries, backlog reports, and data-quality corrections. The database is accessed through a REST API with read-only `/query` and simulation `/simulate` endpoints.

## Database Schema Reference

### Core Tables
- **accounts**: `account_id`, `account_name`, `segment` (enterprise|commercial|startup|internal), `region` (NA|EMEA|APAC|LATAM), `account_status` (active|paused|churned|test), `is_internal` (0|1)
- **products**: `product_id`, `product_name`, `product_family`, `is_active`
- **usage_daily**: `usage_id`, `account_id`, `product_id`, `activity_date`, `environment` (production|staging|sandbox|internal), `source_system` (telemetry_v1|telemetry_v2|import_patch), `seats_active`, `api_calls`, `compute_hours`, `data_gb`, `is_backfill` (0|1), `audit_reason`, `audit_updated_at`
- **tickets**: `ticket_id`, `account_id`, `product_id`, `created_at`, `closed_at`, `status` (open|in_progress|resolved|canceled), `severity` (P1|P2|P3|P4), `category` (bug|outage|performance|data_loss|how_to|billing|feature_request|internal_test), `customer_impact` (0|1), `is_duplicate` (0|1), `duplicate_of`, `linked_incident_id`, `sla_due_at`, `audit_reason`, `audit_updated_at`
- **subscriptions**: `subscription_id`, `account_id`, `product_id`, `plan_code` (enterprise|growth|standard|trial|internal), `subscription_status` (active|paused|ended|trial)
- **incidents**: `incident_id`, `product_id`, `started_at`, `resolved_at`, `severity` (SEV1|SEV2|SEV3), `impacted_region`, `public_status`
- **data_quality_cases**: `case_id`, `case_type` (usage_product_correction|ticket_duplicate_correction), `case_status` (approved|draft|rejected), `target_table`, `target_ids_csv`, `field_name`, `old_value`, `new_value`, `approval_code`, `audit_reason`

### Key Views
- **active_customer_accounts**: accounts WHERE is_internal=0 AND account_status IN ('active','paused')
- **production_usage_daily**: usage_daily WHERE environment='production'
- **customer_support_tickets**: tickets WHERE category<>'internal_test'

## Qualification Rules

### Usage Qualification (for compute-hours metrics)
Start from `usage_daily` and apply these filters in order:

1. **Product scope**: Match the requested `product_id`
2. **Date range**: `activity_date` between inclusive start and end dates
3. **Production only**: `environment = 'production'`
4. **Exclude backfill**: `is_backfill = 0`
5. **Exclude telemetry_v1 overlap**: `source_system <> 'telemetry_v1'` — telemetry_v1 and telemetry_v2 may record overlapping observations during migration periods. Use telemetry_v2 as the canonical source.
6. **Enterprise accounts**: Join with `accounts` WHERE `segment = 'enterprise'`
7. **Exclude internal**: `is_internal = 0`
8. **Region filter**: Apply region constraint when the task scopes to a specific region

Count telemetry_v1 rows excluded by step 5 as `telemetry_v1_rows_excluded` (these are rows matching all other criteria but with `source_system = 'telemetry_v1'`).

### Ticket Qualification (for defect/customer-impacting metrics)
Start from `tickets` and apply these exclusion filters:

1. **Product scope**: Match the requested `product_id`
2. **Date range**: `created_at` between inclusive start and end dates
3. **Exclude internal/test accounts**: Join with `accounts` WHERE `is_internal = 1` OR `account_status = 'test'`
4. **Exclude canceled**: `status <> 'canceled'`
5. **Exclude non-customer-impact**: `customer_impact = 1` only
6. **Defect categories only**: `category IN ('bug', 'outage', 'performance', 'data_loss')`
7. **Exclude duplicates**: `is_duplicate = 0`

Excluded counts are tallied from the **original population** (all tickets in scope), not sequentially. That means:
- `excluded_counts.internal_or_test_account` = count of is_internal=1 OR account_status='test' from all tickets in scope
- `excluded_counts.canceled` = count of status='canceled' from all tickets in scope
- `excluded_counts.non_customer_impact` = count of customer_impact=0 from the non-internal, non-canceled subset
- `excluded_counts.non_defect_category` = count of non-defect categories (how_to, billing, feature_request, internal_test) from the non-internal, non-canceled subset
- `excluded_counts.duplicate` = total is_duplicate=1 from all tickets in scope (equals `excluded_duplicate_count`)

### Incident Usage Qualification
For incident exposure windows:
1. `product_id` matches the incident's product
2. `activity_date` falls within the incident window (inclusive: `started_at` through `resolved_at` dates)
3. `environment = 'production'`
4. `is_backfill = 0`
5. `source_system <> 'telemetry_v1'`
6. Account is non-internal (`is_internal = 0`)
7. Account has an active subscription (`subscription_status = 'active'`) for the product during the incident

Usage `excluded_counts` track each filter step's removal count from the original candidate pool.

### Backlog Definition
Backlog = qualified tickets where `status IN ('open', 'in_progress')`. Use the same qualification rules as ticket qualification above.

## Correction/SQL Patterns

### Writing Correction SQL
Every data-quality correction must be a **safe, idempotent SQLite UPDATE**:

```sql
UPDATE <target_table>
SET <field_name> = '<new_value>',
    audit_reason = '<audit_reason from data_quality_cases>',
    audit_updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now')
WHERE <id_column> IN (<target_ids from data_quality_cases.target_ids_csv>)
  AND <field_name> = '<old_value>'
```

Key rules:
- Always guard with the current value (`AND field_name = old_value`) for safety
- Always populate `audit_reason` from the `data_quality_cases` row verbatim
- Always set `audit_updated_at` to mark the correction timestamp
- For usage corrections: target `usage_daily`, field is typically `product_id`
- For ticket corrections: target `tickets`, field is typically `is_duplicate` + `duplicate_of`
- Use `strftime('%Y-%m-%d %H:%M:%S', 'now')` for the timestamp format
- `changed_row_count` = number of rows actually modified by the UPDATE (what the simulation reports as `changed_rows`)

### Simulation Workflow
Use `/simulate` to apply the correction on a temporary copy, then run read-only queries against it:
```json
{
  "script": "<SQL update statement>",
  "queries": [
    {"sql": "<post-correction query 1>"},
    {"sql": "<post-correction query 2>"}
  ]
}
```

## SLA Breach Rules

A qualified ticket has breached SLA when:
- **Resolved**: `closed_at > sla_due_at`
- **Open or in_progress**: `sla_due_at < current_date` (or end of reporting period)

`sla_breach_rate` = breached_count / qualified_ticket_count, rounded to **4 decimal places**.

For backlog-specific breach counts (`breached_backlog_ticket_count`): same rule applied only to backlog tickets.

## Median Close Hours

Compute `(julianday(closed_at) - julianday(created_at)) * 24` for each **closed** qualified ticket. Sort the values ascending; the median is the middle value (for odd count) or average of two middle values (for even count). Round to **2 decimal places**.

## Output-Field Conventions

### Rounding
- `compute_hours`: round to **2 decimal places**
- `sla_breach_rate`: round to **4 decimal places**
- `median_close_hours`: round to **2 decimal places**
- `added_compute_hours`: round to **2 decimal places**

### Ordering
| Section | Primary Sort | Secondary Sort | Tertiary Sort |
|---------|-------------|----------------|---------------|
| `top_accounts` | `compute_hours` DESC | `account_id` ASC | — |
| `top_accounts` (tickets) | `ticket_count` DESC | `account_id` ASC | — |
| `regional_breakdown` | `region` ASC (alphabetical) | — | — |
| `account_breakdown` | `account_id` ASC | — | — |
| `qualified_ticket_ids` | `ticket_id` ASC | — | — |
| `affected_accounts` | `account_id` ASC | — | — |
| `impacted_accounts` | `compute_hours` DESC | `account_id` ASC | — |
| `accounts_to_notify` | `backlog_ticket_count` DESC | `highest_severity` ASC (P1→P4) | `account_id` ASC |
| `accounts_with_followup_tickets` | `account_id` ASC | — | — |

### Severity Priority
Severities sort in priority order: **P1 > P2 > P3 > P4**. When sorting "ascending highest_severity," P1 comes first (highest priority), then P2, P3, P4.

### Date Formats
- Dates only: `YYYY-MM-DD` (e.g., `2026-01-01`)
- Timestamps: `YYYY-MM-DD HH:MM:SS` (e.g., `2026-05-20 10:57:13`)

### Date Range Inclusivity
- Usage periods: **inclusive** on both start and end dates
- Ticket creation periods: **inclusive** on both start and end dates
- Follow-up ticket windows: **exclusive** start (after `resolved_at`), **inclusive** end (`resolved_at + 7 days`)

### Zero-Valued Severities
When reporting `backlog_by_severity` or `severity_mix`, always include all four keys `{"P1": 0, "P2": 0, "P3": n, "P4": m}` even if some are zero.

### Top Account Limit
`top_accounts` includes the **top 5** accounts by the designated metric, or all qualified accounts if fewer than 5 exist. Ties are broken by ascending `account_id`.

## Incident Follow-Up Tickets

For incident post-resolution monitoring:
- Window: `start_exclusive = resolved_at`, `end_inclusive = resolved_at + 7 days`
- Scope: tickets for the incident's `product_id`, created by external customer accounts in the incident's `impacted_region`
- Qualification: exclude canceled, duplicate, and non-customer-impact tickets
- `ticket_candidates_in_followup_window`: total tickets in the window before exclusions
- `ticket_canceled_or_duplicate_excluded`: count removed for canceled or duplicate
- `ticket_non_customer_impact_excluded`: count removed for non-customer-impact
- `accounts_with_followup_tickets`: only accounts with tickets that survive all exclusions
- `severity_mix`: severity distribution across **all** tickets in the follow-up window (before exclusions)

## Data Quality Case Lookup

Always look up the approved case in `data_quality_cases`:
- Verify `case_status = 'approved'`
- Use `target_ids_csv` split by comma for the UPDATE's WHERE IN clause
- Use `old_value` as the safety guard condition
- Use `new_value` as the new field value
- Use `audit_reason` verbatim in both the SQL UPDATE and the response

## Common Pitfalls

1. **Telemetry overlap**: Never include both telemetry_v1 and telemetry_v2 in qualified usage. Exclude v1 and count excluded rows.
2. **Excluded counts are not sequential**: Excluded counts are computed from the original candidate population, not from what remains after previous exclusions. For `non_defect_category`, this means counting ALL non-defect categories from the non-internal, non-canceled subset — including those that are also non-customer-impact.
3. **Duplicate counts**: `excluded_duplicate_count` and `excluded_counts.duplicate` should match — both count all `is_duplicate=1` tickets in the original scoped population.
4. **Active subscriptions for incidents**: Usage during an incident window requires an active subscription; accounts without active subscriptions are excluded from impacted_accounts but their usage rows count in `usage_without_active_subscription_rows_excluded`.
5. **Account status edge cases**: Paused accounts may have usage data but may not qualify depending on the task's explicit scope. Check `account_status` against the qualification rules.
6. **SLA breach for open tickets**: Open/in_progress tickets past their `sla_due_at` count as breached — not just resolved-late tickets.
7. **Rounding aggregation**: Round sums, not individual rows. Sum raw values first, then round the result.
8. **Correction SQL idempotency**: Always guard with current field value to make the UPDATE safe for re-execution.
