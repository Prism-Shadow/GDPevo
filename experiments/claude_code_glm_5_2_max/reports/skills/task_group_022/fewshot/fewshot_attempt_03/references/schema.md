# Atlas Commerce Operations — Schema Reference

Grounded in `GET /api/schema` and `GET /api/data-dictionary` from the live Atlas workplace service. Use real column names from this file when writing SQL — confirm against a fresh `/api/schema` call if anything looks unfamiliar. **No task-specific answer values appear here; this is the shared data vocabulary.**

## Conventions (from the data dictionary)

- **Timestamps:** ISO-8601 UTC text ending in `Z`. Lexicographic string ordering == chronological ordering.
- **Dates:** `YYYY-MM-DD` text.
- **Money:** `_minor` fields hold the smallest unit of the row `currency`. FX is *USD per one unit* of the foreign currency, keyed by `(rate_date, currency)`.
- **Source rows:** `raw_*` fields preserve upstream values; `canonical_*` fields hold normalized operational values. Corrections and analytics target canonical.

## Tables (21)

Core commerce: `accounts`, `campaigns`, `orders`, `order_lines`, `order_events`, `products`, `shipments`, `warehouses`.
Payments/refunds: `payment_events`, `refund_attempts`, `fx_rates`.
Fulfillment ops: `warehouse_tasks`, `warehouse_task_events`, `employees`, `inventory_movements`, `inventory_snapshots`.
Carrier/support: `carrier_scans`, `support_cases`, `case_events`.
Governance/ingest: `correction_audit`, `source_import_batches`.

## Key tables and the columns each request family reaches for

### `orders`
`order_id` (PK), `account_id`, `campaign_id` (nullable FK→campaigns), `warehouse_id`, `order_created_at`, `promised_at`, `currency`, `current_status`, `gross_amount_minor` (≥0, minor units).

### `order_lines`
`(order_id, line_id)` PK, `sku`, `quantity_each` (>0).

### `order_events`
`event_id` PK, `order_id`, `event_type`, `event_at`, `source_system`, `external_event_id`, `ingested_at`, `metadata_json` (default `'{}'`). Event types (observed): `ALLOCATED, CANCELLED, CREATED, DELIVERED, PACKED, PAYMENT_CONFIRMED, SHIPPED`.

### `shipments`
`shipment_id` PK, `order_id`, `carrier_code`, `warehouse_id`, `shipped_at` (nullable), `promised_delivery_at` (NOT NULL), `current_status`. Shipment statuses (observed): `DELIVERED, IN_TRANSIT, LABEL_CREATED`. An order may have zero, one, or many shipments.

### `campaigns`
`campaign_id` PK, `campaign_name` (unique), `starts_at`, `ends_at`, `channel`. A campaign's "official active window" is `[starts_at, ends_at]`.

### `warehouses`
`warehouse_id` PK, `warehouse_name`, `region`, `timezone`, `daily_cutoff_local`. Region is the warehouse's business region used for regional rollups. Regions (observed): `CENTRAL, EAST, NORTH, SOUTH, WEST`.

### `accounts`
`account_id` PK, `account_name`, `segment`, `tier`, `region`, `currency`, `is_internal` (0/1), `is_test` (0/1), `created_at`.
- `segment` ∈ {`CONSUMER, SMB, ENTERPRISE, STRATEGIC`}
- `tier` ∈ {`STANDARD, SILVER, GOLD, PLATINUM`}
- **Production population** = `is_test = 0` (and typically `is_internal = 0`). Pair `segment`/`tier`/`region` filters with this exclusion.

### `payment_events`
`payment_event_id` PK, `order_id`, `provider`, `event_type`, `amount_minor`, `currency`, `event_at`, `linked_event_id`. Event types (observed): `AUTHORIZED, CAPTURED`.

### `refund_attempts`
`refund_row_id` PK, `refund_id`, `order_id`, `provider`, `status`, `reason_code`, `amount_minor` (≥0), `currency`, `service_date` (`YYYY-MM-DD`), `event_at`, `linked_refund_id`.
- `status` ∈ {`FAILED, REVERSED, SETTLED, VOIDED`} — "effective settled logical refund" typically means `status = SETTLED`; `linked_refund_id` chains a reversal to the refund it reverses.
- `reason_code` ∈ {`CUSTOMER_RETURN, DAMAGED, DUPLICATE_CHARGE, LATE_DELIVERY, NOT_AS_DESCRIBED`}
- Currencies (observed): `AUD, CAD, EUR, GBP, USD`.

### `fx_rates`
`(rate_date, currency)` PK, `usd_per_unit` (>0). Join on the refund/order service or effective date and the row currency. USD→USD requires no conversion (rate identity).

### `carrier_scans`
`scan_row_id` PK, `shipment_id` (FK→shipments), `source_system`, `external_event_id`, `raw_status`, `raw_event_at`, `canonical_status`, `canonical_event_at`, `ingested_at`, `import_batch_id` (FK→source_import_batches), `corrected_at` (nullable), `correction_reason` (nullable).
- `canonical_status` / `raw_status` ∈ {`AT_HUB, DELIVERED, IN_TRANSIT, LABEL_CREATED, OUT_FOR_DELIVERY, PICKED_UP`}
- This is the mutable correction target (canonical field + `corrected_at` + `correction_reason`).

### `support_cases`
`case_id` PK, `account_id`, `order_id` (nullable FK→orders), `priority`, `opened_at`, `current_status`, `current_owner_team`.
- `priority` ∈ {`URGENT, HIGH, MEDIUM, LOW`}
- `current_status` ∈ {`OPEN, REOPENED, RESOLVED`}
- "Active at cutoff" = `OPEN` or `REOPENED`; "reopened subset" = `REOPENED`.

### `case_events`
`case_event_id` PK, `case_id`, `event_type`, `event_at`, `actor_type`, `source_system`, `external_event_id`, `ingested_at`.
- `event_type` ∈ {`OPENED, OPEN, ASSIGNED, AGENT_RESPONDED, CUSTOMER_REPLIED, WAITING_CUSTOMER, ESCALATED, REOPENED, RESOLVED`}
- First-agent response ≈ earliest `AGENT_RESPONDED` event_at for the case.

### `warehouse_tasks`
`task_id` PK, `warehouse_id`, `order_id` (nullable), `sku` (nullable), `assigned_employee_id` (FK→employees), `task_type`, `work_class`, `priority`, `planned_units` (>0), `created_at`, `due_at`, `current_status`.
- `work_class` ∈ {`PRODUCTION, TRAINING`} — "production-task" eligibility keys on `PRODUCTION`.
- `priority` ∈ {`URGENT, HIGH, NORMAL`} — "high priority" = `URGENT` or `HIGH`.
- `current_status` ∈ {`CREATED, IN_PROGRESS, COMPLETED, REWORK`} — `REWORK` rows count toward the rework metric; completion keys on `COMPLETED`.
- `task_type` ∈ {`PICK, PACK, RECEIVE, REPLENISH`}.

### `warehouse_task_events`
`task_event_id` PK, `task_id`, `event_type`, `event_at`, `units` (≥0), `productive_minutes` (>0), `source_system`, `external_event_id`, `ingested_at`.
- `event_type` ∈ {`CREATED, STARTED, IN_PROGRESS, COMPLETED, REWORK`}.
- Completed-production units and the productive minutes *attached to those completed units* come from this table joined to `warehouse_tasks` on `task_id`. Units per hour = (total completed units / total productive minutes) × 60.

### `employees`
`employee_id` PK, `warehouse_id`, `team_id`, `role`, `active_from`, `active_to` (nullable). `team_id` is the unit for lowest-performing-team ranking.

### `inventory_movements`
`movement_row_id` PK, `movement_id`, `warehouse_id`, `sku`, `movement_type`, `raw_quantity`, `raw_uom`, `raw_uom_multiplier`, `canonical_quantity_each`, `canonical_uom_multiplier`, `occurred_at`, `source_system`, `external_event_id`, `ingested_at`, `source_document_id`, `corrected_at`, `correction_reason`. This is the second allowed correction target (canonical quantity/UOM fields, with `corrected_at`/`correction_reason`).

### `correction_audit`
`audit_id` PK, `correction_key` (unique idempotency key), `entity_type`, `entity_id`, `source_row_id`, `field_name`, `old_value`, `new_value`, `reason_code`, `corrected_at`, `actor`. Every committed correction inserts exactly one row here with all 11 columns. `GET /api/correction-audit` exposes committed rows; it starts empty at the beginning of a run.

### `source_import_batches`
`import_batch_id` PK, `source_system`, `entity_type`, `started_at`, `completed_at`, `record_count` (≥0), `status`. "Named batch" / `import_batch_id` scopes carrier-scan cohorts.

### `products`, `inventory_snapshots`
`products(sku PK, …)`; `inventory_snapshots(warehouse_id, sku, snapshot_at, on_hand_each, reserved_each, source_system)`. Used for SKU/inventory contexts not central to the five canonical request families but present in the schema.

## ID shapes (for pattern checks in emitted answers)

Observed stable identifiers and their formats: orders `ORD-######`, shipments `SHP-######`, carrier scans `SCN-#######`, tasks `WT-######`, employees `EMP-####`, teams like `<warehouse_id>-TEAM-#`, accounts `ACC-####`, support cases `CASE-######`. Emitted arrays must respect each template's `pattern` constraints.
