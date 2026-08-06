# Atlas Commerce Operations — Data Model Notes

Operational domain models that resolve the scorecard metrics. Use alongside `GET /api/schema` and `GET /api/data-dictionary`.

## Production filter

`accounts` columns `is_test` (INTEGER 0/1) and `is_internal` (INTEGER 0/1). Account names confirm intent: "Sandbox Account …" ⇒ `is_test=1`; "Internal Account …" ⇒ `is_internal=1`.

- **Production account** = `is_test = 0 AND is_internal = 0`.
- Propagates to orders/shipments/cases/tasks through their `account_id` (orders→accounts; shipments→orders→accounts; support_cases→accounts; warehouse_tasks→employees→warehouses; tasks scoped by `warehouse_id`).
- Apply this whenever the scope says `PRODUCTION_*` or "production accounts/orders/shipments/cases". It is the single most impactful filter — omitting it over-counts cohorts with sandbox + internal rows.

## Carrier scans → effective final status

`carrier_scans` per shipment: `raw_status`, `raw_event_at` (source) and `canonical_status`, `canonical_event_at` (normalized), plus `source_system`, `external_event_id`, `ingested_at`, `import_batch_id`, nullable `corrected_at`/`correction_reason`.

1. **Dedup retries**: keep latest `ingested_at` per `(source_system, external_event_id)`.
2. **Effective final status at cutoff T**: among deduped scans with `canonical_event_at <= T`, take the one with the greatest `(canonical_event_at, ingested_at, scan_row_id)`; its `canonical_status` is the effective final status.
3. A shipment is **delivered by cutoff** iff that final status is `DELIVERED`. (Do not treat "any DELIVERED scan exists" as delivered — a later non-delivered scan changes the final status.)
4. **Backlog** = in-scope production shipments whose effective final status ≠ `DELIVERED`.
5. Delivered timestamp (for on-time / lateness) = the `canonical_event_at` of that final DELIVERED scan.

`shipments.current_status` is a lagging snapshot — do not use it for cutoff state.

## Raw/canonical contradiction (correction tasks)

In a named `import_batch_id`, exactly one row has `raw_status <> canonical_status`. Minimal canonical correction = set the canonical field to the raw value (e.g. `canonical_status: IN_TRANSIT → DELIVERED`), stamp `corrected_at` + `correction_reason='SOURCE_RECONCILIATION'`, and append a `correction_audit` row. Raw source values never change.

`correction_audit` has 11 NOT-NULL-ish columns: `audit_id, correction_key (unique), entity_type, entity_id, source_row_id, field_name, old_value, new_value, reason_code, corrected_at, actor`. `correction_key` is an idempotency key.

## Refund attempts → effective refunds & reversals

`refund_attempts`: `refund_id` (logical refund), `status` ∈ {SETTLED, FAILED, VOIDED, REVERSED}, `reason_code`, `amount_minor` + `currency`, `service_date`, nullable `linked_refund_id`.

- `status` is consistent per `refund_id` across retries → one effective status per logical refund (one row per `refund_id`).
- **SETTLED** = effective (settled) refund.
- **REVERSED** rows carry `linked_refund_id` pointing at the refund they reverse → these are **linked reversals**.
- `effective_linked_reversal_count` = in-scope REVERSED refunds that have a link — count them even if their target is not SETTLED.
- **net_refund_amount_usd** = Σ(SETTLED USD) − Σ(in-scope REVERSED USD). Reversals reduce net regardless of their target's status.
- FX: convert each row by `fx_rates.usd_per_unit` for `(service_date, currency)`. USD's own rate varies daily — use it, don't assume 1.0.
- **Leakage candidate order**: (a) effective settled refund USD (after reversals) > gross order USD (gross valued in the order's currency at the refund's service_date rate), OR (b) ≥2 unreversed effective settled logical refunds with the same normalized `reason_code`. Output `order_id` ascending.

## Support cases → active time & state

`support_cases`: `case_id, account_id, priority, opened_at, current_status (lagging)`. `case_events` (append-only): `OPENED, ASSIGNED, AGENT_RESPONDED, WAITING_CUSTOMER, CUSTOMER_REPLIED, RESOLVED, REOPENED, OPEN, ESCALATED`, each with `event_at`.

- **State at cutoff T**: replay events ≤ T. Last terminal event (`RESOLVED` vs `REOPENED`) decides: resolved unless `REOPENED` follows the last `RESOLVED`. Cases with no terminal event are OPEN. `open_at_cutoff` = Open ∪ Reopened; `reopened_at_cutoff` = Reopened subset. Ignore `current_status`.
- **Active clock** starts at the `opened_at` header field (NOT the `OPENED` event_at — they differ by minutes). Clock pauses during `WAITING_CUSTOMER` (until the next `CUSTOMER_REPLIED`/agent event).
  - `first_response` active time = open → first `AGENT_RESPONDED` (active, pauses excluded). Unresponded ⇒ active elapsed to T.
  - `resolution` active time = open → final `RESOLVED` (active). Active case ⇒ active elapsed to T.
- **SLA breach** = active time **strictly exceeds** the priority threshold (`>`; "EXCEEDS"). Thresholds are priority-specific (first_response, resolution_active_time) from the request.
- **severe active case** = active at cutoff AND priority in {URGENT, HIGH} AND resolution active-time breach. IDs sorted ascending.
- **median active resolution hours** = across cases resolved at cutoff; even count ⇒ average the two central values.

## Warehouse tasks → productivity

`warehouse_tasks`: `task_id, warehouse_id, assigned_employee_id, work_class (PRODUCTION|TRAINING), priority, planned_units, created_at, due_at, current_status (lagging)`. `employees`: `team_id`. `warehouse_task_events`: `event_type (CREATED, STARTED, IN_PROGRESS, COMPLETED, REWORK, …)`, `units`, `productive_minutes`.

- Eligible production tasks: `warehouse_id` match, `work_class='PRODUCTION'`, `created_at` in the request window (inclusive UTC).
- Completion/rework determined by effective (deduped) `COMPLETED`/`REWORK` events at/before the **state cutoff** (not the create window end). Prefer events over `current_status`.
- `units_per_hour` (per employee) = (Σ `units` over that employee's effective COMPLETED events on eligible completed tasks) / (Σ `productive_minutes` over those same events) × 60. Rank employees by units/hour desc, then `employee_id` asc.
- `completed_production_units` = Σ `units` over those effective COMPLETED events.
- `delayed_high_priority_task` = HIGH/URGENT eligible task with `due_at` **strictly before** the state cutoff that is not completed by the cutoff. IDs ascending.
- `lowest_performing_team` = teams ranked by completion-rate asc, then `team_id` asc (first).
- `rework_rate` = rework task count / eligible count; `completion_rate` = completed eligible count / eligible count. Facility status uses **unrounded** rates against the ordered rules.

## Money conventions

`gross_amount_minor` (orders), `amount_minor` (refund_attempts, payment_events): smallest unit of the row `currency`. `fx_rates.usd_per_unit` = USD per one unit of the named currency for `rate_date`. FX is USD-per-unit; minor units are /100 to major. Round only final reported values to the stated decimals.
