---
name: atlas-commerce-ops-analysis
description: Solve Atlas Commerce Operations workplace tasks that provide prompt/payload files, strict JSON answer templates, and an authenticated local API for schema discovery, SQL analysis, controlled canonical corrections, and audit verification. Use for cutoff-based scorecards, refund reconciliation, carrier scan quality corrections, warehouse productivity reviews, support health/SLA reviews, and similar operational analytics that must write exactly one answer.json.
---

# Atlas Commerce Ops Analysis

## Core Workflow

1. Read the task prompt, every request payload, and the answer template before querying data.
2. Read the task's environment access file for the base URL, bearer token, and allowed endpoints. Use only those endpoints.
3. Fetch `/api/schema` and `/api/data-dictionary`; rely on them over memory for table names, fields, timestamp conventions, and source-row semantics.
4. Treat the answer template as the contract. Preserve required keys, nesting, enum values, array sizes, sorting rules, numeric precision, and `additionalProperties: false` constraints.
5. Build SQL from the request's business definitions, not from output field names alone. Keep request-specific IDs, dates, thresholds, statuses, and final values out of reusable notes.
6. Validate every count/rate/list with at least one independent query or decomposition before writing `answer.json`.
7. Write exactly one JSON object to the requested output path with no commentary.

## API Usage

Use JSON-wrapped SQL:

```bash
curl -sS \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sql":"select 1 as ok"}' \
  "$BASE_URL/api/sql"
```

The SQL endpoint returns `columns`, `rows`, `row_count`, and `truncated`. If a broad CTE query is rejected, split it into smaller scoped queries that expose the same intermediate facts.

Use `/api/sql` for read-only analysis. Use `/api/sql/transaction` only when the prompt explicitly requests a controlled data correction, and only for the approved minimal canonical update plus its audit insert. Confirm the transaction endpoint's expected request shape in the active environment before sending a mutating request.

## Data Rules

- All stored timestamps are ISO-8601 UTC text ending in `Z`; compare exact cutoff windows in UTC unless the request says otherwise.
- Calendar dates are `YYYY-MM-DD`; FX rates are keyed by service date and currency, with `usd_per_unit` expressing USD per one currency unit.
- Minor monetary fields use the smallest unit of the row currency. Convert minor units to currency units before multiplying by `usd_per_unit`; round only final displayed money to the template precision.
- Master/header tables such as orders, shipments, warehouse tasks, and support cases can contain lagging current-status snapshots. For point-in-time metrics, prefer deduped event or scan histories at the cutoff when available.
- Source event tables can contain import retries. Build effective CTEs by partitioning on `(source_system, external_event_id)` and keeping the latest `ingested_at`, with the stable row id as a deterministic tie-breaker.

Example effective-source pattern:

```sql
with effective_events as (
  select *
  from (
    select e.*,
           row_number() over (
             partition by source_system, external_event_id
             order by ingested_at desc, event_id desc
           ) as rn
    from order_events e
  )
  where rn = 1
)
```

Adjust the tie-break id to the table, such as `scan_row_id`, `refund_row_id`, `task_event_id`, or `case_event_id`.

## Analytical Patterns

For cohort construction:

- Join to account or warehouse master data when the request says production accounts, account tier/segment/region, warehouse, facility, or warehouse region.
- Exclude internal/test accounts when the scope says production accounts or production customers.
- Use inclusive boundaries when the request says inclusive; otherwise preserve strict comparisons such as "strictly before cutoff."
- Keep incomplete, open, unresolved, unreversed, or delayed records in denominators when the request says they remain eligible.

For rates, ranks, and lists:

- Compute rates from unrounded numerator/denominator values.
- Round only the final reported value to the requested number of decimal places.
- Apply sort order exactly, including tie-breaks such as stable identifier ascending.
- Return required list sizes exactly. Use distinct business identifiers and sort arrays as specified.
- When deriving a status/risk enum, evaluate the request's rules in priority order and use the denominator specified by the request.

For "effective final status" at a cutoff:

- Deduplicate source rows first.
- Filter events/scans to `event_at` or canonical event timestamp at or before the cutoff.
- Pick the latest event per entity using event timestamp descending and stable row id descending.
- For delivered/completed/resolved timing, use the relevant terminal event timestamp from the deduped history, not a later header snapshot.

## Domain Patterns

Fulfillment scorecards:

- Build eligible orders from campaign/account/warehouse scope.
- Treat an order as complete only when it has at least one physical shipment and every associated shipment is effectively delivered by the cutoff.
- Treat on-time completion as requiring every associated shipment's delivered timestamp to be no later than that shipment's promise.
- For severe exceptions, compare delivered or cutoff timing to shipment promises exactly as the request defines, including any grace period.

Refund reconciliation:

- Deduplicate refund attempts by source identity before classification.
- Count distinct eligible orders and distinct logical refunds according to the request's effective-settled definition.
- Link reversals through `linked_refund_id`; subtract linked reversal USD from the logical refund's settled USD for net exposure.
- Rank reasons by effective net USD and the request's tie-breaker.
- Compare net refund USD to the order gross converted at the refund service-date FX rate specified by the request.

Carrier quality corrections:

- Scope contradiction discovery by import batch, warehouse/facility, cutoff, and production shipment rules from the request.
- Compare raw source status with canonical status only to find the single approved contradiction; never change raw source values, source identity fields, unrelated rows, or broad status snapshots unless explicitly approved.
- Before mutation, record the target row id, business entity id, field name, old value, new value, reason code, actor, correction key, audit id, and corrected timestamp from the request.
- Mutate only the minimal canonical field and canonical correction metadata, and insert exactly one audit record in the same controlled transaction.
- After mutation, query both the business row and `/api/correction-audit`. Report `APPLIED` only if the request's success rule is satisfied; otherwise report `NOT_APPLIED` with observed counts.

Warehouse productivity:

- Scope eligible tasks by warehouse, production work class, creation window, and cutoff.
- Compute completed units and productive minutes from deduped task events, not just planned units.
- Compute units per hour as completed production units divided by productive minutes times 60; handle zero productive minutes explicitly.
- Count rework from the request's task or event definition, then divide by all eligible production tasks for rework rate.
- For delayed high-priority work, apply exact priority set, due-time comparison, and cutoff-completion state from the request.
- Rank employees and teams using unrounded metrics and stable identifier tie-breaks.

Support health and SLA reviews:

- Scope cases through accounts when the request names production customers, segment, tier, or regions.
- Deduplicate case events before deriving first response, active/open state, resolved state, reopened state, and active-clock durations.
- Compute active-at-cutoff from event history at the cutoff. Treat reopened as the requested subset of active cases.
- For active-time clocks, sum only intervals where the support clock is active, and stop at first agent response, resolution, or cutoff as the metric requires. Exclude waiting-on-customer intervals when the event history provides `WAITING_CUSTOMER` and `CUSTOMER_REPLIED` transitions.
- For unresolved cases, use active elapsed time at the cutoff for response or resolution breach checks.
- For medians, sort numeric active-resolution hours and average the two central values for even counts before final rounding.

## Output Validation

Before writing `answer.json`:

- Confirm the JSON contains every required key and no extra keys.
- Confirm numbers use the required precision and are JSON numbers, not strings.
- Confirm arrays meet `minItems`/`maxItems`, uniqueness, pattern, and ordering rules.
- Confirm enum strings exactly match the template.
- Confirm all IDs are stable business IDs from the database, not row numbers or labels invented from context.
