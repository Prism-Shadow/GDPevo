---
name: atlas-commerce-ops
description: Solve Atlas Commerce Operations workplace tasks that require reading local prompt and payload contracts, using the authenticated task environment APIs for schema, data dictionary, SQL analysis, controlled SQL transactions, and correction-audit verification, then writing an exact answer.json. Use for cutoff-based operational scorecards, refund reconciliation, carrier quality corrections, warehouse productivity reviews, support health reports, and similar Atlas Commerce database reporting or minimal audited correction tasks.
---

# Atlas Commerce Operations

## Core Contract

- Read the full prompt and every file under `input/payloads/` before querying or writing output.
- Treat the request payload as the business contract and the answer template as the output schema contract. Do not add commentary or extra fields to `answer.json`.
- Read `environment_access.md` for the base URL, authorization header, and allowed endpoints. Use no other network source unless the task explicitly extends access.
- Inspect `GET /api/schema` and `GET /api/data-dictionary` before writing SQL. Prefer discovered table and column names over assumptions from prior tasks.
- Use read-only SQL for analytical requests. Use the transaction endpoint only when the prompt explicitly requests a data correction.
- Preserve exact UTC boundaries from the request. Respect whether each window is inclusive or strict.
- Keep unrounded values through ranking and classification. Round only final reported numbers to the precision required by the answer template or request.

## API Workflow

Use the service details from `environment_access.md`:

```bash
BASE_URL="$(awk -F= '/_BASE_URL=/ {print $2}' environment_access.md)"
AUTH_HEADER="$(awk -F': ' '/^Authorization:/ {print $0}' environment_access.md)"
curl -sS -H "$AUTH_HEADER" "${BASE_URL%/}/api/schema"
curl -sS -H "$AUTH_HEADER" "${BASE_URL%/}/api/data-dictionary"
curl -sS -H "$AUTH_HEADER" -H 'Content-Type: application/json' \
  -d '{"sql":"select 1"}' "${BASE_URL%/}/api/sql"
```

When the output depends on data mutation, make a pre-change query, submit one minimal transaction, then verify with a post-change query and the correction-audit endpoint. If any success condition fails, report the observed result and use the request's failure status.

## SQL Construction

- Build queries with CTEs that mirror the request: `params`, eligible cohort, event/state rows through cutoff, per-entity rollups, final metrics.
- Anchor cohort membership on the requested production population, account tier/segment/region, campaign, facility, warehouse, batch, created/opened/service date window, and cutoff.
- Derive state at cutoff from records effective at or before the cutoff. Exclude future events unless the request explicitly asks otherwise.
- Count distinct business entities at the level named by the output field: orders, logical refunds, linked reversals, shipments, tasks, units, employees, teams, accounts, or cases.
- Use `CASE` expressions for status/risk policies exactly in priority order. Apply the first qualifying status.
- For arrays, sort in SQL using the request's stated primary ordering and tie breakers, then serialize only the requested identifiers or objects.
- Validate edge cases deliberately: no shipment, no promise, unreversed refund, active case without response/resolution, reopened case, equal ranking metrics, even-count median.

## Analytical Patterns

Fulfillment scorecards:
- Eligible orders usually come from production orders tied to a named campaign and created during the campaign's active window.
- A complete order requires at least one physical shipment and every physical shipment effectively delivered by the cutoff.
- On-time completion requires every delivered shipment to be delivered no later than its own promise.
- Severe exceptions usually include incomplete orders more than 24 hours past the latest shipment promise, plus completed orders with any shipment more than 24 hours late. Do not mark a no-promise incomplete order severe unless the request says so.
- Regional rollups use the assigned warehouse region, with incomplete orders retained in the denominator.

Refund reconciliation:
- Determine eligible refunded orders from effective settled logical refunds inside the requested service-date window and account population.
- Convert refunds, reversals, and comparison order gross to USD using the daily FX rate for the relevant service date and row currency.
- Net refund exposure is settled logical refund value minus linked effective reversals.
- Leakage candidates may be value-based or duplicate-reason based; apply all candidate tests and output distinct order IDs sorted by the contract.
- Rank reason codes by effective net USD descending, then normalized reason code ascending.

Warehouse productivity:
- Select eligible production tasks by warehouse and task-created window; evaluate state at the separate state cutoff.
- Completion rate uses completed eligible production-task count over all eligible production tasks.
- Units per hour is completed units divided by productive minutes attached to those units, multiplied by 60.
- Rework rate uses rework task count over eligible production tasks.
- Delayed high-priority tasks are HIGH or URGENT, due strictly before cutoff, and not completed by cutoff.
- Lowest-performing teams rank by completion rate ascending, then team ID ascending.

Support health:
- Select eligible cases by production account scope, segment, region, and opened window.
- Open at cutoff includes open and reopened active states; reopened is a subset.
- Use support active time, not plain wall-clock time, for first-response and resolution thresholds when active-time records are available.
- For unresponded cases, compare active elapsed time at cutoff to the first-response threshold. For active unresolved cases, compare active elapsed time at cutoff to the resolution threshold.
- Severe active cases are open or reopened at cutoff, priority URGENT or HIGH, and beyond the active-time resolution threshold.
- Median active resolution hours is calculated over eligible cases resolved at cutoff; average the two central values for an even count.
- Worst accounts rank by severe active case count descending, active-clock breach count descending, then account ID ascending.

## Controlled Corrections

Use this path only for explicit data-quality correction tasks:

1. Identify the single contradictory business row from raw value, canonical value, source row identity, batch/scope, and cutoff rules.
2. Query and record the requested pre-correction metric.
3. Mutate only the approved canonical field. Do not change raw source values, source identity fields, or unrelated rows.
4. Insert exactly the approved audit record fields from the request, including audit ID, correction key, entity type, entity ID, source row ID, field name, old value, new value, reason code, corrected timestamp, and actor.
5. Commit the business update and audit insert in one transaction.
6. Verify affected business rows, audit row count, corrected canonical value, post-correction metric, and correction-audit visibility.
7. Report `APPLIED` only when the request's success rule is fully satisfied; otherwise report `NOT_APPLIED` with observed counts and values.

## Output Discipline

- Create `answer.json` in the task working directory, not inside the input directory.
- Emit exactly one JSON object conforming to the answer template. Watch for template spelling such as `additionalProperties` versus `additional_properties`; the output still follows the listed `required` and `properties`.
- Keep identifiers stable and sorted as specified. Use empty arrays only when allowed by the schema and business contract.
- Use JSON numbers for numeric fields, not strings. Match requested decimal places or multiples.
- Before finalizing, re-open `answer.json` and check every required field, enum, array length, uniqueness rule, sort order, and rounding rule against the template.
