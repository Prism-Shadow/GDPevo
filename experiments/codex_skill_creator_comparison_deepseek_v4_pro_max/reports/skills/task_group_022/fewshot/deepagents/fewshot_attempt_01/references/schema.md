# Atlas Commerce Operations Schema

## Entity Relationships

The database models a retail fulfillment and support operation with these core entity chains:

**Orders -> Shipments -> Carrier Scans**
orders.order_id -> shipments.order_id -> carrier_scans.shipment_id

**Orders -> Payments / Refunds**
orders.order_id -> payment_events.order_id
orders.order_id -> refund_attempts.order_id

**Orders -> Order Lines -> Products**
orders.order_id -> order_lines.order_id
order_lines.sku -> products.sku

**Accounts -> Orders -> Support Cases**
accounts.account_id -> orders.account_id
accounts.account_id -> support_cases.account_id
support_cases.order_id -> orders.order_id (nullable)

**Warehouses -> Orders / Shipments / Tasks / Employees**
warehouses.warehouse_id -> orders.warehouse_id
warehouses.warehouse_id -> shipments.warehouse_id
warehouses.warehouse_id -> warehouse_tasks.warehouse_id
warehouses.warehouse_id -> employees.warehouse_id

**Warehouse Tasks -> Task Events**
warehouse_tasks.task_id -> warehouse_task_events.task_id
warehouse_tasks.order_id -> orders.order_id (nullable)
warehouse_tasks.sku -> products.sku (nullable)
warehouse_tasks.assigned_employee_id -> employees.employee_id

**Campaigns -> Orders**
campaigns.campaign_id -> orders.campaign_id (nullable)

**Source Import Batches -> Carrier Scans**
source_import_batches.import_batch_id -> carrier_scans.import_batch_id

**Correction Audit**
correction_audit.source_row_id references the corrected table's row identifier.
correction_audit.entity_id references the business entity (e.g., shipment_id).

**FX Rates**
fx_rates.rate_date + fx_rates.currency join with refund_attempts.service_date + currency
or payment_events.event_at date + currency.

**Inventory Movements**
inventory_movements.warehouse_id -> warehouses.warehouse_id
inventory_movements.sku -> products.sku
inventory_movements.source_document_id references a business document.

**Inventory Snapshots**
inventory_snapshots.warehouse_id -> warehouses.warehouse_id
inventory_snapshots.sku -> products.sku

## Table Details

### accounts
- `is_internal` (1/0): internal/employee accounts. Exclude for production analysis.
- `is_test` (1/0): test accounts. Exclude for production analysis.
- `segment`: CONSUMER, SMB, ENTERPRISE, STRATEGIC.
- `tier`: STANDARD, SILVER, GOLD, PLATINUM.
- `region`: NORTH, SOUTH, EAST, CENTRAL, WEST.

### campaigns
- `starts_at` and `ends_at` define the official active window.
- `channel` is the acquisition channel.

### carrier_scans
- Deduplicate on `source_system` + `external_event_id` (keep earliest `ingested_at`).
- `raw_status` is the carrier-supplied value; `canonical_status` is the normalized value.
- `canonical_event_at` is the normalized timestamp; use it for effective ordering.
- `corrected_at` and `correction_reason` are null unless a canonical correction was applied.
- One carrier scan row per observation; a shipment can have multiple scans.

### case_events
- Deduplicate on `source_system` + `external_event_id`.
- `event_type` values include: OPEN, NOTE, AGENT_RESPOND, REOPEN, RESOLVE, CLOSE.
- `actor_type`: AGENT or CUSTOMER.
- `event_at`: when the event occurred in business time.

### correction_audit
- `audit_id`: unique audit record identifier.
- `correction_key`: caller-provided idempotency key.
- `entity_type`: the type of corrected entity (e.g., carrier_scan).
- `entity_id`: the business entity identifier (e.g., shipment_id).
- `source_row_id`: the specific row that was corrected (e.g., scan_row_id).
- `field_name`: the column that was changed.
- `old_value` and `new_value`: before and after values.
- `reason_code`: SOURCE_RECONCILIATION or other approved codes.
- `corrected_at`: UTC timestamp of the correction.
- `actor`: identity that performed the correction.

### employees
- `role`: the employee's job role.
- `active_from` and `active_to` (nullable): the employment active window.
- `team_id`: groups employees under a warehouse team.

### fx_rates
- Primary key: `(rate_date, currency)`.
- `usd_per_unit`: USD value of one unit of the named currency.
- For conversion: `amount_in_row_currency * usd_per_unit = amount_in_usd`.

### inventory_movements
- Deduplicate on `source_system` + `external_event_id`.
- `raw_quantity` and `raw_uom` preserve source values.
- `canonical_quantity_each` is the normalized each-unit quantity.
- `occurred_at` is the business time of the movement.

### inventory_snapshots
- Primary key: `(warehouse_id, sku, snapshot_at)`.
- `on_hand_each`: total units physically present.
- `reserved_each`: units allocated to orders but not yet shipped.

### order_events
- Deduplicate on `source_system` + `external_event_id`.
- `event_type` values include: CREATED, CONFIRMED, SHIPPED, DELIVERED, CANCELED.
- Append-only: the current state of an order is the latest event by `event_at`.
- `metadata_json`: JSON string with extra event attributes.

### order_lines
- Primary key: `(order_id, line_id)`.
- `quantity_each`: number of individual units of the SKU on this line.

### orders
- `campaign_id` can be null (orders not attributed to a campaign).
- `order_created_at`: when the order was placed.
- `promised_at`: the overall order promise timestamp.
- `current_status`: denormalized snapshot, may lag event history.
- `gross_amount_minor`: gross order value in smallest currency unit.

### payment_events
- Deduplicate on `source_system` + `external_event_id`.
- `event_type` values include: AUTHORIZE, SETTLE, VOID, REVERSAL.
- `linked_event_id` (nullable): links a reversal to its original payment event.
- `amount_minor`: in smallest unit of the named currency.

### products
- `product_family`: grouping category.
- `unit_weight_grams`: weight of one individual unit.
- `units_per_case`: how many individual units per case.
- `is_active`: 1/0 flag.

### refund_attempts
- Deduplicate on `source_system` + `external_event_id`.
- `status` values include: SETTLED, FAILED, PENDING.
- `reason_code`: e.g., DAMAGED, NOT_AS_DESCRIBED, DEFECTIVE, WRONG_ITEM.
- `linked_refund_id` (nullable): links a reversal refund to the refund being reversed.
- `service_date`: the business date for FX rate lookup.
- `amount_minor`: in smallest unit of the named currency.

### shipments
- `shipped_at` (nullable): when the shipment left the warehouse; null if not yet shipped.
- `promised_delivery_at`: carrier delivery promise.
- `current_status`: denormalized snapshot, may lag scan history.
- `carrier_code`: identifier for the shipping carrier.

### source_import_batches
- `entity_type`: the type of entity imported (e.g., carrier_scan).
- `started_at` and `completed_at`: import window.
- `record_count`: number of source records in the batch.
- `status`: COMPLETED, PARTIAL, FAILED.

### support_cases
- `priority`: URGENT, HIGH, MEDIUM, LOW.
- `opened_at`: when the case was opened in business time.
- `current_status`: denormalized snapshot (OPEN, REOPENED, RESOLVED, CLOSED).
- `current_owner_team`: team currently assigned.
- `order_id` (nullable): linked order, if any.

### warehouse_task_events
- Deduplicate on `source_system` + `external_event_id`.
- `event_type` values include: ASSIGNED, STARTED, PROGRESS, COMPLETED, CANCELED.
- `units`: units processed in this event.
- `productive_minutes`: productive work minutes for this event.

### warehouse_tasks
- `work_class`: PRODUCTION or TRAINING. Exclude TRAINING for production analysis.
- `task_type`: PICK, PACK, SORT, REWORK, etc.
- `priority`: LOW, MEDIUM, HIGH, URGENT.
- `planned_units`: planned unit count.
- `created_at`: when the task was generated.
- `due_at`: task deadline.
- `current_status`: denormalized snapshot.

### warehouses
- `region`: NORTH, SOUTH, EAST, CENTRAL, WEST.
- `timezone`: IANA timezone identifier.
- `daily_cutoff_local`: local time string for daily operational cutoff.

## Key Indexes

- `idx_scans_batch`: `carrier_scans(import_batch_id)` -- fast batch-scoped scan lookup.
- `idx_scans_shipment_effective`: `carrier_scans(shipment_id, canonical_event_at, scan_row_id)` -- effective final scan per shipment.
- `idx_orders_campaign_created`: `orders(campaign_id, order_created_at)` -- campaign-scoped order retrieval.
- `idx_orders_warehouse_promised`: `orders(warehouse_id, promised_at)` -- warehouse-scoped order promise analysis.
- `idx_orders_account_created`: `orders(account_id, order_created_at)` -- account-scoped order queries.
- `idx_shipments_order`: `shipments(order_id)` -- fast order-to-shipment join.
- `idx_shipments_warehouse_promised`: `shipments(warehouse_id, promised_delivery_at)` -- warehouse-scoped delivery promise.
- `idx_refunds_order_service`: `refund_attempts(order_id, service_date)` -- order-scoped refunds by service date.
- `idx_cases_account_opened`: `support_cases(account_id, opened_at)` -- account-scoped cases by open date.
- `idx_accounts_segment_region`: `accounts(segment, region)` -- segment+region filtering.
- `idx_tasks_warehouse_due`: `warehouse_tasks(warehouse_id, due_at)` -- warehouse-scoped task deadlines.
- `idx_tasks_employee`: `warehouse_tasks(assigned_employee_id, created_at)` -- employee task assignments.
- `idx_task_events_effective`: `warehouse_task_events(task_id, event_at, task_event_id)` -- effective task event ordering.
- `idx_case_events_effective`: `case_events(case_id, event_at, case_event_id)` -- effective case event ordering.
- `idx_audit_entity`: `correction_audit(entity_type, entity_id, corrected_at)` -- audit lookup by entity.
