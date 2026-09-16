# Atlas Commerce Operations — Schema Reference

Always verify against `GET /api/schema` and `GET /api/data-dictionary`. This
is a snapshot for quick lookup; the live responses are authoritative.

## Conventions

| Convention | Rule |
|---|---|
| Timestamps | ISO-8601 UTC, ending in `Z` |
| Dates | `YYYY-MM-DD` |
| Money minor | Smallest unit of the row currency (divide by 100 for display) |
| FX rates | `usd_per_unit` = USD per 1 unit of the named currency |
| Integer booleans | `is_internal`, `is_test`, `is_active`: 1 = true, 0 = false |
| Source rows | `raw_*` columns preserve source values; `canonical_*` are normalized |
| Identifiers | Stable business/row IDs; relationships are FOREIGN KEY constraints |

## Table summary

### accounts
Customer/company master. Production filter: `is_internal = 0 AND is_test = 0`.

| Column | Type | Notes |
|---|---|---|
| account_id | TEXT PK | |
| account_name | TEXT | |
| segment | TEXT | CONSUMER, SMB, ENTERPRISE, STRATEGIC |
| tier | TEXT | STANDARD, SILVER, GOLD, PLATINUM |
| region | TEXT | |
| currency | TEXT | Account's billing currency |
| is_internal | INTEGER | 0/1 |
| is_test | INTEGER | 0/1 |
| created_at | TEXT | UTC timestamp |

### campaigns

| Column | Type | Notes |
|---|---|---|
| campaign_id | TEXT PK | |
| campaign_name | TEXT UNIQUE | |
| starts_at | TEXT | UTC timestamp |
| ends_at | TEXT | UTC timestamp |
| channel | TEXT | |

### carrier_scans
Imported carrier observations. The effective final scan for a shipment is the
latest by `canonical_event_at`, tie-broken on `scan_row_id` ASC.

| Column | Type | Notes |
|---|---|---|
| scan_row_id | TEXT PK | |
| shipment_id | TEXT FK → shipments | |
| source_system | TEXT | Do not overwrite |
| external_event_id | TEXT | Do not overwrite |
| raw_status | TEXT | Do not overwrite |
| raw_event_at | TEXT | Do not overwrite |
| canonical_status | TEXT | Normalized; the correctable field |
| canonical_event_at | TEXT | Normalized event time |
| ingested_at | TEXT | |
| import_batch_id | TEXT FK → source_import_batches | |
| corrected_at | TEXT NULL | Set on correction |
| correction_reason | TEXT NULL | Set on correction |

### case_events
Append-only support case lifecycle events.

| Column | Type | Notes |
|---|---|---|
| case_event_id | TEXT PK | |
| case_id | TEXT FK → support_cases | |
| event_type | TEXT | See below for common types |
| event_at | TEXT | UTC timestamp |
| actor_type | TEXT | AGENT, CUSTOMER, SYSTEM |
| source_system | TEXT | |
| external_event_id | TEXT | |
| ingested_at | TEXT | |

Common `event_type` values: `OPENED`, `REOPENED`, `AGENT_RESPONSE`,
`CUSTOMER_RESPONSE`, `RESOLVED`, `CLOSED`, `STATUS_CHANGE`.

### correction_audit
Public audit records for canonical corrections. One row per correction.

| Column | Type | Notes |
|---|---|---|
| audit_id | TEXT PK | From approved correction params |
| correction_key | TEXT UNIQUE | Idempotency key |
| entity_type | TEXT | e.g., `carrier_scan` |
| entity_id | TEXT | Business entity ID |
| source_row_id | TEXT | Corrected row ID |
| field_name | TEXT | Corrected column |
| old_value | TEXT NULL | |
| new_value | TEXT NULL | |
| reason_code | TEXT | e.g., `SOURCE_RECONCILIATION` |
| corrected_at | TEXT | UTC timestamp |
| actor | TEXT | |

### employees
Warehouse employees with active periods.

| Column | Type | Notes |
|---|---|---|
| employee_id | TEXT PK | |
| warehouse_id | TEXT FK → warehouses | |
| team_id | TEXT | |
| role | TEXT | |
| active_from | TEXT | UTC timestamp |
| active_to | TEXT NULL | NULL = still active |

### fx_rates
Daily FX: `usd_per_unit` gives USD per 1 currency unit.

| Column | Type | Notes |
|---|---|---|
| rate_date | TEXT PK | `YYYY-MM-DD` |
| currency | TEXT PK | |
| usd_per_unit | REAL | > 0 |

### order_lines
SKU quantities on an order.

| Column | Type | Notes |
|---|---|---|
| order_id | TEXT PK (part) → orders | |
| line_id | INTEGER PK (part) | |
| sku | TEXT → products | |
| quantity_each | INTEGER | > 0 |

### orders
Order headers. `gross_amount_minor` is in the order's currency smallest unit.

| Column | Type | Notes |
|---|---|---|
| order_id | TEXT PK | |
| account_id | TEXT FK → accounts | |
| campaign_id | TEXT FK → campaigns (nullable) | |
| warehouse_id | TEXT FK → warehouses | |
| order_created_at | TEXT | |
| promised_at | TEXT | |
| currency | TEXT | |
| current_status | TEXT | May lag event history |
| gross_amount_minor | INTEGER | ≥ 0 |

### refund_attempts
Provider refund attempts. `linked_refund_id` connects a reversal to its original
refund. Effective settled refunds: `status = 'SETTLED' AND linked_refund_id IS NULL`.
Effective reversals: `status = 'SETTLED' AND linked_refund_id IS NOT NULL`.

| Column | Type | Notes |
|---|---|---|
| refund_row_id | TEXT PK | |
| refund_id | TEXT | |
| order_id | TEXT FK → orders | |
| provider | TEXT | |
| source_system | TEXT | |
| external_event_id | TEXT | |
| status | TEXT | SETTLED, FAILED, PENDING |
| reason_code | TEXT | |
| amount_minor | INTEGER | ≥ 0 |
| currency | TEXT | |
| service_date | TEXT | `YYYY-MM-DD` |
| event_at | TEXT | UTC timestamp |
| ingested_at | TEXT | |
| linked_refund_id | TEXT NULL | Non-null for reversals |

### shipments
Physical shipments tied to orders. Completion uses carrier scan data, not
`current_status`.

| Column | Type | Notes |
|---|---|---|
| shipment_id | TEXT PK | |
| order_id | TEXT FK → orders | |
| carrier_code | TEXT | |
| warehouse_id | TEXT FK → warehouses | |
| shipped_at | TEXT NULL | |
| promised_delivery_at | TEXT | |
| current_status | TEXT | May lag; use carrier_scans |

### support_cases
Case headers. `current_status` may lag event history; always derive active state
from `case_events`.

| Column | Type | Notes |
|---|---|---|
| case_id | TEXT PK | |
| account_id | TEXT FK → accounts | |
| order_id | TEXT FK → orders (nullable) | |
| priority | TEXT | URGENT, HIGH, MEDIUM, LOW |
| opened_at | TEXT | |
| current_status | TEXT | |
| current_owner_team | TEXT | |

### warehouse_task_events
Execution events for warehouse work. `productive_minutes` is whole minutes.

| Column | Type | Notes |
|---|---|---|
| task_event_id | TEXT PK | |
| task_id | TEXT FK → warehouse_tasks | |
| event_type | TEXT | `STARTED`, `COMPLETED`, `REWORK`, `ABANDONED` |
| event_at | TEXT | |
| units | INTEGER | |
| productive_minutes | INTEGER | |
| source_system | TEXT | |
| external_event_id | TEXT | |
| ingested_at | TEXT | |

### warehouse_tasks
Work assignments. `work_class = 'PRODUCTION'` filters production tasks.
`task_type` includes completion and rework categories.

| Column | Type | Notes |
|---|---|---|
| task_id | TEXT PK | |
| warehouse_id | TEXT FK → warehouses | |
| order_id | TEXT FK → orders (nullable) | |
| sku | TEXT FK → products (nullable) | |
| assigned_employee_id | TEXT FK → employees | |
| task_type | TEXT | |
| work_class | TEXT | PRODUCTION, TRAINING |
| priority | TEXT | URGENT, HIGH, MEDIUM, LOW |
| planned_units | INTEGER | ≥ 0 |
| created_at | TEXT | |
| due_at | TEXT | |
| current_status | TEXT | May lag event history |

### warehouses
Facility master.

| Column | Type | Notes |
|---|---|---|
| warehouse_id | TEXT PK | e.g., `WH-NORTH-01`, `WH-EAST-01` |
| warehouse_name | TEXT | |
| region | TEXT | NORTH, SOUTH, EAST, WEST, CENTRAL |
| timezone | TEXT | |
| daily_cutoff_local | TEXT | |

### source_import_batches
Batch ingestion metadata.

| Column | Type | Notes |
|---|---|---|
| import_batch_id | TEXT PK | |
| source_system | TEXT | |
| entity_type | TEXT | |
| started_at | TEXT | |
| completed_at | TEXT | |
| record_count | INTEGER | |
| status | TEXT | |

### Other tables

- `order_events`: Append-only order lifecycle events (`event_type`, `event_at`).
- `payment_events`: Payment auth, settlement, void, reversal (`event_type`,
  `amount_minor`, `linked_event_id`).
- `products`: SKU master (`sku`, `product_family`, `units_per_case`).
- `inventory_movements`: Stock movements with raw and canonical quantities.
- `inventory_snapshots`: Periodic on-hand/reserved snapshots.
