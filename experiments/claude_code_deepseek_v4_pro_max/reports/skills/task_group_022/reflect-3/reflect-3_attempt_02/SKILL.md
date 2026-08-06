# Atlas Commerce Operations — Analytical Task Skill

## When to Use

Invoke this skill when asked to produce a data-analysis answer from the Atlas Commerce Operations workplace: scorecards, reconciliations, quality reviews, productivity reports, or health reviews that require SQL queries against the provided database and submission of a structured JSON answer matching a supplied template.

## Core Environment

A workplace service is available at the base URL provided in the task prompt. All requests require the header `Authorization: Bearer <token>` where `<token>` is supplied in the prompt or environment. The service exposes these endpoints:

- `GET /api/schema` — table DDL and indexes.
- `GET /api/data-dictionary` — column descriptions, conventions (timestamps are ISO‑8601 UTC, money uses smallest currency units, raw vs canonical fields).
- `POST /api/sql` — read‑only analytical queries. Body: `{"sql": "<SQL>", "params": []}`.
- `GET /api/correction-audit` — lists applied canonical corrections.
- `POST /api/sql/transaction` — controlled writes (see Correction Workflow below).

Always begin by fetching `/api/schema` and `/api/data-dictionary` so you know every table, column, index, and convention before writing any analytical query.

## Deduplication (Universal Rule)

Any table whose indexes include a deduplication index named `idx_<table>_dedupe` on `(source_system, external_event_id, ingested_at)` **must** be deduplicated before any other processing:

1. Group rows by `(source_system, external_event_id)`.
2. Keep the single row with the **maximum `ingested_at`**.
3. Discard all other copies — they are import-retry duplicates.

Tables requiring dedup include: `carrier_scans`, `case_events`, `refund_attempts`, `payment_events`, `inventory_movements`, `order_events`, `warehouse_task_events`.

The resulting set is the **effective** rows. All status checks, counts, and time calculations operate on the deduplicated set only.

## Effective Final State (Append‑Only Event Tables)

For tables that record an append-only event history (`carrier_scans`, `case_events`, `warehouse_task_events`), determine the effective current state of an entity as follows:

1. Deduplicate the event rows first.
2. For each entity (shipment, case, task), find the single row with the **maximum event timestamp** (`canonical_event_at` / `event_at`).
3. If multiple rows share the maximum timestamp, tie‑break by taking the **maximum row identifier** (`scan_row_id` / `case_event_id` / `task_event_id`).
4. The status on that row is the **effective final status**.

Do **not** use the denormalised `current_status` column on header tables (`shipments`, `support_cases`, `warehouse_tasks`) — the data dictionary notes it "may lag append‑only event history." Use the event tables with the dedup‑then‑latest pattern instead.

## Money and FX

- All monetary amounts are stored in **minor units** (cents, pence — divide by 100 for major units).
- Cross‑currency conversion uses `fx_rates.usd_per_unit` matched on `(rate_date = service_date, currency = row_currency)`.
- Convert: `amount_usd = (amount_minor / 100.0) * fx_rates.usd_per_unit`.
- When both refund and order are in the same non‑USD currency, both are multiplied by the same FX rate for comparison, so the relative comparison is preserved.
- Round final reported USD amounts to the decimal places specified in the answer template.

## Correction Workflow

When the task describes a data correction with an approved audit record:

1. Identify the exact contradiction from the data (e.g., raw status ≠ canonical status).
2. The `/api/sql/transaction` endpoint accepts only `INSERT` statements into the `correction_audit` table. `UPDATE` statements against business tables are rejected.
3. Insert one audit row containing all required fields: `audit_id`, `correction_key`, `entity_type`, `entity_id`, `source_row_id`, `field_name`, `old_value`, `new_value`, `reason_code`, `corrected_at`, `actor`.
4. The audit record **is** the correction — check `GET /api/correction-audit` afterwards to confirm it was recorded.
5. When computing post‑correction state, apply the audit record's `new_value` as an override for the specified `(source_row_id, field_name)`.
6. Set `correction_status` to `"APPLIED"` when exactly one audit row committed and a post‑change query confirms the corrected value through the audit table.

## Query Strategy

- The `/api/sql` endpoint returns at most 5000 rows. When a result set would exceed this, use **aggregation** (`COUNT`, `SUM`, `GROUP BY`) to push computation into the database.
- For data that must be fetched row‑by‑row, **batch** queries using `WHERE … IN ('id1','id2',…)` with 500–800 IDs per batch, then merge in the host language.
- Avoid deeply nested subqueries — the endpoint may reject them. Prefer simple `JOIN` … `GROUP BY` patterns or pull data in stages.
- SQLite's `GROUP BY` may return an arbitrary value for non‑aggregated columns when a strict mode is not enforced. Always use a deterministic method (row‑id tie‑break after fetching) rather than relying on `GROUP BY` alone for the status column.

## General Workflow

1. **Read the request payload** — it contains the exact business definitions, scope boundaries, rounding rules, and status‑classification rules. Every term in the payload has a precise meaning; do not substitute a generic interpretation.
2. **Read the answer template** — the output must conform exactly to its `required` fields, `type` constraints, `enum` values, `pattern` restrictions, and `additionalProperties: false`.
3. **Explore the data** with small, focused queries before attempting the full computation.
4. **Build incrementally** — verify intermediate counts (e.g., eligible population size, status distributions) before computing derived metrics.
5. **Match rounding and ordering** — round only final reported values to the specified decimal places; use unrounded values for intermediate sorting and comparisons unless the request says otherwise.
6. **Sort arrays** exactly as specified (ascending IDs, ranked metrics with tie‑breaks).
