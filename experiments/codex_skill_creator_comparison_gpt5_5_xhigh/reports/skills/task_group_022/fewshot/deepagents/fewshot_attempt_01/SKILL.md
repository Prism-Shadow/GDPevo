---
name: atlas-commerce-ops
description: Solve Atlas Commerce Operations workplace tasks that require authenticated API schema discovery, SQL analytics, strict JSON answer files, cutoff-based operational metrics, production-account filtering, refund/fulfillment/warehouse/support reporting, or controlled canonical corrections through the Atlas workplace API.
---

# Atlas Commerce Operations

## Core Workflow

1. Read the user prompt, every file under `input/payloads/`, and the answer template before querying. Treat the request JSON as the business definition source and the template as the exact output contract.
2. Discover live context with `GET /api/schema` and `GET /api/data-dictionary`. Use the database, not memory, for table names, field names, and value sets.
3. Use `POST /api/sql` for analytical work. Do not mutate data unless the prompt explicitly requests a controlled correction.
4. For correction tasks, first prove the target with read-only SQL, compute the pre-change metrics, apply only the approved canonical-field change through `POST /api/sql/transaction`, then verify the changed row, the audit row, and the post-change metrics. If verification does not match the request's success rule, report the actual observed result and `NOT_APPLIED`.
5. Write only `answer.json`. It must have exactly the keys, nesting, precision, ordering, and enum values required by the template.

Use [`scripts/atlas_api.py`](scripts/atlas_api.py) when shell quoting gets in the way:

```bash
python skill/scripts/atlas_api.py schema
python skill/scripts/atlas_api.py dictionary
python skill/scripts/atlas_api.py sql query.sql
python skill/scripts/atlas_api.py sql - < query.sql
python skill/scripts/atlas_api.py audit
python skill/scripts/atlas_api.py post /api/sql/transaction transaction_body.json
```

The helper reads `TASK_ENV_BASE_URL` when set, otherwise defaults to the staged task host, and sends `Authorization: Bearer $TASK_ENV_API_TOKEN` when the token is present.

## SQL Rules

- Compare stored UTC timestamps as ISO text when they use the documented `YYYY-MM-DDTHH:MM:SSZ` format. Apply inclusive, exclusive, and strict boundaries exactly as written in the request.
- Keep denominators explicit. Incomplete, active, unresolved, or unreversed rows usually remain in rate denominators unless the request excludes them.
- Rank with unrounded metrics, then round only the final reported numbers to the requested precision.
- Sort arrays exactly as requested, including secondary lexical tie-breakers. Use stable IDs for final lists.
- For production account scopes, join `accounts` and exclude internal or test accounts unless the request says otherwise.
- Convert minor monetary values to major units before FX conversion. Join `fx_rates` on the row's currency and service date or request-specified valuation date, then apply the requested rounding only for display.
- De-duplicate imported retry rows before business aggregation when source identity fields are relevant. Prefer a `row_number()` CTE partitioned by the source identity, ordered by latest `ingested_at` and a stable row id as tie-breaker. Keep logical business IDs such as refund IDs, shipment IDs, movement IDs, task IDs, and case IDs distinct from import retry identity.
- For historical cutoff state, reconstruct from event or scan rows at or before the cutoff when the request uses words like effective, active at cutoff, final status, or state cutoff. Use denormalized `current_status` only when the request asks for the current snapshot or after confirming it is equivalent for the requested cutoff.

## Common Domain Patterns

- Fulfillment: define the eligible order cohort from campaign/account/warehouse scope and the campaign or request window. An order with no physical shipment is incomplete. For shipment completion, use the effective final carrier status by cutoff when scans are in scope; on-time delivery usually requires every shipment to be delivered no later than its own promise.
- Refunds: build the eligible order cohort from production account filters plus effective settled logical refunds in the service-date window. Apply linked reversals against their target refund, net in USD with daily FX, rank reasons by net amount and request tie-breakers, and flag leakage only from the request's candidate rules.
- Carrier or inventory quality corrections: identify the single contradiction between raw/source evidence and canonical operational fields. Mutate only the approved canonical column and correction metadata if required; never alter raw source values, source identity fields, or unrelated rows. Insert exactly the requested audit fields and verify through the audit endpoint or table.
- Warehouse productivity: start from eligible production tasks in the requested warehouse/window. Use task events at or before the cutoff for completed units, productive minutes, rework evidence, and completion state when the request is cutoff-based. Compute employee and team rates from the same eligible task set.
- Support health: scope accounts first, then cases. For support active time, derive intervals from case events up to the first response, resolution, or cutoff: active after opened/open/reopened/customer-replied states, paused while waiting on the customer, and stopped when resolved. Use priority-specific thresholds exactly as supplied and compute medians from resolved eligible cases only.

## Answer Discipline

- Build the answer object from the template, not from the query output shape.
- Check `additionalProperties` or equivalent template wording; omit all commentary and helper fields.
- Preserve integer IDs and code strings exactly. Do not normalize case unless the request tells you to.
- For status/risk enums, evaluate rules in the order given and with unrounded rates.
- Before finishing, re-open `answer.json` and compare it against every required key, array length, ordering rule, precision rule, and enum constraint in the template.
