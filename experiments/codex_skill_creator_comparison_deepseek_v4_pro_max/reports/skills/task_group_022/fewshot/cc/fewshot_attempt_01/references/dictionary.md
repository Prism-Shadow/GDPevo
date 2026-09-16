# Atlas Commerce Operations Data Dictionary

Schema version: atlas-commerce-1.0

## Conventions

- **timestamps**: All stored timestamps use ISO-8601 UTC text ending in Z.
- **dates**: Calendar dates use YYYY-MM-DD text.
- **money**: Monetary minor fields use the smallest unit of the row currency; FX is USD per currency unit.
- **source_rows**: Raw fields preserve source values; canonical fields hold normalized operational values.

## accounts

Customer and company account master data, including production-exclusion flags.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| account_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| account_name | TEXT | NO | Account name. |
| segment | TEXT | NO | Segment. |
| tier | TEXT | NO | Tier. |
| region | TEXT | NO | Region. |
| currency | TEXT | NO | Currency. |
| is_internal | INTEGER | NO | Integer boolean: 1 means true and 0 means false. |
| is_test | INTEGER | NO | Integer boolean: 1 means true and 0 means false. |
| created_at | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |

## campaigns

Marketing campaign names, active windows, and acquisition channels.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| campaign_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| campaign_name | TEXT | NO | Campaign name. |
| starts_at | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| ends_at | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| channel | TEXT | NO | Channel. |

## carrier_scans

Imported carrier observations with raw and normalized event values.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| scan_row_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| shipment_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| source_system | TEXT | NO | Stable identifier for the upstream system that supplied the row. |
| external_event_id | TEXT | NO | Upstream event identifier that can recur on import retries. |
| raw_status | TEXT | NO | Status text exactly as supplied by the carrier. |
| raw_event_at | TEXT | NO | Event timestamp exactly as supplied by the carrier, encoded in UTC. |
| canonical_status | TEXT | NO | Normalized carrier status used by operational analytics. |
| canonical_event_at | TEXT | NO | Normalized carrier event timestamp encoded in UTC. |
| ingested_at | TEXT | NO | UTC timestamp when this copy reached the workplace database. |
| import_batch_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| corrected_at | TEXT | YES | UTC timestamp of an approved canonical correction, or null. |
| correction_reason | TEXT | YES | Short reason recorded for an approved canonical correction, or null. |

## case_events

Imported append-only support case lifecycle events.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| case_event_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| case_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| event_type | TEXT | NO | Event type. |
| event_at | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| actor_type | TEXT | NO | Actor type. |
| source_system | TEXT | NO | Stable identifier for the upstream system that supplied the row. |
| external_event_id | TEXT | NO | Upstream event identifier that can recur on import retries. |
| ingested_at | TEXT | NO | UTC timestamp when this copy reached the workplace database. |

## correction_audit

Public audit records appended for controlled canonical corrections.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| audit_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| correction_key | TEXT | NO | Caller-provided unique idempotency key for one correction audit record. |
| entity_type | TEXT | NO | Entity type. |
| entity_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| source_row_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| field_name | TEXT | NO | Field name. |
| old_value | TEXT | YES | Text representation of the value before correction. |
| new_value | TEXT | YES | Text representation of the value after correction. |
| reason_code | TEXT | NO | Reason code. |
| corrected_at | TEXT | NO | UTC timestamp of an approved canonical correction, or null. |
| actor | TEXT | NO | Actor. |

## employees

Warehouse employees, team assignments, roles, and active periods.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| employee_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| warehouse_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| team_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| role | TEXT | NO | Role. |
| active_from | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| active_to | TEXT | YES | ISO-8601 UTC timestamp; nullable only where the schema permits. |

## fx_rates

Daily currency conversion rates expressed as USD per currency unit.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| rate_date | TEXT | NO | ISO calendar date in YYYY-MM-DD form. |
| currency | TEXT | NO | Currency. |
| usd_per_unit | REAL | NO | USD value of one unit of the named currency for the rate date. |

## inventory_movements

Imported stock movements with source quantities and normalized each-unit values.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| movement_row_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| movement_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| warehouse_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| sku | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| movement_type | TEXT | NO | Movement type. |
| raw_quantity | INTEGER | NO | Signed quantity exactly as supplied by the source. |
| raw_uom | TEXT | NO | Source unit of measure, such as EA or CASE. |
| raw_uom_multiplier | INTEGER | NO | Source-declared number of each units per raw unit. |
| canonical_quantity_each | INTEGER | NO | Normalized signed quantity measured in individual each units. |
| canonical_uom_multiplier | INTEGER | NO | Normalized number of each units per raw unit. |
| occurred_at | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| source_system | TEXT | NO | Stable identifier for the upstream system that supplied the row. |
| external_event_id | TEXT | NO | Upstream event identifier that can recur on import retries. |
| ingested_at | TEXT | NO | UTC timestamp when this copy reached the workplace database. |
| source_document_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| corrected_at | TEXT | YES | UTC timestamp of an approved canonical correction, or null. |
| correction_reason | TEXT | YES | Short reason recorded for an approved canonical correction, or null. |

## inventory_snapshots

Periodic point-in-time stock and reservation observations.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| warehouse_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| sku | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| snapshot_at | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| on_hand_each | INTEGER | NO | Integer unit quantity; fields ending in each are individual units. |
| reserved_each | INTEGER | NO | Integer unit quantity; fields ending in each are individual units. |
| source_system | TEXT | NO | Stable identifier for the upstream system that supplied the row. |

## order_events

Imported append-only order lifecycle events.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| event_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| order_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| event_type | TEXT | NO | Event type. |
| event_at | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| source_system | TEXT | NO | Stable identifier for the upstream system that supplied the row. |
| external_event_id | TEXT | NO | Upstream event identifier that can recur on import retries. |
| ingested_at | TEXT | NO | UTC timestamp when this copy reached the workplace database. |
| metadata_json | TEXT | NO | Source event attributes encoded as a JSON object string. |

## order_lines

SKU quantities requested on each order.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| order_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| line_id | INTEGER | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| sku | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| quantity_each | INTEGER | NO | Integer unit quantity; fields ending in each are individual units. |

## orders

Order headers and denormalized current status snapshots.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| order_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| account_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| campaign_id | TEXT | YES | Stable textual business or row identifier; relationships are shown in the schema. |
| warehouse_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| order_created_at | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| promised_at | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| currency | TEXT | NO | Currency. |
| current_status | TEXT | NO | Convenience snapshot that may lag append-only event history. |
| gross_amount_minor | INTEGER | NO | Order gross value in the smallest unit of the order currency. |

## payment_events

Imported payment authorization, settlement, void, and reversal events.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| payment_event_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| order_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| provider | TEXT | NO | Provider. |
| source_system | TEXT | NO | Stable identifier for the upstream system that supplied the row. |
| external_event_id | TEXT | NO | Upstream event identifier that can recur on import retries. |
| event_type | TEXT | NO | Event type. |
| amount_minor | INTEGER | NO | Monetary value in the smallest unit of the named currency. |
| currency | TEXT | NO | Currency. |
| event_at | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| ingested_at | TEXT | NO | UTC timestamp when this copy reached the workplace database. |
| linked_event_id | TEXT | YES | Stable textual business or row identifier; relationships are shown in the schema. |

## products

Sellable SKU master data and physical unit packaging.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| sku | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| product_family | TEXT | NO | Product family. |
| unit_weight_grams | INTEGER | NO | Unit weight grams. |
| units_per_case | INTEGER | NO | Units per case. |
| is_active | INTEGER | NO | Integer boolean: 1 means true and 0 means false. |

## refund_attempts

Provider refund attempts, retries, outcomes, and linked reversals.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| refund_row_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| refund_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| order_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| provider | TEXT | NO | Provider. |
| source_system | TEXT | NO | Stable identifier for the upstream system that supplied the row. |
| external_event_id | TEXT | NO | Upstream event identifier that can recur on import retries. |
| status | TEXT | NO | Status. |
| reason_code | TEXT | NO | Reason code. |
| amount_minor | INTEGER | NO | Monetary value in the smallest unit of the named currency. |
| currency | TEXT | NO | Currency. |
| service_date | TEXT | NO | ISO calendar date in YYYY-MM-DD form. |
| event_at | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| ingested_at | TEXT | NO | UTC timestamp when this copy reached the workplace database. |
| linked_refund_id | TEXT | YES | Stable textual business or row identifier; relationships are shown in the schema. |

## shipments

Physical shipment headers associated with orders.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| shipment_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| order_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| carrier_code | TEXT | NO | Carrier code. |
| warehouse_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| shipped_at | TEXT | YES | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| promised_delivery_at | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| current_status | TEXT | NO | Convenience snapshot that may lag append-only event history. |

## source_import_batches

Operational source-ingestion batches and their completion metadata.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| import_batch_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| source_system | TEXT | NO | Stable identifier for the upstream system that supplied the row. |
| entity_type | TEXT | NO | Entity type. |
| started_at | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| completed_at | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| record_count | INTEGER | NO | Record count. |
| status | TEXT | NO | Status. |

## support_cases

Support case headers and denormalized current ownership/state.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| case_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| account_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| order_id | TEXT | YES | Stable textual business or row identifier; relationships are shown in the schema. |
| priority | TEXT | NO | Priority. |
| opened_at | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| current_status | TEXT | NO | Convenience snapshot that may lag append-only event history. |
| current_owner_team | TEXT | NO | Current owner team. |

## warehouse_task_events

Imported append-only execution events for warehouse work.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| task_event_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| task_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| event_type | TEXT | NO | Event type. |
| event_at | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| units | INTEGER | NO | Integer unit quantity; fields ending in each are individual units. |
| productive_minutes | INTEGER | NO | Productive work duration in whole minutes. |
| source_system | TEXT | NO | Stable identifier for the upstream system that supplied the row. |
| external_event_id | TEXT | NO | Upstream event identifier that can recur on import retries. |
| ingested_at | TEXT | NO | UTC timestamp when this copy reached the workplace database. |

## warehouse_tasks

Operational warehouse work assignments and planning attributes.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| task_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| warehouse_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| order_id | TEXT | YES | Stable textual business or row identifier; relationships are shown in the schema. |
| sku | TEXT | YES | Stable textual business or row identifier; relationships are shown in the schema. |
| assigned_employee_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| task_type | TEXT | NO | Task type. |
| work_class | TEXT | NO | Work class. |
| priority | TEXT | NO | Priority. |
| planned_units | INTEGER | NO | Integer unit quantity; fields ending in each are individual units. |
| created_at | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| due_at | TEXT | NO | ISO-8601 UTC timestamp; nullable only where the schema permits. |
| current_status | TEXT | NO | Convenience snapshot that may lag append-only event history. |

## warehouses

Fulfillment facilities with regional business-clock attributes.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| warehouse_id | TEXT | NO | Stable textual business or row identifier; relationships are shown in the schema. |
| warehouse_name | TEXT | NO | Warehouse name. |
| region | TEXT | NO | Region. |
| timezone | TEXT | NO | Timezone. |
| daily_cutoff_local | TEXT | NO | Daily cutoff local. |
