# Atlas Commerce Operations — Analytical & Correction Task Skill

## Overview

This skill covers analytical reporting and data-correction tasks against the Atlas Commerce Operations database. Every task follows a consistent pattern: read the request facts and answer template, discover the database schema, write SQL to compute the required metrics, and produce a single JSON output matching the template exactly. Correction tasks add a guarded mutation step with audit-trail verification.

## Input Discovery

Every task directory contains:
- `prompt.txt` — narrative instructions, references to payload files, and the required output filename (always `answer.json`).
- `payloads/` — a folder containing the request JSON (business scope, definitions, rules) and the answer template JSON (exact output schema with types, constraints, and ordering rules).

Read all three files before querying the database. The answer template is the authoritative contract: every required field, its type, its constraints (`minimum`, `maximum`, `multipleOf`, `enum`, `pattern`), and any ordering directives must be satisfied.

## Database Discovery

Always begin with two endpoints before writing any SQL:

1. `GET /api/schema` — returns table names and column definitions. Use this to understand what tables exist and how they relate.
2. `GET /api/data-dictionary` — returns business descriptions of each table and column. This clarifies field meanings (e.g., which column represents a "carrier status", which timestamp is "created at" vs "updated at").

Never query `sqlite_master` or PRAGMA interfaces directly; use the schema endpoints.

All API calls require the header `Authorization: Bearer atlas-ops-token-022`.

## Analytical Query Patterns

### Temporal Filtering

Tasks always have time boundaries. Identify them from the request JSON:
- **Cutoff-based**: filter rows where a timestamp is at or before a cutoff (`<= cutoff`). The cutoff may be inclusive or exclusive — check the request.
- **Window-based**: filter rows where a timestamp falls within `[start, end]`, typically inclusive on both sides.
- Some tasks combine both: a creation window plus a state cutoff.

Use the exact UTC timestamps from the request. Do not convert timezones.

### Business-Dimension Filtering

Apply all scope dimensions from the request before computing aggregates:
- **Campaign** (filter by `campaign_id` on the relevant join table).
- **Account tier / segment** (filter by `account_tier` or `segment` on the accounts table).
- **Warehouse / region** (filter or group by warehouse or region IDs).
- **Production-only** populations (filter by a production flag on accounts, orders, shipments, or similar).

### Metric Computation

Translate business definitions into SQL using `CASE`/`WHEN` expressions:
- **Complete vs. incomplete**: a `CASE WHEN` that checks whether every required condition is met (e.g., at least one shipment, all shipments delivered).
- **On-time**: a `CASE WHEN` comparing actual timestamps to promised timestamps.
- **Severe exception / breach**: a `CASE WHEN` combining incompleteness with elapsed-time thresholds.
- **Leakage candidate**: a `CASE WHEN` encoding multi-condition rules (e.g., "net refund > gross in USD OR ≥2 unreversed refunds with same reason").

Compute counts, sums, and rates in a single query or a CTE chain. When multiple levels of aggregation are needed (overall + per-region + per-account), use CTEs or subqueries.

### Ranking and Ordering

When the request specifies ranked output:
- Use `ORDER BY` with the exact tie-breaking rules from the request (e.g., "rate ascending, then region ascending" or "severe count descending, then breach count descending, then account ID ascending").
- For "top N" or "worst N", use `LIMIT N` after ordering.
- For "worst 2 regions" or similar, order by the metric ascending (worst first) and take the limit.

### Rounding

Each answer template specifies rounding via `multipleOf` or a description field:
- Rates: typically 4 decimal places (`multipleOf: 0.0001`).
- Currency amounts: typically 2 decimal places (`multipleOf: 0.01` or `precision: 2`).
- Hours: typically 2 decimal places (`multipleOf: 0.01`).

Round only the final reported values, not intermediate calculations. Use SQL's `ROUND(value, decimals)` or equivalent.

### Currency Conversion (FX)

When a task involves multi-currency amounts:
- The `fx_rates` table provides `usd_per_unit` rates keyed by currency and date.
- Convert by joining on `service_date` (or as specified) and multiplying the amount by `usd_per_unit`.
- Apply conversion before aggregation when comparing across currencies.

### Median Computation

For median of an even-count set, average the two central values. Compute by ordering the values, counting, and selecting the middle row(s). For odd counts use `LIMIT 1 OFFSET ((cnt-1)/2)`. For even counts, average the two central rows.

## Status and Risk Classification

Many tasks have tiered classification rules. Read them from the request JSON:

- Rules are evaluated in listed order (first match wins).
- Each rule has a condition combining thresholds (e.g., "rate ≥ 0.88 AND exception rate < 0.05").
- The last rule is typically a catch-all ("otherwise", "all other outcomes").

Compute the thresholds and apply them in application code after all rates are computed, to avoid complex nested CASE statements.

## Correction (Mutation) Tasks

When a task requires a data correction, follow this pattern:

1. **Identify the contradiction**: Query the relevant table to find the single row where a raw/canonical value mismatch exists. The request will describe the contradiction type (e.g., "raw carrier status contradicts canonical carrier status").

2. **Use the transaction endpoint** (`POST /api/sql/transaction`), not individual SQL statements. The transaction body requires:
   - `statements`: an array of 1–6 SQL statement objects, each with `sql` and optional `params`.
   - `expected_total_changes`: integer count of rows changed across all statements.

3. **Apply the minimal correction**: Update only the single field identified in the contradiction. Use the exact `corrected_at`, `actor`, `reason_code`, `correction_key`, and `audit_id` from the request's `approved_correction` block.

4. **Insert the audit record**: Write a row to `correction_audit` with all required audit columns: `audit_id`, `correction_key`, `entity_type`, `entity_id`, `source_row_id`, `field_name`, `old_value`, `new_value`, `reason_code`, `corrected_at`, `actor`.

5. **Verify**: After the transaction, run a read-only query to confirm the corrected value matches the expected canonical value.

6. **Report `APPLIED`** only when: exactly one business row was updated, exactly one audit row was inserted, and the post-change verification confirms the correction. Otherwise, report `NOT_APPLIED` with the actual observed state.

7. **Backlog analysis**: For carrier/shipment tasks, compute backlog before and after correction (backlog = shipments whose final effective status is not DELIVERED). Report both counts and the delta.

## Output Construction

Build the final JSON object programmatically:

- Match every `required` field from the answer template.
- Do not include extra fields (`additionalProperties: false` in the template).
- Use the exact types specified: integer for counts, number for rates/amounts.
- Apply ordering directives: sort arrays as specified (ascending IDs, ranked lists).
- For empty arrays, use `[]`, not `null`.
- For string fields with no value, use `""` only if the template allows `minLength: 0` or doesn't specify `minLength: 1`.

Write the result to `answer.json` with no commentary, no markdown fences, no trailing text.

## ID Patterns

The database uses stable, formatted business identifiers:
- Orders: `ORD-XXXXXX` (6 digits)
- Cases: `CASE-XXXXXX` (6 digits)
- Accounts: `ACC-XXXX` (4 digits)

These appear in filter values, output arrays, and ranking results. Use them exactly as stored in the database.

## Common Pitfalls

- **Timestamp inclusivity**: Always check whether boundaries are inclusive or exclusive. The request JSON typically states this explicitly.
- **Production-only filters**: Many tasks scope to "production" records. Check for a `production` boolean or `population` field in the relevant table.
- **Effective vs. raw status**: Some tables have both a raw status (from an external system) and a canonical/effective status (the authoritative value). Use the canonical/effective column for business logic.
- **Reversals and net values**: In financial tasks, "effective settled" refunds may have linked reversals. Compute net by subtracting reversal amounts from refund amounts.
- **Active time vs. calendar time**: Some SLA tasks use business/active hours, not calendar hours. Check the `clock_basis` definition in the request.
- **Empty result handling**: When no rows match the filter criteria, return zero counts and empty arrays, not null or missing fields.
- **Unique arrays**: When the template says `uniqueItems: true`, deduplicate before output.
