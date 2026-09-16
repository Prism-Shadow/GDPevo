## Full Atlas Commerce Operations Schema

All tables below are live in the authenticated SQL endpoint. The database uses SQLite3 semantics.

### Conventions

- **Timestamps**: ISO-8601 UTC with `Z` suffix (e.g. `2026-04-15T23:59:59Z`).
- **Calendar dates**: `YYYY-MM-DD` text.
- **Money**: `amount_minor` / `gross_amount_minor` columns hold the smallest unit of the named row currency. `fx_rates.usd_per_unit` is the daily USD value of one unit of that currency.
- **Integer booleans**: `1` = true, `0` = false.
- **Source vs canonical**: `raw_*` columns preserve original source values; `canonical_*` columns hold normalized operational values. Always use canonical fields for business logic.

---

### accounts

| Column | Type | Null | Notes |
|---|---|---|---|
| account_id | TEXT | NO | PK |
| account_name | TEXT | NO | |
| segment | TEXT | NO | CONSUMER, SMB, ENTERPRISE, STRATEGIC |
| tier | TEXT | NO | STANDARD, SILVER, GOLD, PLATINUM |
| region | TEXT | NO | |
| currency | TEXT | NO | |
| is_internal | INTEGER | NO | 1 = internal, 0 = not |
| is_test | INTEGER | NO | 1 = test, 0 = production |
| created_at | TEXT | NO | ISO-8601 UTC |

**Index**: `idx_accounts_segment_region ON (segment, region)`

---

### campaigns

| Column | Type | Null | Notes |
|---|---|---|---|
| campaign_id | TEXT | NO | PK |
| campaign_name | TEXT | NO | UNIQUE |
| starts_at | TEXT | NO | ISO-8601 UTC |
| ends_at | TEXT | NO | ISO-8601 UTC |
| channel | TEXT | NO | |

---

### carrier_scans

| Column | Type | Null | Notes |
|---|---|---|---|
| scan_row_id | TEXT | NO | PK |
| shipment_id | TEXT | NO | FK -> shipments.shipment_id |
| source_system | TEXT | NO | Upstream system identifier |
| external_event_id | TEXT | NO | Upstream event id (can recur on retries) |
| raw_status | TEXT | NO | Status exactly as the carrier supplied |
| raw_event_at | TEXT | NO | Event timestamp exactly as the carrier supplied (UTC) |
| canonical_status | TEXT | NO | Normalized operational status |
| canonical_event_at | TEXT | NO | Normalized event timestamp (UTC) |
| ingested_at | TEXT | NO | UTC when row reached the database |
| import_batch_id | TEXT | NO | FK -> source_import_batches.import_batch_id |
| corrected_at | TEXT | YES | UTC of approved correction, or NULL |
| correction_reason | TEXT | YES | Reason for correction, or NULL |

**Deduplication key**: `(source_system, external_event_id, ingested_at)` — the last-ingested row per key is the effective row.

**Effective-row index**: `idx_scans_shipment_effective ON (shipment_id, canonical_event_at, scan_row_id)`

---

### case_events

| Column | Type | Null | Notes |
|---|---|---|---|
| case_event_id | TEXT | NO | PK |
| case_id | TEXT | NO | FK -> support_cases.case_id |
| event_type | TEXT | NO | e.g. OPENED, REOPENED, RESPONDED, RESOLVED, CLOSED |
| event_at | TEXT | NO | ISO-8601 UTC |
| actor_type | TEXT | NO | e.g. AGENT, CUSTOMER, SYSTEM |
| source_system | TEXT | NO | Upstream system identifier |
| external_event_id | TEXT | NO | Upstream event id |
| ingested_at | TEXT | NO | UTC when row reached the database |

**Deduplication key**: `(source_system, external_event_id, ingested_at)`.

**Effective-event index**: `idx_case_events_effective ON (case_id, event_at, case_event_id)`

---

### correction_audit

| Column | Type | Null | Notes |
|---|---|---|---|
| audit_id | TEXT | NO | PK |
| correction_key | TEXT | NO | UNIQUE, caller-provided idempotency key |
| entity_type | TEXT | NO | e.g. carrier_scan |
| entity_id | TEXT | NO | Business entity id (e.g. shipment_id) |
| source_row_id | TEXT | NO | The corrected source row identifier |
| field_name | TEXT | NO | Corrected field |
| old_value | TEXT | YES | Value before correction |
| new_value | TEXT | YES | Value after correction |
| reason_code | TEXT | NO | e.g. SOURCE_RECONCILIATION |
| corrected_at | TEXT | NO | UTC timestamp |
| actor | TEXT | NO | Actor identifier |

**Index**: `idx_audit_entity ON (entity_type, entity_id, corrected_at)`

---

### employees

| Column | Type | Null | Notes |
|---|---|---|---|
| employee_id | TEXT | NO | PK |
| warehouse_id | TEXT | NO | FK -> warehouses.warehouse_id |
| team_id | TEXT | NO | |
| role | TEXT | NO | |
| active_from | TEXT | NO | ISO-8601 UTC |
| active_to | TEXT | YES | ISO-8601 UTC or NULL |

---

### fx_rates

| Column | Type | Null | Notes |
|---|---|---|---|
| rate_date | TEXT | NO | PK (part) — YYYY-MM-DD |
| currency | TEXT | NO | PK (part) |
| usd_per_unit | REAL | NO | USD value of 1 unit of the named currency |

**PK**: `(rate_date, currency)`

---

### inventory_movements

| Column | Type | Null | Notes |
|---|---|---|---|
| movement_row_id | TEXT | NO | PK |
| movement_id | TEXT | NO | |
| warehouse_id | TEXT | NO | FK -> warehouses.warehouse_id |
| sku | TEXT | NO | FK -> products.sku |
| movement_type | TEXT | NO | |
| raw_quantity | INTEGER | NO | Signed, as supplied by source |
| raw_uom | TEXT | NO | e.g. EA, CASE |
| raw_uom_multiplier | INTEGER | NO | Source-declared each units per raw unit |
| canonical_quantity_each | INTEGER | NO | Normalized signed each-unit quantity |
| canonical_uom_multiplier | INTEGER | NO | Normalized each units per raw unit |
| occurred_at | TEXT | NO | ISO-8601 UTC |
| source_system | TEXT | NO | |
| external_event_id | TEXT | NO | |
| ingested_at | TEXT | NO | |
| source_document_id | TEXT | NO | |
| corrected_at | TEXT | YES | |
| correction_reason | TEXT | YES | |

**Deduplication key**: `(source_system, external_event_id, ingested_at)`.

---

### inventory_snapshots

| Column | Type | Null | Notes |
|---|---|---|---|
| warehouse_id | TEXT | NO | PK (part) |
| sku | TEXT | NO | PK (part) |
| snapshot_at | TEXT | NO | PK (part), ISO-8601 UTC |
| on_hand_each | INTEGER | NO | |
| reserved_each | INTEGER | NO | |
| source_system | TEXT | NO | |

**PK**: `(warehouse_id, sku, snapshot_at)`

---

### order_events

| Column | Type | Null | Notes |
|---|---|---|---|
| event_id | TEXT | NO | PK |
| order_id | TEXT | NO | FK -> orders.order_id |
| event_type | TEXT | NO | |
| event_at | TEXT | NO | ISO-8601 UTC |
| source_system | TEXT | NO | |
| external_event_id | TEXT | NO | |
| ingested_at | TEXT | NO | |
| metadata_json | TEXT | NO | JSON object string, defaults to `{}` |

**Deduplication key**: `(source_system, external_event_id, ingested_at)`.

---

### order_lines

| Column | Type | Null | Notes |
|---|---|---|---|
| order_id | TEXT | NO | PK (part), FK -> orders.order_id |
| line_id | INTEGER | NO | PK (part) |
| sku | TEXT | NO | FK -> products.sku |
| quantity_each | INTEGER | NO | > 0 |

**PK**: `(order_id, line_id)`

---

### orders

| Column | Type | Null | Notes |
|---|---|---|---|
| order_id | TEXT | NO | PK |
| account_id | TEXT | NO | FK -> accounts.account_id |
| campaign_id | TEXT | YES | FK -> campaigns.campaign_id |
| warehouse_id | TEXT | NO | FK -> warehouses.warehouse_id |
| order_created_at | TEXT | NO | ISO-8601 UTC |
| promised_at | TEXT | NO | ISO-8601 UTC |
| currency | TEXT | NO | |
| current_status | TEXT | NO | Convenience snapshot; may lag events |
| gross_amount_minor | INTEGER | NO | >= 0, smallest unit of order currency |

**Indexes**: `idx_orders_account_created ON (account_id, order_created_at)`, `idx_orders_campaign_created ON (campaign_id, order_created_at)`, `idx_orders_warehouse_promised ON (warehouse_id, promised_at)`

---

### payment_events

| Column | Type | Null | Notes |
|---|---|---|---|
| payment_event_id | TEXT | NO | PK |
| order_id | TEXT | NO | FK -> orders.order_id |
| provider | TEXT | NO | |
| source_system | TEXT | NO | |
| external_event_id | TEXT | NO | |
| event_type | TEXT | NO | e.g. AUTHORIZATION, SETTLEMENT, VOID, REVERSAL |
| amount_minor | INTEGER | NO | Smallest unit of named currency |
| currency | TEXT | NO | |
| event_at | TEXT | NO | ISO-8601 UTC |
| ingested_at | TEXT | NO | |
| linked_event_id | TEXT | YES | PK reference or NULL |

**Deduplication key**: `(source_system, external_event_id, ingested_at)`.

---

### products

| Column | Type | Null | Notes |
|---|---|---|---|
| sku | TEXT | NO | PK |
| product_family | TEXT | NO | |
| unit_weight_grams | INTEGER | NO | > 0 |
| units_per_case | INTEGER | NO | > 0 |
| is_active | INTEGER | NO | 1 = active, 0 = inactive |

---

### refund_attempts

| Column | Type | Null | Notes |
|---|---|---|---|
| refund_row_id | TEXT | NO | PK |
| refund_id | TEXT | NO | |
| order_id | TEXT | NO | FK -> orders.order_id |
| provider | TEXT | NO | |
| source_system | TEXT | NO | |
| external_event_id | TEXT | NO | |
| status | TEXT | NO | e.g. SETTLED, DECLINED, REVERSED |
| reason_code | TEXT | NO | e.g. DAMAGED, NOT_AS_DESCRIBED |
| amount_minor | INTEGER | NO | >= 0, smallest unit of named currency |
| currency | TEXT | NO | |
| service_date | TEXT | NO | YYYY-MM-DD |
| event_at | TEXT | NO | ISO-8601 UTC |
| ingested_at | TEXT | NO | |
| linked_refund_id | TEXT | YES | PK of reversed refund, or NULL |

**Deduplication key**: `(source_system, external_event_id, ingested_at)`.

---

### shipments

| Column | Type | Null | Notes |
|---|---|---|---|
| shipment_id | TEXT | NO | PK |
| order_id | TEXT | NO | FK -> orders.order_id |
| carrier_code | TEXT | NO | |
| warehouse_id | TEXT | NO | FK -> warehouses.warehouse_id |
| shipped_at | TEXT | YES | ISO-8601 UTC or NULL |
| promised_delivery_at | TEXT | NO | ISO-8601 UTC |
| current_status | TEXT | NO | Convenience snapshot; may lag scans |

**Indexes**: `idx_shipments_order ON (order_id)`, `idx_shipments_warehouse_promised ON (warehouse_id, promised_delivery_at)`

---

### source_import_batches

| Column | Type | Null | Notes |
|---|---|---|---|
| import_batch_id | TEXT | NO | PK |
| source_system | TEXT | NO | |
| entity_type | TEXT | NO | |
| started_at | TEXT | NO | ISO-8601 UTC |
| completed_at | TEXT | NO | ISO-8601 UTC |
| record_count | INTEGER | NO | >= 0 |
| status | TEXT | NO | |

---

### support_cases

| Column | Type | Null | Notes |
|---|---|---|---|
| case_id | TEXT | NO | PK |
| account_id | TEXT | NO | FK -> accounts.account_id |
| order_id | TEXT | YES | FK -> orders.order_id |
| priority | TEXT | NO | URGENT, HIGH, MEDIUM, LOW |
| opened_at | TEXT | NO | ISO-8601 UTC |
| current_status | TEXT | NO | Convenience snapshot; may lag events |
| current_owner_team | TEXT | NO | |

**Index**: `idx_cases_account_opened ON (account_id, opened_at)`

---

### warehouse_task_events

| Column | Type | Null | Notes |
|---|---|---|---|
| task_event_id | TEXT | NO | PK |
| task_id | TEXT | NO | FK -> warehouse_tasks.task_id |
| event_type | TEXT | NO | e.g. STARTED, UNIT_DONE, COMPLETED, REWORK |
| event_at | TEXT | NO | ISO-8601 UTC |
| units | INTEGER | NO | >= 0 |
| productive_minutes | INTEGER | NO | >= 0, whole minutes |
| source_system | TEXT | NO | |
| external_event_id | TEXT | NO | |
| ingested_at | TEXT | NO | |

**Deduplication key**: `(source_system, external_event_id, ingested_at)`.

**Effective-event index**: `idx_task_events_effective ON (task_id, event_at, task_event_id)`

---

### warehouse_tasks

| Column | Type | Null | Notes |
|---|---|---|---|
| task_id | TEXT | NO | PK |
| warehouse_id | TEXT | NO | FK -> warehouses.warehouse_id |
| order_id | TEXT | YES | FK -> orders.order_id |
| sku | TEXT | YES | FK -> products.sku |
| assigned_employee_id | TEXT | NO | FK -> employees.employee_id |
| task_type | TEXT | NO | |
| work_class | TEXT | NO | PRODUCTION, TRAINING |
| priority | TEXT | NO | LOW, MEDIUM, HIGH, URGENT |
| planned_units | INTEGER | NO | >= 0 |
| created_at | TEXT | NO | ISO-8601 UTC |
| due_at | TEXT | NO | ISO-8601 UTC |
| current_status | TEXT | NO | Convenience snapshot; may lag events |

**Indexes**: `idx_tasks_employee ON (assigned_employee_id, created_at)`, `idx_tasks_warehouse_due ON (warehouse_id, due_at)`

---

### warehouses

| Column | Type | Null | Notes |
|---|---|---|---|
| warehouse_id | TEXT | NO | PK |
| warehouse_name | TEXT | NO | |
| region | TEXT | NO | e.g. NORTH, SOUTH, EAST, WEST, CENTRAL |
| timezone | TEXT | NO | |
| daily_cutoff_local | TEXT | NO | |
