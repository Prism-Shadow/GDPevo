# Atlas Commerce Schema Reference

Complete table catalog with DDL and column descriptions.

## accounts

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

| Column | Description |
|--------|-------------|
| account_id | Stable business identifier |
| account_name | Account name |
| segment | CONSUMER, SMB, ENTERPRISE, STRATEGIC |
| tier | STANDARD, SILVER, GOLD, PLATINUM |
| region | Region label |
| currency | Account currency |
| is_internal | 1 = internal, 0 = external |
| is_test | 1 = test, 0 = production |
| created_at | ISO-8601 UTC |

Production filter: `is_internal = 0 AND is_test = 0`

## campaigns

```sql
CREATE TABLE campaigns (
    campaign_id TEXT PRIMARY KEY,
    campaign_name TEXT NOT NULL UNIQUE,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    channel TEXT NOT NULL
)
```

| Column | Description |
|--------|-------------|
| campaign_id | Stable campaign identifier |
| campaign_name | Unique campaign name |
| starts_at | UTC window start |
| ends_at | UTC window end |
| channel | Acquisition channel |

## carrier_scans

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

| Column | Description |
|--------|-------------|
| scan_row_id | Stable row identifier |
| shipment_id | References shipments |
| source_system | Upstream system identifier |
| external_event_id | Upstream event id (use for dedup) |
| raw_status | Carrier-supplied status text |
| raw_event_at | Carrier-supplied UTC timestamp |
| canonical_status | Normalized operational status |
| canonical_event_at | Normalized UTC timestamp |
| ingested_at | UTC when row reached the database |
| import_batch_id | Source import batch |
| corrected_at | UTC of approved correction or null |
| correction_reason | Short reason or null |

**Deduplication**: Keep latest `ingested_at` per `(source_system, external_event_id)`.
**Effective scan**: Per shipment, use latest `canonical_event_at`, tie-break on latest `scan_row_id`.

Indexes: `idx_scans_dedupe`, `idx_scans_shipment_effective`, `idx_scans_batch`

## case_events

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

| Column | Description |
|--------|-------------|
| case_event_id | Stable row identifier |
| case_id | References support_cases |
| event_type | Lifecycle event type |
| event_at | UTC timestamp |
| actor_type | Actor type (e.g., AGENT, CUSTOMER, SYSTEM) |
| source_system | Upstream system |
| external_event_id | Upstream event id (use for dedup) |
| ingested_at | UTC when row reached the database |

**Deduplication**: Keep latest `ingested_at` per `(source_system, external_event_id)`.
**Active time computation**: Time between events is "active" when `actor_type` is not `SYSTEM`. Compute elapsed hours between successive events per case, summing only active intervals.

Indexes: `idx_case_events_dedupe`, `idx_case_events_effective`

## correction_audit

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

Public audit records appended by transactional corrections.

Index: `idx_audit_entity`

## employees

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

| Column | Description |
|--------|-------------|
| employee_id | Stable employee identifier |
| warehouse_id | Assigned warehouse |
| team_id | Team assignment |
| role | Role |
| active_from | UTC start of active period |
| active_to | UTC end of active period or null |

## fx_rates

```sql
CREATE TABLE fx_rates (
    rate_date TEXT NOT NULL,
    currency TEXT NOT NULL,
    usd_per_unit REAL NOT NULL CHECK (usd_per_unit > 0),
    PRIMARY KEY (rate_date, currency)
)
```

| Column | Description |
|--------|-------------|
| rate_date | YYYY-MM-DD calendar date |
| currency | Source currency |
| usd_per_unit | USD value of one unit of the source currency |

**FX conversion**: `amount_usd = (amount_minor / 100) * usd_per_unit` for currencies where 1 major = 100 minor units.
Generically: `amount_usd = amount_in_source_currency * usd_per_unit`. Convert minor amounts to major first.

## inventory_movements

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

Indexes: `idx_movements_dedupe`, `idx_movements_warehouse_sku_time`

## inventory_snapshots

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

Index: `idx_snapshots_time`

## order_events

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

| Column | Description |
|--------|-------------|
| event_id | Stable event identifier |
| order_id | References orders |
| event_type | Lifecycle event type |
| event_at | UTC timestamp |
| source_system | Upstream system |
| external_event_id | Upstream event id (use for dedup) |
| ingested_at | UTC when row reached the database |
| metadata_json | Source event attributes as JSON string |

Indexes: `idx_order_events_dedupe`, `idx_order_events_effective`

## order_lines

```sql
CREATE TABLE order_lines (
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    line_id INTEGER NOT NULL,
    sku TEXT NOT NULL REFERENCES products(sku),
    quantity_each INTEGER NOT NULL CHECK (quantity_each > 0),
    PRIMARY KEY (order_id, line_id)
)
```

## orders

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

| Column | Description |
|--------|-------------|
| order_id | Unique order identifier (ORD-NNNNNN) |
| account_id | Owning account |
| campaign_id | Attribution campaign or null |
| warehouse_id | Fulfilling warehouse |
| order_created_at | UTC creation timestamp |
| promised_at | UTC fulfillment promise |
| currency | Order currency |
| current_status | Snapshot status (may lag events) |
| gross_amount_minor | Gross value in smallest currency unit (>= 0) |

Indexes: `idx_orders_account_created`, `idx_orders_campaign_created`, `idx_orders_warehouse_promised`

## payment_events

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

Indexes: `idx_payments_dedupe`, `idx_payments_order_event`

## products

```sql
CREATE TABLE products (
    sku TEXT PRIMARY KEY,
    product_family TEXT NOT NULL,
    unit_weight_grams INTEGER NOT NULL CHECK (unit_weight_grams > 0),
    units_per_case INTEGER NOT NULL CHECK (units_per_case > 0),
    is_active INTEGER NOT NULL CHECK (is_active IN (0,1))
)
```

## refund_attempts

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

| Column | Description |
|--------|-------------|
| refund_row_id | Stable row identifier |
| refund_id | Logical refund identifier |
| order_id | References orders |
| provider | Payment provider |
| source_system | Upstream system |
| external_event_id | Upstream event id (use for dedup) |
| status | Refund status (SETTLED, FAILED, etc.) |
| reason_code | Refund reason |
| amount_minor | Amount in smallest currency unit (>= 0) |
| currency | Refund currency |
| service_date | YYYY-MM-DD effective service date |
| event_at | UTC event timestamp |
| ingested_at | UTC when row reached the database |
| linked_refund_id | Linked reversal refund id or null |

**Settled refund**: `status = 'SETTLED'`
**Reversal**: A refund with `linked_refund_id` not null (it reverses a prior settled refund)
**Deduplication**: Keep latest `ingested_at` per `(source_system, external_event_id)`.

Indexes: `idx_refunds_dedupe`, `idx_refunds_order_service`

## shipments

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

| Column | Description |
|--------|-------------|
| shipment_id | Unique shipment identifier (SHP-NNNNNN) |
| order_id | Parent order |
| carrier_code | Carrier identifier |
| warehouse_id | Origin warehouse |
| shipped_at | UTC ship timestamp or null |
| promised_delivery_at | UTC delivery promise |
| current_status | Snapshot status (may lag scans) |

Indexes: `idx_shipments_order`, `idx_shipments_warehouse_promised`

## source_import_batches

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

## support_cases

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

| Column | Description |
|--------|-------------|
| case_id | Unique case identifier (CASE-NNNNNN) |
| account_id | Owning account |
| order_id | Related order or null |
| priority | URGENT, HIGH, MEDIUM, LOW |
| opened_at | UTC open timestamp |
| current_status | Snapshot status (OPEN, REOPENED, RESOLVED, CLOSED) |
| current_owner_team | Current team assignment |

Index: `idx_cases_account_opened`

## warehouse_task_events

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

| Column | Description |
|--------|-------------|
| task_event_id | Stable event identifier |
| task_id | References warehouse_tasks |
| event_type | Lifecycle event type |
| event_at | UTC timestamp |
| units | Completed units in this event |
| productive_minutes | Productive work minutes in this event |
| source_system | Upstream system |
| external_event_id | Upstream event id (use for dedup) |
| ingested_at | UTC when row reached the database |

**Completion**: Sum `units` across events where `event_type` indicates completion.
**Productivity**: `units_per_hour = (total completed units / total productive minutes) * 60`.

## warehouse_tasks

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

| Column | Description |
|--------|-------------|
| task_id | Unique task identifier (WT-NNNNNN) |
| warehouse_id | Assigned warehouse |
| order_id | Related order or null |
| sku | SKU being handled or null |
| assigned_employee_id | Assigned employee |
| task_type | Task type (e.g., PICK, PACK, REWORK) |
| work_class | PRODUCTION or TRAINING |
| priority | LOW, MEDIUM, HIGH, URGENT |
| planned_units | Planned unit quantity |
| created_at | UTC creation timestamp |
| due_at | UTC due date |
| current_status | Snapshot status |

## warehouses

```sql
CREATE TABLE warehouses (
    warehouse_id TEXT PRIMARY KEY,
    warehouse_name TEXT NOT NULL,
    region TEXT NOT NULL,
    timezone TEXT NOT NULL,
    daily_cutoff_local TEXT NOT NULL
)
```

| Column | Description |
|--------|-------------|
| warehouse_id | Unique warehouse identifier |
| warehouse_name | Display name |
| region | Business region |
| timezone | IANA timezone |
| daily_cutoff_local | Local daily cutoff time |
