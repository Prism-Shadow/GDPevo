---
name: atlas-ops
description: Business analytics and data-quality correction workflows against the Atlas Commerce Operations database. Use when working with the Atlas task environment endpoint to: (1) compute fulfillment, refund, warehouse, or support metrics from structured JSON request definitions, (2) run read-only analytical SQL queries via POST /api/sql, (3) apply controlled canonical data corrections via POST /api/sql/transaction with audit verification, (4) produce an exact-template JSON answer with no extra commentary. Triggers on tasks that mention Atlas Commerce Operations, `<TASK_ENV_BASE_URL>`, or the Atlas API endpoints.
---

# Atlas Commerce Operations

Workplace API for the Atlas Commerce Operations database. Provides read-only SQL
analysis, controlled data correction transactions, and live schema introspection.

## Quick start

1. Read every attached request JSON file — it defines scope, business rules, and
   required output exactly.
2. Read the attached answer template JSON — it defines the output structure,
   types, and constraints.
3. Call `GET /api/schema` and `GET /api/data-dictionary` to understand available
   tables, columns, and business meanings.
4. Design and run `POST /api/sql` queries to gather the raw data needed.
5. Compute results in code using the exact business definitions from the request.
   Do not approximate or reinterpret — the request text is authoritative.
6. Write the final JSON object to `answer.json` matching the template exactly.
   No extra commentary, no wrapping object, no extra fields.

## Environment setup

The base URL is always provided as `<TASK_ENV_BASE_URL>` in the prompt.
Substitute it into every API call. Use these headers:

```
Authorization: Bearer atlas-ops-token-022
Content-Type: application/json
```

## API reference

See [references/api.md](references/api.md) for full endpoint documentation and
request/response shapes.

## Schema reference

See [references/schema.md](references/schema.md) for table DDL, column
descriptions, and join relationships. Always verify against the live
`GET /api/schema` and `GET /api/data-dictionary` responses — the reference is a
snapshot that may drift.

## Critical conventions

### Production population

Business requests scope production data. Always exclude test and internal
accounts:

```sql
JOIN accounts a ON ... AND a.is_internal = 0 AND a.is_test = 0
```

`is_internal` and `is_test` are integer booleans (1 = true, 0 = false).

### Timestamps

All stored timestamps use ISO-8601 UTC ending in `Z`. Calendar dates use
`YYYY-MM-DD`. Window boundaries are inclusive unless a request explicitly says
otherwise. Compare timestamps lexicographically as strings.

### Money

- Columns ending in `_minor` hold values in the smallest unit of the row currency
  (e.g., cents for USD). Divide by 100 to get display amounts.
- Convert to USD with `fx_rates.usd_per_unit` matching the row's `currency` and
  the relevant date column (usually `service_date`).
- Round only final monetary values to the decimal places specified in the request.

### "Effective" filtering

When a request uses the word "effective" (e.g., "effective settled logical
refund"), filter for meaningful records before computing:

- **Refunds**: `status = 'SETTLED'` for effective settlements.
- **Reversals**: Effective settled rows where `linked_refund_id IS NOT NULL`.
- **Carrier scans**: The effective final scan per shipment is the latest by
  `canonical_event_at`. Tie-break on `scan_row_id` ascending.
- **Shipment completion**: An order is complete when it has at least one
  shipment and every shipment's effective final carrier scan has
  `canonical_status = 'DELIVERED'` at or before the cutoff.

### Ranking and sort stability

Multi-key ordering applies sorts in priority order. Tie-breakers are always
identifier ascending unless specified otherwise. For top-N lists, compute the
metric for every candidate, apply the full sort, and take the first N.

### Status and risk classification

Requests define tiered rules in order. Evaluate them sequentially and use the
first rule whose conditions are fully satisfied. The final rule (often labeled
"otherwise") is the catch-all.

### Rounding

Round only final reported rates and monetary amounts. Keep intermediate values
at full precision. The request specifies decimal places per metric; round to
that many places at the end.

## Domain workbooks

See [references/patterns.md](references/patterns.md) for methodology covering:

- Fulfillment campaign scorecards (order-to-shipment completion, on-time
  delivery, regional rates, severe exceptions)
- Refund settlement reconciliation (FX conversion, leakage detection, reason
  ranking, cohort risk)
- Carrier quality correction (contradiction detection, canonical UPDATE via
  transaction, audit verification, pre/post backlog analysis)
- Warehouse productivity (task completion, employee and team ranking, delayed
  high-priority tasks, facility status)
- Support health review (SLA breach computation from event history, active-time
  clock, severe case identification, median, account prioritization)

## Answer format

Always write exactly one JSON object to `answer.json`. It must conform to the
`answer_template.json` bundled with the task. No narrative text, no extra keys,
no wrapping envelope.
