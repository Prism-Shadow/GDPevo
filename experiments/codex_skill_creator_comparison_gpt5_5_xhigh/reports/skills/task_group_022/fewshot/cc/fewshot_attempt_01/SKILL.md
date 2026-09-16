---
name: atlas-commerce-ops
description: Use this skill for Atlas Commerce Operations workplace tasks that ask for strict JSON answers from an authenticated TASK_ENV_BASE_URL service, /api/schema, /api/data-dictionary, /api/sql, or /api/sql/transaction. It is especially relevant for cutoff-based fulfillment, refund, carrier quality, warehouse productivity, inventory, payments, support-health, and controlled correction tasks that require SQL over the Atlas Commerce Operations database and saving answer.json.
---

# Atlas Commerce Operations

Use this skill to solve Atlas Commerce Operations database tasks end to end: read the request payload and answer template, query the authenticated workplace API, compute the requested metrics with cutoff-consistent SQL, optionally apply an explicitly approved canonical correction, and write only `answer.json`.

## Required Workflow

1. Read the task prompt, the business request JSON under `input/payloads/`, and `input/payloads/answer_template.json` before querying.
2. Resolve the workplace connection from the prompt or the task environment. If the prompt shows `<TASK_ENV_BASE_URL>`, use `TASK_ENV_BASE_URL`, `ATLAS_BASE_URL`, or an `environment_access.md` file when one is present in the task workspace. Use the bearer token from the named token env var, usually `TASK_ENV_API_TOKEN`.
3. Fetch fresh schema and data dictionary from the service. Do not assume the schema from memory; the service is the authority for the current task.
4. Convert the business request into named CTEs that mirror the request language: cohort, effective source rows, cutoff state, rollups, rankings, status/risk classification, and final projection.
5. Use read-only `POST /api/sql` for analysis. Use `POST /api/sql/transaction` only when the request explicitly authorizes a correction and defines the approved mutation and audit requirements.
6. Validate the final JSON against the answer template, including exact keys, no extra fields, array lengths, ordering, enum values, numeric precision, and ID sorting. Save only the JSON document to `answer.json`.

Useful bundled files:

- Read [references/atlas_sql_patterns.md](references/atlas_sql_patterns.md) when designing the SQL or a controlled correction.
- Use `python skill/scripts/atlas_api.py ...` for API calls if shell quoting becomes awkward.
- Use `python skill/scripts/check_answer.py input/payloads/answer_template.json answer.json` before finishing.

## Atlas Rules That Recur

Treat "production" account or order populations as excluding internal and test accounts unless the request says otherwise:

```sql
accounts.is_internal = 0 AND accounts.is_test = 0
```

For imported source tables with `source_system`, `external_event_id`, and `ingested_at`, first deduplicate import retries by keeping the latest ingested copy for each source event. Then derive cutoff state from those effective rows. Do not mix raw source fields into analytics that request canonical operational state.

For cutoff state, filter events at or before the cutoff, then take the latest event per business entity using event time and a stable row id tie-breaker. Denormalized `current_status` fields are convenience snapshots; prefer event history when the request asks for state "at cutoff" or "effective" state.

Round only final reported metrics. Keep unrounded values for ranking and threshold decisions. For all top/worst lists, order by the specified unrounded metric first and only then by the stated stable identifier tie-breaker.

Use distinct business identifiers at the level named by the request: distinct orders, logical refunds, linked reversals, shipments, tasks, cases, accounts, employees, teams, or SKUs. Row counts from imported tables are rarely the correct final unit after deduplication.

## Domain Shortcuts

Fulfillment scorecards usually combine `orders`, `campaigns`, `accounts`, `shipments`, `carrier_scans`, and `warehouses`. A complete order has at least one physical shipment and every shipment's effective final carrier status is delivered by the cutoff. On-time completion requires every delivered shipment to be delivered no later than its own promise.

Refund reconciliation usually combines `accounts`, `orders`, `refund_attempts`, and `fx_rates`. Count logical settled refunds, subtract linked reversals from net USD exposure, rank normalized reasons by net USD, and compare order gross to net refund value in USD using the request's FX basis.

Warehouse productivity usually combines `warehouse_tasks`, `warehouse_task_events`, `employees`, and sometimes `warehouses`. Build the created-window cohort from tasks, derive completion and rework from effective task events by cutoff, compute units per productive hour from completed units and productive minutes, and rank employees/teams using unrounded rates.

Support health usually combines `accounts`, `support_cases`, and `case_events`. Build active-time intervals from lifecycle events, use cutoff elapsed active time for still-active or unresponded cases, apply priority-specific SLA thresholds, and rank accounts by the exact severe/breach counts requested.

Carrier or inventory quality corrections are narrowly scoped mutations. Identify the single canonical contradiction, leave raw/source identity fields untouched, update only the approved canonical field, insert the required audit row, and verify the post-change value plus audit record. Report an applied status only if the request's success rule is fully satisfied.

## Final Answer Discipline

The final output file must contain one JSON object and nothing else. Match the template's property names exactly, including nested object structure. Sort ID arrays ascending unless the template says otherwise. For arrays of objects, use the request/template ordering rule and include exactly the requested number of items.

Never include analysis notes, SQL, or commentary in `answer.json`.
