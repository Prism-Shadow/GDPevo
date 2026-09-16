---
name: atlas-ops
description: Operational analytics, metric computation, and controlled data corrections against an Atlas Commerce Operations database. Use when Codex needs to query a live Atlas schema, compute business scorecards (fulfillment rates, refund reconciliation, warehouse productivity, carrier quality, support health), execute controlled canonical-field corrections with audit records, or reason over an Atlas data dictionary to derive operational metrics from SQL results. The database is accessed through authenticated HTTP endpoints (schema, data dictionary, read-only SQL, transactional SQL, correction audit).
---

# Atlas Ops

Analyze operational data and apply controlled corrections in an Atlas Commerce Operations database. The database is accessed through a set of authenticated HTTP endpoints with a bearer token.

## Endpoints

All requests use this authorization header:

```
Authorization: Bearer atlas-ops-token-022
```

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/schema` | Full DDL for every table and index |
| GET | `/api/data-dictionary` | Column descriptions and data conventions |
| POST | `/api/sql` | Read-only analytical queries (JSON body with `sql` field) |
| POST | `/api/sql/transaction` | Controlled single-commit SQL transaction wrapped with audit |
| GET | `/api/correction-audit` | Read all committed correction audit records |

The SQL endpoints return JSON with `columns`, `rows`, `row_count`, and `truncated` fields. Never assume truncation; check the flag.

## Data Conventions

See [references/data-conventions.md](references/data-conventions.md) for the full conventions document extracted from the data dictionary. Key points:

- All timestamps use ISO-8601 UTC text ending in `Z`.
- Calendar dates use `YYYY-MM-DD` text.
- Monetary amounts are in the **smallest unit** of the row currency (e.g., cents). Divide by 100 to get major-unit values.
- FX rates are stored in `fx_rates(rate_date, currency, usd_per_unit)` — multiply the minor-unit amount by `usd_per_unit` and then divide by the minor-unit factor to get USD.
- Integer booleans: 1 means true, 0 means false.
- `is_internal`, `is_test` columns on `accounts` exclude non-production accounts.

## Schema

See [references/schema.md](references/schema.md) for the complete table catalog with DDL and column descriptions. Always read it before writing queries. The tables are:

- **accounts** — Customer accounts with segment, tier, region, currency, and production flags
- **campaigns** — Campaign names and active windows
- **carrier_scans** — Raw and canonical carrier scan events per shipment
- **case_events** — Append-only support case lifecycle events
- **correction_audit** — Public audit records for canonical corrections
- **employees** — Warehouse employees with team, role, and active periods
- **fx_rates** — Daily FX rates as USD per currency unit
- **inventory_movements** — Stock movements with raw and canonical quantities
- **inventory_snapshots** — Periodic stock and reservation snapshots
- **order_events** — Append-only order lifecycle events
- **order_lines** — SKU quantities per order
- **orders** — Order headers with campaign, warehouse, currency, and gross amount
- **payment_events** — Payment authorization, settlement, void, reversal events
- **products** — SKU master with weight and case-pack
- **refund_attempts** — Provider refund attempts with status, reason, amount, and linked reversals
- **shipments** — Physical shipments with carrier, warehouse, and promised delivery
- **source_import_batches** — Source ingestion batch metadata
- **support_cases** — Support case headers with priority, status, and owner team
- **warehouse_task_events** — Append-only task execution events with units and productive minutes
- **warehouse_tasks** — Warehouse work assignments with priority, work class, and planning
- **warehouses** — Facility master with region and timezone

## Analytical Patterns

See [references/patterns.md](references/patterns.md) for reusable query patterns covering the five core domains. Each pattern is derived from real Atlas analytical workflows:

1. **Fulfillment Scorecards** — Campaign-scoped order completion, on-time rates, worst regions, severe exceptions
2. **Refund Reconciliation** — Account-tier refund settlement, FX conversion, leakage detection, reason ranking
3. **Carrier Quality Correction** — Canonical-field contradiction detection, transactional correction, backlog analysis
4. **Warehouse Productivity** — Task completion, employee units-per-hour ranking, rework rates, delayed priorities
5. **Support Health** — SLA breach detection, worst accounts, median resolution time, risk classification

## Transactional Corrections

When the task requires a controlled data correction with audit, use `POST /api/sql/transaction`. The endpoint accepts a JSON body:

```json
{
  "sql": "<single SQL statement>",
  "audit": {
    "audit_id": "<unique>",
    "correction_key": "<idempotency key>",
    "entity_type": "<e.g. carrier_scan>",
    "entity_id": "<business entity id>",
    "source_row_id": "<row being corrected>",
    "field_name": "<column name>",
    "old_value": "<text>",
    "new_value": "<text>",
    "reason_code": "SOURCE_RECONCILIATION",
    "corrected_at": "<ISO-8601>",
    "actor": "<actor id>"
  }
}
```

The transaction commits exactly one SQL statement and one audit record together atomically. After committing, verify the correction by re-querying the affected row and by checking `/api/correction-audit` for the audit record.

## Workflow

1. Read the task payload (JSON request file) for scope, definitions, and output contract
2. Read the answer template for the required output shape
3. Read [references/schema.md](references/schema.md) to understand available tables
4. Read [references/data-conventions.md](references/data-conventions.md) for data rules
5. Query `GET /api/schema` and `GET /api/data-dictionary` at runtime if needed for live context
6. Build and execute analytical queries through `POST /api/sql`
7. Compute derived metrics from query results per the business definitions in the request
8. For corrections: use `POST /api/sql/transaction`, then verify via `POST /api/sql` and `GET /api/correction-audit`
9. Write the final JSON output to the specified file, conforming exactly to the answer template

## Critical Rules

- **Effective deduplication**: When tables have `source_system` + `external_event_id` + `ingested_at` indexes, deduplicate by keeping the row with the latest `ingested_at` per `(source_system, external_event_id)` pair.
- **Effective event selection**: For append-only event tables (`order_events`, `case_events`, `warehouse_task_events`), when computing the latest state, select the event with the latest `event_at` per entity, breaking ties with the latest row identifier.
- **Carrier scan effective state**: Per shipment, use the scan with the latest `canonical_event_at`, breaking ties with the latest `scan_row_id`.
- **Production scoping**: Always filter accounts with `is_internal = 0 AND is_test = 0` unless the request explicitly scopes differently.
- **Rounding**: Apply rounding only to final reported values, never to intermediate computations.
- **Sorting stability**: When ranking requires tie-breaking, always include the tie-break column in the ORDER BY clause.
- **Money conversion**: See [references/data-conventions.md](references/data-conventions.md) for the exact FX conversion formula.
- **Answer template compliance**: The output must exactly match the template's `required`, `additionalProperties`, and `properties` constraints. No extra fields, no missing fields.

## Common Pitfalls

- **Forgotten timezone filtering**: Campaign windows are UTC. Cutoff timestamps are UTC. Always compare directly.
- **Double-counting refunds**: Deduplicate refund_attempts by `(source_system, external_event_id)` before analysis.
- **Incomplete order detection**: An order with zero shipments is incomplete regardless of its `current_status` field (the status field is a snapshot that may lag).
- **SLA clock**: Support SLA calculations use active time (time spent in agent-facing states), not wall clock. The `case_events` table records state transitions — compute active time as the sum of time spent in states where the `actor_type` is not `SYSTEM`.
- **Even-count median**: For an even number of values, compute the average of the two central values.
- **Null shipment promises**: When computing severe exceptions, an incomplete order with no shipment promise does not count toward the "cutoff > 24h after promise" condition.
