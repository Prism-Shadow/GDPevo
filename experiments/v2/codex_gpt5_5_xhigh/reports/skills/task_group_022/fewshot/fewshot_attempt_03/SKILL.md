---
name: atlas-commerce-ops-analytics
description: Use for Atlas Commerce Operations tasks that provide local prompt and payload JSON files, require authenticated schema/data-dictionary/SQL analysis through environment_access.md, and need an exact JSON answer or an approved minimal correction with audit verification.
---

# Atlas Commerce Ops Analytics

Use this skill for cutoff-based operational analyses in the Atlas Commerce Operations workplace: fulfillment scorecards, refund reconciliations, carrier quality corrections, warehouse productivity reviews, support-health reviews, and close variants over the same schema.

## Non-Negotiables

- Read the prompt and every file under `input/payloads/` before querying. The request payload and `answer_template.json` are the source of truth for scope, dates, rounding, ordering, risk/status rules, required fields, and output filename.
- Read `environment_access.md` for the base URL, authorization header, and allowed endpoints. Use no other network source.
- Fetch both `GET /api/schema` and `GET /api/data-dictionary` before writing final SQL. They define table relationships, timestamp conventions, source/canonical fields, and snapshot caveats.
- Use `POST /api/sql` for analysis. Its response has `columns`, `rows`, `row_count`, and `truncated`; map columns by name and rerun narrower queries if `truncated` is true.
- Use `POST /api/sql/transaction` only when the request explicitly asks for a correction. Never mutate analytical-only tasks.
- The final response must be exactly the JSON object described by the local answer template: no narrative, no extra fields, correct types, exact array ordering, and final rounding only.
- Do not reuse prior task answers or copy observed answer values. Recompute every value from the current payload and database state.

## Standard Workflow

1. Inventory and read inputs:
   - `prompt.txt`
   - all request JSON files under `input/payloads/`
   - `input/payloads/answer_template.json`
2. Parse runtime access from `environment_access.md`; export local shell variables if useful:
   - `BASE_URL`
   - `Authorization` header value
3. Retrieve schema context:
   - `GET $BASE_URL/api/schema`
   - `GET $BASE_URL/api/data-dictionary`
4. Convert the request payload into SQL constants: exact UTC cutoffs, inclusive or exclusive boundaries, cohort filters, thresholds, status rules, and output order rules.
5. Build SQL as small verifiable CTEs. Query intermediate counts and boundary rows before computing the final object.
6. Independently cross-check totals from at least one alternate aggregation when practical: cohort count, denominator, numerator, exception list count, and any ranked list.
7. Write `answer.json` as strict JSON matching the template. Validate it with `python -m json.tool answer.json` and, when available, a JSON Schema validator.

## API Patterns

Use placeholders from `environment_access.md`; do not hardcode training credentials into reusable work.

```bash
curl -sS -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/schema"
curl -sS -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/data-dictionary"
curl -sS \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sql":"SELECT COUNT(*) AS n FROM orders"}' \
  "$BASE_URL/api/sql"
```

For correction tasks, submit one controlled transaction containing exactly the approved business-row update and the matching `correction_audit` insert, using the endpoint's supported transaction request shape. Then verify with read-only SQL and `GET /api/correction-audit`.

## SQL Construction Rules

- Stored timestamps are ISO-8601 UTC text. Use the request boundary exactly; for inclusive end bounds use `<=`, for exclusive bounds use `<`.
- Production account filters normally mean `accounts.is_internal = 0` and `accounts.is_test = 0`; still honor any narrower request scope such as tier, segment, region, campaign, warehouse, or date window.
- Prefer event history for cutoff state. Snapshot columns such as `current_status` are convenient but may lag append-only events.
- Imported event tables may contain retry copies. When the task says effective rows, dedupe by `(source_system, external_event_id)` using the latest `ingested_at`, then a stable row id as tie-breaker.
- For as-of state, after dedupe choose the latest event per entity at or before the cutoff using the event timestamp and row id tie-breaker.
- Ranking must use unrounded values. Round only final reported rates or amounts to the precision in the request/template.
- Sort ID lists exactly as requested, usually ascending. For ranked arrays, apply every tie-breaker from the payload.

Typical effective-event CTE:

```sql
WITH dedup AS (
  SELECT e.*,
         ROW_NUMBER() OVER (
           PARTITION BY e.source_system, e.external_event_id
           ORDER BY e.ingested_at DESC, e.event_at DESC, e.<row_id> DESC
         ) AS dedupe_rn
  FROM <event_table> e
  WHERE e.event_at <= :cutoff
),
effective_events AS (
  SELECT *
  FROM dedup
  WHERE dedupe_rn = 1
),
latest_state AS (
  SELECT *,
         ROW_NUMBER() OVER (
           PARTITION BY <entity_id>
           ORDER BY event_at DESC, <row_id> DESC
         ) AS state_rn
  FROM effective_events
)
SELECT *
FROM latest_state
WHERE state_rn = 1;
```

For carrier scans, use `canonical_event_at` and `scan_row_id` in the state ordering. Keep raw source fields immutable.

## Domain Recipes

### Fulfillment Scorecards

- Cohort: eligible production orders from the requested campaign/window/scope. Join `orders`, `accounts`, `campaigns`, and `warehouses`.
- Shipment completeness: an order is complete only if it has at least one shipment and every associated shipment has effective final carrier status `DELIVERED` by the cutoff.
- On-time completion: all associated shipments were delivered no later than their `promised_delivery_at`.
- Exceptions: implement the request's lateness or incomplete rules against shipment promises and delivered timestamps. Incomplete orders with no relevant promise should follow the payload's explicit exception rule.
- Region rollups: use the order warehouse region. Rank worst regions by unrounded rate, then the requested textual tie-breaker.

### Refund Reconciliations

- Cohort: production accounts plus the requested tier/segment/date scope. Join `accounts`, `orders`, `refund_attempts`, `payment_events` only if the payload requires payment settlement context, and `fx_rates`.
- Effective settled logical refunds: dedupe source rows, keep settled refund outcomes in the service-date window, and count distinct logical refund identifiers according to the payload.
- Linked reversals: count effective reversal rows linked to in-scope logical refunds and subtract their USD value from settled refund USD.
- FX: convert row minor amounts to major currency units, then multiply by `fx_rates.usd_per_unit` for the row service date and currency. Apply the same service-date FX basis to order gross comparisons when requested.
- Normalize reason codes with `UPPER(TRIM(reason_code))`. Rank reasons by net USD descending and then reason code ascending unless the payload says otherwise.
- Leakage candidates: implement every candidate condition from the payload, such as net refund value exceeding gross value or multiple unreversed settled logical refunds with the same normalized reason.

### Carrier Quality Corrections

- First compute the pre-correction cohort and backlog from effective carrier scans in the named batch/warehouse/cutoff.
- Identify the single raw/canonical contradiction by comparing the raw carrier status to the expected canonical status within the approved cohort. Confirm the target row, shipment, old canonical value, and new canonical value before mutating.
- Apply only the approved minimal canonical correction. Do not change raw status, raw timestamps, source system, external IDs, import batch IDs, or unrelated rows.
- Insert exactly one audit record using the request's approved audit metadata. The audit record must describe the business entity, source row, field name, old value, new value, reason code, timestamp, and actor.
- After the transaction, verify:
  - exactly one business row was affected
  - exactly one audit row was inserted or already present through idempotency
  - the target canonical field now has the approved value
  - post-correction backlog/delivered counts are recomputed from the database
- Report `APPLIED` only if the request's success rule is satisfied; otherwise report `NOT_APPLIED` with observed counts.

### Warehouse Productivity

- Cohort: `warehouse_tasks` in the requested warehouse, creation window, and `work_class = 'PRODUCTION'`.
- Cutoff completion: derive completed state from deduped `warehouse_task_events` at or before the state cutoff.
- Completed production units and productive minutes come from completed task events for eligible tasks through the cutoff. Units per hour is `units / productive_minutes * 60`; guard against zero productive minutes.
- Rework count is distinct eligible tasks with a `REWORK` event in scope.
- Delayed high-priority tasks are requested high/urgent priorities with `due_at` strictly before the cutoff and no completed state by the cutoff.
- Employee rankings use units per hour descending, then `employee_id` ascending. Team performance uses eligible task completion rate and the payload's tie-breakers.

### Support Health

- Cohort: production accounts in the requested segment/regions, then `support_cases` opened inside the requested window.
- Build a case event timeline from deduped `case_events` through the cutoff. Use lifecycle events to reconstruct active state; do not trust `support_cases.current_status` without checking event history.
- Support active time usually accrues while support owns the case and stops while waiting on the customer or after resolution. Treat `OPENED`, `OPEN`, `REOPENED`, and customer replies as active-starting events; treat waiting-customer and resolved events as active-ending events unless the request says otherwise.
- First response breach: compare active time from case open to first agent response against the priority threshold. If no agent response exists by cutoff, use active elapsed time at cutoff.
- Resolution breach: for resolved cases, compare active time to resolution; for active cases at cutoff, compare active elapsed time to cutoff.
- Open-at-cutoff includes open/reopened active states; reopened-at-cutoff is the reopened subset.
- Severe active cases are active at cutoff, high/urgent priority, and beyond the active-time resolution threshold.
- Median active resolution hours uses resolved eligible cases through the cutoff; for even counts, average the two central values, then round as requested.
- Worst accounts rank by severe active case count descending, active-clock breach count descending, then account id ascending unless overridden.

## Output Validation

- Preserve all required keys from the template and omit everything else.
- Ensure integers are integers, not numeric strings.
- Emit rates in `[0, 1]` and amounts at the requested decimal precision.
- Confirm list uniqueness when the schema requires `uniqueItems`.
- For risk/status fields, evaluate rules in the order provided by the request payload.
- Save only the JSON document to the requested `answer.json`; no markdown, comments, or explanation.
