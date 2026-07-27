---
name: atlas-commerce-ops-analytics
description: Analyze Atlas Commerce Operations workplace tasks that provide request payloads, answer templates, and an authenticated Atlas service. Use for cutoff-consistent fulfillment scorecards, refund reconciliation, carrier scan quality corrections, warehouse productivity reviews, support health reviews, and similar operational analytics requiring exact answer.json output through the schema, data dictionary, SQL, transaction, and correction-audit APIs.
---

# Atlas Commerce Ops Analytics

## Required Workflow

1. Read the user prompt, every file under `input/payloads/`, and the output template before querying. Treat the request payload as the source of business scope, cutoff timestamps, rounding, ranking, and risk rules.
2. Resolve the service URL and token only from the task environment instructions. Fetch `/api/schema` and `/api/data-dictionary` before writing SQL.
3. Use `POST /api/sql` for read-only analysis. Send parameterized SQL as `{"sql":"...","params":[...]}`. Use `POST /api/sql/transaction` only when the request explicitly authorizes a correction.
4. Build SQL in CTEs that expose the population, effective facts, metric rows, ranked rows, and final checks separately. Do not rely on convenience snapshot columns when the request asks for state "at cutoff"; derive state from effective events or scans at or before that cutoff.
5. Keep timestamps as UTC ISO text and apply request boundary language exactly. Inclusive windows use `>= start` and `<= end`; strict lateness such as "due before cutoff" uses `< cutoff`.
6. Round only final displayed rates or money values. Rank by unrounded values, then by the stated tie-break key.
7. Check the SQL response `truncated` flag. If true, narrow the query, page by stable ID ranges, or aggregate into JSON/list values so no required ID is lost.
8. Validate the answer against the template exactly: required keys only, array length and ordering rules, unique ID arrays, enum values, and numeric precision. Write only the JSON object to `answer.json`.

## Effective Records

- For imported rows with `source_system`, `external_event_id`, and `ingested_at`, assume upstream retries can exist. Deduplicate before analytics with `row_number() over (partition by source_system, external_event_id order by ingested_at desc, <primary_id> desc) = 1`.
- For a final state at a cutoff, filter deduped lifecycle rows to event time `<= cutoff`, then choose the last row per entity by event timestamp and stable row ID.
- Prefer canonical operational columns for analytics (`canonical_status`, `canonical_event_at`, `canonical_quantity_each`). Preserve raw/source fields unless the request authorizes a minimal canonical correction.
- Apply production exclusions whenever scope says production accounts: `accounts.is_internal = 0` and `accounts.is_test = 0`.
- Use stable business IDs for final lists, sorted exactly as requested. Cross-check every final list with a count query or an aggregate count.

## Fulfillment Scorecards

- Eligible campaign orders: join `orders` to `campaigns` on `campaign_id`, and require the named campaign plus order creation within the campaign active window. Join `warehouses` for region rollups.
- Physical completion: left join `shipments`. An order with no shipment is incomplete. For each shipment, derive the effective final carrier scan at cutoff from deduped `carrier_scans`; a shipment is delivered only when that final canonical status is `DELIVERED`.
- On-time completion: require every physical shipment to be delivered and every delivered shipment's effective delivery timestamp to be `<= promised_delivery_at`.
- Severe exceptions: follow the request definition at order level. For incomplete shipped orders, compare the cutoff to the latest shipment promise; for completed orders, check any shipment delivered more than the allowed lateness interval after its promise.
- Regional rates keep incomplete orders in the denominator. Select worst regions by unrounded rate ascending, then region ascending. Determine the overall status from the request's ordered status rules.

## Refund Reconciliation

- Start from production accounts and the requested account tier, then join to orders and refund rows.
- Treat a logical refund as `refund_id`; dedupe source retries first and count distinct effective settled logical refunds in the requested service-date window.
- Treat linked reversals by `linked_refund_id`; subtract effective linked reversal USD from the settled refund USD for net exposure and count distinct linked reversals.
- Convert minor currency amounts to currency units, then multiply by `fx_rates.usd_per_unit` for the row `service_date` and currency. For order gross comparisons, value the order gross in its order currency using the refund service date required by the request.
- Rank reason codes by effective net refund USD descending, then normalized reason code ascending.
- Flag leakage candidates exactly from the request: net refund value exceeding order gross and/or multiple unreversed effective settled refunds with the same normalized reason code. Sort candidate order IDs ascending and classify cohort risk from the request thresholds.

## Carrier Quality Corrections

- Before mutating, prove the correction target with read-only SQL. Scope to the named import batch, warehouse, population, and cutoff. Find the single raw/canonical contradiction by profiling raw-to-canonical status pairs in the batch and isolating the row whose canonical value conflicts with the dominant/raw-implied mapping.
- Compute pre-correction backlog from the effective final carrier status at the cutoff: shipments in scope whose final canonical status is not `DELIVERED`.
- If the request authorizes a correction, use one guarded transaction with both statements: update only the approved canonical field on the exact source row with old-value predicates, and insert exactly one `correction_audit` row using the request's audit metadata. Set `expected_total_changes` to the required total business plus audit changes.
- Verify after commit with read-only SQL and `/api/correction-audit`. Return `APPLIED` only when exactly the required business row count, audit row count, and post-change canonical value all match the success rule; otherwise return `NOT_APPLIED` with observed counts and state.
- Never change raw status, source identity fields, unrelated rows, or unapproved canonical fields.

## Warehouse Productivity

- Eligible tasks: filter `warehouse_tasks` by requested warehouse, created window, and `work_class = 'PRODUCTION'`.
- Derive task completion by deduped `warehouse_task_events` at or before the state cutoff. Count a task complete when it has a `COMPLETED` event by cutoff.
- Completed units and productive minutes come from completed production events attached to eligible tasks. Employee units per hour is `sum(units) / sum(productive_minutes) * 60`; guard against zero minutes.
- Rework tasks have a `REWORK` event by cutoff. Delayed high-priority tasks have priority in the requested high set, `due_at < cutoff`, and no completion by cutoff.
- Rank employees by units per hour descending, then employee ID ascending. Rank teams by completion rate ascending, then team ID ascending, using the employee's team assignment. Classify facility status from the ordered request rules.

## Support Health

- Eligible cases: join `support_cases` to production `accounts` and apply segment, region, opened-window, and cutoff filters from the request.
- Build deduped `case_events` through the cutoff. Use event order to derive final active state: active-at-cutoff includes open/reopened states, with reopened counted as the reopened subset.
- Use support active time, not wall time, for SLA checks. Accumulate intervals when support owns the case; pause on customer-wait/resolved states and resume on customer reply, reopen, or other support-active events. For unresolved cases, end the interval at the cutoff.
- First response breach: compare active time from opening to the first `AGENT_RESPONDED`; for unresponded cases, compare active elapsed time at cutoff.
- Resolution breach: compare active time to resolution for resolved cases; for active cases, compare active elapsed time at cutoff.
- Severe active cases are active at cutoff, urgent or high priority, and beyond the active-time resolution threshold. Worst accounts are ordered by severe active case count descending, active-clock breach count descending, then account ID ascending.
- Median active resolution hours uses only eligible cases resolved at the cutoff. Sort exact active resolution hours and average the two central values for even counts; round the final median to the requested precision. Classify support risk from the request rates using eligible case count as denominator.

## Final Checks

- Recompute denominator counts independently from numerator/list queries.
- Confirm rates use the requested denominator even when incomplete, unresolved, or active records remain in scope.
- Confirm final arrays contain stable IDs only, not row IDs unless the template asks for row IDs.
- Do not copy values from examples or prior runs. Always recompute against the current task environment and current request payload.
