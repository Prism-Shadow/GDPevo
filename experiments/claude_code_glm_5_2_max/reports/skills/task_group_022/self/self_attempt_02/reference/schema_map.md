# Atlas Commerce Operations — Schema Map & Conventions

This is a stable orientation to the database, distilled from `GET /api/schema` and `GET /api/data-dictionary`. **Confirm column names against the live `/api/schema` at runtime** — do not hardcode. Treat the data-dictionary `conventions` block as authoritative for cross-cutting rules.

## Global conventions (from /api/data-dictionary)

- **Timestamps:** ISO-8601 UTC text ending in `Z`. Compare with string ordering (lexicographic == chronological for this format).
- **Dates:** `YYYY-MM-DD` text.
- **Money:** `*_minor` integer fields hold the **smallest unit of the row's currency** (e.g. cents for USD). The row currency lives in a sibling `currency` column. FX rates are expressed as **USD per one unit of currency**.
- **Source rows:** `raw_*` fields preserve source values exactly; `canonical_*` fields hold normalized operational values used by analytics. Never modify a `raw_*` or identity field; corrections target exactly one `canonical_*` field.

## Integer booleans

Flags like `is_internal`, `is_test`, `is_active` are `INTEGER`: **1 = true, 0 = false**. "Production" populations typically require `is_test = 0 AND is_internal = 0`.

## Table inventory (by domain)

**Accounts / commercial:**
- `accounts` — account_id PK; segment (CONSUMER/SMB/ENTERPRISE/STRATEGIC); tier (STANDARD/SILVER/GOLD/PLATINUM); region; currency; is_internal; is_test; created_at.
- `campaigns` — campaign_id PK; campaign_name; starts_at; ends_at; channel.
- `orders` — order_id PK; account_id; campaign_id (nullable); warehouse_id; order_created_at; **promised_at**; currency; current_status; **gross_amount_minor**.
- `order_lines` — (order_id, line_id) PK; sku; quantity_each.
- `order_events` — event_id PK; order_id; event_type; event_at; metadata_json.

**Fulfillment / shipping:**
- `warehouses` — warehouse_id PK; region (join here for warehouse region).
- `shipments` — shipment_id PK; order_id; carrier_code; warehouse_id; shipped_at (nullable); **promised_delivery_at**; current_status.
- `carrier_scans` — scan_row_id PK; shipment_id; source_system; external_event_id; **raw_status / raw_event_at**; **canonical_status / canonical_event_at**; ingested_at; import_batch_id; corrected_at; correction_reason. (Raw vs canonical contradiction lives here.)
- `source_import_batches` — import_batch_id PK; source_system; entity_type; started_at; completed_at; record_count; status.

**Warehouse operations / productivity:**
- `employees` — employee_id PK; warehouse_id; team_id; role; active_from; active_to (nullable).
- `warehouse_tasks` — warehouse task records (confirm columns at runtime: task_id, warehouse_id, employee_id/team_id, priority, due_at, status, completed units, productive minutes, rework flag, created_at).
- `warehouse_task_events` — lifecycle events for warehouse tasks.
- `inventory_movements` — movement_row_id PK; warehouse_id; sku; movement_type; raw_quantity/raw_uom/raw_uom_multiplier; **canonical_quantity_each**; occurred_at; source columns; corrected_at; correction_reason. (Second correction-capable table.)
- `inventory_snapshots` — (warehouse_id, sku, snapshot_at) PK; on_hand_each; reserved_each.

**Payments / refunds:**
- `payment_events` — payment_event_id PK; order_id; provider; event_type; amount_minor; currency; event_at; **linked_event_id** (reversal linkage).
- `refund_attempts` — refund_row_id PK; refund_id; order_id; provider; status; reason_code; amount_minor; currency; **service_date**; event_at; **linked_refund_id** (reversal linkage). Net/effective refunds subtract reversals via these links.

**Support:**
- `support_cases` — case_id PK; account_id; priority (URGENT/HIGH/MEDIUM/LOW); status (open/reopened/resolved states); opened_at; resolved fields. (Confirm exact columns at runtime.)
- `case_events` — case_event_id PK; case_id; event_type; event_at; actor_type (e.g. AGENT). Use to derive first-agent-response and active resolution times.

**Reference / FX:**
- `fx_rates` — (rate_date, currency) PK; usd_per_unit REAL (>0). Join on the refund/payment **service_date/event date** + row currency to convert minor money to USD.
- `products` — sku PK; product_family; unit_weight_grams; units_per_case; is_active.

**Audit:**
- `correction_audit` — audit_id PK; correction_key (UNIQUE idempotency); entity_type; entity_id; source_row_id; field_name; old_value; new_value; reason_code; corrected_at; actor.

## Recurring join patterns

- **Order → region:** `orders JOIN warehouses USING (warehouse_id)` → `warehouses.region`. Use for regional rollups.
- **Order → campaign window:** `orders JOIN campaigns USING (campaign_id)`; eligibility by `order_created_at` within `campaigns.starts_at`/`ends_at`.
- **Money → USD:** `<event> JOIN fx_rates ON fx_rates.rate_date = <event>.service_date AND fx_rates.currency = <event>.currency`, then `amount_minor * usd_per_unit / 100`.
- **Effective/settled value:** aggregate `<event>` minus its linked reversals: identify reversal rows via `linked_*_id`, net them against parents.
- **Production filter:** `accounts.is_test = 0 AND accounts.is_internal = 0` (plus any segment/tier/region the payload names).
