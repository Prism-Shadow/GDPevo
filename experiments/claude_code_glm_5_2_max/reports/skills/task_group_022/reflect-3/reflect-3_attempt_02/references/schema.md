# Atlas Commerce Operations — Schema Map

SQLite-like dialect. Timestamps are ISO-8601 UTC (`...Z`); calendar dates are `YYYY-MM-DD`. Integer booleans use `1`/`0`. PKs in **bold**.

## Master / reference tables

- **accounts** — `account_id`** PK, account_name, segment ∈ {CONSUMER,SMB,ENTERPRISE,STRATEGIC}, tier ∈ {STANDARD,SILVER,GOLD,PLATINUM}, region, currency, `is_internal` (0/1), `is_test` (0/1), created_at. **Production = `is_internal=0 AND is_test=0`.**
- **campaigns** — `campaign_id`** PK, campaign_name (UNIQUE), starts_at, ends_at, channel. Use starts_at/ends_at to window attributed orders.
- **warehouses** — `warehouse_id`** PK, warehouse_name, region, timezone, daily_cutoff_local.
- **products**** — `sku` PK, product_family, unit_weight_grams, units_per_case, is_active (0/1).
- **employees** — `employee_id`** PK, warehouse_id, team_id, role, active_from, active_to (nullable). One team per employee (via employees.team_id).
- **fx_rates** — (rate_date, **currency**) PK, usd_per_unit REAL (>0). USD has its own row (≠ exactly 1.0). USD per one *unit* (= 100 minor).
- **source_import_batches** — `import_batch_id`** PK, source_system, entity_type, started_at, completed_at, record_count, status.

## Transactional snapshots (current_status "may lag" event history)

- **orders** — `order_id`** PK, account_id, campaign_id (nullable), warehouse_id, order_created_at, promised_at, currency, current_status *(lags)*, gross_amount_minor.
- **shipments** — `shipment_id`** PK, order_id, carrier_code, warehouse_id, shipped_at (nullable), promised_delivery_at, current_status *(lags)*.
- **warehouse_tasks** — `task_id`** PK, warehouse_id, order_id (nullable), sku (nullable), assigned_employee_id, task_type, work_class ∈ {PRODUCTION,TRAINING}, priority, planned_units, created_at, due_at, current_status *(lags)*.
- **support_cases** — `case_id`** PK, account_id, order_id (nullable), priority, opened_at, current_status *(lags)*, current_owner_team.
- **inventory_snapshots** — (warehouse_id, sku, snapshot_at) PK, on_hand_each, reserved_each, source_system.

## Append-only event / scan tables (authoritative for state & time)

These carry deliberate duplicate rows on import retries — dedup by the natural key (see [conventions.md](conventions.md)).

- **order_events** — `event_id`** PK, order_id, event_type, event_at, source_system, external_event_id, ingested_at, metadata_json. event_type ∈ {CREATED,PAYMENT_CONFIRMED,ALLOCATED,PACKED,SHIPPED,DELIVERED,CANCELLED}.
- **carrier_scans** — `scan_row_id`** PK, shipment_id, source_system, external_event_id, raw_status, raw_event_at, `canonical_status` *(normalized/effective)*, `canonical_event_at` *(normalized effective time)*, ingested_at, import_batch_id, corrected_at (nullable), correction_reason (nullable). **Authoritative delivery basis = `canonical_status='DELIVERED'` at `canonical_event_at`.** Dedup by (canonical_event_at, canonical_status) — parallel high-numbered rows echo low-numbered ones.
- **warehouse_task_events** — `task_event_id`** PK, task_id, event_type, event_at, `units`, `productive_minutes`, source_system, external_event_id, ingested_at. event_type ∈ {COMPLETED,REWORK,…}. COMPLETED/REWORK rows carry the real units & productive_minutes.
- **case_events** — `case_event_id`** PK, case_id, event_type, event_at, actor_type, source_system, external_event_id, ingested_at. event_type includes OPENED, AGENT_RESPONDED, CUSTOMER_REPLIED, WAITING_CUSTOMER, RESOLVED, REOPENED. Dedup by (event_at, event_type).
- **payment_events** — `payment_event_id`** PK, order_id, provider, source_system, external_event_id, event_type, amount_minor, currency, event_at, ingested_at, linked_event_id (nullable). Auth/settle/void/reversal events.
- **refund_attempts** — `refund_row_id`** PK, refund_id, order_id, provider, source_system, external_event_id, status, reason_code, amount_minor, currency, `service_date` (YYYY-MM-DD), event_at, ingested_at, linked_refund_id (nullable). Status / reason_code are free-text enums; `service_date` is the money-policy date for FX.

## Money / inventory movement tables

- **refund_attempts** / **payment_events** — `amount_minor` = smallest unit of the row currency. Convert to USD: `(amount_minor/100.0) * usd_per_unit` on (service_date/event date, currency), even for USD rows.
- **inventory_movements** — `movement_row_id`** PK, movement_id, warehouse_id, sku, movement_type, raw_quantity, raw_uom, raw_uom_multiplier, `canonical_quantity_each` *(normalized signed each-units)*, canonical_uom_multiplier, occurred_at, source_system, external_event_id, ingested_at, source_document_id, corrected_at (nullable), correction_reason (nullable). Prefer `canonical_quantity_each` for analytics.

## Correction control

- **correction_audit** — `audit_id`** PK, `correction_key` (UNIQUE, idempotency), entity_type, entity_id, source_row_id, field_name, old_value (nullable), new_value (nullable), reason_code, `corrected_at` (NOT NULL — always supplied), actor. Public log appended by the controlled transaction. `GET /api/correction-audit` reads it.
- Controlled UPDATE targets: `carrier_scans` (canonical_status) and `inventory_movements`. See SKILL.md "The controlled correction".

## Key relationships
- orders → accounts (production flags), campaigns (attribution+window), warehouses.
- orders → order_events (lifecycle), shipments (→ carrier_scans for delivery), order_lines (→ products), warehouse_tasks (→ warehouse_task_events), support_cases (→ case_events), payment_events, refund_attempts.
- warehouse_tasks → employees (team_id via employee), warehouse_task_events.
