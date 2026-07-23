# Atlas Commerce Operations — Analytical Task Skill

## When to use

Use this skill when working with the Atlas Commerce Operations workplace database to answer analytical business questions. The environment provides a read-only SQL API, a controlled transaction API for data corrections, an audit view, and business documents that define cohorts, metrics, thresholds, and output schemas.

---

## Entry workflow

### 1. Explore the schema and data dictionary first

Before writing any analytical query, fetch the full schema and data dictionary from the authenticated workplace service:

```
GET /api/schema
GET /api/data-dictionary
```

The schema returns DDL for every table and index. The data dictionary returns column descriptions and conventions (timestamp formats, money handling, source-row vs canonical-row semantics). Read both completely before proceeding — table relationships, index names, and column-level notes often encode the correct analytical pattern.

### 2. Read the business request document carefully

Every task includes a request document (often in `payloads/` as JSON). This document defines:

- **Cohort / population**: Which rows are in scope. Look for account filters (`tier`, `segment`, `region`, `is_internal = 0`, `is_test = 0`), date windows (with boundary semantics — inclusive/exclusive), and entity-specific membership rules.
- **Business definitions**: How key terms like "complete," "on-time," "effective," "settled," or "severe" are defined. These are operational definitions that must be translated literally into SQL predicates.
- **Rollup / aggregation rules**: How rates are computed, what denominators to use, how to handle incomplete subsets.
- **Rounding policies**: Which values to round, to how many decimal places, and when (usually only final reported rates).
- **Ranking / ordering rules**: Multi-key sort orders with tiebreakers.
- **Status / classification rules**: Tiered thresholds with fallthrough logic (e.g., HEALTHY → WATCH → CRITICAL).

### 3. Map request definitions to schema columns

For every term in the business definitions, identify the exact column and table. Common mappings:

| Business term | Typical column | Notes |
|---|---|---|
| Production accounts | `accounts.is_internal = 0 AND accounts.is_test = 0` | Always filter out internal and test accounts unless explicitly told otherwise |
| Campaign active window | `campaigns.starts_at` / `campaigns.ends_at` | Compare against `orders.order_created_at` |
| Effectively delivered | `carrier_scans.canonical_status` | See [effective-final pattern](#appendix-a-effective-final-determination) |
| Settled refund | `refund_attempts.status = 'SETTLED'` | See [money pattern](#appendix-b-money-and-fx-conversion) |
| Reversal | `refund_attempts.status = 'REVERSED'` with `linked_refund_id` | Connects to the reversed refund |
| Service date | `refund_attempts.service_date` | ISO date YYYY-MM-DD, used for FX rate lookup |
| Cutoff / as-of timestamp | Parameter in request | Used as upper bound for event comparisons |
| Active time | Computed from `case_events.event_at` | Use opened_at from support_cases as the start |

### 4. Always deduplicate source data first

Every event table (`carrier_scans`, `refund_attempts`, `warehouse_task_events`, `case_events`, `payment_events`, `order_events`, `inventory_movements`) may contain duplicate imports of the same source event. The database indexes tell you how: look for `idx_*_dedupe` indexes on `(source_system, external_event_id, ingested_at)`.

**Standard dedup CTE:**

```sql
WITH dedup AS (
  SELECT t.* FROM <table> t
  WHERE t.<row_id_column> = (
    SELECT t2.<row_id_column> FROM <table> t2
    WHERE t2.source_system = t.source_system
      AND t2.external_event_id = t.external_event_id
    ORDER BY t2.ingested_at DESC, t2.<row_id_column> DESC
    LIMIT 1
  )
)
```

Apply this CTE before any other filtering or aggregation. Missing dedup will inflate counts, duplicate amounts, and produce wrong rates. This is the single most common source of errors.

### 5. Determine effective final state from append-only events

For event tables that accumulate over time (`carrier_scans`, `warehouse_task_events`, `case_events`), the "effective" or "current" state of an entity is the **latest event by timestamp**, not a denormalized status column (which the data dictionary describes as "a convenience snapshot that may lag").

**Standard effective-final pattern (after dedup):**

```sql
best_row AS (
  SELECT d.* FROM dedup d
  WHERE NOT EXISTS (
    SELECT 1 FROM dedup d2
    WHERE d2.<entity_id> = d.<entity_id>
      AND (d2.<timestamp_col> > d.<timestamp_col>
           OR (d2.<timestamp_col> = d.<timestamp_col>
               AND d2.<row_id> > d.<row_id>))
  )
)
```

The `NOT EXISTS` pattern reliably selects exactly one row per entity: the one with the highest timestamp, tiebroken by the highest row ID. The index named `idx_*_effective` in the schema confirms the sort columns.

### 6. Convert money values properly

Monetary amounts use the **smallest currency unit** (e.g., cents). The data dictionary states: "Monetary minor fields use the smallest unit of the row currency; FX is USD per currency unit."

**Standard money conversion:**

```
amount_in_currency = amount_minor / 100.0
amount_in_usd = amount_in_currency * fx_rates.usd_per_unit
```

Join `fx_rates` on `rate_date = <row>.service_date AND currency = <row>.currency`. Note that even USD rows may have a `usd_per_unit` value slightly different from 1.0 — always use the FX rate from the table, never assume 1.0.

For order gross comparisons, convert the order's `gross_amount_minor` using the same service-date FX rate as the refund being compared. When multiple refunds exist for one order, each order's refunds in this dataset fall on a single service date, so a single rate applies.

### 7. Use canonical fields, not raw fields

Tables like `carrier_scans` and `inventory_movements` have both `raw_*` and `canonical_*` columns. Always use the canonical columns for operational analytics unless the task explicitly asks you to identify or fix a contradiction between raw and canonical values. The data dictionary states: "Raw fields preserve source values; canonical fields hold normalized operational values."

When a task asks you to find and fix a canonical contradiction, compare `raw_status` against `canonical_status` (or `raw_event_at` against `canonical_event_at`) for rows in the named import batch. The correction changes only the canonical field to match the raw (source) value. The correction is applied via a transaction that includes both an `UPDATE` of the business row and an `INSERT` into `correction_audit`.

### 8. Build output to match the answer template exactly

Every task provides an `answer_template.json` with a JSON Schema. Your output must:

- Include exactly the required properties (no extra fields: `additionalProperties: false`).
- Match the exact types, formats, and constraints (`minimum`, `maximum`, `multipleOf`, `pattern`, `enum`).
- Order array elements as specified (e.g., "order_id ascending").
- Apply rounding only where stated, to the specified number of decimal places.
- Use the exact string values from `enum` constraints.

### 9. Interpret status classification rules as cascading conditions

Many tasks include tiered status rules (e.g., HEALTHY → WATCH → CRITICAL or CONTROLLED → ELEVATED → SEVERE). These are evaluated in order: the first matching condition wins. If conditions reference rates computed from the same data, compute the rates first, then classify.

---

## Common traps

1. **Forgetting to deduplicate** — The most frequent error. Always check for `idx_*_dedupe` indexes; if one exists, you must dedup. Duplicate rows will inflate counts and distort rates.

2. **Using denormalized status columns** — Columns like `orders.current_status` and `shipments.current_status` are described as convenience snapshots that may lag. For cutoff-accurate analysis, determine state from the append-only event tables.

3. **Ignoring no-shipment orders** — An order with no physical shipment is incomplete by definition. Always LEFT JOIN from orders to shipments and handle NULLs explicitly.

4. **Rounding intermediate values** — Only round final reported rates. Rounding intermediate values can compound errors.

5. **Assuming USD FX rate is 1.0** — Always look up the rate from `fx_rates`, even for USD. The data may use non-1.0 rates for USD conversions.

6. **Missing tiebreakers in ranking** — When a ranking says "A DESC, B ASC", always include B as a tiebreaker even if A values appear unique. The tiebreaker ensures deterministic output.

7. **Using the wrong date for FX conversion** — Always use `service_date` for refunds, not `event_at` or `ingested_at`. Match the date to the business event, not the ingestion timestamp.

8. **Including non-production accounts** — Always filter `is_internal = 0 AND is_test = 0` unless the task explicitly scopes to internal or test accounts.

---

## Appendix A: Effective-final determination

For carrier scans, the "effective final carrier status" is the `canonical_status` of the scan with the highest `canonical_event_at` per shipment. When multiple scans tie on `canonical_event_at`, the highest `scan_row_id` breaks the tie. The index `idx_scans_shipment_effective ON carrier_scans(shipment_id, canonical_event_at, scan_row_id)` confirms this ordering.

A shipment is "effectively DELIVERED by a cutoff" when its effective final `canonical_status` is `'DELIVERED'` and its effective final `canonical_event_at` is on or before the cutoff.

An order is complete when it has at least one shipment and every shipment is effectively DELIVERED by the cutoff.

An order is on-time when it is complete and every shipment's effective final `canonical_event_at` is not later than that shipment's `promised_delivery_at`.

## Appendix B: Money and FX conversion

The `fx_rates` table has daily rates expressed as USD per currency unit. To convert a monetary amount:

```
amount_in_usd = (amount_minor / 100.0) * usd_per_unit
```

Where `usd_per_unit` is the rate for the row's `currency` on the row's `service_date` (or `rate_date` for other contexts).

For net refund amounts, sum the USD-converted values of all settled refunds, then subtract the USD-converted values of all linked reversals. Display to 2 decimal places.

## Appendix C: Data correction workflow

When a task requires applying a canonical data correction:

1. Identify the exact contradiction by comparing `raw_status` to `canonical_status` (or `raw_event_at` to `canonical_event_at`) within the named `import_batch_id`.
2. The correction target is the `scan_row_id` (or equivalent row identifier) whose canonical field disagrees with its raw field.
3. Apply the correction through `POST /api/sql/transaction` with an `UPDATE` on the business row and an `INSERT` into `correction_audit`. The `expected_total_changes` must match the actual number of changed rows.
4. The audit record uses the provided `audit_id`, `correction_key`, `reason_code`, `actor`, and `corrected_at` from the request.
5. `entity_type` is the table name, `entity_id` is the business entity (e.g., `shipment_id`), and `source_row_id` is the corrected row's primary key.
6. After the transaction, verify the correction by querying the corrected row to confirm the canonical value changed.
7. Report `APPLIED` only when exactly one business row and one audit row committed AND post-change verification confirms the correction. Report `NOT_APPLIED` otherwise.
