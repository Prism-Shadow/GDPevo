# Atlas Commerce Operations — Data Dictionary

Conventions and column-level semantics for all tables (`schema_version: atlas-commerce-1.0`).

## Global Conventions

- **Timestamps**: All stored timestamps use ISO-8601 UTC text ending in `Z`.
- **Dates**: Calendar dates use `YYYY-MM-DD` text.
- **Money**: Monetary minor fields use the smallest unit of the row currency; FX is USD per currency unit.
- **Source rows**: Raw fields preserve source values; canonical fields hold normalized operational values.
- **Integer booleans**: 1 means true, 0 means false (`is_internal`, `is_test`, `is_active`).
- **Unit quantities**: Fields ending in `_each` are individual units.
- **Nullable**: Only `NULL` where the schema explicitly permits; all columns not marked nullable are required.

## Table: accounts

Customer and company account master data, including production-exclusion flags.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| account_id | TEXT | NO | Stable textual business identifier |
| account_name | TEXT | NO | Account name |
| segment | TEXT | NO | CONSUMER, SMB, ENTERPRISE, STRATEGIC |
| tier | TEXT | NO | STANDARD, SILVER, GOLD, PLATINUM |
| region | TEXT | NO | Region |
| currency | TEXT | NO | Currency |
| is_internal | INTEGER | NO | 1=true, 0=false |
| is_test | INTEGER | NO | 1=true, 0=false |
| created_at | TEXT | NO | ISO-8601 UTC timestamp |

## Table: campaigns

Marketing campaign names, active windows, and acquisition channels.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| campaign_id | TEXT | NO | Stable textual business identifier |
| campaign_name | TEXT | NO | Campaign name (unique) |
| starts_at | TEXT | NO | ISO-8601 UTC timestamp |
| ends_at | TEXT | NO | ISO-8601 UTC timestamp |
| channel | TEXT | NO | Channel |

## Table: carrier_scans

Imported carrier observations with raw and normalized event values.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| scan_row_id | TEXT | NO | Stable textual row identifier |
| shipment_id | TEXT | NO | FK to shipments |
| source_system | TEXT | NO | Upstream system identifier |
| external_event_id | TEXT | NO | Upstream event identifier (can recur on import retries) |
| raw_status | TEXT | NO | Status exactly as supplied by carrier |
| raw_event_at | TEXT | NO | Event timestamp exactly as supplied by carrier (UTC) |
| canonical_status | TEXT | NO | Normalized carrier status for operational analytics |
| canonical_event_at | TEXT | NO | Normalized carrier event timestamp (UTC) |
| ingested_at | TEXT | NO | UTC timestamp when this copy reached the workplace |
| import_batch_id | TEXT | NO | FK to source_import_batches |
| corrected_at | TEXT | YES | UTC timestamp of approved canonical correction, or null |
| correction_reason | TEXT | YES | Short reason for approved canonical correction, or null |

## Table: case_events

Imported append-only support case lifecycle events.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| case_event_id | TEXT | NO | Stable textual row identifier |
| case_id | TEXT | NO | FK to support_cases |
| event_type | TEXT | NO | OPENED, ASSIGNED, AGENT_RESPONDED, CUSTOMER_REPLIED, WAITING_CUSTOMER, ESCALATED, REOPENED, RESOLVED |
| event_at | TEXT | NO | ISO-8601 UTC timestamp |
| actor_type | TEXT | NO | CUSTOMER or AGENT |
| source_system | TEXT | NO | Upstream system identifier |
| external_event_id | TEXT | NO | Upstream event identifier |
| ingested_at | TEXT | NO | UTC timestamp when this copy reached the workplace |

## Table: correction_audit

Public audit records appended for controlled canonical corrections.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| audit_id | TEXT | NO | Stable textual audit identifier |
| correction_key | TEXT | NO | Caller-provided unique idempotency key |
| entity_type | TEXT | NO | Entity type |
| entity_id | TEXT | NO | Stable business entity identifier |
| source_row_id | TEXT | NO | Stable corrected source-row identifier |
| field_name | TEXT | NO | Field name |
| old_value | TEXT | YES | Text representation of value before correction |
| new_value | TEXT | YES | Text representation of value after correction |
| reason_code | TEXT | NO | SOURCE_RECONCILIATION |
| corrected_at | TEXT | NO | UTC timestamp of approved canonical correction |
| actor | TEXT | NO | Actor |

## Table: employees

Warehouse employees, team assignments, roles, and active periods.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| employee_id | TEXT | NO | Stable textual business identifier |
| warehouse_id | TEXT | NO | FK to warehouses |
| team_id | TEXT | NO | Stable textual team identifier |
| role | TEXT | NO | Role |
| active_from | TEXT | NO | ISO-8601 UTC timestamp |
| active_to | TEXT | YES | ISO-8601 UTC timestamp or null |

## Table: fx_rates

Daily currency conversion rates expressed as USD per currency unit.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| rate_date | TEXT | NO | ISO calendar date YYYY-MM-DD |
| currency | TEXT | NO | Currency |
| usd_per_unit | REAL | NO | USD value of one unit of the named currency |

## Table: inventory_movements

Imported stock movements with source quantities and normalized each-unit values.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| movement_row_id | TEXT | NO | Stable textual row identifier |
| movement_id | TEXT | NO | Stable movement identifier |
| warehouse_id | TEXT | NO | FK to warehouses |
| sku | TEXT | NO | FK to products |
| movement_type | TEXT | NO | Movement type |
| raw_quantity | INTEGER | NO | Signed quantity exactly as supplied by source |
| raw_uom | TEXT | NO | Source unit of measure (EA, CASE) |
| raw_uom_multiplier | INTEGER | NO | Source-declared each units per raw unit (>0) |
| canonical_quantity_each | INTEGER | NO | Normalized signed quantity in each units |
| canonical_uom_multiplier | INTEGER | NO | Normalized each units per raw unit (>0) |
| occurred_at | TEXT | NO | ISO-8601 UTC timestamp |
| source_system | TEXT | NO | Upstream system identifier |
| external_event_id | TEXT | NO | Upstream event identifier |
| ingested_at | TEXT | NO | UTC timestamp when this copy reached the workplace |
| source_document_id | TEXT | NO | Upstream document identifier |
| corrected_at | TEXT | YES | UTC timestamp of correction or null |
| correction_reason | TEXT | YES | Correction reason or null |

## Table: inventory_snapshots

Periodic point-in-time stock and reservation observations.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| warehouse_id | TEXT | NO | FK to warehouses |
| sku | TEXT | NO | FK to products |
| snapshot_at | TEXT | NO | ISO-8601 UTC timestamp |
| on_hand_each | INTEGER | NO | On-hand quantity in each units |
| reserved_each | INTEGER | NO | Reserved quantity in each units |
| source_system | TEXT | NO | Upstream system identifier |

## Table: order_events

Imported append-only order lifecycle events.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| event_id | TEXT | NO | Stable textual row identifier |
| order_id | TEXT | NO | FK to orders |
| event_type | TEXT | NO | CREATED, ALLOCATED, PACKED, SHIPPED, DELIVERED, PAYMENT_CONFIRMED, CANCELLED |
| event_at | TEXT | NO | ISO-8601 UTC timestamp |
| source_system | TEXT | NO | Upstream system identifier |
| external_event_id | TEXT | NO | Upstream event identifier |
| ingested_at | TEXT | NO | UTC timestamp when this copy reached the workplace |
| metadata_json | TEXT | NO | JSON metadata, default '{}' |

## Table: order_lines

Line items within orders.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| order_id | TEXT | NO | FK to orders |
| line_id | INTEGER | NO | Line number |
| sku | TEXT | NO | FK to products |
| quantity_each | INTEGER | NO | Quantity in each units (>0) |

## Table: orders

Order headers with fulfillment, account, and monetary attributes.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| order_id | TEXT | NO | Stable textual business identifier |
| account_id | TEXT | NO | FK to accounts |
| campaign_id | TEXT | YES | FK to campaigns, null if not campaign-attributed |
| warehouse_id | TEXT | NO | FK to warehouses |
| order_created_at | TEXT | NO | ISO-8601 UTC timestamp |
| promised_at | TEXT | NO | ISO-8601 UTC timestamp |
| currency | TEXT | NO | Order currency |
| current_status | TEXT | NO | CREATED, ALLOCATED, PACKED, SHIPPED, DELIVERED, CANCELLED |
| gross_amount_minor | INTEGER | NO | Gross order amount in smallest currency unit (>=0) |

## Table: payment_events

Provider payment authorizations and captures.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| payment_event_id | TEXT | NO | Stable textual row identifier |
| order_id | TEXT | NO | FK to orders |
| provider | TEXT | NO | STRIPE, BRAINTREE, ADYEN |
| source_system | TEXT | NO | Upstream system identifier |
| external_event_id | TEXT | NO | Upstream event identifier |
| event_type | TEXT | NO | AUTHORIZED, CAPTURED |
| amount_minor | INTEGER | NO | Monetary value in smallest currency unit |
| currency | TEXT | NO | Currency |
| event_at | TEXT | NO | ISO-8601 UTC timestamp |
| ingested_at | TEXT | NO | UTC timestamp when this copy reached the workplace |
| linked_event_id | TEXT | YES | Link to related payment event |

## Table: products

Sellable SKU master data and physical unit packaging.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| sku | TEXT | NO | Stable textual business identifier |
| product_family | TEXT | NO | Product family |
| unit_weight_grams | INTEGER | NO | Unit weight in grams (>0) |
| units_per_case | INTEGER | NO | Units per case (>0) |
| is_active | INTEGER | NO | 1=true, 0=false |

## Table: refund_attempts

Provider refund attempts, retries, outcomes, and linked reversals.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| refund_row_id | TEXT | NO | Stable textual row identifier |
| refund_id | TEXT | NO | Stable logical refund identifier |
| order_id | TEXT | NO | FK to orders |
| provider | TEXT | NO | STRIPE, BRAINTREE, ADYEN |
| source_system | TEXT | NO | Upstream system identifier |
| external_event_id | TEXT | NO | Upstream event identifier |
| status | TEXT | NO | SETTLED, FAILED, VOIDED, REVERSED |
| reason_code | TEXT | NO | DAMAGED, NOT_AS_DESCRIBED, LATE_DELIVERY, CUSTOMER_RETURN, DUPLICATE_CHARGE |
| amount_minor | INTEGER | NO | Monetary value in smallest currency unit (>=0) |
| currency | TEXT | NO | Currency |
| service_date | TEXT | NO | ISO calendar date YYYY-MM-DD |
| event_at | TEXT | NO | ISO-8601 UTC timestamp |
| ingested_at | TEXT | NO | UTC timestamp when this copy reached the workplace |
| linked_refund_id | TEXT | YES | FK back to refund_id for reversals |

## Table: shipments

Physical shipment headers associated with orders.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| shipment_id | TEXT | NO | Stable textual business identifier |
| order_id | TEXT | NO | FK to orders |
| carrier_code | TEXT | NO | Carrier code |
| warehouse_id | TEXT | NO | FK to warehouses |
| shipped_at | TEXT | YES | ISO-8601 UTC timestamp or null |
| promised_delivery_at | TEXT | NO | ISO-8601 UTC timestamp |
| current_status | TEXT | NO | LABEL_CREATED, IN_TRANSIT, DELIVERED |

## Table: source_import_batches

Operational source-ingestion batches and their completion metadata.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| import_batch_id | TEXT | NO | Stable textual batch identifier |
| source_system | TEXT | NO | Upstream system identifier |
| entity_type | TEXT | NO | Entity type |
| started_at | TEXT | NO | ISO-8601 UTC timestamp |
| completed_at | TEXT | NO | ISO-8601 UTC timestamp |
| record_count | INTEGER | NO | Record count (>=0) |
| status | TEXT | NO | Status |

## Table: support_cases

Support case headers and denormalized current ownership/state.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| case_id | TEXT | NO | Stable textual business identifier |
| account_id | TEXT | NO | FK to accounts |
| order_id | TEXT | YES | FK to orders or null |
| priority | TEXT | NO | URGENT, HIGH, MEDIUM, LOW |
| opened_at | TEXT | NO | ISO-8601 UTC timestamp |
| current_status | TEXT | NO | OPEN, REOPENED, RESOLVED |
| current_owner_team | TEXT | NO | Current owner team |

## Table: warehouse_task_events

Imported append-only execution events for warehouse work.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| task_event_id | TEXT | NO | Stable textual row identifier |
| task_id | TEXT | NO | FK to warehouse_tasks |
| event_type | TEXT | NO | CREATED, STARTED, IN_PROGRESS, COMPLETED, REWORK |
| event_at | TEXT | NO | ISO-8601 UTC timestamp |
| units | INTEGER | NO | Integer unit quantity (>=0) |
| productive_minutes | INTEGER | NO | Productive work duration in whole minutes (>=0) |
| source_system | TEXT | NO | Upstream system identifier |
| external_event_id | TEXT | NO | Upstream event identifier |
| ingested_at | TEXT | NO | UTC timestamp when this copy reached the workplace |

## Table: warehouse_tasks

Operational warehouse work assignments and planning attributes.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| task_id | TEXT | NO | Stable textual business identifier |
| warehouse_id | TEXT | NO | FK to warehouses |
| order_id | TEXT | YES | FK to orders or null |
| sku | TEXT | YES | FK to products or null |
| assigned_employee_id | TEXT | NO | FK to employees |
| task_type | TEXT | NO | PICK, PACK, RECEIVE, REPLENISH |
| work_class | TEXT | NO | PRODUCTION, TRAINING |
| priority | TEXT | NO | NORMAL, HIGH, URGENT |
| planned_units | INTEGER | NO | Integer unit quantity (>=0) |
| created_at | TEXT | NO | ISO-8601 UTC timestamp |
| due_at | TEXT | NO | ISO-8601 UTC timestamp |
| current_status | TEXT | NO | CREATED, IN_PROGRESS, COMPLETED, REWORK |

## Table: warehouses

Fulfillment facilities with regional business-clock attributes.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| warehouse_id | TEXT | NO | Stable textual business identifier |
| warehouse_name | TEXT | NO | Warehouse name |
| region | TEXT | NO | NORTH, SOUTH, EAST, WEST, CENTRAL |
| timezone | TEXT | NO | Timezone |
| daily_cutoff_local | TEXT | NO | Daily cutoff local |
