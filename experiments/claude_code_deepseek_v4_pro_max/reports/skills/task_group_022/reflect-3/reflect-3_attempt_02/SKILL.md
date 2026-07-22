# Atlas Commerce Operations — Analytical Task Solver

## Purpose

Solve operational analytics tasks against the Atlas Commerce Operations database. Each task provides a business request payload and an answer template; you query the authenticated API, compute the requested metrics, and return a JSON answer matching the template exactly.

## Workflow

### Phase 1 — Understand the request

1. Read `prompt.txt` (or equivalent) for the task narrative and scope.
2. Read the request payload (usually `payloads/*_request.json`) for business definitions, date boundaries, thresholds, and ranking rules.
3. Read the answer template (`payloads/answer_template.json`) for the exact output schema. Note every `required` field, type constraint, enum, pattern, and ordering rule.

### Phase 2 — Explore the data model

Call these endpoints first (no data changes):

```
GET {BASE_URL}/api/schema
GET {BASE_URL}/api/data-dictionary
```

From the schema, identify:
- Which tables hold the core entities (orders, shipments, refunds, tasks, cases).
- Foreign-key relationships (e.g., `orders.account_id → accounts.account_id`).
- Deduplication indexes (any index on `source_system, external_event_id` signals duplicate ingestion).
- Snapshot vs. append-only fields (fields described as "Convenience snapshot that may lag" must not be used for time-sensitive determinations).

From the data dictionary, confirm:
- Monetary fields use the smallest currency unit (minor units).
- `FX` rates are stored as `usd_per_unit` (USD per one unit of the named currency).
- Timestamps are ISO-8601 UTC; calendar dates are `YYYY-MM-DD`.

### Phase 3 — Query and deduplicate

Every source/event table (`carrier_scans`, `refund_attempts`, `warehouse_task_events`, `case_events`, `inventory_movements`, `order_events`, `payment_events`) can contain duplicate rows from re-ingestion. **Always deduplicate**:

```sql
-- Preferred: keep the latest ingested row per source event
SELECT ...
FROM some_table t
WHERE t.row_id_column IN (
  SELECT MAX(t2.row_id_column)
  FROM some_table t2
  GROUP BY t2.source_system, t2.external_event_id
)
```

If the subquery is rejected by the API, pull all rows and deduplicate in client code: group by `(source_system, external_event_id)`, keep the row with the maximum `ingested_at` (or maximum row-ID as tiebreaker).

Deduplication must happen **before** any aggregation, status determination, or metric computation.

### Phase 4 — Determine effective state from events

When a business question asks for state "at cutoff" or "effective final" status:

1. Collect all deduplicated events for each entity **with `event_at <= cutoff`**.
2. Sort events by `event_at` ascending.
3. The **effective status at cutoff** is the status of the last event before (or at) the cutoff.

For carrier scans specifically:
- Use `canonical_status` and `canonical_event_at` (the normalized operational values), not `raw_status`.
- A shipment is "delivered" only if there exists a deduplicated scan with `canonical_status = 'DELIVERED'` and `canonical_event_at <= cutoff`.
- For on-time checks, compare the delivery `canonical_event_at` against the shipment's `promised_delivery_at`.

For refunds:
- A logical refund is identified by `refund_id` (not `refund_row_id`).
- "Effective settled" means the deduplicated row has `status = 'SETTLED'`.
- "Unreversed" means no other deduplicated row has `linked_refund_id` pointing to this refund's `refund_id`.
- A reversal is a row where `linked_refund_id IS NOT NULL`; these always have `status = 'REVERSED'`.

For warehouse tasks:
- Task statuses include `COMPLETED`, `CREATED`, `IN_PROGRESS`, and `REWORK`.
- "Rework tasks" are identified by `current_status = 'REWORK'` (not by `task_type`).
- For employee productivity, sum `units` from **only `COMPLETED` event-type rows** (after dedup) attached to completed tasks, and `productive_minutes` from the same rows.

For support cases:
- Derive the active/inactive state from the latest event before cutoff. A case resolved before cutoff is "resolved"; any other last-event status (`OPEN`, `REOPENED`, `AGENT_RESPONDED`, `ASSIGNED`, etc.) means the case is still open.
- `REOPENED` is a subset of open-at-cutoff.
- "Active elapsed time" for breach checks: for cases with a timestamped milestone (first response, resolution), use `milestone_at − opened_at`. For cases missing the milestone, use `cutoff − opened_at`.

### Phase 5 — Apply business rules and compute metrics

Follow the request payload's `business_definitions` / `reporting_definitions` literally:

- **Monetary conversion**: `(amount_minor / 100.0) × fx_rates.usd_per_unit` for the refund's `service_date` and `currency`. Round displayed USD to 2 decimal places. Cap net amounts at 0 (the template's `minimum: 0` constraint).

- **Rates**: Divide the qualifying count by the eligible population. Round **only the final reported rate** to the specified decimal places. When ranking (e.g., worst regions by rate), use **unrounded** values for the sort key, then apply rounding for display.

- **Ranking / ordering**: Follow the request's sort specification exactly (e.g., "by X descending, then Y ascending"). For top-N or bottom-N, use the unrounded values for comparison.

- **Severe-exception / leakage / breach logic**: Apply the request's conditional rules exactly. Boolean integer fields (`is_internal`, `is_test`) use `0` for false and `1` for true.

- **Status tiers**: Evaluate conditions in the order specified. Use a fallback / "otherwise" tier when no earlier condition matches.

### Phase 6 — Build and validate the answer

1. Construct a JSON object that matches every field in the answer template.
2. Ensure `additionalProperties: false` — do not include extra keys.
3. Integers must be integers (no floats for counts).
4. Rates must be numbers with the exact decimal precision specified (`multipleOf` in the template schema).
5. Arrays must have the exact `minItems`/`maxItems` length, with `uniqueItems: true` where specified, and the correct sort order.
6. Enum fields must use one of the listed values exactly.
7. String patterns (regex) must be satisfied.

Write the result to `answer.json` with no commentary outside the JSON document.

## Common pitfalls

| Pitfall | Correction |
|---|---|
| Using raw `current_status` snapshot for time-sensitive state | Derive effective state from deduplicated events with `event_at <= cutoff` |
| Not deduplicating source tables | Always dedup by `(source_system, external_event_id)` before any computation |
| Dividing minor-currency amounts by 100 for all currencies | Confirm the data dictionary: monetary minor fields use the smallest unit of the row currency; divide appropriately |
| Rounding intermediate values | Only round final reported values; sort and rank with unrounded numbers |
| Capping net amounts per-entity instead of total | Sum all values first, then apply `max(0, total)` at the end |
| Including extra fields in the answer | Match the answer template exactly — no additional properties |
| Using `task_type = 'REWORK'` for rework identification | Use `current_status = 'REWORK'` — rework is a status, not a task type |
| Confusing `shipped_at` with delivery time | Use `carrier_scans.canonical_event_at` for the actual delivery timestamp |
