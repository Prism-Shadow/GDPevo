---
name: atlas-ops-analytics
description: Solve Atlas Commerce Operations analytical and controlled-correction tasks that provide a prompt, request payload, JSON answer contract, schema/data dictionary access, and SQL-style workplace data. Use for fulfillment, refund, carrier-scan, warehouse productivity, support health, or similar operational scorecards requiring exact JSON output, event-derived state at a cutoff, imported-row deduplication, FX conversion, risk classification, ranked exceptions, or approved canonical data corrections.
---

# Atlas Ops Analytics

## Core Workflow

1. Read the prompt, request payload, and answer template before querying data. Treat the payload as the business contract and the template as the output contract.
2. Inspect the schema and data dictionary supplied by the task. Prefer canonical fields for analytics; use raw fields only for source-reconciliation checks.
3. Build the cohort first, then calculate metrics from that cohort. Apply production filters from account flags when the request says production accounts, production orders, production shipments, or production customers.
4. Use UTC timestamp boundaries exactly as stated. Respect inclusive, exclusive, and "strictly before" language.
5. Deduplicate imported event or attempt rows before aggregation when source identity fields can repeat. Use `(source_system, external_event_id)` with latest `ingested_at`, then stable row id as a tie-breaker, unless the business entity has a stronger logical id such as `refund_id`.
6. Derive state at a cutoff from effective event history when event tables and snapshot columns disagree or when the request says "effective", "at cutoff", "active at cutoff", or "completed by cutoff".
7. Calculate rankings and classifications from unrounded values. Round only final reported numbers to the requested precision.
8. Validate the final object against the answer template: exact fields only, required array lengths, stable sort order, numeric precision, and no narrative.

## Cohorts And State

- Production account data: exclude `is_internal = 1` and `is_test = 1` unless the request defines production differently.
- Campaign/order cohorts: join through the campaign or account dimensions requested, then apply the campaign or opened/created window exactly.
- Shipment state: for "effective final carrier status", use the latest canonical carrier scan at or before the cutoff, ordered by event timestamp then stable scan row id. Shipment completion usually requires every associated shipment in the cohort to have final `DELIVERED` status by the cutoff.
- Warehouse task state: use deduped `warehouse_task_events` at or before the state cutoff. `COMPLETED` events establish completed tasks, completed units, productive minutes, and delayed-task exclusions. `REWORK` events establish rework tasks.
- Support case state: use deduped lifecycle events at or before the cutoff for active/resolved state when available. Treat `OPENED`, `OPEN`, `CUSTOMER_REPLIED`, and `WAITING_CUSTOMER` as open state labels, `REOPENED` as reopened, and `RESOLVED` as resolved.

## Business Calculations

- Rates: keep incomplete or unresolved entities in denominators when the request says the denominator is the eligible population.
- Exceptions: create boolean flags per entity, then aggregate counts and sorted id lists from those flags. Preserve "more than", "at least", and threshold strictness exactly.
- Worst/best lists: compute per-group unrounded metrics, sort by the requested primary metric and tie-breakers, then round only displayed values.
- Money: convert minor units to major units before applying FX. Use the row's service date and currency. For refunds, dedupe settled logical refunds by `refund_id`, subtract linked reversal rows, normalize reason codes, and compare net order refund value after reversals to the order gross value using the request's FX basis.
- Medians: sort the resolved values; for an even count, average the two middle values; round the final median only.
- Risk/status labels: evaluate rules in priority order and use unrounded rates and amounts.

## Controlled Corrections

Only mutate data when the prompt explicitly requests an approved correction.

1. Identify the single scoped contradiction from raw versus canonical fields using the request's batch, entity, warehouse, and cutoff.
2. Capture pre-correction metrics before mutating.
3. Apply the minimal guarded update to canonical fields and correction metadata only. Do not alter raw source values, event timestamps, source-system identifiers, or unrelated rows.
4. Insert exactly one correction audit row using the approved audit identifiers. Use the source entity type from the import batch when available; use the affected business id as `entity_id` and the corrected source row id as `source_row_id`.
5. Verify the mutation by reading back the corrected value, audit row, and post-correction metric. Report an applied status only when the requested success rule is satisfied.

## Output Discipline

- Write the final answer as one JSON object matching the template.
- Use stable ascending order for id arrays unless another order is explicitly requested.
- Use requested tie-breakers for ranked arrays; do not rely on database default ordering.
- Do not include commentary, provenance notes, query text, or intermediate values in the answer.
