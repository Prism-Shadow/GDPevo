# Atlas Commerce Operations — Schema Reference

Complete DDL and indexes for all tables in the Atlas Commerce database (`schema_version: atlas-commerce-1.0`).

## Table: accounts

```sql
CREATE TABLE accounts (
    account_id TEXT PRIMARY KEY,
    account_name TEXT NOT NULL,
    segment TEXT NOT NULL CHECK (segment IN ('CONSUMER','SMB','ENTERPRISE','STRATEGIC')),
    tier TEXT NOT NULL CHECK (tier IN ('STANDARD','SILVER','GOLD','PLATINUM')),
    region TEXT NOT NULL,
    currency TEXT NOT NULL,
    is_internal INTEGER NOT NULL CHECK (is_internal IN (0,1)),
    is_test INTEGER NOT NULL CHECK (is_test IN (0,1)),
    created_at TEXT NOT NULL
)
```

## Table: campaigns

```sql
CREATE TABLE campaigns (
    campaign_id TEXT PRIMARY KEY,
    campaign_name TEXT NOT NULL UNIQUE,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    channel TEXT NOT NULL
)
```

## Table: carrier_scans

```sql
CREATE TABLE carrier_scans (
    scan_row_id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES shipments(shipment_id),
    source_system TEXT NOT NULL,
    external_event_id TEXT NOT NULL,
    raw_status TEXT NOT NULL,
    raw_event_at TEXT NOT NULL,
    canonical_status TEXT NOT NULL,
    canonical_event_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    import_batch_id TEXT NOT NULL REFERENCES source_import_batches(import_batch_id),
    corrected_at TEXT,
    correction_reason TEXT
)
```

## Table: case_events

```sql
CREATE TABLE case_events (
    case_event_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES support_cases(case_id),
    event_type TEXT NOT NULL,
    event_at TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    source_system TEXT NOT NULL,
    external_event_id TEXT NOT NULL,
    ingested_at TEXT NOT NULL
)
```

## Table: correction_audit

```sql
CREATE TABLE correction_audit (
    audit_id TEXT PRIMARY KEY,
    correction_key TEXT NOT NULL UNIQUE,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    source_row_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason_code TEXT NOT NULL,
    corrected_at TEXT NOT NULL,
    actor TEXT NOT NULL
)
```

## Table: employees

```sql
CREATE TABLE employees (
    employee_id TEXT PRIMARY KEY,
    warehouse_id TEXT NOT NULL REFERENCES warehouses(warehouse_id),
    team_id TEXT NOT NULL,
    role TEXT NOT NULL,
    active_from TEXT NOT NULL,
    active_to TEXT
)
```

## Table: fx_rates

```sql
CREATE TABLE fx_rates (
    rate_date TEXT NOT NULL,
    currency TEXT NOT NULL,
    usd_per_unit REAL NOT NULL CHECK (usd_per_unit > 0),
    PRIMARY KEY (rate_date, currency)
)
```

## Table: inventory_movements

```sql
CREATE TABLE inventory_movements (
    movement_row_id TEXT PRIMARY KEY,
    movement_id TEXT NOT NULL,
    warehouse_id TEXT NOT NULL REFERENCES warehouses(warehouse_id),
    sku TEXT NOT NULL REFERENCES products(sku),
    movement_type TEXT NOT NULL,
    raw_quantity INTEGER NOT NULL,
    raw_uom TEXT NOT NULL,
    raw_uom_multiplier INTEGER NOT NULL CHECK (raw_uom_multiplier > 0),
    canonical_quantity_each INTEGER NOT NULL,
    canonical_uom_multiplier INTEGER NOT NULL CHECK (canonical_uom_multiplier > 0),
    occurred_at TEXT NOT NULL,
    source_system TEXT NOT NULL,
    external_event_id TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    source_document_id TEXT NOT NULL,
    corrected_at TEXT,
    correction_reason TEXT
)
```

## Table: inventory_snapshots

```sql
CREATE TABLE inventory_snapshots (
    warehouse_id TEXT NOT NULL REFERENCES warehouses(warehouse_id),
    sku TEXT NOT NULL REFERENCES products(sku),
    snapshot_at TEXT NOT NULL,
    on_hand_each INTEGER NOT NULL,
    reserved_each INTEGER NOT NULL,
    source_system TEXT NOT NULL,
    PRIMARY KEY (warehouse_id, sku, snapshot_at)
)
```

## Table: order_events

```sql
CREATE TABLE order_events (
    event_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    event_type TEXT NOT NULL,
    event_at TEXT NOT NULL,
    source_system TEXT NOT NULL,
    external_event_id TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
)
```

## Table: order_lines

```sql
CREATE TABLE order_lines (
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    line_id INTEGER NOT NULL,
    sku TEXT NOT NULL REFERENCES products(sku),
    quantity_each INTEGER NOT NULL CHECK (quantity_each > 0),
    PRIMARY KEY (order_id, line_id)
)
```

## Table: orders

```sql
CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    campaign_id TEXT REFERENCES campaigns(campaign_id),
    warehouse_id TEXT NOT NULL REFERENCES warehouses(warehouse_id),
    order_created_at TEXT NOT NULL,
    promised_at TEXT NOT NULL,
    currency TEXT NOT NULL,
    current_status TEXT NOT NULL,
    gross_amount_minor INTEGER NOT NULL CHECK (gross_amount_minor >= 0)
)
```

## Table: payment_events

```sql
CREATE TABLE payment_events (
    payment_event_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    provider TEXT NOT NULL,
    source_system TEXT NOT NULL,
    external_event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    amount_minor INTEGER NOT NULL,
    currency TEXT NOT NULL,
    event_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    linked_event_id TEXT
)
```

## Table: products

```sql
CREATE TABLE products (
    sku TEXT PRIMARY KEY,
    product_family TEXT NOT NULL,
    unit_weight_grams INTEGER NOT NULL CHECK (unit_weight_grams > 0),
    units_per_case INTEGER NOT NULL CHECK (units_per_case > 0),
    is_active INTEGER NOT NULL CHECK (is_active IN (0,1))
)
```

## Table: refund_attempts

```sql
CREATE TABLE refund_attempts (
    refund_row_id TEXT PRIMARY KEY,
    refund_id TEXT NOT NULL,
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    provider TEXT NOT NULL,
    source_system TEXT NOT NULL,
    external_event_id TEXT NOT NULL,
    status TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK (amount_minor >= 0),
    currency TEXT NOT NULL,
    service_date TEXT NOT NULL,
    event_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    linked_refund_id TEXT
)
```

## Table: shipments

```sql
CREATE TABLE shipments (
    shipment_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    carrier_code TEXT NOT NULL,
    warehouse_id TEXT NOT NULL REFERENCES warehouses(warehouse_id),
    shipped_at TEXT,
    promised_delivery_at TEXT NOT NULL,
    current_status TEXT NOT NULL
)
```

## Table: source_import_batches

```sql
CREATE TABLE source_import_batches (
    import_batch_id TEXT PRIMARY KEY,
    source_system TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    record_count INTEGER NOT NULL CHECK (record_count >= 0),
    status TEXT NOT NULL
)
```

## Table: support_cases

```sql
CREATE TABLE support_cases (
    case_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    order_id TEXT REFERENCES orders(order_id),
    priority TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    current_status TEXT NOT NULL,
    current_owner_team TEXT NOT NULL
)
```

## Table: warehouse_task_events

```sql
CREATE TABLE warehouse_task_events (
    task_event_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES warehouse_tasks(task_id),
    event_type TEXT NOT NULL,
    event_at TEXT NOT NULL,
    units INTEGER NOT NULL CHECK (units >= 0),
    productive_minutes INTEGER NOT NULL CHECK (productive_minutes >= 0),
    source_system TEXT NOT NULL,
    external_event_id TEXT NOT NULL,
    ingested_at TEXT NOT NULL
)
```

## Table: warehouse_tasks

```sql
CREATE TABLE warehouse_tasks (
    task_id TEXT PRIMARY KEY,
    warehouse_id TEXT NOT NULL REFERENCES warehouses(warehouse_id),
    order_id TEXT REFERENCES orders(order_id),
    sku TEXT REFERENCES products(sku),
    assigned_employee_id TEXT NOT NULL REFERENCES employees(employee_id),
    task_type TEXT NOT NULL,
    work_class TEXT NOT NULL CHECK (work_class IN ('PRODUCTION','TRAINING')),
    priority TEXT NOT NULL,
    planned_units INTEGER NOT NULL CHECK (planned_units >= 0),
    created_at TEXT NOT NULL,
    due_at TEXT NOT NULL,
    current_status TEXT NOT NULL
)
```

## Table: warehouses

```sql
CREATE TABLE warehouses (
    warehouse_id TEXT PRIMARY KEY,
    warehouse_name TEXT NOT NULL,
    region TEXT NOT NULL,
    timezone TEXT NOT NULL,
    daily_cutoff_local TEXT NOT NULL
)
```

## Indexes

```sql
CREATE INDEX idx_accounts_segment_region ON accounts(segment, region);
CREATE INDEX idx_orders_account_created ON orders(account_id, order_created_at);
CREATE INDEX idx_orders_campaign_created ON orders(campaign_id, order_created_at);
CREATE INDEX idx_orders_warehouse_promised ON orders(warehouse_id, promised_at);
CREATE INDEX idx_shipments_order ON shipments(order_id);
CREATE INDEX idx_shipments_warehouse_promised ON shipments(warehouse_id, promised_delivery_at);
CREATE INDEX idx_scans_batch ON carrier_scans(import_batch_id);
CREATE INDEX idx_scans_dedupe ON carrier_scans(source_system, external_event_id, ingested_at);
CREATE INDEX idx_scans_shipment_effective ON carrier_scans(shipment_id, canonical_event_at, scan_row_id);
CREATE INDEX idx_order_events_dedupe ON order_events(source_system, external_event_id, ingested_at);
CREATE INDEX idx_order_events_effective ON order_events(order_id, event_at, event_id);
CREATE INDEX idx_refunds_dedupe ON refund_attempts(source_system, external_event_id, ingested_at);
CREATE INDEX idx_refunds_order_service ON refund_attempts(order_id, service_date);
CREATE INDEX idx_payments_dedupe ON payment_events(source_system, external_event_id, ingested_at);
CREATE INDEX idx_payments_order_event ON payment_events(order_id, event_at);
CREATE INDEX idx_task_events_dedupe ON warehouse_task_events(source_system, external_event_id, ingested_at);
CREATE INDEX idx_task_events_effective ON warehouse_task_events(task_id, event_at, task_event_id);
CREATE INDEX idx_tasks_employee ON warehouse_tasks(assigned_employee_id, created_at);
CREATE INDEX idx_tasks_warehouse_due ON warehouse_tasks(warehouse_id, due_at);
CREATE INDEX idx_case_events_dedupe ON case_events(source_system, external_event_id, ingested_at);
CREATE INDEX idx_case_events_effective ON case_events(case_id, event_at, case_event_id);
CREATE INDEX idx_cases_account_opened ON support_cases(account_id, opened_at);
CREATE INDEX idx_audit_entity ON correction_audit(entity_type, entity_id, corrected_at);
CREATE INDEX idx_movements_dedupe ON inventory_movements(source_system, external_event_id, ingested_at);
CREATE INDEX idx_movements_warehouse_sku_time ON inventory_movements(warehouse_id, sku, occurred_at);
CREATE INDEX idx_snapshots_time ON inventory_snapshots(snapshot_at, warehouse_id);
```
