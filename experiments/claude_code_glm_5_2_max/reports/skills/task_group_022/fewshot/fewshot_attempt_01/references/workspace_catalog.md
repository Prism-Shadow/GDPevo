# Workspace catalog and storage conventions

The Atlas Commerce Operations workspace is a relational store. **Re-verify everything below live via `GET /api/schema` and `GET /api/data-dictionary` every task** — tables, columns, and the rules in `environment_access.md` are the source of truth, not this catalog. This file captures the stable shape so you know where to look.

## Storage conventions (from the data dictionary)
- **Timestamps**: ISO-8601 UTC text ending in `Z` (e.g. `2026-04-15T23:59:59Z`). Compare with text lexicographic operators safely because of the fixed format.
- **Dates**: `YYYY-MM-DD` text.
- **Money**: monetary minor fields use the smallest unit of the row currency. FX (`fx_rates`) is expressed as **USD per currency unit**.
- **Raw vs canonical**: raw fields preserve the source value; canonical fields hold the normalized operational value. Corrections target **canonical** fields only (write tasks); raw values and source-identity fields are immutable.

## Table catalog (verified schema names)
| Table | Purpose |
|---|---|
| `accounts` | Account master data: segment/tier, region, currency, `is_internal`, `is_test` production-exclusion flags. |
| `campaigns` | Campaign name, active window (`starts_at`/`ends_at`), acquisition channel. |
| `orders` | Order headers + denormalized current-status snapshot. |
| `order_lines` | SKU quantities requested per order. |
| `order_events` | Append-only order lifecycle events. |
| `shipments` | Physical shipment headers tied to orders; carries promised/delivered times. |
| `carrier_scans` | Imported carrier observations with `raw_*` and `canonical_*` event values; `import_batch_id`. |
| `warehouses` | Facilities with regional business-clock attributes. |
| `employees` | Warehouse employees, team assignments, roles, active periods. |
| `warehouse_tasks` | Operational work assignments and planning attributes (priority, due, state). |
| `warehouse_task_events` | Append-only execution events for warehouse work. |
| `inventory_movements` | Stock movements with source and normalized each-unit quantities (guarded-UPDATE candidate). |
| `inventory_snapshots` | Periodic point-in-time stock/reservation observations. |
| `products` | Sellable SKU master data and physical unit packaging. |
| `payment_events` | Payment authorization/settlement/void/reversal events. |
| `refund_attempts` | Provider refund attempts, retries, outcomes, and linked reversals. |
| `fx_rates` | Daily USD-per-currency-unit rates. |
| `support_cases` | Support case headers + denormalized ownership/state. |
| `case_events` | Append-only support case lifecycle events. |
| `correction_audit` | Public audit rows appended for controlled canonical corrections. |
| `source_import_batches` | Source-ingestion batches and completion metadata. |

## How domains map to tables (orientation only — confirm columns live)
- **Fulfillment scorecard**: `campaigns` (window) → `orders` (cohort, region via `warehouses`) → `shipments` (physical, promised/delivered) → completeness/on-time/severe logic; rates over the eligible order population.
- **Refund reconciliation**: `accounts` (tier/segment/production flags) → `refund_attempts` (effective settled logical refunds, linked reversals, reason codes) → `orders`/`order_lines` (gross order value) → `fx_rates` (USD basis) → leakage candidates & risk tier.
- **Carrier quality (write)**: `source_import_batches`/`carrier_scans.import_batch_id` → raw-vs-canonical contradiction → guarded `UPDATE carrier_scans` + `INSERT correction_audit` → backlog recompute over the batch cohort.
- **Warehouse productivity**: `warehouse_tasks` (created window, priority, due, state) + `warehouse_task_events` (completed units, productive minutes) + `employees`/teams → UPH, completion/rework rates, delayed high-priority list, employee/team rankings, facility status.
- **Support health**: `support_cases` (opened window, priority, state, account/segment/region) + `case_events` (active-time clock, first response, resolution) → eligibility, state summary, response/resolution breaches, severe active cases, worst accounts, resolved-case median, risk tier.

## Re-verify checklist (run each task)
1. Hit `GET /api/schema` and extract DDL for every table your task touches; note CHECK enums (they constrain valid values).
2. Hit `GET /api/data-dictionary` and re-read the `conventions` block + the per-column descriptions for the tables you use.
3. For write tasks, hit `GET /api/correction-audit` to see the exact audit-row column set and existing keys (avoid collision with your `audit_id`/`correction_key`).
4. Confirm the production-exclusion flags (`is_internal`, `is_test`) and the cohort window column names before writing cohort filters — these vary and gates the entire population.
