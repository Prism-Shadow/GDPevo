# Atlas Commerce Operations — Schema Summary

This is a quick-reference view of every table and column. Always call
`GET /api/schema` and `GET /api/data-dictionary` for the authoritative
definitions; use this only as a supplement.

## accounts
Customer and company account master data.
- account_id TEXT PK
- account_name TEXT
- segment TEXT — CONSUMER, SMB, ENTERPRISE, STRATEGIC
- tier TEXT — STANDARD, SILVER, GOLD, PLATINUM
- region TEXT
- currency TEXT
- is_internal INTEGER — 0/1
- is_test INTEGER — 0/1
- created_at TEXT

## campaigns
Marketing campaign names, active windows, channels.
- campaign_id TEXT PK
- campaign_name TEXT UNIQUE
- starts_at TEXT
- ends_at TEXT
- channel TEXT

## carrier_scans
Imported carrier observations. **Dedup on (source_system, external_event_id, ingested_at).**
- scan_row_id TEXT PK
- shipment_id TEXT → shipments
- source_system TEXT
- external_event_id TEXT
- raw_status TEXT
- raw_event_at TEXT
- canonical_status TEXT
- canonical_event_at TEXT
- ingested_at TEXT
- import_batch_id TEXT → source_import_batches
- corrected_at TEXT (nullable)
- correction_reason TEXT (nullable)

## case_events
Append-only support case lifecycle events. **Dedup on (source_system, external_event_id, ingested_at).**
- case_event_id TEXT PK
- case_id TEXT → support_cases
- event_type TEXT
- event_at TEXT
- actor_type TEXT
- source_system TEXT
- external_event_id TEXT
- ingested_at TEXT

## correction_audit
Public audit records for controlled corrections.
- audit_id TEXT PK
- correction_key TEXT UNIQUE
- entity_type TEXT
- entity_id TEXT
- source_row_id TEXT
- field_name TEXT
- old_value TEXT (nullable)
- new_value TEXT (nullable)
- reason_code TEXT
- corrected_at TEXT
- actor TEXT

## employees
Warehouse employees, team, role, active period.
- employee_id TEXT PK
- warehouse_id TEXT → warehouses
- team_id TEXT
- role TEXT
- active_from TEXT
- active_to TEXT (nullable)

## fx_rates
Daily USD conversion rates. PK: (rate_date, currency).
- rate_date TEXT
- currency TEXT
- usd_per_unit REAL (>0)

## inventory_movements
Stock movements with raw and canonical quantities. **Dedup on (source_system, external_event_id, ingested_at).**
- movement_row_id TEXT PK
- movement_id TEXT
- warehouse_id TEXT → warehouses
- sku TEXT → products
- movement_type TEXT
- raw_quantity INTEGER
- raw_uom TEXT
- raw_uom_multiplier INTEGER (>0)
- canonical_quantity_each INTEGER
- canonical_uom_multiplier INTEGER (>0)
- occurred_at TEXT
- source_system TEXT
- external_event_id TEXT
- ingested_at TEXT
- source_document_id TEXT
- corrected_at TEXT (nullable)
- correction_reason TEXT (nullable)

## inventory_snapshots
PK: (warehouse_id, sku, snapshot_at).
- warehouse_id TEXT → warehouses
- sku TEXT → products
- snapshot_at TEXT
- on_hand_each INTEGER
- reserved_each INTEGER
- source_system TEXT

## order_events
Append-only order lifecycle events. **Dedup on (source_system, external_event_id, ingested_at).**
- event_id TEXT PK
- order_id TEXT → orders
- event_type TEXT
- event_at TEXT
- source_system TEXT
- external_event_id TEXT
- ingested_at TEXT
- metadata_json TEXT (default '{}')

## order_lines
SKU quantities per order. PK: (order_id, line_id).
- order_id TEXT → orders
- line_id INTEGER
- sku TEXT → products
- quantity_each INTEGER (>0)

## orders
Order headers with denormalized status.
- order_id TEXT PK
- account_id TEXT → accounts
- campaign_id TEXT → campaigns (nullable)
- warehouse_id TEXT → warehouses
- order_created_at TEXT
- promised_at TEXT
- currency TEXT
- current_status TEXT
- gross_amount_minor INTEGER (>=0)

## payment_events
Payment auth, settlement, void, reversal. **Dedup on (source_system, external_event_id, ingested_at).**
- payment_event_id TEXT PK
- order_id TEXT → orders
- provider TEXT
- source_system TEXT
- external_event_id TEXT
- event_type TEXT
- amount_minor INTEGER
- currency TEXT
- event_at TEXT
- ingested_at TEXT
- linked_event_id TEXT (nullable)

## products
Sellable SKU master data.
- sku TEXT PK
- product_family TEXT
- unit_weight_grams INTEGER (>0)
- units_per_case INTEGER (>0)
- is_active INTEGER — 0/1

## refund_attempts
Provider refund attempts, retries, reversals. **Dedup on (source_system, external_event_id, ingested_at).**
- refund_row_id TEXT PK
- refund_id TEXT
- order_id TEXT → orders
- provider TEXT
- source_system TEXT
- external_event_id TEXT
- status TEXT
- reason_code TEXT
- amount_minor INTEGER (>=0)
- currency TEXT
- service_date TEXT
- event_at TEXT
- ingested_at TEXT
- linked_refund_id TEXT (nullable)

## shipments
Physical shipment headers.
- shipment_id TEXT PK
- order_id TEXT → orders
- carrier_code TEXT
- warehouse_id TEXT → warehouses
- shipped_at TEXT (nullable)
- promised_delivery_at TEXT
- current_status TEXT

## source_import_batches
Ingestion batch metadata.
- import_batch_id TEXT PK
- source_system TEXT
- entity_type TEXT
- started_at TEXT
- completed_at TEXT
- record_count INTEGER (>=0)
- status TEXT

## support_cases
Support case headers.
- case_id TEXT PK
- account_id TEXT → accounts
- order_id TEXT → orders (nullable)
- priority TEXT — URGENT, HIGH, MEDIUM, LOW
- opened_at TEXT
- current_status TEXT
- current_owner_team TEXT

## warehouses
Fulfillment facilities.
- warehouse_id TEXT PK
- warehouse_name TEXT
- region TEXT
- timezone TEXT
- daily_cutoff_local TEXT

## warehouse_task_events
Execution events for warehouse work. **Dedup on (source_system, external_event_id, ingested_at).**
- task_event_id TEXT PK
- task_id TEXT → warehouse_tasks
- event_type TEXT
- event_at TEXT
- units INTEGER (>=0)
- productive_minutes INTEGER (>=0)
- source_system TEXT
- external_event_id TEXT
- ingested_at TEXT

## warehouse_tasks
Operational warehouse assignments.
- task_id TEXT PK
- warehouse_id TEXT → warehouses
- order_id TEXT → orders (nullable)
- sku TEXT → products (nullable)
- assigned_employee_id TEXT → employees
- task_type TEXT
- work_class TEXT — PRODUCTION, TRAINING
- priority TEXT
- planned_units INTEGER (>=0)
- created_at TEXT
- due_at TEXT
- current_status TEXT
