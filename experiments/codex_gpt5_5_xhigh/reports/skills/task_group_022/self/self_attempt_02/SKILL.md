---
name: atlas-ops-workplace
description: Analyze and, when explicitly approved, correct Atlas Commerce Operations workplace data through documented task-environment APIs. Use when Codex receives prompts with environment_access.md, input/payload JSON contracts, Atlas Commerce Operations schema/data-dictionary endpoints, SQL analysis endpoints, cutoff-based operational scorecards, refund settlement reconciliation, carrier or inventory canonical-field corrections with correction_audit records, warehouse productivity reviews, or support SLA health reviews that must be returned as strict answer.json JSON.
---

# Atlas Ops Workplace

## Core Workflow

1. Read the prompt, every file under `input/payloads/`, and the answer template before querying data.
2. Read `environment_access.md` and use only the endpoints, method types, headers, and mutation limits documented there.
3. Fetch `/api/schema` and `/api/data-dictionary` before writing SQL. Treat the request payload as the source of business definitions and the answer template as the output contract.
4. Build the cohort first, then add row-level flags, then aggregate. Keep diagnostic queries small enough to inspect intermediate counts.
5. Use read-only `POST /api/sql` for analytics. Use `POST /api/sql/transaction` only when the prompt explicitly requests an approved data correction.
6. Write exactly one JSON object to `answer.json`. Include only fields allowed by the answer template, with required ordering, rounding, uniqueness, and sort order.

## API Handling

- Resolve the base URL, token, allowed endpoints, transaction limits, and required headers from `environment_access.md`; do not hardcode values from prior tasks.
- Send SQL as a single `SELECT` or `WITH` query unless using the controlled transaction endpoint.
- Avoid trailing semicolons and multiple SQL statements in `/api/sql`; the endpoint may reject them.
- Use parameterized SQL through the `params` array for request IDs, timestamps, statuses, tiers, regions, and other payload values.
- Query `/api/correction-audit` before and after approved corrections when the task involves a canonical data change.

## Cohorts

- Apply all request-scoped boundaries exactly. Treat timestamps ending in `Z` as UTC text and use the request's inclusive, exclusive, or strict boundary language.
- For production populations, exclude non-production accounts when account records are in scope: require `accounts.is_internal = 0` and `accounts.is_test = 0`.
- For production warehouse work, prefer the task-level production marker, such as `warehouse_tasks.work_class = 'PRODUCTION'`, plus the requested warehouse and created window.
- For campaign cohorts, join to `campaigns` and use the campaign's official active window when the request says campaign-attributed orders created during the campaign window.
- Preserve denominator rules. Incomplete, unresolved, or active records usually remain in cohort denominators unless the payload says otherwise.

## Event And Source Semantics

- Prefer append-only event/source tables for cutoff-sensitive state when the request says effective, active at cutoff, completed by cutoff, final at cutoff, or resolved at cutoff. Treat `current_status` columns as convenience snapshots that may lag event history unless the request explicitly asks for current snapshot data.
- De-duplicate imported retries when a table has `source_system`, `external_event_id`, and `ingested_at`: keep the latest ingested row for each source event, using the stable row id as a deterministic tie-breaker.
- For latest state at a cutoff, rank effective events by business event time descending and stable row id descending within the entity, after filtering to events at or before the cutoff.
- Do not confuse "has a DELIVERED event by cutoff" with "latest/final status is DELIVERED"; follow the exact wording in the payload.
- Keep raw source values immutable. For correction tasks, update only the approved canonical field and correction metadata.

## Metric Patterns

- Fulfillment: build eligible orders; identify physical shipments; determine delivered-by-cutoff and delivery timing from carrier/shipment evidence; count an order complete only when every shipment satisfies the completion definition and orders with no physical shipments remain incomplete.
- Refunds: count logical refunds by distinct refund identifiers, not duplicate import rows. Treat effective settled refunds and linked reversals according to status, service date, and linkage fields. Normalize reason codes consistently before grouping and ranking.
- Money: convert minor units to currency units before applying `fx_rates.usd_per_unit` for the relevant service date and row currency. Round only final monetary displays to the requested precision.
- Warehouse productivity: select eligible tasks from task headers; derive completion, rework, units, and productive minutes from task events at or before the state cutoff. Rank employees and teams with the tie-breakers in the payload.
- Support health: select cases through account scope and opened window. Build case state from case events at or before the cutoff. For Atlas active-time SLA clocks, start or resume active intervals on `OPENED`, `OPEN`, `REOPENED`, `CUSTOMER_REPLIED`, `ASSIGNED`, `AGENT_RESPONDED`, or `ESCALATED`; pause on `WAITING_CUSTOMER`; stop on `RESOLVED`. Use the first `AGENT_RESPONDED` as the first-response endpoint, the cutoff for unresponded or active cases, and the resolution event for resolved cases. Compute medians from unrounded active hours, averaging the two center values for even counts.

## Corrections

- Perform corrections only when the prompt includes an approved correction scope. Otherwise stay read-only.
- Identify the target row with a diagnostic query that proves the intended anomaly is unique.
- Prepare a guarded transaction with one business-row `UPDATE` and one `correction_audit` `INSERT` when the task asks for an audit record.
- Guard the `UPDATE` by primary key and old canonical value. Set only the approved canonical column, `corrected_at`, and correction reason fields when present.
- Insert the exact audit fields supplied by the request: audit id, correction key, entity type, entity id, source row id, field name, old value, new value, reason code, corrected timestamp, and actor.
- Set `expected_total_changes` to the exact number of business and audit rows expected by the success rule. Verify the changed canonical value and the audit record after the transaction before reporting an applied status.
- If an audit record already exists, the target is not unique, the guarded update affects the wrong number of rows, or verification fails, report the observed outcome according to the answer template rather than assuming success.

## Output Discipline

- Use the answer template as a JSON schema even when it uses nonstandard keys such as `additional_properties`, `min_items`, or precision annotations.
- Respect array sizes, uniqueness, and ordering clauses exactly. Sort IDs lexicographically ascending unless the payload specifies another order.
- Use unrounded values for ranking and classification thresholds; round only final reported numbers.
- Apply status/risk rules in the order listed. Use strict comparisons exactly as written, especially "below", "at least", "greater than", and "strictly before".
- Validate the finished `answer.json` against required fields, enums, decimal precision, and absence of commentary or extra fields before finishing.
